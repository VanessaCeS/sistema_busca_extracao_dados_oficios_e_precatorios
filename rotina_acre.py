import re
import traceback
import xmltodict
from pathlib import Path
from cna_oab import pegar_foto_oab
from rotina_sao_paulo import apagar_arquivos_txt
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_acre_precatorios import get_docs_oficio_precatorios_tjac
from utils import  buscar_xml, converter_string_mes, extrair_processo_origem, identificar_estados, limpar_dados, mandar_documento_para_ocr, mandar_para_banco_de_dados, tipo_de_natureza, tipo_precatorio, verificar_tribunal

def ler_xml():
  arquivo_xml = buscar_xml()
  with open(arquivo_xml, 'r', encoding='utf-8') as fd:
    dados = []
    doc = xmltodict.parse(fd.read())
    base_doc = doc['Pub_OL']['Publicacoes']
    for i in range(len(doc['Pub_OL']['Publicacoes']))  :
      processo_origem =  extrair_processo_origem(f"{base_doc[i]['Publicacao']})")
      requerente, requerido, valor = pegar_requerido_xml(f"{base_doc[i]['Publicacao']})")
      dados.append({"processo": f"{base_doc[i]['Processo']}", "tribunal": f"{base_doc[i]['Tribunal']}", "materia": f"{base_doc[i]['Materia']}", 'origem': processo_origem, 'requerido': requerido, 'requerente': requerente, 'valor': valor})

    for d in dados:
          dados_limpos = limpar_dados(d)
          tipo = tipo_precatorio(d)
          dado = dados_limpos | tipo
          if verificar_tribunal(d['processo']):
            ler_documentos(dado)
          else:
            pass
    apagar_arquivos_txt()

def ler_documentos(dado):
      try:
        processo_geral = dado['processo']
        doc = get_docs_oficio_precatorios_tjac(dado['processo'],zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          file_path = doc[codigo_processo][0][1]
          arquivo_pdf = f"arquivos_pdf_acre/{processo_geral}_arquivo_precatorio.pdf"

          with open(arquivo_pdf, "wb") as arq:
                arquivo = arq.write(file_path)
                
          dados_ocr = mandar_documento_para_ocr(arquivo, '2')
          dados = tratar_dados_ocr(dados_ocr)
          id_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
          dados = dados | {'id_rastreamento': id_arteria}
          mandar_para_banco_de_dados('codigo_processo', dados)
      except Exception as e:
        print(f"Erro no processo -> ", processo_geral, 'Erro: ', e)
        print(traceback.print_exc())
        pass

def tratar_dados_ocr(dados):
  advogado = dados['advogado'][0]['nome'][0] 
  data_expedicao = dados['data-expedicao'][0] 
  cidade = dados['local'][0]['cidade'][0] 
  estado = pegar_estado(dados['local'])
  natureza = pegar_natureza(dados['natureza-do-credito'])
  origem = dados['processo-origem'][0]
  credor = dados['requerente'][0]['nome'][0]
  devedor = dados['requerido'][0]['nome'][0]
  valor = dados['valor'][0].replace('.','').replace(',','.')
  vara = dados['vara'][0]
  documento = pegar_documento(dados['requerente'])
  data = converter_string_mes(data_expedicao)
  natureza = tipo_de_natureza(natureza)
  estado = identificar_estados(estado)
  oab, seccional = pegar_aob_e_seccional(dados['advogado'][0])

  if oab != '':
    telefone = pegar_foto_oab(oab,seccional,advogado)
  else:
    telefone = ''
  
  dado = {'advogado': advogado, 'data_expedicao': data, 'cidade': cidade, 'origem': origem, 'devedor': devedor, 'credor': credor, 'valor': valor, 'vara': vara, 'documento': documento, 'oab': oab, 'seccional': seccional} | natureza | estado | telefone
  
  return dado

def pegar_estado(local):
  estado = ''
  for l in local:
    if 'estado' in dict.keys(l):
      estado = l['estado'][0]
      return estado

def pegar_natureza(natureza):
  descricao = ''
  for n in natureza:
    if 'descricao' in dict.keys(n):
      descricao = n['descricao'][0]
      return descricao
    
def pegar_documento(documento):
  for d in documento:
    if 'documento' in dict.keys(d):
      cpf_cnpj = d['documento'][0]
    else:
      cpf_cnpj = ''
  return cpf_cnpj

def pegar_aob_e_seccional(dados):
  for d in dados:
    if 'oab' in dict.keys(d):
      oab = dados['advogado'][0]['oab'][0].split(' ')[1].strip()
      seccional = dados['advogado'][0]['oab'][0].split('/')[1].strip()
      return oab, seccional    
    
def pegar_requerido_xml(dados):
  if 'Requerente' in dados:
    padrao = r'Requerente:(.*)'
    resultado = re.search(padrao, dados, re.IGNORECASE)
    if resultado != None:
      requerente = resultado.group(1).strip()
    else:
        requerente = ''
  if 'Requerido' in dados:
    padrao = r'Requerido:(.*)'
    resultado = re.search(padrao, dados, re.IGNORECASE)
    if resultado != None:
      requerido = resultado.group(1).strip()
    else:
      requerido = ''
  return  requerente, requerido



pasta = 'minha_pasta'

path = Path(pasta)

if not path.is_dir():
    path.mkdir(parents=True)