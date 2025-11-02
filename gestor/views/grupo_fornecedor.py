# gestor/views/grupo_fornecedor.py - Views completas para grupo de fornecedor

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
import logging

from core.models import GrupoFornecedor
from core.forms import GrupoFornecedorForm

logger = logging.getLogger('synchrobi')

@login_required
def grupo_fornecedor_list(request):
    """Lista de grupos de fornecedores com filtros"""
    search = request.GET.get('search', '')
    ativo = request.GET.get('ativo', '')

    grupos = GrupoFornecedor.objects.annotate(
        total_fornecedores_count=Count('fornecedores')
    ).order_by('nome')

    if search:
        grupos = grupos.filter(
            Q(codigo__icontains=search) |
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )

    if ativo:
        grupos = grupos.filter(ativo=(ativo == 'true'))

    # Paginação
    paginator = Paginator(grupos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'ativo': ativo,
    }
    return render(request, 'gestor/grupo_fornecedor_list.html', context)

@login_required
def grupo_fornecedor_create(request):
    """Criar novo grupo de fornecedor"""
    if request.method == 'POST':
        form = GrupoFornecedorForm(request.POST)
        if form.is_valid():
            try:
                grupo = form.save()
                messages.success(request, f'Grupo "{grupo.nome}" criado com sucesso!')
                logger.info(f'Grupo de Fornecedor criado: {grupo.codigo} - {grupo.nome} por {request.user}')
                return redirect('gestor:grupo_fornecedor_list')
            except Exception as e:
                messages.error(request, f'Erro ao criar grupo: {str(e)}')
                logger.error(f'Erro ao criar grupo de fornecedor: {str(e)}')
        else:
            messages.error(request, 'Erro ao criar grupo. Verifique os dados.')
    else:
        form = GrupoFornecedorForm()

    context = {
        'form': form,
        'title': 'Novo Grupo de Fornecedor',
        'is_create': True
    }
    return render(request, 'gestor/grupo_fornecedor_form.html', context)

@login_required
def grupo_fornecedor_update(request, codigo):
    """Editar grupo de fornecedor"""
    grupo = get_object_or_404(GrupoFornecedor, codigo=codigo)

    # Guardar valores originais para log
    valores_originais = {
        'nome': grupo.nome,
        'descricao': grupo.descricao,
        'ativo': grupo.ativo
    }

    if request.method == 'POST':
        form = GrupoFornecedorForm(request.POST, instance=grupo)
        if form.is_valid():
            try:
                grupo_atualizado = form.save()

                # Log de alterações
                alteracoes = []
                for campo, valor_original in valores_originais.items():
                    valor_novo = getattr(grupo_atualizado, campo)
                    if valor_original != valor_novo:
                        alteracoes.append(f"{campo}: {valor_original} → {valor_novo}")

                if alteracoes:
                    logger.info(f'Grupo {grupo.codigo} alterado por {request.user}: {", ".join(alteracoes)}')

                messages.success(request, f'Grupo "{grupo_atualizado.nome}" atualizado com sucesso!')
                return redirect('gestor:grupo_fornecedor_list')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar grupo: {str(e)}')
                logger.error(f'Erro ao atualizar grupo {grupo.codigo}: {str(e)}')
        else:
            messages.error(request, 'Erro ao atualizar grupo. Verifique os dados.')
    else:
        form = GrupoFornecedorForm(instance=grupo)

    context = {
        'form': form,
        'title': 'Editar Grupo de Fornecedor',
        'grupo': grupo,
        'is_create': False
    }
    return render(request, 'gestor/grupo_fornecedor_form.html', context)

@login_required
def grupo_fornecedor_delete(request, codigo):
    """Deletar grupo de fornecedor"""
    grupo = get_object_or_404(GrupoFornecedor, codigo=codigo)

    # Contar fornecedores associados
    fornecedores_count = grupo.fornecedores.count()

    if request.method == 'POST':
        nome_grupo = grupo.nome
        codigo_grupo = grupo.codigo

        try:
            # Log antes da exclusão
            if fornecedores_count > 0:
                logger.warning(
                    f'Grupo {codigo_grupo} - {nome_grupo} excluído com {fornecedores_count} fornecedor(es) associado(s) por {request.user}'
                )

            grupo.delete()

            # Mensagem de sucesso
            if fornecedores_count > 0:
                messages.warning(
                    request,
                    f'Grupo "{nome_grupo}" excluído! '
                    f'{fornecedores_count} fornecedor(es) ficaram sem grupo.'
                )
            else:
                messages.success(
                    request,
                    f'Grupo "{nome_grupo}" excluído com sucesso!'
                )

            logger.info(f'Grupo excluído: {codigo_grupo} - {nome_grupo} por {request.user}')
            return redirect('gestor:grupo_fornecedor_list')

        except Exception as e:
            messages.error(request, f'Erro ao excluir grupo: {str(e)}')
            logger.error(f'Erro ao excluir grupo {codigo_grupo}: {str(e)}')
            return redirect('gestor:grupo_fornecedor_list')

    context = {
        'grupo': grupo,
        'fornecedores_count': fornecedores_count
    }
    return render(request, 'gestor/grupo_fornecedor_delete.html', context)

@login_required
def grupo_fornecedor_detail(request, codigo):
    """Detalhes do grupo de fornecedor com lista de fornecedores"""
    grupo = get_object_or_404(GrupoFornecedor, codigo=codigo)

    # Buscar fornecedores do grupo
    fornecedores = grupo.fornecedores.all().order_by('razao_social')

    # Paginação
    paginator = Paginator(fornecedores, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'grupo': grupo,
        'page_obj': page_obj,
        'total_fornecedores': fornecedores.count(),
    }
    return render(request, 'gestor/grupo_fornecedor_detail.html', context)
