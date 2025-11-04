# gestor/views/centrocustoexterno_inline.py - CÓDIGOS ERP PARA CENTROS DE CUSTO

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import logging

from core.models import CentroCusto, CentroCustoExterno, GrupoCC
from core.forms import CentroCustoExternoForm

logger = logging.getLogger('synchrobi')

@login_required
def centrocustoexterno_list(request):
    """Lista códigos externos de centros de custo"""

    centro_codigo = request.GET.get('centro')

    # Query base
    queryset = CentroCustoExterno.objects.select_related(
        'centro_custo',
        'codigo_responsavel',
        'codigo_beneficiado'
    ).order_by('codigo_externo')

    # Filtrar por centro se especificado
    if centro_codigo:
        queryset = queryset.filter(centro_custo__codigo=centro_codigo)

    # Paginação (100 itens por página)
    paginator = Paginator(queryset, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Buscar grupos CC ativos para os selects
    grupos_cc = GrupoCC.objects.filter(ativa=True).order_by('codigo')

    context = {
        'page_obj': page_obj,
        'filtros': {'centro_codigo': centro_codigo},
        'grupos_cc': grupos_cc
    }

    # Se for AJAX, retornar template do modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/centrocustoexterno_list_modal.html', context)

    return render(request, 'gestor/centrocustoexterno_list.html', context)

@login_required
def centrocustoexterno_create(request):
    """Criar novo código externo de centro de custo"""

    centro_custo_codigo = request.GET.get('centro_custo') if request.method == 'GET' else None

    if request.method == 'POST':
        form = CentroCustoExternoForm(request.POST, centro_custo_codigo=centro_custo_codigo)

        if form.is_valid():
            try:
                centro_externo = form.save(commit=False)
                form._user = request.user
                centro_externo = form.save()

                logger.info(f'Centro de custo externo criado: {centro_externo.codigo_externo} por {request.user}')

                return JsonResponse({
                    'success': True,
                    'message': f'Código "{centro_externo.codigo_externo}" criado com sucesso!'
                })
            except Exception as e:
                logger.error(f"Erro ao criar centro de custo externo: {str(e)}")
                return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})
        else:
            # Retornar erros do formulário
            errors = []
            for field, error_list in form.errors.items():
                for error in error_list:
                    if field == '__all__':
                        errors.append(error)
                    else:
                        field_label = form.fields[field].label or field
                        errors.append(f"{field_label}: {error}")

            return JsonResponse({
                'success': False,
                'message': ' | '.join(errors)
            })

    # GET - formulário
    form = CentroCustoExternoForm(centro_custo_codigo=centro_custo_codigo)
    context = {
        'form': form,
        'centro_custo_codigo': centro_custo_codigo
    }
    return render(request, 'gestor/centrocustoexterno_create_simple.html', context)

@login_required
def centrocustoexterno_update(request, pk):
    """Editar código externo de centro de custo"""

    centro_externo = get_object_or_404(CentroCustoExterno, pk=pk)

    if request.method == 'POST':
        form = CentroCustoExternoForm(request.POST, instance=centro_externo)

        if form.is_valid():
            try:
                form._user = request.user
                centro_externo = form.save()

                logger.info(f'Centro de custo externo editado: {centro_externo.codigo_externo} por {request.user}')

                return JsonResponse({
                    'success': True,
                    'message': f'Código "{centro_externo.codigo_externo}" atualizado com sucesso!'
                })
            except Exception as e:
                logger.error(f"Erro ao editar centro de custo externo {pk}: {str(e)}")
                return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})
        else:
            # Retornar erros do formulário
            errors = []
            for field, error_list in form.errors.items():
                for error in error_list:
                    if field == '__all__':
                        errors.append(error)
                    else:
                        field_label = form.fields[field].label or field
                        errors.append(f"{field_label}: {error}")

            return JsonResponse({
                'success': False,
                'message': ' | '.join(errors)
            })

    # GET - retornar formulário para edição
    form = CentroCustoExternoForm(instance=centro_externo)
    context = {
        'form': form,
        'centro_externo': centro_externo
    }
    return render(request, 'gestor/centrocustoexterno_update.html', context)

@login_required
@require_POST
def api_centrocustoexterno_delete(request, pk):
    """Excluir código externo de centro de custo"""

    try:
        centro_externo = get_object_or_404(CentroCustoExterno, pk=pk)
        codigo_externo = centro_externo.codigo_externo

        centro_externo.delete()

        logger.info(f'Centro de custo externo excluído: {codigo_externo} por {request.user}')

        return JsonResponse({
            'success': True,
            'message': f'Código "{codigo_externo}" excluído com sucesso!'
        })

    except Exception as e:
        logger.error(f'Erro ao excluir centro de custo externo {pk}: {str(e)}')
        return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})

# Funções auxiliares para compatibilidade
@login_required
def api_validar_codigo_externo_cc(request):
    """Validar código externo de centro de custo"""

    codigo_externo = request.GET.get('codigo_externo', '').strip()
    centro_custo_codigo = request.GET.get('centro_custo', '').strip()
    centro_externo_id = request.GET.get('atual', None)

    if not codigo_externo:
        return JsonResponse({'valid': False, 'error': 'Código externo é obrigatório'})

    if not centro_custo_codigo:
        return JsonResponse({'valid': False, 'error': 'Centro de custo é obrigatório'})

    try:
        centro_custo = CentroCusto.objects.get(codigo=centro_custo_codigo)
    except CentroCusto.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Centro de custo não encontrado'})

    # Verificar duplicação
    query = CentroCustoExterno.objects.filter(
        centro_custo=centro_custo,
        codigo_externo=codigo_externo,
        ativo=True
    )

    if centro_externo_id:
        query = query.exclude(pk=centro_externo_id)

    if query.exists():
        return JsonResponse({
            'valid': False,
            'error': f'Código "{codigo_externo}" já existe para o centro {centro_custo.codigo}'
        })

    return JsonResponse({
        'valid': True,
        'centro_custo': {
            'codigo': centro_custo.codigo,
            'nome': centro_custo.nome
        }
    })
