import re
import PyPDF2
import traceback
from logs import log
from cna_oab import login_cna
from funcoes_arteria import enviar_valores_oficio_arteria
from esaj_mato_grosso_sul_precatorios import get_docs_oficio_precatorios_tjms
from auxiliares import  encontrar_indice_linha, formatar_data_padra_arteria, ler_arquivo_pdf_transformar_em_txt, limpar_dados, mandar_dados_regex, mandar_documento_para_ocr, pdf_to_png, tipo_de_natureza, verificar_tribunal
from banco_de_dados import atualizar_ou_inserir_pessoa_no_banco_de_dados, atualizar_ou_inserir_pessoa_precatorio, atualizar_ou_inserir_precatorios_no_banco_de_dados, atualizar_ou_inserir_situacao_cadastro, consultar_processos, precatorio_exitente_arteria

def buscar_dados_tribunal_mato_grosso_do_sul():     
  dados = consultar_processos('.8.12.')
  for d in dados:
        dado = limpar_dados(d)
        if verificar_tribunal(d['processo']):
          if dado['processo_origem'] == '':
            dado['processo_origem'] = dado['processo']
          ler_documentos(dado)
        else:
          pass
  

def verificar_tribunal(n_processo):
        padrao = r'\d{7}-\d{2}.\d{4}.8.12.\d{4}'
        processo = re.search(padrao, n_processo)
        if processo != None:
          return True

def ler_documentos(dados_xml):
      try:
        processo_geral = dados_xml['processo']
        doc = get_docs_oficio_precatorios_tjms(processo_geral,zip_file=False, pdf=True)
        if doc:
          codigo_processo = next(iter(doc))
          arquivo_pdf = f"arquivos_pdf_mato_grosso_do_sul/{processo_geral}_arquivo_precatorio.pdf"
          merge = PyPDF2.PdfMerger()
          for chave, valor in doc.items():
            for i in range(len(valor)):
              id_documento = valor[i][0] 
              file_path = valor[i][2]
              with open(f"arquivos_pdf_mato_grosso_do_sul/{processo_geral}_{i+1}_arquivo_precatorio.pdf", "wb") as arquivo:
                arquivo.write(file_path)
              merge.append(f"arquivos_pdf_mato_grosso_do_sul/{processo_geral}_{i+1}_arquivo_precatorio.pdf")
          merge.write(arquivo_pdf)
          arquivo_txt = ler_arquivo_pdf_transformar_em_txt(arquivo_pdf)
          dados =  {"processo_geral": processo_geral, "codigo_processo": codigo_processo, 'site': 'https://esaj.tjms.jus.br', 'id_documento': id_documento, 'estado': 'MATO GROSSO DO SUL', 'tipo': 'MUNICIPAL'} | dados_xml
          extrair_dados_pdf(arquivo_pdf, arquivo_txt, dados)
      except Exception as e:
        print(f"Erro! Processo -> {processo_geral}", e)
        print(traceback.print_exc())
        pass

def extrair_dados_pdf(arquivo_pdf, arquivo_txt, dados_pdf):
  with open(arquivo_txt, 'r', encoding='utf-8') as f:
    linhas = f.readlines()

  dados = {}
  indice_autor = encontrar_indice_linha(linhas,'autor')
  indice_credor = encontrar_indice_linha(linhas, 'beneficiários') 
  
  if indice_credor or indice_autor:
    indice_executado = encontrar_indice_linha(linhas,'réu')
    indice_devedor = encontrar_indice_linha(linhas,'devedor:')
    indice_vara = encontrar_indice_linha(linhas,'vara')
    indice_cidade = encontrar_indice_linha(linhas,'comarca: ')
    indice_natureza = encontrar_indice_linha(linhas, "natureza do crédito")
    indice_natureza_juridica = encontrar_indice_linha(linhas, 'natureza jurídica do crédito')
    indice_valor_total = encontrar_indice_linha(linhas, "valor total:")
    indice_valor_principal = encontrar_indice_linha(linhas, "valor principal")
    indice_valor_juros = encontrar_indice_linha(linhas, "valor juros")
    indice_data_expedicao = encontrar_indice_linha(linhas,'liberado nos autos')
    indice_oab = encontrar_indice_linha(linhas,'oab:')
    indice_advogado = encontrar_indice_linha(linhas,'nome/oab/cpf')
    indice_data_nascimento = encontrar_indice_linha(linhas,' nascimento')
    if indice_natureza_juridica != None:
      indice_natureza = indice_natureza_juridica
    if indice_valor_total == None:
      indice_valor_total = indice_valor_principal - 1
    
    indices = {'indice_vara': indice_vara, 'indice_natureza': indice_natureza, 'indice_total': indice_valor_total, 'indice_valor_juros': indice_valor_juros,  'indice_valor_principal': indice_valor_principal, 'indice_data_expedicao': indice_data_expedicao}
    
    dados = mandar_dados_regex(indices, linhas)

    if indice_cidade == None:
      indice_cidade = 2
      dados['cidade'] = linhas[indice_cidade].split('-')[0].strip()
    else:
      dados['cidade'] = linhas[indice_cidade].split(':')[1].strip()
    if ':' in dados['vara_pdf']:
      dados['vara_pdf'] = dados['vara_pdf'].split(':')[1].replace('\n', '').strip()
    if indice_autor != None:
      dados['credor'] = pegar_valor(linhas[indice_autor + 1])
      dados['documento'] = pegar_valor(linhas[indice_autor + 2])
    elif indice_credor != None:
      dados['credor'] = linhas[indice_credor + 2].replace('\n', '').strip()
      dados['documento'] = linhas[indice_credor + 3].replace('\n', '').strip()

    if indice_devedor != None:
      dados['devedor'] = pegar_valor(linhas[indice_devedor])
    elif indice_executado != None:
      dados['devedor'] = pegar_valor(linhas[indice_executado + 1])

    if indice_data_nascimento != None:
      data_nascimento = linhas[indice_data_nascimento].split('Nascimento:')[1].replace('\n','').strip()
      dados['data_nascimento'] = formatar_data_padra_arteria(data_nascimento) if data_nascimento != '' else ''
    
    dados_advogado = extrair_dados_advogado(linhas, indice_advogado, indice_oab, dados_pdf['processo'])
    
    dados = dados | dados_advogado | dados_pdf 
    enviar_dados_banco_de_dados_e_arteria(arquivo_pdf, dados)
  else:
    pdf_para_img = pdf_to_png(arquivo_pdf, 'arquivos_img_mato_grosso_do_sul', dados_pdf['processo_geral'])

    print(pdf_para_img)
    with open(pdf_para_img, 'r', encoding='utf-8') as f:
      linhas = f.readlines()

    indice_processo_origem = encontrar_indice_linha(linhas, 'número processo de conhecimento')
    indice_vara = encontrar_indice_linha(linhas,'juízo')
    indice_natureza = encontrar_indice_linha(linhas,'natureza jurídica')
    indice_devedor = encontrar_indice_linha(linhas, 'devedor')
    indice_credor = encontrar_indice_linha(linhas, 'requerente')
    indice_advogado = encontrar_indice_linha(linhas, 'advogado requerente')
    indice_valor_global = encontrar_indice_linha(linhas, 'valor global:')
    indice_valor_principal = encontrar_indice_linha(linhas, 'valor principal')
    indice_valor_juros = encontrar_indice_linha(linhas, 'valor juros')
    indice_data_expedicao = encontrar_indice_linha(linhas, 'liberado nos autos')

    dados['devedor'] = pegar_valor(linhas[indice_devedor]).split('(')[0]
    dados['credor'] = pegar_valor(linhas[indice_credor]).split('(')[0]
    if dados['credor'] or dados['devedor']:
      dados['documento'] = pegar_valor(linhas[indice_credor]).split('(')[1].replace(')', '')
      dados['valor_global'] = pegar_valor(linhas[indice_valor_global]).strip().replace('.','').replace(',','.')
      dados['valor_principal'] = pegar_valor(linhas[indice_valor_principal]).strip().replace('.','').replace(',','.')
      dados['valor_juros'] = pegar_valor(linhas[indice_valor_juros]).strip().replace('.','').replace(',','.')
      
      dados_pdf['vara'] = pegar_valor(linhas[indice_vara])
      if ',' in dados_pdf['vara']:
        dados_pdf['vara'] = dados_pdf['vara'].split(',')[0].strip()

      dados_pdf['processo_origem'] = pegar_valor(linhas[indice_processo_origem])

      dados['data_nascimento'] = ''
      dados['cidade'] = ''
      natureza = pegar_valor(linhas[indice_natureza])
      natureza = tipo_de_natureza(natureza.upper())

      dados_advogado = {'telefone': '', 'advogado': '', 'seccional': '', 'oab': '', 'documento_advogado': ''}
      if indice_advogado != None:
        advogado = pegar_valor(linhas[indice_advogado]).split('(')[0]
        if advogado.upper().strip() != 'NULL':
          oab = pegar_valor(linhas[indice_advogado]).split('(')[1].replace(')', '')
          dados['oab'] = oab.split('/')[0]
          dados['seccional'] = oab.split('/')[1].split('-')[1]
          dados_advogado = login_cna(dados['oab'], dados['seccional'],  '',advogado , dados_pdf['processo'])
          
      indices = {'data_expedicao': indice_data_expedicao}
      data_expedicao = mandar_dados_regex(indices, linhas)

      dados = dados | dados_pdf | dados_advogado | data_expedicao | natureza
      enviar_dados_banco_de_dados_e_arteria(arquivo_pdf, dados)
    else:
      with open('processos_falha_ms.txt', 'a+') as f:
        f.write(f'O processo não pode ser lido: Processo -->> {dados_pdf["processo"]}, Processo Origem -->> {dados_pdf["processo_origem"]} \n')

def pegar_valor(string):
  valor = string.split(':')[1].replace('\n', '').strip()
  return valor

def extrair_dados_advogado(linhas, indice_advogado, indice_oab, processo):
  dados_advogado = {'telefone': '', 'advogado': '', 'seccional': '', 'oab': '', 'documento_advogado': ''}
  if indice_oab:
      advogado = pegar_valor(linhas[indice_oab - 1])
      oab_e_seccional = pegar_valor(linhas[indice_oab])
      oab = oab_e_seccional[2:]  
      if oab[0] == '0' and oab[1] == '0':
        oab = oab[2:]
      elif oab[0] == '0' and oab[1] != '0':
        oab = oab[1:]
      seccional = oab_e_seccional[:2]
      documento_advogado = pegar_valor(linhas[indice_oab + 1])
      dados_advogado = login_cna(oab,seccional, documento_advogado,advogado, processo)
  elif indice_advogado:
      valores = linhas[indice_advogado + 1].split(':')[1].split('-')
      print(valores[0].replace('\n','').upper().strip())
      if 'PARTE' != valores[0].upper().replace('\n','').strip():
        if 'PARTE' in valores[0].upper().strip():
          valores = linhas[indice_advogado].split(':')[1].split('-')
        advogado = valores[0].strip()
        oab = valores[1].split('/')[0].strip()
        seccional =  valores[2].strip()
        documento_advogado = valores[2].replace('\n', '').strip()
        dados_advogado = login_cna(oab,seccional, documento_advogado,advogado, processo)
  return dados_advogado

def enviar_dados_banco_de_dados_e_arteria(arquivo_pdf, dados):    
    documento = dados['documento']
    site = dados['site']
    atualizar_ou_inserir_pessoa_no_banco_de_dados(documento, {'nome': dados['credor'], 'documento': dados['documento'], 'data_nascimento': dados['data_nascimento'], 'estado': 'Mato Grosso do Sul', 'tipo': 'credor'})
    existe_id_sistema_arteria = precatorio_exitente_arteria(dados['processo'])
    if existe_id_sistema_arteria:
      dados['id_sistema_arteria'] = existe_id_sistema_arteria[0]
      enviar_valores_oficio_arteria(arquivo_pdf, dados, existe_id_sistema_arteria[0])
      mensagem = 'Precatório alterado com sucesso'
    else:
      dados['id_sistema_arteria']  = enviar_valores_oficio_arteria(arquivo_pdf, dados)
      mensagem = 'Precatório registrado com sucesso'
    atualizar_ou_inserir_precatorios_no_banco_de_dados(dados['codigo_processo'], dados)
    atualizar_ou_inserir_pessoa_precatorio(documento, dados['processo'])
    log( dados['processo_origem'], 'Sucesso', site, mensagem ,dados['estado'], dados['tribunal'])
    atualizar_ou_inserir_situacao_cadastro(dados['processo'],{'status': 'Sucesso'})
