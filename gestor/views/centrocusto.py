# gestor/views/centrocusto.py - CORRIGIDO PARA HIERARQUIA DECLARADA

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import logging
import json

from core.models import CentroCusto
from core.forms import CentroCustoForm

logger = logging.getLogger('synchrobi')

# ===== VIEW PRINCIPAL DA ÁRVORE =====

@login_required
def centrocusto_tree_view(request):
    """Visualização hierárquica de centros de custo - HIERARQUIA DECLARADA"""
    
    try:
        # Query única otimizada
        centros_queryset = CentroCusto.objects.filter(ativo=True).order_by('codigo')
        
        # Construir árvore usando hierarquia declarada
        tree_data = construir_arvore_declarada(centros_queryset)
        
        # Calcular stats
        stats = calcular_stats_centros(centros_queryset)
        
        context = {
            'tree_data_json': json.dumps(tree_data, ensure_ascii=False, indent=2),
            'stats': stats,
            'entity_name': 'Centros de Custo',
            'entity_singular': 'Centro de Custo',
            'create_url': 'gestor:centrocusto_create_modal',
            'update_url_base': '/gestor/centros-custo/',
            'tree_url': 'gestor:centrocusto_tree',
            'api_tree_data_url': 'gestor:api_centrocusto_tree_data',
            'breadcrumb': 'Centros de Custo',
            'icon': 'fa-bullseye'
        }
        
        return render(request, 'gestor/centrocusto_tree_main.html', context)
        
    except Exception as e:
        logger.error(f'Erro na construção da árvore de centros de custo: {str(e)}')
        
        # Fallback simples
        context = {
            'tree_data_json': '[]',
            'stats': {'total': 0, 'tipo_s': 0, 'tipo_a': 0},
            'error_message': 'Erro ao carregar árvore de centros de custo',
            'entity_name': 'Centros de Custo',
            'entity_singular': 'Centro de Custo',
            'create_url': 'gestor:centrocusto_create_modal',
            'update_url_base': '/gestor/centros-custo/',
            'tree_url': 'gestor:centrocusto_tree',
            'api_tree_data_url': 'gestor:api_centrocusto_tree_data',
            'breadcrumb': 'Centros de Custo',
            'icon': 'fa-bullseye'
        }
        return render(request, 'gestor/centrocusto_tree_main.html', context)

# ===== VIEWS MODAIS =====

@login_required
def centrocusto_update_modal(request, codigo):
    """Editar centro de custo via modal - HIERARQUIA DECLARADA"""
    
    centro = get_object_or_404(CentroCusto, codigo=codigo)
    
    if request.method == 'POST':
        logger.info(f"Editando centro de custo: {centro.codigo} - {centro.nome}")
        
        form = CentroCustoForm(request.POST, instance=centro)
        
        if form.is_valid():
            try:
                from django.db import transaction
                
                with transaction.atomic():
                    centro_editado = form.save()
                    logger.info(f"Centro de custo atualizado: {centro_editado.codigo} - {centro_editado.nome}")
                
                centro_verificacao = CentroCusto.objects.get(codigo=codigo)
                logger.info(f"Verificação final: {centro_verificacao.nome}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Centro de custo "{centro_verificacao.nome}" atualizado com sucesso!',
                        'centro': {
                            'codigo': centro_verificacao.codigo,
                            'nome': centro_verificacao.nome,
                            'tipo': centro_verificacao.tipo,
                            'codigo_pai': centro_verificacao.codigo_pai or ''
                        }
                    })
                
                messages.success(request, f'Centro de custo "{centro_verificacao.nome}" atualizado com sucesso!')
                return redirect('gestor:centrocusto_tree')
                
            except Exception as e:
                logger.error(f"Erro ao atualizar centro de custo {centro.codigo}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erro ao atualizar centro de custo: {str(e)}'
                    })
                
                messages.error(request, f'Erro ao atualizar centro de custo: {str(e)}')
        else:
            logger.error(f"Formulário inválido para centro {centro.codigo}: {form.errors}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Dados inválidos. Verifique os campos.',
                    'errors': form.errors
                })
            messages.error(request, 'Dados inválidos. Verifique os campos.')
    
    else:
        form = CentroCustoForm(instance=centro)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/centrocusto_form_modal.html', {
            'form': form,
            'title': 'Editar Centro de Custo',
            'centrocusto': centro,
            'is_create': False
        })
    
    return render(request, 'gestor/centrocusto_form.html', {
        'form': form,
        'title': 'Editar Centro de Custo',
        'centro': centro,
        'is_create': False
    })

@login_required
def centrocusto_create_modal(request):
    """Criar novo centro de custo via modal - HIERARQUIA DECLARADA"""
    
    if request.method == 'POST':
        logger.info(f"Criando novo centro de custo")
        logger.info(f"POST data recebido: {dict(request.POST)}")
        
        form = CentroCustoForm(request.POST)
        
        if form.is_valid():
            logger.info(f"Formulário válido. Dados: {form.cleaned_data}")
            
            try:
                from django.db import transaction
                
                with transaction.atomic():
                    centro = form.save()
                    logger.info(f"Centro de custo criado: {centro.codigo} - {centro.nome} (Pai: {centro.codigo_pai or 'Raiz'})")
                
                centro_verificacao = CentroCusto.objects.get(codigo=centro.codigo)
                logger.info(f"Verificação: centro criado com sucesso - {centro_verificacao.nome}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Centro de custo "{centro_verificacao.nome}" criado com sucesso!',
                        'centro': {
                            'codigo': centro_verificacao.codigo,
                            'nome': centro_verificacao.nome,
                            'tipo': centro_verificacao.tipo,
                            'nivel': centro_verificacao.nivel,
                            'codigo_pai': centro_verificacao.codigo_pai or ''
                        }
                    })
                
                messages.success(request, f'Centro de custo "{centro_verificacao.nome}" criado com sucesso!')
                return redirect('gestor:centrocusto_tree')
                
            except Exception as e:
                logger.error(f"Erro ao criar centro de custo: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erro ao criar centro de custo: {str(e)}'
                    })
                
                messages.error(request, f'Erro ao criar centro de custo: {str(e)}')
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
        # GET request - mostrar formulário
        initial_data = {}
        
        # Pré-preencher se veio de um pai
        codigo_pai = request.GET.get('codigo_pai')
        if codigo_pai:
            initial_data['codigo_pai'] = codigo_pai
            
            try:
                centro_pai = CentroCusto.objects.get(codigo=codigo_pai)
                logger.info(f"Criação com pai: {centro_pai.codigo} - {centro_pai.nome}")
            except CentroCusto.DoesNotExist:
                logger.warning(f'Centro pai não encontrado: {codigo_pai}')
        
        form = CentroCustoForm(initial=initial_data)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/centrocusto_form_modal.html', {
            'form': form,
            'title': 'Novo Centro de Custo',
            'is_create': True
        })
    
    context = {
        'form': form,
        'title': 'Novo Centro de Custo',
        'is_create': True
    }
    return render(request, 'gestor/centrocusto_form.html', context)

@login_required
@require_POST
def centrocusto_delete_ajax(request, codigo):
    """Deletar centro de custo via AJAX - HIERARQUIA DECLARADA"""
    centro = get_object_or_404(CentroCusto, codigo=codigo)
    
    # Verificar se tem filhos usando hierarquia declarada
    if centro.tem_filhos:
        filhos_count = centro.get_filhos_diretos().count()
        return JsonResponse({
            'success': False,
            'message': f'Não é possível excluir o centro de custo "{centro.nome}" pois ele possui {filhos_count} sub-centro(s).'
        })
    
    try:
        nome = centro.nome
        codigo_centro = centro.codigo
        centro.delete()
        
        logger.info(f'Centro de custo excluído: {codigo_centro} - {nome} por {request.user}')
        
        return JsonResponse({
            'success': True,
            'message': f'Centro de custo "{nome}" (código: {codigo_centro}) excluído com sucesso!'
        })
        
    except Exception as e:
        logger.error(f'Erro ao excluir centro de custo {centro.codigo}: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'Erro ao excluir centro de custo: {str(e)}'
        })

# ===== APIs =====

@login_required
def api_centrocusto_tree_data(request):
    """API para dados da árvore - HIERARQUIA DECLARADA"""
    
    try:
        # Obter filtros
        search = request.GET.get('search', '').strip()
        nivel = request.GET.get('nivel', '')
        tipo = request.GET.get('tipo', '')
        ativo = request.GET.get('ativo', '')
        
        # Query com filtros
        queryset = CentroCusto.objects.order_by('codigo')
        
        if ativo != '':
            queryset = queryset.filter(ativo=ativo.lower() == 'true')
        else:
            queryset = queryset.filter(ativo=True)
        
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
        tree_data = construir_arvore_declarada(queryset)
        
        # Stats
        stats = calcular_stats_centros(queryset)
        stats['filtros_aplicados'] = {
            'search': search,
            'nivel': nivel,
            'tipo': tipo,
            'ativo': ativo
        }
        
        return JsonResponse({
            'success': True,
            'tree_data': tree_data,
            'stats': stats,
            'total_sem_filtro': CentroCusto.objects.filter(ativo=True).count()
        })
        
    except Exception as e:
        logger.error(f'Erro na API de dados da árvore: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro interno do servidor',
            'message': str(e)
        })

@login_required
def api_validar_codigo_centrocusto(request):
    """API para validar código - HIERARQUIA DECLARADA"""
    codigo = request.GET.get('codigo', '').strip()
    centro_codigo = request.GET.get('atual', None)
    
    if not codigo:
        return JsonResponse({'valid': False, 'error': 'Código é obrigatório'})
    
    # Verificar formato básico
    import re
    if not re.match(r'^[\w\.-]+$', codigo):
        return JsonResponse({'valid': False, 'error': 'Código deve conter apenas letras, números, pontos e hífens'})
    
    # Verificar duplicação
    query = CentroCusto.objects.filter(codigo=codigo)
    if centro_codigo:
        query = query.exclude(codigo=centro_codigo)
    
    if query.exists():
        return JsonResponse({'valid': False, 'error': 'Já existe um centro de custo com este código'})
    
    # Para hierarquia declarada, pai será selecionado no formulário
    info = {
        'valid': True,
        'message': 'Código válido'
    }
    
    return JsonResponse(info)

# ===== FUNÇÕES AUXILIARES =====

def construir_arvore_declarada(queryset):
    """Constrói árvore hierárquica usando campo codigo_pai"""
    
    centros_list = list(queryset)
    centros_dict = {centro.codigo: centro for centro in centros_list}
    
    # Mapear filhos por pai
    filhos_por_pai = {}
    centros_raiz = []
    
    for centro in centros_list:
        if centro.codigo_pai:
            # Tem pai - adicionar à lista de filhos do pai
            if centro.codigo_pai not in filhos_por_pai:
                filhos_por_pai[centro.codigo_pai] = []
            filhos_por_pai[centro.codigo_pai].append(centro)
        else:
            # É raiz
            centros_raiz.append(centro)
    
    def construir_no(centro):
        """Constrói um nó da árvore recursivamente"""
        filhos = filhos_por_pai.get(centro.codigo, [])
        filhos_ordenados = sorted(filhos, key=lambda x: x.codigo)
        
        return {
            'codigo': centro.codigo,
            'nome': centro.nome,
            'tipo': centro.tipo,
            'nivel': centro.nivel,
            'ativo': centro.ativo,
            'descricao': centro.descricao,
            'codigo_pai': centro.codigo_pai or '',
            'tem_filhos': len(filhos) > 0,
            'data_criacao': centro.data_criacao.isoformat() if centro.data_criacao else None,
            'data_alteracao': centro.data_alteracao.isoformat() if centro.data_alteracao else None,
            'filhos': [construir_no(filho) for filho in filhos_ordenados]
        }
    
    # Construir árvore a partir das raízes
    centros_raiz_ordenados = sorted(centros_raiz, key=lambda x: x.codigo)
    return [construir_no(raiz) for raiz in centros_raiz_ordenados]

def calcular_stats_centros(queryset):
    """Calcula estatísticas dos centros de custo"""
    centros_list = list(queryset)
    total = len(centros_list)
    
    if total == 0:
        return {
            'total': 0,
            'tipo_s': 0,
            'tipo_a': 0,
            'nivel_max': 0,
            'contas_por_nivel': {}
        }
    
    # Contadores
    tipo_s = sum(1 for c in centros_list if c.tipo == 'S')
    tipo_a = sum(1 for c in centros_list if c.tipo == 'A')
    
    # Níveis
    niveis = [c.nivel for c in centros_list]
    nivel_max = max(niveis)
    nivel_min = min(niveis)
    
    # Contar por nível
    contas_por_nivel = {}
    for nivel in range(nivel_min, nivel_max + 1):
        count = sum(1 for n in niveis if n == nivel)
        contas_por_nivel[str(nivel)] = count
    
    return {
        'total': total,
        'tipo_s': tipo_s,
        'tipo_a': tipo_a,
        'nivel_max': nivel_max,
        'nivel_min': nivel_min,
        'contas_por_nivel': contas_por_nivel,
        'niveis_existentes': sorted(list(set(niveis)))
    }

# ===== VIEWS MANTIDAS PARA COMPATIBILIDADE =====

@login_required
def centrocusto_list(request):
    """Lista de centros de custo - redireciona para árvore"""
    return redirect('gestor:centrocusto_tree')

@login_required
def centrocusto_create(request):
    """Criar centro de custo - compatibilidade"""
    return centrocusto_create_modal(request)

@login_required
def centrocusto_update(request, codigo):
    """Editar centro de custo - compatibilidade"""
    return centrocusto_update_modal(request, codigo)

@login_required
def centrocusto_delete(request, codigo):
    """Deletar centro de custo - compatibilidade"""
    if request.method == 'POST':
        return centrocusto_delete_ajax(request, codigo)
    return redirect('gestor:centrocusto_tree')

@login_required
def api_centro_custo_detalhes(request, codigo):
    """API para obter detalhes de um centro de custo"""
    try:
        centro = get_object_or_404(CentroCusto, codigo=codigo, ativo=True)
        
        return JsonResponse({
            'success': True,
            'centro': {
                'codigo': centro.codigo,
                'nome': centro.nome,
                'tipo': centro.tipo,
                'nivel': centro.nivel,
                'ativo': centro.ativo,
                'descricao': centro.descricao,
                'codigo_pai': centro.codigo_pai or '',
                'tem_filhos': centro.tem_filhos
            }
        })
        
    except Exception as e:
        logger.error(f'Erro ao buscar detalhes do centro {codigo}: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Centro de custo não encontrado'
        })