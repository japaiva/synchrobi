# gestor/views/contacontabil_tree.py - ATUALIZADO PARA HIERARQUIA DECLARADA
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from core.models import ContaContabil
import json
import logging

logger = logging.getLogger('synchrobi')

@login_required
def contacontabil_tree_view(request):
    """Visualização hierárquica de contas contábeis - HIERARQUIA DECLARADA"""
    
    try:
        # Query única otimizada
        contas_queryset = ContaContabil.objects.filter(ativa=True).order_by('codigo')
        
        # Construir árvore usando hierarquia declarada
        tree_data = construir_arvore_declarada(contas_queryset)
        
        # Calcular stats
        stats = calcular_stats_contas(contas_queryset)
        
        context = {
            'tree_data_json': json.dumps(tree_data, ensure_ascii=False, indent=2),
            'stats': stats,
            'entity_name': 'Contas Contábeis',
            'entity_singular': 'Conta Contábil',
            'create_url': 'gestor:contacontabil_create_modal',
            'update_url_base': '/gestor/contas-contabeis/',
            'tree_url': 'gestor:contacontabil_tree',
            'api_tree_data_url': 'gestor:contacontabil_tree_data',
            'breadcrumb': 'Contas Contábeis',
            'icon': 'fa-calculator'
        }
        
        return render(request, 'gestor/contacontabil_tree_main.html', context)
        
    except Exception as e:
        logger.error(f'Erro na construção da árvore de contas contábeis: {str(e)}')
        
        # Fallback simples
        context = {
            'tree_data_json': '[]',
            'stats': {'total': 0, 'tipo_s': 0, 'tipo_a': 0},
            'error_message': 'Erro ao carregar árvore de contas contábeis',
            'entity_name': 'Contas Contábeis',
            'entity_singular': 'Conta Contábil',
            'create_url': 'gestor:contacontabil_create_modal',
            'update_url_base': '/gestor/contas-contabeis/',
            'tree_url': 'gestor:contacontabil_tree',
            'api_tree_data_url': 'gestor:contacontabil_tree_data',
            'breadcrumb': 'Contas Contábeis',
            'icon': 'fa-calculator'
        }
        return render(request, 'gestor/contacontabil_tree_main.html', context)

@login_required
def contacontabil_tree_data(request):
    """API para dados da árvore - HIERARQUIA DECLARADA"""
    
    try:
        # Obter filtros
        search = request.GET.get('search', '').strip()
        nivel = request.GET.get('nivel', '')
        tipo = request.GET.get('tipo', '')
        ativa = request.GET.get('ativa', '')
        
        # Query com filtros
        queryset = ContaContabil.objects.order_by('codigo')
        
        if ativa != '':
            queryset = queryset.filter(ativa=ativa.lower() == 'true')
        else:
            queryset = queryset.filter(ativa=True)
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(nome__icontains=search) |
                Q(descricao__icontains=search)
            )
        
        if nivel:
            queryset = queryset.filter(nivel=int(nivel))
        
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        # Construir árvore
        tree_data = construir_arvore_declarada(queryset)
        
        # Stats
        stats = calcular_stats_contas(queryset)
        stats['filtros_aplicados'] = {
            'search': search,
            'nivel': nivel,
            'tipo': tipo,
            'ativa': ativa
        }
        
        return JsonResponse({
            'success': True,
            'tree_data': tree_data,
            'stats': stats,
            'total_sem_filtro': ContaContabil.objects.filter(ativa=True).count()
        })
        
    except Exception as e:
        logger.error(f'Erro na API de dados da árvore: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro interno do servidor',
            'message': str(e)
        })

def construir_arvore_declarada(queryset):
    """Constrói árvore hierárquica usando campo codigo_pai"""
    
    contas_list = list(queryset)
    contas_dict = {conta.codigo: conta for conta in contas_list}
    
    # Mapear filhos por pai
    filhos_por_pai = {}
    contas_raiz = []
    
    for conta in contas_list:
        if conta.codigo_pai:
            # Tem pai - adicionar à lista de filhos do pai
            if conta.codigo_pai not in filhos_por_pai:
                filhos_por_pai[conta.codigo_pai] = []
            filhos_por_pai[conta.codigo_pai].append(conta)
        else:
            # É raiz
            contas_raiz.append(conta)
    
    def construir_no(conta):
        """Constrói um nó da árvore recursivamente"""
        filhos = filhos_por_pai.get(conta.codigo, [])
        filhos_ordenados = sorted(filhos, key=lambda x: x.codigo)
        
        return {
            'codigo': conta.codigo,
            'nome': conta.nome,
            'tipo': conta.tipo,
            'nivel': conta.nivel,
            'ativa': conta.ativa,
            'descricao': conta.descricao,
            'codigo_pai': conta.codigo_pai or '',
            'tem_filhos': len(filhos) > 0,
            'data_criacao': conta.data_criacao.isoformat() if conta.data_criacao else None,
            'data_alteracao': conta.data_alteracao.isoformat() if conta.data_alteracao else None,
            'filhos': [construir_no(filho) for filho in filhos_ordenados]
        }
    
    # Construir árvore a partir das raízes
    contas_raiz_ordenadas = sorted(contas_raiz, key=lambda x: x.codigo)
    return [construir_no(raiz) for raiz in contas_raiz_ordenadas]

def calcular_stats_contas(queryset):
    """Calcula estatísticas das contas contábeis"""
    contas_list = list(queryset)
    total = len(contas_list)
    
    if total == 0:
        return {
            'total': 0,
            'tipo_s': 0,
            'tipo_a': 0,
            'nivel_max': 0,
            'contas_por_nivel': {}
        }
    
    # Contadores
    tipo_s = sum(1 for c in contas_list if c.tipo == 'S')
    tipo_a = sum(1 for c in contas_list if c.tipo == 'A')
    
    # Níveis
    niveis = [c.nivel for c in contas_list]
    nivel_max = max(niveis)
    nivel_min = min(niveis)
    
    # Contar por nível
    contas_por_nivel = {}
    for nivel in range(nivel_min, nivel_max + 1):
        count = sum(1 for n in niveis if n == nivel)
        contas_por_nivel[str(nivel)] = count
    
    return {
        'total': total,
        'tipo_s': tipo_s,
        'tipo_a': tipo_a,
        'nivel_max': nivel_max,
        'nivel_min': nivel_min,
        'contas_por_nivel': contas_por_nivel,
        'niveis_existentes': sorted(list(set(niveis)))
    }