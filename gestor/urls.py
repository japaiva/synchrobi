# gestor/urls.py - URLs atualizadas com Centro de Custo e Conta Contábil

from django.urls import path
from . import views
from .views.unidade_tree import unidade_tree_view, unidade_tree_data

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

    # NOVO: Centros de Custo das Empresas
    path('empresa-centros-custo/', views.empresa_centro_custo_list, name='empresa_centro_custo_list'),
    path('empresas/<str:sigla_empresa>/centros-custo/', views.empresa_centro_custo_list, name='empresa_centro_custo_list'),
    path('empresa-centros-custo/novo/', views.empresa_centro_custo_create, name='empresa_centro_custo_create'),
    path('empresas/<str:sigla_empresa>/centros-custo/novo/', views.empresa_centro_custo_create, name='empresa_centro_custo_create'),
    path('empresa-centros-custo/<int:pk>/editar/', views.empresa_centro_custo_update, name='empresa_centro_custo_update'),
    path('empresa-centros-custo/<int:pk>/excluir/', views.empresa_centro_custo_delete, name='empresa_centro_custo_delete'),
    
    # APIs para Centros de Custo das Empresas
    path('api/empresas/<str:sigla_empresa>/centros-custo/', views.api_empresa_centros_custo, name='api_empresa_centros_custo'),
    path('api/centros-custo/<str:codigo_centro>/empresas/', views.api_centro_custo_empresas, name='api_centro_custo_empresas'),

    # Unidades - Árvore Hierárquica (NOVO)
    path('unidades/arvore/', unidade_tree_view, name='unidade_tree'),
    path('api/unidades/tree-data/', unidade_tree_data, name='unidade_tree_data'),

    # Unidades - CRUD tradicional
    path('unidades/', views.unidade_list, name='unidade_list'),
    path('unidades/criar/', views.unidade_create, name='unidade_create'),
    path('unidades/<int:pk>/', views.unidade_detail, name='unidade_detail'),
    path('unidades/<int:pk>/editar/', views.unidade_update, name='unidade_update'),
    path('unidades/<int:pk>/excluir/', views.unidade_delete, name='unidade_delete'),
    
    # APIs para Unidades
    path('api/validar-codigo/', views.api_validar_codigo, name='api_validar_codigo'),
    path('api/unidade/<int:pk>/filhas/', views.api_unidade_filhas, name='api_unidade_filhas'),
    
    # Centros de Custo
    path('centros-custo/', views.centrocusto_list, name='centrocusto_list'),
    path('centros-custo/criar/', views.centrocusto_create, name='centrocusto_create'),
    path('centros-custo/<str:codigo>/editar/', views.centrocusto_update, name='centrocusto_update'),
    path('centros-custo/<str:codigo>/excluir/', views.centrocusto_delete, name='centrocusto_delete'),
    
    # APIs para Centros de Custo
    path('api/validar-codigo-centrocusto/', views.api_validar_codigo_centrocusto, name='api_validar_codigo_centrocusto'),
    
    # Contas Contábeis
    path('contas-contabeis/', views.contacontabil_list, name='contacontabil_list'),
    path('contas-contabeis/criar/', views.contacontabil_create, name='contacontabil_create'),
    path('contas-contabeis/<str:codigo>/editar/', views.contacontabil_update, name='contacontabil_update'),
    path('contas-contabeis/<str:codigo>/excluir/', views.contacontabil_delete, name='contacontabil_delete'),
    
    # APIs para Contas Contábeis
    path('api/validar-codigo-contacontabil/', views.api_validar_codigo_contacontabil, name='api_validar_codigo_contacontabil'),
    
    # Usuários
    path('usuarios/', views.usuario_list, name='usuario_list'),
    path('usuarios/criar/', views.usuario_create, name='usuario_create'),
    path('usuarios/<int:pk>/editar/', views.usuario_update, name='usuario_update'),
    path('usuarios/<int:pk>/excluir/', views.usuario_delete, name='usuario_delete'),
    
    # Parâmetros
    path('parametros/', views.parametro_list, name='parametro_list'),
    path('parametros/criar/', views.parametro_create, name='parametro_create'),
    path('parametros/<str:codigo>/', views.parametro_detail, name='parametro_detail'),
    path('parametros/<str:codigo>/editar/', views.parametro_update, name='parametro_update'),
    path('parametros/<str:codigo>/excluir/', views.parametro_delete, name='parametro_delete'),
    
    # APIs gerais
    path('api/parametro/<str:codigo>/valor/', views.api_parametro_valor, name='api_parametro_valor'),
]