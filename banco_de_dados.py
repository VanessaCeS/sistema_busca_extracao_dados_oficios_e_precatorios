import os
import traceback
import mysql.connector
from dotenv import load_dotenv
from utils import processar_dado
load_dotenv('.env')

def pesquisar_pessoa_por_documento_ou_oab(conn, valor_pesquisa):
    cursor = conn.cursor(dictionary=True)
    query = 'SELECT * FROM pessoas WHERE documento = %s OR oab = %s'
    cursor.execute(query, (valor_pesquisa, valor_pesquisa))
    pessoa = cursor.fetchone()
    cursor.close()
    return pessoa

def atualizar_ou_inserir_pessoa(doc, dados):
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

def mandar_precatorios_para_banco_de_dados(codigo_processo, dados):
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
    database='precatorias_tribunais'
    )

    cursor = conn.cursor()
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
