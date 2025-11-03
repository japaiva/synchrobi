#!/usr/bin/env python
"""
Mostrar 5 exemplos de códigos externos que falharam
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import ContaContabil
import csv

# Pegar 5 exemplos dos códigos que falharam
codigos_exemplo = ['1203010007', '6104010007', '6202010004', '6303010009', '6401010003']

print(f'\n{"="*80}')
print('5 EXEMPLOS DE CÓDIGOS EXTERNOS QUE FALHARAM')
print(f'{"="*80}\n')

csv_file = '/tmp/inserir_contas_externas.csv'

if not os.path.exists(csv_file):
    print('❌ Arquivo CSV não encontrado!')
    sys.exit(1)

# Ler CSV
exemplos = []
with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cod_ext = row['codigo_externo'].strip()
        if cod_ext in codigos_exemplo:
            exemplos.append({
                'cod_ext': cod_ext,
                'conta': row['conta_contabil'].strip(),
                'nome': row['nome_externo'].strip()
            })

# Verificar quais contas existem
contas_existentes = set(ContaContabil.objects.values_list('codigo', flat=True))

for i, ex in enumerate(exemplos, 1):
    existe = ex['conta'] in contas_existentes
    status = '✓ EXISTE' if existe else '✗ NÃO EXISTE'

    print(f'\n--- EXEMPLO {i} ---')
    print(f'Código ERP:      {ex["cod_ext"]}')
    print(f'Conta esperada:  {ex["conta"]}  ({status})')
    print(f'Nome:            {ex["nome"]}')

    if not existe:
        print(f'🔴 PROBLEMA: A conta {ex["conta"]} não existe no banco!')
        print(f'   Por isso este código ERP não pode ser importado.')

print(f'\n{"="*80}')
print('\n💡 RESUMO:')
print('Os códigos externos do Marie.xlsx esperam contas contábeis que não')
print('foram criadas. Você tem duas opções:')
print('')
print('1. CRIAR essas contas extras e importar TODOS os códigos externos')
print('2. IGNORAR esses códigos e manter apenas o que está no cc1.xlsx')
print(f'\n{"="*80}\n')
