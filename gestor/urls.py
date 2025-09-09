# gestor/urls.py - URLs atualizadas para nova arquitetura de unidades

from django.urls import path
from . import views

app_name = 'gestor'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('home/', views.home, name='home'),
    
    # Empresas
    path('empresas/', views.empresa_list, name='empresa_list'),
    path('empresas/criar/', views.empresa_create, name='empresa_create'),
    path('empresas/<str:sigla>/editar/', views.empresa_update, name='empresa_update'),
    path('empresas/<str:sigla>/excluir/', views.empresa_delete, name='empresa_delete'),
    
    # APIs para Empresas
    path('api/validar-sigla-empresa/', views.api_validar_sigla_empresa, name='api_validar_sigla_empresa'),
    path('api/validar-cnpj-empresa/', views.api_validar_cnpj_empresa, name='api_validar_cnpj_empresa'),
    path('api/empresa/<str:sigla>/info/', views.api_empresa_info, name='api_empresa_info'),

    # Centros de Custo das Empresas
    path('empresa-centros-custo/', views.empresa_centro_custo_list, name='empresa_centro_custo_list'),
    path('empresas/<str:sigla_empresa>/centros-custo/', views.empresa_centro_custo_list, name='empresa_centro_custo_list'),
    path('empresa-centros-custo/novo/', views.empresa_centro_custo_create, name='empresa_centro_custo_create'),
    path('empresas/<str:sigla_empresa>/centros-custo/novo/', views.empresa_centro_custo_create, name='empresa_centro_custo_create'),
    path('empresa-centros-custo/<int:pk>/editar/', views.empresa_centro_custo_update, name='empresa_centro_custo_update'),
    path('empresa-centros-custo/<int:pk>/excluir/', views.empresa_centro_custo_delete, name='empresa_centro_custo_delete'),
    
    # APIs para Centros de Custo das Empresas
    path('api/empresas/<str:sigla_empresa>/centros-custo/', views.api_empresa_centros_custo, name='api_empresa_centros_custo'),
    path('api/centros-custo/<str:codigo_centro>/empresas/', views.api_centro_custo_empresas, name='api_centro_custo_empresas'),

    # ===== UNIDADES - NOVA ARQUITETURA FOCADA NA ÁRVORE =====
    
    # View principal (árvore hierárquica)
    path('unidades/', views.unidade_tree_view, name='unidade_tree'),
    
    # Views modais para CRUD
    path('unidades/criar/', views.unidade_create_modal, name='unidade_create_modal'),
    path('unidades/<int:pk>/editar/', views.unidade_update_modal, name='unidade_update_modal'), 
    path('unidades/<int:pk>/detalhes/', views.unidade_detail_modal, name='unidade_detail_modal'),
    path('unidades/<int:pk>/excluir/', views.unidade_delete_ajax, name='unidade_delete_ajax'),
    
    # APIs básicas para unidades
    path('api/unidades/tree-data/', views.api_unidade_tree_data, name='api_unidade_tree_data'),
    path('api/unidades/validar-codigo/', views.api_validar_codigo, name='api_validar_codigo'),
    
    # APIs avançadas da árvore
    path('api/unidades/tree-data-advanced/', views.unidade_tree_data, name='unidade_tree_data_advanced'),
    path('api/unidades/search/', views.unidade_tree_search, name='unidade_tree_search'),
    path('api/unidades/export/', views.unidade_tree_export, name='unidade_tree_export'),
    
    # ===== CENTROS DE CUSTO =====
    path('centros-custo/', views.centrocusto_list, name='centrocusto_list'),
    path('centros-custo/criar/', views.centrocusto_create, name='centrocusto_create'),
    path('centros-custo/<str:codigo>/editar/', views.centrocusto_update, name='centrocusto_update'),
    path('centros-custo/<str:codigo>/excluir/', views.centrocusto_delete, name='centrocusto_delete'),
    
    # APIs para Centros de Custo
    path('api/validar-codigo-centrocusto/', views.api_validar_codigo_centrocusto, name='api_validar_codigo_centrocusto'),
    
    # ===== CONTAS CONTÁBEIS =====
    path('contas-contabeis/', views.contacontabil_list, name='contacontabil_list'),
    path('contas-contabeis/criar/', views.contacontabil_create, name='contacontabil_create'),
    path('contas-contabeis/<str:codigo>/editar/', views.contacontabil_update, name='contacontabil_update'),
    path('contas-contabeis/<str:codigo>/excluir/', views.contacontabil_delete, name='contacontabil_delete'),
    
    # APIs para Contas Contábeis
    path('api/validar-codigo-contacontabil/', views.api_validar_codigo_contacontabil, name='api_validar_codigo_contacontabil'),
    
    # ===== USUÁRIOS =====
    path('usuarios/', views.usuario_list, name='usuario_list'),
    path('usuarios/criar/', views.usuario_create, name='usuario_create'),
    path('usuarios/<int:pk>/editar/', views.usuario_update, name='usuario_update'),
    path('usuarios/<int:pk>/excluir/', views.usuario_delete, name='usuario_delete'),
    
    # ===== PARÂMETROS =====
    path('parametros/', views.parametro_list, name='parametro_list'),
    path('parametros/criar/', views.parametro_create, name='parametro_create'),
    path('parametros/<str:codigo>/', views.parametro_detail, name='parametro_detail'),
    path('parametros/<str:codigo>/editar/', views.parametro_update, name='parametro_update'),
    path('parametros/<str:codigo>/excluir/', views.parametro_delete, name='parametro_delete'),
    
    # APIs gerais
    path('api/parametro/<str:codigo>/valor/', views.api_parametro_valor, name='api_parametro_valor'),
]

# ===== URLS REMOVIDAS DA ARQUITETURA ANTIGA =====
#
# As seguintes URLs foram removidas pois não existem mais na nova arquitetura:
#
# REMOVIDAS:
# - path('unidades/arvore/', ...) → agora é a URL principal 'unidades/'
# - path('unidades/lista/', ...) → substituída pela árvore
# - path('unidades/<int:pk>/', ...) → substituída por modal de detalhes
# - path('unidades/criar/', ...) → agora é modal (unidade_create_modal)
# - path('unidades/<int:pk>/editar/', ...) → agora é modal (unidade_update_modal)
# - path('unidades/<int:pk>/excluir/', ...) → agora é AJAX (unidade_delete_ajax)
# - path('api/unidade/<int:pk>/filhas/', ...) → substituída por tree-data APIs
#
# MUDANÇAS PRINCIPAIS:
# 1. 'unidades/' agora aponta direto para a árvore (unidade_tree_view)
# 2. URLs modais têm nomes específicos (_modal, _ajax)
# 3. APIs organizadas entre básicas e avançadas
# 4. Fallbacks removidos pois interface é centrada na árvore
# 5. URLs mais RESTful e organizadas por funcionalidade