#!/usr/bin/env python
"""
Script standalone para corrigir contas com relatorio_despesa = False

Uso direto:
    python corrigir_relatorio_despesa_standalone.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import ContaContabil, ContaExterna
from django.db import transaction


def main():
    print("\n" + "=" * 100)
    print("DIAGNÓSTICO E CORREÇÃO - RELATÓRIO DE DESPESA")
    print("=" * 100)

    # 1. Contar contas com problema
    contas_false = ContaContabil.objects.filter(relatorio_despesa=False)
    total_false = contas_false.count()

    print(f"\n📊 SITUAÇÃO ATUAL:")
    print(f"   Contas com relatorio_despesa = False: {total_false}")

    if total_false == 0:
        print("\n✅ Nenhuma conta com problema! Todas estão OK.")
        return

    # 2. Buscar códigos externos afetados
    externos_afetados = ContaExterna.objects.filter(
        conta_contabil__relatorio_despesa=False,
        ativa=True
    ).count()

    print(f"   Códigos externos (ERP) afetados: {externos_afetados}")

    # 3. Mostrar as contas
    print(f"\n📋 CONTAS COM PROBLEMA:")
    print(f"   {'Código':<20} {'Nome':<70}")
    print(f"   {'-'*20} {'-'*70}")

    for conta in contas_false[:20]:
        nome = conta.nome[:70] if len(conta.nome) > 70 else conta.nome
        print(f"   {conta.codigo:<20} {nome:<70}")

    if total_false > 20:
        print(f"   ... e mais {total_false - 20} contas")

    # 4. Perguntar o que fazer
    print(f"\n" + "=" * 100)
    print(f"OPÇÕES:")
    print("=" * 100)
    print("\n1. Atualizar TODAS para relatorio_despesa = True (recomendado)")
    print("2. Mostrar códigos externos bloqueados")
    print("0. Sair")

    opcao = input("\nEscolha uma opção: ").strip()

    if opcao == '1':
        print(f"\n⚠️  Esta operação irá:")
        print(f"   - Atualizar {total_false} contas contábeis")
        print(f"   - Permitir importação de {externos_afetados} códigos ERP")
        print(f"   - Definir relatorio_despesa = True em todas")

        confirmacao = input(f"\n🔴 Confirma? (digite SIM): ").strip()

        if confirmacao.upper() == 'SIM':
            print(f"\n💾 Atualizando...")

            with transaction.atomic():
                atualizado = contas_false.update(relatorio_despesa=True)

            print(f"\n✅ SUCESSO!")
            print(f"   {atualizado} contas atualizadas")
            print(f"   Agora você pode importar os movimentos novamente")

        else:
            print(f"\n❌ Operação cancelada")

    elif opcao == '2':
        print(f"\n📋 CÓDIGOS EXTERNOS BLOQUEADOS:")

        externas = ContaExterna.objects.filter(
            conta_contabil__relatorio_despesa=False,
            ativa=True
        ).select_related('conta_contabil').order_by('codigo_externo')[:50]

        print(f"\n   {'Código ERP':<15} {'Conta':<20} {'Nome':<50}")
        print(f"   {'-'*15} {'-'*20} {'-'*50}")

        for ext in externas:
            nome = ext.nome_externo[:50] if len(ext.nome_externo) > 50 else ext.nome_externo
            print(f"   {ext.codigo_externo:<15} {ext.conta_contabil.codigo:<20} {nome:<50}")

        if externos_afetados > 50:
            print(f"\n   ... e mais {externos_afetados - 50}")

    else:
        print(f"\n👋 Saindo...")

    print("\n" + "=" * 100)


if __name__ == '__main__':
    main()
