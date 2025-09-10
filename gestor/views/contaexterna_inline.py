# gestor/views/contaexterna_inline.py - Views adaptadas para edição inline

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
import logging

from core.models import ContaContabil, ContaExterna

logger = logging.getLogger('synchrobi')

@login_required
def contaexterna_list(request):
    """Lista de códigos externos com filtros - adaptada para inline"""
    
    # Filtros da URL
    conta_codigo = request.GET.get('conta')
    sistema = request.GET.get('sistema', '').strip()
    codigo_externo = request.GET.get('codigo_externo', '').strip()
    ativa = request.GET.get('ativa', '')
    
    # Query base
    queryset = ContaExterna.objects.select_related('conta_contabil').order_by(
        'conta_contabil__codigo', 'sistema_origem', 'codigo_externo'
    )
    
    # Aplicar filtros
    if conta_codigo:
        queryset = queryset.filter(conta_contabil__codigo=conta_codigo)
    
    if sistema:
        queryset = queryset.filter(sistema_origem__icontains=sistema)
    
    if codigo_externo:
        queryset = queryset.filter(codigo_externo__icontains=codigo_externo)
    
    if ativa:
        queryset = queryset.filter(ativa=ativa.lower() == 'true')
    else:
        # Por padrão, mostrar apenas ativos
        queryset = queryset.filter(ativa=True)
    
    # Paginação menor para modal
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filtros': {
            'conta_codigo': conta_codigo,
            'sistema': sistema,
            'codigo_externo': codigo_externo,
            'ativa': ativa
        },
        'total_count': queryset.count()
    }
    
    # Se for AJAX (modal), retornar template inline
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/contaexterna_list_modal.html', context)
    
    # Se não for AJAX, retornar página completa
    return render(request, 'gestor/contaexterna_list.html', context)

@login_required
def contaexterna_create(request):
    """Criar nova conta externa - simplificado para inline"""
    
    if request.method == 'POST':
        # Dados do formulário inline
        conta_contabil_codigo = request.POST.get('conta_contabil', '').strip()
        codigo_externo = request.POST.get('codigo_externo', '').strip()
        nome_externo = request.POST.get('nome_externo', '').strip()
        ativa = request.POST.get('ativa') == 'on'
        
        # Validações básicas
        if not conta_contabil_codigo or not codigo_externo or not nome_externo:
            return JsonResponse({
                'success': False,
                'message': 'Todos os campos são obrigatórios'
            })
        
        try:
            # Buscar conta contábil
            conta_contabil = ContaContabil.objects.get(codigo=conta_contabil_codigo)
            
            # Verificar se já existe
            if ContaExterna.objects.filter(
                conta_contabil=conta_contabil,
                codigo_externo=codigo_externo,
                ativa=True
            ).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Já existe código externo "{codigo_externo}" para esta conta'
                })
            
            # Criar conta externa
            conta_externa = ContaExterna.objects.create(
                conta_contabil=conta_contabil,
                codigo_externo=codigo_externo,
                nome_externo=nome_externo,
                ativa=ativa
            )
            
            logger.info(f'Conta externa criada inline: {conta_externa.codigo_externo} por {request.user}')
            
            return JsonResponse({
                'success': True,
                'message': f'Código externo "{conta_externa.codigo_externo}" criado com sucesso!',
                'conta_externa': {
                    'id': conta_externa.id,
                    'codigo_externo': conta_externa.codigo_externo,
                    'nome_externo': conta_externa.nome_externo
                }
            })
            
        except ContaContabil.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Conta contábil não encontrada'
            })
        except Exception as e:
            logger.error(f"Erro ao criar conta externa inline: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Erro ao criar código externo: {str(e)}'
            })
    
    # GET request - formulário modal simples
    conta_contabil_codigo = request.GET.get('conta_contabil')
    
    context = {
        'conta_contabil_codigo': conta_contabil_codigo,
        'title': 'Novo Código Externo'
    }
    
    return render(request, 'gestor/contaexterna_create_inline.html', context)

@login_required
def contaexterna_update(request, pk):
    """Editar conta externa - simplificado para inline"""
    
    conta_externa = get_object_or_404(ContaExterna, pk=pk)
    
    if request.method == 'POST':
        # Dados do formulário inline
        codigo_externo = request.POST.get('codigo_externo', '').strip()
        nome_externo = request.POST.get('nome_externo', '').strip()
        ativa = request.POST.get('ativa') == 'on'
        
        # Validações básicas
        if not codigo_externo or not nome_externo:
            return JsonResponse({
                'success': False,
                'message': 'Código e nome são obrigatórios'
            })
        
        try:
            # Verificar se já existe outro com mesmo código
            duplicata = ContaExterna.objects.filter(
                conta_contabil=conta_externa.conta_contabil,
                codigo_externo=codigo_externo,
                ativa=True
            ).exclude(pk=pk)
            
            if duplicata.exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Já existe outro código externo "{codigo_externo}" para esta conta'
                })
            
            # Atualizar
            conta_externa.codigo_externo = codigo_externo
            conta_externa.nome_externo = nome_externo
            conta_externa.ativa = ativa
            conta_externa.save()
            
            logger.info(f'Conta externa editada inline: {conta_externa.codigo_externo} por {request.user}')
            
            return JsonResponse({
                'success': True,
                'message': f'Código externo "{conta_externa.codigo_externo}" atualizado com sucesso!',
                'conta_externa': {
                    'id': conta_externa.id,
                    'codigo_externo': conta_externa.codigo_externo,
                    'nome_externo': conta_externa.nome_externo
                }
            })
            
        except Exception as e:
            logger.error(f"Erro ao editar conta externa inline {pk}: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Erro ao atualizar código externo: {str(e)}'
            })
    
    # GET request não é necessário para inline
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@login_required
@require_POST
def api_contaexterna_delete(request, pk):
    """API para excluir conta externa"""
    
    conta_externa = get_object_or_404(ContaExterna, pk=pk)
    
    try:
        codigo_externo = conta_externa.codigo_externo
        conta_externa.delete()
        
        logger.info(f'Conta externa excluída inline: {codigo_externo} por {request.user}')
        
        return JsonResponse({
            'success': True,
            'message': f'Código externo "{codigo_externo}" excluído com sucesso!'
        })
        
    except Exception as e:
        logger.error(f'Erro ao excluir conta externa inline {pk}: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'Erro ao excluir código externo: {str(e)}'
        })

@login_required
def api_validar_codigo_externo(request):
    """API para validar código externo em tempo real"""
    
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
    
    # Verificar se já existe OUTRO código externo com esta combinação
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
            'error': f'Já existe código externo ativo "{codigo_externo}" para a conta {conta_contabil.codigo}'
        })
    
    return JsonResponse({
        'valid': True,
        'conta_contabil': {
            'codigo': conta_contabil.codigo,
            'nome': conta_contabil.nome,
            'tipo_display': conta_contabil.get_tipo_display()
        }
    })