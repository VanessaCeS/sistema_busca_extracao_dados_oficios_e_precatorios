import re
import PyPDF2
import traceback
from banco_de_dados import consultar_processos
from rotina_alagoas_pdf_simples import extrair_dados_pdf
from rotina_alagoas_pdf_img import extrair_dados_texto_ocr
from utils import  limpar_dados, tipo_precatorio
from esaj_alagoas_precatorios import get_docs_oficio_precatorios_tjal

def buscar_dados_tribunal_alagoas():   
  dados = consultar_processos('.8.02.')

  for d in dados:
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        if verificar_tribunal(d['processo']):
          ler_documentos(dado)



def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.8.02.\d{4}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True

def ler_documentos(dado_xml):
      try:
          processo_geral = dado_xml['processo']
          doc = get_docs_oficio_precatorios_tjal(dado_xml['processo'],zip_file=False, pdf=True)
          if doc != None:
            codigo_processo = next(iter(doc))
            id_documento = doc[codigo_processo][0][0]
            dados_gerais = {'processo_geral': processo_geral, 'site': 'https://www2.tjal.jus.br/esaj/', 'tipo': 'ESTADUAL', 'estado': 'ALAGOAS','codigo_processo': codigo_processo, 'id_documento': id_documento}
            dado_xml = dado_xml | dados_gerais
            arquivo_pdf = f"arquivos_pdf_alagoas/{processo_geral}_arquivo_precatorio.pdf"
            merge = PyPDF2.PdfMerger()
            for chave, valor in doc.items():
              for i in range(len(valor)):
                file_path = valor[i][2]
                with open(f"arquivos_pdf_alagoas/{processo_geral}_{i+1}_arquivo_precatorio.pdf", "wb") as arquivo:
                      arquivo.write(file_path)
                merge.append(f"arquivos_pdf_alagoas/{processo_geral}_{i+1}_arquivo_precatorio.pdf")
            merge.write(arquivo_pdf)
            
            pdf_file = open(arquivo_pdf, 'rb')
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            number_pages = len(pdf_reader.pages)
            if number_pages > 1:
                extrair_dados_pdf(arquivo_pdf, dado_xml)
            else:
                extrair_dados_texto_ocr(arquivo_pdf, dado_xml, )
      except Exception as e:
        print("Erro no processo -> ", processo_geral, f'Erro: {e}')
        print(traceback.print_exc())
        pass
