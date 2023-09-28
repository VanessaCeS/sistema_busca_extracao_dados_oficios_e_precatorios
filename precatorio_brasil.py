import json
import traceback
import util
import pytz
from pycognito import Cognito
import os
import requests
from datetime import datetime
import funcoes_arteria
from constants import EstadosCidades
from dotenv import load_dotenv

# os.environ["HTTP_PROXY"] = "http://127.0.0.1:8888"
# os.environ["HTTPS_PROXY"] = "http://127.0.0.1:8888"
# os.environ["REQUESTS_CA_BUNDLE"] = r"C:\Users\User\Documents\charles.pem"
load_dotenv('.env')


def get_token(username, password):
    USER_POOL_ID = os.environ.get('USER_POOL_ID')
    CLIENT_ID = os.environ.get('CLIENT_ID')
    REGION = os.environ.get('REGION')
    u = Cognito(USER_POOL_ID, CLIENT_ID, username=username, user_pool_region=REGION)
    u.authenticate(password=password)
    return u.access_token


def get_dados_precatoria(token, id_precatorio):
    headers = {
        'Host': 'api.precatoriosbrasil.com',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'accept': 'application/json, text/plain, */*',
        'sec-ch-ua-mobile': '?0',
        'authorization': f'{token}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://officer.precatoriosbrasil.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://officer.precatoriosbrasil.com/',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    response = requests.get(f'https://api.precatoriosbrasil.com/api/officer/quote/get-by-id/{id_precatorio}',
                            headers=headers)
    if response.status_code == 200:
        return response.json()
    return response


def get_nature_type(token, natureza_arteria):
    headers = {
        'Host': 'api.precatoriosbrasil.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'accept': 'application/json, text/plain, */*',
        'sec-ch-ua-mobile': '?0',
        'authorization': f'{token}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://officer.precatoriosbrasil.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://officer.precatoriosbrasil.com/',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    response = requests.get('https://api.precatoriosbrasil.com/api/officer/nature-type/', headers=headers)
    if response.status_code == 200:
        naturezas = response.json()
        for natureza in naturezas:
            if natureza['name'].strip().upper() == natureza_arteria.upper():
                return natureza['id']
        return 'Não encontrado'
    return response


def get_precatorio_type(token, tipo_precatorio):
    headers = {
        'Host': 'api.precatoriosbrasil.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'accept': 'application/json, text/plain, */*',
        'sec-ch-ua-mobile': '?0',
        'authorization': f'{token}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://officer.precatoriosbrasil.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://officer.precatoriosbrasil.com/',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    response = requests.get('https://api.precatoriosbrasil.com/api/officer/court-type/types', headers=headers)
    if response.status_code == 200:
        response = response.json()
        for r in response:
            if r['value'].strip().upper() == tipo_precatorio.upper():
                return r['id']
    return response


def get_uf_and_cidade(estado, cidade):
    for estado_cidade in EstadosCidades:
        try:
            if estado_cidade['nome'].upper() == estado.upper():
                for city in estado_cidade['cidades']:
                    if city.upper() == cidade.upper():
                        return estado_cidade['uf'], city
                return estado_cidade['uf']
        except:
            print(traceback.print_exc())
    return False


def get_tribunal_type_id(token, courtTypeId, tribunal):
    headers = {
        'Host': 'api.precatoriosbrasil.com',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'accept': 'application/json, text/plain, */*',
        'sec-ch-ua-mobile': '?0',
        'authorization': f'{token}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://officer.precatoriosbrasil.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://officer.precatoriosbrasil.com/',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    params = {
        'idCourtType': f'{courtTypeId}',
        'onlyActive': 'true',
    }

    response = requests.get('https://api.precatoriosbrasil.com/api/officer/court/by-type', params=params,
                            headers=headers)
    if response.status_code == 200:
        tribunais_site = response.json()
        for tribunal_site in tribunais_site:
            if tribunal_site['value'] in tribunal:
                return tribunal_site['id']
    return response


def cadastrar_precatorio(token, json_data):
    headers = {
        'Host': 'api.precatoriosbrasil.com',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json;charset=UTF-8',
        'sec-ch-ua-mobile': '?0',
        'authorization': f'{token}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://officer.precatoriosbrasil.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://officer.precatoriosbrasil.com/',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    response = requests.post(
        'https://api.precatoriosbrasil.com/api/officer/quote/save-quote-manual',
        headers=headers,
        json=json_data
    )
    if response.status_code == 200:
        dado = response.json()
        if dado['success']:
            return dado['data']['id'], '%.2f' % dado['data']['pricing']['price'], dado['data']['precatorio']['id']
        else:
            return dado
    return response


def get_all_precatorio(token):
    headers = {
        'Host': 'api.precatoriosbrasil.com',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'accept': 'application/json, text/plain, */*',
        'sec-ch-ua-mobile': '?0',
        'authorization': f'{token}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://officer.precatoriosbrasil.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://officer.precatoriosbrasil.com/',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    response = requests.get('https://api.precatoriosbrasil.com/api/officer/precatorio/get-all-officer-operator',
                            headers=headers)
    if response.status_code == 200:
        return response.json()
    return response


def get_all_by_id(token):
    headers = {
        'Host': 'api.precatoriosbrasil.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'accept': 'application/json, text/plain, */*',
        'sec-ch-ua-mobile': '?0',
        'authorization': f'{token}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://officer.precatoriosbrasil.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://officer.precatoriosbrasil.com/',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    response = requests.get('https://api.precatoriosbrasil.com/api/officer/quote/get-all-by-user',
                            headers=headers)

    if response.status_code == 200:
        return response.json()
    return response


def get_precatorio_by_id(token, id):
    headers = {
        'Host': 'api.precatoriosbrasil.com',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'accept': 'application/json, text/plain, */*',
        'sec-ch-ua-mobile': '?0',
        'authorization': f'{token}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://officer.precatoriosbrasil.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://officer.precatoriosbrasil.com/',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    response = requests.get(f'https://api.precatoriosbrasil.com/api/officer/quote/get-by-id/{id}',
                            headers=headers)
    if response.status_code == 200:
        return response.json()
    return response


def adicionar_documento_precatorio(token, id_precatorio, base64_arquivo):
    headers = {
        'Host': 'api.precatoriosbrasil.com',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json;charset=UTF-8',
        'sec-ch-ua-mobile': '?0',
        'authorization': f'{token}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://officer.precatoriosbrasil.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://officer.precatoriosbrasil.com/',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    json_data = {
        'precatorioId': int(id_precatorio),
        'file': f'{base64_arquivo}',
    }

    response = requests.put(
        'https://api.precatoriosbrasil.com/api/officer/precatorio/upload-process-document',
        headers=headers,
        json=json_data,
    )

    return response


def formatar_cpf_cnpj(numero):
    numero = ''.join(filter(str.isdigit, numero))  # Remove caracteres não numéricos

    if len(numero) == 11:  # Formatar como CPF
        return f'{numero[:3]}.{numero[3:6]}.{numero[6:9]}-{numero[9:]}'
    elif len(numero) == 14:  # Formatar como CNPJ
        return f'{numero[:2]}.{numero[2:5]}.{numero[5:8]}/{numero[8:12]}-{numero[12:]}'
    else:
        return "Número inválido"


def convert_date(input_date=None):
    gmt_plus_3_timezone = pytz.timezone('Etc/GMT+3')  # Fuso horário GMT+3

    if input_date is None:
        # Se nenhum argumento for fornecido, pegue a data e hora atuais no fuso horário GMT+3
        current_datetime = datetime.now(gmt_plus_3_timezone)
    else:
        try:
            # Parse a data de entrada no formato 'DD/MM/AAAA'
            parsed_date = datetime.strptime(input_date, '%d/%m/%Y')

            # Crie um datetime com a data fornecida e hora zero no fuso horário GMT+3
            current_datetime = gmt_plus_3_timezone.localize(
                datetime(parsed_date.year, parsed_date.month, parsed_date.day))
        except ValueError:
            return None  # Retorna None em caso de data inválida

    # Formate a data no formato desejado 'AAAA-MM-DDTHH:MM:SS.SSSZ'
    formatted_date = current_datetime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    return formatted_date


def montar_dados_precatorio(dado, token):
    courtTypeId = get_precatorio_type(token, dado['Tipo de Precatório'][0] if dado.get('Tipo de Precatório') else '')
    uf, city = get_uf_and_cidade(dado['Estado'][0] if dado.get('Estado') else '', dado['Cidade'])
    valor_principal = float(dado['Valor Principal'].replace(',', '.')) if dado.get('Valor Principal') else 0
    if valor_principal == 0:
        valor_principal = float(dado['Valor Global'].replace(',', '.')) if dado.get('Valor Global') else 0
    valor_juros = float(dado['Valor dos Juros'].replace(',', '.')) if dado['Valor dos Juros'] else 0
    if valor_juros == 0:
        valor_juros = float(dado['Valor Global'].replace(',', '.')) if dado.get('Valor Global') else 0

    json_data = {
        'principal': valor_principal,  # float de 2 casas decimais
        'interest': valor_juros,  # float de 2 casas decimais
        'baseDate': convert_date(dado['Data da Expedição']),  # current day datetime formato :'2023-09-01T14:38:03.899Z'
        'issueDate': convert_date(),  # datetime formato : '2023-08-23T03:00:00.635Z
        'status': 'Precificando',
        'classification': 'Precatorio',
        'natureId': get_nature_type(token, dado['Natureza'][0] if dado.get('Natureza') else ''),
        # int utilizar a os tipos do get_nature_type
        'correctionTypeId': None,
        'courtId': get_tribunal_type_id(token, courtTypeId, dado['Tribunal']),
        # get_tribunal_type_id(token) triar pelo tribunal
        'cpfCnpj': formatar_cpf_cnpj(dado['CPF/CNPJ']),  # cpf/cnpj formatado com pontução
        'active': False,
        'courtTypeId': courtTypeId,  # int utilizar a os tipos do get_precatorio_type
        'precatorioExpeditionType': 'PRECATORIO_EXPEDIDO',
        'birthDate': convert_date(dado['Data  de Nascimento do Requerente']),
        # datetime formato : '1978-09-21T03:00:00.052Z'
        'requester': dado['Nome do Requerente'].upper(),
        'requered': dado['Requerido'].upper(),
        'state': uf,
        'city': city,
        'civilCourt': dado['Vara'].upper(),
        'processCode': dado['Número do Precatório'],
        'sentenceCode': '',
        'processCodeSource': dado['Código do Processo de Origem'].split('/')[0] if '/' in dado[
            'Código do Processo de Origem'] else dado['Código do Processo de Origem'],
    }

    return json_data


def atualizar_arteria(dado, id_sistema_sistema):
    funcoes_arteria.cadastrar_arteria(dado, 'Precatórios', id_sistema_sistema)


token = get_token(os.environ.get('user_precatorio_brasil'),
                  os.environ.get('senha_precatorio_brasil'))

all_precatorio = get_all_by_id(token)
processos = []
for precatorio in all_precatorio:
    processos.append(
        {
            'id': precatorio['id'],
            'cnj': precatorio['precatorio']['processCode'],
            'valor_sistema': '%.2f' % precatorio['pricing']['price']
        })


search_xml = """<SearchReport id="11283" name="RELATORIO PRECATORIO AUTOMACAO">
  <DisplayFields>
    <DisplayField>27080</DisplayField>
    <DisplayField>27094</DisplayField>
    <DisplayField>27093</DisplayField>
    <DisplayField>27084</DisplayField>
    <DisplayField>27099</DisplayField>
    <DisplayField>27085</DisplayField>
    <DisplayField>27105</DisplayField>
    <DisplayField>27106</DisplayField>
    <DisplayField>27087</DisplayField>
    <DisplayField>27083</DisplayField>
    <DisplayField>27103</DisplayField>
    <DisplayField>27097</DisplayField>
    <DisplayField>27100</DisplayField>
    <DisplayField>27081</DisplayField>
    <DisplayField>27086</DisplayField>
    <DisplayField>27091</DisplayField>
    <DisplayField>27088</DisplayField>
    <DisplayField>27089</DisplayField>
    <DisplayField>27096</DisplayField>
    <DisplayField>27101</DisplayField>
    <DisplayField>27102</DisplayField>
    <DisplayField>27095</DisplayField>
    <DisplayField>27090</DisplayField>
    <DisplayField>27082</DisplayField>
    <DisplayField>27107</DisplayField>
  </DisplayFields>
  <PageSize>99999</PageSize>
  <IsResultLimitPercent>False</IsResultLimitPercent>
  <Criteria>
    <Keywords />
    <ModuleCriteria>
      <Module>599</Module>
      <IsKeywordModule>True</IsKeywordModule>
      <BuildoutRelationship>Union</BuildoutRelationship>
      <SortFields>
        <SortField>
          <Field>27080</Field>
          <SortType>Ascending</SortType>
        </SortField>
      </SortFields>
    </ModuleCriteria>
  </Criteria>
</SearchReport>"""
precatorios_arteria = funcoes_arteria.search(search_xml)
for dado in precatorios_arteria:
    if dado['id portal precatórios']:
        if dado['id portal precatórios'] != '':
            atualizar_arteria(
                {
                    'id portal precatórios': dado['id portal precatórios'],
                    'Valor Pago pelo Parceiro/Cliente': dado['Valor Pago pelo Parceiro/Cliente'].replace(".",",")
                },
                dado['ID de rastreamento'])
    elif 'YOUSSEF' not in dado['Nome do Requerente'].upper():
        id, valor, id_documento = cadastrar_precatorio(token, montar_dados_precatorio(dado, token))
        adicionar_documento_precatorio(token, id_documento,
                                       util.get_atach_rest_base(dado['Ofício Requisitório'][0]['id']))
        atualizar_arteria(
            {
                'id portal precatórios': id,
                'Valor Pago pelo Parceiro/Cliente': valor.replace('.', ',')
            },
            dado['ID de rastreamento'])
