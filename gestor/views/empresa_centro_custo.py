# gestor/views/empresa_centro_custo.py - Versão Simplificada

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.db import transaction
import logging

from core.models import Empresa, CentroCusto, Usuario, EmpresaCentroCusto
from core.forms import EmpresaCentroCustoForm, EmpresaCentroCustoFiltroForm

logger = logging.getLogger('synchrobi')

@login_required
def empresa_centro_custo_list(request, sigla_empresa=None):
    """Lista de centros de custo das empresas"""
    
    # Se foi especificada uma empresa, filtrar por ela
    empresa_filtro = None
    if sigla_empresa:
        empresa_filtro = get_object_or_404(Empresa, sigla=sigla_empresa)
    
    # Processar filtros
    form_filtro = EmpresaCentroCustoFiltroForm(request.GET)
    
    # Query base
    relacionamentos = EmpresaCentroCusto.objects.select_related(
        'empresa', 'centro_custo', 'responsavel'
    ).order_by('empresa__sigla', 'centro_custo__codigo')
    
    # Aplicar filtro da empresa se especificada
    if empresa_filtro:
        relacionamentos = relacionamentos.filter(empresa=empresa_filtro)
        form_filtro.fields['empresa'].initial = empresa_filtro
    
    # Aplicar filtros do formulário
    if form_filtro.is_valid():
        if form_filtro.cleaned_data.get('empresa'):
            relacionamentos = relacionamentos.filter(empresa=form_filtro.cleaned_data['empresa'])
        
        if form_filtro.cleaned_data.get('centro_custo'):
            relacionamentos = relacionamentos.filter(centro_custo=form_filtro.cleaned_data['centro_custo'])
        
        if form_filtro.cleaned_data.get('responsavel'):
            relacionamentos = relacionamentos.filter(responsavel=form_filtro.cleaned_data['responsavel'])
    
    # Busca por texto
    search = request.GET.get('search', '')
    if search:
        relacionamentos = relacionamentos.filter(
            Q(empresa__sigla__icontains=search) |
            Q(empresa__razao_social__icontains=search) |
            Q(centro_custo__codigo__icontains=search) |
            Q(centro_custo__nome__icontains=search) |
            Q(responsavel__first_name__icontains=search) |
            Q(responsavel__last_name__icontains=search)
        )
    
    # Paginação
    paginator = Paginator(relacionamentos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form_filtro': form_filtro,
        'search': search,
        'empresa_filtro': empresa_filtro,
    }
    
    return render(request, 'gestor/empresa_centro_custo_list.html', context)

@login_required
def empresa_centro_custo_create(request, sigla_empresa=None):
    """Criar novo relacionamento empresa x centro de custo"""
    
    empresa = None
    if sigla_empresa:
        empresa = get_object_or_404(Empresa, sigla=sigla_empresa)
    
    if request.method == 'POST':
        form = EmpresaCentroCustoForm(
            request.POST, 
            empresa_pk=empresa.pk if empresa else None
        )
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    relacionamento = form.save(commit=False)
                    relacionamento.usuario_criacao = request.user
                    relacionamento.save()
                    
                    messages.success(
                        request, 
                        f'Centro de custo {relacionamento.centro_custo.codigo} vinculado à empresa '
                        f'{relacionamento.empresa.sigla} com sucesso!'
                    )
                    
                    logger.info(
                        f'Relacionamento criado: {relacionamento.empresa.sigla} → '
                        f'{relacionamento.centro_custo.codigo} (responsável: {relacionamento.responsavel.first_name}) '
                        f'por {request.user}'
                    )
                    
                    if empresa:
                        return redirect('gestor:empresa_centro_custo_list', sigla_empresa=empresa.sigla)
                    else:
                        return redirect('gestor:empresa_centro_custo_list')
                        
            except Exception as e:
                messages.error(request, f'Erro ao criar relacionamento: {str(e)}')
                logger.error(f'Erro ao criar relacionamento empresa x centro custo: {str(e)}')
        else:
            messages.error(request, 'Erro ao criar relacionamento. Verifique os dados.')
    else:
        form = EmpresaCentroCustoForm(empresa_pk=empresa.pk if empresa else None)
    
    context = {
        'form': form,
        'title': 'Vincular Centro de Custo',
        'empresa': empresa,
        'is_create': True
    }
    
    return render(request, 'gestor/empresa_centro_custo_form.html', context)

@login_required
def empresa_centro_custo_update(request, pk):
    """Editar relacionamento empresa x centro de custo"""
    
    relacionamento = get_object_or_404(EmpresaCentroCusto, pk=pk)
    
    # Guardar valores originais para log
    valores_originais = {
        'responsavel': relacionamento.responsavel.first_name,
        'data_inicio': relacionamento.data_inicio,
        'data_fim': relacionamento.data_fim,
        'ativo': relacionamento.ativo,
        'observacoes': relacionamento.observacoes
    }
    
    if request.method == 'POST':
        form = EmpresaCentroCustoForm(request.POST, instance=relacionamento)
        
        if form.is_valid():
            try:
                relacionamento_atualizado = form.save()
                
                # Log de alterações
                alteracoes = []
                for campo, valor_original in valores_originais.items():
                    valor_novo = getattr(relacionamento_atualizado, campo)
                    if campo == 'responsavel':
                        valor_novo = valor_novo.first_name
                    
                    if valor_original != valor_novo:
                        alteracoes.append(f"{campo}: {valor_original} → {valor_novo}")
                
                if alteracoes:
                    logger.info(
                        f'Relacionamento {relacionamento.empresa.sigla} → {relacionamento.centro_custo.codigo} '
                        f'alterado por {request.user}: {", ".join(alteracoes)}'
                    )
                
                messages.success(
                    request,
                    f'Relacionamento {relacionamento.empresa.sigla} → {relacionamento.centro_custo.codigo} '
                    'atualizado com sucesso!'
                )
                
                return redirect('gestor:empresa_centro_custo_list')
                
            except Exception as e:
                messages.error(request, f'Erro ao atualizar relacionamento: {str(e)}')
                logger.error(f'Erro ao atualizar relacionamento {pk}: {str(e)}')
        else:
            messages.error(request, 'Erro ao atualizar relacionamento. Verifique os dados.')
    else:
        form = EmpresaCentroCustoForm(instance=relacionamento)
    
    context = {
        'form': form,
        'title': 'Editar Relacionamento',
        'relacionamento': relacionamento,
        'is_create': False
    }
    
    return render(request, 'gestor/empresa_centro_custo_form.html', context)

@login_required
def empresa_centro_custo_delete(request, pk):
    """Deletar relacionamento empresa x centro de custo"""
    
    relacionamento = get_object_or_404(EmpresaCentroCusto, pk=pk)
    
    if request.method == 'POST':
        empresa_sigla = relacionamento.empresa.sigla
        centro_custo_codigo = relacionamento.centro_custo.codigo
        
        try:
            relacionamento.delete()
            messages.success(
                request,
                f'Relacionamento {empresa_sigla} → {centro_custo_codigo} excluído com sucesso!'
            )
            logger.info(
                f'Relacionamento excluído: {empresa_sigla} → {centro_custo_codigo} por {request.user}'
            )
            
            return redirect('gestor:empresa_centro_custo_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao excluir relacionamento: {str(e)}')
            logger.error(f'Erro ao excluir relacionamento {pk}: {str(e)}')
            return redirect('gestor:empresa_centro_custo_list')
    
    context = {
        'relacionamento': relacionamento,
    }
    
    return render(request, 'gestor/empresa_centro_custo_delete.html', context)

# ===== API ENDPOINTS =====

@login_required
def api_empresa_centros_custo(request, sigla_empresa):
    """API para listar centros de custo de uma empresa"""
    
    try:
        empresa = Empresa.objects.get(sigla=sigla_empresa)
        relacionamentos = empresa.get_centros_custo_ativos()
        
        data = {
            'success': True,
            'empresa': {
                'sigla': empresa.sigla,
                'nome': empresa.nome_display,
            },
            'centros_custo': [
                {
                    'id': rel.pk,
                    'centro_custo': {
                        'codigo': rel.centro_custo.codigo,
                        'nome': rel.centro_custo.nome,
                        'tipo': rel.centro_custo.get_tipo_display(),
                    },
                    'responsavel': {
                        'id': rel.responsavel.pk,
                        'nome': str(rel.responsavel),
                    },
                    'periodo': rel.periodo_display,
                    'ativo': rel.ativo,
                }
                for rel in relacionamentos
            ]
        }
        
        return JsonResponse(data)
        
    except Empresa.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Empresa não encontrada'})
    except Exception as e:
        logger.error(f'Erro na API de centros de custo: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Erro interno'})

@login_required
def api_centro_custo_empresas(request, codigo_centro):
    """API para listar empresas vinculadas a um centro de custo"""
    
    try:
        centro_custo = CentroCusto.objects.get(codigo=codigo_centro)
        relacionamentos = centro_custo.get_empresas_vinculadas()
        
        data = {
            'success': True,
            'centro_custo': {
                'codigo': centro_custo.codigo,
                'nome': centro_custo.nome,
                'tipo': centro_custo.get_tipo_display(),
            },
            'empresas': [
                {
                    'id': rel.pk,
                    'empresa': {
                        'sigla': rel.empresa.sigla,
                        'nome': rel.empresa.nome_display,
                    },
                    'responsavel': {
                        'id': rel.responsavel.pk,
                        'nome': str(rel.responsavel),
                    },
                    'periodo': rel.periodo_display,
                    'ativo': rel.ativo,
                }
                for rel in relacionamentos
            ]
        }
        
        return JsonResponse(data)
        
    except CentroCusto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Centro de custo não encontrado'})
    except Exception as e:
        logger.error(f'Erro na API de empresas do centro: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Erro interno'})