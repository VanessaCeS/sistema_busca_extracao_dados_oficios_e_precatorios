import re
import traceback
import xmltodict
from pathlib import Path
from banco_de_dados import atualizar_ou_inserir_pessoa, atualizar_ou_inserir_pessoa_precatorio, mandar_precatorios_para_banco_de_dados
from cna_oab import login_cna
from rotina_sao_paulo import apagar_arquivos_txt
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_acre_precatorios import get_docs_oficio_precatorios_tjac
from utils import  buscar_xml, converter_string_mes, data_corrente_formatada, extrair_processo_origem, identificar_estados, limpar_dados, mandar_documento_para_ocr,  tipo_de_natureza, tipo_precatorio, verificar_tribunal

def ler_xml():
  buscar_xml()
  with open(f'arquivos_xml/relatorio_{data_corrente_formatada()}', 'r', encoding='utf-8') as fd:
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

def ler_documentos(processo, arquivo):
      try:
        # processo_geral = dado['processo']
        # doc = get_docs_oficio_precatorios_tjac(dado['processo'],zip_file=False, pdf=True)
        # if doc != {}:
        #   codigo_processo = next(iter(doc))
        #   file_path = doc[codigo_processo][0][1]
        #   id_documento = doc[codigo_processo][0][0]
        #   arquivo_pdf = f"arquivos_pdf_acre/{processo_geral}_arquivo_precatorio.pdf"

        #   with open(arquivo_pdf, "wb") as arq:
        #         arquivo = arq.write(file_path)
                
          dados_ocr = mandar_documento_para_ocr(arquivo, '2')

          dados_complementares = {"processo_geral": 'processo_geral', "codigo_processo": 'codigo_processo', 'site': 'https://esaj.tjac.jus.br', 'id_documento': 'id_documento', 'valor_juros': '', 'valor_principal': ''}
          dados_ocr = dados_ocr | dados_complementares
          tratar_dados_ocr(arquivo ,processo, dados_ocr)
          
      except Exception as e:
        print(f"Erro no processo -> ", "dado['processo']", 'Erro: ', e)
        print(traceback.print_exc())
        pass

def tratar_dados_ocr(arquivo_pdf,processo, dados):
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
  documento_advogado = ''
  atualizar_ou_inserir_pessoa(documento, {'nome': credor, 'documento': documento, 'data_nascimento': ''})
  
  dados_advogado = {}
  if advogado != '':
    dados_advogado = login_cna(oab,seccional,documento_advogado,advogado,processo)
  dado = {'data_expedicao': data, 'cidade': cidade, 'processo_origem': origem, 'devedor': devedor, 'credor': credor, 'valor_global': valor, 'vara': vara, 'documento': documento} | natureza | estado | dados_advogado
  
  id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dado)
  dado = dado | id_sistema_arteria

  mandar_precatorios_para_banco_de_dados(dados['codigo_processo'], dado)
  atualizar_ou_inserir_pessoa_precatorio(dado['documento'], processo)

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
    if 'oab' in d:
      oab = dados['advogado'][0]['oab'][0].split(' ')[1].strip()
      seccional = dados['advogado'][0]['oab'][0].split('/')[1].strip()
      return oab, seccional    
    else: 
      return '', ''
    
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

ler_documentos('0004533-83.2009.8.01.0001','arquivos_cortados/0100115-98.2018.8.01.0000.pdf_cortado.pdf')