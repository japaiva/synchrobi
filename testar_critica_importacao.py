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
    print(f"\n✅ LINHAS VÁLIDAS PARA IMPORTAR: {criticas['linhas_validas_para_importar']:,}")
    print(f"   Valor total a importar: {formatar_valor_reais(criticas['valor_total_valido'])}")

    # FILTRO DE RELATÓRIO DE DESPESAS
    print(f"\n" + "-" * 100)
    print(f"🚫 MOVIMENTOS NÃO IMPORTADOS (Conta marcada como 'não usar em relatório de despesas')")
    print(f"-" * 100)
    print(f"   Quantidade de movimentos: {criticas['linhas_sem_relatorio_despesa']:,}")
    print(f"   Valor total excluído: {formatar_valor_reais(criticas['valor_total_sem_relatorio_despesa'])}")
    if criticas['contas_sem_relatorio_despesa']:
        print(f"   Contas distintas envolvidas: {len(criticas['contas_sem_relatorio_despesa'])}")

    # PROBLEMAS DE VALIDAÇÃO
    print(f"\n" + "-" * 100)
    print(f"⚠️  PROBLEMAS DE VALIDAÇÃO")
    print(f"-" * 100)

    tem_problemas = False

    if criticas['unidades_nao_encontradas']:
        tem_problemas = True
        print(f"\n   ❌ Unidades não encontradas ({len(criticas['unidades_nao_encontradas'])} códigos distintos):")
        lista_unidades = sorted(list(criticas['unidades_nao_encontradas']))
        for i in range(0, min(20, len(lista_unidades)), 5):
            print(f"      {', '.join(lista_unidades[i:i+5])}")
        if len(lista_unidades) > 20:
            print(f"      ... e mais {len(lista_unidades) - 20}")

    if criticas['centros_nao_encontrados']:
        tem_problemas = True
        print(f"\n   ❌ Centros de Custo não encontrados ({len(criticas['centros_nao_encontrados'])} códigos distintos):")
        lista_centros = sorted(list(criticas['centros_nao_encontrados']))
        for i in range(0, min(20, len(lista_centros)), 5):
            print(f"      {', '.join(lista_centros[i:i+5])}")
        if len(lista_centros) > 20:
            print(f"      ... e mais {len(lista_centros) - 20}")

    if criticas['contas_nao_encontradas']:
        tem_problemas = True
        print(f"\n   ❌ Contas Contábeis não encontradas ({len(criticas['contas_nao_encontradas'])} códigos distintos):")
        lista_contas = sorted(list(criticas['contas_nao_encontradas']))
        for i in range(0, min(20, len(lista_contas)), 5):
            print(f"      {', '.join(lista_contas[i:i+5])}")
        if len(lista_contas) > 20:
            print(f"      ... e mais {len(lista_contas) - 20}")

    if criticas['erros_validacao']:
        tem_problemas = True
        print(f"\n   ❌ Outros erros de validação ({len(criticas['erros_validacao'])} erros):")
        for erro in criticas['erros_validacao'][:10]:
            print(f"      - {erro}")
        if len(criticas['erros_validacao']) > 10:
            print(f"      ... e mais {len(criticas['erros_validacao']) - 10} erros")

    if not tem_problemas:
        print("\n   ✅ Nenhum problema de validação encontrado!")

    # CONCLUSÃO
    print(f"\n" + "=" * 100)
    if criticas['linhas_validas_para_importar'] > 0:
        percentual = (criticas['linhas_validas_para_importar'] / criticas['linhas_no_periodo'] * 100) if criticas['linhas_no_periodo'] > 0 else 0
        print(f"✅ ARQUIVO PODE SER IMPORTADO")
        print(f"   {criticas['linhas_validas_para_importar']:,} de {criticas['linhas_no_periodo']:,} linhas no período serão importadas ({percentual:.1f}%)")
    else:
        print(f"❌ ARQUIVO NÃO PODE SER IMPORTADO - Nenhuma linha válida encontrada")
    print("=" * 100 + "\n")


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
