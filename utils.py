import json
import os
import re
import traceback
import mysql.connector
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv('.env')


def regex(string):
    if 'Vara' in string or 'VARA' in string:
      for linha in string.split('\n'):
        if re.search(r'\bvara\b', linha, re.IGNORECASE):
            return {'vara_pdf': linha}
    if 'E-mail' in string:
      padrao = r'(?<=,\s)([^\d-]+)'
      cidade = re.search(padrao, string)
      verificar_cidade_padrao = r'Fone:*'
      if cidade != None: 
        verificar_cidade = re.search(verificar_cidade_padrao, cidade.group(1))
        if verificar_cidade != None:
          output_string = re.sub(r'\d+', '', string)
          padrao = r"(?:[^,]*,){2}\s*([^\d,-]+)"
          cidade = re.search(padrao, output_string)
      return cidade.group(1)
    if 'Processo  nº:' in string:
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}/\d{2}'
      processo = re.search(padrao, string)
      if processo != None:
        return {'processo': processo.group(0)} 
      else:
        return {'processo': ''}
    if 'Processo  Principal/Conhecimento' in string:
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}/\d{2}'
      processo_principal = re.search(padrao, string)
      if processo_principal != None:
        return {'conhecimento': processo_principal.group(0)}
      else:
        return {'conhecimento': ''} 
    if 'Credor' in string:
      padrao = r"(?:Credor\(s\)|Credor\(es\)):|Credor(.*)"
      credor = re.search(padrao, string)
      if credor != None:
        return {'credor': credor.group(1)}
      else:
        return {'credor': ''}
    elif 'Exequente(s):' in string:
      padrao = r'Exequente\(s\):\s+(.*?)\n'
      exequente = re.search(padrao, string)
      if exequente != None:
        return {'credor': exequente.group(1)}
      else:
        return {'credor': ''}
    if 'Devedor' in string:
      padrao = r'Devedor:|Devedor (.*)'
      devedor = re.search(padrao, string)
      if devedor != None:
        return {'devedor': devedor.group(1)}
      else:
        return {'devedor': ''}
    elif 'Executado(s):' in string:
      padrao = r'Executado\(s\):\s+(.*?)\n'
      devedor = re.search(padrao, string)
      if devedor != None:
        return {'devedor': devedor.group(1)}
      else:
        return {'devedor': ''}
    if 'Natureza' in string:
      padrao = r'Natureza:\s+(.*?)\n'
      natureza = re.search(padrao, string)
      if natureza != None:
        natureza = natureza.group(1)
        if 'Alimentar'.upper() in natureza.upper():
          return {'natureza': 'Alimentar'.upper()}
        else:
          return {'natureza': natureza.upper()}
      else:
        return {'natureza': ''}
    if 'Valor  global  da requisição' in string:
      padrao = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b' 
      valor_global = re.search(padrao, string)
      if valor_global != None:
        return {'global': valor_global.group(0).replace('.','').replace(',','.')}
      else: 
        return {'global': ''}
    if 'Juros  Moratórios' in string:
      padrao = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b' 
      valor_juros = re.search(padrao, string)
      if valor_juros != None:
        return {'juros': valor_juros.group(0).replace('.','').replace(',','.')}
      else:
        return {'juros': ''}
    if 'Principal/Indenização' in string:
      padrao = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b'  
      valor_principal = re.search(padrao, string)
      if valor_principal != None:
        return {'principal': valor_principal.group(0).replace('.','').replace(',','.')}
      else:
        return {'principal': ''}
    if 'SUBTOTAL 1' in string:
      padrao = r'(\d{1,3}(?:\.\d{3})*(?:,\d+)?)(?=\s|$)' 
      valor_principal = re.findall(padrao, string)
      print(valor_principal)
      if valor_principal != None:
        return {'principal': valor_principal[1].replace('.', '').replace(',','.')}
      else:
        return {'principal': ''}
    if 'CPF/CNPJ' in string:
      padrao = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
      cpf_cnpj_rne = re.search(padrao, string)
      if cpf_cnpj_rne != None:
        return {'cpf': cpf_cnpj_rne.group(0)}
      else:
        return {'cpf': ''}
    if 'Data  do nascimento:' in string:
      padrao = r'\b(?:\d{1,2}\/\d{1,2}\/\d{4}|\d{4}\/\d{1,2}\/\d{1,2}|\d{1,2}\-\d{1,2}\-\d{4}|\d{4}\-\d{1,2}\-\d{1,2})\b'
      nascimento = re.search(padrao, string)
      if nascimento != None:
        dia, mes, ano = nascimento.group(0).split('/')
        data_padrao_arteria = f"{mes}/{dia}/{ano}"
        return {'nascimento': data_padrao_arteria}
      else:
        return {'nascimento': ''}
    if 'de 20' in string:
      cidade_data = encontrar_data_expedicao_e_cidade_tjac(string) 
      return cidade_data

def calcular_valor_principal(juros, valor_global):
  if juros != '' and valor_global != '':
    valor_juros = float(juros.replace(',','.'))
    valor_global = float(valor_global.replace(',','.'))
    valor_pricipal = valor_global - valor_juros
    return valor_pricipal

def encontrar_data_expedicao_e_cidade(arquivo_txt):
  with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        texto = arquivo.read()
  padrao = r'individualizado(.*)'
  resultado = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
  if resultado:
        linha = resultado.group(0)
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

def natureza_tjac(arquivo_txt):
  with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        texto = arquivo.read()
  padrao = r'D - NATUREZA DO CRÉDITO(.*)'
  resultado = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
  if resultado:
    padrao = r'\(x\)\s+(.*?)\n'
    natureza = re.search(padrao, resultado.group(0))
    if natureza!= None:
      tipo_natureza = verificar_tipo_natureza(natureza.group(0).split('( )')[0])
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
    return resultado.group(0)
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
        if tribunal == '8':
          identificar_tribunal(dado['processo'])
    return tipo
  except:
    return {'tipo_precatorio': ''}
  
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
def identificar_tribunal(processo):
  processo = processo.split('.')
  tribunais = {
    "AC": "Acre",
    "AL": "Alagoas",
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
      dado['vara'] = vara.group(1)
    elif 'vara' in dado['materia']:
      materia = dado['materia']
      padrao = r'^.*(?:[Vv]ara).*$'
      vara = re.search(padrao, materia, re.MULTILINE)
      dado['vara'] = vara.group(0)
    else:
      dado['vara'] = ''
    dado.pop('materia')

    return dado

def text_ocr(arquivo_base_64_pdf):
  url = 'http://192.168.88.205:9000/extract_text_pdf'
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
    with open('ocr_doc_8831229.txt', 'a', encoding='utf-8') as f:
      arquivo_txt = f.write(txt[i])
  return arquivo_txt

def mandar_para_banco_de_dados(id_processo, dados):
    conn = mysql.connector.connect(
    host=os.getenv('db_server_precatorio'),
    user=os.getenv('db_username_precatorio'),
    password=os.getenv('db_password_precatorio'),
    database='precatorias_tribunais'
)
    if dados['vara'] == '':
        dados['vara'] = dados['vara_pdf']
        del dados['vara_pdf']
    else:
        del dados['vara_pdf']

    if dados['credor'] == '':
        dados['credor'] = dados['exequente']
        del dados['exequente']
    else:
      del dados['exequente']

    if dados['devedor'] == '':
        dados['devedor'] = dados['executado']
        del dados['executado']
    else:
        del dados['executado']
      
    dados['cpf_cnpj'] = dados['cpf']
    del dados['cpf'] 

    if dados['conhecimento'] == '':
            del dados['conhecimento']
    else: 
        dados['processo'] = dados['conhecimento']
        del dados['conhecimento']
    dados['processo'] = dados['processo'].split('/')[0]

    dados['nascimento'] = converter_data(dados['nascimento'])
    dados['data_expedicao'] = converter_data(dados['data_expedicao'])

    cursor = conn.cursor()

    query_consultar_processo = 'SELECT * FROM dados_xml_pdf WHERE processo = %s'
    cursor.execute(query_consultar_processo, (id_processo,))
    id_processo = cursor.fetchone()
    if id_processo is not None:
      try:
                dados_processados = processar_dado(dados)
                colunas_e_valores = ', '.join([f"{coluna} = %s" for coluna in dados_processados.keys()])
                query = f"UPDATE dados_xml_pdf SET {colunas_e_valores} WHERE processo = %s"
                valores = tuple(list(dados_processados.values()) + [dados_processados['processo']])
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

def converter_string_mes(string):
  try:
    string = string.split('\n')[0]
    nome_mes = string.split('de ', 2)
    dict_meses = {'janeiro': '01',
      'fevereiro': '02',
      'março': '03',
      'abril': '04',
      'maior': '05',
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
        print(dict_meses[m])
        mes_numero = string.replace(nome_mes[1], dict_meses[m]).replace('de', '-').replace('.', '').replace(' ', '').strip()
        dia, mes, ano = mes_numero.split('-')
        data_padrao_arteria = f"{mes}/{dia}/{ano}"
        return data_padrao_arteria
  except:
    return ''

def tipo_natureza(natureza):
  if 'Alimentar - ' in natureza:
    return 'ALIMENTAR'
  elif 'Outras  espécies  - Não alimentar' in natureza:
    return 'COMUM - NÃO TRIBUTARIO'
  else:
    natureza
