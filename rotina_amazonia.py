import re
import PyPDF2
import xmltodict
import traceback
from esaj_amazonas_precatorios import get_docs_oficio_precatorios_tjam
from funcoes_arteria import enviar_valores_oficio_arteria

from utils import apagar_arquivos_txt, encontrar_indice_linha, extrair_processo_origem, extrair_processo_origem_amazonas, limpar_dados, mandar_para_banco_de_dados, principal_e_juros_poupanca, regex, tipo_precatorio, verificar_tribunal

def ler_xml(arquivo_xml):     
  with open(arquivo_xml, 'r', encoding='utf-8') as fd:
    doc = xmltodict.parse(fd.read())
  dados = []
  base_doc = doc['Pub_OL']['Publicacoes']
  for i in range(len(doc['Pub_OL']['Publicacoes'])):
    processo_origem =  extrair_processo_origem(f"{base_doc[i]['Publicacao']})")
    print('PROCESSO -> ', f"{base_doc[i]['Processo']}")
    if verificar_tribunal(f"{base_doc[i]['Processo']}"):
      processo_origem = extrair_processo_origem_amazonas(f"{base_doc[i]['Publicacao']})", f"{base_doc[i]['Processo']}")
      print('processo origem -->', processo_origem)
    dados.append({"processo": f"{base_doc[i]['Processo']}", "tribunal": f"{base_doc[i]['Tribunal']}", "materia": f"{base_doc[i]['Materia']}", 'origem': processo_origem})

  for d in dados:
      if d['origem'] == '0688105-15.2020.8.04.0001':
        dados_limpos = limpar_dados(d)
        tipo = tipo_precatorio(d)
        dado = dados_limpos | tipo
        if verificar_tribunal(d['processo']) and d['origem'] != '':
          ler_documentos(dado)
        else:
          pass
  apagar_arquivos_txt('./arquivos_txt_amazonas')

def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.8.04.\d{4}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True
        
def ler_documentos(dado_xml):
      try:
        processo_geral = dado_xml['origem']
        doc = get_docs_oficio_precatorios_tjam(dado_xml['origem'],zip_file=False, pdf=True)
        if doc != {}:
          codigo_processo = next(iter(doc))
          for i in range(len(doc[codigo_processo])):
            file_path = doc[codigo_processo][i][1]
            arquivo_pdf = f"{processo_geral}_arquivo_precatorio.pdf"
            with open(arquivo_pdf, "ab") as arquivo:
                    arquivo.write(file_path)
          pdf_file = open(arquivo_pdf, 'rb')
          
          pdf_reader = PyPDF2.PdfReader(pdf_file)
          text = ''
          for page_num in range(len(pdf_reader.pages)): 
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
            with open(f"{processo_geral}_extrair.txt", "a", encoding='utf-8') as arquivo:
                    arquivo.write(text)
          dados_pdf = extrair_dados_pdf(f'{processo_geral}_extrair.txt')
          dados = dado_xml | dados_pdf | {"processo_geral": processo_geral,'codigo_processo': codigo_processo, 'site': 'https://consultasaj.tjam.jus.br/', 'tipo_precatorio': 'ESTADUAL', 'estado': 'AMAZONAS'}

          mandar_para_banco_de_dados(dados['processo'], dados)
          enviar_valores_oficio_arteria(arquivo_pdf, dados)
      except Exception as e:
        print(f"Erro meno, processo -> {processo_geral}", e)
        print(traceback.print_exc())
        pass

def extrair_dados_pdf(arquivo_txt):
    with open(arquivo_txt, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()

    indice_vara = encontrar_indice_linha(linhas, "Vara  ")
    indice_juizado = encontrar_indice_linha(linhas, " Juizado")
    indice_cidade = encontrar_indice_linha(linhas, 'E-mail')
    indice_bruto = encontrar_indice_linha(linhas, "Valor  Bruto:")
    indice_global = encontrar_indice_linha(linhas, "R$")
    indice_juros_e_principal = encontrar_indice_linha(linhas, "%") 
    indice_valores = encontrar_indice_linha(linhas, "poupança")
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
              'indice_bruto': indice_bruto

              }
    
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

    if dados['global'] == '':
      indice = indice_global + 2
      valor = linhas[indice]
      dados['global'] = valor.strip().replace('.','').replace(',','.') 
    print(dados)
    

    cpf_credor = pegar_cpf_e_credor(indice_cpf_credor, linhas)
    principal_e_juros = pegar_principal_e_juros(indice_juros_e_principal, linhas)
    # dados_limpos = remover_e_reatribuir_dados(dados)
    dados = dados | cpf_credor | principal_e_juros
    if dados['juros'] == '':
      principal, juros = principal_e_juros_poupanca(linhas[indice_valores])
      dados['principal'] = principal
      dados['juros'] = juros
    print('DADOS --->> ', dados)
    return dados
    
def remover_e_reatribuir_dados(dados):
  if dados['juizado'] != '':
      dados['vara'] = dados['juizado']
      del dados['juizado']
  else:
      del dados['juizado']
    
  if dados['requerido'] != '':
      dados['devedor'] = dados['requerido']
      del dados['requerido']
  else:
      del dados['requerido']

  return dados
def pegar_principal_e_juros(indice, linhas):
  if indice != None:
    string = linhas[indice]
    valores = string.split('R$')
    principal = valores[1].strip().replace('.','').replace(',','.')
    principal = principal.split(' ')[0]
    juros = valores[2].strip().replace('.','').replace(',','.')
    return {'principal': principal, 'juros': juros}  
  else:
    return {'principal': '', 'juros': ''}  

def pegar_cpf_e_credor(indice, texto):
  string = texto[indice]
  padrao_cpf = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b|\b\d{11}\b'
  cpf_cnpj_rne = re.search(padrao_cpf, string)
  if cpf_cnpj_rne != None:
      cpf = cpf_cnpj_rne.group(0).strip()
  else:
      cpf =  ''
  padrao_credor = r'[a-zA-ZÀ-ÖØ-öø-ÿ]+'
  resultado_credor = re.findall(padrao_credor, string)
  if resultado_credor != None:
      credor = ' '.join(resultado_credor)
  else:
      credor = ''
  return {'cpf': cpf,'credor': credor}

    
def pegar_processo_origem(texto, indice):
  for i in dict.keys(indice):
      if indice[i] != None:
        origem = texto[indice[i]].replace('\n', '').replace(',', '').strip()
        return {'origem': origem}
      else:
          return {'origem': ''}
      
def pegar_cidade(texto, indice):
    for i in dict.keys(indice):
      if indice[i] != None:
        cidade = texto[indice[i]].replace('\n', '').replace(',', '').replace('.', '').strip()
        return {'cidade': cidade}
      else:
          return {'cidade': ''}

ler_xml('arquivos_xml/relatorio_23_08.xml')