#!/usr/bin/env python
"""
Importação completa de todas as 82 unidades IKESAKI
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import Unidade

def importar_todas_unidades():
    """Importa todas as 82 unidades com dados corretos"""
    
    # Todos os dados extraídos do Excel
    unidades_dados = [
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
        ("1.2.01.20.02.102", "1.2.01.20.02", "102", "102 São Miguel", "A"),
        ("1.2.01.20.02.103", "1.2.01.20.02", "103", "103 Praça da Liberdade", "A"),
        ("1.2.01.20.02.105", "1.2.01.20.02", "105", "105 Santo Amaro", "A"),
        ("1.2.01.20.02.106", "1.2.01.20.02", "106", "106 Santo André", "A"),
        ("1.2.01.20.02.107", "1.2.01.20.02", "107", "107 Osasco", "A"),
        ("1.2.01.20.03", "1.2.01.20", "1.2.01.20.03", "Lojas de Shopping", "S"),
        ("1.2.01.20.03.108", "1.2.01.20.03", "108", "108 Tucuruvi", "A"),
        ("1.2.01.20.03.111", "1.2.01.20.03", "111", "111 Campinas", "A"),
        ("1.2.01.20.03.112", "1.2.01.20.03", "112", "112 Tatuapé", "A"),
        ("1.2.01.20.03.113", "1.2.01.20.03", "113", "113 Aricanduva", "A"),
        ("1.2.01.20.03.114", "1.2.01.20.03", "114", "114 Campo Limpo", "A"),
        ("1.2.01.20.03.115", "1.2.01.20.03", "115", "115 Sorocaba", "A"),
        ("1.2.01.20.03.116", "1.2.01.20.03", "116", "116 Santos", "A"),
        ("1.2.01.20.03.117", "1.2.01.20.03", "117", "117 Center Norte * Quiosque", "A"),
        ("1.2.01.20.03.118", "1.2.01.20.03", "118", "118 Center Norte", "A"),
        ("1.2.01.20.03.119", "1.2.01.20.03", "119", "119 SP Market", "A"),
        ("1.2.01.20.03.120", "1.2.01.20.03", "120", "120 Piracicaba", "A"),
        ("1.2.01.20.03.121", "1.2.01.20.03", "121", "121 Loja 8", "A"),
        ("1.2.01.20.03.122", "1.2.01.20.03", "122", "122 Loja 9", "A"),
        ("1.2.01.20.03.123", "1.2.01.20.03", "123", "123 Loja 10", "A"),
        ("1.2.01.20.03.124", "1.2.01.20.03", "124", "124 Loja 11", "A"),
        ("1.2.01.30", "1.2.01", "1.2.01.30", "Televendas", "S"),
        ("1.2.01.30.00.110", "1.2.01.30", "309930110", "Televendas", "A"),
        ("1.2.01.40", "1.2.01", "1.2.01.40", "Vendas Externas", "S"),
        ("1.2.01.40.00.110", "1.2.01.40", "409940110", "Vendas Externas", "A"),
        ("1.2.01.50", "1.2.01", "1.2.01.50", "Ecommerce", "S"),
        ("1.2.01.50.00.110", "1.2.01.50", "509950110", "Ecommerce", "A"),
        ("1.2.01.60", "1.2.01", "1.2.01.60", "Feiras e Eventos", "S"),
        ("1.2.01.60.00.110", "1.2.01.60", "609960101", "Feiras e Eventos", "A"),
        ("1.2.01.90", "1.2.01", "1.2.01.90", "Ikesaki", "S"),
        ("1.2.01.90.00.101", "1.2.01.90", "909990101", "Ikesaki Custos Indiretos 101", "A"),
        ("1.2.01.90.00.110", "1.2.01.90", "909990110", "Ikesaki Custos Indiretos 110", "A"),
        ("1.3", "1", "1.3", "ATACADO", "S"),
        ("1.3.01", "1.3", "1.3.01", "EBC Cosméticos", "S"),
        ("1.3.01.20", "1.3.01", "1.3.01.20", "Lojas", "S"),
        ("1.3.01.20.00.201", "1.3.01.20", "209920201", "Loja Varejo", "A"),
        ("1.3.01.20.00.211", "1.3.01.20", "209920211", "Loja Atacado", "A"),
        ("1.3.01.30", "1.3.01", "1.3.01.30", "Televendas", "S"),
        ("1.3.01.30.00.201", "1.3.01.30", "309930201", "Televendas", "A"),
        ("1.3.01.40", "1.3.01", "1.3.01.40", "Vendas Externas", "S"),
        ("1.3.01.40.00.200", "1.3.01.40", "409940200", "Vendas Externas * Amazon", "A"),
        ("1.3.01.40.00.201", "1.3.01.40", "409940201", "Vendas Externas * PE", "A"),
        ("1.3.01.40.00.208", "1.3.01.40", "409940208", "Vendas Externas * ATAC", "A"),
        ("1.3.01.50", "1.3.01", "1.3.01.50", "Ecommerce", "S"),
        ("1.3.01.50.00.201", "1.3.01.50", "509950201", "Ecommerce", "A"),
        ("1.3.01.60", "1.3.01", "1.3.01.60", "Feiras e Eventos", "S"),
        ("1.3.01.60.00.201", "1.3.01.60", "609960201", "Feiras e Eventos", "A"),
        ("1.3.01.90", "1.3.01", "1.3.01.90", "EBC", "S"),
        ("1.3.01.90.00.201", "1.3.01.90", "909990201", "EBC Custos Indiretos", "A"),
        ("1.4", "1", "1.4", "INDÚSTRIA", "S"),
        ("1.4.01", "1.4", "1.4.01", "Taiff", "S"),
        ("1.4.01.10", "1.4.01", "1.4.01.10", "Action Varginha", "S"),
        ("1.4.01.10.001", "1.4.01.10", "0402", "Mercado Interno * VGA", "A"),
        ("1.4.01.10.002", "1.4.01.10", "20402", "Mercado Externo", "A"),
        ("1.4.01.20", "1.4.01", "1.4.01.20", "Taiff São Paulo", "S"),
        ("1.4.01.20.001", "1.4.01.20", "0301", "Mercado Interno * SP", "A"),
        ("1.4.01.20.003", "1.4.01.20", "30301", "Assistência Técnica", "A"),
        ("1.4.01.30", "1.4.01", "1.4.01.30", "Taiff Extrema", "S"),
        ("1.4.01.30.001", "1.4.01.30", "0302", "Mercado Interno _ EXTREMA", "A"),
        ("1.4.01.30.004", "1.4.01.30", "40302", "Ecommerce", "A"),
        ("1.4.02", "1.4", "1.4.02", "Action Motors", "S"),
        ("1.4.02.10.401", "1.4.02", "0401", "Action Motors", "A"),
        ("1.5", "1", "1.5", "SERVIÇOS", "S"),
        ("1.5.01", "1.5", "1.5.01", "Beauty Fair", "S"),
        ("1.5.01.01", "1.5.01", "0105", "Feira BF", "A"),
        ("1.5.01.02", "1.5.01", "0205", "Feiras Regionais", "A"),
        ("1.5.01.03", "1.5.01", "0305", "Eventos Nicho Profissional", "A"),
        ("1.5.01.04", "1.5.01", "0405", "Eventos Internacionais", "A"),
        ("1.5.01.05", "1.5.01", "0505", "Dados e Conteúdo", "A"),
        ("1.5.01.06", "1.5.01", "0605", "Eventos Varejo", "A"),
    ]
    
    print("=== IMPORTAÇÃO COMPLETA - 82 UNIDADES IKESAKI ===\n")
    print(f"Dados para importar: {len(unidades_dados)} unidades")
    
    # Verificar se quer limpar
    limpar = input("Limpar todas as unidades existentes? (s/N): ")
    if limpar.lower() == 's':
        Unidade.objects.all().delete()
        print("✓ Base de unidades limpa")
    
    print(f"\nIniciando importação...")
    
    criadas = 0
    atualizadas = 0
    erros = []
    
    # Importar em ordem para garantir hierarquia
    for codigo, codigo_pai_str, codigo_allstrategy, nome, tipo in unidades_dados:
        try:
            # Ajustar código pai para evitar auto-referência
            codigo_pai_real = None
            if codigo_pai_str and codigo_pai_str != codigo:
                try:
                    codigo_pai_real = Unidade.objects.get(codigo=codigo_pai_str)
                except Unidade.DoesNotExist:
                    # Se pai não existe ainda, deixar None
                    pass
            
            # Criar ou atualizar
            unidade, criada = Unidade.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'codigo_allstrategy': codigo_allstrategy,
                    'nome': nome,
                    'tipo': tipo,
                    'unidade_pai': codigo_pai_real,
                    'nivel': codigo.count('.') + 1,
                    'ativa': True,
                    'sincronizado_allstrategy': True
                }
            )
            
            if criada:
                criadas += 1
                print(f"✓ {codigo} - {nome} ({tipo})")
            else:
                # Atualizar dados
                unidade.codigo_allstrategy = codigo_allstrategy
                unidade.nome = nome
                unidade.tipo = tipo
                unidade.unidade_pai = codigo_pai_real
                unidade.nivel = codigo.count('.') + 1
                unidade.save()
                atualizadas += 1
                print(f"↻ {codigo} - {nome} ({tipo})")
                
        except Exception as e:
            erro = f"Erro em {codigo}: {str(e)}"
            erros.append(erro)
            print(f"❌ {erro}")
    
    # Segunda passada para ajustar pais que não existiam
    print(f"\nSegunda passada para ajustar hierarquia...")
    ajustados = 0
    
    for codigo, codigo_pai_str, _, _, _ in unidades_dados:
        if codigo_pai_str and codigo_pai_str != codigo:
            try:
                unidade = Unidade.objects.get(codigo=codigo)
                if not unidade.unidade_pai:  # Se não tem pai definido
                    pai = Unidade.objects.get(codigo=codigo_pai_str)
                    unidade.unidade_pai = pai
                    unidade.save()
                    ajustados += 1
                    print(f"🔗 Ajustado pai de {codigo}")
            except:
                pass
    
    # Estatísticas finais
    total_final = Unidade.objects.count()
    
    print(f"\n=== RESULTADO FINAL ===")
    print(f"Criadas: {criadas}")
    print(f"Atualizadas: {atualizadas}")
    print(f"Pais ajustados: {ajustados}")
    print(f"Erros: {len(erros)}")
    print(f"Total na base: {total_final}")
    
    if erros:
        print(f"\nErros encontrados:")
        for erro in erros:
            print(f"  - {erro}")
    
    # Verificação por tipo e nível
    print(f"\nVerificação:")
    print(f"Sintéticas: {Unidade.objects.filter(tipo='S').count()}")
    print(f"Analíticas: {Unidade.objects.filter(tipo='A').count()}")
    
    for nivel in range(1, 7):
        count = Unidade.objects.filter(nivel=nivel).count()
        print(f"Nível {nivel}: {count} unidades")
    
    return total_final

if __name__ == '__main__':
    resultado = importar_todas_unidades()
    
    if resultado == 79:  # 79 = total esperado baseado nos dados
        print(f"\n🎉 SUCESSO! Todas as {resultado} unidades foram importadas!")
    else:
        print(f"\n⚠️  Resultado: {resultado} unidades. Esperado: 79")
    
    print(f"\nPara verificar: acesse http://localhost:8000/gestor/unidades/")