import re
from logs import log
from cna_oab import login_cna
from funcoes_arteria import enviar_valores_oficio_arteria
from auxiliares import encontrar_indice_linha, formatar_data_padrao_arteria, ler_arquivo_pdf_transformar_em_txt
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro, precatorio_existente_arteria


def ler_e_transformar_em_txt(arquivo_pdf):
  arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
  with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()
  return linhas

def extrair_dados_arquivo_txt(dados_xml):
  linhas = ler_e_transformar_em_txt(dados_xml['arquivo_pdf'])
  e_precatorio = pegar_valores(linhas[encontrar_indice_linha(linhas, 'modalidade de requisição')])
  
  if e_precatorio == 'Precatório':
    vara = linhas[encontrar_indice_linha(linhas, 'órgão julgador')].split('-')[-1]
    complemento_vara = linhas[encontrar_indice_linha(linhas, 'órgão julgador') + 1]
    vara = vara + complemento_vara

    valor_principal = pegar_valores(linhas[encontrar_indice_linha(linhas, 'principal corrigido')]).split(' ')[0]
    valor_juros = pegar_valores(linhas[encontrar_indice_linha(linhas, 'principal corrigido')]).split(':')[1] if pegar_valores(linhas[encontrar_indice_linha(linhas, 'principal corrigido')]).split(':')[1] != '' else '0,00'
    advogado = pegar_valores(linhas[encontrar_indice_linha(linhas, 'advogado (a)')])
    oab = pegar_valores(linhas[encontrar_indice_linha(linhas, 'oab')]).split('/')[0]
    seccional = pegar_valores(linhas[encontrar_indice_linha(linhas, 'oab')]).split('/')[1]
    dados_advogado = login_cna(oab, seccional, '', advogado, dados_xml['processo'])
    
    dados = {
    'vara': vara.replace('\n','').strip(),
    'processo_origem': pegar_valores(linhas[encontrar_indice_linha(linhas, 'conhecimento')]),
    'processo': pegar_valores(linhas[encontrar_indice_linha(linhas, 'número:')]).replace('Nº.', ''),
    'credor': pegar_valores(linhas[encontrar_indice_linha(linhas, 'autor')]),
    'valor_global': pegar_valores(linhas[encontrar_indice_linha(linhas, 'valor da causa')]),
    'devedor': pegar_valores(linhas[encontrar_indice_linha(linhas, 'ente devedor')]),
    'natureza': pegar_valores(linhas[encontrar_indice_linha(linhas, 'natureza do crédito')]).replace('Data de', ''),
    'documento': pegar_valores(linhas[encontrar_indice_linha(linhas, 'cpf')]).replace('Data de', ''),
    'data_nascimento': formatar_data_padrao_arteria(pegar_valores(linhas[encontrar_indice_linha(linhas, 'nascimento:')])),
    'data_expedicao': pegar_data_expedicao(pegar_valores(linhas[encontrar_indice_linha(linhas, 'assinado eletronicamente')])), 
    'valor_principal': valor_principal.replace('.','').replace(',','.').strip(),
    'vslor_juros': valor_juros.replace('.','').replace(',','.').strip(),
  } | dados_advogado

    enviar_dados_banco_de_dados_e_arteria(dados_xml['arquivo_pdf'], dados)

def pegar_valores(string):
  valor = string.split(':',1)[1].replace('R$','').replace('\n','').strip()
  return valor

def pegar_data_expedicao(string):
  data = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
  resposta = data.search(string)
  data_expedicao = formatar_data_padrao_arteria(resposta.group(1))
  return data_expedicao

def enviar_dados_banco_de_dados_e_arteria(arquivo_pdf, dados):    
    documento = dados['documento']
    site = dados['site']

    atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento'], 'estado': dados['estado'], 'tipo': 'credor'})
    existe_id_sistema_arteria = precatorio_existente_arteria(dados['processo'])
    if existe_id_sistema_arteria:
      dados['id_sistema_arteria'] = existe_id_sistema_arteria[0]
      enviar_valores_oficio_arteria(arquivo_pdf, dados, existe_id_sistema_arteria[0])
      mensagem = 'Precatório alterado com sucesso'
    else:
      dados['id_sistema_arteria']  = enviar_valores_oficio_arteria(arquivo_pdf, dados)
      mensagem = 'Precatório registrado com sucesso'

    atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
    atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])
    log(dados['processo_origem'], 'Sucesso', site, mensagem ,dados['estado'], dados['tribunal'])
    atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})

extrair_dados_arquivo_txt('arquivos_pdf_espirito_santo_pje/Ofício (3).pdf')