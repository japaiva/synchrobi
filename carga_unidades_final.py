#!/usr/bin/env python
"""
Script de carga das unidades IKESAKI 
Baseado no arquivo "Unidades synchrobi.xlsx"
Execute: python carga_unidades_final.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import Unidade
import pandas as pd

def carregar_unidades_do_excel():
    """Carrega unidades diretamente do arquivo Excel"""
    
    try:
        # Ler arquivo Excel
        df = pd.read_excel('Unidades synchrobi.xlsx')
        
        print("=== CARGA DAS UNIDADES ORGANIZACIONAIS ===\n")
        print(f"Arquivo carregado com {len(df)} registros")
        
        # Verificar se deseja limpar base
        if input("Deseja limpar todas as unidades existentes? (s/N): ").lower() == 's':
            Unidade.objects.all().delete()
            print("✓ Unidades existentes removidas\n")
        
        criadas = 0
        atualizadas = 0
        erros = []
        
        # Ordenar por código para garantir que pais sejam criados antes dos filhos
        df_ordenado = df.sort_values('codigo')
        
        for index, row in df_ordenado.iterrows():
            try:
                codigo = str(row['codigo']).strip()
                codigo_pai = str(row['codigo pai']).strip() if pd.notna(row['codigo pai']) else None
                codigo_allstrategy = str(row['codigo all strategy']).strip() if pd.notna(row['codigo all strategy']) else ''
                nome = str(row['Nome da unidade']).strip()
                tipo = str(row['Sintético /\r\nAnalítico']).strip().upper()
                
                if not codigo or not nome:
                    continue
                
                # Buscar pai se existe
                unidade_pai = None
                if codigo_pai and codigo_pai != codigo:  # Evitar auto-referência
                    try:
                        unidade_pai = Unidade.objects.get(codigo=codigo_pai)
                    except Unidade.DoesNotExist:
                        print(f"⚠️  Pai não encontrado para {codigo}: {codigo_pai}")
                
                # Criar ou atualizar unidade
                unidade, criada = Unidade.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        'codigo_allstrategy': codigo_allstrategy,
                        'nome': nome,
                        'tipo': tipo,
                        'unidade_pai': unidade_pai,
                        'nivel': codigo.count('.') + 1,
                        'ativa': True,
                        'sincronizado_allstrategy': True
                    }
                )
                
                if criada:
                    criadas += 1
                    print(f"✓ Criada: {codigo} - {nome} ({tipo})")
                else:
                    # Atualizar dados existentes
                    unidade.codigo_allstrategy = codigo_allstrategy
                    unidade.nome = nome
                    unidade.tipo = tipo
                    unidade.unidade_pai = unidade_pai
                    unidade.nivel = codigo.count('.') + 1
                    unidade.save()
                    atualizadas += 1
                    print(f"↻ Atualizada: {codigo} - {nome} ({tipo})")
                    
            except Exception as e:
                erro_msg = f"Erro na linha {index}: {str(e)}"
                erros.append(erro_msg)
                print(f"✗ {erro_msg}")
        
        print(f"\n=== RESUMO ===")
        print(f"Criadas: {criadas}")
        print(f"Atualizadas: {atualizadas}")
        print(f"Erros: {len(erros)}")
        
        if erros:
            print("\nErros encontrados:")
            for erro in erros[:5]:  # Mostrar apenas os primeiros 5 erros
                print(f"  - {erro}")
            if len(erros) > 5:
                print(f"  ... e mais {len(erros) - 5} erros")
        
        # Estatísticas finais
        total_unidades = Unidade.objects.count()
        unidades_sinteticas = Unidade.objects.filter(tipo='S').count()
        unidades_analiticas = Unidade.objects.filter(tipo='A').count()
        
        print(f"\n=== ESTATÍSTICAS ===")
        print(f"Total de unidades: {total_unidades}")
        print(f"Sintéticas: {unidades_sinteticas}")
        print(f"Analíticas: {unidades_analiticas}")
        
        return {
            'criadas': criadas,
            'atualizadas': atualizadas,
            'erros': erros
        }
        
    except FileNotFoundError:
        print("❌ Arquivo 'Unidades synchrobi.xlsx' não encontrado!")
        return None
    except Exception as e:
        print(f"❌ Erro ao processar arquivo: {str(e)}")
        return None

def carregar_unidades_manual():
    """Carga manual com dados extraídos do Excel"""
    
    # Dados extraídos do arquivo Excel
    unidades_data = [
        ("1", "1", "1", "Grupo IKESAKI", "S"),
        ("1.1", "1", "1.1", "CONSOLIDADO HMI", "S"),
        ("1.1.01", "1.1", "001", "HMI", "A"),
        ("1.1.02", "1.1", "002", "Eliminações", "A"),
        ("1.2", "1", "1.2", "VAREJO", "S"),
        ("1.2.01", "1.2", "1.2.01", "Ikesaki Cosmeticos - CMC", "S"),
        ("1.2.01.20", "1.2.01", "1.2.01.20", "Lojas", "S"),
        ("1.2.01.20.01", "1.2.01.20", "1.2.01.20.01", "Loja Modelo", "S"),
        ("1.2.01.20.01.101", "1.2.01.20.01", "101", "101 Galvão Bueno", "A"),
        ("1.2.01.20.02", "1.2.01.20", "1.2.01.20.02", "Lojas de Rua", "S"),
        # ... resto dos dados (todas as 82 linhas)
    ]
    
    print("=== CARGA MANUAL DAS UNIDADES ===\n")
    
    # Verificar se deseja limpar base
    if input("Deseja limpar todas as unidades existentes? (s/N): ").lower() == 's':
        Unidade.objects.all().delete()
        print("✓ Unidades existentes removidas\n")
    
    criadas = 0
    atualizadas = 0
    
    for codigo, codigo_pai_str, codigo_allstrategy, nome, tipo in unidades_data:
        try:
            # Buscar pai se existe
            unidade_pai = None
            if codigo_pai_str and codigo_pai_str != codigo:
                try:
                    unidade_pai = Unidade.objects.get(codigo=codigo_pai_str)
                except Unidade.DoesNotExist:
                    pass
            
            # Criar ou atualizar
            unidade, criada = Unidade.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'codigo_allstrategy': codigo_allstrategy,
                    'nome': nome,
                    'tipo': tipo,
                    'unidade_pai': unidade_pai,
                    'nivel': codigo.count('.') + 1,
                    'ativa': True
                }
            )
            
            if criada:
                criadas += 1
                print(f"✓ Criada: {codigo} - {nome}")
            else:
                atualizadas += 1
                print(f"↻ Atualizada: {codigo} - {nome}")
                
        except Exception as e:
            print(f"✗ Erro em {codigo}: {str(e)}")
    
    print(f"\nCriadas: {criadas}, Atualizadas: {atualizadas}")

if __name__ == '__main__':
    print("Escolha o método de carga:")
    print("1 - Carregar do arquivo Excel")
    print("2 - Carga manual (dados no script)")
    
    escolha = input("Digite 1 ou 2: ").strip()
    
    if escolha == "1":
        carregar_unidades_do_excel()
    elif escolha == "2":
        carregar_unidades_manual()
    else:
        print("Opção inválida!")