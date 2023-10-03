import re
import PyPDF2
import traceback
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados
from cna_oab import login_cna
from funcoes_arteria import enviar_valores_oficio_arteria
from utils import  encontrar_indice_linha, mandar_dados_regex


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

    indice_processo = encontrar_indice_linha(linhas, 'Autos  da Ação  n.º') + 1
    indice_precatorio = encontrar_indice_linha(linhas, "Número  do processo:")
    indice_vara = encontrar_indice_linha(linhas, "Origem/Foro  Comarca/  Vara:")
    indice_valor_principal = encontrar_indice_linha(linhas, "Valor  originário:")
    indice_valor_global = encontrar_indice_linha(linhas, "Valor  total da requisição:")
    indice_valor_juros = encontrar_indice_linha(linhas, "Valor  dos juros  moratórios:")
    indice_natureza = encontrar_indice_linha(linhas, "Natureza  do Crédito:")
    indice_credor = encontrar_indice_linha(linhas, "Nome  do Credor:")
    indice_devedor = encontrar_indice_linha(linhas, "Ente Devedor:")
    indice_documento = encontrar_indice_linha(linhas, "CPF")
    indice_data_nascimento = encontrar_indice_linha(linhas, "Data  de nascimento:")
    indice_data_expedicao = encontrar_indice_linha(linhas, "liberado nos autos")
    indice_cidade = encontrar_indice_linha(linhas, "datado") - 1
    
    indices = {'indice_precatorio': indice_precatorio,'indice_vara': indice_vara,'indice_valor_principal': indice_valor_principal, 'indice_valor_global': indice_valor_global, 'indice_credor': indice_credor,'indice_devedor': indice_devedor, 'indice_data_expedicao': indice_data_expedicao,'indice_natureza': indice_natureza,'indice_valor_juros': indice_valor_juros, 'indice_documento': indice_documento, 'indice_data_nascimento': indice_data_nascimento}

    dados_regex = mandar_dados_regex(indices, linhas)
    cidade = pegar_cidade(linhas,{'indice_cidade': indice_cidade})
    processo_origem = pegar_processo_origem(linhas,{'indice_processo': indice_processo})
    dados_advogado = extrair_e_salvar_dados_advogado(dados_regex['processo'],arquivo_pdf)
    dados = dados_xml | dados_regex | cidade |  processo_origem | dados_advogado

    enviar_dados_banco_de_dados_e_arteria_alagoas(arquivo_pdf, dados)

def pegar_cidade(texto, indice):
    for i in dict.keys(indice):
      if indice[i] != None:
        cidade = texto[indice[i]].replace('\n', '').replace(',', '').replace('.', '').strip()
        return {'cidade': cidade}
      else:
          return {'cidade': ''}

def pegar_processo_origem(texto,indice):
  for i in dict.keys(indice):
      if indice[i] != None:
        origem = texto[indice[i]].replace('\n', '').replace(',', '').strip()
        return {'processo_origem': origem}
      else:
          return {'processo_origem': ''}

def extrair_e_salvar_dados_advogado(processo, arquivo_pdf):
    pdf_file = open(arquivo_pdf, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    for page_num in range(len(pdf_reader.pages)):
      page = pdf_reader.pages[page_num]
      text = page.extract_text()
      if 'Honorários  Contratuais:' in text:   
          padrao_nome = r'Nome: (.*)'
          resultado_nome = re.search(padrao_nome, text)
          padrao_oab = r'OAB: (.*)'
          resultado_oab = re.search(padrao_oab, text)
          if resultado_nome != None or resultado_oab != None:
            if resultado_nome.group(1).upper() == 'NÃO':
              advogado = ''
            else:
              advogado = resultado_nome.group(1).strip()
          if resultado_oab != None:
            if resultado_oab.group(1) == 'NÃO' or resultado_oab.group(1) == '':
              oab = ''
              documento_advogado = ''
            else:
              oab = resultado_oab.group(1).strip()
              padrao_documento_advogado = r'CPF: (.*)'
              resultado = re.search(padrao_documento_advogado, text)
              if resultado != None:
                documento_advogado = resultado.group(1).strip()
              else:
                documento_advogado = ''
    dados_advogado = login_cna(oab, 'AL', documento_advogado, advogado, processo)

    return dados_advogado

def enviar_dados_banco_de_dados_e_arteria_alagoas(arquivo_pdf, dados):    
    documento = dados['documento']
    atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento']})

    id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
    dados['id_sistema_arteria'] = id_sistema_arteria

    atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
    print('DADOS PRECATORIOS ---->>> ', dados)

    atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])

# extrair_e_salvar_dados_advogado('0500334-40.2023.8.02.0001', "arquivos_pdf_alagoas/0500334-40.2023.8.02.0001_arquivo_precatorio.pdf")
# # ler_documentos("./arquivos_pdf_alagoas/0500334-40.2023.8.02.0001_arquivo_precatorio.pdf", {'processo': '0500334-40.2023.8.02.0001'})