# gestor/urls.py - URLs do módulo gestor do SynchroBI

from django.urls import path
from . import views

app_name = 'gestor'

urlpatterns = [
    # ===== DASHBOARD =====
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ===== USUÁRIOS =====
    path('usuarios/', views.usuario_list, name='usuario_list'),
    path('usuarios/criar/', views.usuario_create, name='usuario_create'),
    path('usuarios/<int:pk>/', views.usuario_detail, name='usuario_detail'),
    path('usuarios/<int:pk>/editar/', views.usuario_update, name='usuario_update'),
    path('usuarios/<int:pk>/deletar/', views.usuario_delete, name='usuario_delete'),
    
    # ===== UNIDADES ORGANIZACIONAIS =====
    path('unidades/', views.unidade_list, name='unidade_list'),
    path('unidades/criar/', views.unidade_create, name='unidade_create'),
    path('unidades/<int:pk>/', views.unidade_detail, name='unidade_detail'),
    path('unidades/<int:pk>/editar/', views.unidade_update, name='unidade_update'),
    path('unidades/<int:pk>/deletar/', views.unidade_delete, name='unidade_delete'),
    path('unidades/importar/', views.unidade_importar, name='unidade_importar'),
    
    # ===== PARÂMETROS DO SISTEMA =====
    path('parametros/', views.parametro_list, name='parametro_list'),
    path('parametros/criar/', views.parametro_create, name='parametro_create'),
    path('parametros/<str:codigo>/', views.parametro_detail, name='parametro_detail'),
    path('parametros/<str:codigo>/editar/', views.parametro_update, name='parametro_update'),
    path('parametros/<str:codigo>/deletar/', views.parametro_delete, name='parametro_delete'),
    
    # ===== APIs AJAX =====
    path('api/unidades/arvore/', views.unidade_arvore_json, name='api_unidades_arvore'),
    path('api/unidade/<str:codigo>/', views.api_unidade_por_codigo, name='api_unidade_por_codigo'),
    path('api/parametro/<str:codigo>/', views.api_parametro_valor, name='api_parametro_valor'),
]