import re
import PyPDF2
import traceback
import xmltodict
from rotina_sao_paulo import apagar_arquivos_txt
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_acre_precatorios import get_docs_oficio_precatorios_tjac
from utils import buscar_cpf, buscar_xml, encontrar_indice_linha, extrair_processo_origem, limpar_dados, mandar_documento_para_ocr, mandar_para_banco_de_dados, regex, natureza_tjac, tipo_precatorio, verificar_tribunal

def ler_xml():
  arquivo_xml = buscar_xml()
  with open(arquivo_xml, 'r', encoding='utf-8') as fd:
    dados = []
    doc = xmltodict.parse(fd.read())
    base_doc = doc['Pub_OL']['Publicacoes']
    for i in range(len(doc['Pub_OL']['Publicacoes']))  :
      processo_origem =  extrair_processo_origem(f"{base_doc[i]['Publicacao']})")
      requerente, requerido, valor = pegar_requerido_xml(f"{base_doc[i]['Publicacao']})")
      dados.append({"processo": f"{base_doc[i]['Processo']}", "tribunal": f"{base_doc[i]['Tribunal']}", "materia": f"{base_doc[i]['Materia']}", 'origem': processo_origem, 'requerido': requerido, 'requerente': requerente, 'valor': valor})

    for d in dados:
          dados_limpos = limpar_dados(d)
          tipo = tipo_precatorio(d)
          dado = dados_limpos | tipo
          if verificar_tribunal(d['processo']):
            ler_documentos(dado)
          else:
            pass
    apagar_arquivos_txt()

def ler_documentos(dado):
      try:
        processo_geral = dado['processo']
        doc = get_docs_oficio_precatorios_tjac(dado['processo'],zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          file_path = doc[codigo_processo][0][1]
          arquivo_pdf = f"arquivos_pdf_acre/{processo_geral}_arquivo_precatorio.pdf"

          with open(arquivo_pdf, "wb") as arq:
                arquivo = arq.write(file_path)

          arquivo_cortado = cortar_pags_especifica(arquivo)
          arquivo_ocr = mandar_documento_para_ocr(arquivo_cortado, processo_geral)
          dados = dividir_linhas_arquivo(arquivo_ocr)

          id_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
          dados = dados | {'id_rastreamento': id_arteria}
          mandar_para_banco_de_dados(dado['codigo_processo'], dados)
      except Exception as e:
        print(f"Erro no processo -> ", processo_geral, 'Erro: ', e)
        print(traceback.print_exc())
        pass


def dividir_linhas_arquivo(nome_arquivo):
    try:
        valores_regex = []
        natureza = natureza_tjac(nome_arquivo)
        cpf = buscar_cpf(nome_arquivo)
        with open(nome_arquivo, 'r', encoding='utf-8') as arquivo:
            linhas = arquivo.readlines()
            indice_nascimento = encontrar_indice_linha(linhas, "DATA DE NASCIMENTO") + 4
            indice_data_expedicao = encontrar_indice_linha(linhas, "Endereço:") - 1
            indices = {'indice_data_expedicao': indice_data_expedicao, 'indice_nascimento': indice_nascimento}
            data = {}
            for i in dict.keys(indices):
              nome = i.split('_')[1]
              if indices[i] != None:
                valores = linhas[indices[i]]
                valores_regex = regex(valores)
                if valores_regex == None:
                  valores_regex = {f'{nome}': ''}
                data = data | valores_regex
              else:
                data = data | {f'{nome}': ''}
            dados_completos = data | natureza| cpf

        return dados_completos
    except FileNotFoundError:
        print(f"O arquivo '{nome_arquivo}' não foi encontrado.")
        return {}
    
def pegar_requerido_xml(dados):
  if 'Requerente' in dados:
    padrao = r'Requerente:(.*)'
    resultado = re.search(padrao, dados, re.IGNORECASE)
    if resultado != None:
      requerente = resultado.group(1).strip()
    else:
        requerente = ''
  if 'Requerido' in dados:
    padrao = r'Requerido:(.*)'
    resultado = re.search(padrao, dados, re.IGNORECASE)
    if resultado != None:
      requerido = resultado.group(1).strip()
      print('requerido --->> ', requerido)
    else:
      requerido = ''
  if 'no valor' in dados:
    padrao =  r'R\$ ([\d.,]+)'
    resultado = re.search(padrao, dados, re.IGNORECASE)
    if resultado != None:
      valor = resultado.group(1).strip()
      print('valor --->> ', valor)
    else:
      valor = ''
  return  requerente, requerido, valor

def pegar_pags_especifica(dados, arquivo):
  pdf_file = open(arquivo, 'rb')
  pdf_reader = PyPDF2.PdfReader(pdf_file)
  pdf_writer = PyPDF2.PdfWriter()
  nome = arquivo.split('_merged')[0]
  print(dados[0])
  for i in range(len(dados)):
    if 'cpf_cnpj' in dict.keys(dados[i]):
      for pagina_num in range(len(pdf_reader.pages)):
        if 'fls. 4' in page_text or 'fls. 5' in page_text:
              pdf_writer.add_page(page)
              with open(f'{nome}_cortado.pdf', 'ab') as novo_pdf_file:
                novo_pdf = pdf_writer.write(novo_pdf_file)
    if 'nascimento' in dict.keys(dados[i]):
      for pagina_num in range(len(pdf_reader.pages)):
          page = pdf_reader.pages[pagina_num] 
          page_text = page.extract_text()
          if 'fls. 5' in page_text:
              pdf_writer.add_page(page)
              with open(f'{nome}_cortado.pdf', 'ab') as novo_pdf_file:
                  novo_pdf = pdf_writer.write(novo_pdf_file)
  return novo_pdf

def cortar_pags_especifica(arquivo):
  pdf_file = open(arquivo, 'rb')
  pdf_reader = PyPDF2.PdfReader(pdf_file)
  pdf_writer = PyPDF2.PdfWriter()
  nome = arquivo.split('/')[1]
  novo_pdf = ''
  for pagina_num in range(len(pdf_reader.pages)):
    page = pdf_reader.pages[pagina_num] 
    page_text = page.extract_text()
    if 'fls. 2' in page_text or 'fls. 3' in page_text or 'fls. 4' in page_text:
      pdf_writer.add_page(page)
      with open(f'arquivos_cortados/{nome}_cortado.pdf', 'ab') as novo_pdf_file:
        novo_pdf = pdf_writer.write(novo_pdf_file)
  return novo_pdf
dividir_linhas_arquivo('aquiiiiiii.txt')
# ler_documentos('arquivos_cortados/0100145-70.2017.8.01.0000.pdf_cortado.pdf')