import os
import re
import traceback
from logs import log
from cna_oab import login_cna
from eproc_ import login_eproc
from dotenv import load_dotenv
from rotina_acre import ler_documentos
from banco_de_dados import atualizar_ou_inserir_situacao_cadastro, consultar_processos
from funcoes_arteria import enviar_valores_oficio_arteria
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados
from auxiliares import  encontrar_indice_linha, formatar_data_padra_arteria, identificar_estados, ler_arquivo_pdf_transformar_em_txt, mandar_dados_regex, limpar_dados, tipo_precatorio, verificar_tribunal_lista

load_dotenv('.env')

def buscar_dados_tribunal_regional_federal():     
  trfs = ['.4.02.', '.4.04.','8.08.', '.8.16.', '.8.19', '.8.21.', '.8.24.']
  for trf in trfs:
    dados = consultar_processos(f'{trf}')
    for d in dados:
          dados_limpos = limpar_dados(d)
          tipo = tipo_precatorio(d)
          processo_origem = verificar_tribunal_lista(d['processo_origem'])
          dado = dados_limpos | tipo
          dado['processo_origem'] = processo_origem
          if dado['processo_origem'] != []:
            ler_documentos(dado)
          else:
            pass

def ler_documentos(dados_xml):
    try:
      login_trf = 'DF018283'
      codigos_trf4 = ['.4.04', '.8.16.', '.8.21.', '.8.24.']
      codigos_trf2 = ['.4.02','.8.04.','.8.19.']
      processo_origem = dados_xml['processo']
      if any(s in processo_origem for s in codigos_trf4):
        site = 'https://eproc.trf4.jus.br/eproc2trf4'
        tribunal = 'trf4'
        senha = 'Costaesilva4*'
      elif any(s in processo_origem for s in codigos_trf2):
        site = 'https://eproc.trf2.jus.br/eproc'
        tribunal = 'trf2'
        senha = os.getenv('senha_trf2')

      for processo_origem in dados_xml['processo_origem']:
        processo_origem = processo_origem.replace('-','').replace('.','')
        arquivo_pdf, id_documento = login_eproc(login_trf,senha,site, processo_origem)

        if arquivo_pdf != '':
            arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
            dados_complementares = { 'site': site, 'id_documento': id_documento, 'codigo_processo': id_documento, 'tipo': 'FEDERAL', 'cidade': '', 'tribunal': tribunal}  | dados_xml
            
            extrair_dados_txt(arquivo_pdf, arquivo_txt, dados_complementares)            
    except Exception as e:
        print( f'Erro: {str(e)} |', 'Processo ->> ', f'{dados_xml["processo"]}'.replace('\n', ''))
        print(traceback.print_exc())
        pass
    
def extrair_dados_txt(arquivo_pdf, arquivo_txt, dados_xml):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    
    indice_processo = encontrar_indice_linha(linhas, 'processo :')
    indice_processo_origem = encontrar_indice_linha(linhas, 'originário')
    indice_vara = encontrar_indice_linha(linhas, 'deprecante')
    indice_credor = encontrar_indice_linha(linhas, 'requerente')
    indice_devedor = encontrar_indice_linha(linhas, 'requerido')
    indice_advogado = encontrar_indice_linha(linhas,'advogado')
    indice_natureza = encontrar_indice_linha(linhas,'tipo de despesa')
    indice_data_expedicao = encontrar_indice_linha(linhas,'data:')
    indice_documento = encontrar_indice_linha(linhas, 'cpf/cgc')
    indice_valor_principal = encontrar_indice_linha(linhas, 'valor principal')
    indice_valor_atualizado = encontrar_indice_linha(linhas, 'valor atualizado')
    indice_valor_juros = encontrar_indice_linha(linhas, 'valor juros')
    indice_valor_global = encontrar_indice_linha(linhas, 'da requisição')
    if indice_valor_principal == None:
        indice_valor_principal = indice_valor_atualizado
    indices = {'indice_credor': indice_credor,'indice_devedor': indice_devedor, 'indice_natureza': indice_natureza, 'indice_documento': indice_documento, 'indice_valor_juros': indice_valor_juros,  'indice_valor_principal': indice_valor_principal}
    dados = mandar_dados_regex(indices, linhas)
    
    dados['data_nascimento'] = ''
    dados['data_expedicao'] = extrair_data_expedicao(linhas[indice_data_expedicao])
    dados_xml['vara'] = linhas[indice_vara].upper().replace(':', '').replace('DEPRECANTE', '').strip()
    dados['valor_global'] = linhas[indice_valor_global].split(':')[1].strip().replace('.','').replace(',','.')
    dados_xml['processo_origem'] = linhas[indice_processo_origem].split(':')[1].split('/')[0].strip()
    dados_xml['processo'] = linhas[indice_processo].split(':')[1].split('/')[0].strip()
    estado = identificar_estados(linhas[indice_processo_origem].split(':')[1].split('/')[1].strip())
    if indice_advogado:
      dados_advogado = extrair_dados_advogado(linhas[indice_advogado], dados_xml['processo'])
    else:
      dados_advogado = {'telefone': '', 'advogado': '', 'seccional': '', 'oab': ''}

    dados = dados |  dados_advogado | dados_xml | estado
    print(dados)
    enviar_dados(dados, arquivo_pdf)

def extrair_data_expedicao(texto):
  padrao = r'\d{2}/\d{2}/\d{4}'
  resultado = re.findall(padrao, texto)
  if resultado != []:
    data_padrao_arteria = formatar_data_padra_arteria(resultado[0])
    return data_padrao_arteria
  else:
    return ''
  
def extrair_dados_advogado(texto, processo):
    texto_dividido = texto.replace('\n','').split('-')
    advogado = texto_dividido[0].upper().replace('ADVOGADO','').replace(':','').strip()
    oab = texto_dividido[1][3:].strip()
    if oab[0] == '0':
      oab = oab[1:]
    seccional = texto_dividido[1][:3].strip()
    dados = login_cna(oab, seccional, '', advogado, processo)
    return dados

def enviar_dados(dados, arquivo_pdf):
  documento = dados['documento']
  site = dados['site']

  atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento'], 'estado': dados['estado'], 'tipo': 'credor'})
  id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
  dados['id_sistema_arteria'] = id_sistema_arteria
  atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
  atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])
  log(dados['processo'], 'Sucesso', site, 'Precatório registrado com sucesso',dados['estado'], dados['tribunal'])
  atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})
