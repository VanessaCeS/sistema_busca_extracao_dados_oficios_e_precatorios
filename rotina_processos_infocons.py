import os
import util
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
load_dotenv('.env')

def data_corrente_formatada():
    data_atual = datetime.now()
    data_formatada = data_atual.strftime("%d/%m/%Y")
    return data_formatada


def buscar_xml():
    url_info_cons = "https://clippingbrasil.com.br/InfoWsScript/service_xml.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
    }
    sigla = os.getenv('sigla')
    user = os.getenv('user')
    password = os.getenv('password')
    data = {
        'input': (None, f'{{"data": "06/11/2023","sigla": "{sigla}","user": "{user}","pass":"{password}"}}')
    }

    response = requests.post(url=url_info_cons, headers=headers, files=data)

    soup = BeautifulSoup(response.content, 'xml')

    with open(f'arquivos_xml/relatorio_{data_corrente_formatada().replace("/", "_")}.xml', 'w', encoding='utf-8') as f:
        f.write(response.text)
    publicacoes_tags = soup.find_all('Publicacoes')
    publicacoes_dict = {}
    for i, publicacao_tag in enumerate(publicacoes_tags, start=1):
        publicacao = {}
        for child_tag in publicacao_tag.find_all(recursive=False):
            publicacao[child_tag.name] = child_tag.text.strip()
        publicacoes_dict[f"Publicacao_{i}"] = publicacao

    for chave, valor in publicacoes_dict.items():
        dados_processo = {}
        dados_publicacao = {}
        for campo, conteudo in valor.items():
            if campo == 'Processo':
                dados_processo['processo'] = conteudo
            if campo == "Nome":
                dados_processo['nome'] = conteudo
            if campo == "Tribunal":
                dados_processo['tribunal'] = conteudo
            if campo == 'Materia':
                dados_processo['materia'] = conteudo
            if campo == 'Publicacao':
                dados_publicacao['publicacao'] = conteudo
            if campo == 'DataPub':
                dados_publicacao['data_publicacao'] = conteudo
            if campo == 'SeqRecorte':
                dados_publicacao['seq_recorte'] = conteudo
        processo_id = insert_or_update_processo(util.connector_precatorio_banco(), dados_processo)
        if processo_id == 0:
            processo_id = select_id(util.connector_precatorio_banco(), dados_processo['processo'])
        insert_publicacao(util.connector_precatorio_banco(), processo_id, dados_publicacao)
    print('fim')


def select_id(conn, processo):
    cursor = conn.cursor()
    sql = f"SELECT id_processo FROM processos WHERE processo = '{processo}'"
    cursor.execute(sql)

    results = cursor.fetchall()

    return results[0][0]

def insert_or_update_processo(conn, dados_processo):
    cursor = conn.cursor()

    sql = """
    INSERT INTO processos (nome, processo, materia, tribunal)
    VALUES (%(nome)s, %(processo)s, %(materia)s, %(tribunal)s)
    ON DUPLICATE KEY UPDATE
    nome = VALUES(nome),
    processo = VALUES(processo),
    materia = VALUES(materia),
    tribunal = VALUES(tribunal);
    """

    cursor.execute(sql, dados_processo)

    processo_id = cursor.lastrowid

    conn.commit()

    return processo_id


def insert_publicacao(conn, processo_id, dados_publicacao):
    cursor = conn.cursor()

    dados_publicacao["id_processo"] = processo_id

    sql = """
    INSERT INTO publicacoes (id_processo, seq_recorte, publicacao, data_publicacao)
    VALUES (%(id_processo)s, %(seq_recorte)s, %(publicacao)s, %(data_publicacao)s);
    """

    cursor.execute(sql, dados_publicacao)

    conn.commit()

def insert(conn, processo_id,cnj, dados_publicacao):
    cursor = conn.cursor()

    dados_publicacao['id_processo'] = processo_id
    cnj_numerico = cnj.replace('-','').replace('.','').replace('/','')
    
    sql = '''
    INSERT INTO publicacoes_infocons (id_publicacao, cnj, cnj_numerico, nome, data_publicacao, tribunal, dados) VALUES (%(id_publicacao)s, %(cnj)s, %(cnj_numerico)s, %(nome)s, %(data_pubicacao)s, %(tribunal)s, %(publicacoes)s)                
    '''
    cursor.execute(sql, dados_publicacao)
    conn.commit()
