from logs import log
from PyPDF2 import PdfReader
from cna_oab import login_cna
from eproc_ import login_eproc
from funcoes_arteria import enviar_valores_oficio_arteria
from auxiliares import  encontrar_indice_linha, limpar_dados, tipo_de_natureza, ler_arquivo_pdf_transformar_em_txt, tipo_precatorio
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro, consultar_processos

def buscar_dados_tribunal_santa_catarina():     
    dados = consultar_processos('.8.16.')
    for d in dados:
          dados_limpos = limpar_dados(d)
          tipo = tipo_precatorio(d)
          dado = dados_limpos | tipo
          ler_documento(dado)
        
def ler_documento(dados_xml):
  login_trf = 'DF018283'
  senha = 'Costaesilva33*'
  site = 'https://eproc2g.tjsc.jus.br/eproc'

  arquivo_pdf, id_documento = login_eproc(login_trf,senha,site, dados_xml['processo'])
  arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
  dados = dados_xml | {'site': site, 'tipo': 'ESTADUAL', 'id_documento': id_documento, 'codigo_processo': id_documento}

  extrair_dados(arquivo_pdf, arquivo_txt, dados)

def extrair_dados(arquivo_pdf, arquivo_txt, dados_xml):
  with open(arquivo_txt, 'r', encoding='utf-8') as f:
    linhas = f.readlines()
  dados = {}
  indice_estado = 0
  indice_processo = encontrar_indice_linha(linhas, 'número do processo')
  indice_advogado = encontrar_indice_linha(linhas, "procurador do autor")
  indice_credor = encontrar_indice_linha(linhas, 'beneficiário do crédito')
  indice_devedor = encontrar_indice_linha(linhas, 'parte passiva')
  indice_data_expedicao = encontrar_indice_linha(linhas, 'data de intimação das partes sobre valor e expedição desta requisição de precatório')
  indice_data_nascimento = encontrar_indice_linha(linhas, 'data de nascimento')
  indice_natureza = encontrar_indice_linha(linhas, 'natureza do crédito')
  indice_documento = encontrar_indice_linha(linhas, 'cpf/cnpj')
  indice_valor_principal = encontrar_indice_linha(linhas, 'valor corrigido')
  indice_valor_juros = encontrar_indice_linha(linhas, 'valor dos juros moratórios')
  indice_valor_global = encontrar_indice_linha(linhas, 'valor total da requisição')

  dados['estado'] = linhas[indice_estado].replace('\n', '').replace('ESTADO DE','').strip()
  dados['processo'] = extrair_dados(linhas[indice_processo])
  dados['credor'] = extrair_dados(linhas[indice_credor])
  dados['devedor'] = extrair_dados(linhas[indice_devedor])
  dados['data_expedicao'] = extrair_dados(linhas[indice_data_expedicao])
  dados['valor_principal'] = extrair_dados(linhas[indice_valor_principal])
  dados['valor_juros'] = extrair_dados(linhas[indice_valor_juros])
  dados['valor_global'] = extrair_dados(linhas[indice_valor_global])
  natureza = tipo_de_natureza(extrair_dados(linhas[indice_natureza]).upper())
  dados_advogado = extrair_dados_advogado(linhas[indice_advogado], dados['processo'])
  documento = extrair_documento_e_email(linhas[indice_documento])
  dados['data_nascimento'] = extrair_dados(linhas[indice_data_nascimento]) if indice_data_nascimento is not None else ''

  dados_gerais = dados | natureza | dados_advogado | documento | dados_xml
  enviar_dados(dados_gerais, arquivo_pdf)
  
def extrair_dados(texto):
  valor = texto.split(':')[1]
  if 'R$' in valor:
    valor = valor.replace('R$','').replace('.','').replace(',','.')
  return  valor.replace('\n','').strip()

def extrair_dados_advogado(texto, processo):
  texto_dividido = texto.split('-')
  advogado = texto_dividido[0].split(':')[1]
  oab = texto_dividido[1].split(':')[1][3:].strip()
  if oab[0] == '0':
      oab = oab[1:]
  seccional = texto_dividido[1].split(':')[1][:3].strip()
  documento = texto_dividido[2].split(':')[1].replace('\n','').strip()
  dados_advogado = login_cna(oab, seccional, documento, advogado, processo)
  return dados_advogado

def extrair_documento_e_email(texto):
  if 'Email' in texto:
    texto_dividido = texto.replace('\n','').split(':')
    documento = texto_dividido[1].replace('Email', '').strip()
    email = texto_dividido[2].strip()
    dados = {'email': email, 'documento': documento}
  else:
    texto_dividido = texto.split(':')
    documento = texto_dividido[1].strip()
    dados = {'documento': documento}
  return dados

def enviar_dados(arquivo_pdf, dados):
  documento = dados['documento']
  site = dados['site']
  dados['processo_origem'] = dados['processo_origem'][0]

  atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento'], 'estado': dados['estado'], 'tipo': 'credor'})
  id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
  dados['id_sistema_arteria'] = id_sistema_arteria
  atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
  atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])
  log(dados['processo'], 'Sucesso', site, 'Precatório registrado com sucesso',dados['estado'], dados['tribunal'])
  atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})
  
ler_documento({}, './arquivos_pdf_santa_catarina/1_INIC1 (1).pdf')