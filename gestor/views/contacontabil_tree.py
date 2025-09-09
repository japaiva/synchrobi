# gestor/views/contacontabil_tree.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from core.models import ContaContabil
from core.utils.tree_utils import TreeViewMixin
import json

@login_required
def contacontabil_tree_view(request):
    """Visualização hierárquica de contas contábeis"""
    
    class ContaContabilTreeView(TreeViewMixin):
        model = ContaContabil
        codigo_field = 'codigo'
        nome_field = 'nome'
        parent_field = 'conta_pai'
        active_field = 'ativa'
        tipo_field = 'tipo'
        descricao_field = 'descricao'
    
    tree_view = ContaContabilTreeView()
    tree_data = tree_view.build_tree_structure()
    stats = tree_view.calculate_tree_stats()
    
    context = {
        'tree_data_json': json.dumps(tree_data, ensure_ascii=False),
        'stats': stats,
        'entity_name': 'Contas Contábeis',
        'entity_singular': 'Conta Contábil',
        'create_url': 'gestor:contacontabil_create',
        'list_url': 'gestor:contacontabil_list',
        'tree_url': 'gestor:contacontabil_tree',
        'update_url_base': '/gestor/contas-contabeis/',
        'breadcrumb': 'Contas Contábeis',
        'icon': 'fa-calculator'
    }
    
    return render(request, 'gestor/generic_tree.html', context)

@login_required
def contacontabil_tree_data(request):
    """API para dados da árvore de contas contábeis"""
    
    class ContaContabilTreeView(TreeViewMixin):
        model = ContaContabil
        codigo_field = 'codigo'
        nome_field = 'nome'
        parent_field = 'conta_pai'
        active_field = 'ativa'
        tipo_field = 'tipo'
        descricao_field = 'descricao'
    
    tree_view = ContaContabilTreeView()
    
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