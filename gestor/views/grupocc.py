# gestor/views/grupocc.py - CRUD de Grupos CC

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
import logging

from core.models import GrupoCC
from core.forms import GrupoCCForm

logger = logging.getLogger('synchrobi')

@login_required
def grupocc_list(request):
    """Lista de grupos CC com filtros"""
    search = request.GET.get('search', '')
    ativa = request.GET.get('ativa', '')

    grupos = GrupoCC.objects.all().order_by('codigo')

    if search:
        grupos = grupos.filter(
            Q(codigo__icontains=search) |
            Q(descricao__icontains=search)
        )

    if ativa:
        grupos = grupos.filter(ativa=(ativa == 'true'))

    # Paginação
    paginator = Paginator(grupos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'ativa': ativa,
    }
    return render(request, 'gestor/grupocc_list.html', context)

@login_required
def grupocc_create(request):
    """Criar novo grupo CC"""
    if request.method == 'POST':
        form = GrupoCCForm(request.POST)
        if form.is_valid():
            try:
                grupo = form.save()
                messages.success(request, f'Grupo CC "{grupo.codigo} - {grupo.descricao}" criado com sucesso!')
                logger.info(f'Grupo CC criado: {grupo.codigo} - {grupo.descricao} por {request.user}')
                return redirect('gestor:grupocc_list')
            except Exception as e:
                messages.error(request, f'Erro ao criar Grupo CC: {str(e)}')
                logger.error(f'Erro ao criar Grupo CC: {str(e)}')
        else:
            messages.error(request, 'Erro ao criar Grupo CC. Verifique os dados.')
    else:
        form = GrupoCCForm()

    context = {
        'form': form,
        'title': 'Novo Grupo CC',
        'is_create': True
    }
    return render(request, 'gestor/grupocc_form.html', context)

@login_required
def grupocc_update(request, codigo):
    """Editar grupo CC"""
    grupo = get_object_or_404(GrupoCC, codigo=codigo)

    # Guardar valores originais para log
    valores_originais = {
        'codigo': grupo.codigo,
        'descricao': grupo.descricao,
        'ativa': grupo.ativa
    }

    if request.method == 'POST':
        form = GrupoCCForm(request.POST, instance=grupo)
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
                    logger.info(f'Grupo CC {grupo.codigo} alterado por {request.user}: {", ".join(alteracoes)}')

                messages.success(request, f'Grupo CC "{grupo_atualizado.codigo} - {grupo_atualizado.descricao}" atualizado com sucesso!')
                return redirect('gestor:grupocc_list')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar Grupo CC: {str(e)}')
                logger.error(f'Erro ao atualizar Grupo CC {grupo.codigo}: {str(e)}')
        else:
            messages.error(request, 'Erro ao atualizar Grupo CC. Verifique os dados.')
    else:
        form = GrupoCCForm(instance=grupo)

    context = {
        'form': form,
        'title': 'Editar Grupo CC',
        'grupo': grupo,
        'is_create': False
    }
    return render(request, 'gestor/grupocc_form.html', context)

@login_required
def grupocc_delete(request, codigo):
    """Deletar grupo CC"""
    grupo = get_object_or_404(GrupoCC, codigo=codigo)

    if request.method == 'POST':
        codigo_grupo = grupo.codigo
        descricao = grupo.descricao

        try:
            grupo.delete()
            messages.success(request, f'Grupo CC "{codigo_grupo} - {descricao}" excluído com sucesso!')
            logger.info(f'Grupo CC excluído: {codigo_grupo} - {descricao} por {request.user}')
            return redirect('gestor:grupocc_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir Grupo CC: {str(e)}')
            logger.error(f'Erro ao excluir Grupo CC {codigo_grupo}: {str(e)}')
            return redirect('gestor:grupocc_list')

    context = {
        'grupo': grupo,
    }
    return render(request, 'gestor/grupocc_delete.html', context)

# ===== API ENDPOINTS PARA GRUPOS CC =====

@login_required
def api_validar_codigo_grupocc(request):
    """API para validar código de grupo CC em tempo real"""
    codigo = request.GET.get('codigo', '').strip().upper()
    codigo_atual = request.GET.get('atual', None)

    if not codigo:
        return JsonResponse({'valid': False, 'error': 'Código é obrigatório'})

    if len(codigo) > 10:
        return JsonResponse({'valid': False, 'error': 'Código deve ter no máximo 10 caracteres'})

    # Verificar duplicação
    query = GrupoCC.objects.filter(codigo=codigo)
    if codigo_atual:
        query = query.exclude(codigo=codigo_atual)

    if query.exists():
        return JsonResponse({'valid': False, 'error': 'Já existe um Grupo CC com este código'})

    return JsonResponse({
        'valid': True,
        'codigo_formatado': codigo,
        'message': f'Código {codigo} disponível'
    })

@login_required
def api_grupocc_info(request, codigo):
    """API para buscar informações de um grupo CC"""
    try:
        grupo = GrupoCC.objects.get(codigo=codigo)

        data = {
            'success': True,
            'grupo': {
                'codigo': grupo.codigo,
                'descricao': grupo.descricao,
                'ativa': grupo.ativa,
            }
        }

        return JsonResponse(data)

    except GrupoCC.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Grupo CC não encontrado'})
    except Exception as e:
        logger.error(f'Erro na API de Grupo CC: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Erro interno'})
