import re
import PyPDF2
import xmltodict
import traceback
from dotenv import load_dotenv
from cna_oab import pegar_foto_oab
from utils import apagar_arquivos_txt, mandar_documento_para_ocr
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_sao_paulo_precatorios import get_docs_oficio_precatorios_tjsp
from utils import encontrar_data_expedicao_e_cidade, extrair_processo_origem, limpar_dados, mandar_para_banco_de_dados, regex, tipo_precatorio,  verificar_tribunal
load_dotenv('.env')

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
  apagar_arquivos_txt('./arquivos_txt_sao_paulo')
  return dados

def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.8.26.\d{4}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True
        
def ler_documentos(dado_xml):
    try:
        if dado_xml['origem'] == None:
          processo_geral = dado_xml['processo']
          doc = get_docs_oficio_precatorios_tjsp(dado_xml['processo'],zip_file=False, pdf=True)
        else:
          processo_geral = dado_xml['origem'].split('/')[0]
          doc = get_docs_oficio_precatorios_tjsp(processo_geral ,zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          file_path = doc[codigo_processo][0][1]
          arquivo_pdf = f"arquivos_pdf_sao_paulo/{processo_geral}_arquivo_precatorio.pdf"

          with open(arquivo_pdf, "wb") as arquivo:
                  arquivo.write(file_path)

          pdf_file = open(arquivo_pdf, 'rb')
          pdf_reader = PyPDF2.PdfReader(pdf_file)
          text = ''
          for page_num in range(len(pdf_reader.pages)): 
              page = pdf_reader.pages[page_num]
              text += page.extract_text()
          with open(f"arquivos_txt_sao_paulo/{processo_geral}_extrair.txt", "w", encoding='utf-8') as arquivo:
                    arquivo.write(text)
          
          dados_pdf = extrair_dados_pdf(f"arquivos_txt_sao_paulo/{processo_geral}_extrair.txt")
          dados_complementares = {"processo_geral": processo_geral, "codigo_processo": codigo_processo, 'site': 'https://esaj.tjac.jus.br'}
          novos_dados = dado_xml | dados_pdf | dados_complementares
          id_arteria = enviar_valores_oficio_arteria(arquivo_pdf, novos_dados)
          novos_dados = novos_dados | {'id_rastreamento': id_arteria}
          mandar_para_banco_de_dados(codigo_processo, novos_dados)
    except Exception as e:
        print(f"Erro no processo -> {processo_geral}", f'Erro: {e}')
        print(traceback.print_exc())
        pass
    
def extrair_dados_pdf(arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    

    indice_estado = 0
    indice_vara = 3 
    indice_precatorio = encontrar_indice_linha(linhas, "Processo  nº: ")
    indice_conhecimento = encontrar_indice_linha(linhas, "Processo  Principal/Conhecimento:")
    indice_credor = encontrar_indice_linha(linhas, "Credor")
    indice_executado = encontrar_indice_linha(linhas, "Executado(s):")
    indice_exequente = encontrar_indice_linha(linhas, "Exequente(s):")
    indice_devedor = encontrar_indice_linha(linhas, "Devedor:")
    indice_advogado = encontrar_indice_linha(linhas, "Advogad")
    indice_natureza = encontrar_indice_linha(linhas, "Natureza")
    indice_valor_global = encontrar_indice_linha(linhas, "Valor  global  da requisição:")
    indice_principal = encontrar_indice_linha(linhas, "Principal/Indenização:")
    indice_juros = encontrar_indice_linha(linhas, "Juros  Moratórios:")
    indice_cpf = encontrar_indice_linha(linhas, "CPF/CNPJ")
    indice_nascimento = encontrar_indice_linha(linhas, "Data  do nascimento:")
    
    indices = {'indice_estado': indice_estado,'indice_vara': indice_vara,'indice_precatorio': indice_precatorio, 'indice_conhecimento': indice_conhecimento, 'indice_credor': indice_credor,'indice_devedor': indice_devedor,'indice_exequente': indice_exequente, 'indice_executado': indice_executado,'indice_natureza': indice_natureza, 'indice_global': indice_valor_global, 'indice_principal': indice_principal, 'indice_juros': indice_juros, 'indice_cpf': indice_cpf, 'indice_nascimento': indice_nascimento}
    dados = {}

    for i in dict.keys(indices):
      if indices[i] != None:
        valores = linhas[indices[i]]
        valores_regex = regex(valores)
        dados = dados | valores_regex
      else:
        nome = i.split('_')[1]
        dados = dados | {f'{nome}': ''}

    if dados['natureza'] == '':
      dados['natureza'] = 'ALIMENTAR'

    advogado_e_oab = regex(linhas[indice_advogado])
    cidada_e_data_precatorio = encontrar_data_expedicao_e_cidade(arquivo_txt)
    dados = dados | cidada_e_data_precatorio | advogado_e_oab
    oab(dados)
    return dados

def encontrar_indice_linha(linhas, texto):
    for indice, linha in enumerate(linhas):
      if texto in linha:
        return indice
    return None

def oab(dado):
  if dado['oab'] != '' and dado['seccional'] != '':
    pdf = pegar_foto_oab(dado['oab'], dado['seccional'])
    arquivo_txt = mandar_documento_para_ocr(pdf)



