from datetime import datetime
from banco_de_dados import inserir_ou_atualizar_log_rotina_esaj
from rotina_processos_infocons import data_corrente_formatada


def log(cnj,tipo, site, mensagem, estado):
    hora = datetime.now()
    hora_formatada = hora.strftime('%H:%M:%S')
    tentativas = 1

    if tipo != 'Sucesso':
        mensagem = dict_erros(mensagem)
        with open('LOG_FALHA_ESAJ.txt', '+a', encoding='utf-8') as f:
            f.write(f"{data_corrente_formatada()} {hora_formatada} - {estado} - {cnj} - {mensagem} - {site}\n")
    else:
        with open('LOG_SUCESSO_ESAJ.txt', '+a', encoding='utf-8') as f:
            f.write(f"{data_corrente_formatada()} {hora_formatada} - {estado} - {cnj} - {mensagem} - {site}\n")

    with open('LOG_COMPLETO_ESAJ.txt', '+a', encoding='utf-8') as f:
        f.write(f"{data_corrente_formatada()} {hora_formatada} - {estado} - {cnj} - {mensagem} - {site}\n")

    dados = {'processo': cnj, 'site': site, 'mensagem': mensagem, 'tipo': tipo, 'tentativas': tentativas, 'estado': estado}
    inserir_ou_atualizar_log_rotina_esaj(dados, cnj)

def dict_erros(mensagem):
    erros = {
    "'99024'": 'Não há ofício precatório expedido.', 
    "'342'": 'Não há ofício precatório expedido.',
    "'147'": 'Não há ofício precatório expedido.',
    "'7'": 'Não há ofício precatório expedido.',
    "'31": 'Não há ofício precatório expedido.',
    "'NoneType' object has no attribute 'find_all'": "Falha em estabelecer conexão com o tribunal.", 
    "unsupported operand type(s) for |: 'dict' and 'NoneType'": 'O documento não é um ofício precatório.',
    '"NoneType" object is not iterable': 'Não há precatório associado ao processo.', 
    "descriptor 'keys' for 'dict' objects doesn't apply to a 'NoneType' object": 'Não há precatório associado ao processo.',
    "'NoneType' object has no attribute 'items'": 'Não há ofício precatório.',
    "'NoneType' object has no attribute 'split'": 'Não há ofício precatório'}

    mensagem_erro = 'Não há precatório.'
    for e in dict.keys(erros):
        if e in mensagem:
            mensagem_erro = erros[e]
    return mensagem_erro
