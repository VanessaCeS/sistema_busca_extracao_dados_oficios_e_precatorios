import os
import requests
from PIL import Image
from capmon_utils import recaptcha
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def pegar_foto_oab(insc, uf, nome=''):
  site_key = os.environ.get('site_key')
  url_cna = os.environ.get('url_cna')
  captcha = recaptcha(site_key, url_cna)
  form_data  = {
    'IsMobile': 'false',
    'NomeAdvo': f'{nome}',
    'Insc': f'{insc}',
    'Uf': f'{uf}',
    'TipoInsc': '1',
    'g-recaptcha-response': captcha['code']
  }

  pesquisar_cna = f'{url_cna}/Home/Search'
  resp_foto = requests.post(pesquisar_cna, data=form_data).json()

  url_foto = resp_foto['Data'][0]['DetailUrl']
  pegar_foto = f'{url_cna}{url_foto}'

  foto = requests.get(pegar_foto).json()
  detalhes_foto = foto['Data']['DetailUrl']

  with open(f'fotos_oab/{insc}_foto_oab.jpg', 'wb') as imagem:
    resposta = requests.get(f'{url_cna}{detalhes_foto}')
    if not resposta.ok:
      print("Ocorreu um erro, status:" , resposta.status_code)
    else:
      for dado in resposta.iter_content(1024):
        if not dado:
            break
        imagem.write(dado)
    pdf = transformar_foto_em_pdf(f'fotos_oab/{insc}_foto_oab.jpg', insc)
    return pdf

def transformar_foto_em_pdf(foto,insc):
  imagem = Image.open(foto)

  c = canvas.Canvas(f'pdf_oab/{insc}_pdf_oab.pdf', pagesize=letter)
  c.setPageSize((imagem.width, imagem.height))
  c.drawImage(foto, 0, 0, width=imagem.width, height=imagem.height)
  c.save()
  return f'pdf_oab/{insc}_pdf_oab.pdf'