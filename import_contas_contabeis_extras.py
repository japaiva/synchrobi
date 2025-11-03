#!/usr/bin/env python
"""
Script para importar contas contábeis extras necessárias
(Contas que estão no Marie.xlsx mas não estavam no cc1.xlsx)
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

from core.models import ContaContabil

def importar_contas_extras(csv_file):
    """
    Importa contas contábeis extras do CSV
    """
    print(f'\n{"="*80}')
    print('IMPORTAÇÃO DE CONTAS CONTÁBEIS EXTRAS')
    print(f'{"="*80}\n')
    print(f'Arquivo: {csv_file}')
    print(f'Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}\n')

    if not os.path.exists(csv_file):
        print(f'❌ ERRO: Arquivo não encontrado: {csv_file}')
        print('\nExecute primeiro: python investigar_contas_faltantes.py')
        return

    sucessos = 0
    erros = 0
    pulos = 0
    erros_lista = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        linhas = list(reader)
        total = len(linhas)

        print(f'Total de registros a processar: {total}\n')
        print('Características das contas:')
        print('  • Sem pai (conta raiz)')
        print('  • Analítica (tipo A)')
        print('  • Ativa')
        print('  • Sem relatório de despesa\n')
        print('-' * 80)

        for idx, row in enumerate(linhas, 1):
            codigo = row['codigo'].strip()
            nome = row['nome'].strip()
            tipo = row['tipo'].strip()
            ativa_str = row['ativa'].strip()
            relatorio_despesa_str = row['relatorio_despesa'].strip()

            ativa = ativa_str.lower() in ['true', '1', 'sim', 'verdadeiro']
            relatorio_despesa = relatorio_despesa_str.lower() in ['true', '1', 'sim', 'verdadeiro']

            try:
                # Verificar se já existe
                if ContaContabil.objects.filter(codigo=codigo).exists():
                    print(f'{idx:3}/{total} ⏭️  PULADO: {codigo:15} | Já existe')
                    pulos += 1
                    continue

                # Criar conta contábil
                conta = ContaContabil.objects.create(
                    codigo=codigo,
                    nome=nome,
                    codigo_pai=None,
                    tipo=tipo,
                    ativa=ativa,
                    relatorio_despesa=relatorio_despesa,
                    nivel=codigo.count('.') + 1
                )

                print(f'{idx:3}/{total} ✓ OK: {codigo:15} | {nome[:50]}')
                sucessos += 1

            except Exception as e:
                msg = str(e)
                print(f'{idx:3}/{total} ❌ ERRO: {codigo:15} | {msg}')
                erros += 1
                erros_lista.append({'linha': idx, 'codigo': codigo, 'erro': msg})

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

    if sucessos > 0:
        print(f'✓ {sucessos} contas contábeis extras criadas com sucesso!')
        print(f'\nAgora execute novamente:')
        print(f'  python import_contas_externas_faltantes.py')

if __name__ == '__main__':
    csv_path = '/Users/joseantoniopaiva/Downloads/contas_contabeis_EXTRAS_necessarias.csv'
    importar_contas_extras(csv_path)
