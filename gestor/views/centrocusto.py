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


# gestor/views/centrocusto.py - View de criação com debug detalhado

@login_required
def centrocusto_create_modal(request):
    """Criar novo centro de custo via modal - COM DEBUG"""
    
    if request.method == 'POST':
        # Debug: logs dos dados recebidos
        logger.info(f"=== INÍCIO DEBUG CENTRO CUSTO ===")
        logger.info(f"POST data: {request.POST}")
        logger.info(f"User: {request.user}")
        logger.info(f"AJAX request: {request.headers.get('X-Requested-With')}")
        
        form = CentroCustoForm(request.POST)
        
        # Debug: verificar se form é válido
        logger.info(f"Form is_valid: {form.is_valid()}")
        
        if not form.is_valid():
            logger.error(f"Form errors: {form.errors}")
            logger.error(f"Form non_field_errors: {form.non_field_errors()}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Dados inválidos. Verifique os campos.',
                    'errors': form.errors
                })
            else:
                messages.error(request, 'Dados inválidos. Verifique os campos.')
        else:
            # Form é válido, tentar salvar
            try:
                logger.info("Form válido, tentando salvar...")
                
                # Debug: dados limpos
                logger.info(f"Cleaned data: {form.cleaned_data}")
                
                # Salvar sem commit primeiro para debug
                centro = form.save(commit=False)
                logger.info(f"Centro criado em memória: {centro}")
                logger.info(f"Centro código: {centro.codigo}")
                logger.info(f"Centro nome: {centro.nome}")
                logger.info(f"Centro tipo: {centro.tipo}")
                
                # Tentar validação manual
                try:
                    centro.full_clean()
                    logger.info("Validação manual passou")
                except Exception as validation_error:
                    logger.error(f"Erro na validação manual: {validation_error}")
                    raise validation_error
                
                # Tentar salvar
                centro.save()
                logger.info(f"Centro salvo com sucesso! PK: {centro.pk}")
                
                # Verificar se realmente foi salvo
                centro_verificacao = CentroCusto.objects.get(codigo=centro.codigo)
                logger.info(f"Verificação: centro encontrado no banco: {centro_verificacao}")
                
                # Resposta de sucesso
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Centro de custo "{centro.nome}" criado com sucesso!',
                        'centro': {
                            'codigo': centro.codigo,
                            'nome': centro.nome,
                            'tipo': centro.tipo,
                            'nivel': centro.nivel
                        }
                    })
                
                messages.success(request, f'Centro de custo "{centro.nome}" criado com sucesso!')
                return redirect('gestor:centrocusto_tree')
                
            except Exception as e:
                # Log detalhado do erro
                import traceback
                logger.error(f"=== ERRO AO SALVAR CENTRO ===")
                logger.error(f"Erro: {str(e)}")
                logger.error(f"Tipo do erro: {type(e)}")
                logger.error(f"Traceback completo:")
                logger.error(traceback.format_exc())
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erro ao criar centro de custo: {str(e)}',
                        'error_type': type(e).__name__,
                        'traceback': traceback.format_exc()
                    })
                
                messages.error(request, f'Erro ao criar centro de custo: {str(e)}')
    
    else:
        # GET request
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
                    filhos_diretos = centro_pai.get_filhos_diretos()
                    proxima_sequencia = filhos_diretos.count() + 1
                    codigo_sugerido = f"{centro_pai.codigo}.{proxima_sequencia:02d}"
                    form.initial['codigo'] = codigo_sugerido
                
                form.pai_info = {
                    'codigo': centro_pai.codigo,
                    'nome': centro_pai.nome,
                    'tipo_display': centro_pai.get_tipo_display()
                }
            except CentroCusto.DoesNotExist:
                logger.warning(f'Centro pai não encontrado: {codigo_pai}')
    
    # Renderizar modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/centrocusto_form_modal.html', {
            'form': form,
            'title': 'Novo Centro de Custo',
            'is_create': True
        })
    
    # Fallback
    context = {
        'form': form,
        'title': 'Novo Centro de Custo',
        'is_create': True
    }
    return render(request, 'gestor/centrocusto_form.html', context)


# gestor/views/centrocusto.py - Debug detalhado do save com transaction

@login_required
def centrocusto_update_modal(request, codigo):
    """Editar centro de custo com debug DETALHADO do save"""
    
    centro = get_object_or_404(CentroCusto, codigo=codigo)
    
    if request.method == 'POST':
        logger.info(f"=== DEBUG SAVE DETALHADO ===")
        logger.info(f"Centro ANTES da edição: {centro.nome}")
        
        form = CentroCustoForm(request.POST, instance=centro)
        
        if form.is_valid():
            logger.info(f"Cleaned data: {form.cleaned_data}")
            
            # VERIFICAR VALOR ANTES DO SAVE
            centro_antes = CentroCusto.objects.get(codigo=codigo)
            logger.info(f"ANTES DO SAVE - Nome no banco: '{centro_antes.nome}'")
            
            try:
                # USAR TRANSACTION EXPLÍCITA
                from django.db import transaction
                
                with transaction.atomic():
                    logger.info("Iniciando transação...")
                    
                    # Save sem commit primeiro
                    centro_editado = form.save(commit=False)
                    logger.info(f"Save commit=False - Nome: '{centro_editado.nome}'")
                    
                    # Verificar se mudou
                    if centro_antes.nome != centro_editado.nome:
                        logger.info(f"MUDANÇA DETECTADA: '{centro_antes.nome}' → '{centro_editado.nome}'")
                    else:
                        logger.warning("NENHUMA MUDANÇA DETECTADA!")
                    
                    # Validação manual
                    centro_editado.full_clean()
                    logger.info("Validação passou")
                    
                    # SAVE COM COMMIT EXPLÍCITO
                    centro_editado.save()
                    logger.info(f"Save() executado - PK: {centro_editado.pk}")
                    
                    # VERIFICAR IMEDIATAMENTE SE SALVOU
                    centro_verificacao_1 = CentroCusto.objects.get(codigo=codigo)
                    logger.info(f"VERIFICAÇÃO 1 (dentro da transação): '{centro_verificacao_1.nome}'")
                    
                    # FORÇAR REFRESH DO OBJETO
                    centro_editado.refresh_from_db()
                    logger.info(f"Após refresh_from_db: '{centro_editado.nome}'")
                    
                    # TRANSACTION COMMIT AUTOMÁTICO AQUI
                    logger.info("Saindo da transação (commit automático)")
                
                # VERIFICAR APÓS TRANSACTION
                centro_verificacao_2 = CentroCusto.objects.get(codigo=codigo)
                logger.info(f"VERIFICAÇÃO 2 (após transação): '{centro_verificacao_2.nome}'")
                
                # VERIFICAR COM SELECT FOR UPDATE
                centro_verificacao_3 = CentroCusto.objects.select_for_update().get(codigo=codigo)
                logger.info(f"VERIFICAÇÃO 3 (com lock): '{centro_verificacao_3.nome}'")
                
                # VERIFICAR TODOS OS CAMPOS
                logger.info(f"Campos finais - Nome: '{centro_verificacao_3.nome}', Tipo: '{centro_verificacao_3.tipo}', Ativo: {centro_verificacao_3.ativo}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Centro atualizado: "{centro_verificacao_3.nome}"',
                        'debug': {
                            'nome_antes': centro_antes.nome,
                            'nome_depois': centro_verificacao_3.nome,
                            'mudou': centro_antes.nome != centro_verificacao_3.nome
                        }
                    })
                
            except Exception as e:
                logger.error(f"ERRO NO SAVE: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erro: {str(e)}',
                        'traceback': traceback.format_exc()
                    })
        else:
            logger.error(f"Form inválido: {form.errors}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Form inválido',
                    'errors': form.errors
                })
    
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
