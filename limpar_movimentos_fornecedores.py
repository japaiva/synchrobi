"""
Script para limpar Movimentos e Fornecedores antes de nova importação

Uso:
    python manage.py shell < limpar_movimentos_fornecedores.py

    OU dentro do Django shell:

    python manage.py shell
    >>> exec(open('limpar_movimentos_fornecedores.py').read())
"""

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
        print("\nPara executar a exclusão, chame:")
        print("   limpar_dados(confirmar=True)")
        return

    print("\n⚠️  ATENÇÃO: Iniciando exclusão de dados...")

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

    # Resetar sequências (IDs) - opcional
    # resetar_sequencias()

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

    print(f"📊 Fornecedores criados automaticamente: {total:,}")

    if not confirmar:
        print("\n⚠️  MODO DE VISUALIZAÇÃO")
        print("Para executar, chame: limpar_apenas_fornecedores_automaticos(confirmar=True)")
        return

    if total > 0:
        print(f"🗑️  Apagando {total:,} fornecedores automáticos...")
        deleted = Fornecedor.objects.filter(criado_automaticamente=True).delete()
        print(f"✓ {deleted[0]:,} fornecedores deletados")


def limpar_movimentos_periodo(data_inicio, data_fim, confirmar=False):
    """
    Limpa apenas movimentos de um período específico

    Args:
        data_inicio: Data inicial (formato: 'YYYY-MM-DD' ou objeto date)
        data_fim: Data final (formato: 'YYYY-MM-DD' ou objeto date)
        confirmar: Se True, executa a exclusão

    Exemplo:
        limpar_movimentos_periodo('2024-01-01', '2024-12-31', confirmar=True)
    """
    from datetime import datetime

    # Converter strings para date se necessário
    if isinstance(data_inicio, str):
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if isinstance(data_fim, str):
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

    movimentos = Movimento.objects.filter(data__gte=data_inicio, data__lte=data_fim)
    total = movimentos.count()

    print(f"📊 Movimentos no período {data_inicio} a {data_fim}: {total:,}")

    if not confirmar:
        print("\n⚠️  MODO DE VISUALIZAÇÃO")
        print(f"Para executar, chame:")
        print(f"   limpar_movimentos_periodo('{data_inicio}', '{data_fim}', confirmar=True)")
        return

    if total > 0:
        print(f"🗑️  Apagando {total:,} movimentos...")
        deleted = movimentos.delete()
        print(f"✓ {deleted[0]:,} movimentos deletados")


def resetar_sequencias():
    """
    Reseta as sequências (auto-increment) das tabelas
    CUIDADO: Use apenas se tiver certeza que as tabelas estão vazias
    """
    with connection.cursor() as cursor:
        # PostgreSQL
        if connection.vendor == 'postgresql':
            cursor.execute("ALTER SEQUENCE movimentos_id_seq RESTART WITH 1;")
            print("✓ Sequência de movimentos resetada")

        # SQLite - não tem sequências, mas podemos resetar o sqlite_sequence
        elif connection.vendor == 'sqlite':
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='movimentos';")
            print("✓ Sequência de movimentos resetada")


def executar_sql_direto():
    """
    Queries SQL diretas (mais rápido para grandes volumes)
    CUIDADO: Não aciona signals do Django
    """
    with connection.cursor() as cursor:
        # Apagar movimentos
        cursor.execute("DELETE FROM movimentos;")
        print(f"✓ Movimentos deletados via SQL direto")

        # Apagar fornecedores
        cursor.execute("DELETE FROM fornecedores;")
        print(f"✓ Fornecedores deletados via SQL direto")

        # Opcional: Apagar grupos
        # cursor.execute("DELETE FROM grupos_fornecedores;")
        # print(f"✓ Grupos deletados via SQL direto")


# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("OPÇÕES DISPONÍVEIS:")
    print("=" * 80)
    print("\n1. Visualizar o que será deletado:")
    print("   >>> limpar_dados()")
    print("\n2. Executar limpeza completa:")
    print("   >>> limpar_dados(confirmar=True)")
    print("\n3. Limpar apenas fornecedores automáticos:")
    print("   >>> limpar_apenas_fornecedores_automaticos(confirmar=True)")
    print("\n4. Limpar movimentos de um período:")
    print("   >>> limpar_movimentos_periodo('2024-01-01', '2024-12-31', confirmar=True)")
    print("\n5. SQL direto (mais rápido, mas sem signals Django):")
    print("   >>> executar_sql_direto()")
    print("\n" + "=" * 80)

    # Executar visualização por padrão
    limpar_dados(confirmar=False)
