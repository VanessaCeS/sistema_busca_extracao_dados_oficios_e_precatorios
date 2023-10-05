import os
import PyPDF2
import traceback
from cna_oab import login_cna
from funcoes_arteria import enviar_valores_oficio_arteria
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, consultar_processos
from esaj_amazonas_precatorios import get_docs_oficio_precatorios_tjam
from utils import apagar_arquivos_txt, encontrar_indice_linha, limpar_dados, mandar_dados_regex, mandar_documento_para_ocr, regex, tipo_precatorio, verificar_tribunal

def ler_xml(arquivo_xml):   
  dados = consultar_processos('.8.04.')
  
  for d in dados:
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        if verificar_tribunal(d['processo']) and d['processo_origem'] != '':
          ler_documentos(dado)
        else:
          pass
  apagar_arquivos_txt(['./arquivos_txt_amazonas', './arquivos_pdf_amazonas', './fotos_oab', './arquivos_texto_ocr'])

def ler_documentos(dado_xml):
      try:
        processo_geral = dado_xml['processo_origem']
        doc = get_docs_oficio_precatorios_tjam(dado_xml['processo_origem'],zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          arquivo_pdf = f"arquivos_pdf_amazonas/{processo_geral}_arquivo_precatorio.pdf"
          dados_complementares = {"processo_geral": processo_geral,'codigo_processo':codigo_processo,'site':'https://consultasaj.tjam.jus.br/', 
            'tipo_precatorio':  'MUNICIPAL', 'estado': 'AMAZONAS'} | dado_xml
          for i in range(len(doc[codigo_processo])):
              arquivo_pdf = f"arquivos_pdf_amazonas/{processo_geral}_{i + 1}_arquivo_precatorio.pdf"
              file_path = doc[codigo_processo][i][1]
              pdf_precatorio = verificar_pdf(file_path, arquivo_pdf)
              if pdf_precatorio:
                  extrair_dados_pdf(arquivo_pdf, dados_complementares,f"arquivos_txt_amazonas/{processo_geral}_{i + 1}_extrair.txt")
      except Exception as e:
        print(f"Erro! Processo -> {processo_geral}", e)
        print(traceback.print_exc())
        pass

def verificar_pdf(doc_codigo_processo, arquivo_pdf):
  encontrado = False
  # with open(arquivo_pdf, "wb") as arquivo:
  #   arquivo.write(doc_codigo_processo)
  pdf_file = open(arquivo_pdf, 'rb')
  pdf_reader = PyPDF2.PdfReader(pdf_file)
  for page_num in range(len(pdf_reader.pages)): 
      page = pdf_reader.pages[page_num]
      texto_extraido = page.extract_text()
      if 'REQUISIÇÃO  DE PRECATÓRIO' in texto_extraido or 'ofício  precatório' in texto_extraido:
        encontrado = True
        break
  if encontrado:
    nome = arquivo_pdf.split('/')[1].split('_arquivo')[0]
    arquivo_txt = mandar_documento_para_ocr(arquivo_pdf, '1', nome)
    with open(arquivo_txt, "w", encoding='utf-8') as arquivo:
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
# verificar_pdf('', 'arquivos_pdf_amazonas/0231203-59.2010.8.04.0001_2_arquivo_precatorio.pdf')
def extrair_dados_pdf(arquivo_pdf, dados_xml, arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()
    dados_advogado = cortar_advogado(arquivo_txt)
    if dados_advogado == []:
      return  {'advogado': '', 'oab': '', 'telefone': '', 'documento_advogado': ''}
    else:
      pass

    indice_vara = encontrar_indice_linha(linhas, "Vara")
    indice_juizado = encontrar_indice_linha(linhas, "Juizado")
    indice_valor_global = encontrar_indice_linha(linhas, "de R$")
    indice_data_expedicao = encontrar_indice_linha(linhas, "liberado nos autos")
    indice_beneficiario = encontrar_indice_linha(linhas, "Beneficiário")
    indice_credor = encontrar_indice_linha(linhas, "Credor")
    indice_devedor = encontrar_indice_linha(linhas, "devedor")
    indice_nascimento = encontrar_indice_linha(linhas, "Nascimento")
    indice_valor_juros = encontrar_indice_linha(linhas,"dos Juros") + 1
    indice_valor_principal = encontrar_indice_linha(linhas,"Valor Corrigido") + 1
    indice_cidade = encontrar_indice_linha(linhas, 'Fone:')
    indice_documento = encontrar_indice_linha(linhas, "CPF") + 1
    
    juros = linhas[indice_valor_juros]
    if '(R$)' in juros or 'R$' in juros:
      indice_valor_juros = encontrar_indice_linha(linhas,"dos Juros") + 2
    if indice_vara == None:
      indice_vara = indice_juizado
    if indice_beneficiario != None:
      indice_credor = indice_beneficiario

    indices = {'indice_vara': indice_vara,
              'indice_cidade':indice_cidade,
              'indice_valor_global': indice_valor_global,
              'indice_devedor': indice_devedor,
              'indice_credor': indice_credor,
              'indice_data_expedicao': indice_data_expedicao, 
              'indice_nascimento': indice_nascimento,
              'indice_valor_principal': indice_valor_principal,
              'indice_valor_juros': indice_valor_juros,
              'indice_documento': indice_documento}
    
    dados = mandar_dados_regex(indices, linhas)
    valor_natureza = cortar_natureza(arquivo_txt)
    for nat in valor_natureza:
      natureza = regex(nat)

    dados = dados | dados_xml |  natureza | dados_advogado
    enviar_dados(arquivo_pdf, dados)
    
def remover_e_reatribuir_dados(dados):
    chaves_a_verificar = [('juizado', 'vara'), ('vara_pdf', 'vara'), ('nasceu', 'nascimento')]
    for chave_antiga, chave_nova in chaves_a_verificar:
        if chave_antiga in dados:
            valor = dados[chave_antiga]
            if valor != '':
                dados[chave_nova] = valor
            del dados[chave_antiga]

    return dados

def cortar_advogado(nome_arquivo):
        with open(nome_arquivo, 'r', encoding='utf-8') as arquivo:
            linhas = arquivo.readlines()
            encontrou_inicio = False
            texto_cortado = []
            for linha in linhas:
                if "honorários contractuais" in linha or 'Procurador  do beneficiário OAB' in linha or 'Honorários  Contratuais:' in linha:
                    encontrou_inicio = True
                    texto_cortado.append(linha)
                if encontrou_inicio:
                    texto_cortado.append(linha)
                if '•Natureza  da obrigação  (assunto)  a que se refere  o pagamento:' in linha:
                    encontrou_inicio = False
                    break
            aqui = ' '.join(texto_cortado)
            print(aqui)
            return ' '.join(texto_cortado)

cortar_advogado('arquivos_texto_ocr/0231203-59.2010.8.04.0001_2_texto_ocr.txt')

def cortar_natureza(nome_arquivo):
        with open(nome_arquivo, 'r', encoding='utf-8') as arquivo:
            linhas = arquivo.readlines()
            encontrou_inicio = False
            texto_cortado = []
            for linha in linhas:
                if "ALIMENTAR" in linha:
                    encontrou_inicio = True
                    texto_cortado.append(linha)
                if encontrou_inicio:
                    texto_cortado.append(linha)
                if "Residencial  do Credor  (Art. 78, § 3º, ADCT)" in linha or 'Residencial  do Credor  (Art.  78, § 3º, ADCT)' in linha:
                    encontrou_inicio = False
                    break
            aqui = '\n'.join(texto_cortado)
            with open('cortado.txt', 'w') as f:
              f.write(aqui)

            return '\n'.join(texto_cortado)
        
def pegar_processo_origem(texto, indice):
  for i in dict.keys(indice):
      if indice[i] != None:
        origem = texto[indice[i]].replace('\n', '').replace(',', '').strip()
        return {'processo_origem': origem}
      else:
          return {'processo_origem': ''}
      
def pegar_cidade(texto, indice):
    for i in dict.keys(indice):
      if indice[i] != None:
        cidade = texto[indice[i]].replace('\n', '').replace(',', '').replace('.', '').strip()
        return {'cidade': cidade}
      else:
          return {'cidade': ''}

def enviar_dados(arquivo_pdf, dados):
  atualizar_ou_inserir_pessoa_no_banco_de_dados(dados['documento'], dados)
  id_sistema_arteria = enviar_valores_oficio_arteria(arquivo_pdf, dados)
  dados['id_sistema_arteria'] = id_sistema_arteria
  atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
  atualizar_ou_inserir_pessoa_precatorio(dados['documento'], dados['processo'])

