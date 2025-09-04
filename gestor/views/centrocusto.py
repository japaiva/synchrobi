# gestor/views/centrocusto.py - CRUD de Centros de Custo

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
import logging

from core.models import CentroCusto
from core.forms import CentroCustoForm

logger = logging.getLogger('synchrobi')

@login_required
def centrocusto_list(request):
    """Lista de centros de custo com filtros"""
    search = request.GET.get('search', '')
    nivel = request.GET.get('nivel', '')
    ativo = request.GET.get('ativo', '')
    
    centros = CentroCusto.objects.select_related('centro_pai').filter(ativo=True)
    
    if search:
        centros = centros.filter(
            Q(codigo__icontains=search) |
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )
    
    if nivel:
        centros = centros.filter(nivel=nivel)
    
    if ativo:
        centros = centros.filter(ativo=(ativo == 'true'))
    
    # Ordenar por código para manter hierarquia
    centros = centros.order_by('codigo')
    
    # Paginação
    paginator = Paginator(centros, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opções para filtros
    niveis_disponiveis = sorted(set(CentroCusto.objects.values_list('nivel', flat=True)))
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'nivel': nivel,
        'ativo': ativo,
        'niveis_disponiveis': niveis_disponiveis,
    }
    return render(request, 'gestor/centrocusto_list.html', context)

@login_required
def centrocusto_create(request):
    """Criar novo centro de custo"""
    if request.method == 'POST':
        form = CentroCustoForm(request.POST)
        if form.is_valid():
            try:
                centro = form.save()
                messages.success(request, f'Centro de custo "{centro.nome}" criado com sucesso!')
                
                # Informar sobre o tipo determinado automaticamente
                tipo_msg = "Sintético (agrupador)" if centro.e_sintetico else "Analítico (operacional)"
                messages.info(request, f'Tipo determinado automaticamente: {tipo_msg}')
                
                logger.info(f'Centro de custo criado: {centro.codigo} - {centro.nome} por {request.user}')
                return redirect('gestor:centrocusto_list')
            except Exception as e:
                messages.error(request, f'Erro ao criar centro de custo: {str(e)}')
                logger.error(f'Erro ao criar centro de custo: {str(e)}')
        else:
            messages.error(request, 'Erro ao criar centro de custo. Verifique os dados.')
    else:
        form = CentroCustoForm()
    
    context = {
        'form': form, 
        'title': 'Novo Centro de Custo',
        'is_create': True
    }
    return render(request, 'gestor/centrocusto_form.html', context)

@login_required
def centrocusto_update(request, codigo):
    """Editar centro de custo"""
    centro = get_object_or_404(CentroCusto, codigo=codigo)
    
    # Guardar valores originais para log
    valores_originais = {
        'codigo': centro.codigo,
        'nome': centro.nome,
        'tipo': centro.get_tipo_display(),
        'ativo': centro.ativo
    }
    
    if request.method == 'POST':
        form = CentroCustoForm(request.POST, instance=centro)
        if form.is_valid():
            try:
                centro_atualizado = form.save()
                
                # Log de alterações
                alteracoes = []
                for campo, valor_original in valores_originais.items():
                    if campo == 'tipo':
                        valor_novo = centro_atualizado.get_tipo_display()
                    else:
                        valor_novo = getattr(centro_atualizado, campo)
                    
                    if valor_original != valor_novo:
                        alteracoes.append(f"{campo}: {valor_original} → {valor_novo}")
                
                if alteracoes:
                    logger.info(f'Centro de custo {centro.codigo} alterado por {request.user}: {", ".join(alteracoes)}')
                
                messages.success(request, f'Centro de custo "{centro_atualizado.nome}" atualizado com sucesso!')
                
                # Se o tipo mudou, informar
                if valores_originais['tipo'] != centro_atualizado.get_tipo_display():
                    messages.info(request, 
                        f'Tipo alterado automaticamente de {valores_originais["tipo"]} '
                        f'para {centro_atualizado.get_tipo_display()}')
                
                return redirect('gestor:centrocusto_list')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar centro de custo: {str(e)}')
                logger.error(f'Erro ao atualizar centro de custo {centro.codigo}: {str(e)}')
        else:
            messages.error(request, 'Erro ao atualizar centro de custo. Verifique os dados.')
    else:
        form = CentroCustoForm(instance=centro)
    
    context = {
        'form': form, 
        'title': 'Editar Centro de Custo', 
        'centro': centro,
        'is_create': False
    }
    return render(request, 'gestor/centrocusto_form.html', context)

@login_required
def centrocusto_delete(request, codigo):
    """Deletar centro de custo"""
    centro = get_object_or_404(CentroCusto, codigo=codigo)
    
    # Verificar se tem sub-centros
    tem_sub_centros = centro.tem_sub_centros
    
    if request.method == 'POST':
        if tem_sub_centros:
            messages.error(request, 
                f'Não é possível excluir o centro de custo "{centro.nome}" pois ele possui {centro.sub_centros.count()} sub-centro(s).')
            return redirect('gestor:centrocusto_list')
        
        nome = centro.nome
        codigo_centro = centro.codigo
        tipo = centro.get_tipo_display()
        
        # Se tem pai, ele pode mudar de sintético para analítico
        centro_pai = centro.centro_pai
        
        try:
            centro.delete()
            messages.success(request, f'Centro de custo "{nome}" (código: {codigo_centro}, tipo: {tipo}) excluído com sucesso!')
            
            # Verificar se o pai mudou de tipo
            if centro_pai:
                centro_pai.refresh_from_db()
                if centro_pai.e_analitico:
                    messages.info(request, 
                        f'O centro pai "{centro_pai.nome}" foi automaticamente '
                        f'alterado para Analítico por não ter mais sub-centros.')
            
            logger.info(f'Centro de custo excluído: {codigo_centro} - {nome} por {request.user}')
            return redirect('gestor:centrocusto_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir centro de custo: {str(e)}')
            logger.error(f'Erro ao excluir centro de custo {codigo_centro}: {str(e)}')
            return redirect('gestor:centrocusto_list')
    
    context = {
        'centro': centro,
        'tem_sub_centros': tem_sub_centros,
    }
    return render(request, 'gestor/centrocusto_delete.html', context)

# ===== API ENDPOINT =====

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
        partes = codigo.split('.')
        codigo_pai = '.'.join(partes[:-1])
        
        try:
            centro_pai = CentroCusto.objects.get(codigo=codigo_pai)
            info['pai'] = {
                'codigo': centro_pai.codigo,
                'nome': centro_pai.nome,
                'tipo_display': centro_pai.get_tipo_display()
            }
                
        except CentroCusto.DoesNotExist:
            info['valid'] = False
            info['error'] = f'Centro de custo pai com código "{codigo_pai}" não existe'
    else:
        info['pai'] = None
    
    # Calcular nível
    info['nivel'] = codigo.count('.') + 1
    
    return JsonResponse(info)