#!/usr/bin/env python
"""
Verificar quais contas contábeis realmente faltam no banco de dados
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import ContaContabil
import csv

# Ler contas do cc1.xlsx (via CSV gerado)
csv_file = '/Users/joseantoniopaiva/Downloads/contas_contabeis_criar.csv'

contas_cc1 = {}
with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        codigo = row['codigo'].strip()
        nome = row['nome'].strip()
        contas_cc1[codigo] = nome

print(f'=== ANÁLISE DE CONTAS CONTÁBEIS ===\n')
print(f'Contas no cc1.xlsx: {len(contas_cc1)}')

# Verificar quais já existem no banco
contas_existentes = set()
contas_no_banco = ContaContabil.objects.all().values_list('codigo', flat=True)
contas_existentes = set(contas_no_banco)

print(f'Contas no banco de dados: {len(contas_existentes)}')

# Identificar faltantes
contas_faltantes = {}
for codigo, nome in contas_cc1.items():
    if codigo not in contas_existentes:
        contas_faltantes[codigo] = nome

print(f'\n=== RESULTADO ===')
print(f'Contas que FALTAM no banco: {len(contas_faltantes)}')
print(f'Contas que JÁ EXISTEM: {len(contas_cc1) - len(contas_faltantes)}')

if contas_faltantes:
    print(f'\n=== CONTAS FALTANTES ({len(contas_faltantes)}) ===')
    for i, (codigo, nome) in enumerate(sorted(contas_faltantes.items()), 1):
        print(f'{i:3}. {codigo:15} | {nome}')

    # Gerar CSV apenas com as faltantes
    output_file = '/Users/joseantoniopaiva/Downloads/contas_contabeis_REALMENTE_faltantes.csv'
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['codigo', 'nome', 'codigo_pai', 'tipo', 'ativa', 'relatorio_despesa'])
        writer.writeheader()
        for codigo, nome in sorted(contas_faltantes.items()):
            writer.writerow({
                'codigo': codigo,
                'nome': nome,
                'codigo_pai': '',
                'tipo': 'A',
                'ativa': 'True',
                'relatorio_despesa': 'False'
            })

    print(f'\n✓ CSV gerado com APENAS as contas faltantes: {output_file}')
else:
    print('\n✓ Todas as contas do cc1.xlsx já existem no banco de dados!')
    print('  Você pode executar diretamente o import_contas_externas_faltantes.py')
