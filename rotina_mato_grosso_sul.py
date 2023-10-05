import os
import re
import PyPDF2
import xmltodict
import traceback
from banco_de_dados import consultar_processos
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_amazonas_precatorios import get_docs_oficio_precatorios_tjam
from utils import apagar_arquivos_txt, encontrar_indice_linha, extrair_processo_origem, extrair_processo_origem_amazonas, limpar_dados, mandar_dados_regex, pegar_cpf_e_credor,  regex, tipo_precatorio, verificar_tribunal

def ler_xml(arquivo_xml):     
  dados = consultar_processos('.8.12.')
  with open(arquivo_xml, 'r', encoding='utf-8') as fd:
    doc = xmltodict.parse(fd.read())
  dados = []
  base_doc = doc['Pub_OL']['Publicacoes']
  for i in range(len(doc['Pub_OL']['Publicacoes'])):
    processo_origem =  extrair_processo_origem(f"{base_doc[i]['Publicacao']})")
    if verificar_tribunal(f"{base_doc[i]['Processo']}"):
      processo_origem = extrair_processo_origem_amazonas(f"{base_doc[i]['Publicacao']})", f"{base_doc[i]['Processo']}")
    dados.append({"processo": f"{base_doc[i]['Processo']}", "tribunal": f"{base_doc[i]['Tribunal']}", "materia": f"{base_doc[i]['Materia']}", 'origem': processo_origem})

  for d in dados:
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        if verificar_tribunal(d['processo']) and d['origem'] != '':
          ler_documentos(dado)
        else:
          pass
  apagar_arquivos_txt(['./arquivos_txt_mato_grosso_sul', './arquivos_pdf_mato_grosso_do_sul','./fotos_oab', './arquivos_texto_ocr', './pdf_oab'])

def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.4.03.\d{4}'
        processo = re.search(padrao, n_processo)
        print(n_processo)
        if processo != None:
          return True
        
def ler_documentos(dado_xml):
      try:
        processo_geral = dado_xml['origem']
        doc = get_docs_oficio_precatorios_tjam(dado_xml['origem'],zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          arquivo_pdf = f"arquivos_pdf_amazonas/{processo_geral}_arquivo_precatorio.pdf"
          for i in range(len(doc[codigo_processo])):
              arquivo_pdf = f"arquivos_pdf_amazonas/{processo_geral}_{i + 1}_arquivo_precatorio.pdf"
              file_path = doc[codigo_processo][i][1]
              pdf_precatorio = verificar_pdf(processo_geral, file_path, arquivo_pdf, i+1)
              if pdf_precatorio:
                dados_pdf = extrair_dados_pdf(f"arquivos_txt_amazonas/{processo_geral}_{i + 1}_extrair.txt")
                if dados_pdf['devedor'] != '' and dados_pdf['credor'] != '' and dados_pdf['global'] != '':
                  dados = dado_xml | dados_pdf | {"processo_geral": processo_geral,'codigo_processo': codigo_processo, 'site': 'https://consultasaj.tjam.jus.br/', 'tipo_precatorio': 'MUNICIPAL', 'estado': 'AMAZONAS'}
      except Exception as e:
        print(f"Erro! Processo -> {processo_geral}", e)
        print(traceback.print_exc())
        pass

def verificar_pdf(processo_geral, doc_codigo_processo, arquivo_pdf, cod):
  encontrado = False
  with open(arquivo_pdf, "wb") as arquivo:
    arquivo.write(doc_codigo_processo)
  pdf_file = open(arquivo_pdf, 'rb')
  pdf_reader = PyPDF2.PdfReader(pdf_file)
  for page_num in range(len(pdf_reader.pages)): 
      page = pdf_reader.pages[page_num]
      texto_extraido = page.extract_text()
      if 'REQUISIÇÃO  DE PRECATÓRIO' in texto_extraido or 'ofício  precatório' in texto_extraido:
        encontrado = True
        break
  if encontrado:
    with open(f"arquivos_txt_amazonas/{processo_geral}_{cod}_extrair.txt", "w", encoding='utf-8') as arquivo:
      text = ''
      for page_num in range(len(pdf_reader.pages)): 
        page = pdf_reader.pages[page_num]
        text += page.extract_text()
      arquivo.write(text)
      return True
  else:
    pdf_file.close()
    os.remove(arquivo_pdf)

    return False

def extrair_dados_pdf(arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()

    indice_vara = encontrar_indice_linha(linhas, "Vara  ")
    indice_advogado = encontrar_indice_linha(linhas, 'Advogad')
    indice_honorarios = encontrar_indice_linha(linhas, 'Valor de Honorários')
    indice_juizado = encontrar_indice_linha(linhas, " Juizado")
    indice_cidade = encontrar_indice_linha(linhas, 'E-mail')
    indice_principal = encontrar_indice_linha(linhas, "Valor  Bruto:")
    indice_global = encontrar_indice_linha(linhas, "R$")
    indice_natureza = encontrar_indice_linha(linhas, "ALIMENTAR COMUM") + 1
    indice_devedor = encontrar_indice_linha(linhas, "público  devedor")
    indice_cpf_credor = encontrar_indice_linha(linhas, "CPF") + 1
    indice_nascimento = encontrar_indice_linha(linhas, "Data  de Nascimento")
    indice_nasceu = encontrar_indice_linha(linhas, "Beneficiário:")
    indice_expedicao = encontrar_indice_linha(linhas, "liberado nos autos")

    indices = {'indice_vara': indice_vara,
              'indice_juizado': indice_juizado,
              'indice_cidade':indice_cidade,
              'indice_global': indice_global,
              'indice_devedor': indice_devedor,
              'indice_natureza':indice_natureza, 
              'indice_expedicao': indice_expedicao, 
              'indice_nascimento': indice_nascimento,
              'indice_nasceu': indice_nasceu,
              'indice_principal': indice_principal}
    
    dados = mandar_dados_regex(indices, linhas)

    if dados['global'] == '':
      valor = linhas[indice_global + 2]
      dados['global'] = valor.strip().replace('.','').replace(',','.') 
    
    cpf_credor = pegar_cpf_e_credor(indice_cpf_credor, linhas)
    principal_e_juros = principal_e_juros_linha(linhas)
    dados_limpos = remover_e_reatribuir_dados(dados)
    if indice_advogado > 1:
      advogado_e_oab = regex(linhas[indice_advogado])
    else:
      return {'advogado': '', 'oab': ''}
    dados = dados_limpos | dados | cpf_credor | principal_e_juros | advogado_e_oab 
    dados['cpf_cnpj'] = dados.pop('cpf')
    return dados
    
def remover_e_reatribuir_dados(dados):
    chaves_a_verificar = [('juizado', 'vara'), ('vara_pdf', 'vara'), ('nasceu', 'nascimento')]
    for chave_antiga, chave_nova in chaves_a_verificar:
        if chave_antiga in dados:
            valor = dados[chave_antiga]
            if valor != '':
                dados[chave_nova] = valor
            del dados[chave_antiga]

    return dados

def principal_e_juros_linha(linhas):
  principal = ''
  juros = ''
  for linha in linhas:
    if 'R$' in linha:
      padrao = r'R\$ (\d{1,3}(?:\.\d{3})*(?:,\d{2}))\s*(?:%0\.(\d) )?(.*?)\s*R\$ (\d{1,3}(?:\.\d{3})*(?:,\d{2}))'
      result = re.search(padrao, linha)
      if result != None:  
        principal_e_juros = linha.split('R$')
        principal = principal_e_juros[1].strip().split(' ')[0].replace('.','').replace(',','.')
        juros = principal_e_juros[2].strip().split(' ')[0].replace('.','').replace(',','.')
        break
  return {'principal': principal, 'juros': juros}


def pegar_processo_origem(texto, indice):
  for i in dict.keys(indice):
      if indice[i] != None:
        origem = texto[indice[i]].replace('\n', '').replace(',', '').strip()
        return {'origem': origem}
      else:
          return {'origem': ''}
      
ler_xml('arquivos_xml/relatorio_12_09.xml')
# extrair_dados_pdf('arquivos_txt_amazonas/0231203-59.2010.8.04.0001_2_extrair.txt')