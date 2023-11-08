import os
import re
import PyPDF2
import traceback
from logs import log
from cna_oab import login_cna
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_amazonas_precatorios import get_docs_oficio_precatorios_tjam
from auxiliares import  encontrar_indice_linha, limpar_dados, mandar_dados_regex, mandar_documento_para_ocr, regex, tipo_precatorio
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro, consultar_processos

def buscar_dados_tribunal_amazonas():   
  dados = consultar_processos('.8.04')

  for d in dados:
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        if verificar_tribunal(d['processo']) and d['processo_origem'] != '':
          ler_documentos(dado)
        else:
          pass
  
  
def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.8.04.\d{4}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True

def ler_documentos(dado_xml):
      try:
        processo_geral = dado_xml['processo_origem']
        doc = get_docs_oficio_precatorios_tjam(dado_xml['processo_origem'],zip_file=False, pdf=True)
        if doc:
          codigo_processo = next(iter(doc))
          arquivo_pdf = f"arquivos_pdf_amazonas/{processo_geral}_arquivo_precatorio.pdf"
          tamanho = len(doc[codigo_processo])
          oq = doc[codigo_processo]
          for i in range(len(doc[codigo_processo])):
              arquivo_pdf = f"arquivos_pdf_amazonas/{processo_geral}_{i + 1}_arquivo_precatorio.pdf"
              file_path = doc[codigo_processo][i][2]
              id_documento = doc[codigo_processo][0][0]
              dados_complementares = {
                  'id_documento': id_documento,
                  "processo_geral": processo_geral,             
                  'codigo_processo':codigo_processo,'site':'https://consultasaj.tjam.jus.br/', 
                  'tipo':  'MUNICIPAL', 'estado': 'AMAZONAS', 'cidade': 'Manaus'} | dado_xml
              pdf_precatorio = verificar_pdf(file_path, arquivo_pdf)
              if pdf_precatorio:
                  extrair_dados_pdf(arquivo_pdf, dados_complementares, f"arquivos_txt_amazonas/{processo_geral}_{i + 1}_texto_ocr.txt")
      except Exception as e:
        print(f"Erro! Processo -> {processo_geral}", e)
        print(traceback.print_exc())
        pass

def verificar_pdf(file_path, arquivo_pdf):
  encontrado = False
  with open(arquivo_pdf, "wb") as arquivo:
    arquivo.write(file_path)
  pdf_file = open(arquivo_pdf, 'rb')
  pdf_reader = PyPDF2.PdfReader(pdf_file)
  if len(pdf_reader.pages) > 1:
    for page_num in range(len(pdf_reader.pages)): 
        page = pdf_reader.pages[page_num]
        texto_extraido = page.extract_text()
        if 'REQUISIÇÃO  DE PRECATÓRIO' in texto_extraido or 'ofício  precatório' in texto_extraido:
          encontrado = True
          break
    if encontrado:
      nome = arquivo_pdf.split('/')[1].split('_arquivo')[0]
      arquivo_txt = mandar_documento_para_ocr(arquivo_pdf, '1', nome, 'arquivos_txt_amazonas')
      with open(arquivo_txt, "w", encoding='utf-8') as arquivo:
        text = ''
        for page_num in range(len(pdf_reader.pages)): 
          page = pdf_reader.pages[page_num]
          text += page.extract_text()
        arquivo.write(text)
        return True
    else:
      pdf_file.close()
      os.remove(arquivo_pdf)
      return False
  else:
    return False
    
def extrair_dados_pdf(arquivo_pdf, dados_xml, arquivo_txt):
    dados = {}
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()
    
    indice_procurador = encontrar_indice_linha(linhas, 'procurador do beneficiário oab') 
    indice_advogado = encontrar_indice_linha(linhas, 'de honorários') 
    indice_vara = encontrar_indice_linha(linhas, " vara ")
    indice_juizado = encontrar_indice_linha(linhas, "juizado")
    indice_valor_global = encontrar_indice_linha(linhas, "r$")
    indice_data_expedicao = encontrar_indice_linha(linhas, "liberado nos autos")
    indice_beneficiario = encontrar_indice_linha(linhas, "beneficiário cpf")
    indice_credor = encontrar_indice_linha(linhas, "credor") 
    indice_devedor = encontrar_indice_linha(linhas, "devedor") + 1
    indice_data_nascimento = encontrar_indice_linha(linhas, "nascimento")
    indice_valor_juros = encontrar_indice_linha(linhas,"dos juros")
    indice_cidade = encontrar_indice_linha(linhas, 'fone:')
    if indice_vara == None:
      indice_vara = indice_juizado 
    indices = {'indice_vara': indice_vara,
              'indice_cidade':indice_cidade,
              'indice_valor_global': indice_valor_global,
              'indice_data_expedicao': indice_data_expedicao, 
              'indice_data_nascimento': indice_data_nascimento}
    
    dados_regex = mandar_dados_regex(indices, linhas)
    
    natureza = cortar_natureza(arquivo_txt)
    dados_advogado = mandar_dados_advogado(linhas, dados_xml['processo_geral'], indice_procurador, indice_advogado)
    devedor = extrair_dados_devedor(linhas[indice_devedor])
    if devedor == '' or devedor == ' ':
      devedor = extrair_dados_devedor(linhas[indice_devedor - 1])
    dados_regex['devedor'] = devedor

    if indice_beneficiario != None:
      indice_credor = indice_beneficiario + 1
    if 'CREDOR' in linhas[indice_credor].upper():
      credor = indice_credor + 1
    else:
      credor = indice_credor
    credor_e_documento = extrair_credor_e_documento(linhas[credor])

    if indice_valor_juros != None:
      juros = linhas[indice_valor_juros + 2]
      if 'R$' in juros:
        valor_juros = indice_valor_juros + 2
      else:
        valor_juros = indice_valor_juros + 1
    valor_principal_e_juros = extrair_valor_principal_e_juros(linhas[valor_juros])

    if dados_regex['valor_global'] == '':
      dados_regex['valor_global'] = linhas[indice_valor_global + 2].replace('\n', '').replace('.','').replace(',','.').replace('(','').replace(')', '').strip()
    if 'data_nascimento' not in dados_regex:
      dados_regex['data_nascimento'] = ''
    if credor_e_documento['valor_principal'] != '':
      dados_regex['valor_principal'] = credor_e_documento['valor_principal']
    else:
      dados_regex['valor_principal'] = valor_principal_e_juros['valor_principal']
    
    dados =  dados_xml | credor_e_documento | valor_principal_e_juros | dados_advogado | natureza | dados_regex
    enviar_dados(arquivo_pdf, dados)

def cortar_natureza(nome_arquivo):
        with open(nome_arquivo, 'r', encoding='utf-8') as arquivo:
            linhas = arquivo.readlines()
            encontrou_inicio = False
            texto_cortado = []
            for linha in linhas:
                if "ALIMENTAR" in linha:
                    encontrou_inicio = True
                    texto_cortado.append(linha)
                if encontrou_inicio:
                    texto_cortado.append(linha)
                if "Residencial  do Credor  (Art. 78, § 3º, ADCT)" in linha or 'Residencial  do Credor  (Art.  78, § 3º, ADCT)' in linha:
                    encontrou_inicio = False
                    break
            texto = '\n'.join(texto_cortado)
            with open('arquivos_txt_amazonas/arquivo_advogado.txt', 'w', encoding='utf-8') as f:
              f.write(texto)
        with open('arquivos_txt_amazonas/arquivo_advogado.txt', 'r', encoding='utf-8') as r:
            linhas_natureza = r.readlines()
        indice_natureza = encontrar_indice_linha(linhas_natureza, 'x')
        natureza = regex(linhas_natureza[indice_natureza])
        if natureza == None:
          return {'natureza': ''}
        return natureza

def mandar_dados_advogado(linhas, processo_geral,indice_procurador, indice_advogado):
    if indice_procurador != None:
      dados_advogado = extrair_dados_advogado(linhas[indice_procurador + 1],processo_geral)
    elif indice_advogado != None:
      dados_advogado = extrair_dados_advogado(linhas[indice_advogado + 1],processo_geral)
    elif indice_advogado == None and indice_procurador == None:
      dados_advogado = {'advogado': '', 'telefone': '', 'oab' : '', 'documento_advogado': '', 'seccional': ''}
    return dados_advogado

def extrair_dados_devedor(string):
  padrao = r'(?:Devedor|Devedor:|Devedor\(s\)|Devedor\(es\)|devedor): (.*)'
  resultado_nome = re.search(padrao,string)
  if resultado_nome:
    nome = resultado_nome.group(1).replace('.','').replace('-','').replace('/','')
    if nome.isnumeric():
      return ''
    else:
      padrao_documento = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
      resultado_padrao = re.search(padrao_documento, resultado_nome.group(1))
      if resultado_padrao != None:
        devedor = resultado_nome.group(1).split(f'{resultado_padrao.group(0)}')[0]
        return devedor
      else:
        devedor = resultado_nome.group(1)
        return devedor
  else:
    return ''
  
def extrair_credor_e_documento(string):
  nome,documento, valor = '', '',''
  padrao_documento = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
  resultado_documento = re.search(padrao_documento, string)
  padrao_nome = r'[A-Za-zÀ-ÖØ-öø-ÿ, &]+'
  resultado_nome = re.search(padrao_nome, string)

  if resultado_nome:
    nome = resultado_nome.group(0)
  if resultado_documento:
    documento = resultado_documento.group(0)
    string = string.replace(f'{documento}', '')
  
  padrao_valor = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b'  
  resultado_valor = re.search(padrao_valor, string)
  
  if resultado_valor:
    valor = resultado_valor.group(0)
    if valor in documento:
      valor = ''
  ''.isalpha
  return {'credor': nome, 'documento': documento, 'valor_principal': valor.strip().replace('.','').replace(',','.')} 

def extrair_dados_advogado(texto, processo):
  advogado, oab, documento_advogado = '', '',''
  padrao_advogado = r'[A-Za-zÀ-ÖØ-öø-ÿ, &]+'
  resultado_advogado = re.search(padrao_advogado, texto)
  padrao_oab = r'\b(\d+\.\d+)\b'
  resultado_oab = re.search(padrao_oab, texto)
  padrao_documento_advogado = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
  resultado_documento_advogado = re.search(padrao_documento_advogado, texto)
  if resultado_advogado:
      advogado = resultado_advogado.group(0)
      if 'OAB' in advogado.upper():
        advogado = advogado.replace('OAB', '').strip()
  if resultado_documento_advogado:
      documento_advogado = resultado_documento_advogado.group(0)
      string = string.replace(f'{documento_advogado}', '')
  if resultado_oab:
    oab = resultado_oab.group(0)
  
  dados_advogado = login_cna(oab, 'AM', documento_advogado, advogado, processo)
  return dados_advogado


def pegar_cidade(texto, indice):
    for i in dict.keys(indice):
      if indice[i] != None:
        cidade = texto[indice[i]].replace('\n', '').replace(',', '').replace('.', '').strip()
        return {'cidade': cidade}
      else:
          return {'cidade': ''}

def extrair_valor_principal_e_juros(texto):
  if 'R$' in texto:
    valores = texto.replace('R$','').replace('\n','').strip().split(' ')
    valores = [i for i in valores if i and '%' not in i and not i.isalpha()]
    if valores != []:
      valor_principal = valores[0]
      valor_juros = valores[1]
      return {'valor_principal': valor_principal.strip().replace('.','').replace(',','.'), 'valor_juros': valor_juros.strip().replace('.','').replace(',','.')}
    else:
      return {'valor_principal': '', 'valor_juros': ''}
  else:
      return {'valor_principal': '', 'valor_juros': ''}  
  
def enviar_dados(arquivo_pdf, dados):
  documento = dados['documento']
  dados_pessoas = {'nome': dados['credor'], 'documento':  documento,'data_nascimento': dados['data_nascimento'], 'estado': 'Amazonas', 'tipo': 'credor'}
  atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, dados_pessoas)
  id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
  dados['id_sistema_arteria'] = id_sistema_arteria
  atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
  atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])
  log( dados['processo_origem'], 'Sucesso',dados['site'], 'Precatório registrado com sucesso','Amazonas', dados['tribunal'])
  atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})