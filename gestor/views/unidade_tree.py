# gestor/views/unidade_tree.py - Atualizado para arquitetura focada na árvore

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
    """Visualização hierárquica principal de unidades organizacionais"""
    
    # Buscar todas as unidades ativas
    unidades = Unidade.objects.filter(ativa=True).select_related('empresa').order_by('codigo')
    
    # Construir estrutura de árvore usando hierarquia dinâmica
    def construir_arvore_completa():
        def construir_no(unidade):
            filhos_diretos = unidade.get_filhos_diretos().order_by('codigo')
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
                'tem_filhos': unidade.tem_filhos,
                'data_criacao': unidade.data_criacao.isoformat() if unidade.data_criacao else None,
                'data_alteracao': unidade.data_alteracao.isoformat() if unidade.data_alteracao else None,
                'filhos': [construir_no(filho) for filho in filhos_diretos]
            }
        
        # Buscar raízes (nível 1) e construir árvore completa
        raizes = [u for u in unidades if u.nivel == 1]
        return [construir_no(raiz) for raiz in raizes]
    
    tree_data = construir_arvore_completa()
    
    # Calcular estatísticas detalhadas
    def calcular_stats():
        unidades_list = list(unidades)
        total_unidades = len(unidades_list)
        
        # Contar por tipo
        unidades_sinteticas = sum(1 for u in unidades_list if u.tem_filhos)
        unidades_analiticas = total_unidades - unidades_sinteticas
        
        # Contar por nível
        niveis_existentes = sorted(set(u.nivel for u in unidades_list))
        contas_por_nivel = {
            str(nivel): len([u for u in unidades_list if u.nivel == nivel]) 
            for nivel in niveis_existentes
        }
        
        # Contar por empresa
        empresas_stats = {}
        for unidade in unidades_list:
            if unidade.empresa:
                sigla = unidade.empresa.sigla
                if sigla not in empresas_stats:
                    empresas_stats[sigla] = 0
                empresas_stats[sigla] += 1
        
        return {
            'total': total_unidades,
            'tipo_s': unidades_sinteticas,
            'tipo_a': unidades_analiticas,
            'nivel_max': max(niveis_existentes) if niveis_existentes else 0,
            'nivel_min': min(niveis_existentes) if niveis_existentes else 0,
            'contas_por_nivel': contas_por_nivel,
            'empresas_stats': empresas_stats,
            'niveis_existentes': niveis_existentes
        }
    
    stats = calcular_stats()
    
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
    """API para dados da árvore de unidades com filtros avançados"""
    
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
        
        # Construir árvore filtrada
        def construir_arvore_filtrada():
            unidades_filtradas = list(queryset)
            
            def construir_no(unidade):
                # Buscar filhos que também passaram pelo filtro
                filhos_filtrados = [
                    u for u in unidades_filtradas 
                    if u.pai and u.pai.id == unidade.id
                ]
                
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
                    'tem_filhos': len(filhos_filtrados) > 0,
                    'filhos': [construir_no(filho) for filho in sorted(filhos_filtrados, key=lambda x: x.codigo)]
                }
            
            # Encontrar raízes (unidades sem pai ou com pai fora do filtro)
            raizes = []
            for unidade in unidades_filtradas:
                if unidade.nivel == 1 or not any(u.id == unidade.pai.id for u in unidades_filtradas if unidade.pai):
                    raizes.append(unidade)
            
            return [construir_no(raiz) for raiz in sorted(raizes, key=lambda x: x.codigo)]
        
        tree_data = construir_arvore_filtrada()
        
        # Calcular estatísticas dos dados filtrados
        unidades_filtradas = list(queryset)
        total_filtradas = len(unidades_filtradas)
        sinteticas_filtradas = sum(1 for u in unidades_filtradas if u.tem_filhos)
        analiticas_filtradas = total_filtradas - sinteticas_filtradas
        
        stats = {
            'total': total_filtradas,
            'tipo_s': sinteticas_filtradas,
            'tipo_a': analiticas_filtradas,
            'nivel_max': max([u.nivel for u in unidades_filtradas]) if unidades_filtradas else 0,
            'filtros_aplicados': {
                'search': search,
                'nivel': nivel,
                'tipo': tipo,
                'empresa': empresa,
                'ativa': ativa
            }
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
            caminho = unidade.get_caminho_hierarquico()
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
            def construir_no_export(unidade):
                filhos = unidade.get_filhos_diretos()
                if not apenas_ativas:
                    filhos = filhos.filter(ativa=True)
                
                return {
                    'codigo': unidade.codigo,
                    'codigo_allstrategy': unidade.codigo_allstrategy,
                    'nome': unidade.nome,
                    'tipo': unidade.tipo,
                    'tipo_display': unidade.get_tipo_display(),
                    'nivel': unidade.nivel,
                    'ativa': unidade.ativa,
                    'empresa_sigla': unidade.empresa.sigla if unidade.empresa else None,
                    'empresa_nome': unidade.empresa.nome_display if unidade.empresa else None,
                    'descricao': unidade.descricao,
                    'data_criacao': unidade.data_criacao.isoformat() if unidade.data_criacao else None,
                    'filhos': [construir_no_export(filho) for filho in filhos.order_by('codigo')]
                }
            
            raizes = [u for u in queryset if u.nivel == 1]
            export_data = {
                'metadata': {
                    'export_date': timezone.now().isoformat(),
                    'total_unidades': queryset.count(),
                    'apenas_ativas': apenas_ativas,
                    'formato': 'hierarquico'
                },
                'unidades': [construir_no_export(raiz) for raiz in raizes]
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
                'Ativa', 'Empresa', 'Descrição', 'Caminho Hierárquico'
            ])
            
            for unidade in queryset:
                caminho = unidade.get_caminho_hierarquico()
                caminho_texto = ' > '.join([u.nome for u in caminho])
                
                writer.writerow([
                    unidade.codigo,
                    unidade.codigo_allstrategy or '',
                    unidade.nome,
                    unidade.get_tipo_display(),
                    unidade.nivel,
                    'Sim' if unidade.ativa else 'Não',
                    unidade.empresa.sigla if unidade.empresa else '',
                    unidade.descricao or '',
                    caminho_texto
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

# Funções auxiliares mantidas para compatibilidade
def build_tree_structure(queryset=None):
    """Constrói estrutura de árvore - mantida para compatibilidade"""
    if queryset is None:
        queryset = Unidade.objects.filter(ativa=True).select_related('empresa')
    
    def construir_no(unidade):
        filhos_diretos = unidade.get_filhos_diretos()
        return {
            'unidade': unidade,
            'filhos': [construir_no(filho) for filho in filhos_diretos.order_by('codigo')]
        }
    
    raizes = [u for u in queryset if u.nivel == 1]
    return [construir_no(raiz) for raiz in raizes]

def calculate_tree_stats(queryset=None):
    """Calcula estatísticas da árvore - mantida para compatibilidade"""
    if queryset is None:
        queryset = Unidade.objects.filter(ativa=True)
    
    unidades_list = list(queryset)
    total = len(unidades_list)
    sinteticas = sum(1 for u in unidades_list if u.tem_filhos)
    analiticas = total - sinteticas
    
    return {
        'total': total,
        'tipo_s': sinteticas,
        'tipo_a': analiticas,
        'nivel_max': max([u.nivel for u in unidades_list]) if unidades_list else 0
    }