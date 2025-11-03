#!/usr/bin/env python
"""
Investigar quais contas contábeis são referenciadas pelos códigos externos
que falharam na importação
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

# Códigos externos que falharam (você informou 20, mas disse que são 30 no total)
codigos_com_erro = [
    '1203010007', '1203010023', '1204010002', '6104010007', '6202010004',
    '6202010008', '6202010009', '6303010009', '6303020017', '6305050001',
    '6305050009', '6305050010', '6305060003', '6305060007', '6305070003',
    '6401010003', '6401010004', '6401010005', '6401010007', '6402010003'
]

print(f'=== INVESTIGANDO {len(codigos_com_erro)} CÓDIGOS COM ERRO ===\n')

# Ler o CSV original para ver qual conta cada código espera
csv_file = '/tmp/inserir_contas_externas.csv'

if not os.path.exists(csv_file):
    print(f'❌ Arquivo {csv_file} não encontrado!')
    print('Por favor, gere novamente o CSV de códigos externos.')
    sys.exit(1)

mapeamento = {}
with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cod_ext = row['codigo_externo'].strip()
        if cod_ext in codigos_com_erro:
            mapeamento[cod_ext] = {
                'conta_esperada': row['conta_contabil'].strip(),
                'nome': row['nome_externo'].strip(),
                'sistema': row['sistema_origem'].strip()
            }

print(f'Códigos encontrados no CSV: {len(mapeamento)}\n')

# Verificar quais contas existem no banco
contas_existentes = set(ContaContabil.objects.values_list('codigo', flat=True))

print('=== ANÁLISE DOS CÓDIGOS COM ERRO ===\n')
contas_faltantes = {}

for cod_ext in sorted(codigos_com_erro):
    if cod_ext in mapeamento:
        info = mapeamento[cod_ext]
        conta = info['conta_esperada']
        existe = '✓' if conta in contas_existentes else '✗'

        print(f'{existe} Cód: {cod_ext:15} → Conta: {conta:15} | {info["nome"][:40]}')

        if conta not in contas_existentes:
            if conta not in contas_faltantes:
                contas_faltantes[conta] = []
            contas_faltantes[conta].append({
                'cod_ext': cod_ext,
                'nome': info['nome']
            })
    else:
        print(f'? Cód: {cod_ext:15} → Não encontrado no CSV')

print(f'\n\n=== RESUMO ===')
print(f'Total de códigos analisados: {len(codigos_com_erro)}')
print(f'Contas únicas que faltam: {len(contas_faltantes)}')

if contas_faltantes:
    print(f'\n=== CONTAS QUE PRECISAM SER CRIADAS ({len(contas_faltantes)}) ===\n')

    for i, (conta, codigos) in enumerate(sorted(contas_faltantes.items()), 1):
        print(f'{i:2}. Conta: {conta:15} ({len(codigos)} código(s) precisam dela)')
        for cod_info in codigos[:2]:
            print(f'    → {cod_info["cod_ext"]}: {cod_info["nome"][:50]}')
        if len(codigos) > 2:
            print(f'    ... e mais {len(codigos) - 2}')

    # Gerar CSV
    output_file = '/Users/joseantoniopaiva/Downloads/contas_contabeis_EXTRAS_necessarias.csv'
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['codigo', 'nome', 'codigo_pai', 'tipo', 'ativa', 'relatorio_despesa'])
        writer.writeheader()

        for conta in sorted(contas_faltantes.keys()):
            primeiro = contas_faltantes[conta][0]
            writer.writerow({
                'codigo': conta,
                'nome': primeiro['nome'],
                'codigo_pai': '',
                'tipo': 'A',
                'ativa': 'True',
                'relatorio_despesa': 'False'
            })

    print(f'\n✓ CSV gerado: {output_file}')
    print(f'\nPara criar essas contas, execute:')
    print(f'  python import_contas_contabeis_extras.py')
else:
    print('\n✓ Todas as contas necessárias já existem no banco!')
