import re
from logs import log
from cna_oab import login_cna
from funcoes_arteria import enviar_valores_oficio_arteria
from auxiliares import encontrar_indice_linha, formatar_data_padra_arteria, ler_arquivo_pdf_transformar_em_txt, limpar_dados, verificar_tribunal
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro, consultar_processos, precatorio_exitente_arteria

def buscar_dados_pje_bahia():     
  dados = consultar_processos('.8.05.')
  for d in dados:
        dado = limpar_dados(d)
        if verificar_tribunal(d['processo']):
          ler_documentos(dado)
      
def ler_documentos(dados):
  pass

def extrair_dados_txt(arquivo_pdf):
  arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
  with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    
  
  dados = {
    'vara': pegar_valor(linhas[encontrar_indice_linha(linhas, 'órgão julgador')]),
    'credor': pegar_valor(linhas[encontrar_indice_linha(linhas, 'parte credora:')]),
    'devedor': pegar_valor(linhas[encontrar_indice_linha(linhas, 'ente devedor:')]), 
    'advogado': pegar_valor(linhas[encontrar_indice_linha(linhas, 'advogado(a)(s):')]),
    'telefone': pegar_telefone_advogado(linhas[encontrar_indice_linha(linhas, 'telefone: ')]),
    'documento_advogado': pegar_valor(linhas[encontrar_indice_linha(linhas, 'advogado(a)(s):') + 1]),
    'data_expedicao': pegar_data_expedicao(linhas[encontrar_indice_linha(linhas, 'assinado eletronicamente por:')]),
    'valor_juros': pegar_valor(linhas[encontrar_indice_linha(linhas, 'juros')]).replace('.','').replace(',','.').strip(),
    'valor_principal': pegar_valor(linhas[encontrar_indice_linha(linhas, 'valor da causa')]).replace('.','').replace(',','.').strip(),
    'valor_global': pegar_valor(linhas[encontrar_indice_linha(linhas, 'valor total requisitado')]).replace('.','').replace(',','.').strip()
  }
  
  oab_e_seccional = pegar_valor(linhas[encontrar_indice_linha(linhas, 'advogado(a)(s):') + 2])
  dados['oab'], dados['seccional'] = pegar_oab_e_seccional(oab_e_seccional)
  dados['cidade'] = pegar_cidade(linhas[encontrar_indice_linha(linhas, 'servidor autorizado, digitei')])
  dados['documento'], dados['data_nascimento'] = pegar_documento_e_data_nascimento(linhas[encontrar_indice_linha(linhas, 'cpf/cnpj')])

  enviar_dados_banco_de_dados_e_arteria(arquivo_pdf, dados)

def pegar_valor(string):
  valor = string.split(':')[1].replace('\n', '').replace('R$','').strip()
  return valor

def pegar_data_expedicao(string):
  data = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
  resposta = data.search(string)
  data_expedicao = formatar_data_padra_arteria(resposta.group(1))
  return data_expedicao

def pegar_telefone_advogado(string):
  telefone = string.split('Telefone: ')[1].replace('\n','').strip()
  return telefone

def pegar_oab_e_seccional(string):
  string = string.split('/')
  oab = string[0]
  seccional = string[1]
  return oab, seccional

def pegar_cidade(string):
  cidade = string.split('.')[1].split(',')[0].split('/')[0].strip()
  return cidade

def pegar_documento_e_data_nascimento(string):
  string = string.split('CPF/CNPJ: ')[1]
  documento = string.split(' ')[0].strip()
  data_nascimento = formatar_data_padra_arteria(string.split(': ')[1].strip())
  return documento, data_nascimento

def enviar_dados_banco_de_dados_e_arteria(arquivo_pdf, dados):    
    documento = dados['documento']
    site = dados['site']
    pegar_advogado_e_oab(dados['advogado'], dados['documento_advogado'], dados['oab'] ,dados['seccional'], dados['processo'])

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

def pegar_advogado_e_oab(advogado, documento, oab ,seccional, processo):
  if oab and seccional:
    login_cna(oab, seccional, documento, advogado, processo)

# extrair_dados_txt('../../Downloads/Ofício.pdf')