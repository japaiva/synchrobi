#!/usr/bin/env python
"""
Script standalone para limpar Movimentos e Fornecedores

Uso direto:
    python limpar_dados_standalone.py
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

# Agora podemos importar os models
from core.models import Movimento, Fornecedor, GrupoFornecedor
from django.db import connection


def limpar_dados(confirmar=False):
    """
    Limpa todos os movimentos e fornecedores

    Args:
        confirmar: Se True, executa a exclusão. Se False, apenas mostra o que seria deletado.
    """

    print("=" * 80)
    print("LIMPEZA DE MOVIMENTOS E FORNECEDORES")
    print("=" * 80)

    # Contar registros atuais
    total_movimentos = Movimento.objects.count()
    total_fornecedores = Fornecedor.objects.count()
    total_fornecedores_auto = Fornecedor.objects.filter(criado_automaticamente=True).count()
    total_grupos = GrupoFornecedor.objects.count()

    print(f"\n📊 Registros atuais:")
    print(f"   - Movimentos: {total_movimentos:,}")
    print(f"   - Fornecedores: {total_fornecedores:,}")
    print(f"   - Fornecedores (criados automaticamente): {total_fornecedores_auto:,}")
    print(f"   - Grupos de Fornecedores: {total_grupos:,}")

    if not confirmar:
        print("\n⚠️  MODO DE VISUALIZAÇÃO - Nenhum dado será deletado")
        print("\nPara executar a exclusão, execute novamente com:")
        print("   python limpar_dados_standalone.py --confirmar")
        return

    print("\n⚠️  ATENÇÃO: Iniciando exclusão de dados...")
    resposta = input("\n🔴 Tem certeza que deseja APAGAR TODOS OS DADOS? (digite SIM para confirmar): ")

    if resposta.strip().upper() != 'SIM':
        print("\n❌ Operação cancelada pelo usuário")
        return

    # 1. Apagar Movimentos (primeiro, pois tem FK para Fornecedor)
    if total_movimentos > 0:
        print(f"\n🗑️  Apagando {total_movimentos:,} movimentos...")
        deleted_mov = Movimento.objects.all().delete()
        print(f"   ✓ {deleted_mov[0]:,} movimentos deletados")
    else:
        print("\n✓ Nenhum movimento para apagar")

    # 2. Apagar Fornecedores (depois que movimentos foram removidos)
    if total_fornecedores > 0:
        print(f"\n🗑️  Apagando {total_fornecedores:,} fornecedores...")
        deleted_forn = Fornecedor.objects.all().delete()
        print(f"   ✓ {deleted_forn[0]:,} fornecedores deletados")
    else:
        print("\n✓ Nenhum fornecedor para apagar")

    # 3. Opcionalmente, apagar Grupos de Fornecedores
    # Descomente as linhas abaixo se também quiser apagar os grupos
    # if total_grupos > 0:
    #     print(f"\n🗑️  Apagando {total_grupos:,} grupos de fornecedores...")
    #     deleted_grupos = GrupoFornecedor.objects.all().delete()
    #     print(f"   ✓ {deleted_grupos[0]:,} grupos deletados")

    print("\n" + "=" * 80)
    print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
    print("=" * 80)

    # Verificar contagens finais
    print(f"\n📊 Registros restantes:")
    print(f"   - Movimentos: {Movimento.objects.count():,}")
    print(f"   - Fornecedores: {Fornecedor.objects.count():,}")
    print(f"   - Grupos de Fornecedores: {GrupoFornecedor.objects.count():,}")


def limpar_apenas_fornecedores_automaticos(confirmar=False):
    """
    Limpa apenas fornecedores criados automaticamente
    (CUIDADO: Isso pode causar erros de integridade se houver movimentos referenciando-os)
    """
    total = Fornecedor.objects.filter(criado_automaticamente=True).count()

    print(f"\n📊 Fornecedores criados automaticamente: {total:,}")

    if not confirmar:
        print("\n⚠️  MODO DE VISUALIZAÇÃO")
        return

    if total > 0:
        resposta = input(f"\n🔴 Confirma apagar {total:,} fornecedores automáticos? (digite SIM): ")
        if resposta.strip().upper() != 'SIM':
            print("\n❌ Operação cancelada")
            return

        print(f"🗑️  Apagando {total:,} fornecedores automáticos...")
        deleted = Fornecedor.objects.filter(criado_automaticamente=True).delete()
        print(f"✓ {deleted[0]:,} fornecedores deletados")


def limpar_movimentos_periodo(data_inicio, data_fim, confirmar=False):
    """
    Limpa apenas movimentos de um período específico

    Args:
        data_inicio: Data inicial (formato: 'YYYY-MM-DD')
        data_fim: Data final (formato: 'YYYY-MM-DD')
        confirmar: Se True, executa a exclusão
    """
    from datetime import datetime

    # Converter strings para date
    if isinstance(data_inicio, str):
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if isinstance(data_fim, str):
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

    movimentos = Movimento.objects.filter(data__gte=data_inicio, data__lte=data_fim)
    total = movimentos.count()

    print(f"\n📊 Movimentos no período {data_inicio} a {data_fim}: {total:,}")

    if not confirmar:
        print("\n⚠️  MODO DE VISUALIZAÇÃO")
        return

    if total > 0:
        resposta = input(f"\n🔴 Confirma apagar {total:,} movimentos? (digite SIM): ")
        if resposta.strip().upper() != 'SIM':
            print("\n❌ Operação cancelada")
            return

        print(f"🗑️  Apagando {total:,} movimentos...")
        deleted = movimentos.delete()
        print(f"✓ {deleted[0]:,} movimentos deletados")


def executar_sql_direto():
    """
    Queries SQL diretas (mais rápido para grandes volumes)
    CUIDADO: Não aciona signals do Django
    """
    print("\n⚠️  ATENÇÃO: Executará SQL direto (sem signals Django)")
    resposta = input("🔴 Tem certeza? (digite SIM): ")

    if resposta.strip().upper() != 'SIM':
        print("\n❌ Operação cancelada")
        return

    with connection.cursor() as cursor:
        # Apagar movimentos
        cursor.execute("DELETE FROM movimentos;")
        print(f"✓ Movimentos deletados via SQL direto")

        # Apagar fornecedores
        cursor.execute("DELETE FROM fornecedores;")
        print(f"✓ Fornecedores deletados via SQL direto")


def mostrar_menu():
    """Mostra menu interativo"""
    print("\n" + "=" * 80)
    print("OPÇÕES DISPONÍVEIS:")
    print("=" * 80)
    print("\n1. Visualizar dados atuais (não apaga nada)")
    print("2. Apagar TODOS os movimentos e fornecedores")
    print("3. Apagar apenas fornecedores criados automaticamente")
    print("4. Apagar movimentos de um período específico")
    print("5. SQL direto (mais rápido, mas sem signals Django)")
    print("0. Sair")
    print("\n" + "=" * 80)

    return input("\nEscolha uma opção: ").strip()


# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == '__main__':
    # Verificar argumentos de linha de comando
    if '--confirmar' in sys.argv:
        limpar_dados(confirmar=True)
        sys.exit(0)

    if '--auto' in sys.argv:
        # Modo não-interativo para scripts
        limpar_dados(confirmar=True)
        sys.exit(0)

    # Modo interativo
    while True:
        opcao = mostrar_menu()

        if opcao == '0':
            print("\n👋 Saindo...")
            break

        elif opcao == '1':
            limpar_dados(confirmar=False)

        elif opcao == '2':
            limpar_dados(confirmar=True)

        elif opcao == '3':
            limpar_apenas_fornecedores_automaticos(confirmar=True)

        elif opcao == '4':
            data_inicio = input("Data inicial (YYYY-MM-DD): ").strip()
            data_fim = input("Data final (YYYY-MM-DD): ").strip()
            try:
                limpar_movimentos_periodo(data_inicio, data_fim, confirmar=True)
            except ValueError as e:
                print(f"❌ Erro: {e}")

        elif opcao == '5':
            executar_sql_direto()

        else:
            print("\n❌ Opção inválida!")

        input("\n[Pressione ENTER para continuar...]")
