import openpyxl
from datetime import datetime
from banco_de_dados import inserir_log_no_banco_de_dados
from rotina_processos_infocons import data_corrente_formatada


def log(cnj,tipo, site, mensagem, estado, tribunal):
    hora = datetime.now()
    hora_formatada = hora.strftime('%H:%M:%S')
    tentativas = 1
    regiao = estado
    if estado == '':
        regiao = tribunal

    if tipo != 'Sucesso':
        mensagem = dict_erros(mensagem)
        with open('arquivos_logs/log_falha_rotina_precatorios.txt', '+a', encoding='utf-8') as f:
            f.write(f"{data_corrente_formatada()} {hora_formatada} - {regiao} - {cnj} - {mensagem} - {site}\n")
    else:
        with open('arquivos_logs/log_sucesso_rotina_precatorios.txt', '+a', encoding='utf-8') as f:
            f.write(f"{data_corrente_formatada()} {hora_formatada} - {regiao} - {cnj} - {mensagem} - {site}\n")

    with open('arquivos_logs/log_completo_rotina_precatorios.txt', '+a', encoding='utf-8') as f:
        f.write(f"{data_corrente_formatada()} {hora_formatada} - {regiao} - {cnj} - {mensagem} - {site}\n")
        
    dados = {'processo': cnj, 'site': site, 'mensagem': mensagem, 'tipo': tipo, 'tentativas': tentativas, 'estado': estado, 'tribunal': tribunal}
    inserir_log_no_banco_de_dados(dados)

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
    "'NoneType' object has no attribute 'split'": 'Não há ofício precatório',
    "Esse processo não gera precatório": "Esse processo não gera precatório",
    "O processo informado não existe": "O processo informado não existe", 
    "cannot access local variable 'pdf_precatorio' where it is not associated with a value": 'Falha em estabelecer conexão com o tribunal.', 
    'cannot unpack non-iterable NoneType object': 'Falha em estabelecer conexão com o tribunal.',
    "Não foi possivel acessar o pdf referente ao precatório.": "Não foi possivel acessar o pdf referente ao precatório.",
    'Invalid URL '': No scheme supplied. Perhaps you meant https://?' : 'Limite diário de acessos a pasta digital foi atingido.',
    'Não há ofício requisitório no processo': 'Não há ofício requisitório no processo'
    }

    mensagem_erro = 'Não há precatório.'
    for e in dict.keys(erros):
        if e in mensagem:
            mensagem_erro = erros[e]
    return mensagem_erro

def salvar_em_excel(dados):
    del dados['site']
    try:
        workbook = openpyxl.load_workbook('logs_do_sistema.xlsx')
        sheet = workbook.active
    except FileNotFoundError:
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(list(dados.keys()))

    sheet.append(list(dados.values()))
    workbook.save('logs_do_sistema.xlsx')
    