#!/usr/bin/env python
"""
Script para visualizar estrutura do Excel
"""

import pandas as pd

excel_path = '/Users/joseantoniopaiva/Downloads/C-Contabeis.xlsx'

print("=" * 80)
print(f"ESTRUTURA DO ARQUIVO: {excel_path}")
print("=" * 80)

try:
    # Ler Excel
    df = pd.read_excel(excel_path)

    print(f"\n📊 Informações Gerais:")
    print(f"   Total de linhas: {len(df):,}")
    print(f"   Total de colunas: {len(df.columns)}")

    print(f"\n📋 Colunas:")
    for i, col in enumerate(df.columns):
        print(f"   {i}: '{col}'")

    print(f"\n👀 Primeiras 5 linhas:")
    print(df.head(5).to_string())

    print(f"\n📝 Exemplo de dados (primeira linha não-nula):")
    for col in df.columns:
        valor = df[col].iloc[0]
        print(f"   {col}: {valor}")

except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()
