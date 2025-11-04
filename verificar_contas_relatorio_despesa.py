#!/usr/bin/env python
"""
Script para verificar e atualizar contas com relatorio_despesa = False

Uso:
    python manage.py shell < verificar_contas_relatorio_despesa.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import ContaContabil, ContaExterna
from django.db import transaction


def listar_contas_sem_relatorio():
    """Lista todas as contas contábeis com relatorio_despesa = False"""

    print("\n" + "=" * 100)
    print("CONTAS SEM RELATÓRIO DE DESPESA (relatorio_despesa = False)")
    print("=" * 100)

    # Contas internas
    contas_internas = ContaContabil.objects.filter(relatorio_despesa=False).order_by('codigo')

    print(f"\n📋 Total de contas contábeis com relatorio_despesa = False: {contas_internas.count()}")

    if contas_internas.exists():
        print(f"\n{'Código':<20} {'Nome':<60} {'Tipo':<10}")
        print("-" * 100)

        for conta in contas_internas:
            nome_curto = conta.nome[:60] if len(conta.nome) > 60 else conta.nome
            tipo = 'Sintético' if conta.tipo == 'S' else 'Analítico'
            print(f"{conta.codigo:<20} {nome_curto:<60} {tipo:<10}")

    # Verificar códigos externos dessas contas
    print(f"\n" + "-" * 100)
    print(f"CÓDIGOS EXTERNOS (ERP) AFETADOS")
    print("-" * 100)

    total_externos = 0
    contas_com_externos = []

    for conta in contas_internas:
        externos = ContaExterna.objects.filter(
            conta_contabil=conta,
            ativa=True
        ).order_by('codigo_externo')

        if externos.exists():
            contas_com_externos.append({
                'conta': conta,
                'externos': list(externos),
                'total': externos.count()
            })
            total_externos += externos.count()

    print(f"\nTotal de códigos externos afetados: {total_externos}")

    if contas_com_externos:
        print(f"\nDetalhamento:")
        for item in contas_com_externos:
            conta = item['conta']
            print(f"\n   {conta.codigo} - {conta.nome}")
            print(f"   Códigos ERP ({item['total']}):")
            for ext in item['externos'][:10]:  # Mostrar primeiros 10
                print(f"      - {ext.codigo_externo}: {ext.nome_externo}")
            if item['total'] > 10:
                print(f"      ... e mais {item['total'] - 10}")

    return contas_internas, total_externos


def listar_contas_codigo_especifico(codigo_externo):
    """Lista informações de um código externo específico"""

    print(f"\n" + "=" * 100)
    print(f"INFORMAÇÕES DO CÓDIGO: {codigo_externo}")
    print("=" * 100)

    externas = ContaExterna.objects.filter(codigo_externo=codigo_externo)

    if not externas.exists():
        print(f"\n❌ Código externo '{codigo_externo}' não encontrado")
        return

    for externa in externas:
        conta = externa.conta_contabil
        print(f"\n📋 Código Externo: {externa.codigo_externo}")
        print(f"   Nome Externo: {externa.nome_externo}")
        print(f"   Ativa: {'Sim' if externa.ativa else 'Não'}")
        print(f"\n📊 Conta Contábil: {conta.codigo}")
        print(f"   Nome: {conta.nome}")
        print(f"   Tipo: {'Sintético' if conta.tipo == 'S' else 'Analítico'}")
        print(f"   ⚠️  Relatório Despesa: {'SIM' if conta.relatorio_despesa else 'NÃO'}")
        print(f"   Ativa: {'Sim' if conta.ativa else 'Não'}")


def atualizar_todas_para_sim(confirmar=False):
    """Atualiza TODAS as contas para relatorio_despesa = True"""

    contas = ContaContabil.objects.filter(relatorio_despesa=False)
    total = contas.count()

    print(f"\n" + "=" * 100)
    print(f"ATUALIZAR TODAS AS CONTAS PARA relatorio_despesa = True")
    print("=" * 100)

    print(f"\nTotal de contas a serem atualizadas: {total}")

    if not confirmar:
        print(f"\n⚠️  MODO DE VISUALIZAÇÃO")
        print(f"Para executar, chame: atualizar_todas_para_sim(confirmar=True)")
        return

    confirmacao = input(f"\n🔴 Tem certeza que deseja atualizar {total} contas? (digite SIM): ")
    if confirmacao.strip().upper() != 'SIM':
        print("\n❌ Operação cancelada")
        return

    print(f"\n💾 Atualizando...")

    with transaction.atomic():
        atualizado = contas.update(relatorio_despesa=True)

    print(f"✅ {atualizado} contas atualizadas com sucesso!")


def atualizar_contas_especificas(codigos_contas, confirmar=False):
    """
    Atualiza contas específicas para relatorio_despesa = True

    Args:
        codigos_contas: Lista de códigos de contas contábeis
        confirmar: Se True, executa a atualização
    """

    print(f"\n" + "=" * 100)
    print(f"ATUALIZAR CONTAS ESPECÍFICAS")
    print("=" * 100)

    contas_encontradas = []
    contas_nao_encontradas = []

    for codigo in codigos_contas:
        try:
            conta = ContaContabil.objects.get(codigo=codigo)
            contas_encontradas.append(conta)
            print(f"✓ {conta.codigo} - {conta.nome} (relatorio_despesa = {conta.relatorio_despesa})")
        except ContaContabil.DoesNotExist:
            contas_nao_encontradas.append(codigo)
            print(f"✗ {codigo} - NÃO ENCONTRADO")

    if contas_nao_encontradas:
        print(f"\n⚠️  {len(contas_nao_encontradas)} contas não encontradas:")
        for codigo in contas_nao_encontradas:
            print(f"   - {codigo}")

    if not contas_encontradas:
        print("\n❌ Nenhuma conta válida para atualizar")
        return

    if not confirmar:
        print(f"\n⚠️  MODO DE VISUALIZAÇÃO")
        print(f"Para executar, chame:")
        print(f"   atualizar_contas_especificas({codigos_contas}, confirmar=True)")
        return

    confirmacao = input(f"\n🔴 Confirma atualização de {len(contas_encontradas)} contas? (digite SIM): ")
    if confirmacao.strip().upper() != 'SIM':
        print("\n❌ Operação cancelada")
        return

    print(f"\n💾 Atualizando...")

    with transaction.atomic():
        for conta in contas_encontradas:
            conta.relatorio_despesa = True
            conta.save()

    print(f"✅ {len(contas_encontradas)} contas atualizadas com sucesso!")


def buscar_codigos_externos_problematicos():
    """Busca códigos externos que estão bloqueando importação"""

    print(f"\n" + "=" * 100)
    print(f"CÓDIGOS EXTERNOS BLOQUEADOS (relatorio_despesa = False)")
    print("=" * 100)

    # Buscar todas as contas externas cujas contas contábeis têm relatorio_despesa = False
    externas = ContaExterna.objects.filter(
        conta_contabil__relatorio_despesa=False,
        ativa=True
    ).select_related('conta_contabil').order_by('codigo_externo')

    total = externas.count()
    print(f"\nTotal: {total} códigos externos bloqueados")

    if total == 0:
        print("\n✅ Nenhum código externo bloqueado!")
        return

    # Agrupar por conta contábil
    from collections import defaultdict
    por_conta = defaultdict(list)

    for externa in externas:
        por_conta[externa.conta_contabil].append(externa)

    print(f"\nAgrupado por conta contábil ({len(por_conta)} contas distintas):")

    for conta, lista_externas in sorted(por_conta.items(), key=lambda x: x[0].codigo):
        print(f"\n   {conta.codigo} - {conta.nome}")
        print(f"   Total de códigos ERP: {len(lista_externas)}")
        print(f"   Códigos:")
        for ext in lista_externas[:5]:
            print(f"      - {ext.codigo_externo}: {ext.nome_externo}")
        if len(lista_externas) > 5:
            print(f"      ... e mais {len(lista_externas) - 5}")


# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 100)
    print("FUNÇÕES DISPONÍVEIS:")
    print("=" * 100)
    print("\n1. Listar contas sem relatório de despesa:")
    print("   >>> listar_contas_sem_relatorio()")

    print("\n2. Ver código externo específico:")
    print("   >>> listar_contas_codigo_especifico('6101010003')")

    print("\n3. Buscar códigos externos bloqueados:")
    print("   >>> buscar_codigos_externos_problematicos()")

    print("\n4. Atualizar TODAS as contas para relatorio_despesa = True:")
    print("   >>> atualizar_todas_para_sim(confirmar=True)")

    print("\n5. Atualizar contas específicas:")
    print("   >>> atualizar_contas_especificas(['010.010.01', '130.010.01.01'], confirmar=True)")

    print("\n" + "=" * 100)

    # Executar análise por padrão
    print("\n🔍 Executando análise automática...")
    listar_contas_sem_relatorio()
    print("\n")
    buscar_codigos_externos_problematicos()
