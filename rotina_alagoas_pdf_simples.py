import re
import PyPDF2
import traceback
from logs import log
from cna_oab import login_cna
from funcoes_arteria import enviar_valores_oficio_arteria
from auxiliares import  encontrar_indice_linha, formatar_data_padra_arteria, tipo_de_natureza, transformar_valor_monetario_padrao_arteria
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro

def extrair_dados_pdf(arquivo_pdf, dados):
      try:
          processo_geral = dados['processo']
          pdf_file = open(arquivo_pdf, 'rb')
          pdf_reader = PyPDF2.PdfReader(pdf_file)
          text = ''
          for page_num in range(len(pdf_reader.pages)): 
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
            with open(f"arquivos_txt_alagoas/{processo_geral}_extrair.txt", "w", encoding='utf-8') as arquivo:
                    arquivo.write(text)
          ler_dados_txt(arquivo_pdf, dados, f'arquivos_txt_alagoas/{processo_geral}_extrair.txt')
      except Exception as e:
        print("ERRO NO PDF SIMPLES", f"Erro no processo -> {processo_geral}", f'Erro: {e}')
        print(traceback.print_exc())
        pass

def ler_dados_txt(arquivo_pdf, dados_xml,arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    

    processo = pegar_valores(linhas[encontrar_indice_linha(linhas, 'do processo:')])
    dados_advogado = extrair_e_salvar_dados_advogado(processo,arquivo_pdf, linhas)
    
    dados = {
      'processo_origem': linhas[encontrar_indice_linha(linhas, 'da ação') + 1].replace('\n', '').strip(),
      'processo': processo,
      'vara': pegar_valores(linhas[encontrar_indice_linha(linhas, 'vara:')]),
      'valor_principal': transformar_valor_monetario_padrao_arteria(pegar_valores(linhas[encontrar_indice_linha(linhas, 'originário:')])),
      'valor_juros': transformar_valor_monetario_padrao_arteria(pegar_valores(linhas[encontrar_indice_linha(linhas, 'moratórios:')])),
      'valor_global': transformar_valor_monetario_padrao_arteria(pegar_valores(linhas[encontrar_indice_linha(linhas, 'devido ao beneficiário:')])),
      'natureza': tipo_de_natureza(pegar_valores(linhas[encontrar_indice_linha(linhas, 'do crédito:')])),
      'credor': pegar_valores(linhas[encontrar_indice_linha(linhas, 'do credor:')]),
      'devedor': pegar_valores(linhas[encontrar_indice_linha(linhas, 'ente devedor:')]),
      'documento': pegar_valores(linhas[encontrar_indice_linha(linhas, 'cpf')]).split(' ')[0],
      'data_nascimento': formatar_data_padra_arteria(pegar_valores(linhas[encontrar_indice_linha(linhas, " nascimento:")])),
      'data_expedicao': pegar_data_expedicao(pegar_valores(linhas[encontrar_indice_linha(linhas, "liberado nos autos")])),
      'cidade': pegar_cidade(linhas[encontrar_indice_linha(linhas, "endereço:")])
          } | dados_advogado | dados_xml

    enviar_dados_banco_de_dados_e_arteria_alagoas(arquivo_pdf, dados)

def pegar_valores(string):
  valor = string.split(':')[1].replace('\n', '').replace('R$','').strip()
  return valor 

def extrair_e_salvar_dados_advogado(processo, arquivo_pdf, linhas):
  advogado = ''
  oab = ''
  documento_advogado = ''
  with open(arquivo_pdf, 'rb') as pdf_file:
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    for page_num in range(len(pdf_reader.pages)):
      page = pdf_reader.pages[page_num]
      text = page.extract_text()
      if 'Honorários Contratuais:' in text or 'Honorários  Contratuais:' in text:
        indice_linha_nome = encontrar_indice_linha(linhas, "nome:")
        if indice_linha_nome:
          advogado = linhas[indice_linha_nome].replace('\n', '').strip().split(':')[1].strip()
          oab_e_documento = linhas[indice_linha_nome + 1].replace('\n', '').strip()
          oab = oab_e_documento.split('CPF/CNPJ')[0].split(':')[1].strip()
          documento_advogado = oab_e_documento.split('CPF/CNPJ')[1].replace(':', '').strip()
          if advogado.upper() == 'NÃO' or advogado == "*" or oab.upper() == 'NÃO' or oab == "*":
            advogado = ''
            oab = ''
            documento_advogado = ''

    dados_advogado = login_cna(oab, 'AL', documento_advogado, advogado, processo)
    return dados_advogado


def pegar_data_expedicao(string):
  padrao_data = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
  match = padrao_data.search(string)
  data = ''
  if match:
    data = formatar_data_padra_arteria(match.group(1))
  return data

def pegar_cidade(string):
  return string.split('Fone:')[1].split(',')[1].split('-')[0].strip()

def enviar_dados_banco_de_dados_e_arteria_alagoas(arquivo_pdf, dados):    
    documento = dados['documento']
    site = dados['site']
    atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento'], 'estado': 'Alagoas', 'tipo': 'credor'})
    id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
    dados['id_sistema_arteria'] = id_sistema_arteria
    atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
    atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])
    log( dados['processo'], 'Sucesso',site , 'Precatório registrado com sucesso', 'Alagoas', dados['tribunal'])
    atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})
