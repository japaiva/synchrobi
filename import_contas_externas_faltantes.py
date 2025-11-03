#!/usr/bin/env python
"""
Script para importar códigos externos de contas contábeis faltantes
Gerado automaticamente - importa 327 registros do Marie.xlsx
"""

import os
import sys
import django
import csv
from datetime import datetime

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import ContaContabil, ContaExterna

def importar_contas_externas(csv_file):
    """
    Importa códigos externos de contas contábeis do CSV
    """
    print(f'\n{"="*80}')
    print('IMPORTAÇÃO DE CÓDIGOS EXTERNOS DE CONTAS CONTÁBEIS')
    print(f'{"="*80}\n')
    print(f'Arquivo: {csv_file}')
    print(f'Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}\n')

    if not os.path.exists(csv_file):
        print(f'❌ ERRO: Arquivo não encontrado: {csv_file}')
        return

    sucessos = 0
    erros = 0
    pulos = 0
    erros_lista = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        total = sum(1 for row in reader)
        f.seek(0)
        next(reader)  # Pular cabeçalho novamente

        print(f'Total de registros a importar: {total}\n')
        print('-' * 80)

        for idx, row in enumerate(reader, 1):
            codigo_externo = row['codigo_externo'].strip()
            nome_externo = row['nome_externo'].strip()
            conta_codigo = row['conta_contabil'].strip()
            sistema_origem = row['sistema_origem'].strip() or 'ERP'

            try:
                # Verificar se já existe
                if ContaExterna.objects.filter(codigo_externo=codigo_externo).exists():
                    print(f'{idx:3}/{total} ⏭️  PULADO: {codigo_externo:15} | Já existe')
                    pulos += 1
                    continue

                # Buscar conta contábil
                try:
                    conta = ContaContabil.objects.get(codigo=conta_codigo)
                except ContaContabil.DoesNotExist:
                    msg = f'Conta contábil não encontrada: {conta_codigo}'
                    print(f'{idx:3}/{total} ❌ ERRO: {codigo_externo:15} | {msg}')
                    erros += 1
                    erros_lista.append({
                        'linha': idx,
                        'codigo': codigo_externo,
                        'erro': msg
                    })
                    continue

                # Criar código externo
                conta_externa = ContaExterna.objects.create(
                    codigo_externo=codigo_externo,
                    nome_externo=nome_externo,
                    sistema_origem=sistema_origem,
                    conta_contabil=conta,
                    ativa=True,
                    observacoes='Importado do cadastro completo Marie'
                )

                print(f'{idx:3}/{total} ✓ OK: {codigo_externo:15} | Conta: {conta_codigo:15} | {nome_externo[:40]}')
                sucessos += 1

            except Exception as e:
                msg = str(e)
                print(f'{idx:3}/{total} ❌ ERRO: {codigo_externo:15} | {msg}')
                erros += 1
                erros_lista.append({
                    'linha': idx,
                    'codigo': codigo_externo,
                    'erro': msg
                })

    # Resumo
    print('\n' + '='*80)
    print('RESUMO DA IMPORTAÇÃO')
    print('='*80)
    print(f'Total de registros processados: {total}')
    print(f'✓ Sucessos:  {sucessos:3} ({sucessos*100//total if total > 0 else 0}%)')
    print(f'⏭  Pulados:   {pulos:3} ({pulos*100//total if total > 0 else 0}%)')
    print(f'❌ Erros:     {erros:3} ({erros*100//total if total > 0 else 0}%)')

    if erros_lista:
        print(f'\n{"="*80}')
        print('DETALHES DOS ERROS')
        print('='*80)
        for erro_info in erros_lista[:20]:
            print(f'Linha {erro_info["linha"]}: {erro_info["codigo"]} - {erro_info["erro"]}')
        if len(erros_lista) > 20:
            print(f'\n... e mais {len(erros_lista) - 20} erros')

    print(f'\n{"="*80}\n')

if __name__ == '__main__':
    # Usar o CSV com apenas os códigos que realmente faltam
    csv_path = '/Users/joseantoniopaiva/Downloads/codigos_externos_REALMENTE_faltantes.csv'

    # Se não existir, usar o original (primeira rodada)
    if not os.path.exists(csv_path):
        print(f'\n⚠️  Arquivo {csv_path} não encontrado.')
        print('Execute primeiro: python verificar_codigos_externos_faltantes.py')
        print('Ou use o CSV original para primeira rodada.\n')
        csv_path = '/tmp/inserir_contas_externas.csv'

    importar_contas_externas(csv_path)
