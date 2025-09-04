#!/usr/bin/env python
"""
Script para importar centros de custo via terminal
Execute: python import_centros_terminal.py
"""

import os
import sys
import django
from pathlib import Path

# Adicionar o diretório do projeto ao Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import CentroCusto

def main():
    """Função principal de importação"""
    
    print("=== IMPORTADOR DE CENTROS DE CUSTO ===\n")
    
    # Lista de centros únicos (código, nome)
    centros_dados = [
        ("10.10.12", "Logística"),
        ("10.10.13", "Transportes"),
        ("10.10.50", "Logística _ ECOM"),
        ("10.10.60", "Logística _ F&E"),
        ("10.20.31", "Compras Internacionais"),
        ("10.20.32", "Compras Nacionais"),
        ("10.20.33", "Comex"),
        ("10.20.34", "Engenharia de Processo"),
        ("10.20.35", "Engenharia de Produto"),
        ("10.20.36", "Qualidade"),
        ("10.20.37", "PCP"),
        ("10.20.38", "Produção"),
        ("10.20.39", "Assistência Técnica"),
        ("10.30.51", "Educacional _ BF"),
        ("10.30.52", "Infraestrutura _ BF"),
        ("10.30.53", "Novos Negócios _ BF"),
        ("10.30.54", "Estratégico _ BF"),
        ("20.02.02", "Coml Vendas _ LOJAS"),
        ("20.03.03", "Intelig Mercado _ LOJAS"),
        ("20.05.05", "Prev de Perdas _ LOJAS"),
        ("20.06.06", "Contábil Fiscal _ LOJAS"),
        ("20.08.08", "Rec Humanos _ LOJAS"),
        ("20.10.01", "Coml Compras (Folha)"),
        ("20.10.10", "Financeiro _ LOJAS"),
        ("20.11.11", "Jurídico _ LOJAS"),
        ("20.16.02", "Patrimonial & Coml Vendas _ UTILIZAR 90.16.02"),
        ("20.16.05", "Patrimonial & Prev Perdas _ LOJAS"),
        ("20.16.15", "Patrimonial & Educacional"),
        ("20.16.16", "Patrimonial _ LOJAS"),
        ("20.18.18", "TI _ LOJAS"),
        ("20.20.02", "Comercial"),
        ("20.20.40", "Exportação"),
        ("20.20.54", "Feiras Regionais _ BF"),
        ("20.30.03", "Adm Vendas _ Coml"),
        ("20.40.20", "Lojas"),
        ("20.40.30", "Televendas"),
        ("20.40.40", "Vendas Externas"),
        ("20.40.50", "Ecommerce"),
        ("20.40.51", "Market Place_Shopee"),
        ("20.40.60", "Feiras e Eventos"),
        ("20.50.01", "Regional Sul / Sudeste"),
        ("20.50.02", "Regional SP"),
        ("20.50.03", "Regional RJ"),
        ("20.50.04", "Regional Norte / Nordeste"),
        ("20.50.05", "Regional Norte / Centro Oeste"),
        ("30.02.02", "Coml Vendas _ TLV"),
        ("30.05.05", "Prev de Perdas _ TLV"),
        ("30.06.06", "Contábil Fiscal _ TLV"),
        ("30.07.12", "DP & TLV Log"),
        ("30.08.08", "Rec Humanos _ TLV"),
        ("30.10.10", "Financeiro _ TLV"),
        ("30.10.14", "Marketing"),
        ("30.10.55", "Marketing _ Comunicação"),
        ("30.10.56", "Marketing _ CRM"),
        ("30.10.57", "Marketing _ Performance"),
        ("30.11.11", "Jurídico _ TLV"),
        ("30.16.16", "Patrimonial _ TLV"),
        ("30.18.18", "TI _ TLV"),
        ("30.20.15", "Educacional"),
        ("30.30.19", "SAC VERIFICAR"),
        ("30.40.02", "Merchandising"),
        ("30.40.04", "Merchandising Regional Sul"),
        ("30.40.05", "Merchandising Regional SP"),
        ("30.40.06", "Merchandising Regional RJ"),
        ("30.40.07", "Merchandising Regional NO / NE"),
        ("30.40.08", "Merchandising Regional Centro Oeste"),
        ("40.02.02", "Coml Vendas _ VEX"),
        ("40.03.02", "Adm Vendas & Coml Vendas VEX UTILIZAR 40.02.02"),
        ("40.05.05", "Prev de Perdas _ VEX"),
        ("40.06.06", "Contábil Fiscal _ VEX"),
        ("40.08.08", "Rec Humanos _ VEX"),
        ("40.10.10", "Financeiro _ VEX"),
        ("40.11.11", "Jurídico _ VEX"),
        ("40.16.16", "Patrimonial _ VEX"),
        ("40.18.18", "TI _ VEX"),
        ("50.02.02", "Coml Vendas _ ECOM"),
        ("50.05.05", "Prev de Perdas _ Ecomm"),
        ("50.06.06", "Contábil Fiscal _ ECOM"),
        ("50.07.12", "DP & Ecom Log"),
        ("50.07.50", "DP & Ecom Restrito"),
        ("50.08.08", "Rec Humanos _ ECOM"),
        ("50.10.10", "Financeiro _ ECOM"),
        ("50.11.11", "Jurídico _ ECOM"),
        ("50.16.16", "Patrimonial _ ECOM"),
        ("50.18.18", "TI _ ECOM"),
        ("51.02.02", "Coml Vendas _ MKTPLC_Shopee"),
        ("51.06.06", "Contabil Fiscal _ MKTPLC_Shopee"),
        ("51.10.10", "Financeiro _ MKTPLC_Shopee"),
        ("51.18.18", "TI _ MKTPLC_Shopee"),
        ("60.02.02", "Coml Vendas _ F&E"),
        ("60.05.05", "Prev de Perdas _ F&E"),
        ("60.06.06", "Contábil Fiscal _ F&E"),
        ("60.07.12", "DP & F&E Log"),
        ("60.08.08", "Rec Humanos _ F&E"),
        ("60.10.10", "Financeiro _ F&E"),
        ("60.16.16", "Patrimonial _ F&E"),
        ("60.18.18", "TI _ F&E"),
        ("90.00.00", "Administrativo"),
        ("90.00.93", "Operações"),
        ("90.01.01", "Coml Compras"),
        ("90.02.02", "Coml Vendas"),
        ("90.03.03", "Intelig Mercado / Cad"),
        ("90.04.04", "Controladoria"),
        ("90.05.05", "Prev de Perdas"),
        ("90.05.12", "Prev de Perdas & Logística"),
        ("90.06.01", "Contábil Fiscal & Coml Compras"),
        ("90.06.02", "Contábil Fiscal & Coml Vendas"),
        ("90.06.03", "Contábil Fiscal & Intelig Mercado"),
        ("90.06.04", "Contábil Fiscal & Controladoria"),
        ("90.06.05", "Contábil Fiscal & Prev de Perdas"),
        ("90.06.06", "Contábil Fiscal"),
        ("90.06.07", "Contábil Fiscal & DP"),
        ("90.06.08", "Contábil Fiscal & RH"),
        ("90.06.09", "Contábil Fiscal & Diretoria"),
        ("90.06.10", "Contábil Fiscal & Financeiro"),
        ("90.06.11", "Contábil Fiscal & Jurídico"),
        ("90.06.12", "Contábil Fiscal & Logística"),
        ("90.06.13", "Contábil Fiscal & Transportes"),
        ("90.06.14", "Contábil Fiscal & Marketing"),
        ("90.06.15", "Contábil Fiscal & Educacional"),
        ("90.06.16", "Contábil Fiscal & Patrimonial"),
        ("90.06.17", "Contábil Fiscal & Facilities"),
        ("90.06.18", "Contábil Fiscal & TI"),
        ("90.06.19", "Contábil Fiscal & Adm Vendas"),
        ("90.06.91", "Contábil Fiscal & Grupo"),
        ("90.06.98", "Contábil Fiscal & Aj Avaliação Patrimonial"),
        ("90.07.03", "DP & Intelig Mercado"),
        ("90.07.04", "DP & Controladoria"),
        ("90.07.05", "DP & Prev de Perdas"),
        ("90.07.06", "DP & Contábil Fiscal"),
        ("90.07.07", "Departamento Pessoal"),
        ("90.07.08", "DP & Rec Humanos"),
        ("90.07.09", "DP & Diretoria"),
        ("90.07.10", "DP & Financeiro"),
        ("90.07.11", "DP & Jurídico"),
        ("90.07.12", "DP & Logística"),
        ("90.07.13", "DP & Transportes"),
        ("90.07.14", "DP & Marketing"),
        ("90.07.15", "DP & Educacional"),
        ("90.07.16", "DP & Patrimonial"),
        ("90.07.17", "DP & Facilities"),
        ("90.07.18", "DP & TI"),
        ("90.07.19", "DP & Adm Vendas"),
        ("90.07.93", "DP & Adm Operações"),
        ("90.08.01", "RH & Coml Compras"),
        ("90.08.02", "RH & Coml Vendas"),
        ("90.08.03", "RH & Intelig Mercado"),
        ("90.08.04", "RH & Controladoria"),
        ("90.08.05", "RH & Prev de Perdas"),
        ("90.08.06", "RH & Contábil Fiscal"),
        ("90.08.07", "RH & Depto Pessoal"),
        ("90.08.08", "Recursos Humanos"),
        ("90.08.09", "RH & Diretoria"),
        ("90.08.10", "RH & Financeiro"),
        ("90.08.11", "RH & Jurídico"),
        ("90.08.12", "RH & Logística"),
        ("90.08.13", "RH & Transportes"),
        ("90.08.14", "RH & Marketing"),
        ("90.08.15", "RH & Educacional"),
        ("90.08.16", "RH & Patrimonial"),
        ("90.08.17", "RH & Facilities"),
        ("90.08.18", "RH & TI"),
        ("90.08.19", "RH & Adm Vendas"),
        ("90.09.09", "Diretoria"),
        ("90.09.92", "Diretoria Corporativo"),
        ("90.10.10", "Financeiro"),
        ("90.11.06", "Jurídico & Contábil Fiscal"),
        ("90.11.07", "Jurídico & Depto Pessoal"),
        ("90.11.10", "Jurídico & Financeiro"),
        ("90.11.11", "Jurídico"),
        ("90.11.12", "Jurídico & Logística"),
        ("90.11.14", "Jurídico & Marketing"),
        ("90.11.16", "Jurídico & Patrimonial"),
        ("90.16.01", "Patrimonial & Coml Compras"),
        ("90.16.02", "Patrimonial & Coml Vendas"),
        ("90.16.05", "Patrimonial & Prev Perdas"),
        ("90.16.12", "Patrimonial & Logística"),
        ("90.16.16", "Patrimonial"),
        ("90.16.18", "Patrimonial & TI"),
        ("90.17.17", "Facilities"),
        ("90.18.01", "TI & Coml Compras"),
        ("90.18.02", "TI & Coml Vendas"),
        ("90.18.03", "TI & Intelig Mercado"),
        ("90.18.04", "TI & Controladoria"),
        ("90.18.05", "TI & Prev de Perdas"),
        ("90.18.06", "TI & Contábil Fiscal"),
        ("90.18.07", "TI & Depto Pessoal"),
        ("90.18.08", "TI & Rec Humanos"),
        ("90.18.09", "TI & Diretoria"),
        ("90.18.10", "TI & Financeiro"),
        ("90.18.11", "TI & Jurídico"),
        ("90.18.12", "TI & Logística"),
        ("90.18.13", "TI & Transportes"),
        ("90.18.14", "TI & Marketing"),
        ("90.18.15", "TI & Educacional"),
        ("90.18.16", "TI & Patrimonial"),
        ("90.18.17", "TI & Facilities"),
        ("90.18.18", "TI"),
        ("90.18.91", "TI & Grupo"),
        ("90.19.19", "Adm Vendas"),
    ]
    
    print(f"Encontrados {len(centros_dados)} centros únicos para importar\n")
    
    # Confirmar antes de executar
    resposta = input("Deseja prosseguir com a importação? (s/N): ")
    if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
        print("Importação cancelada.")
        return
    
    print("\nIniciando importação...\n")
    
    # Coletar todos os códigos pais necessários
    codigos_pais = set()
    for codigo, nome in centros_dados:
        partes = codigo.split('.')
        for i in range(1, len(partes)):
            codigo_pai = '.'.join(partes[:i])
            codigos_pais.add(codigo_pai)
    
    # Criar códigos pais primeiro
    sucessos = 0
    erros = 0
    
    print("Criando centros pais...")
    for codigo_pai in sorted(codigos_pais):
        try:
            centro_pai, created = CentroCusto.objects.get_or_create(
                codigo=codigo_pai,
                defaults={
                    'nome': f'Grupo {codigo_pai}',
                    'ativo': True,
                    'descricao': 'Centro sintético criado automaticamente'
                }
            )
            if created:
                print(f"  ✓ {codigo_pai} - {centro_pai.nome}")
                sucessos += 1
        except Exception as e:
            print(f"  ✗ Erro em {codigo_pai}: {e}")
            erros += 1
    
    print(f"\nCriando centros principais...")
    
    # Criar centros principais
    for codigo, nome in centros_dados:
        try:
            centro, created = CentroCusto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nome': nome,
                    'ativo': True
                }
            )
            
            if created:
                print(f"  ✓ {codigo} - {nome}")
                sucessos += 1
            else:
                print(f"  ○ {codigo} - {nome} (já existe)")
                
        except Exception as e:
            print(f"  ✗ Erro em {codigo}: {e}")
            erros += 1
    
    # Relatório final
    print(f"\n=== RESULTADO ===")
    print(f"Sucessos: {sucessos}")
    print(f"Erros: {erros}")
    
    # Estatísticas
    total = CentroCusto.objects.count()
    sinteticos = sum(1 for c in CentroCusto.objects.all() if c.tem_sub_centros)
    analiticos = total - sinteticos
    
    print(f"\n=== ESTATÍSTICAS ===")
    print(f"Total no banco: {total}")
    print(f"Sintéticos: {sinteticos}")
    print(f"Analíticos: {analiticos}")
    print("\nImportação concluída!")

if __name__ == "__main__":
    main()