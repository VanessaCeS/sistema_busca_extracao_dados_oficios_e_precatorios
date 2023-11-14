import os
import zipfile
import requests
from dotenv import load_dotenv
from urllib.parse import unquote
load_dotenv('.env')

def descompactar_pasta(caminho_arquivo_zip, pasta_destino):

    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)

    with zipfile.ZipFile(caminho_arquivo_zip, 'r') as zip_ref:
        zip_ref.extractall(pasta_destino)
        nomes_arquivos = zip_ref.namelist()
    
    return nomes_arquivos

def download_doc(cod, proc_hash, s):
    json_pdf = {"codHash": proc_hash, "codDoctoElet": cod, "compact": False}
    file_bytes = s.post(
        "https://www3.tjrj.jus.br/visproc/api/obterDocumento", json=json_pdf
    )

    return file_bytes.content


def auth_session():
    usuario = os.getenv('login_tjrj')
    senha = os.getenv('senha_tjrj')
    s = requests.Session()

    s.headers.update(
        {
            "Authorization": "Basic dGpyajpzM2NyM3Q=",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        }
    )

    first = s.post(
        "https://www3.tjrj.jus.br/idserverjus-api/sessao",
        json={"usuario": usuario, "senha": senha},
    ).json()

    jwt_body = {
        "chave": first["chave"],
        "idUsu": first["idUsu"],
        "inicio": first["inicio"],
        "ultimoAcesso": first["ultimoAcesso"],
    }

    s.post(
        "https://www3.tjrj.jus.br/idserverjus-api/sessao/criarJwt", json=jwt_body
    ).json()

    s.cookies.update(
        {
            "SEGSESSIONID": first["chave"],
            "SIGLASISTEMA": "PORTALSERVICOS",
            "SEGCODORGAO": "2385",
        }
    )

    s.headers.update({"Authorization": first["chave"]})

    jwt_auth = s.post("https://www3.tjrj.jus.br/visproc/api/jwt-auth").json()["jwt"]

    s.headers.update({"Authorization": jwt_auth})

    atualizar = s.post(
        "https://www3.tjrj.jus.br/portalservicos/api/usuarios/atualizar-perfil-logado",
        data="1",
    ).json()[0]

    s.headers.update({"Authorization": atualizar})

    s.headers.update({"ETag": "MC42LjQ="})

    return s


def busca_docs(cnj, s):
    json_busca = {"tipoProcesso": "1", "codigoProcesso": cnj}

    procs = s.post(
        "https://www3.tjrj.jus.br/consultaprocessual/api/processos/por-numeracao-unica",
        json=json_busca,
        headers={
            "recaptcha-token": "03AFcWeA4N7IQOUdiu9Qm7F0Dsiewp-8gwpEa5JnxFS_Bafn_pZ6c4yuYa1P6pREpQ3bkd9Bz1A55nqfUBQ9cveCp2SK8pxIgRCenRv9rUd7God0ClNRy8OdaTrftkzH95LN7dLLNy-Q50GT5FjPXsxhyAXmIOs33_SQMtMOfdcOOu15twJRNNYoCbqNv3dMMvaxBfq6nD4NvF3DxN_jiaL_5rAR6iFlZywP7cX-r5b32_0CDVliugDRETVR3edUVGS-NVrIzuzyG5QQFkpIchnYjWbpMctCRBPqpATLPR8MDmm3ufBgRRbfXbOit0YYdNybfKSuby194y2WWaFP8-AISIq6DZ3rrlxclxWW_zgZHPUcBveb-OjHdOJTks329CcKVy-YKjWTphIHTcN-ZfM9AR_L0sz5wRlVVSG_qwWoaZi-ZehZEVKlS4EsVLkYNtNCTwa1ecjVXN-EY_xL_Neth5I6SNie_V2Iud3udcd9xK1Jfal-MrZLVBgaUfQNyNAr4h_VUB64jG7hVkzR8XIWoM0EX-vF8h1xyq5CVqqxPCOa-lc85odpc"
        },
    ).json()

    body_busca_detalhes = {
        "codigoProcessoCNJ": cnj,
        "codigoProcessoAntigo": procs[0]["numProcesso"],
        "codTipoProcesso": procs[0]["tipoProcesso"],
        "motivo": "advogado",
    }

    hash_proc = unquote(
        s.post(
            "https://www3.tjrj.jus.br/consultaprocessual/api/montar-vis-proc/url-processo-eletronico",
            json=body_busca_detalhes,
        )
        .json()[0]
        .split("#/")[-1]
    )

    body_ = {"codHash": hash_proc}

    docs = s.post(
        "https://www3.tjrj.jus.br/visproc/api/consultarProcesso", json=body_
    ).json()["filhos"]
    num_processo = procs[0]['numProcesso']
    return s, docs,num_processo, hash_proc


def get_docs_oficio_precatorio_tjrj(cnj):
    s = auth_session()

    s, docs,num_processo, hash_proc = busca_docs(cnj, s)

    files = []
    for doc in docs:
        if not doc.get('codDoctoElet'):
            continue
        if 'OFREQ' in doc.get('descricao'):
            file_bytes = download_doc(doc["codDoctoElet"], hash_proc, s)

            files.append({"descricao": doc["descricao"], "file_bytes": file_bytes})
            arq_zip = f'{doc["descricao"]}.zip'.replace("/", "-")
            with open(f'pasta_zip/{arq_zip}', "wb") as f:
                f.write(file_bytes)
            codigo_documento = doc["codDoctoElet"]
            print(f"Arquivo baixado. {doc['descricao']}")
            pasta_zip = doc["descricao"] + '.zip'
    if files != []:
        arquivo_descompactado = descompactar_pasta(f'pasta_zip/{arq_zip}', 'arquivos_pdf_rio_de_janeiro')
        return arquivo_descompactado, codigo_documento, num_processo
    else:
        return None, None, None


# test("0002338-39.2023.8.19.0000")
