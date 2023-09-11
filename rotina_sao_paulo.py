import os
import re
import json
import PyPDF2
import requests
import xmltodict
from util import regex
from datetime import datetime
from dotenv import load_dotenv
from esaj_sao_paulo_precatorios import get_docs_oficio_precatorios_tjsp
from utils import apagar_arquivos_txt

load_dotenv('.env')

def buscar_xml():
  url_info_cons = "https://clippingbrasil.com.br/InfoWsScript/service_xml.php"

  json_data = {
        "data": datetime.utcnow(),
        "sigla": f"{os.getenv('sigla')}",
        "user":f"{os.getenv('user')}",
        "pass":f"{os.getenv('password')}"
        }
        
  json_string = json.dumps(json_data)
  form_data = {
      "json": json_string
  }

  response = requests.post(url_info_cons, data=form_data)
  with open('dados_processos.xml', 'w', encoding='utf-8') as arquivo:
    arquivo.write(response.content)
  return response.content 

def ler_xml(arquivo_xml):     
  with open(arquivo_xml, 'r', encoding='utf-8') as fd:
    doc = xmltodict.parse(fd.read())
  
  dados = []
  materia = []
  base_doc = doc['Pub_OL']['Publicacoes']
  for i in range(len(doc['Pub_OL']['Publicacoes']))  :
    dados.append({"Processo": f"{base_doc[i]['Processo']}", "Tribunal": f"{base_doc[i]['Tribunal']}"})
    materia.append(f"{base_doc[i]['Materia']}")

  for dado in dados:
    if dado['Tribunal'] == 'STFSITE':
      dado['Vara'] = 'STF'
      dado['Tribunal'] = 'STF'
    elif dado['Tribunal'] == 'STJ':
      dado['Vara'] = 'STJ'
    else:
      for k in range(len(materia)):
        if 'Orgão' in materia[k]:
          padrao = r'Orgão: (.*)'
          orgao = re.search(padrao, materia[k]).group(1)
          dado['Vara'] = orgao
  return dados

def ler_documentos():
  dados = ler_xml('relatorio.xml')

  for dado in dados:
    doc = get_docs_oficio_precatorios_tjsp(dado['Processo'], zip_file=False, pdf=True)
    file_path = doc['1H00029HC0001'][0][1]

    with open(f"arquivo_precatorio.pdf", "wb") as arquivo:
              arquivo.write(file_path)

    pdf_file = open('arquivo_precatorio.pdf', 'rb')
    pdf_reader = PyPDF2.PdfFileReader(pdf_file)
    for i in range(pdf_reader.numPages):
      page = pdf_reader.getPage(i)
      text = page.extractText()

      with open(f"arquivos_txt/extrair.txt", "a", encoding='utf-8') as arquivo:
              arquivo.write(text)
      extrair_dados_pdf(f"arquivos_txt/extrair.txt")

  apagar_arquivos_txt('./arquivos_txt_sao_paulo')

def extrair_dados_pdf(arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()

    indice_processo = encontrar_indice_linha(linhas, "Processo  nº: ")
    indice_credor = encontrar_indice_linha(linhas, "Credor(s):")
    indice_devedor = encontrar_indice_linha(linhas, "Devedor:")
    indice_natureza = encontrar_indice_linha(linhas, "Natureza:")
    indice_valor_global = encontrar_indice_linha(linhas, "Valor  global  da requisição:")
    indice_valor_principal = encontrar_indice_linha(linhas, "Principal/Indenização:")
    indice_valor_juros = encontrar_indice_linha(linhas, "Juros  Moratórios:")
    indice_cpf_cnpj = encontrar_indice_linha(linhas, "CPF/CNPJ/RNE:")

    if (
        indice_processo is not None
        and indice_credor is not None
        and indice_devedor is not None
        and indice_natureza is not None
        and indice_valor_global is not None
        and indice_valor_principal is not None
        and indice_valor_juros is not None
        and indice_cpf_cnpj is not None

    ):
        processo = linhas[indice_processo]
        credor = linhas[indice_credor]
        devedor = linhas[indice_devedor]
        natureza = linhas[indice_natureza]
        valor_global = linhas[indice_valor_global]
        valor_principal = linhas[indice_valor_principal]
        valor_juros = linhas[indice_valor_juros]
        cpf_cnpj = linhas[indice_cpf_cnpj]

        dados_extraidos = {
            'Processo': regex(processo),
            'Credor': regex(credor),
            'Devedor': regex(devedor),
            'Natureza': regex(natureza),
            'Valor Global': regex(valor_global),
            'Valor Principal': regex(valor_principal),
            'Valor Juros': regex(valor_juros),
            'CPF/CNPJ': regex(cpf_cnpj)}
    else:
        dados_extraidos = {
            'Processo': None,
            'Credor': None,
            'Devedor': None,
            'Natureza': None,
            'Valor Global': None,
            'Valor Principal': None,
            'Valor Juros': None,
            'CPF/CNPJ': None
        }

    return dados_extraidos

def encontrar_indice_linha(linhas, texto):
    for indice, linha in enumerate(linhas):
      if texto in linha:
        return indice
    return None


# ler_documentos()

ler_xml('relatorio.xml')