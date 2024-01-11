import re
import traceback
from logs import log
from cna_oab import login_cna
from funcoes_arteria import enviar_valores_oficio_arteria
from tribunal_justica_rio_de_janeiro import get_docs_oficio_precatorio_tjrj
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro, consultar_processos, precatorio_exitente_arteria
from auxiliares import encontrar_indice_linha, formatar_data_padra_arteria, ler_arquivo_pdf_transformar_em_txt, limpar_dados, tipo_de_natureza,  verificar_tribunal

def buscar_dados_tribunal_rio_de_janeiro():     
  dados = consultar_processos('.8.19.')
  for d in dados:
        dado = limpar_dados(d)
        if verificar_tribunal(d['processo']):
          ler_documentos(dado)
        else:
          continue

def verificar_tribunal(n_processo):
  padrao = r'\d{2,4}|\d{7}-\d{2}.\d{4}.8.19.\d{4}'
  processo = re.search(padrao, n_processo)
  if processo != None:
    return True
  
def ler_documentos(dado_xml):
    try:
      processo_geral = dado_xml['processo']
      arquivo_pdf, codigo_documento, num_processo = get_docs_oficio_precatorio_tjrj(processo_geral)
      if arquivo_pdf:
        arquivo_pdf = f'arquivos_pdf_rio_de_janeiro/{arquivo_pdf[0]}'
        arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
        dados_complementares = {"processo_geral": processo_geral, "codigo_processo": codigo_documento, 'site': 'https://www.tjrj.jus.br', 'id_documento': num_processo, 'estado': 'RIO DE JANEIRO', 'tipo':'ESTADUAL'} | dado_xml
        extrair_dados_txt(arquivo_txt, dados_complementares, arquivo_pdf)
      else:
        log(processo_geral, 'Fracasso', 'https://www.tjrj.jus.br', 'Não há ofício requisitório no processo', 'Rio de Janeiro', dado_xml['tribunal'])
        atualizar_ou_inserir_situacao_cadastro(processo_geral,{'status': 'Fracasso'})
    except Exception as e:
        print(f"Erro no processo ---> {processo_geral}", f'Erro: {e}')
        print(traceback.print_exc())
    
def extrair_dados_txt(arquivo_txt, dados_pdf, arquivo_pdf):
  novas_linhas = []
  with open(arquivo_txt, 'r',encoding='utf-8') as f:
    linhas = f.readlines()
  for linha in linhas:
    novas_linhas.append(linha.replace('\xa0', ' ').replace('\n',''))
  
  dados = {}
  indices_processo_origem = encontrar_indice_linha(novas_linhas, 'processo de conhecimento')
  indice_natureza = encontrar_indice_linha(novas_linhas, 'natureza:')
  indice_devedor = encontrar_indice_linha(novas_linhas, 'entidade executada')
  indice_credor = encontrar_indice_linha(novas_linhas, 'beneficiário')
  indice_valor_principal = encontrar_indice_linha(novas_linhas, 'valor do principal')
  indice_valor_juros = encontrar_indice_linha(novas_linhas, 'valor dos juros')
  indice_valor_global = encontrar_indice_linha(novas_linhas, 'valor bruto')
  indice_advogado = encontrar_indice_linha(novas_linhas, 'advogado do beneficiário')
  indice_data_nascimento = encontrar_indice_linha(novas_linhas, 'nascimento do beneficiário')
  indice_data_expedicao = encontrar_indice_linha(novas_linhas, 'habilitados')    
  
  if indice_devedor and indice_credor:
    dados_pdf['processo'] = dados_pdf['id_documento']
    dados['devedor'] = extrair_devedor(novas_linhas, indice_devedor)
    
    credor, documento = extrair_credor_e_documento(novas_linhas, indice_credor)
    dados['credor'] = credor
    dados['documento'] = documento
      
    natureza = pegar_valor(novas_linhas[indice_natureza])
    natureza = tipo_de_natureza(natureza)

    dados_advogado = extrair_dados_advogado(novas_linhas, indice_advogado, dados_pdf['processo'])

    dados['valor_global'] = pegar_valor(novas_linhas[indice_valor_global]).replace('.','').replace(',','.').strip()
    dados['valor_principal'] = pegar_valor(novas_linhas[indice_valor_principal]).replace('.','').replace(',','.').strip()
    dados['valor_juros'] = pegar_valor(novas_linhas[indice_valor_juros]).replace('.','').replace(',','.').strip()
    dados_pdf['processo_origem'] = pegar_valor(novas_linhas[indices_processo_origem])
    

    if indice_data_nascimento:
      data_nascimento = pegar_valor(novas_linhas[indice_data_nascimento])
      dados['data_nascimento'] = formatar_data_padra_arteria(data_nascimento)
    else:
      dados['data_nascimento'] = ''

    cidade, data_expedicao = extrair_cidade_data_expedicao(novas_linhas, indice_data_expedicao)
    dados['cidade'] = cidade
    dados['data_expedicao'] = data_expedicao

    dados = dados | dados_pdf | dados_advogado | natureza
    enviar_dados_banco_de_dados_e_arteria(arquivo_pdf, dados)
    

def pegar_valor(string):
  valor = string.split(':')[1].replace('\n', '').replace('R$','').strip()
  return valor

def extrair_credor_e_documento(novas_linhas, indice_credor):
  palavras_credor = ['\n', 'BENEFICIÁRIO']
  if any(credor in novas_linhas[indice_credor] for credor in palavras_credor):
    if 'nome' in novas_linhas[indice_credor + 1].lower():
      credor = pegar_valor(novas_linhas[indice_credor + 1])
      documento = pegar_valor(novas_linhas[indice_credor + 2])
    elif 'nome' in novas_linhas[indice_credor + 2].lower():
      credor = pegar_valor(novas_linhas[indice_credor + 2])      
      documento = pegar_valor(novas_linhas[indice_credor + 3])

  return credor, documento

def extrair_devedor(novas_linhas, indice_devedor):
  palavras_devedor = ['\n', 'ENTIDADE', 'EXECUTADA']
  if any(devedor in novas_linhas[indice_devedor] for devedor in palavras_devedor):
    if 'nome' in novas_linhas[indice_devedor + 1].lower():
      devedor = pegar_valor(novas_linhas[indice_devedor + 1])
    elif 'nome' in novas_linhas[indice_devedor + 2].lower():
      devedor = pegar_valor(novas_linhas[indice_devedor + 2])
  return devedor

def extrair_dados_advogado(novas_linhas, indice_advogado, processo):
  dados_advogado = {'telefone': '', 'advogado': '', 'seccional': '', 'oab': ''}
  if indice_advogado:
    linhas_advogado = [novas_linhas[indice_advogado + i].lower().replace('\n','').strip() for i in range(3)]
    if 'nome:  - não há' not in linhas_advogado:
      palavras_advogado = ['\n', 'ADVOGADO', 'BENEFICIÁRIO']
      if any(advogado in novas_linhas[indice_advogado] for advogado in palavras_advogado):
        if 'nome' in novas_linhas[indice_advogado + 1].lower():
          string_completa = novas_linhas[indice_advogado + 1].split('-')
          advogado = string_completa[1].replace('\n', '').strip()
          oab, seccional = extrair_oab_e_seccional(string_completa[0])
          documento_advogado= pegar_valor(novas_linhas[indice_advogado + 2])
          dados_advogado = login_cna(oab, seccional, documento_advogado, advogado, processo)
        elif 'nome' in novas_linhas[indice_advogado + 2].lower():
          string_completa = novas_linhas[indice_advogado + 2].split('-')
          advogado = string_completa[1].replace('\n', '').strip()
          oab, seccional = extrair_oab_e_seccional(string_completa[0])
          documento_advogado = pegar_valor(novas_linhas[indice_advogado + 3])
          dados_advogado = login_cna(oab, seccional, documento_advogado, advogado, processo)
  return dados_advogado
      
def extrair_oab_e_seccional(texto):
  oab_seccional = pegar_valor(texto) 
  oab = oab_seccional[2:]
  if oab[0] == '0' and oab[1] == '0':
    oab = oab[2:]
  elif oab[0] == '0' and oab[1] != '0':
    oab = oab[1:]
  seccional = oab_seccional[:2]

  return oab, seccional

def extrair_cidade_data_expedicao(novas_linhas, indice_data_expedicao):
  if data_expedicao != ' ' or indice_data_expedicao:
    cidade_data_expedicao = data_expedicao.split(',')
    cidade = cidade_data_expedicao[0].strip()
    data_expedicao = formatar_data_padra_arteria(cidade_data_expedicao[1].replace('.','').strip())
  elif 'herdeiros' in novas_linhas[indice_data_expedicao + 5] or 'herdeiros' in novas_linhas[indice_data_expedicao + 4]:
    cidade = ''
    data_expedicao = ''
  else:
    data_expedicao = novas_linhas[indice_data_expedicao + 4]
    cidade_data_expedicao = data_expedicao.split(',')
    cidade = cidade_data_expedicao[0].strip()
    data_expedicao = formatar_data_padra_arteria(cidade_data_expedicao[1].replace('.','').strip())
  
  return cidade, data_expedicao

def enviar_dados_banco_de_dados_e_arteria(arquivo_pdf, dados):    
    documento = dados['documento']
    site = dados['site']
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
    log( dados['processo_origem'], 'Sucesso', site, mensagem ,dados['estado'], dados['tribunal'])
    atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})

