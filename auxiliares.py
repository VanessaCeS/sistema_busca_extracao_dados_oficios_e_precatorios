import os
import re
import base64
from PyPDF2 import PdfReader
import requests
from datetime import datetime
from dotenv import load_dotenv
import fitz 
from PIL import Image
load_dotenv('.env')

tipos_alimentar = os.getenv('tipos_alimentar')
tipos_comum = os.getenv('tipos_comum')

def regex(string):
    string = string.upper().replace('  ', ' ')
    if 'PARA CONFERIR O ORIGINAL' in string or 'LIBERADO NOS AUTOS' in string or 'LIBERADO NOS AUTOS DIGITAIS' in string or 'DATA:' in string:
      padrao = r'\d{2}/\d{2}/\d{4}'
      resultado = re.findall(padrao, string)
      if resultado != []:
        dia, mes, ano = resultado[0].strip().split('/')
        data_padrao_arteria = f"{mes}/{dia}/{ano}"
        return {'data_expedicao': data_padrao_arteria}
      else:
        return {'data_expedicao': ''}   
    if 'ADVOGAD' in string :
      padrao = r'ADVOGADO\(S\):(.*)'
      resultado = re.search(padrao, string, re.IGNORECASE)
      if resultado != None:
        resultado = resultado.group(1).split('OAB')
        oab = resultado[1].split('/')[0].replace(':','').strip()
        seccional = resultado[1].split('/')[1].strip()
        return  oab, seccional
      else:
        padrao = r'(?:ADVOGADO\(A\)|ADVOGADO|ADVOGADA|ADVOGADO\(S\)|ADVOGADOS\(AS\)): (.*)'
        padrao_2  = r'(.+ ADVOGAD[OA][S]?[AS]?)'
        advogado_e_oab_2 = re.search(padrao_2, string)
        advogado_e_oab = re.search(padrao, string,re.IGNORECASE)
        if advogado_e_oab != None:
          advogado = advogado_e_oab.group(1).strip()
          string_completa = advogado.split(',')
          adv = string_completa[0]
          oab = string_completa[1].replace('.', '').split(' ')
          oab = next((i for i in oab if i.isnumeric()), None)
          return {'advogado': advogado, 'oab': oab}
        elif advogado_e_oab_2 != None:
          adv = advogado_e_oab_2.group(1)
          oab = string.split(adv)[1]
          return {'advogado': adv, 'oab': oab}
        else:
          return {'advogado': '', 'oab': ''}
    if 'OAB' in string and 'CPF' not in string:
      padrao = r'OAB:(.*)'
      resultado = re.search(padrao, string, re.IGNORECASE)
      if resultado != None:
        oab = resultado.group(1).split('/')[0].strip()
        seccional = resultado.group(1).split('/')[1].strip()
        return {'oab': oab, 'seccional': seccional}
      else:
        return {'advogado': '', 'oab': '', 'seccional': ''}
    if 'OAB' in string and 'CPF' in string:
      padrao_cpf = r'CPF:(.*)'
      padrao_oab = r'OAB:(.*)'
      resultado_oab = re.search(padrao_oab, string) 
      resultado_documento = re.search(padrao_cpf, string)
      if resultado_documento != None:
        documento_advogado = resultado_documento.group(1).strip()
      else:
        documento_advogado =  ''
      if resultado_oab != None:
        oab = resultado_oab.group(1).strip().split(' ')[0]
      else:
        oab = ''
      return {'documento_advogado': documento_advogado, 'oab': oab}
    if 'OAB:' in string:
      padrao = r'OAB:(.*)'
      resultado = re.search(padrao, string, re.IGNORECASE)
      if resultado != None:
        resultado = resultado.group(0).strip()
        oab = resultado.split(':')[1].replace('/','').replace('CPF','').strip()
        return {'oab': oab.strip()}
      else:
        return {'oab': ''}
    if 'NOME:' in string or 'NOME(S):' in string or 'NOMES:' in string:
      padrao = r'(?:NOME\(S\)|NOME:|NOME)(.*)'
      resultado = re.search(padrao, string, re.IGNORECASE)
      if resultado != None:
        advogado = resultado.group(1)
        return {'advogado': advogado.strip()}
      else:
        return {'advogado': ''}
    
    if 'QUANTIDADE DE CREDORES' in string:
        padrao = r'QUANTIDADE DE CREDORES:(.*)'
        qdt_credores = re.search(padrao, string,re.IGNORECASE)
        if qdt_credores != None:
          return {'qtd_credores': qdt_credores.group(1)}
        else:
          return {'qtd_credores': '1'}
    if 'TRIBUNAL' in string:
      padrao = r'(?:  DO ESTADO DE| DO ESTADO DO)(.*)'
      estado = re.search(padrao, string, re.IGNORECASE)
      if estado!= None:
        return {'estado': estado.group(1).replace('  ', ' ').strip()}
      else:
        return {'estado': ''}
    if 'VARA' in string or ' VARA' in string or 'VF' in string:
      for linha in string.split('\n'):
        if 'ORIGEM/FORO COMARCA/ VARA:' in linha:
          padrao = r'VARA:(.*)'
          resultado = re.search(padrao, linha, re.IGNORECASE)
          if resultado != None:
            vara = resultado.group(1).split('/')[0]
            return {'vara': vara.strip()}
          else:
            return {'vara': ''}
        if re.search(r'\bVARA\b', linha, re.IGNORECASE):
            return {'vara_pdf': linha.strip()}
    if 'ORIGEM:' in string:
      padrao = r'ORIGEM:(.*)'
      resultado = re.search(padrao, string, re.IGNORECASE)
      if resultado != None:
        vara = resultado.group(0).strip()
        return {'vara': vara}
      else:
        return {'oab': ''}
    if 'JUIZADO' in string:
      return {'vara': string.replace('\n','').strip()}
    if 'FONE' in string and 'CEP' in string:
      padrao = r'([A-Za-zÀ-ÿ\s]+-[A-Za-zÀ-ÿ\s]+'
      resultado = re.search(padrao, string, re.IGNORECASE)
      if resultado != None:
        cidade = resultado.group(1)
        return {'cidade': cidade}
      else:
        return {'cidade': ''}
    if 'E-MAIL' in string:
      padrao = r'(?<=,\s)([^\d-]+)'
      cidade = re.search(padrao, string,re.IGNORECASE)
      verificar_cidade_padrao = r'FONE:*'
      if cidade != None: 
        verificar_cidade = re.search(verificar_cidade_padrao, cidade.group(1).strip())
        if verificar_cidade != None:
          output_string = re.sub(r'\d+', '', string)
          padrao = r"(?:[^,]*,){2}\s*([^\d,-]+)"
          cidade = re.search(padrao, output_string)
          if cidade != None:
            return {'cidade': cidade.group(1).strip()}
          else: 
            return {'cidade': ''}
        else:
          string_completa = string.split(',')
          if 'FONE' in string_completa[1]:
            cidade = string_completa[2].split('-')[0]
            return {'cidade': cidade}
          elif 'FONE' not in string_completa[1]:
            cidade = string_completa[1].split('-')
            return {'cidade': cidade}
          else:
            return {'cidade': ''}
      else:
          return {'cidade': ''}

    if 'PROCESSO Nº:' in string :
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}/\d{2}'
      processo = re.search(padrao, string,re.IGNORECASE)
      if processo != None:
        return {'processo': processo.group(0).strip()} 
      else:
        return {'processo': ''}
    elif 'NÚMERO DO PROCESSO' in string:
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}'
      processo = re.search(padrao, string,re.IGNORECASE)
      if processo != None:
        return {'processo': processo.group(0).strip()} 
      else:
        return {'processo': ''}
    if 'PRINCIPAL/CONHECIMENTO' in string :
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}'
      processo_principal = re.search(padrao, string,re.IGNORECASE)
      if processo_principal != None:
        return {'conhecimento': processo_principal.group(0).strip()}
      else:
        return {'conhecimento': ''} 
    if 'AUTOS DA AÇÃO' in string:
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}'
      processo_principal = re.search(padrao, string, re.MULTILINE)
      if processo_principal != None:
        return {'conhecimento': processo_principal.group(0).strip()}
      else:
        return {'conhecimento': ''} 
    if 'CREDOR' in string:
      padrao = r'(?:CREDOR\(S\)|CREDOR|CREDOR\(ES\)):(.*)'
      credor = re.search(padrao, string,re.IGNORECASE)
      if credor != None:
        credor = limpar_string(credor.group(1).strip())
        return {'credor': credor}
      else:
        return {'credor': ''}
    if 'EXEQUENTE' in string:
      padrao = r'EXEQUENTE\(S\):\s+(.*?)\n'
      exequente = re.search(padrao, string, re.IGNORECASE)
      if exequente != None:
        credor = limpar_string(exequente.group(1).strip())
        return {'credor': credor}
      else:
        return {'credor': ''}
    if 'REQUERENTE' in string:
      padrao = r'REQUERENTE\s+(.*?)\n'
      requerente = re.search(padrao, string)
      if requerente!= None:
        requerente = limpar_string(requerente.group(1))
        return {'credor': requerente}
      else:
        return {'credor': ''}
    if 'DEVEDOR' in string or 'NOME DEVEDOR' in string or 'PÚBLICO DEVEDOR:' in string:
      padrao = r'(?:DEVEDOR|DEVEDOR:|DEVEDOR\(S\)|DEVEDOR\(ES\)|DEVEDOR|EXECUTADO\(S\):) (.*)'
      devedor = re.search(padrao, string, re.IGNORECASE)
      if devedor != None:
        return {'devedor': devedor.group(1).strip().replace('  ', ' ')}
      else:
        return {'devedor': ''}
    elif 'EXECUTADO' in string:
      padrao = r'EXECUTADO\(S\):\s+(.*?)\n'
      devedor = re.search(padrao, string, re.IGNORECASE)
      if devedor != None:
        return {'devedor': devedor.group(1).strip()}
      else:
        return {'devedor': ''}
    if 'REQUERIDO' in string:
      padrao = r'(?:REQUERIDO:|REQUERIDO|REQUERIDO\s+:)\s+(.*?)\n'
      requerido = re.search(padrao, string, re.IGNORECASE)
      if requerido!= None:
        return {'devedor': requerido.group(1).replace(':', '').strip()}
      else:
        return {'devedor': ''}
    if 'NOME' in string:
      padrao = r'NOME:\s+(.+)'
      credor = re.search(padrao, string,re.IGNORECASE)
      if credor!= None:
        return {'nome': credor.group(1).strip()}
      else:
        return {'nome': ''}
    if 'NATUREZA DO CRÉDITO' in string or 'DO CRÉDITO:' in string or 'NATUREZA' in string or 'NATUREZA JURÍDICA DO CRÉDITO' in string or 'TIPO DE DESPESA' in string:
      padrao = r'(?:NATUREZA DO CRÉDITO:|NATUREZA DO CRÉDITO:|DO CRÉDITO:|NATUREZA:|DO CRÉDITO:|TIPO DE DESPESA :)\s+(.*?)\n'
      natureza = re.search(padrao, string,re.IGNORECASE)
      if natureza != None:
        natureza_arteria = tipo_de_natureza(natureza.group(1).strip())
        return natureza_arteria
      else:
          return{'natureza': ''}
    if '(X)' in string or '(X )' in string or '( X )' in string or '( X)' in string or '(X) ' in string:
      padrao = r'\([Xx]\s*\)'
      resultado = re.search(padrao, string, re.IGNORECASE)
      if resultado != None:
        natureza = resultado.end()
        natureza = string[natureza:].strip()
        tipo_natureza = tipo_de_natureza(natureza)
        return tipo_natureza
      else:
        return {'natureza': ''}
    if '(X ) SALÁRIOS, VENCIMENTOS, PROVENTOS, PENSÕES.' in string or '( X ) NÃO-ALIMENTAR' in string or '(X ) BENEFÍCIOS PREVIDENCIÁRIOS E INDENIZAÇÕES.' in string or '( X ) DESAPROPRIAÇÕES – ÚNICO IMÓVEL' in string or '( X ) SALÁRIOS, VENCIMENTOS, PROVENTOS,' in string or '(X ) SALÁRIOS, VENCIMENTOS, PROVENTOS, PENSÕES. ( ) NÃO-ALIMENTAR' in string or '(x ) Salários, Vencimentos, Proventos, Pensões. ( ) Não-Alimentar' in string:
      padrao = r'\( ?x ?\) (.+?)\.'
      resultado = re.search(padrao, string, re.IGNORECASE)
      if resultado != None:
        natureza = resultado.group(1).strip()
        tipo_natureza = tipo_de_natureza(natureza)
        return tipo_natureza
      else:
        return {'natureza': ''}
    if 'JUROS  MORATÓRIOS' in string or 'MORATÓRIOS' in string or 'VALOR JUROS' in string:
      padrao = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b' 
      valor_juros = re.search(padrao, string, re.IGNORECASE)
      if valor_juros != None:
        return {'valor_juros': valor_juros.group(0).strip().replace('.','').replace(',','.')}
      else:
        return {'valor_juros': ''}
    if 'PRINCIPAL/INDENIZAÇÃO' in string or "VALOR ORIGINÁRIO" in string or 'ORIGINÁRIO:' in string or 'VALOR BRUTO' in string or "VALOR PRINCIPAL" in string or 'VALOR ATUALIZADO' in string:
      padrao = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b'  
      valor_principal = re.search(padrao, string, re.IGNORECASE)
      if valor_principal != None:
        return {'valor_principal': valor_principal.group(0).strip().replace('.','').replace(',','.')}
      else:
        return {'valor_principal': ''}
    if 'SUBTOTAL 1' in string:
      padrao = r'(\d{1,3}(?:\.\d{3})*(?:,\d+)?)(?=\s|$)' 
      valor_principal = re.findall(padrao, string)
      if valor_principal != None:
        return {'valor_principal': valor_principal[1].strip().replace('.', '').replace(',','.')}
      else:
        return {'valor_principal': ''}
    if 'VALOR TOTAL DA CONDENAÇÃO' in string:
      padrao = r'(\d{1,3}(?:\.\d{3})*(?:,\d+)?)(?=\s|$)' 
      valor_principal = re.findall(padrao, string)
      if valor_principal != None:
        return {'valor_principal': valor_principal[0].strip().replace('.','').replace(',','.')}
      else:
        return {'valor_principal': ''}
    if 'VALOR GLOBAL' in string or "VALOR TOTAL" in string or 'R$' in string or 'VALOR(R$):' in string or 'GLOBAL' in string :
        if 'VALOR JUROS' not in string and 'VALOR PRINCIPAL' not in string:
          padrao = r'\b(?:0{1,3}|[1-9](?:\d{0,2}(?:\.\d{3})*(?:,\d{1,2})?|,\d{1,2})?)\b|\b(?:0{1,3}|[1-9](?:\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?|\.\d{1,2})?)\b' 
          valor_global = re.search(padrao, string,re.IGNORECASE)
          if valor_global != None:
            return {'valor_global': valor_global.group(0).strip().replace('.','').replace(',','.')}
          else: 
            return {'valor_global': ''}
    if 'CPF/CNPJ' in string or 'CPF' in string:
      padrao = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
      documento = re.search(padrao, string, re.IGNORECASE)
      if documento != None:
        return {'documento': documento.group(0).strip()}
      else:
        return {'documento': ''}
    if 'DATA DO NASCIMENTO' in string or 'DATA DE NASCIMENTO' in string or 'BENEFICIÁRIO:' in string or 'DATA NASCIMENTO' in string:
      padrao = r'\b(?:\d{1,2}\/\d{1,2}\/\d{4}|\d{4}\/\d{1,2}\/\d{1,2}|\d{1,2}\-\d{1,2}\-\d{4}|\d{4}\-\d{1,2}\-\d{1,2})\b'
      nascimento = re.search(padrao, string,re.IGNORECASE)
      if nascimento != None:
        nascimento  = nascimento.group(0).replace('-','/').strip()
        dia, mes, ano = nascimento.split('/')
        data_padrao_arteria = f"{mes}/{dia}/{ano}"
        return {'data_nascimento': data_padrao_arteria}
      else:
        return {'data_nascimento': ''}
    if 'DE 20' in string: 
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

def principal_e_juros_poupanca(string):
  valores = string.split('poupança')
  principal = valores[0].split('R$')
  principal = principal[1].replace('.', '').replace(',','.').strip()
  juros  = valores[1].split('R$')
  juros = juros[1].replace('.', '').replace(',','.').strip()
  return principal, juros

def tipo_de_natureza(natureza):
  natureza = limpar_string(natureza)
  print('natureza = ', natureza)
  if natureza in tipos_alimentar:
    return {'natureza': 'ALIMENTAR'.upper()}
  elif  natureza in tipos_comum:
    return {'natureza': 'COMUM - NÃO TRIBUTÁRIO'.upper()}
  else:
    return {'natureza': ''}

def limpar_string(string):
  string_limpa = re.sub(r'[^a-zA-ZÀ-ÿ\s]', '', string).replace(':', '')
  return string_limpa.strip()

def identificar_estados(sigla_estado):
  estado = ''
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
    if e == sigla_estado.strip():
      estado =  f'{estados_brasileiros[e].upper()}'
  return estado

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
      tipo = 'COMUM - NÃO TRIBUTÁRIO'
  return tipo

def procurar_precatorio_trf(publicacao, processo):
    padrao = r'(?:\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}|\d{7}-\s\d{2}.\d{4}.\d{1}.\d{2}.\d{4})'
    resultado = re.findall(padrao, publicacao)
    if len(resultado) > 1:
      for i in resultado:
        if i == processo:
          resultado.remove(i)
      if len(resultado) >= 1:
        resultados = []
        for n_processo in resultado:
          resultado_trf = re.search(padrao, n_processo)
          if resultado_trf:
            if resultados == []:
              resultados.append(resultado_trf.group(0))
            elif resultados[-1] != resultado_trf.group(0):
              resultados.append(resultado_trf.group(0))
        return resultados 
      else:
        return []
    else:
      return resultado

def extrair_processo_origem_amazonas(processo_origem, processo_xml):
  # if '.8.26.' in processo_xml:
  #   padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}/\d{2,6}'
  # else:
  padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}'
  resultado = re.findall(padrao, processo_origem)
  if len(resultado) > 1:
    if processo_xml in resultado:
      for i in range(resultado.count(processo_xml)):
        if processo_xml in resultado:
          resultado.remove(processo_xml)
        else:
          return resultado[0]
      if len(resultado) > 0:
        return resultado[0]
      else:
        return ''
        
  elif len(resultado) == 1:
    return ''
  else:
    return ''

def extrair_processo_origem(processo, processo_xml):
  padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}/\d{2,4}'
  resultado = re.search(padrao, processo)
  if resultado != None:
    if resultado.group(0).strip() == processo_xml:
      return ''
    else:
      return resultado.group(0).strip()
  else:
    return ''

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
        tipo = {'tipo': dict_tribunais[tribunal].upper()}
    return tipo
  except:
    return {'tipo': ''}
  

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
  padrao = r'\d{2,4}|\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}'
  processo = re.search(padrao, n_processo)
  if processo != None:
    return True


def verificar_tribunal_lista(processos):
  padrao = r'(?:\d{7}-\d{2}.\d{4}.4.04.\d{4}/\d{2,4}|\d{7}-\d{2}.\d{4}.4.04.\d{4}|\d{7}-\d{2}.\d{4}.4.02.\d{4}/\d{2,4}|\d{7}-\d{2}.\d{4}.4.02.\d{4})'
  processos_origem = []
  for n_processo in processos:
    processo = re.search(padrao, n_processo)
    if processo != None:
      processos_origem.append(processo.group(0))
  return processos_origem     

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

def mandar_documento_para_ocr(arquivo, op,insc='',pasta="arquivos_texto_ocr"):
  arquivo_base_64 = converter_arquivo_base_64(arquivo)
  if op == '1':
    arquivo_txt = text_ocr(arquivo_base_64, insc, pasta)
    return arquivo_txt
  if op == '2':
    resp = google_ocr(arquivo_base_64)
    return resp
  if op == '3':
    resultado = ler_imagem_ocr(arquivo_base_64)
    return resultado
  if op == '4':
    arquivo_txt = ler_img_sem_google(arquivo_base_64, insc, pasta)
    return arquivo_txt

def converter_arquivo_base_64(nome_arquivo):
  with open(nome_arquivo, "rb") as arquivo:
            dados = arquivo.read()
            dados_base64 = base64.b64encode(dados)
            return dados_base64.decode("utf-8") 
  
def text_ocr(arquivo_base_64_pdf, insc,pasta):
  url = 'http://192.168.88.205:9000/extrair_texto_ocr_image'
  headers = {
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'api-key': '8cb99ca8-9e55-11ed-a8fc-0242ac120002'
  }
  json_data = {
    'img': f"{arquivo_base_64_pdf}"
  }
  response = requests.post(url, headers=headers, json=json_data)
  response = response.json()
  txt = response['img_text']
  arquivo_txt = f'{pasta}/{insc}_texto_ocr.txt'
  for i in range(len(txt)):
    with open(f'{pasta}/{insc}_texto_ocr.txt', 'a', encoding='utf-8') as f:
      f.write(txt[i])
  return arquivo_txt

def google_ocr(arquivo_base_64_pdf):
  url = 'http://192.168.88.205:9000/google_extract'
  headers = {
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'api-key': '8cb99ca8-9e55-11ed-a8fc-0242ac120002'
  }
  json_data = {
    'pdf': f"{arquivo_base_64_pdf}"
  }
  response = requests.post(url, headers=headers, json=json_data).json()
  return response 

def ler_imagem_ocr(arquivo_base_64_pdf):
  url = 'http://192.168.88.205:9000/extrair_texto_ocr_image'
  headers = {
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'api-key': '8cb99ca8-9e55-11ed-a8fc-0242ac120002'
  }
  json_data = {
    'img': f"{arquivo_base_64_pdf}"
  }
  response = requests.post(url, headers=headers, json=json_data).json()
  txt = response['img_text']
  return txt

def ler_img_sem_google(arquivo_base_64_pdf, insc,pasta):
  url = 'http://192.168.88.205:9000/extrair_texto_ocr_image'
  headers = {
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'api-key': '8cb99ca8-9e55-11ed-a8fc-0242ac120002'
  }
  json_data = {
    'img': f"{arquivo_base_64_pdf}"
  }
  response = requests.post(url, headers=headers, json=json_data)
  response = response.json()
  txt = response['img_text']
  arquivo_txt = f'{pasta}/{insc}_texto_ocr.txt'
  for i in range(len(txt)):
    with open(f'{pasta}/{insc}_texto_ocr.txt', 'a', encoding='utf-8') as f:
      f.write(txt[i])
  return arquivo_txt

def dados_limpos_banco_de_dados(dados):
  dados['data_nascimento'] = converter_data(dados['data_nascimento'])
  dados['data_expedicao'] = converter_data(dados['data_expedicao'])


  if 'conhecimento' in dados:  
    if dados['conhecimento'] == '':
      del dados['conhecimento']
    else:
      dados['processo_origem'] = dados.pop('conhecimento')

  chaves_a_excluir = ['credor', 'data_nascimento', 'oab','seccional' ,'advogado','data_nascimento','devedor','documento','processo_geral','site','seccional','telefone', 'documento_advogado']

  for chave in chaves_a_excluir:
    dados.pop(chave, '')

  return dados
        
def converter_data(data):
  if data != '':
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
    return 'COMUM - NÃO TRIBUTÁRIO'
  else:
    natureza

def buscar_cpf(arquivo_txt):
      with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        texto = arquivo.read()
      padrao = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
      documento = re.search(padrao, texto)
      if documento != None:
        return {'cpf_cnpj': documento.group(0)}
      else:
        return {'cpf_cnpj': ''}

def encontrar_indice_linha(linhas, texto):
  for indice, linha in enumerate(linhas):
    if texto in linha.lower().replace('  ', ' '):
        return indice
  return None

def apagar_arquivos(pastas):
  for pasta in pastas:
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
    
def data_corrente_formatada():
    data_atual = datetime.now()
    data_formatada = data_atual.strftime("%d_%m_%Y")
    return data_formatada

def dados_limpos_banco_de_dados(dados):
  dados['data_nascimento'] = converter_data(dados['data_nascimento'])
  dados['data_expedicao'] = converter_data(dados['data_expedicao'])


  if 'conhecimento' in dados:  
    if dados['conhecimento'] == '':
      del dados['conhecimento']
    else:
      dados['processo_origem'] = dados.pop('conhecimento')

  chaves_a_excluir = ['credor', 'nascimento', 'oab','seccional' ,'advogado','data_nascimento','devedor','documento','processo_geral','site','seccional','telefone', 'documento_advogado']

  for chave in chaves_a_excluir:
    dados.pop(chave, '')

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

def pegar_cpf_e_credor(indice, texto):
  string = texto[indice]
  padrao_cpf = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
  cpf_cnpj_rne = re.search(padrao_cpf, string)
  if cpf_cnpj_rne != None:
      cpf = cpf_cnpj_rne.group(0).strip()
  else:
      cpf =  ''
  padrao_credor = r'[a-zA-ZÀ-ÖØ-öø-ÿ]+'
  resultado_credor = re.findall(padrao_credor, string)
  if resultado_credor != None:
      credor = ' '.join(resultado_credor)
  else:
      credor = ''
  return {'cpf': cpf,'credor': credor}

def pegar_cidade(texto, indice):
    for i in dict.keys(indice):
      if indice[i] != None:
        cidade = texto[indice[i]].replace('\n', '').replace(',', '').replace('.', '').strip()
        return {'cidade': cidade}
      else:
          return {'cidade': ''}

def verificar_e_criar_pastas(lista_pastas, diretorio):
    for pasta in lista_pastas:
        caminho_pasta = os.path.join(diretorio, pasta)
        if not os.path.exists(caminho_pasta):
            os.makedirs(caminho_pasta)


def ler_arquivo_pdf_transformar_em_txt(arquivo_pdf):
  nome_txt = arquivo_pdf.replace('pdf', 'txt')
  pdf_file = open(arquivo_pdf, 'rb')
  pdf_reader = PdfReader(pdf_file)
  text = ''
  
  for page_num in range(len(pdf_reader.pages)): 
    page = pdf_reader.pages[page_num]
    text += page.extract_text()

    with open(nome_txt, "a", encoding='utf-8') as arquivo:
      arquivo.write(text)
  return nome_txt

def pdf_to_png(pdf_path, output_pdf_path, processo):
    pdf_document = fitz.open(pdf_path)
    for page_number in range(pdf_document.page_count):
        page = pdf_document[page_number]
        image = page.get_pixmap()
        pil_image = Image.frombytes("RGB", [image.width, image.height], image.samples)
        pil_image.save(f"{output_pdf_path}/{processo}_{page_number + 1}.png", "PNG")
    pdf_document.close()
    return f"{output_pdf_path}/{processo}_4.png"

def formatar_data_padrao_arteria(data):
  dia, mes, ano = data.strip().split('/')
  data_padrao_arteria = f"{mes}/{dia}/{ano}"
  return data_padrao_arteria