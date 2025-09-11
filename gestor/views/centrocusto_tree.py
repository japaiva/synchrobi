# gestor/views/centrocusto_tree.py - ATUALIZADO PARA HIERARQUIA DECLARADA
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from core.models import CentroCusto
import json

@login_required
def centrocusto_tree_view(request):
    """Visualização hierárquica de centros de custo com hierarquia declarada"""
    
    try:
        # Usar método nativo do modelo que já suporta hierarquia declarada
        centros_queryset = CentroCusto.objects.filter(ativo=True).order_by('codigo')
        
        # Construir árvore usando hierarquia declarada
        tree_data = construir_arvore_declarada(centros_queryset)
        
        # Calcular estatísticas
        stats = calcular_stats_centros(centros_queryset)
        
        context = {
            'tree_data_json': json.dumps(tree_data, ensure_ascii=False, indent=2),
            'stats': stats,
            'entity_name': 'Centros de Custo',
            'entity_singular': 'Centro de Custo',
            'create_url': 'gestor:centrocusto_create_modal',
            'update_url_base': '/gestor/centros-custo/',
            'tree_url': 'gestor:centrocusto_tree',
            'api_tree_data_url': 'gestor:centrocusto_tree_data',
            'breadcrumb': 'Centros de Custo',
            'icon': 'fa-bullseye'
        }
        
        return render(request, 'gestor/centrocusto_tree_main.html', context)
        
    except Exception as e:
        import logging
        logger = logging.getLogger('synchrobi')
        logger.error(f'Erro na árvore de centros de custo: {str(e)}')
        
        # Fallback
        context = {
            'tree_data_json': '[]',
            'stats': {'total': 0, 'tipo_s': 0, 'tipo_a': 0},
            'error_message': 'Erro ao carregar árvore',
            'entity_name': 'Centros de Custo',
            'entity_singular': 'Centro de Custo',
            'create_url': 'gestor:centrocusto_create_modal',
            'update_url_base': '/gestor/centros-custo/',
        }
        return render(request, 'gestor/centrocusto_tree_main.html', context)

@login_required
def centrocusto_tree_data(request):
    """API para dados da árvore - HIERARQUIA DECLARADA"""
    
    try:
        # Obter filtros
        search = request.GET.get('search', '').strip()
        nivel = request.GET.get('nivel', '')
        tipo = request.GET.get('tipo', '')
        ativo = request.GET.get('ativo', '')
        
        # Query base
        queryset = CentroCusto.objects.order_by('codigo')
        
        # Aplicar filtros
        if ativo != '':
            queryset = queryset.filter(ativo=ativo.lower() == 'true')
        else:
            queryset = queryset.filter(ativo=True)
        
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
        
        # Calcular stats
        stats = calcular_stats_centros(queryset)
        stats['filtros_aplicados'] = {
            'search': search,
            'nivel': nivel,
            'tipo': tipo,
            'ativo': ativo
        }
        
        return JsonResponse({
            'success': True,
            'tree_data': tree_data,
            'stats': stats,
            'total_sem_filtro': CentroCusto.objects.filter(ativo=True).count()
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger('synchrobi')
        logger.error(f'Erro na API de dados da árvore: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro interno do servidor',
            'message': str(e)
        })

def construir_arvore_declarada(queryset):
    """Constrói árvore hierárquica usando campo codigo_pai"""
    
    # Converter para lista
    centros_list = list(queryset)
    
    # Mapear centros por código
    centros_dict = {centro.codigo: centro for centro in centros_list}
    
    # Mapear filhos por pai
    filhos_por_pai = {}
    centros_raiz = []
    
    for centro in centros_list:
        if centro.codigo_pai:
            # Tem pai - adicionar à lista de filhos do pai
            if centro.codigo_pai not in filhos_por_pai:
                filhos_por_pai[centro.codigo_pai] = []
            filhos_por_pai[centro.codigo_pai].append(centro)
        else:
            # É raiz
            centros_raiz.append(centro)
    
    def construir_no(centro):
        """Constrói um nó da árvore recursivamente"""
        filhos = filhos_por_pai.get(centro.codigo, [])
        filhos_ordenados = sorted(filhos, key=lambda x: x.codigo)
        
        return {
            'codigo': centro.codigo,
            'nome': centro.nome,
            'tipo': centro.tipo,
            'nivel': centro.nivel,
            'ativo': centro.ativo,
            'descricao': centro.descricao,
            'codigo_pai': centro.codigo_pai or '',
            'tem_filhos': len(filhos) > 0,
            'data_criacao': centro.data_criacao.isoformat() if centro.data_criacao else None,
            'data_alteracao': centro.data_alteracao.isoformat() if centro.data_alteracao else None,
            'filhos': [construir_no(filho) for filho in filhos_ordenados]
        }
    
    # Construir árvore a partir das raízes
    centros_raiz_ordenados = sorted(centros_raiz, key=lambda x: x.codigo)
    return [construir_no(raiz) for raiz in centros_raiz_ordenados]

def calcular_stats_centros(queryset):
    """Calcula estatísticas dos centros de custo"""
    centros_list = list(queryset)
    total = len(centros_list)
    
    if total == 0:
        return {
            'total': 0,
            'tipo_s': 0,
            'tipo_a': 0,
            'nivel_max': 0,
            'contas_por_nivel': {}
        }
    
    # Contadores
    tipo_s = sum(1 for c in centros_list if c.tipo == 'S')
    tipo_a = sum(1 for c in centros_list if c.tipo == 'A')
    
    # Níveis
    niveis = [c.nivel for c in centros_list]
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