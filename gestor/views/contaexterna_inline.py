# gestor/views/contaexterna_inline.py - VERSÃO ULTRA SIMPLES

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import logging

from core.models import ContaContabil, ContaExterna

logger = logging.getLogger('synchrobi')

@login_required
def contaexterna_list(request):
    """Lista códigos externos - versão simples"""
    
    conta_codigo = request.GET.get('conta')
    
    # Query base
    queryset = ContaExterna.objects.select_related('conta_contabil').order_by('codigo_externo')
    
    # Filtrar por conta se especificado
    if conta_codigo:
        queryset = queryset.filter(conta_contabil__codigo=conta_codigo, ativa=True)
    
    # Paginação
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filtros': {'conta_codigo': conta_codigo}
    }
    
    # Se for AJAX, retornar template do modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/contaexterna_list_modal.html', context)
    
    return render(request, 'gestor/contaexterna_list.html', context)

@login_required
def contaexterna_create(request):
    """Criar nova conta externa - versão simples"""
    
    if request.method == 'POST':
        try:
            # Pegar dados do POST
            conta_contabil_codigo = request.POST.get('conta_contabil', '').strip()
            codigo_externo = request.POST.get('codigo_externo', '').strip()
            nome_externo = request.POST.get('nome_externo', '').strip()
            sistema_origem = request.POST.get('sistema_origem', '').strip()
            
            # Validações básicas
            if not conta_contabil_codigo:
                return JsonResponse({'success': False, 'message': 'Conta contábil é obrigatória'})
            
            if not codigo_externo:
                return JsonResponse({'success': False, 'message': 'Código externo é obrigatório'})
            
            if not nome_externo:
                return JsonResponse({'success': False, 'message': 'Nome externo é obrigatório'})
            
            # Buscar conta contábil
            try:
                conta_contabil = ContaContabil.objects.get(codigo=conta_contabil_codigo)
            except ContaContabil.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Conta contábil não encontrada'})
            
            # Verificar duplicação
            if ContaExterna.objects.filter(
                conta_contabil=conta_contabil,
                codigo_externo=codigo_externo,
                ativa=True
            ).exists():
                return JsonResponse({'success': False, 'message': f'Código "{codigo_externo}" já existe para esta conta'})
            
            # Criar conta externa
            conta_externa = ContaExterna.objects.create(
                conta_contabil=conta_contabil,
                codigo_externo=codigo_externo,
                nome_externo=nome_externo,
                sistema_origem=sistema_origem,
                ativa=True
            )
            
            logger.info(f'Conta externa criada: {conta_externa.codigo_externo} por {request.user}')
            
            return JsonResponse({
                'success': True,
                'message': f'Código "{conta_externa.codigo_externo}" criado com sucesso!'
            })
            
        except Exception as e:
            logger.error(f"Erro ao criar conta externa: {str(e)}")
            return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})
    
    # GET - formulário simples
    conta_contabil_codigo = request.GET.get('conta_contabil')
    context = {'conta_contabil_codigo': conta_contabil_codigo}
    return render(request, 'gestor/contaexterna_create_simple.html', context)

@login_required
def contaexterna_update(request, pk):
    """Editar conta externa - versão simples"""
    
    conta_externa = get_object_or_404(ContaExterna, pk=pk)
    
    if request.method == 'POST':
        try:
            # Pegar dados do POST
            codigo_externo = request.POST.get('codigo_externo', '').strip()
            nome_externo = request.POST.get('nome_externo', '').strip()
            sistema_origem = request.POST.get('sistema_origem', '').strip()
            
            # Validações básicas
            if not codigo_externo:
                return JsonResponse({'success': False, 'message': 'Código externo é obrigatório'})
            
            if not nome_externo:
                return JsonResponse({'success': False, 'message': 'Nome externo é obrigatório'})
            
            # Verificar duplicação (excluindo o atual)
            duplicata = ContaExterna.objects.filter(
                conta_contabil=conta_externa.conta_contabil,
                codigo_externo=codigo_externo,
                ativa=True
            ).exclude(pk=pk)
            
            if duplicata.exists():
                return JsonResponse({'success': False, 'message': f'Código "{codigo_externo}" já existe para esta conta'})
            
            # Atualizar
            conta_externa.codigo_externo = codigo_externo
            conta_externa.nome_externo = nome_externo
            conta_externa.sistema_origem = sistema_origem
            conta_externa.save()
            
            logger.info(f'Conta externa editada: {conta_externa.codigo_externo} por {request.user}')
            
            return JsonResponse({
                'success': True,
                'message': f'Código "{conta_externa.codigo_externo}" atualizado com sucesso!'
            })
            
        except Exception as e:
            logger.error(f"Erro ao editar conta externa {pk}: {str(e)}")
            return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@login_required
@require_POST
def api_contaexterna_delete(request, pk):
    """Excluir conta externa - versão simples"""
    
    try:
        conta_externa = get_object_or_404(ContaExterna, pk=pk)
        codigo_externo = conta_externa.codigo_externo
        
        conta_externa.delete()
        
        logger.info(f'Conta externa excluída: {codigo_externo} por {request.user}')
        
        return JsonResponse({
            'success': True,
            'message': f'Código "{codigo_externo}" excluído com sucesso!'
        })
        
    except Exception as e:
        logger.error(f'Erro ao excluir conta externa {pk}: {str(e)}')
        return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})

# Funções auxiliares mantidas para compatibilidade
@login_required
def api_validar_codigo_externo(request):
    """Validar código externo - versão simples"""
    
    codigo_externo = request.GET.get('codigo_externo', '').strip()
    conta_contabil_codigo = request.GET.get('conta_contabil', '').strip()
    conta_externa_id = request.GET.get('atual', None)
    
    if not codigo_externo:
        return JsonResponse({'valid': False, 'error': 'Código externo é obrigatório'})
    
    if not conta_contabil_codigo:
        return JsonResponse({'valid': False, 'error': 'Conta contábil é obrigatória'})
    
    try:
        conta_contabil = ContaContabil.objects.get(codigo=conta_contabil_codigo)
    except ContaContabil.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Conta contábil não encontrada'})
    
    # Verificar duplicação
    query = ContaExterna.objects.filter(
        conta_contabil=conta_contabil,
        codigo_externo=codigo_externo,
        ativa=True
    )
    
    if conta_externa_id:
        query = query.exclude(pk=conta_externa_id)
    
    if query.exists():
        return JsonResponse({
            'valid': False, 
            'error': f'Código "{codigo_externo}" já existe para a conta {conta_contabil.codigo}'
        })
    
    return JsonResponse({
        'valid': True,
        'conta_contabil': {
            'codigo': conta_contabil.codigo,
            'nome': conta_contabil.nome
        }
    })