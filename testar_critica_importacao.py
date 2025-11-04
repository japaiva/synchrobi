#!/usr/bin/env python
"""
Script para testar crítica de importação de movimentos

Uso:
    python testar_critica_importacao.py arquivo.xlsx 2024-01-01 2024-12-31
"""

import os
import sys
import django
from datetime import datetime
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

# Importar funções necessárias
from gestor.views.movimento_import import analisar_arquivo_pre_importacao, corrigir_estrutura_excel
import pandas as pd


def formatar_valor_reais(valor):
    """Formata valor em reais"""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def imprimir_critica(criticas, arquivo_nome):
    """Imprime relatório de crítica formatado"""

    print("\n" + "=" * 100)
    print(f"RELATÓRIO DE CRÍTICA DE IMPORTAÇÃO - {arquivo_nome}")
    print("=" * 100)

    # RESUMO GERAL
    print(f"\n📊 RESUMO GERAL:")
    print(f"   Total de linhas no arquivo: {criticas['total_linhas']:,}")
    print(f"   Linhas no período informado: {criticas['linhas_no_periodo']:,}")
    print(f"   Linhas fora do período: {criticas['linhas_fora_periodo']:,}")
    print(f"\n✅ MOVIMENTOS VÁLIDOS (serão importados): {criticas['linhas_validas_para_importar']:,}")
    print(f"   Valor total a importar: {formatar_valor_reais(criticas['valor_total_valido'])}")
    print(f"\n🚫 MOVIMENTOS NÃO IMPORTADOS: {criticas['total_movimentos_nao_importados']:,}")
    print(f"   Valor total não importado: {formatar_valor_reais(criticas['valor_total_nao_importado'])}")

    # MOVIMENTOS NÃO IMPORTADOS
    if criticas['total_movimentos_nao_importados'] > 0:
        print(f"\n" + "-" * 130)
        print(f"🚫 MOVIMENTOS NÃO IMPORTADOS")
        print(f"-" * 130)

        # 1. SEM RELATÓRIO DESPESA (apenas total)
        if criticas['linhas_sem_relatorio_despesa'] > 0:
            print(f"\n   ⚠️  TOTAL NÃO É RELATÓRIO DE DESPESA:")
            print(f"       Quantidade: {criticas['linhas_sem_relatorio_despesa']:>8,} movimentos")
            print(f"       Valor Total: {formatar_valor_reais(criticas['valor_total_sem_relatorio_despesa']):>20}")

        # 2. ERROS DE VALIDAÇÃO (detalhado)
        linhas_erros = []

        for codigo, info in criticas['unidades_nao_encontradas'].items():
            linhas_erros.append({
                'motivo': 'Unidade não encontrada',
                'detalhe': f"Código: {codigo}",
                'quantidade': info['quantidade'],
                'valor': info['valor_total']
            })

        for codigo, info in criticas['centros_nao_encontrados'].items():
            linhas_erros.append({
                'motivo': 'Centro não encontrado',
                'detalhe': f"Código: {codigo}",
                'quantidade': info['quantidade'],
                'valor': info['valor_total']
            })

        for codigo, info in criticas['contas_nao_encontradas'].items():
            linhas_erros.append({
                'motivo': 'Conta não encontrada',
                'detalhe': f"Código: {codigo}",
                'quantidade': info['quantidade'],
                'valor': info['valor_total']
            })

        if linhas_erros:
            # Ordenar por valor (maior primeiro)
            linhas_erros = sorted(linhas_erros, key=lambda x: x['valor'], reverse=True)

            # Calcular subtotal de erros
            subtotal_qtd = sum(l['quantidade'] for l in linhas_erros)
            subtotal_valor = sum(l['valor'] for l in linhas_erros)

            print(f"\n   📋 DETALHAMENTO DE ERROS DE VALIDAÇÃO:")
            print(f"\n   {'Motivo':<30} {'Detalhe':<65} {'Qtd.':>8} {'Valor':>20}")
            print(f"   {'-'*30} {'-'*65} {'-'*8} {'-'*20}")

            for linha in linhas_erros:
                print(f"   {linha['motivo']:<30} {linha['detalhe']:<65} {linha['quantidade']:>8,} {formatar_valor_reais(linha['valor']):>20}")

            print(f"   {'-'*30} {'-'*65} {'-'*8} {'-'*20}")
            print(f"   {'Subtotal Erros':<30} {'':<65} {subtotal_qtd:>8,} {formatar_valor_reais(subtotal_valor):>20}")

        # 3. TOTAL GERAL
        print(f"\n   {'='*130}")
        print(f"   {'TOTAL GERAL NÃO IMPORTADOS':<96} {criticas['total_movimentos_nao_importados']:>8,} {formatar_valor_reais(criticas['valor_total_nao_importado']):>20}")
        print(f"   {'='*130}")

    # OUTROS ERROS DE VALIDAÇÃO
    if criticas['erros_validacao']:
        print(f"\n" + "-" * 130)
        print(f"⚠️  OUTROS ERROS DE VALIDAÇÃO")
        print(f"-" * 130)
        for erro in criticas['erros_validacao'][:10]:
            print(f"   - {erro}")
        if len(criticas['erros_validacao']) > 10:
            print(f"   ... e mais {len(criticas['erros_validacao']) - 10} erros")

    # CONCLUSÃO
    print(f"\n" + "=" * 130)
    if criticas['linhas_validas_para_importar'] > 0:
        percentual_validas = (criticas['linhas_validas_para_importar'] / criticas['linhas_no_periodo'] * 100) if criticas['linhas_no_periodo'] > 0 else 0
        percentual_nao_importadas = (criticas['total_movimentos_nao_importados'] / criticas['linhas_no_periodo'] * 100) if criticas['linhas_no_periodo'] > 0 else 0

        print(f"✅ ARQUIVO PODE SER IMPORTADO")
        print(f"\n   Resumo:")
        print(f"   - Total no período: {criticas['linhas_no_periodo']:,} movimentos")
        print(f"   - ✅ Serão importados: {criticas['linhas_validas_para_importar']:,} ({percentual_validas:.1f}%) - {formatar_valor_reais(criticas['valor_total_valido'])}")
        print(f"   - 🚫 Não serão importados: {criticas['total_movimentos_nao_importados']:,} ({percentual_nao_importadas:.1f}%) - {formatar_valor_reais(criticas['valor_total_nao_importado'])}")
    else:
        print(f"❌ ARQUIVO NÃO PODE SER IMPORTADO - Nenhuma linha válida encontrada")
        print(f"   - Total no período: {criticas['linhas_no_periodo']:,} movimentos")
        print(f"   - Todos foram rejeitados ({criticas['total_movimentos_nao_importados']:,} movimentos)")
    print("=" * 130 + "\n")


def main():
    """Função principal"""

    if len(sys.argv) < 4:
        print("Uso: python testar_critica_importacao.py <arquivo.xlsx> <data_inicio> <data_fim>")
        print("\nExemplo:")
        print("  python testar_critica_importacao.py movimentos.xlsx 2024-01-01 2024-12-31")
        sys.exit(1)

    arquivo_path = sys.argv[1]
    data_inicio_str = sys.argv[2]
    data_fim_str = sys.argv[3]

    # Validar arquivo
    if not os.path.exists(arquivo_path):
        print(f"❌ Erro: Arquivo '{arquivo_path}' não encontrado")
        sys.exit(1)

    if not arquivo_path.endswith(('.xlsx', '.xls')):
        print(f"❌ Erro: Arquivo deve ser Excel (.xlsx ou .xls)")
        sys.exit(1)

    # Validar datas
    try:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    except ValueError:
        print(f"❌ Erro: Formato de data inválido. Use YYYY-MM-DD")
        sys.exit(1)

    if data_inicio > data_fim:
        print(f"❌ Erro: Data inicial deve ser menor ou igual à data final")
        sys.exit(1)

    print(f"\n🔍 Analisando arquivo: {arquivo_path}")
    print(f"📅 Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
    print("\nAguarde...")

    try:
        # Carregar arquivo
        with open(arquivo_path, 'rb') as f:
            df = corrigir_estrutura_excel(f)

        if df.empty:
            print(f"❌ Erro: Arquivo está vazio ou não contém dados válidos")
            sys.exit(1)

        # Executar crítica
        criticas = analisar_arquivo_pre_importacao(df, data_inicio, data_fim)

        # Imprimir resultado
        imprimir_critica(criticas, os.path.basename(arquivo_path))

    except Exception as e:
        print(f"\n❌ Erro ao analisar arquivo: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
