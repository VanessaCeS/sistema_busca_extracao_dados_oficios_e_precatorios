from rotina_processos_infocons import buscar_xml
from rotina_sao_paulo import buscar_dados_tribunal_sao_paulo
from rotina_alagoas import buscar_dados_tribunal_alagoas
from rotina_acre import buscar_dados_tribunal_acre
from rotina_amazonas import buscar_dados_tribunal_amazonas
from rotina_mato_grosso_do_sul import buscar_dados_tribunal_mato_grosso_do_sul
import traceback

try:
  buscar_xml()
  buscar_dados_tribunal_sao_paulo()
  buscar_dados_tribunal_alagoas()
  buscar_dados_tribunal_acre()
  buscar_dados_tribunal_amazonas()
  buscar_dados_tribunal_mato_grosso_do_sul()
except Exception as e:
  print(f"Error -->> ", e)
  print(traceback.print_exc())