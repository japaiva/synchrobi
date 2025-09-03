# gestor/urls.py - URLs do módulo gestor

from django.urls import path
from . import views

app_name = 'gestor'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('home/', views.home, name='home'),
    
    # Unidades
    path('unidades/', views.unidade_list, name='unidade_list'),
    path('unidades/criar/', views.unidade_create, name='unidade_create'),
    path('unidades/<int:pk>/', views.unidade_detail, name='unidade_detail'),
    path('unidades/<int:pk>/editar/', views.unidade_update, name='unidade_update'),
    path('unidades/<int:pk>/excluir/', views.unidade_delete, name='unidade_delete'),
    path('unidades/arvore/', views.unidade_arvore, name='unidade_arvore'),
    
    # APIs para Unidades
    path('api/validar-codigo/', views.api_validar_codigo, name='api_validar_codigo'),
    path('api/unidade/<int:pk>/filhas/', views.api_unidade_filhas, name='api_unidade_filhas'),
    
    # Usuários
    path('usuarios/', views.usuario_list, name='usuario_list'),
    path('usuarios/criar/', views.usuario_create, name='usuario_create'),
    path('usuarios/<int:pk>/', views.usuario_detail, name='usuario_detail'),
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