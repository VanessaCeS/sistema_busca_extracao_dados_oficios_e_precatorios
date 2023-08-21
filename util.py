import re

def regex(string):
    if 'Processo' in string:
      padrao = r'\d{7}-\d{2}.\d{4}.\d{1}.\d{2}.\d{4}/\d{2}'
      processo = re.search(padrao, string)
      print('processo --->> ',processo.group(0))
      return processo.group(0)
    if 'Credor(s):' in string:
      padrao = r'Credor\(s\):\s+(.*?)\n'
      credor = re.search(padrao, string)
      print('credor --->> ', credor.group(1))
      return credor.group(1)
    if 'Devedor' in string:
      padrao = r'Devedor: (.*)'
      devedor = re.search(padrao, string)
      print('devedor --->> ',devedor.group(1))
      return devedor.group(1)
    if 'Natureza' in string:
      padrao = r'Natureza:\s+(.*?)\n'
      natureza = re.search(padrao, string)
      print('natureza --->> ',natureza.group(1))
      return natureza.group(1)
    if 'Valor  global  da requisição' in string:
      padrao = r'\b(?:1{1,3}(?:\.\d{3})*(?:,\d{2})?|1{1,3}(?:,\d{3})*(?:\.\d{2})?|[2-9]\d{0,2}(?:\.\d{3})*(?:,\d{2})?)\b' 
      valor_global = re.search(padrao, string)
      print('valor_global --->> ',valor_global.group(0))
      return valor_global.group(0)
    if 'Juros  Moratórios' in string:
      padrao = r'\b(?:1{1,3}(?:\.\d{3})*(?:,\d{2})?|1{1,3}(?:,\d{3})*(?:\.\d{2})?|[2-9]\d{0,2}(?:\.\d{3})*(?:,\d{2})?)\b' 
      valor_juros = re.search(padrao, string)
      print('valor_juros --->> ',valor_juros.group(0))
      return valor_juros.group(0)
    if 'Principal/Indenização' in string:
      padrao = r'\b(?:1{1,3}(?:\.\d{3})*(?:,\d{2})?|1{1,3}(?:,\d{3})*(?:\.\d{2})?|[2-9]\d{0,2}(?:\.\d{3})*(?:,\d{2})?)\b'  
      valor_principal = re.search(padrao, string)
      print('valor_principal.group(0) --->> ',valor_principal.group(0))
      return valor_principal.group(0)
    if 'CPF/CNPJ/RNE' in string:
      padrao = r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|RNE-\d{10})\b'
      cpf_cnpj_rne = re.search(padrao, string)
      print('cpf_cnpj_rne --->> ',cpf_cnpj_rne.group(0))
      return cpf_cnpj_rne.group(0)