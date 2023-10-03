import os
import re
import requests
import urllib.request
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio
from capmon_utils import recaptcha
from utils import mandar_documento_para_ocr


def pegar_foto_oab(insc, uf, documento_advogado, nome, processo):
  site_key = os.environ.get('site_key')
  url_cna = os.environ.get('url_cna')
  captcha = recaptcha(site_key, url_cna)
  form_data  = {
    'IsMobile': 'false',
    'NomeAdvo': '',
    'Insc': f'{insc}',
    'Uf': f'{uf}',
    'TipoInsc': '1',
    'g-recaptcha-response': captcha['code']
  }

  pesquisar_cna = f'{url_cna}/Home/Search'
  resp_foto = requests.post(pesquisar_cna, data=form_data).json()

  if resp_foto['Data'] != [] :
    url_foto = resp_foto['Data'][0]['DetailUrl']
    pegar_foto = f'{url_cna}{url_foto}'
    data_nome = resp_foto['Data'][0]['Nome'].capitalize()
    foto = requests.get(pegar_foto).json()
    detalhes_foto = foto['Data']['DetailUrl']
    caminho_foto = f'fotos_oab/{insc}_foto_oab.jpg'
    urllib.request.urlretrieve(f'{url_cna}{detalhes_foto}', caminho_foto)
    texto_ocr = mandar_documento_para_ocr(caminho_foto, '3')
    dados = dados_advogado(texto_ocr, data_nome, uf, insc, documento_advogado)
    enviar_banco_de_dados(dados, processo)
    
  else:
    dados = {'telefone': '', 'advogado': nome.strip(), 'seccional': uf, 'oab': insc, 'documento_advogado': documento_advogado}
    enviar_banco_de_dados(dados, processo)

  return dados

def dados_advogado(txt, nome, uf, insc, documento_advogado):
  padrao = r'\(?\d{2}\)?\s?\d{4,5}-\d{4}'
  resultado = re.search(padrao, txt, re.MULTILINE)
  if resultado != None:
    return {'telefone': resultado.group(0), 'advogado': nome, 'seccional': uf, 'oab': insc, 'documento_advogado': documento_advogado}
  else:
    return {'telefone': '', 'advogado': nome, 'seccional': uf, 'oab': insc, 'documento_advogado': documento_advogado}

def enviar_banco_de_dados(dados, processo):
    dados['documento'] = dados.pop('documento_advogado')
    dados['nome'] = dados.pop('advogado')
    dados['estado'] = dados.pop('seccional')

    if type(dados['documento'])is dict:
      dados['documento'] = dados['documento']['documento']

    atualizar_ou_inserir_pessoa_no_banco_de_dados(dados['oab'], dados)
    atualizar_ou_inserir_pessoa_precatorio(dados['oab'], processo)
    dados['seccional'] = dados.pop('estado')
    dados['advogado'] = dados.pop('nome')
    del dados['documento']