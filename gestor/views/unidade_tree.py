# gestor/views/unidade_tree.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from core.models import Unidade
from core.utils.tree_utils import TreeViewMixin  # ← Remove generic_tree_data_api daqui
import json

# Configuração específica para Unidades
UNIDADE_CONFIG = {
    'codigo_field': 'codigo',
    'nome_field': 'nome',
    'parent_field': 'unidade_pai',
    'active_field': 'ativa',
    'tipo_field': 'tipo',
    'descricao_field': 'descricao'
}

@login_required
def unidade_tree_view(request):
    """Visualização hierárquica de unidades organizacionais"""
    
    class UnidadeTreeView(TreeViewMixin):
        model = Unidade
        codigo_field = 'codigo'
        nome_field = 'nome'
        parent_field = 'unidade_pai'
        active_field = 'ativa'
        tipo_field = 'tipo'
        descricao_field = 'descricao'
    
    tree_view = UnidadeTreeView()
    tree_data = tree_view.build_tree_structure()
    stats = tree_view.calculate_tree_stats()
    
    context = {
        'tree_data_json': json.dumps(tree_data, ensure_ascii=False),
        'stats': stats,
        'entity_name': 'Unidades Organizacionais',
        'entity_singular': 'Unidade',
        'create_url': 'gestor:unidade_create',
        'list_url': 'gestor:unidade_list',
        'tree_url': 'gestor:unidade_tree',
        'update_url_base': '/gestor/unidades/',
        'breadcrumb': 'Unidades',
        'icon': 'fa-sitemap'
    }
    
    return render(request, 'gestor/generic_tree.html', context)

@login_required
def unidade_tree_data(request):
    """API para dados da árvore de unidades"""
    
    # Criar instância do mixin diretamente
    class UnidadeTreeView(TreeViewMixin):
        model = Unidade
        codigo_field = 'codigo'
        nome_field = 'nome'
        parent_field = 'unidade_pai'
        active_field = 'ativa'
        tipo_field = 'tipo'
        descricao_field = 'descricao'
    
    tree_view = UnidadeTreeView()
    
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