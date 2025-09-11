# gestor/views/contacontabil.py - CRUD com Modal Hierárquico - HIERARQUIA DECLARADA

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import logging
import json

from core.models import ContaContabil
from core.forms import ContaContabilForm

logger = logging.getLogger('synchrobi')

# ===== VIEW PRINCIPAL DA ÁRVORE =====

@login_required
def contacontabil_tree_view(request):
    """Visualização hierárquica de contas contábeis - HIERARQUIA DECLARADA"""
    
    try:
        # Query única otimizada
        contas_queryset = ContaContabil.objects.filter(ativa=True).order_by('codigo')
        
        # Construir árvore usando hierarquia declarada (importar de contacontabil_tree.py)
        from .contacontabil_tree import construir_arvore_declarada, calcular_stats_contas
        tree_data = construir_arvore_declarada(contas_queryset)
        stats = calcular_stats_contas(contas_queryset)
        
        context = {
            'tree_data_json': json.dumps(tree_data, ensure_ascii=False, indent=2),
            'stats': stats,
            'entity_name': 'Contas Contábeis',
            'entity_singular': 'Conta Contábil',
            'create_url': 'gestor:contacontabil_create_modal',
            'update_url_base': '/gestor/contas-contabeis/',
            'tree_url': 'gestor:contacontabil_tree',
            'api_tree_data_url': 'gestor:api_contacontabil_tree_data',
            'breadcrumb': 'Contas Contábeis',
            'icon': 'fa-calculator'
        }
        
        return render(request, 'gestor/contacontabil_tree_main.html', context)
        
    except Exception as e:
        logger.error(f'Erro na construção da árvore de contas contábeis: {str(e)}')
        
        # Fallback simples
        context = {
            'tree_data_json': '[]',
            'stats': {'total': 0, 'tipo_s': 0, 'tipo_a': 0},
            'error_message': 'Erro ao carregar árvore de contas contábeis',
            'entity_name': 'Contas Contábeis',
            'entity_singular': 'Conta Contábil',
            'create_url': 'gestor:contacontabil_create_modal',
            'update_url_base': '/gestor/contas-contabeis/',
            'tree_url': 'gestor:contacontabil_tree',
            'api_tree_data_url': 'gestor:api_contacontabil_tree_data',
            'breadcrumb': 'Contas Contábeis',
            'icon': 'fa-calculator'
        }
        return render(request, 'gestor/contacontabil_tree_main.html', context)

# ===== VIEWS MODAIS =====

@login_required
def contacontabil_create_modal(request):
    """Criar nova conta contábil via modal"""
    
    if request.method == 'POST':
        logger.info(f"Criando nova conta contábil")
        logger.info(f"POST data recebido: {dict(request.POST)}")
        
        form = ContaContabilForm(request.POST)
        
        if form.is_valid():
            logger.info(f"Formulário válido. Dados: {form.cleaned_data}")
            
            try:
                from django.db import transaction
                
                with transaction.atomic():
                    conta = form.save()
                    logger.info(f"Conta contábil criada: {conta.codigo} - {conta.nome}")
                
                conta_verificacao = ContaContabil.objects.get(codigo=conta.codigo)
                logger.info(f"Verificação: conta criada com sucesso - {conta_verificacao.nome}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Conta contábil "{conta_verificacao.nome}" criada com sucesso!',
                        'conta': {
                            'codigo': conta_verificacao.codigo,
                            'nome': conta_verificacao.nome,
                            'tipo': conta_verificacao.tipo,
                            'nivel': conta_verificacao.nivel
                        }
                    })
                
                messages.success(request, f'Conta contábil "{conta_verificacao.nome}" criada com sucesso!')
                return redirect('gestor:contacontabil_tree')
                
            except Exception as e:
                logger.error(f"Erro ao criar conta contábil: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erro ao criar conta contábil: {str(e)}'
                    })
                
                messages.error(request, f'Erro ao criar conta contábil: {str(e)}')
        else:
            logger.error(f"Formulário inválido: {form.errors}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Dados inválidos. Verifique os campos.',
                    'errors': form.errors
                })
            messages.error(request, 'Dados inválidos. Verifique os campos.')
    
    else:
        form = ContaContabilForm()
        
        codigo_pai = request.GET.get('codigo_pai')
        sugestao_codigo = request.GET.get('sugestao')
        
        if codigo_pai:
            try:
                conta_pai = ContaContabil.objects.get(codigo=codigo_pai)
                if sugestao_codigo:
                    form.initial['codigo'] = sugestao_codigo
                else:
                    filhos_diretos = conta_pai.get_filhos_diretos()
                    proxima_sequencia = filhos_diretos.count() + 1
                    codigo_sugerido = f"{conta_pai.codigo}.{proxima_sequencia:03d}"
                    form.initial['codigo'] = codigo_sugerido
                
                form.pai_info = {
                    'codigo': conta_pai.codigo,
                    'nome': conta_pai.nome,
                    'tipo_display': conta_pai.get_tipo_display()
                }
                logger.info(f"Criação com pai: {conta_pai.codigo} - {conta_pai.nome}")
            except ContaContabil.DoesNotExist:
                logger.warning(f'Conta pai não encontrada: {codigo_pai}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/contacontabil_form_modal.html', {
            'form': form,
            'title': 'Nova Conta Contábil',
            'is_create': True
        })
    
    context = {
        'form': form,
        'title': 'Nova Conta Contábil',
        'is_create': True
    }
    return render(request, 'gestor/contacontabil_form.html', context)

@login_required
def contacontabil_update_modal(request, codigo):
    """Editar conta contábil via modal"""
    
    conta = get_object_or_404(ContaContabil, codigo=codigo)
    
    if request.method == 'POST':
        logger.info(f"Editando conta contábil: {conta.codigo} - {conta.nome}")
        
        form = ContaContabilForm(request.POST, instance=conta)
        
        if form.is_valid():
            try:
                from django.db import transaction
                
                with transaction.atomic():
                    conta_editada = form.save()
                    logger.info(f"Conta contábil atualizada: {conta_editada.codigo} - {conta_editada.nome}")
                
                conta_verificacao = ContaContabil.objects.get(codigo=codigo)
                logger.info(f"Verificação final: {conta_verificacao.nome}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Conta contábil "{conta_verificacao.nome}" atualizada com sucesso!',
                        'conta': {
                            'codigo': conta_verificacao.codigo,
                            'nome': conta_verificacao.nome,
                            'tipo': conta_verificacao.tipo
                        }
                    })
                
                messages.success(request, f'Conta contábil "{conta_verificacao.nome}" atualizada com sucesso!')
                return redirect('gestor:contacontabil_tree')
                
            except Exception as e:
                logger.error(f"Erro ao atualizar conta contábil {conta.codigo}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erro ao atualizar conta contábil: {str(e)}'
                    })
                
                messages.error(request, f'Erro ao atualizar conta contábil: {str(e)}')
        else:
            logger.error(f"Formulário inválido para conta {conta.codigo}: {form.errors}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Dados inválidos. Verifique os campos.',
                    'errors': form.errors
                })
            messages.error(request, 'Dados inválidos. Verifique os campos.')
    
    else:
        form = ContaContabilForm(instance=conta)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/contacontabil_form_modal.html', {
            'form': form,
            'title': 'Editar Conta Contábil',
            'contacontabil': conta,
            'is_create': False
        })
    
    return render(request, 'gestor/contacontabil_form.html', {
        'form': form,
        'title': 'Editar Conta Contábil',
        'conta': conta,
        'is_create': False
    })

@login_required
@require_POST
def contacontabil_delete_ajax(request, codigo):
    """Deletar conta contábil via AJAX"""
    conta = get_object_or_404(ContaContabil, codigo=codigo)
    
    if conta.tem_filhos:
        filhos_count = conta.get_filhos_diretos().count()
        return JsonResponse({
            'success': False,
            'message': f'Não é possível excluir a conta contábil "{conta.nome}" pois ela possui {filhos_count} sub-conta(s).'
        })
    
    try:
        nome = conta.nome
        codigo_conta = conta.codigo
        conta.delete()
        
        logger.info(f'Conta contábil excluída: {codigo_conta} - {nome} por {request.user}')
        
        return JsonResponse({
            'success': True,
            'message': f'Conta contábil "{nome}" (código: {codigo_conta}) excluída com sucesso!'
        })
        
    except Exception as e:
        logger.error(f'Erro ao excluir conta contábil {conta.codigo}: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'Erro ao excluir conta contábil: {str(e)}'
        })

# ===== APIs =====

@login_required
def api_contacontabil_tree_data(request):
    """API para dados da árvore - HIERARQUIA DECLARADA"""
    
    try:
        # Obter filtros
        search = request.GET.get('search', '').strip()
        nivel = request.GET.get('nivel', '')
        tipo = request.GET.get('tipo', '')
        ativa = request.GET.get('ativa', '')
        
        # Query com filtros
        queryset = ContaContabil.objects.order_by('codigo')
        
        if ativa != '':
            queryset = queryset.filter(ativa=ativa.lower() == 'true')
        else:
            queryset = queryset.filter(ativa=True)
        
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(nome__icontains=search) |
                Q(descricao__icontains=search)
            )
        
        if nivel:
            queryset = queryset.filter(nivel=int(nivel))
        
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        # Construir árvore
        from .contacontabil_tree import construir_arvore_declarada, calcular_stats_contas
        tree_data = construir_arvore_declarada(queryset)
        stats = calcular_stats_contas(queryset)
        
        stats['filtros_aplicados'] = {
            'search': search,
            'nivel': nivel,
            'tipo': tipo,
            'ativa': ativa
        }
        
        return JsonResponse({
            'success': True,
            'tree_data': tree_data,
            'stats': stats,
            'total_sem_filtro': ContaContabil.objects.filter(ativa=True).count()
        })
        
    except Exception as e:
        logger.error(f'Erro na API de dados da árvore: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro interno do servidor',
            'message': str(e)
        })

@login_required
def api_validar_codigo_contacontabil(request):
    """API para validar código de conta contábil em tempo real - HIERARQUIA DECLARADA"""
    codigo = request.GET.get('codigo', '').strip()
    conta_codigo = request.GET.get('atual', None)
    
    if not codigo:
        return JsonResponse({'valid': False, 'error': 'Código é obrigatório'})
    
    # Verificar formato básico
    import re
    if not re.match(r'^[\d\.]+$', codigo):
        return JsonResponse({'valid': False, 'error': 'Código deve conter apenas números e pontos'})
    
    # Verificar duplicação
    query = ContaContabil.objects.filter(codigo=codigo)
    if conta_codigo:
        query = query.exclude(codigo=conta_codigo)
    
    if query.exists():
        return JsonResponse({'valid': False, 'error': 'Já existe uma conta contábil com este código'})
    
    # Para hierarquia declarada, pai será selecionado no formulário
    info = {
        'valid': True,
        'message': 'Código válido',
        'nivel': codigo.count('.') + 1
    }
    
    # Sugerir pai automaticamente baseado no código (opcional)
    if '.' in codigo:
        partes = codigo.split('.')
        codigo_pai_sugerido = '.'.join(partes[:-1])
        
        try:
            pai_sugerido = ContaContabil.objects.get(codigo=codigo_pai_sugerido, ativa=True)
            if pai_sugerido.tipo == 'S':  # Só se for sintético
                info['pai_sugerido'] = {
                    'codigo': pai_sugerido.codigo,
                    'nome': pai_sugerido.nome,
                    'tipo': pai_sugerido.tipo
                }
        except ContaContabil.DoesNotExist:
            pass
    
    return JsonResponse(info)

# ===== VIEWS MANTIDAS PARA COMPATIBILIDADE =====

@login_required
def contacontabil_list(request):
    """Redirecionar para a árvore"""
    return redirect('gestor:contacontabil_tree')

@login_required
def contacontabil_create(request):
    """Compatibilidade"""
    return contacontabil_create_modal(request)

@login_required
def contacontabil_update(request, codigo):
    """Compatibilidade"""
    return contacontabil_update_modal(request, codigo)

@login_required
def contacontabil_delete(request, codigo):
    """Compatibilidade"""
    if request.method == 'POST':
        return contacontabil_delete_ajax(request, codigo)
    return redirect('gestor:contacontabil_tree')