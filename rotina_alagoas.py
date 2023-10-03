import re
import PyPDF2
import xmltodict
import traceback
from rotina_alagoas_pdf_simples import extrair_dados_pdf
from rotina_alagoas_pdf_img import extrair_dados_texto_ocr
from esaj_alagoas_precatorios import get_docs_oficio_precatorios_tjal
from rotina_processos_infocons import buscar_xml
from utils import apagar_arquivos_txt, data_corrente_formatada, extrair_processo_origem, limpar_dados, tipo_precatorio, verificar_tribunal

def ler_xml(arquivo_xml):     
  
  with open(arquivo_xml, 'r', encoding='utf-8') as fd:
    doc = xmltodict.parse(fd.read())

  dados = []
  base_doc = doc['Pub_OL']['Publicacoes']
  for i in range(len(doc['Pub_OL']['Publicacoes']))  :
    processo_origem =  extrair_processo_origem(f"{base_doc[i]['Publicacao']})")
    dados.append({"processo": f"{base_doc[i]['Processo']}", "tribunal": f"{base_doc[i]['Tribunal']}", "materia": f"{base_doc[i]['Materia']}", 'processo_origem': processo_origem})
    
  for d in dados:
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        if verificar_tribunal(d['processo']):
          ler_documentos(dado)
        else:
          pass

  apagar_arquivos_txt([])

def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.8.02.\d{4}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True

def ler_documentos(dado_xml):
      try:
          processo_geral = dado_xml['processo']
          doc = get_docs_oficio_precatorios_tjal(dado_xml['processo'],zip_file=False, pdf=True)
          if doc != {}:
            codigo_processo = next(iter(doc))
            id_documento = doc[codigo_processo][0][0]
            dados_gerais = {'processo_geral': processo_geral, 'site': 'https://www2.tjal.jus.br/esaj/', 'tipo': 'ESTADUAL', 'estado': 'ALAGOAS','codigo_processo': codigo_processo, 'id_documento': id_documento}
            dado_xml = dado_xml | dados_gerais
            arquivo_pdf = f"arquivos_pdf_alagoas/{processo_geral}_arquivo_precatorio.pdf"
            for i in range(len(doc[codigo_processo])):
              file_path = doc[codigo_processo][i][2]
              with open(arquivo_pdf, "ab") as arquivo:
                      arquivo.write(file_path)
              pdf_file = open(arquivo_pdf, 'rb')
              pdf_reader = PyPDF2.PdfReader(pdf_file)
              number_pages = len(pdf_reader.pages)
            if number_pages > 1:
                extrair_dados_pdf(arquivo_pdf, dado_xml)
            else:
                extrair_dados_texto_ocr(arquivo_pdf, dado_xml, )
      except Exception as e:
        print("Erro no processo -> ", f'Erro: {e}')
        print(traceback.print_exc())
        pass

ler_xml('arquivos_xml/relatorio_28_09.xml')