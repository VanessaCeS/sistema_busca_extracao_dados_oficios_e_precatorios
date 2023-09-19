import os
import re
import json
import base64
import requests
import traceback
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
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

  data = datetime.utcnow()
  with open(f'arquivos_xml/dados_processos_{data.day}_{data.month}.xml', 'w', encoding='utf-8') as arq:
    arquivo = arq.write(response.content)
  return arquivo

def regex(string):
    if 'Advogad' in string:
      padrao = r'Advogados\(s\):(.*)'
      resultado = re.search(padrao, string)
      if resultado != None:
        resultado = resultado.group(1).split('OAB')
        oab = resultado[1].split('/')[0].replace(':','').strip()
        seccional = resultado[1].split('/')[1].strip()
        advogado = resultado[0]
        return {'advogado': advogado.strip(), 'oab': oab, 'seccional': seccional}
      else:
        return {'advogado': '', 'oab': '', 'seccional': ''}
    if 'Nome:' in string or 'Nome(s):' in string or 'Nomes:' in string:
      padrao = r'(?:Nome\(s\)|Nome:|Nome)(.*)'
      resultado = re.search(padrao, string)
      if resultado != None:
        advogado = resultado.group(1)
        return {'advogado': advogado.strip()}
      else:
        return {'advogado': ''}
    if 'OAB:' in string:
      padrao = r'OAB:(.*)'
      resultado = re.search(padrao, string)
      if resultado != None:
        resultado = resultado.group(0).strip()
        oab = resultado.split(':')[1].replace('/','').replace('CPF','').strip()
        return {'oab': oab.strip()}
      else:
        return {'oab': ''}
    if 'Para conferir o original' in string:
      padrao = r'\d{2}/\d{2}/\d{4}'
      resultado = re.findall(padrao, string)
      if resultado != None:
        dia, mes, ano = resultado[0].strip().split('/')
        data_padrao_arteria = f"{mes}/{dia}/{ano}"
        return {'expedicao': data_padrao_arteria}
      else:
        return {'expedicao': ''}   
    if 'TRIBUNAL' in string.upper():
      padrao = r'(?:  DO ESTADO  DE|  DO ESTADO  DO)(.*)'
      estado = re.search(padrao, string, re.IGNORECASE)
      if estado!= None:
        return {'estado': estado.group(1).replace('  ', ' ').strip()}
      else:
        return {'estado': ''}
    if 'VARA' in string.upper():
      for linha in string.split('\n'):
        if 'Origem/Foro  Comarca/  Vara:' in linha:
          padrao = r':(.*)'
          resultado = re.search(padrao, linha)
          if resultado != None:
            vara = resultado.group(1).split('/')[0]
            return {'vara': vara.strip()}
          else:
            return {'vara': ''}
        if re.search(r'\bvara\b', linha, re.IGNORECASE):
            return {'vara_pdf': linha.strip()}
    if 'E-mail' in string:
      padrao = r'(?<=,\s)([^\d-]+)'
      cidade = re.search(padrao, string)
      verificar_cidade_padrao = r'Fone:*'
      if cidade != None: 
        verificar_cidade = re.search(verificar_cidade_padrao, cidade.group(1).strip())
        if verificar_cidade != None:
          output_string = re.sub(r'\d+', '', string)
          padrao = r"(?:[^,]*,){2}\s*([^\d,-]+)"
          cidade = re.search(padrao, output_string)
      return cidade.group(1).strip()
    if 'Processo  nº:' in string :
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}/\d{2}'
      processo = re.search(padrao, string)
      if processo != None:
        return {'processo': processo.group(0).strip()} 
      else:
        return {'processo': ''}
    elif 'Número  do processo' in string :
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}'
      processo = re.search(padrao, string)
      if processo != None:
        return {'processo': processo.group(0).strip()} 
      else:
        return {'processo': ''}
    if 'Principal/Conhecimento' in string :
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}'
      processo_principal = re.search(padrao, string)
      if processo_principal != None:
        return {'conhecimento': processo_principal.group(0).strip()}
      else:
        return {'conhecimento': ''} 
    if 'Autos  da Ação' in string:
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}'
      processo_principal = re.search(padrao, string, re.MULTILINE)
      if processo_principal != None:
        return {'conhecimento': processo_principal.group(0).strip()}
      else:
        return {'conhecimento': ''} 
    if 'Credor' in string:
      padrao = r"(?:Credor\(s\)|Credor|Credor\(es\)):(.*)"
      credor = re.search(padrao, string)
      if credor != None:
        return {'credor': credor.group(1).strip()}
      else:
        return {'credor': ''}
    elif 'Exequente(s):' in string:
      padrao = r'Exequente\(s\):\s+(.*?)\n'
      exequente = re.search(padrao, string)
      if exequente != None:
        return {'credor': exequente.group(1).strip()}
      else:
        return {'credor': ''}
    elif 'Requerente' in string:
      padrao = r'Requerente:\s+(.*?)\n'
      requerente = re.search(padrao, string)
      if requerente!= None:
        return {'credor': requerente.group(1).strip()}
      else:
        return {'credor': ''}
    if 'Devedor' in string:
      padrao = r'(?:Devedor|Devedor:|Devedor\(s\)|Devedor\(es\)) (.*)'
      devedor = re.search(padrao, string)
      if devedor != None:
        return {'devedor': devedor.group(1).strip().replace('  ', ' ')}
      else:
        return {'devedor': ''}
    elif 'Executado(s):' in string:
      padrao = r'Executado\(s\):\s+(.*?)\n'
      devedor = re.search(padrao, string)
      if devedor != None:
        return {'devedor': devedor.group(1).strip()}
      else:
        return {'devedor': ''}
    elif 'Requerido' in string:
      padrao = r'Requerido:\s+(.*?)\n'
      requerido = re.search(padrao, string)
      if requerido!= None:
        return {'devedor': requerido.group(1).strip()}
      else:
        return {'devedor': ''}
    if 'Natureza  do Crédito' in string:
      padrao = r'Natureza  do Crédito:\s+(.*?)\n'
      natureza = re.search(padrao, string)
      if natureza != None:
        return{'natureza': natureza.group(1).strip()}
      else:
        return{'natureza': ''}
    elif 'Natureza' in string:
      padrao = r'Natureza:\s+(.*?)\n'
      natureza = re.search(padrao, string)
      if natureza != None:
        tipos_alimentar = ['Alimentar  - Benefícios  previdenciários  e indenizações,  por morte  ou invalidez', ' Alimentar  - Salários,  vencimentos,  proventos  e pensões']
        natureza = natureza.group(1).strip()
        if natureza in tipos_alimentar:
          return {'natureza': 'ALIMENTAR'.upper()}
        elif 'Outras  espécies  - Não alimentar'.upper() == natureza.upper():
          return {'natureza': 'COMUM - NÃO TRIBUTARIO'.upper()}
        else:
          return {'natureza': ''}
      else:
        return {'natureza': ''}
    if 'Valor  global  da requisição' in string or "Valor  total da requisição" in string:
      padrao = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b' 
      valor_global = re.search(padrao, string)
      if valor_global != None:
        return {'global': valor_global.group(0).strip().replace('.','').replace(',','.')}
      else: 
        return {'global': ''}
    if 'JUROS  MORATÓRIOS' in string.upper():
      padrao = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b' 
      valor_juros = re.search(padrao, string)
      if valor_juros != None:
        return {'juros': valor_juros.group(0).strip().replace('.','').replace(',','.')}
      else:
        return {'juros': ''}
    if 'Principal/Indenização' in string or "Valor  originário" in string:
      padrao = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b'  
      valor_principal = re.search(padrao, string)
      if valor_principal != None:
        return {'principal': valor_principal.group(0).strip().replace('.','').replace(',','.')}
      else:
        return {'principal': ''}
    
    if 'SUBTOTAL 1' in string:
      padrao = r'(\d{1,3}(?:\.\d{3})*(?:,\d+)?)(?=\s|$)' 
      valor_principal = re.findall(padrao, string)
      if valor_principal != None:
        return {'principal': valor_principal[1].replace('.', '').replace(',','.')}
      else:
        return {'principal': ''}
    if 'CPF/CNPJ' in string or 'CPF' in string:
      padrao = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
      cpf_cnpj_rne = re.search(padrao, string)
      if cpf_cnpj_rne != None:
        return {'cpf': cpf_cnpj_rne.group(0).strip()}
      else:
        return {'cpf': ''}
    if 'Data  do nascimento:' in string or 'Data  de nascimento':
      padrao = r'\b(?:\d{1,2}\/\d{1,2}\/\d{4}|\d{4}\/\d{1,2}\/\d{1,2}|\d{1,2}\-\d{1,2}\-\d{4}|\d{4}\-\d{1,2}\-\d{1,2})\b'
      nascimento = re.search(padrao, string)
      if nascimento != None:
        dia, mes, ano = nascimento.group(0).strip().split('/')
        data_padrao_arteria = f"{mes}/{dia}/{ano}"
        return {'nascimento': data_padrao_arteria}
      else:
        return {'nascimento': ''}
    elif 'DATA DE NASCIMENTO' in string:
      padrao = r'\b(?:\d{1,2}\/\d{1,2}\/\d{4}|\d{4}\/\d{1,2}\/\d{1,2}|\d{1,2}\-\d{1,2}\-\d{4}|\d{4}\-\d{1,2}\-\d{1,2})\b'
      nascimento = re.search(padrao, string, re.IGNORECASE)
      if nascimento != None:
        dia, mes, ano = nascimento.group(0).strip().split('/')
        data_padrao_arteria = f"{mes}/{dia}/{ano}"
        return {'nascimento': data_padrao_arteria}
      else:
        return {'nascimento': ''}
    if 'de 20' in string: 
      cidade_data = encontrar_data_expedicao_e_cidade_tjac(string) 
      return cidade_data
    

def encontrar_data_expedicao_e_cidade_tjac(string):
  partes = string.split(',')
  estado = ''
  if len(partes) > 1:
    cidade = partes[0].strip()
    if '(' in cidade:
      estado = cidade.split('(')[1]
      estado = estado.replace(')', '')
      estado = identificar_estados(estado)
      cidade = cidade.split('(')[0].strip()
    if '/' in cidade:
      estado = cidade.split('/')[1]
      estado = identificar_estados(estado)
      cidade = cidade.split('/')[0].strip()
    data_expedicao = partes[1].strip()
    data_expedicao_tratada = converter_string_mes(data_expedicao)
    dados = {'cidade': cidade, 'data_expedicao': data_expedicao_tratada} | estado
    return dados
  else:
          return {'cidade': '', 'data_expedicao': ''}
  
def identificar_estados(estado):
  estados_brasileiros = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins"
    }
  for e in dict.keys(estados_brasileiros):
    if e == estado.strip():
      return {'estado': f'{estados_brasileiros[e]}'} 
    else:
      {'estado': ''}

def encontrar_data_expedicao_e_cidade(arquivo_txt):
  with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        texto = arquivo.read()
  padrao = r'individualizado(.*)'
  resultado = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
  if resultado:
        linha = resultado.group(0).strip()
        partes = linha.split(',', 1)
        if len(partes) > 1:
            cidade = partes[0].split('\n')[1].strip()
            data_expedicao = partes[1].strip()
            data_expedicao_tratada = converter_string_mes(data_expedicao)
            dados = {'cidade': cidade, 'data_expedicao': data_expedicao_tratada}
            return dados
        else:
          return {'cidade': '', 'data_expedicao': ''}
  else:
        return {'cidade': '', 'data_expedicao': ''}

def converter_string_mes(string):
  try:
    string = string.split('\n')[0]
    nome_mes = string.split('de ', 2)
    dict_meses = {'janeiro': '01',
      'fevereiro': '02',
      'março': '03',
      'abril': '04',
      'maio': '05',
      'junho': '06',
      'julho': '07',
      'agosto': '08',
      'setembro': '09',
      'outubro': '10',
      'novembro': '11',
      'dezembro': '12'
    }
    for m in dict.keys(dict_meses):
      if m in nome_mes[1]:
        mes_numero = string.replace(nome_mes[1], dict_meses[m]).replace('de', '-').replace('.', '').replace(' ', '').strip()
        dia, mes, ano = mes_numero.split('-')
        data_padrao_arteria = f"{mes}/{dia}/{ano}"
        return data_padrao_arteria
  except:
    return ''
  
def natureza_tjac(arquivo_txt):
  with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        texto = arquivo.read()
  padrao = r'D - NATUREZA DO CRÉDITO(.*)'
  resultado = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
  if resultado:
    padrao = r'\(x\)\s+(.*?)\n'
    natureza = re.search(padrao, resultado.group(0).strip())
    if natureza!= None:
      tipo_natureza = verificar_tipo_natureza(natureza.group(0).strip().split('( )')[0])
      return {'natureza': tipo_natureza}
    else:
      {'natureza': ''}
  else:
    {'natureza': ''}

def verificar_tipo_natureza(natureza):
  alimentar = ['Benefícios', 'Indenizações', 'Salários']
  for i in alimentar:
    if i in natureza:
      tipo = 'ALIMENTAR'
    else:
      tipo = 'COMUM - NÃO TRIBUTARIO'
  return tipo

def extrair_processo_origem(processo):
  padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}/\d{2,4}'
  resultado = re.search(padrao, processo)
  if resultado != None:
    return resultado.group(0).strip()
  else:
    return None

def tipo_precatorio(dado):
  try:
    processo = dado['processo'].split('.')
    dict_tribunais = {
        '1': 'FEDERAL',
        '2': 'FEDERAL',
        '3': 'FEDERAL',
        '4': 'FEDERAL',
        '5': 'FEDERAL',
        '6': 'FEDERAL',
        '7': 'FEDERAL',
        '8': 'ESTADUAL',
        '9': 'ESTADUAL',
      }

    for tribunal in dict.keys(dict_tribunais):
      if tribunal == processo[2]:
        tipo = {'tipo_precatorio': dict_tribunais[tribunal].upper()}
    return tipo
  except:
    return {'tipo_precatorio': ''}
  

def identificar_tribunal(processo):
  processo = processo.split('.')
  tribunais = {
    "1": "Acre",
    "2": "Alagoas",
    "3": "Amapá",
    "4": "Amazonas",
    "5": "Bahia",
    "6": "Ceará",
    "7": "Distrito Federal",
    "8": "Espírito Santo",
    "9": "Goiás",
    "10": "Maranhão",
    "11": "Mato Grosso",
    "12": "Mato Grosso do Sul",
    "13": "Minas Gerais",
    "14": "Pará",
    "15": "Paraíba",
    "16": "Paraná",
    "17": "Pernambuco",
    "18": "Piauí",
    "19": "Rio de Janeiro",
    "20": "Rio Grande do Norte",
    "21": "Rio Grande do Sul",
    "22": "Rondônia",
    "23": "Roraima",
    "24": "Santa Catarina",
    "25": "Sergipe",
    "26": "São Paulo",
    "27": "Tocantins"
}
  for t in dict.keys(tribunais):
    if t == processo[3]:
      return {'estado': f'{tribunais[t].upper()}'} 
    else:
      {'estado': ''}
  
def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.8.26.\d{4}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True
        
def limpar_dados(dado):
    if dado['tribunal'] == 'STFSITE':
      dado['vara'] = 'STF'
      dado['tribunal'] = 'STF'
    elif dado['tribunal'] == 'STJ':
      dado['vara'] = 'STJ'
    elif 'Orgão' in dado['materia']:
      materia = dado['materia']
      padrao = r"Orgão: (.*)"
      vara = re.search(padrao, materia)
      dado['vara'] = vara.group(1).strip()
    elif 'vara' in dado['materia']:
      materia = dado['materia']
      padrao = r'^.*(?:[Vv]ara).*$'
      vara = re.search(padrao, materia, re.MULTILINE)
      dado['vara'] = vara.group(0).strip()
    else:
      dado['vara'] = ''
    dado.pop('materia')

    return dado

def mandar_documento_para_ocr(arquivo):
  arquivo_base_64 = converter_arquivo_base_64(arquivo)
  text_ocr(arquivo_base_64)

def converter_arquivo_base_64(nome_arquivo):
  with open(nome_arquivo, "rb") as arquivo:
            dados = arquivo.read()
            dados_base64 = base64.b64encode(dados)
            return dados_base64.decode("utf-8") 
  
def text_ocr(arquivo_base_64_pdf):
  url = 'http://192.168.88.205:9000/google_ocr'
  headers = {
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'api-key': '8cb99ca8-9e55-11ed-a8fc-0242ac120002'
  }
  json_data = {
    'pdf': f"{arquivo_base_64_pdf}"
  }
  response = requests.post(url, headers=headers, json=json_data).json()
  txt = json.loads(response['pdf_text'])
  for i in range(len(txt)):
    with open(f'_ocr.txt', 'a', encoding='utf-8') as f:
      arquivo_txt = f.write(txt[i])
  return arquivo_txt

def mandar_para_banco_de_dados(codigo_processo, dados):
    conn = mysql.connector.connect(
    host=os.getenv('db_server_precatorio'),
    user=os.getenv('db_username_precatorio'),
    password=os.getenv('db_password_precatorio'),
    database='precatorias_tribunais'
    )

    dados = dados_limpos_banco_de_dados(dados)
    cursor = conn.cursor()
    query_consultar_codigo_processo = 'SELECT * FROM dados_xml_pdf WHERE codigo_processo = %s'
    cursor.execute(query_consultar_codigo_processo, (codigo_processo,))
    codigo_processo = cursor.fetchone()
    if codigo_processo is not None:
      try:
                dados_processados = processar_dado(dados)
                colunas_e_valores = ', '.join([f"{coluna} = %s" for coluna in dados_processados.keys()])
                query = f"UPDATE dados_xml_pdf SET {colunas_e_valores} WHERE codigo_processo = %s"
                valores = tuple(list(dados_processados.values()) + [dados_processados['codigo_processo']])
                cursor.execute(query, valores)
                conn.commit()
                conn.close()
      except Exception as e:
                print("E ==>> ", e)
                print("Exec ==>> ", traceback.print_exc())
    else:
      try:
        dado_processado = {key: (value if value != '' else None) for key, value in dados.items()}
        colunas = ', '.join(dado_processado.keys())
        valores = ', '.join(['%s'] * len(dado_processado))
        query = f"INSERT INTO dados_xml_pdf ({colunas}) VALUES ({valores})"
        valores_insercao = tuple(dado_processado.values())
        cursor.execute(query, valores_insercao)
        conn.commit()
        cursor.close()
        conn.close()
      except Exception as e:
                print("E ==>> ", e)
                print("Exec ==>> ", traceback.print_exc())

def dados_limpos_banco_de_dados(dados):
  dados['processo'] = dados['processo'].split('/')[0]
  dados['nascimento'] = converter_data(dados['nascimento'])

  if 'data_expedicao' not in dict.keys(dados):  
    dados['data_expedicao'] = converter_data(dados['expedicao'])
    del dados['expedicao']
  else:
    dados['data_expedicao'] = converter_data(dados['data_expedicao'])

  if 'conhecimento' in dict.keys(dados):  
    if dados['conhecimento'] == '':
      del dados['conhecimento']
    else:
      dados['processo'] = dados['conhecimento']
      del dados['conhecimento']
  
  return dados
        
def converter_data(data):
  data = data.replace('/','-')
  date_object = datetime.strptime(data, '%m-%d-%Y')
  data_padrao_bd = date_object.strftime('%Y-%m-%d')
  return data_padrao_bd

def processar_dado(dado):
    dado_processado = {}
    for key, value in dado.items():
        dado_processado[key] = value if value != '' else None
    return dado_processado

def tipo_natureza(natureza):
  if 'Alimentar - ' in natureza:
    return 'ALIMENTAR'
  elif 'Outras  espécies  - Não alimentar' in natureza:
    return 'COMUM - NÃO TRIBUTARIO'
  else:
    natureza

def buscar_cpf(arquivo_txt):
      with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        texto = arquivo.read()
      padrao = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
      cpf_cnpj_rne = re.search(padrao, texto)
      if cpf_cnpj_rne != None:
        return {'cpf_cnpj': cpf_cnpj_rne.group(0)}
      else:
        return {'cpf_cnpj': ''}

def encontrar_indice_linha(linhas, texto):
  for indice, linha in enumerate(linhas):
    if texto in linha:
        return indice
  return None

def apagar_arquivos_txt(pasta):
    arquivos = os.listdir(pasta) 
    for arquivo in arquivos:
        caminho_arquivo = os.path.join(pasta, arquivo)
        if os.path.isfile(caminho_arquivo):  
            os.remove(caminho_arquivo)

def selecionar_seccional(estado):
  seccionais_oab = {
    "AC": "Conselho Seccional - Acre",
    "AL": "Conselho Seccional - Alagoas",
    "AM": "Conselho Seccional - Amazonas",
    "AP": "Conselho Seccional - Amapá",
    "BA": "Conselho Seccional - Bahia",
    "CE": "Conselho Seccional - Ceará",
    "DF": "Conselho Seccional - Distrito Federal",
    "ES": "Conselho Seccional - Espírito Santo",
    "GO": "Conselho Seccional - Goiás",
    "MA": "Conselho Seccional - Maranhão",
    "MG": "Conselho Seccional - Minas Gerais",
    "MS": "Conselho Seccional - Mato Grosso do Sul",
    "MT": "Conselho Seccional - Mato Grosso",
    "PA": "Conselho Seccional - Pará",
    "PB": "Conselho Seccional - Paraíba",
    "PE": "Conselho Seccional - Pernambuco",
    "PI": "Conselho Seccional - Piauí",
    "PR": "Conselho Seccional - Paraná",
    "RJ": "Conselho Seccional - Rio de Janeiro",
    "RN": "Conselho Seccional - Rio Grande do Norte",
    "RO": "Conselho Seccional - Rondônia",
    "RR": "Conselho Seccional - Roraima",
    "RS": "Conselho Seccional - Rio Grande do Sul",
    "SC": "Conselho Seccional - Santa Catarina",
    "SE": "Conselho Seccional - Sergipe",
    "SP": "Conselho Seccional - São Paulo",
    "TO": "Conselho Seccional - Tocantins"
}
  
  seccional = ''
  for e in dict.keys(seccionais_oab):
    if e == estado.strip().upper():
      seccional = seccionais_oab[e]
  return seccional
    