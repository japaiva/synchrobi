# gestor/views/unidade.py - CRUD via modais (sem view principal)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import logging
import json

from core.models import Unidade
from core.forms import UnidadeForm

logger = logging.getLogger('synchrobi')

@login_required
def unidade_create_modal(request):
    """Criar nova unidade via modal"""
    if request.method == 'POST':
        form = UnidadeForm(request.POST)
        if form.is_valid():
            try:
                unidade = form.save()
                
                # Resposta para AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Unidade "{unidade.nome}" criada com sucesso!',
                        'unidade': {
                            'id': unidade.id,
                            'codigo': unidade.codigo,
                            'nome': unidade.nome,
                            'tipo': unidade.tipo,
                            'nivel': unidade.nivel
                        }
                    })
                
                messages.success(request, f'Unidade "{unidade.nome}" criada com sucesso!')
                return redirect('gestor:unidade_tree')
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erro ao criar unidade: {str(e)}',
                        'errors': form.errors
                    })
                messages.error(request, f'Erro ao criar unidade: {str(e)}')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Erro ao criar unidade. Verifique os dados.',
                    'errors': form.errors
                })
    else:
        form = UnidadeForm()
        
        # Pré-preencher se veio de um pai
        codigo_pai = request.GET.get('codigo_pai')
        sugestao_codigo = request.GET.get('sugestao')
        
        if codigo_pai:
            try:
                unidade_pai = Unidade.objects.get(codigo=codigo_pai)
                if sugestao_codigo:
                    form.initial['codigo'] = sugestao_codigo
                else:
                    filhos_diretos = unidade_pai.get_filhos_diretos()
                    proxima_sequencia = filhos_diretos.count() + 1
                    codigo_sugerido = f"{unidade_pai.codigo}.{proxima_sequencia:02d}"
                    form.initial['codigo'] = codigo_sugerido
                
                form.pai_info = {
                    'codigo': unidade_pai.codigo,
                    'nome': unidade_pai.nome
                }
            except Unidade.DoesNotExist:
                pass
    
    # Renderizar modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/unidade_form_modal.html', {
            'form': form,
            'title': 'Nova Unidade',
            'is_create': True
        })
    
    # Fallback para requisições não-AJAX
    context = {
        'form': form,
        'title': 'Nova Unidade',
        'is_create': True
    }
    return render(request, 'gestor/unidade_form.html', context)

@login_required
def unidade_update_modal(request, pk):
    """Editar unidade via modal"""
    unidade = get_object_or_404(Unidade, pk=pk)
    
    if request.method == 'POST':
        form = UnidadeForm(request.POST, instance=unidade)
        if form.is_valid():
            try:
                unidade_atualizada = form.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Unidade "{unidade_atualizada.nome}" atualizada com sucesso!',
                        'unidade': {
                            'id': unidade_atualizada.id,
                            'codigo': unidade_atualizada.codigo,
                            'nome': unidade_atualizada.nome,
                            'tipo': unidade_atualizada.tipo,
                            'nivel': unidade_atualizada.nivel
                        }
                    })
                
                messages.success(request, f'Unidade "{unidade_atualizada.nome}" atualizada com sucesso!')
                return redirect('gestor:unidade_tree')
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erro ao atualizar unidade: {str(e)}',
                        'errors': form.errors
                    })
                messages.error(request, f'Erro ao atualizar unidade: {str(e)}')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Erro ao atualizar unidade. Verifique os dados.',
                    'errors': form.errors
                })
    else:
        form = UnidadeForm(instance=unidade)
    
    # Renderizar modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/unidade_form_modal.html', {
            'form': form,
            'title': 'Editar Unidade',
            'unidade': unidade,
            'is_create': False
        })
    
    # Fallback para requisições não-AJAX
    context = {
        'form': form,
        'title': 'Editar Unidade',
        'unidade': unidade,
        'is_create': False
    }
    return render(request, 'gestor/unidade_form.html', context)

@login_required
def unidade_detail_modal(request, pk):
    """Detalhes da unidade via modal"""
    unidade = get_object_or_404(Unidade, pk=pk)
    
    # Informações hierárquicas - CORRIGIDO para hierarquia declarada
    sub_unidades = unidade.get_filhos_diretos().order_by('codigo')
    caminho = unidade.get_caminho_completo()  # ✓ Método correto
    total_descendentes = len(unidade.get_todos_filhos())  # ✓ Método correto
    unidades_operacionais = sub_unidades.filter(tipo='A').count()  # ✓ Lógica simples
    
    context = {
        'unidade': unidade,
        'sub_unidades': sub_unidades,
        'caminho': caminho,
        'total_descendentes': total_descendentes,
        'unidades_operacionais': unidades_operacionais,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/unidade_detail_modal.html', context)
    
    # Fallback - redirecionar para árvore
    return redirect('gestor:unidade_tree')

@login_required
@require_POST
def unidade_delete_ajax(request, pk):
    """Deletar unidade via AJAX"""
    unidade = get_object_or_404(Unidade, pk=pk)
    
    # Verificar se tem filhos
    if unidade.tem_filhos:
        filhos_count = unidade.get_filhos_diretos().count()
        return JsonResponse({
            'success': False,
            'message': f'Não é possível excluir a unidade "{unidade.nome}" pois ela possui {filhos_count} sub-unidade(s).'
        })
    
    try:
        nome = unidade.nome
        codigo = unidade.codigo
        unidade.delete()
        
        logger.info(f'Unidade excluída: {codigo} - {nome} por {request.user}')
        
        return JsonResponse({
            'success': True,
            'message': f'Unidade "{nome}" (código: {codigo}) excluída com sucesso!'
        })
        
    except Exception as e:
        logger.error(f'Erro ao excluir unidade {unidade.codigo}: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'Erro ao excluir unidade: {str(e)}'
        })

# ===== API ENDPOINTS BÁSICAS =====

@login_required
def api_unidade_tree_data(request):
    """API básica para dados atualizados da árvore"""
    try:
        unidades = Unidade.objects.filter(ativa=True).select_related('empresa').order_by('codigo')
        
        def construir_no(unidade):
            filhos_diretos = unidade.get_filhos_diretos()
            return {
                'id': unidade.id,
                'codigo': unidade.codigo,
                'codigo_allstrategy': unidade.codigo_allstrategy,
                'nome': unidade.nome,
                'tipo': unidade.tipo,
                'nivel': unidade.nivel,
                'ativa': unidade.ativa,
                'empresa_sigla': unidade.empresa.sigla if unidade.empresa else '',
                'descricao': unidade.descricao,
                'tem_filhos': unidade.tem_filhos,
                'filhos': [construir_no(filho) for filho in filhos_diretos.order_by('codigo')]
            }
        
        raizes = [u for u in unidades if u.nivel == 1]
        arvore_data = [construir_no(raiz) for raiz in raizes]
        
        # Estatísticas
        total_unidades = len(list(unidades))
        unidades_sinteticas = sum(1 for u in unidades if u.tem_filhos)
        unidades_analiticas = total_unidades - unidades_sinteticas
        
        return JsonResponse({
            'success': True,
            'tree_data': arvore_data,
            'stats': {
                'total': total_unidades,
                'tipo_s': unidades_sinteticas,
                'tipo_a': unidades_analiticas,
            }
        })
        
    except Exception as e:
        logger.error(f'Erro na API básica de dados da árvore: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro interno'
        })

@login_required
def api_validar_codigo(request):
    """API para validar código de unidade em tempo real - HIERARQUIA DECLARADA"""
    codigo = request.GET.get('codigo', '').strip()
    unidade_id = request.GET.get('id', None)
    
    if not codigo:
        return JsonResponse({'valid': False, 'error': 'Código é obrigatório'})
    
    # Verificar formato
    import re
    if not re.match(r'^[\d\.]+$', codigo):
        return JsonResponse({'valid': False, 'error': 'Código deve conter apenas números e pontos'})
    
    # Verificar duplicação
    query = Unidade.objects.filter(codigo=codigo)
    if unidade_id:
        query = query.exclude(id=unidade_id)
    
    if query.exists():
        return JsonResponse({'valid': False, 'error': 'Já existe uma unidade com este código'})
    
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
            pai_sugerido = Unidade.objects.get(codigo=codigo_pai_sugerido, ativa=True)
            info['pai_sugerido'] = {
                'codigo': pai_sugerido.codigo,
                'nome': pai_sugerido.nome,
                'tipo': pai_sugerido.tipo
            }
        except Unidade.DoesNotExist:
            pass
    
    return JsonResponse(info)

@login_required
def api_buscar_unidade_multiplos_criterios(request):
    """
    API para busca de unidades por múltiplos critérios incluindo código All Strategy
    """
    search_term = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    apenas_ativas = request.GET.get('ativas_only', 'true').lower() == 'true'
    
    if not search_term or len(search_term) < 1:
        return JsonResponse({'success': False, 'message': 'Termo de busca é obrigatório'})
    
    try:
        from django.db.models import Q
        
        queryset = Unidade.objects.select_related('empresa')
        if apenas_ativas:
            queryset = queryset.filter(ativa=True)
        
        # Busca por código, All Strategy, nome e descrição
        filtros = (
            Q(codigo__icontains=search_term) |
            Q(codigo_allstrategy__icontains=search_term) |
            Q(nome__icontains=search_term) |
            Q(descricao__icontains=search_term)
        )
        
        unidades = queryset.filter(filtros).order_by('nivel', 'codigo')[:limit]
        
        results = []
        for unidade in unidades:
            caminho = unidade.get_caminho_completo()  # ✓ CORRIGIDO
            caminho_texto = ' > '.join([f"{u.codigo_display}" for u in caminho])
            
            results.append({
                'id': unidade.id,
                'codigo': unidade.codigo,
                'codigo_allstrategy': unidade.codigo_allstrategy,
                'codigo_display': unidade.codigo_display,
                'nome': unidade.nome,
                'tipo_display': unidade.get_tipo_display(),
                'nivel': unidade.nivel,
                'empresa_sigla': unidade.empresa.sigla if unidade.empresa else '',
                'caminho_hierarquico': caminho_texto,
                'tem_filhos': unidade.tem_filhos
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'total_found': len(results),
            'has_more': len(results) == limit
        })
        
    except Exception as e:
        logger.error(f'Erro na busca de unidades: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Erro na busca'})

@login_required
def api_buscar_unidade_para_movimento(request):
    """
    API específica para buscar unidade durante importação - prioriza All Strategy
    """
    codigo_unidade = request.GET.get('codigo', '').strip()
    
    if not codigo_unidade:
        return JsonResponse({'success': False, 'error': 'Código da unidade é obrigatório'})
    
    try:
        unidade = Unidade.buscar_unidade_para_movimento(codigo_unidade)
        
        if unidade:
            return JsonResponse({
                'success': True,
                'unidade': {
                    'id': unidade.id,
                    'codigo': unidade.codigo,
                    'codigo_allstrategy': unidade.codigo_allstrategy,
                    'nome': unidade.nome,
                    'tipo_display': unidade.get_tipo_display()
                },
                'encontrado_por': 'codigo_allstrategy' if unidade.codigo_allstrategy == codigo_unidade else 'codigo_normal'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unidade não encontrada para código: {codigo_unidade}'
            })
            
    except Exception as e:
        logger.error(f'Erro ao buscar unidade para movimento: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Erro interno'})