import re
import time
from banco_de_dados import atualizar_ou_inserir_situacao_cadastro
from logs import log
from rich import print
from requests import Session
from bs4 import BeautifulSoup
from custom_captcha import quebra_imagem
from capmon_utils import recaptcha, hcaptcha
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

def login_eproc(
        user, 
        password, 
        raiz,
        n_processo,  
        processo_xml,
        endpoint="PesquisaRapida", 
        f_encoding="ISO-8859-1"):
    """
    endpoint options:
    PesquisaRapida - Pesquisa por numero cnj
    PesquisaAvancada - Pesquisa por numero de processo, Documento, Parte
    """
    form = {
        "txtUsuario": user,
        "pwdSenha": password,
        "hdnAcao": "login",
        "hdnDebug": ""
    }
    adapter = HTTPAdapter(max_retries=5)
    
    s = Session()

    s.encoding = f_encoding

    s.mount('httos://', adapter)

    s.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    login = s.post(f"{raiz}/index.php", data=form)

    soup = BeautifulSoup(login.text, "lxml")

    while captcha := soup.find(
            id="lblInfraCaptcha") or soup.find(
            attrs={"data-sitekey": True}):
        for attempt in range(5):
            try:
                captcha = (
                    hcaptcha(
                        captcha.get("data-sitekey"),
                        login.url)
                    if "h-captcha" in str(captcha).lower() else
                    recaptcha(
                        captcha.get("data-sitekey"),
                        login.url)
                    if "recaptcha" in str(captcha).lower() else
                    quebra_imagem(
                        captcha.img["src"].split("base64,")[-1],
                        base64=True))
                break
            except Exception as e:
                print(e)
        else:
            raise Exception("Captcha not solved")

        form = {
            "txtInfraCaptcha": captcha["code"],
            "g-recaptcha-response": captcha["code"],
            "h-captcha-response": captcha["code"],
            "hdnInfraCaptcha": 1,
            "hdnAcao": "login",
            "hdnDebug": ""
        }

        login = s.post(f"{raiz}/index.php", data=form)

        soup = BeautifulSoup(login.text, "lxml")

    if "msg=" in login.url:
        raise Exception(login.url.split("msg=")[-1])

    if soup.find("form", {"id": "frmEscolherUsuario"}):
        id_usuario = soup.find(
            "button", {
                "data-descricao": re.compile(r"PROCURADOR - CHEFE")}).attrs["onclick"].split("'")[1]

        query = {
            "acao": "pessoa_usuario_logar",
            "acao_origem": "entrar",
            "id_usuario": id_usuario}

        re_login = s.post(
            f"{raiz}/controlador.php",
            params=query,
            data={
                "lista_processos": ""})

        soup = BeautifulSoup(re_login.text, "lxml")

    if endpoint == "PesquisaRapida":
        endpoint = soup.find(
            "form", {
                "name": "formPesquisaRapida"}).attrs["action"]
    elif endpoint == "PesquisaAvancada":
        endpoint = soup.find(href=re.compile(
            r"acao=processo_consultar")).attrs["href"]
    else:
        raise ValueError("Endpoint not found")
    print(endpoint)
    hash = endpoint.split('hash=')[1]
    pdf_precatorio, id_documento = buscar_processo(s, raiz,hash, n_processo, processo_xml)
    return pdf_precatorio, id_documento

def buscar_processo(s, raiz, hash, n_processo, processo_xml):
    tipo_processo = s.post(f'{raiz}/controlador.php?acao=processo_selecionar&num_processo={n_processo}&hash={hash}')
    soup = BeautifulSoup(tipo_processo.content, 'lxml')
    procurar = soup.find(id='divInfraAreaGlobal').find('h1').text
    tribunal = raiz.split('.')[1]
    time.sleep(7)
    try:
        if 'Detalhes do Processo' in procurar: 
            txtClasse = soup.find(id='divCapaProcesso').find(id='txtClasse').text.strip()
            processo_origem = soup.find(id='divCapaProcesso').find(id='tableRelacionado').text.strip()
            if 'PRECATÓRIO' in txtClasse.upper():
                pesq_acoes = soup.find(id='fldAcoes')
                pesq_autos = pesq_acoes.find(class_="infraButton").get('onclick', None)
                hash_autos = pesq_autos.split('hash=')[1].split(',')[0].replace("'", '').strip()
                url_autos = s.get(f"{raiz}/controlador.php?acao=processo_vista_sem_procuracao&txtNumProcesso={n_processo}&hash={hash_autos}")
                soup = BeautifulSoup(url_autos.content, 'lxml')
                procurar_img_captcha = soup.find(id='lblInfraCaptcha')
                img_captcha = procurar_img_captcha.find('img').get('src').split('base64,')[1]
                captcha = quebra_imagem(img_captcha, is_base64=True)
                params = {
                        'txtInfraCaptcha': captcha['code'],
                        'hdnInfraCaptcha': ''
                    }
                nos_autos = s.post(url_autos.url, data=params).url
                pdf_precatorio, id_documento = download_precatorio(s,raiz,nos_autos, n_processo, processo_xml)
                return pdf_precatorio, id_documento
            else:
                print('ERRO: não é precatório')
                # processo_xml = n_processo if processo_xml == '' else processo_xml
                # processo = re.sub(r'(\d{7})(\d{2})(\d{4})(\d{1})(\d{2})(\d{2})(\d{4})', r'\1-\2.\3.\4.\5.\6.\7', processo_xml)
                atualizar_ou_inserir_situacao_cadastro(processo_xml, {'status': 'Não é precatório'})
                log(n_processo, 'Fracasso', raiz, "Esse processo não gera precatório", '',tribunal)
                return '',''
        else:
            log(n_processo, 'Fracasso', raiz, "O processo informado não existe", '',tribunal)
            return '', ''
    except Exception as e:
        with open('rodar_novamente.txt', 'a') as f:
            f.write(f'{processo_xml}\n')
        return '',''
    
def download_precatorio(s, raiz, url_autos, n_processo, processo_xml):
    tribunal = raiz.split('.')[1]
    procurar_precatorio = s.get(url_autos)
    soup = BeautifulSoup(procurar_precatorio.content, 'lxml')
    todos_links = soup.find_all(class_='infraLinkDocumento')
    link_precatorio = ''
    for link in todos_links:
        texto = link.get('aria-label').upper()
        if texto == "VISUALIZAR DOCUMENTO INIC1 DO TIPO PDF ":
            link_precatorio = link
    if link_precatorio != '':
        link_documento = link_precatorio.get('href')
        pag_precatorio = s.get(f'{raiz}/{link_documento}')
        url_pdf_precatorio = s.get(pag_precatorio.url)
        url_pdf, id_documento = extrair_url_pdf(raiz, url_pdf_precatorio.content)

        if url_pdf:
            response = s.get(url_pdf)
            pdf_precatorio = f'arquivos_pdf_{tribunal}/{n_processo}_{tribunal}.pdf'
            print('--->> ', pdf_precatorio)
            with open(pdf_precatorio, 'wb') as pdf_file:
                pdf_file.write(response.content)
            print('PDF --->> ', pdf_precatorio)
            
        return pdf_precatorio, id_documento
    else:
        # processo_xml = n_processo if processo_xml == '' else processo_xml
        # processo = re.sub(r'(\d{7})(\d{2})(\d{4})(\d{1})(\d{2})(\d{2})(\d{4})', r'\1-\2.\3.\4.\5.\6.\7', processo_xml)
        atualizar_ou_inserir_situacao_cadastro(processo_xml, {'status': 'Não foi possivel acessar pdf'})
        with open('rodar_novamente.txt', 'a') as f:
            f.write(f'{processo_xml}\n')
        log(n_processo, 'Fracasso', raiz, "Não foi possivel acessar o pdf referente ao precatório.", '',tribunal)

def extrair_url_pdf(raiz, html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    iframe = soup.find('iframe')
    if iframe:
        id_documento = iframe['src'].split('doc=')[1].split('&')[0]
        return f'{raiz}/{iframe["src"]}', id_documento
    else:
        return '', ''

