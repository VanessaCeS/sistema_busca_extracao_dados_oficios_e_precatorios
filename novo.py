import re
import PyPDF2
import xmltodict
import traceback
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados
from funcoes_arteria import enviar_valores_oficio_arteria
from utils import  mandar_documento_para_ocr, encontrar_indice_linha, mandar_dados_regex

def ler_documentos(arquivo_pdf, dados):
      try:
          processo_geral = dados['processo']
          dados = dados | {'valor_juros': '', 'valor_principal': ''}
          arquivo_txt = mandar_documento_para_ocr(arquivo_pdf, '1', processo_geral)
          extrair_dados_texto_ocr(arquivo_pdf, dados, arquivo_txt)
      except Exception as e:
        print("Erro no processo -> ", f'Erro: {e}')
        print(traceback.print_exc())
        pass

def extrair_dados_texto_ocr(arquivo_pdf, dados_xml, arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
    indice_credor = encontrar_indice_linha(linhas, 'Credor:')
    indice_documento = indice_credor + 1
    indice_data_nascimento = encontrar_indice_linha(linhas, 'Data de Nascimento:')
    indice_devedor = encontrar_indice_linha(linhas, 'Nome Devedor:')
    indice_valor_global = encontrar_indice_linha(linhas, 'Valor(R$):')
    indice_natureza = encontrar_indice_linha(linhas, 'Natureza do Crédito: ')
    indice_cidade = encontrar_indice_linha(linhas, "")
    indice_data_expedicao = encontrar_indice_linha(linhas, "")
    inddice_vara = encontrar_indice_linha(linhas,'Origem:')
    indices = {'indice_credor': indice_credor, 'indice_documento': indice_documento, 'indice_data_nascimento': indice_data_nascimento, 'indice_devedor': indice_devedor, 'indice_valor_global': indice_valor_global, 'indice_natureza': indice_natureza,'indice_data_expedicao': indice_data_expedicao, 'indice_cidade': indice_cidade}


    dados = mandar_dados_regex(indices, linhas)
    dados_advogado  = {'advogado': '', 'oab': '', 'telefone': '', 'seccional': ''}
    dados = dados | dados_advogado | dados_xml
    enviar_dados_boy(arquivo_pdf,  dados)
    return dados

def enviar_dados_boy(arquivo_pdf, dados):
    atualizar_ou_inserir_pessoa_no_banco_de_dados(dados['documento'], {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento']})
    
    id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
    dados['id_sistema_arteria'] = id_sistema_arteria
    atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
    atualizar_ou_inserir_pessoa_precatorio(dados['documento'], dados['processo'])
