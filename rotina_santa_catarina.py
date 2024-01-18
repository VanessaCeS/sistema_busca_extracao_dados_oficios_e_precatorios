from logs import log
from cna_oab import login_cna
from eproc_ import login_eproc
from funcoes_arteria import enviar_valores_oficio_arteria
from auxiliares import  encontrar_indice_linha, extrair_valor_txt, formatar_data_padra_arteria, limpar_dados, tipo_de_natureza, ler_arquivo_pdf_transformar_em_txt, tipo_precatorio, transformar_pdf_em_txt, transformar_valor_monetario_padrao_arteria
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

  extrair_dados_pdf(arquivo_pdf,  dados)

def extrair_dados_pdf(arquivo_pdf, dados_xml):
  linhas = transformar_pdf_em_txt(arquivo_pdf)

  documento, email = extrair_documento_e_email(linhas[encontrar_indice_linha(linhas, 'cpf/cnpj')])
  natureza = tipo_de_natureza(extrair_valor_txt(linhas[encontrar_indice_linha(linhas, 'natureza do crédito')]))
  processo = extrair_valor_txt(linhas[encontrar_indice_linha(linhas, 'número do processo')])
  dados_advogado = extrair_dados_advogado(linhas[encontrar_indice_linha(linhas, "procurador do autor")], processo)

  dados = {
    'email': email,
    'processo': processo,
    'natureza': natureza,
    'documento': documento,
    'estado': 'SANTA CATARINA',
    'credor': extrair_valor_txt(linhas[encontrar_indice_linha(linhas, 'beneficiário do crédito')]),
    'devedor': extrair_valor_txt(linhas[encontrar_indice_linha(linhas, 'parte passiva')]),
    'data_expedicao': formatar_data_padra_arteria(extrair_valor_txt(linhas[encontrar_indice_linha(linhas, 'data de intimação das partes sobre valor e expedição desta requisição de precatório')])),    
    'valor_principal': transformar_valor_monetario_padrao_arteria(extrair_valor_txt(linhas[encontrar_indice_linha(linhas, 'valor corrigido')])),
    'valor_juros': transformar_valor_monetario_padrao_arteria(extrair_valor_txt(linhas[encontrar_indice_linha(linhas, 'valor dos juros moratórios')])),
    'valor_global': transformar_valor_monetario_padrao_arteria(extrair_valor_txt(linhas[encontrar_indice_linha(linhas, 'valor total da requisição')])),
    'data_nascimento': formatar_data_padra_arteria(extrair_data_nascimento(linhas[encontrar_indice_linha(linhas, 'data de nascimento')])) if encontrar_indice_linha(linhas, 'data de nascimento') else ''
  } | dados_advogado

  enviar_dados(arquivo_pdf, dados)

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
  documento = ''
  email = ''
  if 'Email' in texto:
    texto_dividido = texto.replace('\n','').split(':')
    documento = texto_dividido[1].replace('Email', '').strip()
    email = texto_dividido[2].strip()
  else:
    texto_dividido = texto.split(':')
    documento = texto_dividido[1].strip()

  return documento, email

def extrair_data_nascimento(string):
  return string.split('nascimento:')[1].replace('\n','').strip()

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

extrair_dados_pdf('arquivos_pdf_santa_catarina/1_INIC1 (18).pdf', {'tribunal': 'tjsc'})
