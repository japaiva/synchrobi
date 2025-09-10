#!/usr/bin/env python
"""
Script para importar APENAS códigos externos da planilha para as contas contábeis do grupo 130
Execute: python script_importar_apenas_externos.py
"""

import os
import sys
import django
from pathlib import Path
import pandas as pd

# Adicionar o diretório do projeto ao Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import ContaContabil, ContaExterna
from django.db import models

def main():
    """Função principal de importação dos códigos externos"""
    
    print("=== IMPORTAÇÃO DE CÓDIGOS EXTERNOS DO GRUPO 130 ===\n")
    
    # 1. CARREGAR PLANILHA
    print("1. Carregando planilha de contas contábeis...")
    try:
        # Ler a planilha
        planilha_path = 'contas contabeis.xlsx'
        df = pd.read_excel(planilha_path)
        
        # Limpar nomes das colunas
        df.columns = df.columns.str.strip()
        
        print(f"   ✅ Planilha carregada: {len(df)} linhas")
        print(f"   Colunas: {list(df.columns)}")
        
    except Exception as e:
        print(f"   ❌ Erro ao carregar planilha: {e}")
        return
    
    # 2. FILTRAR APENAS GRUPO 130
    print("\n2. Filtrando dados do grupo 130...")
    
    # Filtrar apenas linhas que começam com 130 na coluna "Estrutura"
    df_grupo_130 = df[df['Estrutura'].astype(str).str.startswith('130')].copy()
    
    print(f"   ✅ Encontradas {len(df_grupo_130)} entradas do grupo 130")
    
    # 3. VERIFICAR CONTAS CONTÁBEIS EXISTENTES
    print("\n3. Verificando contas contábeis no banco...")
    
    contas_banco = {conta.codigo: conta for conta in ContaContabil.objects.all()}
    print(f"   ✅ Encontradas {len(contas_banco)} contas contábeis no banco")
    
    # 4. MOSTRAR ESTATÍSTICAS ANTES
    contas_externas_antes = ContaExterna.objects.count()
    print(f"   📊 Códigos externos antes: {contas_externas_antes}")
    
    # 5. CONFIRMAR ANTES DE PROSSEGUIR
    if contas_externas_antes > 0:
        resposta = input(f"\nJá existem {contas_externas_antes} códigos externos. Deseja limpar e reimportar? (s/N): ")
        if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
            print("Importação cancelada.")
            return
        
        print("\n4. Limpando contas externas existentes...")
        ContaExterna.objects.all().delete()
        print(f"   ✅ {contas_externas_antes} contas externas removidas")
    
    # 6. PROCESSAR E IMPORTAR CÓDIGOS EXTERNOS
    print("\n5. Processando códigos externos...")
    
    sucessos = 0
    erros = 0
    conta_nao_encontrada = 0
    sem_codigo_externo = 0
    
    for idx, row in df_grupo_130.iterrows():
        try:
            # Extrair dados da linha - apenas o essencial
            estrutura = str(row['Estrutura']).strip()
            codigo_externo = str(row['Código']).strip() if pd.notna(row['Código']) else None
            nome_externo = str(row['Nome conta externa']).strip() if pd.notna(row['Nome conta externa']) else None
            
            # Verificar se a conta interna existe
            if estrutura not in contas_banco:
                print(f"   ⚠️  Conta interna não encontrada: {estrutura}")
                conta_nao_encontrada += 1
                continue
            
            # Verificar se tem código externo
            if not codigo_externo or codigo_externo == 'nan' or codigo_externo == 'None':
                sem_codigo_externo += 1
                continue
            
            # Criar conta externa - simples e direto
            conta_externa = ContaExterna.objects.create(
                conta_contabil=contas_banco[estrutura],
                codigo_externo=codigo_externo,
                nome_externo=nome_externo or f"Conta {codigo_externo}",
                sistema_origem="ERP",  # Genérico
                empresas_utilizacao="",  # Vazio
                observacoes=f"Importado da planilha",
                ativa=True
            )
            
            print(f"   ✅ {estrutura} ← {codigo_externo}")
            sucessos += 1
            
        except Exception as e:
            print(f"   ❌ Erro na linha {idx + 2}: {e}")
            erros += 1
    
    # 7. RELATÓRIO FINAL
    print(f"\n=== RESULTADO DA IMPORTAÇÃO ===")
    print(f"Sucessos: {sucessos}")
    print(f"Erros: {erros}")
    print(f"Contas internas não encontradas: {conta_nao_encontrada}")
    print(f"Linhas sem código externo: {sem_codigo_externo}")
    
    # 8. ESTATÍSTICAS FINAIS
    print(f"\n=== ESTATÍSTICAS FINAIS ===")
    
    # Contas com códigos externos
    contas_com_externos = ContaContabil.objects.filter(contas_externas__isnull=False).distinct().count()
    total_contas_externas = ContaExterna.objects.count()
    
    print(f"Contas contábeis com códigos externos: {contas_com_externos}")
    print(f"Total de códigos externos importados: {total_contas_externas}")
    
    # Por sistema
    print(f"\n=== POR SISTEMA ===")
    sistemas = ContaExterna.objects.values('sistema_origem').annotate(count=models.Count('id')).order_by('-count')
    for sistema in sistemas:
        print(f"  - {sistema['sistema_origem']}: {sistema['count']} códigos")
    
    # Contas com mais códigos externos
    print(f"\n=== CONTAS COM MAIS CÓDIGOS EXTERNOS ===")
    contas_com_muitos_externos = (
        ContaContabil.objects
        .annotate(num_externos=models.Count('contas_externas'))
        .filter(num_externos__gt=1)
        .order_by('-num_externos')[:10]
    )
    
    for conta in contas_com_muitos_externos:
        print(f"  {conta.codigo} - {conta.nome}: {conta.num_externos} códigos externos")
    
    # Verificar alguns exemplos
    print(f"\n=== EXEMPLOS IMPORTADOS ===")
    exemplos = ContaExterna.objects.select_related('conta_contabil')[:5]
    for exemplo in exemplos:
        print(f"  {exemplo.conta_contabil.codigo} - {exemplo.conta_contabil.nome}")
        print(f"    → {exemplo.codigo_externo} ({exemplo.sistema_origem}) - {exemplo.nome_externo}")
    
    print("\n✅ Importação de códigos externos concluída!")
    print("\nPróximos passos:")
    print("1. Testar a visualização na árvore hierárquica")
    print("2. Implementar interface para gerenciar códigos externos")
    print("3. Configurar as views e templates fornecidos")

if __name__ == "__main__":
    main()