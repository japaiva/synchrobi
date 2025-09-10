#!/usr/bin/env python
"""
Script para limpeza e importação específica das contas contábeis do grupo 130
Execute: python script_limpeza_grupo_130.py
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

from core.models import ContaContabil

def main():
    """Função principal de limpeza e reimportação"""
    
    print("=== LIMPEZA E IMPORTAÇÃO GRUPO 130 ===\n")
    
    # 1. LIMPEZA TOTAL
    print("1. Limpando todas as contas contábeis existentes...")
    contas_deletadas = ContaContabil.objects.count()
    ContaContabil.objects.all().delete()
    print(f"   ✅ {contas_deletadas} contas removidas\n")
    
    # 2. ESTRUTURA HIERÁRQUICA DO GRUPO 130
    # Baseado na análise da planilha, essas são as contas necessárias
    contas_grupo_130 = [
        # Nível 1 - Raiz
        ("130", "Grupo 130"),
        
        # Nível 2 - Grandes grupos
        ("130.010", "Despesas com Pessoal"),
        ("130.020", "Despesas Prediais"),
        ("130.030", "Despesas com Tecnologia"),
        ("130.040", "Despesas Administrativas"),
        ("130.050", "Reversões e Ajustes"),
        ("130.060", "Serviços Especializados"),
        ("130.080", "Despesas Corporativas"),
        ("130.085", "Ajuste de Redução de Despesas"),
        ("130.090", "Depreciação e Amortização"),
        
        # Nível 3 - Subgrupos de Pessoal
        ("130.010.01", "Folha de Pagamento"),
        ("130.010.02", "Encargos Sociais"),
        ("130.010.03", "Benefícios"),
        ("130.010.04", "Outras Despesas com Pessoal"),
        
        # Nível 3 - Subgrupos Prediais
        ("130.020.01", "Ocupação"),
        ("130.020.02", "IPTU"),
        ("130.020.03", "Utilidades"),
        ("130.020.04", "Serviços Prediais"),
        ("130.020.05", "Outras Despesas Prediais"),
        
        # Nível 3 - Subgrupos Administrativos
        ("130.040.01", "Materiais"),
        ("130.040.02", "Questões Legais"),
        ("130.040.03", "Veículos"),
        ("130.040.04", "Diversas Administrativas"),
        ("130.040.05", "Tributos"),
        
        # Nível 3 - Serviços Especializados
        ("130.060.01", "Prestadores de Serviços"),
        ("130.060.02", "Equipamentos"),
        ("130.060.03", "Desenvolvimento de Produtos"),
        
        # Nível 4 - Detalhes Folha de Pagamento
        ("130.010.01.01", "Salários"),
        ("130.010.01.02", "Décimo Terceiro, Férias"),
        ("130.010.01.03", "Adicionais"),
        ("130.010.01.04", "Premiações"),
        ("130.010.01.05", "Rescisões"),
        
        # Nível 4 - Detalhes Encargos
        ("130.010.02.01", "Encargos"),
        
        # Nível 4 - Detalhes Benefícios
        ("130.010.03.01", "Assistência Médica"),
        ("130.010.03.02", "Vale Refeição"),
        ("130.010.03.03", "Vale Transporte"),
        ("130.010.03.04", "Cestas Básica e de Natal"),
        ("130.010.03.05", "Seguro de Vida"),
        
        # Nível 4 - Outras Despesas Pessoal
        ("130.010.04.01", "Contrato de Estagiários"),
        ("130.010.04.02", "Desp c/ Endomarketing"),
        ("130.010.04.03", "Desp c/ Jovem Aprendiz / PCD"),
        ("130.010.04.04", "Desp Diversas c/ Pessoal"),
        ("130.010.04.05", "Serviços de Recrutamento e Seleção"),
        ("130.010.04.06", "Serviços Segurança do Trabalho"),
        ("130.010.04.07", "Sindicatos"),
        ("130.010.04.08", "Treinamentos e Formação de Pessoal"),
        ("130.010.04.09", "Uniforme e EPI"),
        
        # Nível 4 - Detalhes Prediais
        ("130.020.01.01", "Aluguel"),
        ("130.020.01.02", "Condomínio e Outros"),
        ("130.020.01.03", "Crédito de PIS/COFINS s/ Aluguel"),
        ("130.020.01.04", "Aluguel Complementar"),
        
        ("130.020.03.01", "Água e Esgoto"),
        ("130.020.03.02", "Energia Elétrica"),
        ("130.020.03.03", "Internet"),
        ("130.020.03.04", "Telefone Fixo"),
        ("130.020.03.05", "Telefone Móvel"),
        ("130.020.03.06", "Crédito de PIS/COFINS s/ Energia Elétrica"),
        
        ("130.020.04.01", "Serviços de Limpeza"),
        ("130.020.04.02", "Serviços de Segurança e Vigilância"),
        ("130.020.04.03", "Serviços de Conservação e Reparo"),
        ("130.020.04.04", "Serviços de Controle de Pragas"),
        ("130.020.04.05", "Serviços de Gerenciamento de Resíduos"),
        
        ("130.020.05.01", "Desp c/ Regularização das Instalações"),
        ("130.020.05.02", "Material de Conservação e Reparo"),
        ("130.020.05.03", "Seguro do Imóvel"),
        ("130.020.05.04", "Serviços de Engenharia e Arquitetura"),
        
        # Nível 3 e 4 - Tecnologia
        ("130.030.01", "Licenças de Software"),
        ("130.030.02", "Suporte e Serviços _ TI"),
        ("130.030.03", "CRM _ Tecnologia"),
        ("130.030.04", "Gestão Comercial _ Tecnologia"),
        
        # Nível 4 - Materiais Administrativos
        ("130.040.01.01", "Material de Copa e Refeitório"),
        ("130.040.01.02", "Material de Escritório"),
        ("130.040.01.03", "Material de Limpeza"),
        ("130.040.01.04", "Material de Logística"),
        ("130.040.01.05", "Material de Loja"),
        ("130.040.01.06", "Material de Prevenção de Perdas"),
        ("130.040.01.07", "Suprimentos de Informática"),
        ("130.040.01.08", "Bens de Pequeno Valor"),
        ("130.040.01.09", "Outros Materiais de Consumo"),
        
        # Nível 4 - Questões Legais
        ("130.040.02.01", "Processos Judiciais  (Trabal-Civel-Tribut)"),
        ("130.040.02.02", "Desp c/ Sinistros de Terceiros"),
        
        # Nível 4 - Veículos
        ("130.040.03.01", "Desp Diversas c/ Veículos"),
        ("130.040.03.02", "IPVA e Licenciamento"),
        ("130.040.03.03", "Seguros de Veículos"),
        
        # Nível 4 - Diversas Administrativas
        ("130.040.04.01", "Desp c/ Associações de Classe"),
        ("130.040.04.02", "Desp c/ Cartório e Cópias"),
        ("130.040.04.03", "Desp c/ Confraternizações"),
        ("130.040.04.04", "Desp c/ Correios"),
        ("130.040.04.05", "Desp c/ Deslocamento"),
        ("130.040.04.06", "Desp Diversas de Desembaraço"),
        ("130.040.04.07", "Refeições e Lanches _ Eventos & Extras"),
        ("130.040.04.08", "Serviços Gráficos _ ADM"),
        ("130.040.04.09", "Taxas Administrativas"),
        ("130.040.04.10", "Taxas Estaduais, Federais e Municipais"),
        ("130.040.04.11", "Outras Desp Administrativas"),
        
        # Nível 4 - Tributos
        ("130.040.05.01", "Imposto Complementar"),
        
        # Nível 3 - Reversões e Ajustes
        ("130.050.01", "Rescisões Comerciais (reutilizar)"),
        ("130.050.02", "Reversão Premiação"),
        ("130.050.03", "Reversão Rescisões Comerciais"),
        ("130.050.04", "Ajuste Linha Vendas"),
        ("130.050.05", "Ajuste Linha Logística"),
        ("130.050.06", "Ajuste Linha Marketing"),
        ("130.050.07", "Ajuste Linha Compras"),
        ("130.050.08", "Ajuste Linha Corporativo"),
        
        # Nível 4 - Prestadores de Serviços
        ("130.060.01.01", "Serv e Desp c/ Marcas e Patentes"),
        ("130.060.01.02", "Serviços Administrativos"),
        ("130.060.01.03", "Serviços Advocatícios"),
        ("130.060.01.04", "Serviços Área TI"),
        ("130.060.01.05", "Serviços Contábeis"),
        ("130.060.01.06", "Serviços de Auditoria"),
        ("130.060.01.07", "Serviços de Cobrança"),
        ("130.060.01.08", "Serviços de Consultoria"),
        ("130.060.01.09", "Serviços de Crédito e Cadastro"),
        ("130.060.01.10", "Serviços de Entrega e Coleta"),
        ("130.060.01.12", "Serviços de Gestão de Documentos"),
        ("130.060.01.13", "Serviços de Inventário"),
        ("130.060.01.14", "Serviços de Peritos"),
        ("130.060.01.15", "Serviços de Transportes de Valores"),
        ("130.060.01.16", "Serviços de Gestão Financeira"),
        ("130.060.01.17", "Outros Prestadores de Serviços Administrativos"),
        ("130.060.01.18", "Multas Contratuais"),
        ("130.060.01.19", "Rescisões de Prestadores de Serviços"),
        
        # Nível 4 - Equipamentos
        ("130.060.02.01", "Locação de Equipamentos"),
        ("130.060.02.02", "Manutenção de Equipamentos"),
        ("130.060.02.03", "Material p/ Manutenção de Equipamentos"),
        
        # Nível 4 - Desenvolvimento de Produtos
        ("130.060.03.01", "Desp c/ Compras de Amostras"),
        ("130.060.03.02", "Desp c/ Normas Técnicas"),
        ("130.060.03.03", "Protótipos"),
        ("130.060.03.04", "Serviços de Calibração"),
        ("130.060.03.05", "Serviços de Certificação"),
        ("130.060.03.06", "Serviços de Inspeção"),
        ("130.060.03.07", "Serviços de Desenhos Técnicos"),
        ("130.060.03.08", "Serviços de Engenharia"),
        ("130.060.03.09", "Serviços de Laboratório e Análises"),
        
        # Nível 3 - Depreciação
        ("130.090.01", "Depreciação e Amortização"),
        ("130.090.02", "Desp c/ Depreciação AAP"),
    ]
    
    print(f"2. Importando {len(contas_grupo_130)} contas do grupo 130...")
    
    sucessos = 0
    erros = 0
    
    # Importar em ordem hierárquica (pais primeiro)
    for codigo, nome in contas_grupo_130:
        try:
            # Determinar tipo baseado na estrutura
            # Se não tem filhos na lista, é analítico
            tem_filhos = any(c[0].startswith(codigo + '.') for c in contas_grupo_130)
            tipo = 'S' if tem_filhos else 'A'
            
            conta = ContaContabil.objects.create(
                codigo=codigo,
                nome=nome,
                tipo=tipo,
                ativa=True,
                descricao=f"Conta do grupo 130 - {nome}"
            )
            
            print(f"   ✅ {codigo} - {nome} ({tipo})")
            sucessos += 1
            
        except Exception as e:
            print(f"   ❌ Erro em {codigo}: {e}")
            erros += 1
    
    # 3. VERIFICAÇÃO FINAL
    print(f"\n=== RESULTADO ===")
    print(f"Sucessos: {sucessos}")
    print(f"Erros: {erros}")
    
    # Estatísticas
    total = ContaContabil.objects.count()
    sinteticos = ContaContabil.objects.filter(tipo='S').count()
    analiticos = ContaContabil.objects.filter(tipo='A').count()
    
    print(f"\n=== ESTATÍSTICAS FINAIS ===")
    print(f"Total no banco: {total}")
    print(f"Sintéticos: {sinteticos}")
    print(f"Analíticos: {analiticos}")
    
    # Verificar hierarquia
    print(f"\n=== VERIFICAÇÃO HIERÁRQUICA ===")
    niveis = {}
    for conta in ContaContabil.objects.all():
        nivel = conta.nivel
        if nivel not in niveis:
            niveis[nivel] = 0
        niveis[nivel] += 1
    
    for nivel in sorted(niveis.keys()):
        print(f"Nível {nivel}: {niveis[nivel]} conta(s)")
    
    print("\n✅ Limpeza e importação do grupo 130 concluída!")
    print("\nPróximos passos:")
    print("1. Criar tabela de mapeamento de códigos externos")
    print("2. Importar os códigos externos da planilha")
    print("3. Integrar na árvore hierárquica")

if __name__ == "__main__":
    main()