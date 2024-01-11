import re
from logs import log
from cna_oab import login_cna
from eproc_ import login_eproc
from funcoes_arteria import enviar_valores_oficio_arteria
from auxiliares import  encontrar_data_expedicao_e_cidade_tjac, encontrar_indice_linha, formatar_data_padra_arteria, limpar_dados, mascara_processo, tipo_de_natureza, ler_arquivo_pdf_transformar_em_txt
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro, consultar_processos, precatorio_exitente_arteria
from rotina_rio_de_janeiro import extrair_cidade_data_expedicao

def buscar_dados_tribunal_santa_catarina():     
    dados = consultar_processos('.8.24.')
    for d in dados:
          dado = limpar_dados(d)
          ler_documento(dado)
        
def ler_documento(dados_xml):
  login_trf = 'DF018283'
  senha = 'Costaesilva33*'
  site = 'https://eproc2g.tjsc.jus.br/eproc'
  processo = dados_xml['processo'].replace('.','').replace('-','')

  arquivo_pdf, id_documento = login_eproc(login_trf,senha,site, processo, '')
  if arquivo_pdf:
    arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
    dados_xml['tribunal'] = 'TJSC'
    dados = dados_xml | {'site': 'site', 'tipo': 'ESTADUAL', 'id_documento': id_documento, 'codigo_processo': id_documento}

    extrair_dados_arquivo(arquivo_pdf, arquivo_txt, dados)

def extrair_dados_arquivo(arquivo_pdf, arquivo_txt, dados_xml):
  with open(arquivo_txt, 'r', encoding='utf-8') as f:
    linhas = f.readlines()
  dados = {}
  indice_estado = 0
  indice_processo_origem = encontrar_indice_linha(linhas, 'número do processo')
  indice_advogado = encontrar_indice_linha(linhas, "procurador do autor")
  indice_credor = encontrar_indice_linha(linhas, 'beneficiário do crédito')
  indice_devedor = encontrar_indice_linha(linhas, 'parte passiva')
  indice_data_expedicao = encontrar_indice_linha(linhas, 'data de intimação das partes sobre valor e expedição desta requisição de precatório')
  indice_data_nascimento = encontrar_indice_linha(linhas, 'data de nascimento')
  indice_natureza = encontrar_indice_linha(linhas, 'natureza do crédito')
  indice_documento = encontrar_indice_linha(linhas, 'cpf/cnpj')
  indice_valor_principal = encontrar_indice_linha(linhas, 'valor corrigido')
  indice_valor_juros_moratorio = encontrar_indice_linha(linhas, 'valor dos juros moratórios')
  indice_valor_juros_compensatorio = encontrar_indice_linha(linhas, 'valor dos juros compensatórios')
  indice_valor_global = encontrar_indice_linha(linhas, 'valor total da requisição')
  indice_cidade = encontrar_indice_linha(linhas, 'presente documento')
  processo_origem = extrair_dados(linhas[indice_processo_origem])
  dados_xml['processo_origem'] = mascara_processo(processo_origem)
  
  cidade_data_expedicao = encontrar_data_expedicao_e_cidade_tjac(linhas[indice_cidade + 2])
  if cidade_data_expedicao == {'cidade': '', 'data_expedicao': ''}:
    cidade_data_expedicao = encontrar_data_expedicao_e_cidade_tjac(linhas[indice_cidade + 1])
  dados['cidade'] = cidade_data_expedicao['cidade']
  
  dados['estado'] = linhas[indice_estado].replace('\n', '').replace('ESTADO DE','').strip()
  dados['credor'] = extrair_dados(linhas[indice_credor])
  dados['devedor'] = extrair_dados(linhas[indice_devedor])
  data_expedicao = extrair_dados(linhas[indice_data_expedicao])
  dados['data_expedicao'] = formatar_data_padra_arteria(data_expedicao)
  if indice_data_nascimento:
    dados['data_nascimento'] = extrair_data_nascimento(linhas[indice_data_nascimento])
  else:
    dados['data_nascimento'] = ''
  dados['valor_principal'] = extrair_dados(linhas[indice_valor_principal])
  dados['valor_global'] = extrair_dados(linhas[indice_valor_global])
  juros_moratorio = extrair_dados(linhas[indice_valor_juros_moratorio])
  juros_compensatorio = extrair_dados(linhas[indice_valor_juros_compensatorio])
  juros = float(juros_moratorio) + float(juros_compensatorio)
  dados['valor_juros'] = str(juros)

  natureza = tipo_de_natureza(extrair_dados(linhas[indice_natureza]).upper())
  dados_advogado = extrair_dados_advogado(linhas[indice_advogado], dados_xml['processo'])
  documento = extrair_documento_e_email(linhas[indice_documento])

  dados_gerais = dados | natureza | dados_advogado | documento | dados_xml
  enviar_dados(arquivo_pdf, dados_gerais)

def extrair_dados(texto):
  valor = texto.split(':')[1]
  if 'R$' in valor:
    valor = valor.replace('R$','').replace('.','').replace(',','.')
  return  valor.replace('\n','').strip()

def extrair_data_nascimento(texto):
  data = ''
  padrao = r'\b(?:\d{1,2}\/\d{1,2}\/\d{4}|\d{4}\/\d{1,2}\/\d{1,2}|\d{1,2}\-\d{1,2}\-\d{4}|\d{4}\-\d{1,2}\-\d{1,2})\b'
  nascimento = re.search(padrao, texto)
  if nascimento:
    data = formatar_data_padra_arteria(nascimento.group(0))
  return data

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
  print(dados)
  documento = dados['documento']
  site = dados['site']
  dados['processo_origem'] = dados['processo_origem']
  atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento'], 'estado': dados['estado'], 'tipo': 'credor'})
  
  existe_id_sistema_arteria = precatorio_exitente_arteria(dados['processo'])
  if existe_id_sistema_arteria:
    dados['id_sistema_arteria'] = existe_id_sistema_arteria[0]
    enviar_valores_oficio_arteria(arquivo_pdf, dados, existe_id_sistema_arteria[0])
    mensagem = 'Precatório alterado com sucesso'
  else:
    dados['id_sistema_arteria']  = enviar_valores_oficio_arteria(arquivo_pdf, dados)
    mensagem = 'Precatório registrado com sucesso'

  atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
  atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])
  log(dados['processo'], 'Sucesso', site, mensagem ,dados['estado'], dados['tribunal'])
  atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})
  

