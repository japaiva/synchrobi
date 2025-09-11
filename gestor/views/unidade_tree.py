# gestor/views/unidade_tree.py - Atualizado para hierarquia declarada

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from core.models import Unidade
import json
import logging
from django.utils import timezone

logger = logging.getLogger('synchrobi')

@login_required
def unidade_tree_view(request):
    """Visualização hierárquica principal de unidades organizacionais - HIERARQUIA DECLARADA"""
    
    # Buscar todas as unidades ativas
    unidades = Unidade.objects.filter(ativa=True).select_related('empresa').order_by('codigo')
    
    # Construir estrutura de árvore usando hierarquia declarada
    tree_data = construir_arvore_declarada(unidades)
    
    # Calcular estatísticas detalhadas
    stats = calcular_stats_unidades(unidades)
    
    context = {
        'tree_data_json': json.dumps(tree_data, ensure_ascii=False, indent=2),
        'stats': stats,
        'entity_name': 'Unidades Organizacionais',
        'entity_singular': 'Unidade',
        'create_url': 'gestor:unidade_create_modal',
        'update_url_base': '/gestor/unidades/',
        'tree_url': 'gestor:unidade_tree',
        'api_tree_data_url': 'gestor:api_unidade_tree_data',
        'api_validar_codigo_url': 'gestor:api_validar_codigo',
        'breadcrumb': 'Unidades',
        'icon': 'fa-sitemap'
    }
    
    return render(request, 'gestor/unidade_tree_main.html', context)

@login_required
def unidade_tree_data(request):
    """API para dados da árvore de unidades com filtros avançados - HIERARQUIA DECLARADA"""
    
    try:
        # Obter filtros da requisição
        search = request.GET.get('search', '').strip()
        nivel = request.GET.get('nivel', '')
        tipo = request.GET.get('tipo', '')
        empresa = request.GET.get('empresa', '')
        ativa = request.GET.get('ativa', '')
        
        # Construir queryset base
        queryset = Unidade.objects.select_related('empresa').order_by('codigo')
        
        # Aplicar filtros
        if ativa != '':
            queryset = queryset.filter(ativa=ativa.lower() == 'true')
        else:
            queryset = queryset.filter(ativa=True)  # Padrão: apenas ativas
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(codigo_allstrategy__icontains=search) |
                Q(nome__icontains=search) |
                Q(descricao__icontains=search)
            )
        
        if nivel:
            queryset = queryset.filter(nivel=int(nivel))
        
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        if empresa:
            queryset = queryset.filter(empresa__sigla=empresa)
        
        # Construir árvore filtrada usando hierarquia declarada
        tree_data = construir_arvore_declarada(queryset)
        
        # Calcular estatísticas dos dados filtrados
        stats = calcular_stats_unidades(queryset)
        stats['filtros_aplicados'] = {
            'search': search,
            'nivel': nivel,
            'tipo': tipo,
            'empresa': empresa,
            'ativa': ativa
        }
        
        return JsonResponse({
            'success': True,
            'tree_data': tree_data,
            'stats': stats,
            'total_sem_filtro': Unidade.objects.filter(ativa=True).count()
        })
        
    except Exception as e:
        logger.error(f'Erro na API de dados da árvore: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro interno do servidor',
            'message': str(e)
        })

def construir_arvore_declarada(queryset):
    """Constrói árvore hierárquica usando campo codigo_pai"""
    
    # Converter para lista
    unidades_list = list(queryset)
    
    # Mapear unidades por código
    unidades_dict = {unidade.codigo: unidade for unidade in unidades_list}
    
    # Mapear filhos por pai
    filhos_por_pai = {}
    unidades_raiz = []
    
    for unidade in unidades_list:
        if unidade.codigo_pai:
            # Tem pai - adicionar à lista de filhos do pai
            if unidade.codigo_pai not in filhos_por_pai:
                filhos_por_pai[unidade.codigo_pai] = []
            filhos_por_pai[unidade.codigo_pai].append(unidade)
        else:
            # É raiz
            unidades_raiz.append(unidade)
    
    def construir_no(unidade):
        """Constrói um nó da árvore recursivamente"""
        filhos = filhos_por_pai.get(unidade.codigo, [])
        filhos_ordenados = sorted(filhos, key=lambda x: x.codigo)
        
        return {
            'id': unidade.id,
            'codigo': unidade.codigo,
            'codigo_allstrategy': unidade.codigo_allstrategy,
            'nome': unidade.nome,
            'tipo': unidade.tipo,
            'nivel': unidade.nivel,
            'ativa': unidade.ativa,
            'empresa_sigla': unidade.empresa.sigla if unidade.empresa else '',
            'empresa_nome': unidade.empresa.nome_display if unidade.empresa else '',
            'descricao': unidade.descricao,
            'codigo_pai': unidade.codigo_pai or '',
            'tem_filhos': len(filhos) > 0,
            'data_criacao': unidade.data_criacao.isoformat() if unidade.data_criacao else None,
            'data_alteracao': unidade.data_alteracao.isoformat() if unidade.data_alteracao else None,
            'filhos': [construir_no(filho) for filho in filhos_ordenados]
        }
    
    # Construir árvore a partir das raízes
    unidades_raiz_ordenadas = sorted(unidades_raiz, key=lambda x: x.codigo)
    return [construir_no(raiz) for raiz in unidades_raiz_ordenadas]

def calcular_stats_unidades(queryset):
    """Calcula estatísticas das unidades"""
    unidades_list = list(queryset)
    total = len(unidades_list)
    
    if total == 0:
        return {
            'total': 0,
            'tipo_s': 0,
            'tipo_a': 0,
            'nivel_max': 0,
            'contas_por_nivel': {}
        }
    
    # Contadores
    tipo_s = sum(1 for u in unidades_list if u.tem_filhos)
    tipo_a = total - tipo_s
    
    # Níveis
    niveis = [u.nivel for u in unidades_list]
    nivel_max = max(niveis)
    nivel_min = min(niveis)
    
    # Contar por nível
    contas_por_nivel = {}
    for nivel in range(nivel_min, nivel_max + 1):
        count = sum(1 for n in niveis if n == nivel)
        contas_por_nivel[str(nivel)] = count
    
    # Contar por empresa
    empresas_stats = {}
    for unidade in unidades_list:
        if unidade.empresa:
            sigla = unidade.empresa.sigla
            if sigla not in empresas_stats:
                empresas_stats[sigla] = 0
            empresas_stats[sigla] += 1
    
    return {
        'total': total,
        'tipo_s': tipo_s,
        'tipo_a': tipo_a,
        'nivel_max': nivel_max,
        'nivel_min': nivel_min,
        'contas_por_nivel': contas_por_nivel,
        'empresas_stats': empresas_stats,
        'niveis_existentes': sorted(list(set(niveis)))
    }

# Manter outras funções existentes para compatibilidade
@login_required
def unidade_tree_search(request):
    """API específica para busca rápida na árvore"""
    
    search_term = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    
    if not search_term or len(search_term) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Termo de busca deve ter pelo menos 2 caracteres'
        })
    
    try:
        from django.db.models import Q
        
        # Buscar unidades que atendem ao critério
        unidades = Unidade.objects.filter(
            Q(codigo__icontains=search_term) |
            Q(codigo_allstrategy__icontains=search_term) |
            Q(nome__icontains=search_term),
            ativa=True
        ).select_related('empresa').order_by('codigo')[:limit]
        
        results = []
        for unidade in unidades:
            # Construir caminho hierárquico para contexto
            caminho = unidade.get_caminho_completo()
            caminho_texto = ' > '.join([f"{u.codigo} {u.nome}" for u in caminho])
            
            results.append({
                'id': unidade.id,
                'codigo': unidade.codigo,
                'codigo_allstrategy': unidade.codigo_allstrategy,
                'nome': unidade.nome,
                'tipo': unidade.tipo,
                'tipo_display': unidade.get_tipo_display(),
                'nivel': unidade.nivel,
                'empresa_sigla': unidade.empresa.sigla if unidade.empresa else '',
                'caminho': caminho_texto,
                'tem_filhos': unidade.tem_filhos,
                'descricao': unidade.descricao[:100] + '...' if unidade.descricao and len(unidade.descricao) > 100 else unidade.descricao
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'total_found': len(results),
            'search_term': search_term,
            'has_more': len(results) == limit
        })
        
    except Exception as e:
        logger.error(f'Erro na busca da árvore: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro na busca',
            'message': str(e)
        })

@login_required
def unidade_tree_export(request):
    """Export da estrutura hierárquica para diferentes formatos"""
    
    formato = request.GET.get('format', 'json')  # json, csv, excel
    apenas_ativas = request.GET.get('ativas_only', 'true').lower() == 'true'
    
    try:
        # Buscar unidades
        queryset = Unidade.objects.select_related('empresa').order_by('codigo')
        if apenas_ativas:
            queryset = queryset.filter(ativa=True)
        
        if formato == 'json':
            # Export JSON estruturado
            tree_data = construir_arvore_declarada(queryset)
            
            export_data = {
                'metadata': {
                    'export_date': timezone.now().isoformat(),
                    'total_unidades': queryset.count(),
                    'apenas_ativas': apenas_ativas,
                    'formato': 'hierarquico_declarado'
                },
                'unidades': tree_data
            }
            
            response = JsonResponse(export_data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
            response['Content-Disposition'] = 'attachment; filename="unidades_hierarquia.json"'
            return response
            
        elif formato == 'csv':
            # Export CSV plano
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="unidades_plano.csv"'
            response.write('\ufeff')  # BOM para UTF-8
            
            writer = csv.writer(response)
            writer.writerow([
                'Código', 'Código All Strategy', 'Nome', 'Tipo', 'Nível', 
                'Ativa', 'Empresa', 'Descrição', 'Código Pai'
            ])
            
            for unidade in queryset:
                writer.writerow([
                    unidade.codigo,
                    unidade.codigo_allstrategy or '',
                    unidade.nome,
                    unidade.get_tipo_display(),
                    unidade.nivel,
                    'Sim' if unidade.ativa else 'Não',
                    unidade.empresa.sigla if unidade.empresa else '',
                    unidade.descricao or '',
                    unidade.codigo_pai or ''
                ])
            
            return response
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Formato não suportado',
                'formatos_disponiveis': ['json', 'csv']
            })
    
    except Exception as e:
        logger.error(f'Erro no export da árvore: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Erro no export',
            'message': str(e)
        })