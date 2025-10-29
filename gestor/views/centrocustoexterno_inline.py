# gestor/views/centrocustoexterno_inline.py - CÓDIGOS ERP PARA CENTROS DE CUSTO

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import logging

from core.models import CentroCusto, CentroCustoExterno

logger = logging.getLogger('synchrobi')

@login_required
def centrocustoexterno_list(request):
    """Lista códigos externos de centros de custo"""

    centro_codigo = request.GET.get('centro')

    # Query base
    queryset = CentroCustoExterno.objects.select_related('centro_custo').order_by('codigo_externo')

    # Filtrar por centro se especificado
    if centro_codigo:
        queryset = queryset.filter(centro_custo__codigo=centro_codigo, ativo=True)

    # Paginação
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filtros': {'centro_codigo': centro_codigo}
    }

    # Se for AJAX, retornar template do modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestor/partials/centrocustoexterno_list_modal.html', context)

    return render(request, 'gestor/centrocustoexterno_list.html', context)

@login_required
def centrocustoexterno_create(request):
    """Criar novo código externo de centro de custo"""

    if request.method == 'POST':
        try:
            # Pegar dados do POST
            centro_custo_codigo = request.POST.get('centro_custo', '').strip()
            codigo_externo = request.POST.get('codigo_externo', '').strip()
            nome_externo = request.POST.get('nome_externo', '').strip()
            sistema_origem = request.POST.get('sistema_origem', '').strip()

            # Validações básicas
            if not centro_custo_codigo:
                return JsonResponse({'success': False, 'message': 'Centro de custo é obrigatório'})

            if not codigo_externo:
                return JsonResponse({'success': False, 'message': 'Código externo é obrigatório'})

            if not nome_externo:
                return JsonResponse({'success': False, 'message': 'Nome externo é obrigatório'})

            # Buscar centro de custo
            try:
                centro_custo = CentroCusto.objects.get(codigo=centro_custo_codigo)
            except CentroCusto.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Centro de custo não encontrado'})

            # Verificar duplicação
            if CentroCustoExterno.objects.filter(
                centro_custo=centro_custo,
                codigo_externo=codigo_externo,
                ativo=True
            ).exists():
                return JsonResponse({'success': False, 'message': f'Código "{codigo_externo}" já existe para este centro de custo'})

            # Criar centro externo
            centro_externo = CentroCustoExterno.objects.create(
                centro_custo=centro_custo,
                codigo_externo=codigo_externo,
                nome_externo=nome_externo,
                sistema_origem=sistema_origem,
                ativo=True
            )

            logger.info(f'Centro de custo externo criado: {centro_externo.codigo_externo} por {request.user}')

            return JsonResponse({
                'success': True,
                'message': f'Código "{centro_externo.codigo_externo}" criado com sucesso!'
            })

        except Exception as e:
            logger.error(f"Erro ao criar centro de custo externo: {str(e)}")
            return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})

    # GET - formulário simples
    centro_custo_codigo = request.GET.get('centro_custo')
    context = {'centro_custo_codigo': centro_custo_codigo}
    return render(request, 'gestor/centrocustoexterno_create_simple.html', context)

@login_required
def centrocustoexterno_update(request, pk):
    """Editar código externo de centro de custo"""

    centro_externo = get_object_or_404(CentroCustoExterno, pk=pk)

    if request.method == 'POST':
        try:
            # Pegar dados do POST
            codigo_externo = request.POST.get('codigo_externo', '').strip()
            nome_externo = request.POST.get('nome_externo', '').strip()
            sistema_origem = request.POST.get('sistema_origem', '').strip()

            # Validações básicas
            if not codigo_externo:
                return JsonResponse({'success': False, 'message': 'Código externo é obrigatório'})

            if not nome_externo:
                return JsonResponse({'success': False, 'message': 'Nome externo é obrigatório'})

            # Verificar duplicação (excluindo o atual)
            duplicata = CentroCustoExterno.objects.filter(
                centro_custo=centro_externo.centro_custo,
                codigo_externo=codigo_externo,
                ativo=True
            ).exclude(pk=pk)

            if duplicata.exists():
                return JsonResponse({'success': False, 'message': f'Código "{codigo_externo}" já existe para este centro de custo'})

            # Atualizar
            centro_externo.codigo_externo = codigo_externo
            centro_externo.nome_externo = nome_externo
            centro_externo.sistema_origem = sistema_origem
            centro_externo.save()

            logger.info(f'Centro de custo externo editado: {centro_externo.codigo_externo} por {request.user}')

            return JsonResponse({
                'success': True,
                'message': f'Código "{centro_externo.codigo_externo}" atualizado com sucesso!'
            })

        except Exception as e:
            logger.error(f"Erro ao editar centro de custo externo {pk}: {str(e)}")
            return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Método não permitido'})

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
