import re
import traceback
from logs import log
from cna_oab import login_cna
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_acre_precatorios import get_docs_oficio_precatorios_tjac
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, consultar_processos, atualizar_ou_inserir_precatorios_no_banco_de_dados
from utils import  converter_string_mes, identificar_estados, limpar_dados, mandar_documento_para_ocr,  tipo_de_natureza, tipo_precatorio, verificar_tribunal

def buscar_dados_tribunal_acre():
  dados = consultar_processos('.8.01')

  for d in dados:
          dados_limpos = limpar_dados(d)
          tipo = tipo_precatorio(d)
          dado = dados_limpos | tipo
          if verificar_tribunal(d['processo']):
            ler_documentos(dado)
          else:
            pass


def ler_documentos(dado_xml):
      try:      
        processo_geral = dado_xml['processo_origem']
        doc = get_docs_oficio_precatorios_tjac(dado_xml['processo_origem'],zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          arquivo_pdf = f"arquivos_pdf_acre/{processo_geral}_arquivo_precatorio.pdf"
          id_documento = doc[codigo_processo][0][0]
          file_path = doc[codigo_processo][0][2]
          with open(arquivo_pdf, "wb") as arquivo:
                  arquivo.write(file_path)

          dados_ocr = mandar_documento_para_ocr(arquivo_pdf, '2')
          dados_complementares = {"processo_geral": 'processo_geral', "codigo_processo": codigo_processo, 'site': 'https://esaj.tjac.jus.br', 'id_documento': id_documento, 'valor_juros': '', 'valor_principal': ''}
          dados_ocr = dados_ocr | dados_complementares
          tratar_dados_ocr(arquivo_pdf ,processo_geral, dados_ocr)
          
      except Exception as e:
        print(f"Erro no processo -> ", processo_geral, 'Erro: ', e)
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
  atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, {'nome': credor, 'documento': documento, 'data_nascimento': ''})
  
  dados_advogado = {}
  if advogado != '':
    dados_advogado = login_cna(oab,seccional,documento_advogado,advogado,processo)
  dado = {'data_expedicao': data, 'cidade': cidade, 'processo_origem': origem, 'devedor': devedor, 'credor': credor, 'valor_global': valor, 'vara': vara, 'documento': documento} | natureza | estado | dados_advogado
  id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dado)
  dado['id_sistema_arteria'] = id_sistema_arteria
  atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dado)
  atualizar_ou_inserir_pessoa_precatorio(dado['documento'], processo)
  log({'processo': origem, 'tipo': 'Sucesso', 'site': dados['site'], 'mensagem': 'Precatório registrado com sucesso', 'estado': dados['estado']})


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
