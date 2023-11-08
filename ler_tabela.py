import pandas as pd

def ler_excel(arquivo_excel):
    try:
        df = pd.read_excel(arquivo_excel)
        dados = df.iloc[:, 3]
        print(dados)
        dados.to_csv('precatorios_tfr4.txt', index=False, sep='\t')
        return dados

    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        return None

# Exemplo de uso
arquivo_excel = '../../Downloads/ORDEM-CRONOLÓGICA-DE-PAGAMENTOS-TRF4-UNIÃO.xlsx'
dados_extraidos = ler_excel(arquivo_excel)

if dados_extraidos is not None:
    print("Dados extraídos:")
    print(dados_extraidos)

