#!/usr/bin/env python
"""
Script para importar contas externas faltantes

Lê o arquivo Excel com todas as combinações e compara com o CSV atual,
inserindo as que estão faltando na tabela contas_externas.

Uso:
    python importar_contas_externas_faltantes.py
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import ContaContabil, ContaExterna
from django.db import transaction


def carregar_excel(caminho):
    """Carrega o arquivo Excel com todas as combinações"""
    print(f"📂 Lendo arquivo Excel: {caminho}")

    # Arquivo tem cabeçalho na linha 2 (índice 1), pular linha 1
    df = pd.read_excel(caminho, header=1)
    print(f"   Total de linhas: {len(df):,}")

    # Mostrar colunas
    print(f"   Colunas: {list(df.columns)}")

    return df


def carregar_csv_atual(caminho):
    """Carrega o CSV com a situação atual"""
    print(f"\n📂 Lendo CSV atual: {caminho}")

    df = pd.read_csv(caminho)
    print(f"   Total de registros atuais: {len(df):,}")

    # Criar set de códigos externos já cadastrados
    codigos_existentes = set()
    for idx, row in df.iterrows():
        codigo_externo = str(row['codigo_externo']).strip()
        conta_contabil = str(row['conta_contabil_id']).strip()
        chave = f"{codigo_externo}|{conta_contabil}"
        codigos_existentes.add(chave)

    print(f"   Combinações únicas existentes: {len(codigos_existentes):,}")

    return codigos_existentes


def analisar_diferencas(df_excel, codigos_existentes):
    """Identifica quais combinações estão faltando"""
    print(f"\n🔍 Analisando diferenças...")

    faltantes = []
    duplicados_excel = []
    erros = []

    # Supondo que as colunas do Excel são algo como:
    # 'Cód. da conta contábil' e alguma outra coluna para descrição
    # Vou tentar identificar as colunas corretas

    colunas = list(df_excel.columns)
    print(f"\n   Colunas disponíveis no Excel:")
    for i, col in enumerate(colunas):
        print(f"   {i}: {col}")

    # Detectar colunas baseado na estrutura conhecida do arquivo C-Contabeis.xlsx
    # Coluna A (índice 0): "Estrutura" = código conta contábil
    # Coluna C (índice 2): "Código" = código externo
    # Coluna D (índice 3): "Nome conta externa" = descrição

    col_codigo_externo = None
    col_conta_contabil = None
    col_descricao = None

    for col in colunas:
        col_str = str(col).strip() if col else ''
        col_lower = col_str.lower()

        # Estrutura = conta contábil interna
        if 'estrutura' in col_lower:
            col_conta_contabil = col
        # Código = código externo ERP
        elif col_str == 'Código' or (col_str.startswith('Código') and 'externa' not in col_lower):
            col_codigo_externo = col
        # Nome conta externa = descrição
        elif 'nome' in col_lower and 'externa' in col_lower:
            col_descricao = col

    print(f"\n   Detectado:")
    print(f"   - Código Externo: {col_codigo_externo}")
    print(f"   - Conta Contábil: {col_conta_contabil}")
    print(f"   - Descrição: {col_descricao}")

    if not col_codigo_externo or not col_conta_contabil:
        print("\n❌ Erro: Não foi possível detectar as colunas necessárias")
        print("   Por favor, informe manualmente as colunas corretas no script")
        return None

    chaves_vistas = set()

    for idx, row in df_excel.iterrows():
        try:
            codigo_externo = str(row[col_codigo_externo]).strip()
            conta_contabil = str(row[col_conta_contabil]).strip()

            # Pular linhas vazias
            if not codigo_externo or codigo_externo == 'nan':
                continue
            if not conta_contabil or conta_contabil == 'nan':
                continue

            # Limpar código da conta contábil (remover espaços)
            conta_contabil = conta_contabil.replace(' ', '')

            # Descrição (opcional)
            descricao = ''
            if col_descricao and col_descricao in row:
                descricao = str(row[col_descricao]).strip()
                if descricao == 'nan':
                    descricao = ''

            # Se não tiver descrição, usar o código externo
            if not descricao:
                descricao = codigo_externo

            chave = f"{codigo_externo}|{conta_contabil}"

            # Verificar duplicados no próprio Excel
            if chave in chaves_vistas:
                duplicados_excel.append({
                    'codigo_externo': codigo_externo,
                    'conta_contabil': conta_contabil,
                    'linha': idx + 2
                })
                continue

            chaves_vistas.add(chave)

            # Verificar se já existe
            if chave not in codigos_existentes:
                faltantes.append({
                    'codigo_externo': codigo_externo,
                    'conta_contabil': conta_contabil,
                    'descricao': descricao,
                    'linha': idx + 2
                })

        except Exception as e:
            erros.append({
                'linha': idx + 2,
                'erro': str(e)
            })

    print(f"\n📊 Resultados da análise:")
    print(f"   Total no Excel: {len(df_excel):,}")
    print(f"   Já existentes: {len(chaves_vistas & codigos_existentes):,}")
    print(f"   Faltantes: {len(faltantes):,}")
    print(f"   Duplicados no Excel: {len(duplicados_excel):,}")
    print(f"   Erros: {len(erros):,}")

    if duplicados_excel:
        print(f"\n⚠️  Duplicados encontrados no Excel (primeiros 10):")
        for dup in duplicados_excel[:10]:
            print(f"   - Linha {dup['linha']}: {dup['codigo_externo']} | {dup['conta_contabil']}")

    if erros:
        print(f"\n❌ Erros encontrados (primeiros 10):")
        for erro in erros[:10]:
            print(f"   - Linha {erro['linha']}: {erro['erro']}")

    return faltantes


def importar_faltantes(faltantes, modo_teste=True):
    """Importa as contas externas faltantes"""

    if not faltantes:
        print("\n✅ Nenhuma conta faltante para importar!")
        return

    print(f"\n{'🔍 MODO TESTE' if modo_teste else '💾 IMPORTANDO'}: {len(faltantes):,} contas")

    sucessos = 0
    erros = []
    contas_nao_encontradas = set()

    for item in faltantes:
        try:
            codigo_externo = item['codigo_externo']
            codigo_conta = item['conta_contabil']
            descricao = item['descricao'] or codigo_externo

            # Verificar se a conta contábil existe
            try:
                conta = ContaContabil.objects.get(codigo=codigo_conta)
            except ContaContabil.DoesNotExist:
                contas_nao_encontradas.add(codigo_conta)
                erros.append({
                    'codigo_externo': codigo_externo,
                    'erro': f'Conta contábil {codigo_conta} não existe'
                })
                continue

            if not modo_teste:
                # Criar a conta externa
                ContaExterna.objects.create(
                    codigo_externo=codigo_externo,
                    nome_externo=descricao,
                    conta_contabil=conta,
                    sistema_origem='ERP',
                    ativa=True,
                    observacoes='Importado automaticamente'
                )

            sucessos += 1

        except Exception as e:
            erros.append({
                'codigo_externo': codigo_externo,
                'erro': str(e)
            })

    print(f"\n📊 Resultado:")
    print(f"   ✅ Sucessos: {sucessos:,}")
    print(f"   ❌ Erros: {len(erros):,}")

    if contas_nao_encontradas:
        print(f"\n⚠️  Contas Contábeis não encontradas ({len(contas_nao_encontradas)}):")
        for conta in sorted(list(contas_nao_encontradas))[:20]:
            print(f"   - {conta}")
        if len(contas_nao_encontradas) > 20:
            print(f"   ... e mais {len(contas_nao_encontradas) - 20}")

    if erros:
        print(f"\n❌ Erros (primeiros 10):")
        for erro in erros[:10]:
            print(f"   - {erro['codigo_externo']}: {erro['erro']}")

    return sucessos, erros


def main():
    """Função principal"""

    print("\n" + "=" * 80)
    print("IMPORTAÇÃO DE CONTAS EXTERNAS FALTANTES")
    print("=" * 80)

    # Caminhos dos arquivos
    excel_path = '/Users/joseantoniopaiva/Downloads/C-Contabeis.xlsx'
    csv_path = '/Users/joseantoniopaiva/Downloads/contas_externas.csv'

    # Verificar se arquivos existem
    if not os.path.exists(excel_path):
        print(f"\n❌ Arquivo Excel não encontrado: {excel_path}")
        return

    if not os.path.exists(csv_path):
        print(f"\n❌ Arquivo CSV não encontrado: {csv_path}")
        return

    # 1. Carregar Excel
    df_excel = carregar_excel(excel_path)

    # 2. Carregar CSV atual
    codigos_existentes = carregar_csv_atual(csv_path)

    # 3. Analisar diferenças
    faltantes = analisar_diferencas(df_excel, codigos_existentes)

    if faltantes is None:
        return

    if not faltantes:
        print("\n✅ Nenhuma conta faltante! Tudo já está importado.")
        return

    # 4. Perguntar ao usuário
    print(f"\n" + "=" * 80)
    print(f"Encontradas {len(faltantes):,} contas externas faltantes")
    print("=" * 80)

    # Mostrar primeiras 20
    print(f"\nPrimeiras 20 faltantes:")
    for i, item in enumerate(faltantes[:20], 1):
        print(f"   {i}. {item['codigo_externo']} → {item['conta_contabil']} ({item['descricao'][:40]})")

    if len(faltantes) > 20:
        print(f"   ... e mais {len(faltantes) - 20}")

    print(f"\nOpções:")
    print(f"1. Executar TESTE (não salva no banco)")
    print(f"2. IMPORTAR (salva no banco)")
    print(f"0. Sair")

    opcao = input("\nEscolha uma opção: ").strip()

    if opcao == '1':
        print("\n🔍 Executando em MODO TESTE...")
        importar_faltantes(faltantes, modo_teste=True)

    elif opcao == '2':
        confirmacao = input(f"\n🔴 Confirma importação de {len(faltantes):,} contas? (digite SIM): ").strip()
        if confirmacao.upper() == 'SIM':
            print("\n💾 Iniciando importação...")
            with transaction.atomic():
                sucessos, erros = importar_faltantes(faltantes, modo_teste=False)

            print(f"\n✅ Importação concluída!")
            print(f"   - Importadas: {sucessos:,}")
            print(f"   - Erros: {len(erros):,}")
        else:
            print("\n❌ Importação cancelada")

    else:
        print("\n👋 Saindo...")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
