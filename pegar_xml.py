import base64
import os
import traceback
from funcoes_arteria import enviar_valores_oficio_arteria
import PyPDF2
import requests
import xmltodict
from utils import encontrar_data_expedicao_e_cidade, extrair_processo_origem, limpar_dados, mandar_para_banco_de_dados, regex, text_ocr, tipo_precatorio,  verificar_tribunal
from datetime import datetime
from dotenv import load_dotenv
from esaj_precatorios import get_docs_oficio_precatorios_tjsp

load_dotenv('.env')

def buscar_xml():
  url_info_cons = "https://clippingbrasil.com.br/InfoWsScript/service_xml.php"
  headers = {
      "Content-Type": "application/json; charset=utf-8"
    }

  data = {
    'input':
          {  "data": "21/08/2023",
            "sigla": f"{os.getenv('sigla')}",
            "user":f"{os.getenv('user')}",
            "pass":f"{os.getenv('password')}"}
    }

  response = requests.post(url=url_info_cons, headers=headers, json=data)
  print(response)
  data = datetime.utcnow()
  with open(f'arquivos_xml/dados_processos_{data.day}_{data.month}.xml', 'w', encoding='utf-8') as arq:
    arquivo = arq.write(response.content)
    ler_xml(arquivo)

def ler_xml(arquivo_xml):     
  with open(arquivo_xml, 'r', encoding='utf-8') as fd:
    doc = xmltodict.parse(fd.read())
  
  dados = []
  base_doc = doc['Pub_OL']['Publicacoes']
  for i in range(len(doc['Pub_OL']['Publicacoes']))  :
    processo_origem =  extrair_processo_origem(f"{base_doc[i]['Publicacao']})")
    dados.append({"processo": f"{base_doc[i]['Processo']}", "tribunal": f"{base_doc[i]['Tribunal']}", "materia": f"{base_doc[i]['Materia']}", 'origem': processo_origem})
  
  for d in dados:
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        if verificar_tribunal(d['processo']):
          ler_documentos(dado)
        else:
          pass
  apagar_arquivos_txt()
  
def ler_documentos(dado):
      try:
        if dado['origem'] == None:
          processo_geral = dado['processo']
          doc = get_docs_oficio_precatorios_tjsp(dado['processo'],zip_file=False, pdf=True)
        else:
          processo_geral = dado['origem'].split('/')[0]
          doc = get_docs_oficio_precatorios_tjsp(processo_geral ,zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          file_path = doc[codigo_processo][0][1]
          arquivo_pdf = f"arquivos_pdf/{processo_geral}_arquivo_precatorio.pdf"

          with open(arquivo_pdf, "wb") as arquivo:
                  arquivo.write(file_path)

          pdf_file = open(arquivo_pdf, 'rb')
          pdf_reader = PyPDF2.PdfReader(pdf_file)
          text = ''
          for page_num in range(len(pdf_reader.pages)): 
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
            with open(f"arquivos_txt/{processo_geral}_extrair.txt", "w", encoding='utf-8') as arquivo:
                    arquivo.write(text)
          
          dados_pdf = extrair_dados_pdf(f"arquivos_txt/{processo_geral}_extrair.txt")
          dados_complementares = {"processo_geral": processo_geral, "codigo_processo": codigo_processo, 'site': 'https://esaj.tjac.jus.br'}
          novos_dados = dado | dados_pdf | dados_complementares

          mandar_para_banco_de_dados(dado['processo'], novos_dados)
          enviar_valores_oficio_arteria(arquivo_pdf, novos_dados)
      except Exception as e:
        print(f"Erro meno, processo -> {processo_geral}", e)
        print(traceback.print_exc())
        pass

def extrair_dados_pdf(arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    
    indice_vara = 3 
    indice_precatorio = encontrar_indice_linha(linhas, "Processo  nº: ")
    indice_conhecimento = encontrar_indice_linha(linhas, "Processo  Principal/Conhecimento:")
    indice_credor = encontrar_indice_linha(linhas, "Credor")
    indice_executado = encontrar_indice_linha(linhas, "Executado(s):")
    indice_exequente = encontrar_indice_linha(linhas, "Exequente(s):")
    indice_devedor = encontrar_indice_linha(linhas, "Devedor:")
    indice_natureza = encontrar_indice_linha(linhas, "Natureza:")
    indice_valor_global = encontrar_indice_linha(linhas, "Valor  global  da requisição:")
    indice_principal = encontrar_indice_linha(linhas, "Principal/Indenização:")
    indice_juros = encontrar_indice_linha(linhas, "Juros  Moratórios:")
    indice_cpf = encontrar_indice_linha(linhas, "CPF/CNPJ")
    indice_nascimento = encontrar_indice_linha(linhas, "Data  do nascimento:")
    
    
    indices = {'indice_vara': indice_vara,'indice_precatorio': indice_precatorio, 'indice_conhecimento': indice_conhecimento, 'indice_credor': indice_credor,'indice_devedor': indice_devedor,'indice_exequente': indice_exequente, 'indice_executado': indice_executado,'indice_natureza': indice_natureza, 'indice_global': indice_valor_global, 'indice_principal': indice_principal, 'indice_juros': indice_juros, 'indice_cpf': indice_cpf, 'indice_nascimento': indice_nascimento}
    dados = {}

    for i in dict.keys(indices):
      if indices[i] != None:
        valores = linhas[indices[i]]
        aqui = regex(valores)
        dados = dados | aqui
      else:
        nome = i.split('_')[1]
        dados = dados | {f'{nome}': ''}

    cidada_e_data_precatorio = encontrar_data_expedicao_e_cidade(arquivo_txt)
    dados = dados | cidada_e_data_precatorio
    return dados

def encontrar_indice_linha(linhas, texto):
    for indice, linha in enumerate(linhas):
      if texto in linha:
        return indice
    return None

def apagar_arquivos_txt():
    pasta = './arquivos_txt'
    arquivos = os.listdir(pasta) 
    for arquivo in arquivos:
        caminho_arquivo = os.path.join(pasta, arquivo)
        if os.path.isfile(caminho_arquivo):  
            os.remove(caminho_arquivo)

def pegar_documentos_pessoais(processo):
  doc = get_docs_oficio_precatorios_tjsp(processo, zip_file=False, pdf=True)
  file_path = doc['1H00029HC0001'][0][1]
  with open(f"arquivos_pessoais.pdf", "wb") as arq:
    arquivo = arq.write(file_path)
  
  arquivo_base_64 = converter_arquivo_base_64(arquivo)
  text_ocr(arquivo_base_64)

def converter_arquivo_base_64(nome_arquivo):
  with open(nome_arquivo, "rb") as arquivo:
            dados = arquivo.read()
            dados_base64 = base64.b64encode(dados)
            return dados_base64.decode("utf-8") 
