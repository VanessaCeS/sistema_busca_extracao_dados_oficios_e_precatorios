import os
import traceback
from auxiliares import apagar_arquivos
from rotina_processos_infocons import buscar_xml
from rotina_acre import buscar_dados_tribunal_acre
from rotina_alagoas import buscar_dados_tribunal_alagoas
from rotina_amazonia import buscar_dados_tribunal_amazonas
from rotina_rio_de_janeiro import buscar_dados_tribunal_rio_de_janeiro
from rotina_sao_paulo import buscar_dados_tribunal_sao_paulo
from rotina_eproc_trfs import buscar_dados_tribunal_regional_federal
from rotina_mato_grosso_sul import buscar_dados_tribunal_mato_grosso_do_sul

lista_de_pastas = os.getenv('lista_de_pastas')
try:
  buscar_xml()
  buscar_dados_tribunal_sao_paulo()
  buscar_dados_tribunal_alagoas()
  buscar_dados_tribunal_acre()
  buscar_dados_tribunal_amazonas()
  buscar_dados_tribunal_mato_grosso_do_sul()
  buscar_dados_tribunal_regional_federal()
  buscar_dados_tribunal_rio_de_janeiro()
  apagar_arquivos(lista_de_pastas)

except Exception as e:
  print(f"Error -->> ", e)
  print(traceback.print_exc())