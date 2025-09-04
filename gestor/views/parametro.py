# gestor/views/parametro.py - CRUD de Parâmetros do Sistema

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
import logging

from core.models import ParametroSistema
from core.forms import ParametroSistemaForm

logger = logging.getLogger('synchrobi')

@login_required
def parametro_list(request):
    """Lista de parâmetros do sistema"""
    search = request.GET.get('search', '')
    categoria = request.GET.get('categoria', '')
    tipo = request.GET.get('tipo', '')
    
    parametros = ParametroSistema.objects.all().order_by('categoria', 'nome')
    
    if search:
        parametros = parametros.filter(
            Q(codigo__icontains=search) |
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )
    
    if categoria:
        parametros = parametros.filter(categoria=categoria)
    
    if tipo:
        parametros = parametros.filter(tipo=tipo)
    
    # Paginação
    paginator = Paginator(parametros, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opções para filtros
    categorias_disponiveis = ParametroSistema.objects.values_list(
        'categoria', flat=True
    ).distinct().order_by('categoria')
    tipos_disponiveis = ParametroSistema.TIPO_CHOICES
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'categoria': categoria,
        'tipo': tipo,
        'categorias_disponiveis': categorias_disponiveis,
        'tipos_disponiveis': tipos_disponiveis,
    }
    return render(request, 'gestor/parametro_list.html', context)

@login_required
def parametro_create(request):
    """Criar novo parâmetro"""
    if request.method == 'POST':
        form = ParametroSistemaForm(request.POST)
        if form.is_valid():
            parametro = form.save(commit=False)
            parametro.usuario_alteracao = request.user
            parametro.save()
            messages.success(request, f'Parâmetro "{parametro.nome}" criado com sucesso!')
            return redirect('gestor:parametro_list')
        else:
            messages.error(request, 'Erro ao criar parâmetro. Verifique os dados.')
    else:
        form = ParametroSistemaForm()
    
    context = {'form': form, 'title': 'Novo Parâmetro'}
    return render(request, 'gestor/parametro_form.html', context)

@login_required
def parametro_detail(request, codigo):
    """Detalhes do parâmetro"""
    parametro = get_object_or_404(ParametroSistema, codigo=codigo)
    
    context = {'parametro': parametro}
    return render(request, 'gestor/parametro_detail.html', context)

@login_required
def parametro_update(request, codigo):
    """Editar parâmetro"""
    parametro = get_object_or_404(ParametroSistema, codigo=codigo)
    
    if request.method == 'POST':
        form = ParametroSistemaForm(request.POST, instance=parametro)
        if form.is_valid():
            parametro = form.save(commit=False)
            parametro.usuario_alteracao = request.user
            parametro.save()
            messages.success(request, f'Parâmetro "{parametro.nome}" atualizado com sucesso!')
            return redirect('gestor:parametro_list')
        else:
            messages.error(request, 'Erro ao atualizar parâmetro. Verifique os dados.')
    else:
        form = ParametroSistemaForm(instance=parametro)
    
    context = {'form': form, 'title': 'Editar Parâmetro', 'parametro': parametro}
    return render(request, 'gestor/parametro_form.html', context)

@login_required
def parametro_delete(request, codigo):
    """Deletar parâmetro"""
    parametro = get_object_or_404(ParametroSistema, codigo=codigo)
    
    # Verificar se parâmetro é editável
    if not parametro.editavel:
        messages.error(request, 'Este parâmetro não pode ser excluído.')
        return redirect('gestor:parametro_detail', codigo=codigo)
    
    if request.method == 'POST':
        nome = parametro.nome
        parametro.delete()
        messages.success(request, f'Parâmetro "{nome}" excluído com sucesso!')
        return redirect('gestor:parametro_list')
    
    context = {'parametro': parametro}
    return render(request, 'gestor/parametro_confirm_delete.html', context)

# ===== API ENDPOINT =====

@login_required  
def api_parametro_valor(request, codigo):
    """API para buscar valor de um parâmetro"""
    try:
        valor = ParametroSistema.get_parametro(codigo)
        if valor is None:
            return JsonResponse({'success': False, 'error': 'Parâmetro não encontrado'})
        
        return JsonResponse({
            'success': True, 
            'codigo': codigo,
            'valor': valor
        })
        
    except Exception as e:
        logger.error(f'Erro na API de parâmetro: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Erro interno'})