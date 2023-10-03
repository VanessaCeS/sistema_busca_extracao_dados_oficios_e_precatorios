import re
import PyPDF2
import xmltodict
import traceback
from cna_oab import pegar_foto_oab
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_alagoas_precatorios import get_docs_oficio_precatorios_tjal
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados
from utils import apagar_arquivos_txt, data_corrente_formatada, encontrar_indice_linha, extrair_processo_origem, limpar_dados, mandar_dados_regex, regex, tipo_precatorio, verificar_tribunal

def ler_xml(arquivo_xml):     
  # with open(f'arquivos_xml/relatorio_{data_corrente_formatada()}.xml', 'r', encoding='utf-8') as fd:
  #   doc = xmltodict.parse(fd.read())
  with open(arquivo_xml, 'r', encoding='utf-8') as fd:
    doc = xmltodict.parse(fd.read())

  dados = []
  base_doc = doc['Pub_OL']['Publicacoes']
  for i in range(len(doc['Pub_OL']['Publicacoes']))  :
    processo_origem =  extrair_processo_origem(f"{base_doc[i]['Publicacao']})")
    dados.append({"processo": f"{base_doc[i]['Processo']}", "tribunal": f"{base_doc[i]['Tribunal']}", "materia": f"{base_doc[i]['Materia']}", 'processo_origem': processo_origem})
    
  for d in dados:
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        if verificar_tribunal(d['processo']):
          ler_documentos(dado)
        else:
          pass
  apagar_arquivos_txt([])

def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.8.02.\d{4}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True
        
def ler_documentos(arquivo_pdf, dados):
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
          extrair_dados_pdf(arquivo_pdf, dados, f'arquivos_txt_alagoas/{processo_geral}_extrair.txt')
      except Exception as e:
        print("Erro no processo -> ", f'Erro: {e}')
        print(traceback.print_exc())
        pass

def extrair_dados_pdf(arquivo_pdf, dados_xml,arquivo_txt):
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
    indice_advogado  = encontrar_indice_linha(linhas, "OAB:") - 1
    indice_oab_e_documento_advogado = encontrar_indice_linha(linhas, "OAB")
    indice_data_nascimento = encontrar_indice_linha(linhas, "Data  de nascimento:")
    indice_data_expedicao = encontrar_indice_linha(linhas, "liberado nos autos")
    indice_cidade = encontrar_indice_linha(linhas, "datado") - 1
    processo_origem = pegar_processo_origem(linhas,{'indice_processo': indice_processo})
    
    indices = {'indice_precatorio': indice_precatorio,'indice_vara': indice_vara,'indice_valor_principal': indice_valor_principal, 'indice_valor_global': indice_valor_global, 'indice_credor': indice_credor,'indice_devedor': indice_devedor, 'indice_data_expedicao': indice_data_expedicao,'indice_natureza': indice_natureza,'indice_valor_juros': indice_valor_juros, 'indice_documento': indice_documento, 'indice_data_nascimento': indice_data_nascimento}
    
    cidade = pegar_cidade(linhas,{'indice_cidade': indice_cidade})
    dados = dados_xml | cidade |  processo_origem 
      
    enviar_dados(indices, linhas, arquivo_pdf, dados)

def enviar_dados(indices, linhas, arquivo_pdf, dados):
    dados_regex = mandar_dados_regex(indices, linhas)
    dados = dados | dados_regex
    
    atualizar_ou_inserir_pessoa_no_banco_de_dados(dados['documento'], {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento']})

    id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
    dados['id_sistema_arteria'] = id_sistema_arteria

    atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
    print('DADOS PRECATORIOS ---->>> ', dados)

    atualizar_ou_inserir_pessoa_precatorio(dados_regex['documento'], dados['processo'])
    print('----------------- FIM ---------------------------------')

def pegar_processo_origem(texto,indice):
  for i in dict.keys(indice):
      if indice[i] != None:
        origem = texto[indice[i]].replace('\n', '').replace(',', '').strip()
        return {'processo_origem': origem}
      else:
          return {'processo_origem': ''}
  
  
def pegar_cidade(texto, indice):
    for i in dict.keys(indice):
      if indice[i] != None:
        cidade = texto[indice[i]].replace('\n', '').replace(',', '').replace('.', '').strip()
        return {'cidade': cidade}
      else:
          return {'cidade': ''}
# ler_documentos({'processo': '0500334-40.2023.8.02.0001'})