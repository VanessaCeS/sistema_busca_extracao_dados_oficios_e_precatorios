import re
import PyPDF2
import traceback
from logs import log
from cna_oab import login_cna
from dotenv import load_dotenv
from funcoes_arteria import enviar_valores_oficio_arteria
from auxiliares import  encontrar_indice_linha, ler_arquivo_pdf_transformar_em_txt, mandar_dados_regex
from esaj_sao_paulo_precatorios import get_docs_oficio_precatorios_tjsp
from auxiliares import encontrar_data_expedicao_e_cidade, limpar_dados, regex, tipo_precatorio,  verificar_tribunal
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro, consultar_processos

load_dotenv('.env')

def buscar_dados_tribunal_sao_paulo():     
  dados = consultar_processos('.8.26.0053')
  for d in dados:
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        if verificar_tribunal(d['processo']) and d['processo'] != '1053116-70.2022.8.26.0053':
          ler_documentos(dado)
        else:
          continue

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
        print(doc)
        if doc:
          for codigo_processo, valores in dict.items(doc):
              try:
                file_path = valores[0][2]
                id_documento = valores[0][0]
                arquivo_pdf = f"arquivos_pdf_sao_paulo/{codigo_processo}_{id_documento}_arquivo_precatorio.pdf"
                with open(arquivo_pdf, "wb") as arquivo:
                        arquivo.write(file_path)
                arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
              
                dados_complementares = {"processo_geral": processo_geral, "codigo_processo": codigo_processo, 'site': 'https://esaj.tjac.jus.br', 'id_documento': id_documento, 'estado': 'SÃO PAULO'} | dado_xml
                extrair_dados_txt(arquivo_pdf, arquivo_txt, dados_complementares)
              except:
                continue
    except Exception as e:
        print(f"Erro no processo ---> {processo_geral}", f'Erro: {e}')
        print(traceback.print_exc())
        pass
    
def extrair_dados_txt(arquivo_pdf, arquivo_txt, dados_xml):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    

    indice_oficio_requisitorio = 7
    oficio_requisitorio = 'OFÍCIO REQUISITÓRIO' in linhas[indice_oficio_requisitorio].upper().replace('  ', ' ').strip()
    if oficio_requisitorio == False:
      oficio_requisitorio = 'OFÍCIO REQUISITÓRIO' in linhas[indice_oficio_requisitorio + 1].upper().replace('  ', ' ').strip()

    if oficio_requisitorio: 
      indice_estado = 0
      indice_vara = 3 
      indice_precatorio = encontrar_indice_linha(linhas, "processo nº: ")
      indice_conhecimento = encontrar_indice_linha(linhas, "processo principal/conhecimento:")
      indice_executado = encontrar_indice_linha(linhas, "executado(s):")
      indice_devedor = encontrar_indice_linha(linhas, "devedor:")
      indice_advogado = encontrar_indice_linha(linhas, "advogad")
      indice_documento_advogado = encontrar_indice_linha(linhas, "dados do advogado") 
      indice_natureza = encontrar_indice_linha(linhas, "natureza")
      indice_valor_global = encontrar_indice_linha(linhas, "valor global da requisição:")
      indice_valor_principal = encontrar_indice_linha(linhas, "principal/indenização:")
      indice_valor_juros = encontrar_indice_linha(linhas, "juros moratórios:")
      indice_qtd_credores  = encontrar_indice_linha(linhas, "quantidade de credores")
      
      indices = {'indice_estado': indice_estado,'indice_precatorio': indice_precatorio, 'indice_conhecimento': indice_conhecimento,'indice_devedor': indice_devedor,'indice_executado': indice_executado,'indice_natureza': indice_natureza, 'indice_global': indice_valor_global, 'indice_valor_juros': indice_valor_juros,  'indice_valor_principal': indice_valor_principal, 'indice_qtd_credores': indice_qtd_credores}
      
      dados = mandar_dados_regex(indices, linhas)
      dados_xml['vara'] = linhas[indice_vara].replace('\n', ' ')
      if dados['natureza'] == '':
        dados['natureza'] = 'ALIMENTAR'
      dados_xml['processo'] = dados['processo']
      cidada_e_data_precatorio = encontrar_data_expedicao_e_cidade(arquivo_txt)
      dados_advogado =  extrair_dados_advogado(linhas[indice_advogado], indice_documento_advogado, linhas, dados['processo'])
      dados = dados | cidada_e_data_precatorio | dados_advogado | dados_xml
      extrair_informacoes_credores_e_mandar_para_banco_dados(arquivo_pdf, dados)

def extrair_dados_advogado(texto_advogado, indice_documento_advogado, linhas, processo):

    oab =  re.search(r'\d+', texto_advogado)
    oab = oab.group().strip()
    seccional =  re.search(r'/[A-Z]+', texto_advogado)
    seccional = seccional.group().replace('/','')
    documento_advogado = ''
    if indice_documento_advogado != None:
      documento_advogado = regex(linhas[indice_documento_advogado + 3])
    else:
      dados_advogado = {'advogado': '', 'telefone': '', 'oab' : '', 'documento_advogado': '', 'seccional': ''}

    dados_advogado = login_cna(oab, seccional, documento_advogado, '',processo)
    return dados_advogado

def extrair_informacoes_credores_e_mandar_para_banco_dados(arquivo_pdf,dados_txt ):
  pdf_file = open(arquivo_pdf, 'rb')
  pdf_reader = PyPDF2.PdfReader(pdf_file)
  text = ''
  for page_num in range(len(pdf_reader.pages)):
    page = pdf_reader.pages[page_num]
    text = page.extract_text() 
    if f'Credor  nº.:' in text:
      linhas = text.split('\n')
      indice_nome = encontrar_indice_linha(linhas, 'nome')
      indice_documento = encontrar_indice_linha(linhas, 'cpf/cnpj')
      indice_data_nascimento = encontrar_indice_linha(linhas, 'data do nascimento')
      indice_valor_principal = encontrar_indice_linha(linhas, 'valor total da condenação')
      indices = {'indice_documento': indice_documento, 'indice_data_nascimento': indice_data_nascimento}
      
      dados = mandar_dados_regex(indices, linhas)
      dados['nome'] = buscar_nome_credor(linhas[indice_nome])
      documento = dados['documento']
      dados = dados | {'estado': "São Paulo", 'tipo': "credor"}
      atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, dados)
      dados['credor'] = dados.pop('nome')
      if int(dados_txt['qtd_credores']) > 1:
              valor_principal_credor = regex(linhas[indice_valor_principal])
              dados['valor_principal_credor'] = valor_principal_credor['valor_principal']
              
      dados = dados | dados_txt
      dados['id_sistema_arteria']  = enviar_valores_oficio_arteria(arquivo_pdf, dados)
      site = dados['site']
      atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
      atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])
      
      log( dados['processo'], 'Sucesso', site, 'Precatório registrado com sucesso',dados['estado'], dados['tribunal'])
      atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})

def buscar_nome_credor(string):
  if 'Nome:' in string or 'Nome(s):' in string or 'Nomes:' in string:
      padrao = r'(?:Nome\(s\)|Nome:|Nome)(.*)'
      resultado = re.search(padrao, string)
      if resultado != None:
        credor = resultado.group(1)
        return credor.strip()
      else:
        return  ''
