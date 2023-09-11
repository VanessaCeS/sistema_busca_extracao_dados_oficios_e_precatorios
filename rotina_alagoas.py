import traceback
import PyPDF2
from utils import encontrar_indice_linha, regex
def ler_documentos(dado):
      try:
        # processo_geral = dado['processo']
        # doc = get_docs_oficio_precatorios_tjac(dado['processo'],zip_file=False, pdf=True)
        # if doc != {}:
        #   codigo_processo = next(iter(doc))
        #   file_path = doc[codigo_processo][0][1]
          processo_geral = 'doc_109036052'
          arquivo_pdf = f"arquivos_pdf_alagoas\doc_109036052.pdf"

          with open(arquivo_pdf, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            if len(pdf_reader.pages) > 0:
              with open('doc_109036052.txt', 'w', encoding='utf-8') as txt_file:
                  for page_num in range(len(pdf_reader.pages)):
                      page = pdf_reader.pages[page_num]
                      page_text = page.extract_text()
                      txt_file.write(page_text)
          # extrair_dados_pdf('109036052.txt')
      except Exception as e:
        print(f"Erro meno, processo -> {processo_geral}", e)
        print(traceback.print_exc())
        pass

def extrair_dados_pdf(arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()    
    indice_processo = encontrar_indice_linha(linhas, "Número  do processo:")
    indice_vara = encontrar_indice_linha(linhas, "Origem/Foro  Comarca/  Vara:")
    indice_valor = encontrar_indice_linha(linhas, "Valor  originário:")
    indice_valor_total = encontrar_indice_linha(linhas, "Valor  total da requisição:")
    indice_juros = encontrar_indice_linha(linhas, "Valor  dos juros  moratórios:")
    indice_natureza = encontrar_indice_linha(linhas, "Natureza  do Crédito:")
    indice_credor = encontrar_indice_linha(linhas, "Nome  do Credor:")
    indice_devedor = encontrar_indice_linha(linhas, "Ente Devedor:")
    indice_cpf = encontrar_indice_linha(linhas, "CPF")
    indice_nascimento = encontrar_indice_linha(linhas, "Data  de nascimento:")
    indice_data_expedicao = encontrar_indice_linha(linhas, "liberado nos autos")
    indice_cidade = encontrar_indice_linha(linhas, "datado") - 1

    
    indices = {'indice_processo': indice_processo,'indice_vara': indice_vara,'indice_valor': indice_valor, 'indice_valor_total': indice_valor_total, 'indice_credor': indice_credor,'indice_devedor': indice_devedor,'indice_cidade': indice_cidade, 'indice_data_expedicao': indice_data_expedicao,'indice_natureza': indice_natureza,'indice_juros': indice_juros, 'indice_cpf': indice_cpf, 'indice_nascimento': indice_nascimento}
    dados = {}

    for i in dict.keys(indices):
      nome = i.split('_')[1]
      if indices[i] != None:
        valores = linhas[indices[i]]
        aqui = regex(valores)
        if aqui == None:
          aqui = {f'{nome}': ''}
          dados = dados | aqui
        else:
          dados = dados | {f'{nome}': ''}

    return dados
extrair_dados_pdf('./arquivos_txt_alagoas/doc_107672968.txt')
# ler_documentos('./arquivos_pdf_alagoas/doc_109036052.pdf')