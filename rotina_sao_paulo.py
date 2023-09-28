import re
import PyPDF2
import xmltodict
import traceback
from dotenv import load_dotenv
from cna_oab import pegar_foto_oab
from utils import apagar_arquivos_txt
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_sao_paulo_precatorios import get_docs_oficio_precatorios_tjsp
from banco_de_dados import atualizar_ou_inserir_pessoa, atualizar_ou_inserir_pessoa_precatorio, mandar_precatorios_para_banco_de_dados
from utils import encontrar_data_expedicao_e_cidade, extrair_processo_origem, limpar_dados, regex, tipo_precatorio,  verificar_tribunal
load_dotenv('.env')

def ler_xml(arquivo_xml):     
  with open(arquivo_xml, 'r', encoding='utf-8') as fd: 
    doc = xmltodict.parse(fd.read())
  
  dados = []
  base_doc = doc['Pub_OL']['Publicacoes']
  for i in range(len(doc['Pub_OL']['Publicacoes']))  :
    processo_origem =  extrair_processo_origem(f"{base_doc[i]['Publicacao']})")
    dados.append({"processo": f"{base_doc[i]['Processo']}", "tribunal": f"{base_doc[i]['Tribunal']}", "materia": f"{base_doc[i]['Materia']}", 'processo_origem': processo_origem})
  for d in dados:
      # if d['processo'] == '0215695-62.2023.8.26.0500':
      # if d['processo'] == '0000014-29.2017.8.26.0053':
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
        if dado_xml['processo_origem'] == None:
          processo_geral = dado_xml['processo']
          doc = get_docs_oficio_precatorios_tjsp(dado_xml['processo'],zip_file=False, pdf=True)
        else:
          processo_geral = dado_xml['processo_origem'].split('/')[0]
          doc = get_docs_oficio_precatorios_tjsp(processo_geral ,zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          file_path = doc[codigo_processo][0][2]
          id_documento = doc[codigo_processo][0][0]
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
          
          dados_txt = extrair_dados_txt(f"arquivos_txt_sao_paulo/{processo_geral}_extrair.txt")
          
          dados_complementares = {"processo_geral": processo_geral, "codigo_processo": codigo_processo, 'site': 'https://esaj.tjac.jus.br', 'id_documento': id_documento}
          novos_dados = dado_xml | dados_txt | dados_complementares
          extrair_informacoes_credores_e_mandar_para_banco_dados(arquivo_pdf, novos_dados)
    except Exception as e:
        print(f"Erro no processo ---> {processo_geral}", f'Erro: {e}')
        print(traceback.print_exc())
        pass
    
def extrair_dados_txt(arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    

    indice_estado = 0
    indice_vara = 3 
    indice_precatorio = encontrar_indice_linha(linhas, "Processo  nº: ")
    indice_conhecimento = encontrar_indice_linha(linhas, "Processo  Principal/Conhecimento:")
    indice_executado = encontrar_indice_linha(linhas, "Executado(s):")
    indice_devedor = encontrar_indice_linha(linhas, "Devedor:")
    indice_advogado = encontrar_indice_linha(linhas, "Advogad")
    indice_documento_advogado = encontrar_indice_linha(linhas, "Dados  do Advogado") 
    indice_natureza = encontrar_indice_linha(linhas, "Natureza")
    indice_valor_global = encontrar_indice_linha(linhas, "Valor  global  da requisição:")
    indice_valor_principal = encontrar_indice_linha(linhas, "Principal/Indenização:")
    indice_valor_juros = encontrar_indice_linha(linhas, "Juros  Moratórios:")
    indice_qtd_credores  = encontrar_indice_linha(linhas, "Quantidade  de credores")
    
    indices = {'indice_estado': indice_estado,'indice_vara': indice_vara,'indice_precatorio': indice_precatorio, 'indice_conhecimento': indice_conhecimento,'indice_devedor': indice_devedor,'indice_executado': indice_executado,'indice_natureza': indice_natureza, 'indice_global': indice_valor_global, 'indice_valor_juros': indice_valor_juros,  'indice_valor_principal': indice_valor_principal, 'indice_qtd_credores': indice_qtd_credores}
    
    dados = mandar_dados_regex(indices, linhas)
    if dados['natureza'] == '':
      dados['natureza'] = 'ALIMENTAR'
    advogado, oab, seccional = regex(linhas[indice_advogado])
    documento_advogado = ''
    if indice_documento_advogado != None:
      documento_advogado = regex(linhas[indice_documento_advogado + 3])
      
    cidada_e_data_precatorio = encontrar_data_expedicao_e_cidade(arquivo_txt)
    telefone_seccional_e_nome_advogado = pegar_foto_oab(oab, seccional, documento_advogado, advogado,dados['processo'])
    dados = dados | cidada_e_data_precatorio | telefone_seccional_e_nome_advogado
    return dados

def mandar_dados_regex(indices, linhas):
  dados = {}
  for i in dict.keys(indices):
      nome = i.split('_', 1)[1]
      if indices[i] != None:
        valores = linhas[indices[i]]
        valores_regex = regex(valores)
        dados = dados | valores_regex
      else:
        if len(nome) > 1:
          dados = dados | {f'{nome}': ''}
  return dados

def extrair_informacoes_credores_e_mandar_para_banco_dados(arquivo_pdf,dados_txt ):
  i = 0 
  pdf_file = open(arquivo_pdf, 'rb')
  pdf_reader = PyPDF2.PdfReader(pdf_file)
  text = ''
  for page_num in range(len(pdf_reader.pages)):
    page = pdf_reader.pages[page_num]
    text = page.extract_text() 
    if f'Credor  nº.:' in text:
      linhas = text.split('\n')
      indice_nome = encontrar_indice_linha(linhas, 'Nome')
      indice_documento = encontrar_indice_linha(linhas, 'CPF/CNPJ')
      indice_data_nascimento = encontrar_indice_linha(linhas, 'Data  do nascimento')
      indice_valor_principal = encontrar_indice_linha(linhas, 'Valor  total  da condenação')
      indices = {'indice_nome': indice_nome, 'indice_documento': indice_documento, 'indice_data_nascimento': indice_data_nascimento}
      dados = mandar_dados_regex(indices, linhas)
      atualizar_ou_inserir_pessoa(dados['documento'], dados)
      
      if int(dados_txt['qtd_credores']) > 1:
              valor_principal_credor = regex(linhas[indice_valor_principal])
              dados['valor_principal_credor'] = valor_principal_credor['valor_principal']
              
      dados = dados | dados_txt
      print('dados arteria -->> ', dados)
      id_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
      dados = dados | id_arteria
      print('dados banco de dados -->> ', dados)
      mandar_precatorios_para_banco_de_dados(dados['codigo_processo'], dados)
      atualizar_ou_inserir_pessoa_precatorio(dados['documento'], dados['processo'])
    i = int(i) + 1
  print('-----------------------------------FIM---------------------------------')
def encontrar_indice_linha(linhas, texto):
    for indice, linha in enumerate(linhas):
      if texto in linha:
        return indice
    return None

# extrair_dados_credores('arquivos_pdf_sao_paulo/0000459-51.2023.8.26.0404_arquivo_precatorio.pdf')
ler_xml('./arquivos_xml/relatorio_27_09.xml')