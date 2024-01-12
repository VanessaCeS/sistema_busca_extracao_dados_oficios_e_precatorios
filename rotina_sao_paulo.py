import re
import PyPDF2
import traceback
from logs import log
from cna_oab import login_cna
from dotenv import load_dotenv
from funcoes_arteria import enviar_valores_oficio_arteria
from auxiliares import  encontrar_cidade_e_data_expedicao, encontrar_indice_linha, formatar_data_padra_arteria, ler_arquivo_pdf_transformar_em_txt,limpar_dados, tipo_precatorio
from esaj_sao_paulo_precatorios import get_docs_oficio_precatorios_tjsp
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro, consultar_processos

load_dotenv('.env')

def buscar_dados_tribunal_sao_paulo():     
  dados = consultar_processos('.8.26.0053')
  for d in dados:
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        ler_documentos(dado)

def ler_documentos(dado_xml):
    try:
        if dado_xml['processo_origem'] == None:
          processo_geral = dado_xml['processo']
          doc = get_docs_oficio_precatorios_tjsp(dado_xml['processo'],zip_file=False, pdf=True)
        else:
          processo_geral = dado_xml['processo_origem'].split('/')[0]
          doc = get_docs_oficio_precatorios_tjsp(processo_geral ,zip_file=False, pdf=True)
        if doc:
          for codigo_processo, valores in dict.items(doc):
              try:
                file_path = valores[0][2]
                id_documento = valores[0][0]
                arquivo_pdf = f"arquivos_pdf_sao_paulo/{codigo_processo}_{id_documento}_arquivo_precatorio.pdf"
                with open(arquivo_pdf, "wb") as arquivo:
                        arquivo.write(file_path)
                arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
                dado_xml.pop('vara')
                dado_xml.pop('processo')
                dados_complementares = {"processo_geral": processo_geral, "codigo_processo": codigo_processo, 'id_documento': id_documento} | dado_xml
                extrair_dados_txt(arquivo_pdf, arquivo_txt, dados_complementares)
              except:
                continue
    except Exception as e:
        print(f"Erro no processo ---> {processo_geral}", f'Erro: {e}')
        print(traceback.print_exc())
        pass
    
def extrair_dados_txt(arquivo_pdf, dados_xml):
    arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    

    indice_oficio_requisitorio = 7
    oficio_requisitorio = 'OFÍCIO REQUISITÓRIO' in linhas[indice_oficio_requisitorio].upper().replace('  ', ' ').strip()
    if oficio_requisitorio == False:
      oficio_requisitorio = 'OFÍCIO REQUISITÓRIO' in linhas[indice_oficio_requisitorio + 1].upper().replace('  ', ' ').strip()

    if oficio_requisitorio:
      devedor = pegar_valor(linhas[encontrar_indice_linha(linhas, "devedor:")]) if encontrar_indice_linha(linhas, "devedor:") else pegar_valor(linhas[encontrar_indice_linha(linhas, "executado(s):")]) 
      if devedor:
        cidade, data_expedicao = encontrar_cidade_e_data_expedicao(arquivo_txt)
        processo = pegar_valor(linhas[encontrar_indice_linha(linhas, "processo nº: ")])        
        dados_advogado = pegar_dados_advogado(linhas, encontrar_indice_linha(linhas, "advogad"), processo)
        conhecimento = pegar_valor(linhas[encontrar_indice_linha(linhas, "processo principal/conhecimento:")]) if encontrar_indice_linha(linhas, "processo principal/conhecimento:") else processo.split('/')[0]
        valor_juros = pegar_valor(linhas[encontrar_indice_linha(linhas, "juros moratórios")]).split(' ')[0] if encontrar_indice_linha(linhas, 'juros moratórios') else ''

        dados = {
          'cidade': cidade,
          'vara': linhas[3].replace('\n',''),
          'devedor': devedor,
          'natureza': pegar_valor(linhas[encontrar_indice_linha(linhas, "natureza")]).split('-')[0].upper().strip(), 
          'estado': 'São Paulo',
          'processo_origem': conhecimento,
          'data_expedicao': data_expedicao,
          'site':  'https://esaj.tjac.jus.br',
          'valor_juros': valor_juros.replace('.', '').replace(',','.').strip(), 
          'advogado': pegar_valor(linhas[encontrar_indice_linha(linhas, "advogad")]), 
          'qtd_credores': pegar_valor(linhas[encontrar_indice_linha(linhas, "quantidade de credores")]),
          'valor_global': pegar_valor(linhas[encontrar_indice_linha(linhas, "valor global da requisição:")]).split(' ')[0].replace('.', '').replace(',','.').strip()
        } | dados_advogado | dados_xml

        extrair_informacoes_credores_e_mandar_para_banco_dados(arquivo_pdf, dados)


def pegar_valor(string):
  valor = string.split(':')[1].replace('\n', '').replace('R$','').strip()
  return valor

def pegar_dados_advogado(linhas, indice, processo):
  if indice:
    string = linhas[indice].split(':')
    advogado = string[1].replace('OABC','')
    oab = string[-1].split('/')[0].strip()
    seccional = string[-1].split('/')[1].replace('\n','').strip()
    dados_advogado = login_cna(oab, seccional, '', advogado,processo)
    return dados_advogado
  else:
    return {'advogado': '', 'telefone': '', 'oab' : '', 'documento_advogado': '', 'seccional': ''}

def extrair_informacoes_credores_e_mandar_para_banco_dados(arquivo_pdf,dados_txt):
  pdf_file = open(arquivo_pdf, 'rb')
  pdf_reader = PyPDF2.PdfReader(pdf_file)
  text = ''
  for page_num in range(len(pdf_reader.pages)):
    page = pdf_reader.pages[page_num]
    text = page.extract_text() 
    if f'Credor  nº.:' in text:
      linhas = text.split('\n')
      data_nascimento = pegar_valor(linhas[encontrar_indice_linha(linhas, 'data do nascimento')]) if encontrar_indice_linha(linhas, 'data do nascimento') else ''
      data_nascimento = formatar_data_padra_arteria(data_nascimento) if data_nascimento.lower() != 'n/c' else ''
      valor_principal = pegar_valor(linhas[encontrar_indice_linha(linhas, 'total deste requerente')]).split(' ')[0] if encontrar_indice_linha(linhas, 'total deste requerente') else pegar_valor(linhas[encontrar_indice_linha(linhas, 'valor total da condenação')]).split(' ')[0]
      dados = {
        'tipo': 'credor',
        'data_nascimento': data_nascimento,
        'credor': pegar_valor(linhas[encontrar_indice_linha(linhas, 'nome')]),
        'documento': pegar_valor(linhas[encontrar_indice_linha(linhas, 'cpf/cnpj')]),
        'valor_principal': valor_principal.replace('.', '').replace(',','.').strip() 
      } | dados_txt

      atualizar_ou_inserir_pessoa_no_banco_de_dados(dados['documento'], dados)
      if int(dados_txt['qtd_credores']) > 1:
        dados['valor_principal_credor'] = dados['valor_principal']
      dados['id_sistema_arteria']  = enviar_valores_oficio_arteria(arquivo_pdf, dados)
      site = dados['site']
      atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
      atualizar_ou_inserir_pessoa_precatorio(dados['documento'], dados['processo'])
      log( dados['processo'], 'Sucesso', site, 'Precatório registrado com sucesso',dados['estado'], dados['tribunal'])
      atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})
