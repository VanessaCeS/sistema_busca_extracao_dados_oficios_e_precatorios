import re
import os
import functools
import traceback
from logs import log
from requests import Session
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry
from banco_de_dados import atualizar_ou_inserir_situacao_cadastro


def configure_session(session, retries=3, backoff=0.3, timeout=None, not_retry_on_methods=None, retry_on_status=None):
    retry_methods = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]

    retry_methods = frozenset(retry_methods) if not not_retry_on_methods else frozenset([method for method in retry_methods if method not in not_retry_on_methods])

    Retry.DEFAULT_BACKOFF_MAX = 60

    retry = Retry(total=retries, read=retries, connect=retries, status=retries, backoff_factor=backoff, status_forcelist=retry_on_status, allowed_methods=retry_methods)

    adapter = HTTPAdapter(max_retries=retry)

    session.mount("http://", adapter)

    session.mount("https://", adapter)

    if timeout:
        session.request = functools.partial(session.request, timeout=timeout)

    return session


def login_esaj(url_tribunal: str, username: str, password: str) -> Session:
    url = f"{url_tribunal}/sajcas/login"

    s = configure_session(Session(), timeout=120, retry_on_status=(403,), backoff=60)

    s.headers = {
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Google Chrome";v="95", "Chromium";v="95", ";Not A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "Upgrade-Insecure-Requests": "1",
        "Origin": url_tribunal,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Referer": url,
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        page_login = s.get(url, timeout=15)
    except Exception as e:
        print(f"[bold red]Não foi possivel acessar o site do tribunal. {e}[/bold red]")
        
        raise Exception(f"{url_tribunal} - Não foi possivel acessar o site do tribunal {e}")
    
    if page_login.status_code != 200:
        print(f"[bold red]{url_tribunal} - Não foi possivel acessar o site do tribunal. Status code: {page_login.status_code}[/bold red]")
        
        raise Exception(f"{url_tribunal} - Não foi possivel acessar o site do tribunal.  Status code: {page_login.status_code}")

    soup = BeautifulSoup(page_login.content, "lxml")

    exec_key = soup.find("input", type="hidden", id="flowExecutionKey")
    
    if exec_key:
        exec_key = exec_key["value"]

        exec_name = "execution"
    else:
        exec_key = soup.find("input", type="hidden", value=True)

        exec_name = exec_key["name"]

        exec_key = exec_key["value"]

    data = {"username": username, "password": password, exec_name: exec_key, "_eventId": "submit", "pbEntrar": "Entrar"}

    logar = s.post(url, data=data)

    if url in logar.url:
        print(f"[bold red]{url_tribunal} - Login Falhou[/bold red]")

        raise Exception(f"{url_tribunal} - Login Falhou")

    return s


def get_docs_precatorio(codigo_prec, url, s, zip_file=False, pdf=False):
        oficios = []
        id_documento = '' 
        value = f'/cpopg/show.do?localPesquisa.cdLocal=53&processo.codigo={codigo_prec}&processo.foro=53'        
        pasta_digital_req = s.get(f'{url}{value}') 
        soup = BeautifulSoup(pasta_digital_req.text, "lxml")
        tabela = soup.find(id="tabelaUltimasMovimentacoes")
        colunas = tabela.find_all(class_='descricaoMovimentacao')
        for col in colunas:
            texto = (col.text).replace("\t", "").replace('\n','').strip()
            if 'OFÍCIO REQUISITÓRIO' in texto.upper() and 'RPV' not in texto.upper():
                
                procurar_link_precatorio = col.find('a', class_='linkMovVincProc')
                if procurar_link_precatorio:
                    link = procurar_link_precatorio['href']
                    abrir_documento_pdf = s.get(f'{url}{link}')
                    soup = BeautifulSoup(abrir_documento_pdf.text, 'lxml')
                    procurar_script = soup.find_all('script')[-2]
                    script = str(procurar_script)
                    padrao = re.compile(r'var requestScope = (.*?);', re.DOTALL)
                    correspondencias = padrao.search(script)
                    if correspondencias:
                        correspondencias = correspondencias.group(1)
                        params = correspondencias.split('parametros')[1].split(',')[0][2:]
                        if pdf:
                            file_req = s.get(f'https://esaj.tjsp.jus.br/pastadigital/getPDF.do?{params}')
                            file_name = file_req.headers['Content-Disposition'].split('filename=')[1].replace('"', '')
                            id_documento = params.split('idDocumento=')[1].split('&')[0]
                            oficios.append([id_documento, file_name, file_req.content])
                            
                else:
                    continue
        return {'id_documento': id_documento, 'pdfs': oficios} if zip_file and pdf else oficios if pdf else zip_file if zip_file else None

        
def get_incidentes(cnj, url, s):
    url_tribunal = url[: url.find(".br") + 3]

    pagi_consulta = s.get(f"{url}/open.do?gateway=true")

    soup = BeautifulSoup(pagi_consulta.content, "lxml")

    novo = soup.find("nav")

    form = soup.find("form")

    tipo_busca = "NUMPROC"

    inputs_cnj = form.find(id=tipo_busca).find_all("input", disabled=False)

    inputs_cnj = [i.attrs["name"] for i in inputs_cnj]

    if novo:
        query_consulta = {
            "conversationId": "",
            "cbPesquisa": "NUMPROC",
            inputs_cnj[0]: cnj[0:15],
            inputs_cnj[1]: cnj[21:25],
            inputs_cnj[2]: [cnj, "UNIFICADO"] if inputs_cnj[2] == inputs_cnj[3] else cnj,
            "dePesquisa": "",
            inputs_cnj[5]: "UNIFICADO"
        }
        if inputs_cnj[2] != inputs_cnj[3]:
            query_consulta[inputs_cnj[3]] = "UNIFICADO"

        consulta = s.get(f"{url}/search.do", params=query_consulta)

        soup = BeautifulSoup(consulta.content, "lxml")

        processo_selecionado = soup.find("input", id="processoSelecionado")

        if processo_selecionado:
            consulta = s.get(f'{url}/show.do?processo.codigo={processo_selecionado.attrs["value"]}')
            soup = BeautifulSoup(consulta.content, "lxml")

        segredo = soup.find("form", id="popupSenha")
        if segredo:
            if segredo.attrs["style"] != "display: none;":
                print(f"[bold red]Processo {cnj} em segredo de justiça[/bold red]")
                return

        redirect_proc = soup.find("span", id="numeroProcesso") or soup.find("div", class_="unj-entity-header__summary") or soup.find("span", text=re.compile(f"\({cnj}\)"))

        if redirect_proc is None:
            links_resultado = []
            link_proc = soup.find_all("a", class_="linkProcesso", href=True)
            for link in link_proc:
                if link.text.strip() == cnj:
                    links_resultado.append(link.text.strip())

            if len(links_resultado) == 1:
                consulta = s.get(f"{url_tribunal}{link_proc[0]['href']}")
                soup = BeautifulSoup(consulta.content, "lxml")
                redirect_proc = soup.find("span", id="numeroProcesso")
                if redirect_proc is None:
                    redirect_proc = soup.find("div", class_="unj-entity-header__summary")
            elif len(links_resultado) > 1:
                print(f"[red]Mais de um processo encontrado como resultado para processo {cnj}[/red]")
                return
            else:
                print(f"[red]Nenhum processo identico encontrado como resultado para processo {cnj}[/red]")
                return

        if redirect_proc:
            if redirect_proc.text.strip() != cnj and cnj not in redirect_proc.text.strip():
                if not redirect_proc.text.strip():
                    print(f"[red]Processo {cnj} provavel segredo de justiça[/red]")
                    return
                print(f"[red]Processo com cnj divergente {cnj} != {redirect_proc.text.strip()}[/red]")
                return

            incidentes = soup.find_all("a", class_="incidente")

            incidentes = {x.text.strip().replace('\n', '').replace('\t', ''): x['href'] for x in incidentes}

            return incidentes
        else:
            print(f"[red]Processo {cnj} não encontrado[/red]")
            return
    else:
        print(f"[red]Tribunal no modelo antigo")

def get_docs_oficio_precatorios_tjsp(cnj, zip_file=False, pdf=False):
    login_esja = f'{os.getenv("login_esja")}'
    senha_esja_sao_paulo = f'{os.getenv("senha_esja_sao_paulo")}'
    session = login_esaj('https://esaj.tjsp.jus.br', '69173753149', 'Costaesilva2023#')
    incidentes = get_incidentes(cnj, 'https://esaj.tjsp.jus.br/cpopg', session)
    
    docs = {}
    try:
        cods_incidentes = [v.split('codigo=')[1].split('&')[0] for k, v in incidentes.items() if 'precatório' in k.lower()]
        docs = {cod: get_docs_precatorio(cod, 'https://esaj.tjsp.jus.br', session, zip_file=zip_file, pdf=pdf) for cod in cods_incidentes}
        return docs
    except Exception as e:
        print('Erro --> ', e)
        print(traceback.print_exc())
        log(cnj, 'Fracasso','https://esaj.tjsp.jus.br', str(e), 'São Paulo','tjsp')
        atualizar_ou_inserir_situacao_cadastro(cnj,{'status': 'Fracasso'})
        
