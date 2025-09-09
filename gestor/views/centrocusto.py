# gestor/views/centrocusto.py - CRUD corrigidas para modal

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
    """Visualização hierárquica OTIMIZADA de centros de custo"""
    
    # OTIMIZAÇÃO 1: Query única otimizada
    centros_queryset = CentroCusto.objects.filter(ativo=True).order_by('codigo')
    
    # OTIMIZAÇÃO 2: Usar o mapa de hierarquia
    def construir_arvore_otimizada():
        # Método otimizado usando mapa de hierarquia
        hierarchy_map, root_items = CentroCusto.build_hierarchy_map(centros_queryset)
        
        def construir_no_otimizado(centro):
            children_data = hierarchy_map.get(centro.codigo, {}).get('children', [])
            
            return {
                'codigo': centro.codigo,
                'nome': centro.nome,
                'tipo': centro.tipo,
                'nivel': centro.nivel,
                'ativo': centro.ativo,
                'descricao': centro.descricao,
                'tem_filhos': len(children_data) > 0,
                'data_criacao': centro.data_criacao.isoformat() if centro.data_criacao else None,
                'data_alteracao': centro.data_alteracao.isoformat() if centro.data_alteracao else None,
                'filhos': [construir_no_otimizado(filho) for filho in sorted(children_data, key=lambda x: x.codigo)]
            }
        
        return [construir_no_otimizado(raiz) for raiz in sorted(root_items, key=lambda x: x.codigo)]
    
    # OTIMIZAÇÃO 3: Calcular stats em uma passada
    def calcular_stats_otimizado():
        centros_list = list(centros_queryset)  # Uma única conversão
        total_centros = len(centros_list)
        
        # Contadores em uma única iteração
        stats_data = {
            'total': total_centros,
            'tipo_s': 0,
            'tipo_a': 0,
            'contas_por_nivel': {},
            'niveis_existentes': set()
        }
        
        for centro in centros_list:
            # Contar por tipo (baseado no campo, não em cálculo)
            if centro.tipo == 'S':
                stats_data['tipo_s'] += 1
            else:
                stats_data['tipo_a'] += 1
            
            # Contar por nível
            nivel = centro.nivel
            stats_data['niveis_existentes'].add(nivel)
            stats_data['contas_por_nivel'][str(nivel)] = stats_data['contas_por_nivel'].get(str(nivel), 0) + 1
        
        # Finalizar
        niveis_list = sorted(stats_data['niveis_existentes'])
        stats_data.update({
            'nivel_max': max(niveis_list) if niveis_list else 0,
            'nivel_min': min(niveis_list) if niveis_list else 0,
            'niveis_existentes': niveis_list
        })
        
        return stats_data
    
    try:
        tree_data = construir_arvore_otimizada()
        stats = calcular_stats_otimizado()
        
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
            # ... resto do context
        }
        return render(request, 'gestor/centrocusto_tree_main.html', context)




# ===== VIEWS MODAIS =====

# gestor/views/centrocusto.py - View de edição corrigida (substituir apenas esta função)

@login_required
def centrocusto_update_modal(request, codigo):
    """Editar centro de custo via modal - VERSÃO CORRIGIDA"""
    
    centro = get_object_or_404(CentroCusto, codigo=codigo)
    
    if request.method == 'POST':
        logger.info(f"Editando centro de custo: {centro.codigo} - {centro.nome}")
        
        form = CentroCustoForm(request.POST, instance=centro)
        
        if form.is_valid():
            try:
                # USAR TRANSACTION EXPLÍCITA
                from django.db import transaction
                
                with transaction.atomic():
                    # Save normal
                    centro_editado = form.save()
                    logger.info(f"Centro de custo atualizado: {centro_editado.codigo} - {centro_editado.nome}")
                
                # Verificação simples após transação
                centro_verificacao = CentroCusto.objects.get(codigo=codigo)
                logger.info(f"Verificação final: {centro_verificacao.nome}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Centro de custo "{centro_verificacao.nome}" atualizado com sucesso!',
                        'centro': {
                            'codigo': centro_verificacao.codigo,
                            'nome': centro_verificacao.nome,
                            'tipo': centro_verificacao.tipo
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

# gestor/views/centrocusto.py - View de criação corrigida (substituir apenas esta função)

@login_required
def centrocusto_create_modal(request):
    """Criar novo centro de custo via modal - VERSÃO CORRIGIDA"""
    
    if request.method == 'POST':
        logger.info(f"Criando novo centro de custo")
        logger.info(f"POST data recebido: {dict(request.POST)}")
        
        form = CentroCustoForm(request.POST)
        
        if form.is_valid():
            logger.info(f"Formulário válido. Dados: {form.cleaned_data}")
            
            try:
                # USAR TRANSACTION EXPLÍCITA
                from django.db import transaction
                
                with transaction.atomic():
                    # Save normal
                    centro = form.save()
                    logger.info(f"Centro de custo criado: {centro.codigo} - {centro.nome}")
                
                # Verificação simples após transação
                centro_verificacao = CentroCusto.objects.get(codigo=centro.codigo)
                logger.info(f"Verificação: centro criado com sucesso - {centro_verificacao.nome}")
                
                # Resposta de sucesso
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Centro de custo "{centro_verificacao.nome}" criado com sucesso!',
                        'centro': {
                            'codigo': centro_verificacao.codigo,
                            'nome': centro_verificacao.nome,
                            'tipo': centro_verificacao.tipo,
                            'nivel': centro_verificacao.nivel
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
        form = CentroCustoForm()
        
        # Pré-preencher se veio de um pai
        codigo_pai = request.GET.get('codigo_pai')
        sugestao_codigo = request.GET.get('sugestao')
        
        if codigo_pai:
            try:
                centro_pai = CentroCusto.objects.get(codigo=codigo_pai)
                if sugestao_codigo:
                    form.initial['codigo'] = sugestao_codigo
                else:
                    # Sugerir próximo código
                    filhos_diretos = centro_pai.get_filhos_diretos()
                    proxima_sequencia = filhos_diretos.count() + 1
                    codigo_sugerido = f"{centro_pai.codigo}.{proxima_sequencia:02d}"
                    form.initial['codigo'] = codigo_sugerido
                
                # Informações do pai para o template
                form.pai_info = {
                    'codigo': centro_pai.codigo,
                    'nome': centro_pai.nome,
                    'tipo_display': centro_pai.get_tipo_display()
                }
                logger.info(f"Criação com pai: {centro_pai.codigo} - {centro_pai.nome}")
            except CentroCusto.DoesNotExist:
                logger.warning(f'Centro pai não encontrado: {codigo_pai}')
    
    # Renderizar modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/centrocusto_form_modal.html', {
            'form': form,
            'title': 'Novo Centro de Custo',
            'is_create': True
        })
    
    # Fallback para requisições não-AJAX
    context = {
        'form': form,
        'title': 'Novo Centro de Custo',
        'is_create': True
    }
    return render(request, 'gestor/centrocusto_form.html', context)


@login_required
@require_POST
def centrocusto_delete_ajax(request, codigo):
    """Deletar centro de custo via AJAX"""
    centro = get_object_or_404(CentroCusto, codigo=codigo)
    
    # Verificar se tem filhos
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
    """API OTIMIZADA para dados da árvore de centros de custo"""
    
    try:
        # Obter filtros
        search = request.GET.get('search', '').strip()
        nivel = request.GET.get('nivel', '')
        tipo = request.GET.get('tipo', '')
        ativo = request.GET.get('ativo', '')
        
        # OTIMIZAÇÃO: Query única com todos os filtros
        queryset = CentroCusto.objects.order_by('codigo')
        
        # Aplicar filtros no banco de dados
        if ativo != '':
            queryset = queryset.filter(ativo=ativo.lower() == 'true')
        else:
            queryset = queryset.filter(ativo=True)
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(nome__icontains=search) |
                Q(descricao__icontains=search)
            )
        
        if nivel:
            queryset = queryset.filter(nivel=int(nivel))
        
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        # OTIMIZAÇÃO: Usar mapa de hierarquia para dados filtrados
        hierarchy_map, root_items = CentroCusto.build_hierarchy_map(queryset)
        
        def construir_no_api(centro):
            children_data = hierarchy_map.get(centro.codigo, {}).get('children', [])
            
            return {
                'codigo': centro.codigo,
                'nome': centro.nome,
                'tipo': centro.tipo,
                'nivel': centro.nivel,
                'ativo': centro.ativo,
                'descricao': centro.descricao,
                'tem_filhos': len(children_data) > 0,
                'filhos': [construir_no_api(filho) for filho in sorted(children_data, key=lambda x: x.codigo)]
            }
        
        tree_data = [construir_no_api(raiz) for raiz in sorted(root_items, key=lambda x: x.codigo)]
        
        # Stats dos dados filtrados
        centros_filtrados = list(queryset)
        total_filtrados = len(centros_filtrados)
        sinteticos = sum(1 for c in centros_filtrados if c.tipo == 'S')
        analiticos = total_filtrados - sinteticos
        
        stats = {
            'total': total_filtrados,
            'tipo_s': sinteticos,
            'tipo_a': analiticos,
            'nivel_max': max([c.nivel for c in centros_filtrados]) if centros_filtrados else 0,
            'filtros_aplicados': {
                'search': search,
                'nivel': nivel,
                'tipo': tipo,
                'ativo': ativo
            }
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

# ===== VIEWS MANTIDAS PARA COMPATIBILIDADE =====

@login_required
def centrocusto_list(request):
    """Lista de centros de custo com filtros - mantida para compatibilidade"""
    # Redirecionar para a árvore
    return redirect('gestor:centrocusto_tree')

@login_required
def centrocusto_create(request):
    """Criar novo centro de custo - mantida para compatibilidade"""
    return centrocusto_create_modal(request)

@login_required
def centrocusto_update(request, codigo):
    """Editar centro de custo - mantida para compatibilidade"""
    return centrocusto_update_modal(request, codigo)

@login_required
def centrocusto_delete(request, codigo):
    """Deletar centro de custo - mantida para compatibilidade"""
    if request.method == 'POST':
        return centrocusto_delete_ajax(request, codigo)
    
    # Para GET, redirecionar para árvore
    return redirect('gestor:centrocusto_tree')

@login_required
def api_validar_codigo_centrocusto(request):
    """API para validar código de centro de custo em tempo real"""
    codigo = request.GET.get('codigo', '').strip()
    centro_codigo = request.GET.get('atual', None)
    
    if not codigo:
        return JsonResponse({'valid': False, 'error': 'Código é obrigatório'})
    
    # Verificar formato
    import re
    if not re.match(r'^[\d\.]+$', codigo):
        return JsonResponse({'valid': False, 'error': 'Código deve conter apenas números e pontos'})
    
    # Verificar duplicação
    query = CentroCusto.objects.filter(codigo=codigo)
    if centro_codigo:
        query = query.exclude(codigo=centro_codigo)
    
    if query.exists():
        return JsonResponse({'valid': False, 'error': 'Já existe um centro de custo com este código'})
    
    # Verificar hierarquia
    info = {'valid': True}
    
    if '.' in codigo:
        temp_centro = CentroCusto(codigo=codigo)
        pai = temp_centro.encontrar_pai_hierarquico()
        
        if pai:
            info['pai'] = {
                'codigo': pai.codigo,
                'nome': pai.nome,
                'tipo_display': pai.get_tipo_display()
            }
        else:
            partes = codigo.split('.')
            codigo_pai = '.'.join(partes[:-1])
            info['valid'] = False
            info['error'] = f'Centro de custo pai com código "{codigo_pai}" não existe'
    else:
        info['pai'] = None
    
    # Calcular nível
    info['nivel'] = codigo.count('.') + 1
    
    return JsonResponse(info)
