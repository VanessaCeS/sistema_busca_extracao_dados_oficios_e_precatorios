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
from auxiliares import  encontrar_indice_linha, formatar_data_padrao_arteria, identificar_estados, ler_arquivo_pdf_transformar_em_txt,  limpar_dados, mandar_dados_regex, tipo_precatorio, verificar_tribunal_lista

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
            dados_complementares = { 'site': site, 'id_documento': id_documento, 'codigo_processo': id_documento, 'tipo': 'FEDERAL', 'cidade': '', 'tribunal': tribunal}  | dados_xml
            
            extrair_dados_txt(arquivo_pdf, dados_complementares)            
    except Exception as e:
        print( f'Erro: {str(e)} |', 'Processo ->> ', f'{dados_xml["processo"]}'.replace('\n', ''))
        print(traceback.print_exc())
        pass
    
def extrair_dados_txt(arquivo_pdf, dados_xml):
    arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    

    valor_principal = pegar_valor(linhas[encontrar_indice_linha(linhas, 'valor principal')]) if encontrar_indice_linha(linhas, 'valor principal') else pegar_valor(linhas[encontrar_indice_linha(linhas, 'valor atualizado')])
    match = re.search(r'\b\d+(?:\.\d{1,3})?(?:,\d{1,2})?\b', linhas[encontrar_indice_linha(linhas, 'valor juros')])
    valor_juros = match.group().replace('.','').replace(',','.') if match else ''
    estado = identificar_estados(pegar_valor(linhas[encontrar_indice_linha(linhas, 'originário')]).split('/')[1].strip())
    dict_natureza = mandar_dados_regex({'indice_natureza': encontrar_indice_linha(linhas,'tipo de despesa')}, linhas)
    dados_advogado = extrair_dados_advogado(linhas[encontrar_indice_linha(linhas,'advogado')], dados_xml['processo']) if encontrar_indice_linha(linhas,'advogado') else {'telefone': '', 'advogado': '', 'seccional': '', 'oab': ''}
    dados = {
      'natureza': dict_natureza['natureza'],
      'estado': estado,
      'data_nascimento': '',
      'vara': linhas[encontrar_indice_linha(linhas, 'deprecante')].replace(': DEPRECANTE', '').strip(),
      'valor_principal': valor_principal.strip().replace('.','').replace(',','.'), 
      'devedor': pegar_valor(linhas[encontrar_indice_linha(linhas, 'requerido')]),
      'documento': pegar_valor(linhas[encontrar_indice_linha(linhas, 'cpf/cgc')]).replace('\n',''),
      'credor': pegar_valor(linhas[encontrar_indice_linha(linhas, 'requerente')]),
      'processo': pegar_valor(linhas[encontrar_indice_linha(linhas, 'processo :')]),
      'processo_origem': pegar_valor(linhas[encontrar_indice_linha(linhas, 'originário')]).split('/')[0],
      'data_expedicao': formatar_data_padrao_arteria(pegar_valor(linhas[encontrar_indice_linha(linhas,'data:')])),
      'valor_juros': valor_juros,      
      'valor_global': pegar_valor(linhas[encontrar_indice_linha(linhas, 'da requisição')]).replace('.','').replace(',','.')
      } |  dados_advogado | dados_xml
    
    enviar_dados(dados, arquivo_pdf)

def pegar_valor(string):
  if ':' in string:
    valor = string.split(':')[1].replace('\n', '').strip() 
  else:
    valores = string.split(' ', 3)
    valor = valores[2] if len(valores) == 4 else valores[-1]
  return valor

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

extrair_dados_txt('arquivos_pdf_trf4/50261140420204049388_trf4.pdf', {'tribunal': 'trf2'})