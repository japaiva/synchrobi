#!/usr/bin/env python
"""
Verificar quais códigos externos realmente faltam no banco de dados
após a primeira rodada de importação
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import ContaExterna
import csv

# Ler códigos do CSV original (todos os 327)
csv_original = '/tmp/inserir_contas_externas.csv'

codigos_planejados = {}
with open(csv_original, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        codigo = row['codigo_externo'].strip()
        codigos_planejados[codigo] = {
            'nome': row['nome_externo'].strip(),
            'conta': row['conta_contabil'].strip(),
            'sistema': row['sistema_origem'].strip()
        }

print(f'=== ANÁLISE DE CÓDIGOS EXTERNOS ===\n')
print(f'Códigos externos no CSV original: {len(codigos_planejados)}')

# Verificar quais já foram importados
codigos_importados = set()
codigos_no_banco = ContaExterna.objects.all().values_list('codigo_externo', flat=True)
codigos_importados = set(codigos_no_banco)

print(f'Códigos já importados no banco: {len(codigos_importados)}')

# Identificar faltantes
codigos_faltantes = {}
for codigo, dados in codigos_planejados.items():
    if codigo not in codigos_importados:
        codigos_faltantes[codigo] = dados

print(f'\n=== RESULTADO ===')
print(f'Códigos que FALTAM importar: {len(codigos_faltantes)}')
print(f'Códigos que JÁ FORAM importados: {len(codigos_planejados) - len(codigos_faltantes)}')

if codigos_faltantes:
    print(f'\n=== CÓDIGOS EXTERNOS FALTANTES ({len(codigos_faltantes)}) ===')
    for i, (codigo, dados) in enumerate(sorted(codigos_faltantes.items())[:30], 1):
        print(f'{i:3}. {codigo:15} | Conta: {dados["conta"]:15} | {dados["nome"][:40]}')

    if len(codigos_faltantes) > 30:
        print(f'\n... e mais {len(codigos_faltantes) - 30} códigos')

    # Gerar CSV apenas com os faltantes
    output_file = '/Users/joseantoniopaiva/Downloads/codigos_externos_REALMENTE_faltantes.csv'
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['codigo_externo', 'nome_externo', 'conta_contabil', 'sistema_origem'])
        writer.writeheader()
        for codigo, dados in sorted(codigos_faltantes.items()):
            writer.writerow({
                'codigo_externo': codigo,
                'nome_externo': dados['nome'],
                'conta_contabil': dados['conta'],
                'sistema_origem': dados['sistema']
            })

    print(f'\n✓ CSV gerado com APENAS os códigos externos faltantes: {output_file}')
    print(f'✓ Total de códigos no CSV: {len(codigos_faltantes)}')
else:
    print('\n✓ Todos os códigos externos já foram importados!')
