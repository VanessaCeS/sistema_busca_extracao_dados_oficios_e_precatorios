import re
import PyPDF2
import xmltodict
import traceback
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_alagoas_precatorios import get_docs_oficio_precatorios_tjal
from utils import apagar_arquivos_txt, encontrar_indice_linha, extrair_processo_origem, limpar_dados, mandar_para_banco_de_dados, regex, tipo_precatorio, verificar_tribunal

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
  apagar_arquivos_txt('./arquivos_txt_alagoas')

def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.8.02.\d{4}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True
        
def ler_documentos(dado_xml):
      try:
        processo_geral = dado_xml['processo']
        doc = get_docs_oficio_precatorios_tjal(dado_xml['processo'],zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          file_path = doc[codigo_processo][0][1]
          arquivo_pdf = f"arquivos_pdf_alagoas/{processo_geral}_arquivo_precatorio.pdf"

          with open(arquivo_pdf, "wb") as arquivo:
                  arquivo.write(file_path)

          pdf_file = open(arquivo_pdf, 'rb')
          pdf_reader = PyPDF2.PdfReader(pdf_file)
          text = ''
          for page_num in range(len(pdf_reader.pages)): 
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
            with open(f"arquivos_txt_alagoas/{processo_geral}_extrair.txt", "w", encoding='utf-8') as arquivo:
                    arquivo.write(text)
          dados_pdf = extrair_dados_pdf(f'arquivos_txt_alagoas/{processo_geral}_extrair.txt')
          dados = dado_xml | dados_pdf | {"processo_geral": processo_geral,'codigo_processo': codigo_processo, 'site': 'https://www2.tjal.jus.br/esaj/', 'tipo_precatorio': 'ESTADUAL', 'estado': 'ALAGOAS', 'seccional': 'AL'}
          id_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
          dados = dados | {'id_rastreamento': id_arteria}
          mandar_para_banco_de_dados(codigo_processo, dados)
      except Exception as e:
        print(f"Erro no processo -> {processo_geral}", f'Erro: {e}')
        print(traceback.print_exc())
        pass

def extrair_dados_pdf(arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    
    indice_processo = encontrar_indice_linha(linhas, 'Autos  da Ação  n.º') + 1
    indice_precatorio = encontrar_indice_linha(linhas, "Número  do processo:")
    indice_vara = encontrar_indice_linha(linhas, "Origem/Foro  Comarca/  Vara:")
    indice_valor = encontrar_indice_linha(linhas, "Valor  originário:")
    indice_valor_total = encontrar_indice_linha(linhas, "Valor  total da requisição:")
    indice_juros = encontrar_indice_linha(linhas, "Valor  dos juros  moratórios:")
    indice_natureza = encontrar_indice_linha(linhas, "Natureza  do Crédito:")
    indice_credor = encontrar_indice_linha(linhas, "Nome  do Credor:")
    indice_devedor = encontrar_indice_linha(linhas, "Ente Devedor:")
    indice_cpf = encontrar_indice_linha(linhas, "CPF")
    indice_advogado  = encontrar_indice_linha(linhas, "Nome:")
    indice_oab  = encontrar_indice_linha(linhas, "OAB:")
    indice_nascimento = encontrar_indice_linha(linhas, "Data  de nascimento:")
    indice_expedicao = encontrar_indice_linha(linhas, "liberado nos autos")
    indice_cidade = encontrar_indice_linha(linhas, "datado") - 1
    processo_origem = pegar_processo_origem(linhas,{'indice_processo': indice_processo})
    cidade = pegar_cidade(linhas,{'indice_cidade': indice_cidade})
    indices = {'indice_precatorio': indice_precatorio,'indice_vara': indice_vara,'indice_valor': indice_valor, 'indice_valor_total': indice_valor_total, 'indice_credor': indice_credor,'indice_devedor': indice_devedor, 'indice_expedicao': indice_expedicao,'indice_natureza': indice_natureza,'indice_juros': indice_juros, 'indice_cpf': indice_cpf, 'indice_nascimento': indice_nascimento, 'indice_advogado': indice_advogado, 'indice_oab': indice_oab}
    dados = {}

    for i in dict.keys(indices):
      nome = i.split('_')[1]
      if indices[i] != None:
        valores = linhas[indices[i]]
        aqui = regex(valores)
        if aqui == None:
          aqui = {f'{nome}': ''}
        dados = dados | aqui
      else:
          dados = dados | {f'{nome}': ''}
    
    dados = dados | processo_origem | cidade

    return dados

def pegar_processo_origem(texto, indice):
  for i in dict.keys(indice):
      if indice[i] != None:
        origem = texto[indice[i]].replace('\n', '').replace(',', '').strip()
        return {'origem': origem}
      else:
          return {'origem': ''}
      
def pegar_cidade(texto, indice):
    for i in dict.keys(indice):
      if indice[i] != None:
        cidade = texto[indice[i]].replace('\n', '').replace(',', '').replace('.', '').strip()
        return {'cidade': cidade}
      else:
          return {'cidade': ''}
ler_xml('arquivos_xml/relatorio_06_09.xml')