import os
import re
import traceback
import mysql.connector
from dotenv import load_dotenv
from auxiliares import dados_limpos_banco_de_dados, extrair_processo_origem, extrair_processo_origem_amazonas, processar_dado, procurar_precatorio_trf
load_dotenv('.env')

def consultar_processos(valor_tribunal):
  conn = mysql.connector.connect(
    host=os.getenv('db_server_precatorio'),
    user=os.getenv('db_username_precatorio'),
    password=os.getenv('db_password_precatorio'),
    database=os.getenv('db_database_precatorio')
    )
  dados = []
  processo_origem = ''

  cursor = conn.cursor()
  consulta_sql = "SELECT * FROM processos WHERE processo LIKE '%{}%' AND status NOT IN ('Sucesso') ORDER BY data_criacao DESC".format(valor_tribunal)

  cursor.execute(consulta_sql)
  resultados = cursor.fetchall()
  for registro in resultados:
        if registro[4] != 'STFSITE':
            id_processo = registro[0]
            processo = registro[2]
            materia = registro[3]
            tribunal = registro[4]
            print('processo ---> ', processo)
            if pesquisar_processo_em_precatorios(processo):
                consulta_publicacao = "SELECT publicacao FROM publicacoes WHERE id_processo LIKE '%{}%' ORDER BY data_criacao DESC".format(id_processo)
                cursor.execute(consulta_publicacao)
                publicacoes = cursor.fetchall()
                for publicacao in publicacoes:
                        atualizar_ou_inserir_situacao_cadastro(processo, {'status': 'pesquisado'})
                        if not any(item in processo for item in ['.4.02.', '.4.04.','8.08.', '.8.16.', '.8.19', '.8.21.', '.8.24.']):
                            processo_origem = extrair_processo_origem(publicacao[0].replace('\n', ''),processo)
                            if processo_origem == '':
                                if verificar_tribunal(processo, valor_tribunal):
                                    processo_origem = extrair_processo_origem_amazonas(publicacao[0].replace('\n', ''), processo)
                        else:
                            processo_origem = procurar_precatorio_trf(publicacao[0],processo)
                if processo_origem == None:
                        processo_origem = ''
                dados.append({"processo": processo, "tribunal": tribunal, "materia": materia, 'processo_origem': processo_origem})
        
  cursor.close()
  conn.close()
  return dados

def verificar_tribunal(n_processo, n_tribunal):
        padrao = fr'\d{{7}}-\d{{2}}.*?{re.escape(n_tribunal)}.*?\d{{4}}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True

def pesquisar_pessoa_por_documento_ou_oab(conn, valor_pesquisa):
    cursor = conn.cursor(dictionary=True)
    query = 'SELECT * FROM pessoas WHERE documento = %s OR oab = %s'
    cursor.execute(query, (valor_pesquisa, valor_pesquisa))
    pessoa = cursor.fetchone()
    cursor.close()
    return pessoa

def pesquisar_processo_em_precatorios(processo):
  conn = mysql.connector.connect(
        host=os.getenv('db_server_precatorio'),
        user=os.getenv('db_username_precatorio'),
        password=os.getenv('db_password_precatorio'),
        database=os.getenv('db_database_precatorio'))
    
  cursor = conn.cursor()
  query = 'SELECT id_precatorio FROM precatorios WHERE processo = %s'
  cursor.execute(query, (processo,))
  id_precatorio = cursor.fetchone()
  if id_precatorio is None:
      return True
  else:
      return False

def atualizar_ou_inserir_pessoa_no_banco_de_dados(doc, dados):
    conn = mysql.connector.connect(
        host=os.getenv('db_server_precatorio'),
        user=os.getenv('db_username_precatorio'),
        password=os.getenv('db_password_precatorio'),
        database=os.getenv('db_database_precatorio'))
    
    cursor = conn.cursor()

    try:
        documento = dados.get('documento')
        oab = dados.get('oab')
        pessoa = pesquisar_pessoa_por_documento_ou_oab(conn, doc)
        
        if pessoa is not None:
            dados_processados = processar_dado(dados)
            colunas_e_valores = ', '.join([f"{coluna} = %s" for coluna in dados_processados.keys()])
            query = f"UPDATE pessoas SET {colunas_e_valores} WHERE documento = %s OR oab = %s"
            valores = list(dados_processados.values()) + [documento, oab]
            cursor.execute(query, valores)
        else:
            dado_processado = {key: (value if value != '' else None) for key, value in dados.items()}
            colunas = ', '.join(dado_processado.keys())
            valores = ', '.join(['%s'] * len(dado_processado))
            query = f"INSERT INTO pessoas ({colunas}) VALUES ({valores})"
            valores_insercao = tuple(dado_processado.values())
            cursor.execute(query, valores_insercao)
        conn.commit()
    except Exception as e:
        print("Erro: ", e)
    finally:
        cursor.close()

def atualizar_ou_inserir_precatorios_no_banco_de_dados(codigo_processo, dados):
    conn = mysql.connector.connect(
    host=os.getenv('db_server_precatorio'),
    user=os.getenv('db_username_precatorio'),
    password=os.getenv('db_password_precatorio'),
    database=os.getenv('db_database_precatorio')
    )

    dados = dados_limpos_banco_de_dados(dados)
    cursor = conn.cursor(buffered=True)
    query_consultar_codigo_processo = 'SELECT * FROM precatorios WHERE codigo_processo = %s'
    cursor.execute(query_consultar_codigo_processo, (codigo_processo,))
    codigo_processo = cursor.fetchone()
    if codigo_processo is not None and int(dados['qtd_credores']) == 1:
      try:
                del dados['qtd_credores']
                dados_processados = processar_dado(dados)
                colunas_e_valores = ', '.join([f"{coluna} = %s" for coluna in dados_processados.keys()])
                query = f"UPDATE precatorios SET {colunas_e_valores} WHERE codigo_processo = %s"
                valores = tuple(list(dados_processados.values()) + [dados_processados['codigo_processo']])
                cursor.execute(query, valores)
                conn.commit()
                conn.close()
      except Exception as e:
                print("E ==>> ", e)
                print("Exec ==>> ", traceback.print_exc())
    else:
      try:
        del dados['qtd_credores']
        dado_processado = {key: (value if value != '' else None) for key, value in dados.items()}
        colunas = ', '.join(dado_processado.keys())
        valores = ', '.join(['%s'] * len(dado_processado))
        query = f"INSERT INTO precatorios ({colunas}) VALUES ({valores})"
        valores_insercao = tuple(dado_processado.values())
        cursor.execute(query, valores_insercao)
        conn.commit()
        cursor.close()
        conn.close()
      except Exception as e:
                print("E ==>> ", e)
                print("Exec ==>> ", traceback.print_exc())

def atualizar_ou_inserir_pessoa_precatorio(documento, processo):
    conn = mysql.connector.connect(
    host=os.getenv('db_server_precatorio'),
    user=os.getenv('db_username_precatorio'),
    password=os.getenv('db_password_precatorio'),
    database=os.getenv('db_database_precatorio')
    )

    cursor = conn.cursor(buffered=True)
    query_consultar_pessoa = 'SELECT * FROM pessoas WHERE documento = %s'
    cursor.execute(query_consultar_pessoa, (documento,))
    pessoa = cursor.fetchone()

    query_consultar_pessoa = 'SELECT * FROM precatorioS WHERE processo = %s'
    cursor.execute(query_consultar_pessoa, (processo,))
    precatorio = cursor.fetchone()

    if pessoa is not None and precatorio is not None:
        id_pessoa = pessoa[0]
        id_precatorio = precatorio[0]
        tipo = ''
        if pessoa[2] is not None and pessoa[4] is None:
            tipo = 'credor'
        elif pessoa[4] is not None:
            tipo = 'advogado'

        dados = {'id_pessoa': id_pessoa, 'id_precatorio': id_precatorio, 'tipo': tipo}

        query_consultar_pessoa_precatorio = 'SELECT * FROM pessoa_precatorio WHERE id_pessoa = %s'
        cursor.execute(query_consultar_pessoa_precatorio, (id_pessoa,))
        pessoa_precatorio = cursor.fetchone()
        if pessoa_precatorio is not None:
            try:
                        dados_processados = processar_dado(dados)
                        colunas_e_valores = ', '.join([f"{coluna} = %s" for coluna in dados_processados.keys()])
                        query = f"UPDATE pessoa_precatorio SET {colunas_e_valores} WHERE id_pessoa = %s"
                        valores = tuple(list(dados_processados.values()) + [dados_processados['id_pessoa']])
                        cursor.execute(query, valores)
                        conn.commit()
                        conn.close()
            except Exception as e:
                        print("E ==>> ", e)
                        print("Exec ==>> ", traceback.print_exc())
        else:
            try:
                dado_processado = {key: (value if value != '' else None) for key, value in dados.items()}
                colunas = ', '.join(dado_processado.keys())
                valores = ', '.join(['%s'] * len(dado_processado))
                query = f"INSERT INTO pessoa_precatorio ({colunas}) VALUES ({valores})"
                valores_insercao = tuple(dado_processado.values())
                cursor.execute(query, valores_insercao)
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                        print("E ==>> ", e)
                        print("Exec ==>> ", traceback.print_exc())
                        
def inserir_log_no_banco_de_dados(dados):
    conn = mysql.connector.connect(
    host=os.getenv('db_server_precatorio'),
    user=os.getenv('db_username_precatorio'),
    password=os.getenv('db_password_precatorio'),
    database=os.getenv('db_database_precatorio')
    )
    cursor = conn.cursor(buffered=True)

    try:
        dado_processado = {key: (value if value != '' else None) for key, value in dados.items()}
        colunas = ', '.join(dado_processado.keys())
        valores = ', '.join(['%s'] * len(dado_processado))
        query = f"INSERT INTO log_rotina_esaj ({colunas}) VALUES ({valores})"
        valores_insercao = tuple(dado_processado.values())
        cursor.execute(query, valores_insercao)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("E ==>> ", e)
        print("Exec ==>> ", traceback.print_exc())

def atualizar_ou_inserir_situacao_cadastro(n_processo, status):
    conn = mysql.connector.connect(
    host=os.getenv('db_server_precatorio'),
    user=os.getenv('db_username_precatorio'),
    password=os.getenv('db_password_precatorio'),
    database=os.getenv('db_database_precatorio')
    )

    cursor = conn.cursor(buffered=True)
    query_consultar_processo = 'SELECT * FROM processos WHERE processo = %s'
    cursor.execute(query_consultar_processo, (n_processo,))
    processo = cursor.fetchone()
    if processo is not None:
      try:
                dados_processados = processar_dado(status)
                colunas_e_valores = ', '.join([f"{coluna} = %s" for coluna in dados_processados.keys()])
                query = f"UPDATE processos SET {colunas_e_valores} WHERE processo = %s"
                valores = tuple(list(dados_processados.values()) + [n_processo])
                cursor.execute(query, valores)
                conn.commit()
                conn.close()
      except Exception as e:
                print("E ==>> ", e)
                print("Exec ==>> ", traceback.print_exc())
    