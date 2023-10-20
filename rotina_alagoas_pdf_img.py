import traceback
from logs import log
from funcoes_arteria import enviar_valores_oficio_arteria
from utils import   mandar_documento_para_ocr, encontrar_indice_linha, mandar_dados_regex
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados

def extrair_dados_texto_ocr(arquivo_pdf, dados):
    try:
        processo_geral = dados['processo']
        dados = dados | {'valor_juros': '', 'valor_principal': '', 'cidade': ''}
        arquivo_txt = mandar_documento_para_ocr(arquivo_pdf, '1', processo_geral)
        ler_texto_ocr(arquivo_pdf, dados, arquivo_txt)
    except Exception as e:
        print("ERRO NO PDF IMAGEM", f"Erro no processo -> {processo_geral}", f'Erro: {e}')
        print(traceback.print_exc())
        pass

def ler_texto_ocr(arquivo_pdf, dados_xml, arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
    indice_credor = encontrar_indice_linha(linhas, 'credor:')
    indice_documento = indice_credor + 1
    indice_data_nascimento = encontrar_indice_linha(linhas, 'data de nascimento:')
    indice_devedor = encontrar_indice_linha(linhas, 'nome devedor:')
    indice_valor_global = encontrar_indice_linha(linhas, 'valor(r$):')
    indice_natureza = encontrar_indice_linha(linhas, 'natureza do crédito: ')
    indice_data_expedicao = encontrar_indice_linha(linhas, "liberado nos autos em")
    indice_vara = encontrar_indice_linha(linhas,'origem:')
    indices = {'indice_credor': indice_credor, 'indice_documento': indice_documento, 'indice_data_nascimento': indice_data_nascimento, 'indice_devedor': indice_devedor, 'indice_valor_global': indice_valor_global, 'indice_vara': indice_vara, 'indice_natureza': indice_natureza,'indice_data_expedicao': indice_data_expedicao, }

    dados_regex = mandar_dados_regex(indices, linhas)
    dados_advogado  = {'advogado': '', 'oab': '', 'telefone': '', 'seccional': ''}
    dados = dados_regex | dados_advogado | dados_xml
    enviar_dados_banco_de_dados_e_arteria_alagoas(arquivo_pdf,  dados)

    return dados

def enviar_dados_banco_de_dados_e_arteria_alagoas(arquivo_pdf, dados):    
    documento = dados['documento']
    atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento']})
    id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
    dados['id_sistema_arteria'] = id_sistema_arteria
    atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
    atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])
    log({'processo': dados['processo'], 'tipo': 'Sucesso', 'site': dados['site'], 'mensagem': 'Precatório registrado com sucesso', 'estado': dados['estado']})