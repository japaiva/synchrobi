# gestor/views/centrocusto_tree.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from core.models import CentroCusto
from core.utils.tree_utils import TreeViewMixin
import json

@login_required
def centrocusto_tree_view(request):
    """Visualização hierárquica de centros de custo"""
    
    class CentroCustoTreeView(TreeViewMixin):
        model = CentroCusto
        codigo_field = 'codigo'
        nome_field = 'nome'
        parent_field = 'centro_pai'
        active_field = 'ativo'
        tipo_field = 'tipo'
        descricao_field = 'descricao'
    
    tree_view = CentroCustoTreeView()
    tree_data = tree_view.build_tree_structure()
    stats = tree_view.calculate_tree_stats()
    
    context = {
        'tree_data_json': json.dumps(tree_data, ensure_ascii=False),
        'stats': stats,
        'entity_name': 'Centros de Custo',
        'entity_singular': 'Centro de Custo',
        'create_url': 'gestor:centrocusto_create',
        'list_url': 'gestor:centrocusto_list',
        'tree_url': 'gestor:centrocusto_tree',
        'update_url_base': '/gestor/centros-custo/',
        'breadcrumb': 'Centros de Custo',
        'icon': 'fa-bullseye'
    }
    
    return render(request, 'gestor/generic_tree.html', context)

@login_required
def centrocusto_tree_data(request):
    """API para dados da árvore de centros de custo"""
    
    class CentroCustoTreeView(TreeViewMixin):
        model = CentroCusto
        codigo_field = 'codigo'
        nome_field = 'nome'
        parent_field = 'centro_pai'
        active_field = 'ativo'
        tipo_field = 'tipo'
        descricao_field = 'descricao'
    
    tree_view = CentroCustoTreeView()
    
    # Obter filtros
    search = request.GET.get('search', '').strip()
    nivel = request.GET.get('nivel', '')
    tipo = request.GET.get('tipo', '')
    
    # Aplicar filtros
    queryset = tree_view.get_tree_queryset()
    queryset = tree_view.apply_filters(queryset, search, nivel, tipo)
    
    # Construir árvore
    tree_data = tree_view.build_tree_structure(queryset)
    stats = tree_view.calculate_tree_stats(queryset)
    
    return JsonResponse({
        'tree_data': tree_data,
        'stats': stats,
        'success': True
    })