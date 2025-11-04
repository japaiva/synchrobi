#!/usr/bin/env python
"""
Script de teste para o sistema de sugestão de fornecedores

Uso:
    python test_sugestao_fornecedor.py

Ou com Django shell:
    python manage.py shell < test_sugestao_fornecedor.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synchrobi.settings')
django.setup()

from core.models import Fornecedor

def test_criacao_fornecedores():
    """Criar fornecedores de teste"""
    print("\n" + "="*60)
    print("TESTE 1: Criação de Fornecedores de Teste")
    print("="*60)

    fornecedores_teste = [
        {
            'codigo': 'BF001',
            'razao_social': 'BEAUTY FAIR',
            'cnpj_cpf': '12345678000190',
        },
        {
            'codigo': 'TAIF01',
            'razao_social': 'TAIFF INDUSTRIA E COMERCIO LTDA',
            'cnpj_cpf': '98765432000110',
        },
        {
            'codigo': 'CHOSI01',
            'razao_social': 'CHOSEI',
            'cnpj_cpf': '11223344000155',
        },
        {
            'codigo': 'ACT001',
            'razao_social': 'ACTION TECHNOLOGY',
            'cnpj_cpf': '55667788000199',
        },
        {
            'codigo': 'EBC001',
            'razao_social': 'EMPRESA BRASILEIRA DE COSMETICOS LTDA',
            'cnpj_cpf': '99887766000133',
        },
    ]

    criados = 0
    existentes = 0

    for dados in fornecedores_teste:
        if not Fornecedor.objects.filter(codigo=dados['codigo']).exists():
            Fornecedor.objects.create(**dados)
            print(f"✅ Criado: {dados['razao_social']}")
            criados += 1
        else:
            print(f"ℹ️  Já existe: {dados['razao_social']}")
            existentes += 1

    print(f"\n📊 Resumo: {criados} criados, {existentes} já existentes")


def test_busca_exata():
    """Teste de busca exata"""
    print("\n" + "="*60)
    print("TESTE 2: Busca Exata")
    print("="*60)

    testes = [
        'BEAUTY FAIR',
        'TAIFF INDUSTRIA E COMERCIO LTDA',
        'CHOSEI',
        'ACTION TECHNOLOGY',
    ]

    for nome in testes:
        resultado = Fornecedor.buscar_por_nome(nome)
        if resultado:
            print(f"✅ Encontrado: {nome} → {resultado.codigo}")
        else:
            print(f"❌ Não encontrado: {nome}")


def test_busca_similar():
    """Teste de busca por similaridade"""
    print("\n" + "="*60)
    print("TESTE 3: Busca por Similaridade (Fuzzy Matching)")
    print("="*60)

    testes = [
        ('BEAUTY FAIR EVENTOS LTDA', 0.60),
        ('TAIFF COMERCIO', 0.60),
        ('CHOSEI BRASIL', 0.60),
        ('ACTION TECHNOLOGY SISTEMAS', 0.60),
        ('EMPRESA BRASILEIRA COSMETICOS', 0.60),
        ('BEAUTY FAIR INTERNACIONAL', 0.60),
    ]

    for nome, min_score in testes:
        print(f"\n🔍 Buscando: '{nome}' (score mín: {min_score*100}%)")

        resultados = Fornecedor.buscar_similares(
            nome=nome,
            min_score=min_score,
            apenas_ativos=True,
            limit=5
        )

        if resultados:
            print(f"   Encontrados: {len(resultados)}")
            for fornecedor, score in resultados:
                barra = "█" * int(score * 20)  # Barra visual
                print(f"   [{score*100:5.1f}%] {barra:20s} {fornecedor.razao_social}")
        else:
            print("   ❌ Nenhum resultado encontrado")


def test_diferentes_scores():
    """Teste com diferentes scores mínimos"""
    print("\n" + "="*60)
    print("TESTE 4: Diferentes Scores Mínimos")
    print("="*60)

    nome_teste = 'BEAUTY FAIR EVENTOS LTDA'
    scores = [0.50, 0.60, 0.70, 0.80, 0.90]

    print(f"Buscando: '{nome_teste}'")
    print()

    for min_score in scores:
        resultados = Fornecedor.buscar_similares(nome_teste, min_score=min_score)
        print(f"Score ≥ {min_score*100:3.0f}%: {len(resultados)} resultado(s)")

        for fornecedor, score in resultados:
            print(f"  → {fornecedor.razao_social} ({score*100:.1f}%)")


def test_extractor_service():
    """Teste do FornecedorExtractorService"""
    print("\n" + "="*60)
    print("TESTE 5: FornecedorExtractorService")
    print("="*60)

    from gestor.services.fornecedor_extractor_service import FornecedorExtractorService

    historicos_teste = [
        "ALUGUEL - 123456 BEAUTY FAIR EVENTOS LTDA - 2024/07",
        "PAGAMENTO - 789012 TAIFF COMERCIO E INDUSTRIA LTDA - NF 12345",
        "SERVICOS - 456789 CHOSEI BRASIL LIMITADA - MANUTENCAO",
        "COMPRA - 111222 ACTION TECHNOLOGY SISTEMAS LTDA - SOFTWARE",
    ]

    for historico in historicos_teste:
        print(f"\n📝 Histórico: {historico}")

        # Extrair fornecedor
        fornecedor_extraido = FornecedorExtractorService.extrair_fornecedor(historico)

        if fornecedor_extraido:
            print(f"   ✅ Extraído: {fornecedor_extraido.nome}")
            print(f"   📊 Confiança: {fornecedor_extraido.confianca*100:.0f}%")
            print(f"   🏷️  Padrão: {fornecedor_extraido.padrao_usado}")

            # Buscar ou sugerir
            resultado = FornecedorExtractorService.buscar_ou_sugerir_fornecedor(
                fornecedor_extraido,
                historico_original=historico,
                min_score=0.60
            )

            if resultado['encontrado']:
                print(f"   ✅ MATCH EXATO: {resultado['fornecedor'].razao_social}")
            else:
                print(f"   💡 Sugestões ({len(resultado['sugestoes'])}):")
                for fornecedor, score in resultado['sugestoes']:
                    print(f"      - {fornecedor.razao_social} ({score*100:.1f}%)")
        else:
            print("   ❌ Não foi possível extrair fornecedor")


def test_casos_especiais():
    """Teste de casos especiais"""
    print("\n" + "="*60)
    print("TESTE 6: Casos Especiais")
    print("="*60)

    casos = [
        ('B', "Nome muito curto (1 caractere)"),
        ('BE', "Nome muito curto (2 caracteres)"),
        ('FORNECEDOR INEXISTENTE XYZ LTDA', "Fornecedor que não existe"),
        ('BEAUTY', "Parte do nome"),
        ('beauty fair', "Minúsculas (deve converter)"),
        ('  BEAUTY FAIR  ', "Com espaços extras"),
    ]

    for nome, descricao in casos:
        print(f"\n🧪 Teste: {descricao}")
        print(f"   Nome: '{nome}'")

        resultados = Fornecedor.buscar_similares(nome, min_score=0.60)

        if resultados:
            print(f"   ✅ Encontrados: {len(resultados)}")
            for fornecedor, score in resultados[:2]:  # Mostrar só 2 primeiros
                print(f"      - {fornecedor.razao_social} ({score*100:.1f}%)")
        else:
            print("   ℹ️  Nenhum resultado")


def test_performance():
    """Teste de performance"""
    print("\n" + "="*60)
    print("TESTE 7: Performance")
    print("="*60)

    import time

    nome_teste = 'BEAUTY FAIR EVENTOS LTDA'
    repeticoes = 10

    print(f"Executando busca {repeticoes}x para '{nome_teste}'...")

    inicio = time.time()
    for _ in range(repeticoes):
        Fornecedor.buscar_similares(nome_teste, min_score=0.60)
    fim = time.time()

    tempo_total = fim - inicio
    tempo_medio = tempo_total / repeticoes

    print(f"\n⏱️  Tempo total: {tempo_total:.3f}s")
    print(f"⏱️  Tempo médio: {tempo_medio:.3f}s")
    print(f"⏱️  Buscas/segundo: {1/tempo_medio:.1f}")


def executar_todos_testes():
    """Executar todos os testes"""
    print("\n" + "="*60)
    print("🧪 SISTEMA DE SUGESTÃO DE FORNECEDORES - TESTES")
    print("="*60)

    try:
        # 1. Criar fornecedores de teste
        test_criacao_fornecedores()

        # 2. Teste de busca exata
        test_busca_exata()

        # 3. Teste de busca similar
        test_busca_similar()

        # 4. Teste com diferentes scores
        test_diferentes_scores()

        # 5. Teste do extractor service
        test_extractor_service()

        # 6. Casos especiais
        test_casos_especiais()

        # 7. Performance
        test_performance()

        print("\n" + "="*60)
        print("✅ TODOS OS TESTES CONCLUÍDOS!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    executar_todos_testes()
