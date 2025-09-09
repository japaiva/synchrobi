# gestor/views/dashboard.py - Dashboard principal do SynchroBI

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import logging

from core.models import Usuario, Unidade, ParametroSistema

logger = logging.getLogger('synchrobi')

@login_required
def home(request):
    """Dashboard principal do gestor"""
    
    # Estatísticas básicas
    unidades_ativas = list(Unidade.objects.filter(ativa=True))  # ← CORRIGIDO
    total_unidades = len(unidades_ativas)
    
    # Contar sintéticas e analíticas
    unidades_sinteticas = sum(1 for u in unidades_ativas if u.tem_sub_unidades)
    unidades_analiticas = total_unidades - unidades_sinteticas
    
    total_usuarios = Usuario.objects.filter(is_active=True).count()
    total_parametros = ParametroSistema.objects.filter(ativo=True).count()
    
    # Unidades recentes
    unidades_recentes = Unidade.objects.filter(ativa=True).order_by('-data_criacao')[:5]
    
    # Parâmetros críticos
    parametros_criticos = ParametroSistema.objects.filter(
        ativo=True, categoria='financeiro'
    ).order_by('nome')[:5]
    
    context = {
        'total_unidades': total_unidades,
        'unidades_sinteticas': unidades_sinteticas,
        'unidades_analiticas': unidades_analiticas,
        'total_usuarios': total_usuarios,
        'total_parametros': total_parametros,
        'unidades_recentes': unidades_recentes,
        'parametros_criticos': parametros_criticos,
    }
    
    return render(request, 'gestor/dashboard.html', context)

@login_required
def dashboard(request):
    """Alias para home"""
    return home(request)