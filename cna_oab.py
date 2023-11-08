import os
import re
import requests
import urllib.request
from capmon_utils import recaptcha
from auxiliares import mandar_documento_para_ocr
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio

def login_cna(insc, uf, documento_advogado, nome, processo):
  if ' e ' in nome:
    novo_nome = nome.split(' e ')
    if len(novo_nome) > 1:
      if ' ' in novo_nome[1].strip():
        for name in novo_nome:
          if ',' in name:
            n = name.split(',')
            for i in n:
              dados_advogado = login(insc, uf, documento_advogado, i, processo)
              return dados_advogado
      else:
        dados_advogado = login(insc, uf, documento_advogado, nome , processo)
        return dados_advogado
  else:
    dados_advogado = login(insc, uf, documento_advogado, nome, processo)
    return dados_advogado
  
def login(insc, uf, documento_advogado, nome, processo):      
  site_key = os.environ.get('site_key')
  url_cna = os.environ.get('url_cna')
  captcha = recaptcha(site_key, url_cna)
  nome_adv = ''
  if insc == '':
    nome_adv = nome  
  form_data  = {
    'IsMobile': 'false',
    'NomeAdvo': f'{nome_adv}',
    'Insc': f'{insc}',
    'Uf': f'{uf}',
    'TipoInsc': '1',
    'g-recaptcha-response': captcha['code']
  }

  pesquisar_cna = f'{url_cna}/Home/Search'
  resp_foto = requests.post(pesquisar_cna, data=form_data).json()
  resp = baixar_foto_carteirinha_oab(resp_foto, url_cna, documento_advogado, processo, nome, uf,insc)
  return resp

def baixar_foto_carteirinha_oab(resp_foto, url_cna, documento_advogado, processo, nome, uf,insc):
    documento_advogado = limpar_string_documento(documento_advogado)
    if resp_foto['Data'] != [] :
      url_foto = resp_foto['Data'][0]['DetailUrl']
      pegar_foto = f'{url_cna}{url_foto}'
      data_nome = resp_foto['Data'][0]['Nome']
      foto = requests.get(pegar_foto).json()
      detalhes_foto = foto['Data']['DetailUrl']
      if insc == '':
        insc = resp_foto['Data'][0]['Inscricao']
      nome_insc = insc.replace('.','').replace('/','')
      caminho_foto = f'fotos_oab/{nome_insc}_foto_oab.jpg'
      urllib.request.urlretrieve(f'{url_cna}{detalhes_foto}', caminho_foto)
      texto_ocr = mandar_documento_para_ocr(caminho_foto, '3')
      texto_ocr = texto_ocr.replace('\n', ' ')
      dados = dados_advogado(texto_ocr, data_nome, uf, insc, documento_advogado)
      enviar_banco_de_dados(dados, processo)  
    else:
      dados = {'telefone': '', 'advogado': nome.strip(), 'seccional': uf, 'oab': insc, 'documento_advogado': documento_advogado}
      enviar_banco_de_dados(dados, processo)
    return dados
  
def limpar_string_documento(documento):
  padrao = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
  resultado = re.search(padrao, documento)
  if resultado:
    documento = resultado.group(0)
  return documento.strip()

def dados_advogado(txt, nome, uf, insc, documento_advogado):
  padrao = r'(?:\(?\d{2}\)?\s?\d{4,5}-\d{4}|\(?\d{2}\)?\s?\d{8,9}|\d{10,11})'
  resultado = re.search(padrao, txt, re.MULTILINE)
  if resultado != None:
    return {'telefone': resultado.group(0), 'advogado': nome, 'seccional': uf, 'oab': insc, 'documento_advogado': documento_advogado}
  else:
    return {'telefone': '', 'advogado': nome, 'seccional': uf, 'oab': insc, 'documento_advogado': documento_advogado}

def enviar_banco_de_dados(dados, processo):
    dados['documento'] = dados.pop('documento_advogado')
    dados['nome'] = dados.pop('advogado')
    dados['estado'] = dados.pop('seccional')
    dados['tipo'] = 'advogado'
    
    if type(dados['documento']) is dict:
      dados['documento'] = dados['documento']['documento']

    atualizar_ou_inserir_pessoa_no_banco_de_dados(dados['oab'], dados)
    atualizar_ou_inserir_pessoa_precatorio(dados['oab'], processo)
    dados['seccional'] = dados.pop('estado')
    dados['advogado'] = dados.pop('nome')
    del dados['tipo']
    del dados['documento']
