# gestor/urls.py - ATUALIZADO COM SERVIÇO DE FORNECEDOR

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
    
    # ===== CENTROS DE CUSTO - NOVA ARQUITETURA FOCADA NA ÁRVORE =====
    
    # View principal (árvore hierárquica)
    path('centros-custo/', views.centrocusto_tree_view, name='centrocusto_tree'),
    
    # Views modais para CRUD
    path('centros-custo/criar/', views.centrocusto_create_modal, name='centrocusto_create_modal'),
    path('centros-custo/<str:codigo>/editar/', views.centrocusto_update_modal, name='centrocusto_update_modal'),
    path('centros-custo/<str:codigo>/excluir/', views.centrocusto_delete_ajax, name='centrocusto_delete_ajax'),
    
    # APIs para árvore de centros de custo
    path('api/centros-custo/tree-data/', views.api_centrocusto_tree_data, name='api_centrocusto_tree_data'),
    path('api/centros-custo/validar-codigo/', views.api_validar_codigo_centrocusto, name='api_validar_codigo_centrocusto'),
    path('api/centro-custo/<str:codigo>/', views.api_centro_custo_detalhes, name='api_centro_custo_detalhes'),
    
    # Views mantidas para compatibilidade (redirecionam para árvore ou modais)
    path('centros-custo/lista/', views.centrocusto_list, name='centrocusto_list'),
    path('centros-custo/novo/', views.centrocusto_create, name='centrocusto_create'),
    path('centros-custo/<str:codigo>/editar-old/', views.centrocusto_update, name='centrocusto_update'),
    path('centros-custo/<str:codigo>/excluir-old/', views.centrocusto_delete, name='centrocusto_delete'),

    # ===== CONTAS CONTÁBEIS - NOVA ARQUITETURA FOCADA NA ÁRVORE =====
    
    # View principal da árvore
    path('contas-contabeis/', views.contacontabil_tree_view, name='contacontabil_tree'),
    
    # Views modais
    path('contas-contabeis/nova/', views.contacontabil_create_modal, name='contacontabil_create_modal'),
    path('contas-contabeis/<str:codigo>/editar/', views.contacontabil_update_modal, name='contacontabil_update_modal'),
    path('contas-contabeis/<str:codigo>/excluir/', views.contacontabil_delete_ajax, name='contacontabil_delete_ajax'),
    
    # APIs básicas
    path('api/contas-contabeis/tree-data/', views.api_contacontabil_tree_data, name='api_contacontabil_tree_data'),
    path('api/contas-contabeis/validar-codigo/', views.api_validar_codigo_contacontabil, name='api_validar_codigo_contacontabil'),
    
    # URLs de compatibilidade (redirecionam para árvore)
    path('contas-contabeis/lista/', views.contacontabil_list, name='contacontabil_list'),
    path('contas-contabeis/criar/', views.contacontabil_create, name='contacontabil_create'),
    path('contas-contabeis/<str:codigo>/', views.contacontabil_update, name='contacontabil_update'),
    path('contas-contabeis/<str:codigo>/deletar/', views.contacontabil_delete, name='contacontabil_delete'),

    # ===== CONTAS CONTÁBEIS COM CÓDIGOS EXTERNOS =====
    
    # Redirecionamento simples para lista com filtro
    path('contas-contabeis/arvore-externa/', views.contaexterna_list, name='contacontabil_tree_with_external'),
    
    # API básica (redireciona para lista também)
    path('api/contas-contabeis/arvore-externa/', views.contaexterna_list, name='api_contacontabil_tree_with_external'),
    
    # ===== CRUD PARA CÓDIGOS EXTERNOS (INLINE) =====
    
    # Views principais para contas externas
    path('contas-externas/', views.contaexterna_list, name='contaexterna_list'),
    path('contas-externas/nova/', views.contaexterna_create, name='contaexterna_create'),
    path('contas-externas/<int:pk>/editar/', views.contaexterna_update, name='contaexterna_update'),
    
    # APIs para operações inline
    path('api/contas-externas/validar-codigo/', views.api_validar_codigo_externo, name='api_validar_codigo_externo'),
    path('api/contas-externas/<int:pk>/delete/', views.api_contaexterna_delete, name='api_contaexterna_delete'),

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
    
    # ===== FORNECEDORES =====
    path('fornecedores/', views.fornecedor_list, name='fornecedor_list'),
    path('fornecedores/novo/', views.fornecedor_create, name='fornecedor_create'),
    path('fornecedores/<str:codigo>/editar/', views.fornecedor_update, name='fornecedor_update'),
    path('fornecedores/<str:codigo>/excluir/', views.fornecedor_delete, name='fornecedor_delete'),
    
    # APIs Fornecedor
    path('api/fornecedor/validar-codigo/', views.api_validar_codigo_fornecedor, name='api_validar_codigo_fornecedor'),
    path('api/fornecedor/buscar/', views.api_buscar_fornecedor, name='api_buscar_fornecedor'),
    path('api/fornecedor/<str:codigo>/', views.api_fornecedor_info, name='api_fornecedor_info'),
    path('api/fornecedor/extrair-historico/', views.api_extrair_fornecedor_historico, name='api_extrair_fornecedor_historico'),
    
    # ===== MOVIMENTOS - CRUD BÁSICO =====
    path('movimentos/', views.movimento_list, name='movimento_list'),
    path('movimentos/novo/', views.movimento_create, name='movimento_create'),
    path('movimentos/<int:pk>/editar/', views.movimento_update, name='movimento_update'),
    path('movimentos/<int:pk>/excluir/', views.movimento_delete, name='movimento_delete'),
    path('movimentos/export-excel/', views.movimento_export_excel, name='movimento_export_excel'),
    
    # ===== MOVIMENTOS - IMPORTAÇÃO COM SERVIÇO OTIMIZADO =====
    path('movimentos/importar/', views.movimento_importar, name='movimento_importar'),
    
    # APIs Movimento Import Otimizadas
    path('api/movimento/preview-excel/', views.api_preview_movimentos_excel, name='api_preview_movimentos_excel'),
    path('api/movimento/importar-excel/', views.api_importar_movimentos_excel, name='api_importar_movimentos_excel'),
    path('api/movimento/validar-periodo/', views.api_validar_periodo_importacao, name='api_validar_periodo_importacao'),
    path('api/movimento/validar-periodo-simples/', views.api_validar_periodo_simples, name='api_validar_periodo_simples'),
    path('api/movimento/importar-simples/', views.api_importar_movimentos_simples, name='api_importar_movimentos_simples'),

    # APIs gerais
    path('api/parametro/<str:codigo>/valor/', views.api_parametro_valor, name='api_parametro_valor'),
]