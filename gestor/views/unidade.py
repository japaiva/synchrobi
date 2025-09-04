# gestor/views/unidade.py - CRUD de Unidades Organizacionais

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
import logging

from core.models import Unidade
from core.forms import UnidadeForm

logger = logging.getLogger('synchrobi')

@login_required
def unidade_list(request):
    """Lista de unidades organizacionais com filtros"""
    search = request.GET.get('search', '')
    nivel = request.GET.get('nivel', '')
    
    # Buscar todas as unidades com hierarquia
    unidades = Unidade.objects.select_related('unidade_pai').prefetch_related('sub_unidades').filter(ativa=True)
    
    if search:
        unidades = unidades.filter(
            Q(codigo__icontains=search) |
            Q(codigo_allstrategy__icontains=search) |
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )
    
    if nivel:
        unidades = unidades.filter(nivel=nivel)
    
    # Ordenar por código para manter hierarquia
    unidades = unidades.order_by('codigo')
    
    # Paginação
    paginator = Paginator(unidades, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opções para filtros
    niveis_disponiveis = sorted(set(Unidade.objects.values_list('nivel', flat=True)))
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'nivel': nivel,
        'niveis_disponiveis': niveis_disponiveis,
    }
    return render(request, 'gestor/unidade_list.html', context)

@login_required
def unidade_create(request):
    """Criar nova unidade"""
    if request.method == 'POST':
        form = UnidadeForm(request.POST)
        if form.is_valid():
            try:
                unidade = form.save()
                messages.success(request, f'Unidade "{unidade.nome}" criada com sucesso!')
                
                # Informar sobre o tipo determinado automaticamente
                tipo_msg = "Sintética (agrupadora)" if unidade.e_sintetico else "Analítica (operacional)"
                messages.info(request, f'Tipo determinado automaticamente: {tipo_msg}')
                
                logger.info(f'Unidade criada: {unidade.codigo} - {unidade.nome} por {request.user}')
                return redirect('gestor:unidade_detail', pk=unidade.id)
            except Exception as e:
                messages.error(request, f'Erro ao criar unidade: {str(e)}')
                logger.error(f'Erro ao criar unidade: {str(e)}')
        else:
            messages.error(request, 'Erro ao criar unidade. Verifique os dados.')
    else:
        form = UnidadeForm()
        
        # Se veio de uma unidade pai, pré-preencher
        unidade_pai_id = request.GET.get('unidade_pai')
        if unidade_pai_id:
            try:
                unidade_pai = Unidade.objects.get(id=unidade_pai_id)
                # Sugerir código baseado no pai
                proxima_sequencia = unidade_pai.sub_unidades.count() + 1
                codigo_sugerido = f"{unidade_pai.codigo}.{proxima_sequencia:02d}"
                form.initial['codigo'] = codigo_sugerido
                form.initial['unidade_pai_display'] = f"{unidade_pai.codigo} - {unidade_pai.nome}"
            except Unidade.DoesNotExist:
                pass
    
    context = {
        'form': form, 
        'title': 'Nova Unidade',
        'is_create': True
    }
    return render(request, 'gestor/unidade_form.html', context)

@login_required
def unidade_detail(request, pk):
    """Detalhes da unidade"""
    unidade = get_object_or_404(Unidade, pk=pk)
    
    # Buscar sub-unidades diretas (prefetch para evitar N+1)
    sub_unidades = unidade.sub_unidades.filter(ativa=True).prefetch_related('sub_unidades').order_by('codigo')
    
    # Caminho hierárquico
    caminho = unidade.caminho_hierarquico
    
    # Estatísticas
    total_sub_unidades = unidade.get_todas_sub_unidades(include_self=False)
    unidades_operacionais = unidade.get_unidades_operacionais()
    
    context = {
        'unidade': unidade,
        'sub_unidades': sub_unidades,
        'caminho': caminho,
        'total_sub_unidades': total_sub_unidades,
        'unidades_operacionais': unidades_operacionais,
    }
    return render(request, 'gestor/unidade_detail.html', context)

@login_required
def unidade_update(request, pk):
    """Editar unidade"""
    unidade = get_object_or_404(Unidade, pk=pk)
    
    # Guardar valores originais para log
    valores_originais = {
        'codigo': unidade.codigo,
        'nome': unidade.nome,
        'tipo': unidade.get_tipo_display(),
        'ativa': unidade.ativa
    }
    
    if request.method == 'POST':
        form = UnidadeForm(request.POST, instance=unidade)
        if form.is_valid():
            try:
                unidade_atualizada = form.save()
                
                # Log de alterações
                alteracoes = []
                for campo, valor_original in valores_originais.items():
                    if campo == 'tipo':
                        valor_novo = unidade_atualizada.get_tipo_display()
                    else:
                        valor_novo = getattr(unidade_atualizada, campo)
                    
                    if valor_original != valor_novo:
                        alteracoes.append(f"{campo}: {valor_original} → {valor_novo}")
                
                if alteracoes:
                    logger.info(f'Unidade {unidade.codigo} alterada por {request.user}: {", ".join(alteracoes)}')
                
                messages.success(request, f'Unidade "{unidade_atualizada.nome}" atualizada com sucesso!')
                
                # Se o tipo mudou, informar
                if valores_originais['tipo'] != unidade_atualizada.get_tipo_display():
                    messages.info(request, 
                        f'Tipo alterado automaticamente de {valores_originais["tipo"]} '
                        f'para {unidade_atualizada.get_tipo_display()}')
                
                return redirect('gestor:unidade_detail', pk=unidade_atualizada.id)
            except Exception as e:
                messages.error(request, f'Erro ao atualizar unidade: {str(e)}')
                logger.error(f'Erro ao atualizar unidade {unidade.codigo}: {str(e)}')
        else:
            messages.error(request, 'Erro ao atualizar unidade. Verifique os dados.')
    else:
        form = UnidadeForm(instance=unidade)
    
    context = {
        'form': form, 
        'title': 'Editar Unidade', 
        'unidade': unidade,
        'is_create': False
    }
    return render(request, 'gestor/unidade_form.html', context)

@login_required
def unidade_delete(request, pk):
    """Deletar unidade"""
    unidade = get_object_or_404(Unidade, pk=pk)
    
    # Verificar se tem sub-unidades
    tem_sub_unidades = unidade.tem_sub_unidades
    
    if request.method == 'POST':
        if tem_sub_unidades:
            messages.error(request, 
                f'Não é possível excluir a unidade "{unidade.nome}" pois ela possui {unidade.sub_unidades.count()} sub-unidade(s).')
            return redirect('gestor:unidade_detail', pk=pk)
        
        nome = unidade.nome
        codigo = unidade.codigo
        tipo = unidade.get_tipo_display()
        
        # Se tem pai, ele pode mudar de sintético para analítico
        unidade_pai = unidade.unidade_pai
        
        try:
            unidade.delete()
            messages.success(request, f'Unidade "{nome}" (código: {codigo}, tipo: {tipo}) excluída com sucesso!')
            
            # Verificar se o pai mudou de tipo
            if unidade_pai:
                unidade_pai.refresh_from_db()
                if unidade_pai.e_analitico:
                    messages.info(request, 
                        f'A unidade pai "{unidade_pai.nome}" foi automaticamente '
                        f'alterada para Analítica por não ter mais sub-unidades.')
            
            logger.info(f'Unidade excluída: {codigo} - {nome} por {request.user}')
            return redirect('gestor:unidade_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir unidade: {str(e)}')
            logger.error(f'Erro ao excluir unidade {codigo}: {str(e)}')
            return redirect('gestor:unidade_detail', pk=pk)
    
    context = {
        'unidade': unidade,
        'tem_sub_unidades': tem_sub_unidades,
    }
    return render(request, 'gestor/unidade_delete.html', context)

@login_required
def unidade_arvore(request):
    """View para exibir árvore hierárquica de unidades"""
    unidades = Unidade.objects.filter(ativa=True).prefetch_related('sub_unidades').order_by('codigo')
    
    # Construir estrutura de árvore
    def construir_arvore(unidade_pai=None, nivel=0):
        arvore = []
        unidades_nivel = [u for u in unidades if u.unidade_pai == unidade_pai]
        
        for unidade in unidades_nivel:
            arvore.append({
                'unidade': unidade,
                'nivel': nivel,
                'sub_arvore': construir_arvore(unidade, nivel + 1)
            })
        
        return arvore
    
    arvore_completa = construir_arvore()
    
    # Contar tipos
    unidades_list = list(unidades)
    unidades_sinteticas = sum(1 for u in unidades_list if u.tem_sub_unidades)
    unidades_analiticas = len(unidades_list) - unidades_sinteticas
    
    context = {
        'arvore': arvore_completa,
        'total_unidades': len(unidades_list),
        'unidades_sinteticas': unidades_sinteticas,
        'unidades_analiticas': unidades_analiticas,
    }
    return render(request, 'gestor/unidade_arvore.html', context)

# ===== API ENDPOINTS =====

@login_required
def api_unidade_filhas(request, pk):
    """API para buscar sub-unidades de uma unidade"""
    try:
        unidade = Unidade.objects.get(pk=pk)
        sub_unidades = unidade.sub_unidades.filter(ativa=True).order_by('codigo')
        
        data = {
            'success': True,
            'unidade': {
                'id': unidade.id,
                'codigo': unidade.codigo,
                'nome': unidade.nome,
            },
            'sub_unidades': [
                {
                    'id': sub.id,
                    'codigo': sub.codigo,
                    'codigo_allstrategy': sub.codigo_allstrategy,
                    'nome': sub.nome,
                    'tipo_display': sub.get_tipo_display(),
                    'tem_filhas': sub.tem_sub_unidades
                }
                for sub in sub_unidades
            ]
        }
        
        return JsonResponse(data)
        
    except Unidade.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Unidade não encontrada'})
    except Exception as e:
        logger.error(f'Erro na API de sub-unidades: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Erro interno'})

@login_required
def api_validar_codigo(request):
    """API para validar código de unidade em tempo real"""
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
    
    # Verificar hierarquia
    info = {'valid': True}
    
    if '.' in codigo:
        partes = codigo.split('.')
        codigo_pai = '.'.join(partes[:-1])
        
        try:
            unidade_pai = Unidade.objects.get(codigo=codigo_pai)
            info['pai'] = {
                'id': unidade_pai.id,
                'codigo': unidade_pai.codigo,
                'nome': unidade_pai.nome,
                'tipo_display': unidade_pai.get_tipo_display()
            }
                
        except Unidade.DoesNotExist:
            info['valid'] = False
            info['error'] = f'Unidade pai com código "{codigo_pai}" não existe'
    else:
        info['pai'] = None
        info['nivel'] = 1
    
    # Calcular nível
    info['nivel'] = codigo.count('.') + 1
    
    return JsonResponse(info)