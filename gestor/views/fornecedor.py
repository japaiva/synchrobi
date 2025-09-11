# gestor/views/fornecedor.py - Views completas para fornecedor (SEM TOGGLE STATUS)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
import logging

from core.models import Fornecedor
from core.forms import FornecedorForm

logger = logging.getLogger('synchrobi')

@login_required
def fornecedor_list(request):
    """Lista de fornecedores com filtros"""
    search = request.GET.get('search', '')
    criado_auto = request.GET.get('criado_auto', '')
    ativo = request.GET.get('ativo', '')
    
    fornecedores = Fornecedor.objects.all().order_by('razao_social')
    
    if search:
        fornecedores = fornecedores.filter(
            Q(codigo__icontains=search) |
            Q(razao_social__icontains=search) |
            Q(nome_fantasia__icontains=search) |
            Q(cnpj_cpf__icontains=search)
        )
    
    if criado_auto:
        fornecedores = fornecedores.filter(criado_automaticamente=(criado_auto == 'true'))
    
    if ativo:
        fornecedores = fornecedores.filter(ativo=(ativo == 'true'))
    
    # Paginação
    paginator = Paginator(fornecedores, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'criado_auto': criado_auto,
        'ativo': ativo,
    }
    return render(request, 'gestor/fornecedor_list.html', context)

@login_required
def fornecedor_create(request):
    """Criar novo fornecedor"""
    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            try:
                fornecedor = form.save()
                messages.success(request, f'Fornecedor "{fornecedor.razao_social}" criado com sucesso!')
                logger.info(f'Fornecedor criado: {fornecedor.codigo} - {fornecedor.razao_social} por {request.user}')
                return redirect('gestor:fornecedor_list')
            except Exception as e:
                messages.error(request, f'Erro ao criar fornecedor: {str(e)}')
                logger.error(f'Erro ao criar fornecedor: {str(e)}')
        else:
            messages.error(request, 'Erro ao criar fornecedor. Verifique os dados.')
    else:
        form = FornecedorForm()
    
    context = {
        'form': form,
        'title': 'Novo Fornecedor',
        'is_create': True
    }
    return render(request, 'gestor/fornecedor_form.html', context)

@login_required
def fornecedor_update(request, codigo):
    """Editar fornecedor"""
    fornecedor = get_object_or_404(Fornecedor, codigo=codigo)
    
    # Guardar valores originais para log
    valores_originais = {
        'razao_social': fornecedor.razao_social,
        'nome_fantasia': fornecedor.nome_fantasia,
        'cnpj_cpf': fornecedor.cnpj_cpf,
        'ativo': fornecedor.ativo
    }
    
    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            try:
                fornecedor_atualizado = form.save()
                
                # Log de alterações
                alteracoes = []
                for campo, valor_original in valores_originais.items():
                    valor_novo = getattr(fornecedor_atualizado, campo)
                    if valor_original != valor_novo:
                        alteracoes.append(f"{campo}: {valor_original} → {valor_novo}")
                
                if alteracoes:
                    logger.info(f'Fornecedor {fornecedor.codigo} alterado por {request.user}: {", ".join(alteracoes)}')
                
                messages.success(request, f'Fornecedor "{fornecedor_atualizado.razao_social}" atualizado com sucesso!')
                return redirect('gestor:fornecedor_list')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar fornecedor: {str(e)}')
                logger.error(f'Erro ao atualizar fornecedor {fornecedor.codigo}: {str(e)}')
        else:
            messages.error(request, 'Erro ao atualizar fornecedor. Verifique os dados.')
    else:
        form = FornecedorForm(instance=fornecedor)
    
    context = {
        'form': form,
        'title': 'Editar Fornecedor',
        'fornecedor': fornecedor,
        'is_create': False
    }
    return render(request, 'gestor/fornecedor_form.html', context)


# gestor/views/fornecedor.py - VIEW DELETE CORRIGIDA E SIMPLIFICADA

@login_required
def fornecedor_delete(request, codigo):
    """Deletar fornecedor - VERSÃO SIMPLIFICADA"""
    fornecedor = get_object_or_404(Fornecedor, codigo=codigo)
    
    # Contar movimentos associados (para informar o usuário)
    movimentos_count = fornecedor.movimentos.count()
    
    if request.method == 'POST':
        razao_social = fornecedor.razao_social
        codigo_fornecedor = fornecedor.codigo
        
        try:
            # Log antes da exclusão
            if movimentos_count > 0:
                logger.warning(
                    f'Fornecedor {codigo_fornecedor} - {razao_social} excluído com {movimentos_count} movimento(s) associado(s) por {request.user}'
                )
            
            fornecedor.delete()
            
            # CORREÇÃO: Mensagem de sucesso CORRETA
            if movimentos_count > 0:
                messages.warning(
                    request,  # ADICIONADO: request como primeiro parâmetro
                    f'Fornecedor "{razao_social}" excluído! '
                    f'Atenção: {movimentos_count} movimento(s) ficaram sem referência de fornecedor.'
                )
            else:
                messages.success(
                    request,  # ADICIONADO: request como primeiro parâmetro
                    f'Fornecedor "{razao_social}" excluído com sucesso!'
                )
            
            logger.info(f'Fornecedor excluído: {codigo_fornecedor} - {razao_social} por {request.user}')
            return redirect('gestor:fornecedor_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao excluir fornecedor: {str(e)}')
            logger.error(f'Erro ao excluir fornecedor {codigo_fornecedor}: {str(e)}')
            return redirect('gestor:fornecedor_list')
    
    context = {
        'fornecedor': fornecedor,
        'movimentos_count': movimentos_count
    }
    return render(request, 'gestor/fornecedor_delete.html', context)


# ===== API ENDPOINTS =====

@login_required
def api_validar_codigo_fornecedor(request):
    """API para validar código de fornecedor em tempo real"""
    codigo = request.GET.get('codigo', '').strip()
    fornecedor_codigo = request.GET.get('atual', None)
    
    if not codigo:
        return JsonResponse({'valid': False, 'error': 'Código é obrigatório'})
    
    # Verificar duplicação
    query = Fornecedor.objects.filter(codigo=codigo)
    if fornecedor_codigo:
        query = query.exclude(codigo=fornecedor_codigo)
    
    if query.exists():
        return JsonResponse({'valid': False, 'error': 'Já existe um fornecedor com este código'})
    
    return JsonResponse({
        'valid': True,
        'message': f'Código {codigo} disponível'
    })

@login_required
def api_buscar_fornecedor(request):
    """API para buscar fornecedor por código ou nome"""
    search_term = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 10))
    
    if not search_term or len(search_term) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Termo de busca deve ter pelo menos 2 caracteres'
        })
    
    try:
        # Buscar fornecedores
        fornecedores = Fornecedor.objects.filter(
            Q(codigo__icontains=search_term) |
            Q(razao_social__icontains=search_term) |
            Q(nome_fantasia__icontains=search_term),
            ativo=True
        ).order_by('razao_social')[:limit]
        
        results = []
        for fornecedor in fornecedores:
            results.append({
                'codigo': fornecedor.codigo,
                'razao_social': fornecedor.razao_social,
                'nome_fantasia': fornecedor.nome_fantasia,
                'nome_display': fornecedor.nome_display,
                'cnpj_cpf': fornecedor.cnpj_cpf_formatado,
                'tipo_pessoa': fornecedor.tipo_pessoa,
                'criado_automaticamente': fornecedor.criado_automaticamente,
                'telefone': fornecedor.telefone,
                'email': fornecedor.email
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'total_found': len(results),
            'has_more': len(results) == limit
        })
        
    except Exception as e:
        logger.error(f'Erro na busca de fornecedores: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro na busca'
        })

@login_required
def api_fornecedor_info(request, codigo):
    """API para buscar informações de um fornecedor"""
    try:
        fornecedor = Fornecedor.objects.get(codigo=codigo)
        
        data = {
            'success': True,
            'fornecedor': {
                'codigo': fornecedor.codigo,
                'razao_social': fornecedor.razao_social,
                'nome_fantasia': fornecedor.nome_fantasia,
                'nome_display': fornecedor.nome_display,
                'cnpj_cpf': fornecedor.cnpj_cpf_formatado,
                'tipo_pessoa': fornecedor.tipo_pessoa,
                'ativo': fornecedor.ativo,
                'criado_automaticamente': fornecedor.criado_automaticamente,
                'telefone': fornecedor.telefone,
                'email': fornecedor.email,
                'endereco': fornecedor.endereco,
                'total_movimentos': fornecedor.movimentos.count()
            }
        }
        
        return JsonResponse(data)
        
    except Fornecedor.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Fornecedor não encontrado'})
    except Exception as e:
        logger.error(f'Erro na API de fornecedor: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Erro interno'})

@login_required
def api_extrair_fornecedor_historico(request):
    """API para extrair fornecedor do histórico (para testes)"""
    historico = request.GET.get('historico', '').strip()
    
    if not historico:
        return JsonResponse({'success': False, 'error': 'Histórico é obrigatório'})
    
    try:
        fornecedor = Fornecedor.extrair_do_historico(historico, salvar=False)
        
        if fornecedor:
            return JsonResponse({
                'success': True,
                'fornecedor_extraido': {
                    'codigo': fornecedor.codigo,
                    'razao_social': fornecedor.razao_social,
                    'existe': Fornecedor.objects.filter(codigo=fornecedor.codigo).exists()
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Nenhum fornecedor encontrado no histórico'
            })
            
    except Exception as e:
        logger.error(f'Erro ao extrair fornecedor: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro ao processar histórico'
        })