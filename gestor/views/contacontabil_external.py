# gestor/views/contacontabil_external.py
from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Prefetch
from django.db import models
from core.models import ContaContabil, ContaExterna
import json
import logging

logger = logging.getLogger('synchrobi')

@login_required
def contacontabil_tree_with_external_view(request):
    """Visualização hierárquica de contas contábeis com códigos externos"""
    
    try:
        # Query otimizada com prefetch de contas externas
        contas_queryset = ContaContabil.objects.filter(ativa=True).prefetch_related(
            Prefetch(
                'contas_externas',
                queryset=ContaExterna.objects.filter(ativa=True).order_by('sistema_origem', 'codigo_externo')
            )
        ).order_by('codigo')
        
        # Construir árvore com contas externas
        def construir_arvore_com_externos():
            hierarchy_map, root_items = ContaContabil.build_hierarchy_map(contas_queryset)
            
            def construir_no_com_externos(conta):
                children_data = hierarchy_map.get(conta.codigo, {}).get('children', [])
                
                # Serializar contas externas
                contas_externas_data = []
                for externa in conta.contas_externas.all():
                    contas_externas_data.append({
                        'id': externa.id,
                        'codigo_externo': externa.codigo_externo,
                        'nome_externo': externa.nome_externo,
                        'sistema_origem': externa.sistema_origem,
                        'empresas_utilizacao': externa.empresas_utilizacao,
                        'observacoes': externa.observacoes,
                        'ativa': externa.ativa,
                        'sincronizado': externa.sincronizado
                    })
                
                return {
                    'codigo': conta.codigo,
                    'nome': conta.nome,
                    'tipo': conta.tipo,
                    'nivel': conta.nivel,
                    'ativa': conta.ativa,
                    'descricao': conta.descricao,
                    'tem_filhos': len(children_data) > 0,
                    'contas_externas': contas_externas_data,
                    'data_criacao': conta.data_criacao.isoformat() if conta.data_criacao else None,
                    'data_alteracao': conta.data_alteracao.isoformat() if conta.data_alteracao else None,
                    'filhos': [construir_no_com_externos(filho) for filho in sorted(children_data, key=lambda x: x.codigo)]
                }
            
            return [construir_no_com_externos(raiz) for raiz in sorted(root_items, key=lambda x: x.codigo)]
        
        # Calcular estatísticas
        def calcular_stats_com_externos():
            total_contas = contas_queryset.count()
            
            # Contas com códigos externos
            contas_com_externos = contas_queryset.annotate(
                num_externos=Count('contas_externas', filter=models.Q(contas_externas__ativa=True))
            ).filter(num_externos__gt=0).count()
            
            # Total de códigos externos
            total_externos = ContaExterna.objects.filter(ativa=True).count()
            
            # Sistemas diferentes
            sistemas = ContaExterna.objects.filter(ativa=True).values_list('sistema_origem', flat=True).distinct()
            sistemas_count = len([s for s in sistemas if s])
            
            # Estatísticas por tipo
            tipos = contas_queryset.values('tipo').annotate(count=Count('tipo'))
            tipo_s = next((t['count'] for t in tipos if t['tipo'] == 'S'), 0)
            tipo_a = next((t['count'] for t in tipos if t['tipo'] == 'A'), 0)
            
            return {
                'total_contas': total_contas,
                'contas_com_externos': contas_com_externos,
                'total_externos': total_externos,
                'sistemas_count': sistemas_count,
                'tipo_s': tipo_s,
                'tipo_a': tipo_a,
                'sistemas_lista': list(sistemas)
            }
        
        tree_data = construir_arvore_com_externos()
        stats = calcular_stats_com_externos()
        
        context = {
            'tree_data_json': json.dumps(tree_data, ensure_ascii=False, indent=2),
            'stats': stats,
            'entity_name': 'Contas Contábeis',
            'entity_singular': 'Conta Contábil',
            'create_url': 'gestor:contacontabil_create_modal',
            'update_url_base': '/gestor/contas-contabeis/',
            'tree_url': 'gestor:contacontabil_tree_with_external',
            'api_tree_data_url': 'gestor:api_contacontabil_tree_with_external',
            'breadcrumb': 'Contas Contábeis com Códigos Externos',
            'icon': 'fa-calculator'
        }
        
        return render(request, 'gestor/contacontabil_tree_with_external.html', context)
        
    except Exception as e:
        logger.error(f'Erro na construção da árvore com contas externas: {str(e)}')
        context = {
            'tree_data_json': '[]',
            'stats': {
                'total_contas': 0, 'contas_com_externos': 0, 
                'total_externos': 0, 'sistemas_count': 0
            },
            'error_message': 'Erro ao carregar árvore de contas contábeis',
        }
        return render(request, 'gestor/contacontabil_tree_with_external.html', context)

@login_required
def api_contacontabil_tree_with_external_data(request):
    """API para dados da árvore de contas contábeis com códigos externos"""
    
    try:
        search = request.GET.get('search', '').strip()
        nivel = request.GET.get('nivel', '')
        tipo = request.GET.get('tipo', '')
        sistema = request.GET.get('sistema', '')
        has_external = request.GET.get('has_external', '')
        ativa = request.GET.get('ativa', '')
        
        # Query base
        queryset = ContaContabil.objects.prefetch_related(
            Prefetch(
                'contas_externas',
                queryset=ContaExterna.objects.filter(ativa=True).order_by('sistema_origem', 'codigo_externo')
            )
        ).order_by('codigo')
        
        # Filtros básicos
        if ativa != '':
            queryset = queryset.filter(ativa=ativa.lower() == 'true')
        else:
            queryset = queryset.filter(ativa=True)
        
        if nivel:
            queryset = queryset.filter(nivel=int(nivel))
        
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        # Filtro por presença de códigos externos
        if has_external == 'with':
            queryset = queryset.filter(contas_externas__ativa=True).distinct()
        elif has_external == 'without':
            queryset = queryset.filter(contas_externas__isnull=True)
        
        # Filtro por sistema (requer join)
        if sistema:
            queryset = queryset.filter(
                contas_externas__sistema_origem__icontains=sistema,
                contas_externas__ativa=True
            ).distinct()
        
        # Filtro de busca textual
        if search:
            from django.db.models import Q
            
            # Busca em contas contábeis
            q_contas = Q(codigo__icontains=search) | Q(nome__icontains=search) | Q(descricao__icontains=search)
            
            # Busca em contas externas
            q_externos = Q(
                contas_externas__codigo_externo__icontains=search
            ) | Q(
                contas_externas__nome_externo__icontains=search
            ) | Q(
                contas_externas__sistema_origem__icontains=search
            ) | Q(
                contas_externas__empresas_utilizacao__icontains=search
            )
            
            queryset = queryset.filter(q_contas | q_externos).distinct()
        
        # Construir árvore
        hierarchy_map, root_items = ContaContabil.build_hierarchy_map(queryset)
        
        def construir_no_api_externos(conta):
            children_data = hierarchy_map.get(conta.codigo, {}).get('children', [])
            
            # Serializar contas externas
            contas_externas_data = []
            for externa in conta.contas_externas.all():
                contas_externas_data.append({
                    'id': externa.id,
                    'codigo_externo': externa.codigo_externo,
                    'nome_externo': externa.nome_externo,
                    'sistema_origem': externa.sistema_origem,
                    'empresas_utilizacao': externa.empresas_utilizacao,
                    'ativa': externa.ativa,
                    'sincronizado': externa.sincronizado
                })
            
            return {
                'codigo': conta.codigo,
                'nome': conta.nome,
                'tipo': conta.tipo,
                'nivel': conta.nivel,
                'ativa': conta.ativa,
                'descricao': conta.descricao,
                'tem_filhos': len(children_data) > 0,
                'contas_externas': contas_externas_data,
                'filhos': [construir_no_api_externos(filho) for filho in sorted(children_data, key=lambda x: x.codigo)]
            }
        
        tree_data = [construir_no_api_externos(raiz) for raiz in sorted(root_items, key=lambda x: x.codigo)]
        
        # Estatísticas filtradas
        contas_filtradas = list(queryset)
        total_filtradas = len(contas_filtradas)
        sinteticas = sum(1 for c in contas_filtradas if c.tipo == 'S')
        analiticas = total_filtradas - sinteticas
        
        # Contar códigos externos nas contas filtradas
        total_externos_filtradas = sum(len(c.contas_externas.all()) for c in contas_filtradas)
        contas_com_externos_filtradas = sum(1 for c in contas_filtradas if c.contas_externas.exists())
        
        stats = {
            'total': total_filtradas,
            'tipo_s': sinteticas,
            'tipo_a': analiticas,
            'contas_com_externos': contas_com_externos_filtradas,
            'total_externos': total_externos_filtradas,
            'nivel_max': max([c.nivel for c in contas_filtradas]) if contas_filtradas else 0,
            'filtros_aplicados': {
                'search': search,
                'nivel': nivel,
                'tipo': tipo,
                'sistema': sistema,
                'has_external': has_external,
                'ativa': ativa
            }
        }
        
        return JsonResponse({
            'success': True,
            'tree_data': tree_data,
            'stats': stats,
            'total_sem_filtro': ContaContabil.objects.filter(ativa=True).count()
        })
        
    except Exception as e:
        logger.error(f'Erro na API de dados da árvore com externos: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro interno do servidor',
            'message': str(e)
        })

# ===== VIEWS CRUD PARA CONTAS EXTERNAS =====

@login_required
def contaexterna_list(request):
    """Lista de códigos externos"""
    
    # Filtros
    conta_codigo = request.GET.get('conta')
    sistema = request.GET.get('sistema')
    ativa = request.GET.get('ativa')
    
    queryset = ContaExterna.objects.select_related('conta_contabil').order_by(
        'conta_contabil__codigo', 'sistema_origem', 'codigo_externo'
    )
    
    if conta_codigo:
        queryset = queryset.filter(conta_contabil__codigo=conta_codigo)
    
    if sistema:
        queryset = queryset.filter(sistema_origem__icontains=sistema)
    
    if ativa:
        queryset = queryset.filter(ativa=ativa.lower() == 'true')
    else:
        queryset = queryset.filter(ativa=True)
    
    # Paginação
    from django.core.paginator import Paginator
    paginator = Paginator(queryset, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filtros': {
            'conta_codigo': conta_codigo,
            'sistema': sistema,
            'ativa': ativa
        },
        'total_count': queryset.count()
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/contaexterna_list_modal.html', context)
    
    return render(request, 'gestor/contaexterna_list.html', context)

@login_required
def contaexterna_create(request):
    """Criar nova conta externa"""
    
    from core.forms import ContaExternaForm
    
    conta_contabil_codigo = request.GET.get('conta_contabil')
    
    if request.method == 'POST':
        form = ContaExternaForm(request.POST)
        
        if form.is_valid():
            try:
                conta_externa = form.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Código externo "{conta_externa.codigo_externo}" criado com sucesso!',
                        'conta_externa': {
                            'id': conta_externa.id,
                            'codigo_externo': conta_externa.codigo_externo,
                            'nome_externo': conta_externa.nome_externo,
                            'sistema_origem': conta_externa.sistema_origem
                        }
                    })
                
                from django.contrib import messages
                messages.success(request, f'Código externo "{conta_externa.codigo_externo}" criado com sucesso!')
                return redirect('gestor:contacontabil_tree_with_external')
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erro ao criar código externo: {str(e)}'
                    })
                
                from django.contrib import messages
                messages.error(request, f'Erro ao criar código externo: {str(e)}')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Dados inválidos. Verifique os campos.',
                    'errors': form.errors
                })
    else:
        form = ContaExternaForm(conta_contabil_codigo=conta_contabil_codigo)
    
    context = {
        'form': form,
        'title': 'Novo Código Externo',
        'is_create': True
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/contaexterna_form_modal.html', context)
    
    return render(request, 'gestor/contaexterna_form.html', context)