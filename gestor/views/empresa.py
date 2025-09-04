# gestor/views/empresa.py - CRUD de Empresas

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
import logging

from core.models import Empresa
from core.forms import EmpresaForm

logger = logging.getLogger('synchrobi')

@login_required
def empresa_list(request):
    """Lista de empresas com filtros"""
    search = request.GET.get('search', '')
    ativa = request.GET.get('ativa', '')
    
    empresas = Empresa.objects.all().order_by('sigla')
    
    if search:
        empresas = empresas.filter(
            Q(sigla__icontains=search) |
            Q(razao_social__icontains=search) |
            Q(nome_fantasia__icontains=search) |
            Q(cnpj__icontains=search)
        )
    
    if ativa:
        empresas = empresas.filter(ativa=(ativa == 'true'))
    
    # Paginação
    paginator = Paginator(empresas, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'ativa': ativa,
    }
    return render(request, 'gestor/empresa_list.html', context)

@login_required
def empresa_create(request):
    """Criar nova empresa"""
    if request.method == 'POST':
        form = EmpresaForm(request.POST)
        if form.is_valid():
            try:
                empresa = form.save()
                messages.success(request, f'Empresa "{empresa.nome_display}" criada com sucesso!')
                logger.info(f'Empresa criada: {empresa.sigla} - {empresa.razao_social} por {request.user}')
                return redirect('gestor:empresa_list')
            except Exception as e:
                messages.error(request, f'Erro ao criar empresa: {str(e)}')
                logger.error(f'Erro ao criar empresa: {str(e)}')
        else:
            messages.error(request, 'Erro ao criar empresa. Verifique os dados.')
    else:
        form = EmpresaForm()
    
    context = {
        'form': form, 
        'title': 'Nova Empresa',
        'is_create': True
    }
    return render(request, 'gestor/empresa_form.html', context)

@login_required
def empresa_update(request, sigla):
    """Editar empresa"""
    empresa = get_object_or_404(Empresa, sigla=sigla)
    
    # Guardar valores originais para log
    valores_originais = {
        'sigla': empresa.sigla,
        'razao_social': empresa.razao_social,
        'nome_fantasia': empresa.nome_fantasia,
        'cnpj': empresa.cnpj,
        'ativa': empresa.ativa
    }
    
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            try:
                empresa_atualizada = form.save()
                
                # Log de alterações
                alteracoes = []
                for campo, valor_original in valores_originais.items():
                    valor_novo = getattr(empresa_atualizada, campo)
                    if valor_original != valor_novo:
                        alteracoes.append(f"{campo}: {valor_original} → {valor_novo}")
                
                if alteracoes:
                    logger.info(f'Empresa {empresa.sigla} alterada por {request.user}: {", ".join(alteracoes)}')
                
                messages.success(request, f'Empresa "{empresa_atualizada.nome_display}" atualizada com sucesso!')
                return redirect('gestor:empresa_list')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar empresa: {str(e)}')
                logger.error(f'Erro ao atualizar empresa {empresa.sigla}: {str(e)}')
        else:
            messages.error(request, 'Erro ao atualizar empresa. Verifique os dados.')
    else:
        form = EmpresaForm(instance=empresa)
    
    context = {
        'form': form, 
        'title': 'Editar Empresa', 
        'empresa': empresa,
        'is_create': False
    }
    return render(request, 'gestor/empresa_form.html', context)

@login_required
def empresa_delete(request, sigla):
    """Deletar empresa"""
    empresa = get_object_or_404(Empresa, sigla=sigla)
    
    if request.method == 'POST':
        nome = empresa.nome_display
        sigla_empresa = empresa.sigla
        
        try:
            empresa.delete()
            messages.success(request, f'Empresa "{nome}" (sigla: {sigla_empresa}) excluída com sucesso!')
            logger.info(f'Empresa excluída: {sigla_empresa} - {nome} por {request.user}')
            return redirect('gestor:empresa_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir empresa: {str(e)}')
            logger.error(f'Erro ao excluir empresa {sigla_empresa}: {str(e)}')
            return redirect('gestor:empresa_list')
    
    context = {
        'empresa': empresa,
    }
    return render(request, 'gestor/empresa_delete.html', context)

# ===== API ENDPOINTS PARA EMPRESAS =====

@login_required
def api_validar_sigla_empresa(request):
    """API para validar sigla de empresa em tempo real"""
    sigla = request.GET.get('sigla', '').strip().upper()
    empresa_sigla = request.GET.get('atual', None)
    
    if not sigla:
        return JsonResponse({'valid': False, 'error': 'Sigla é obrigatória'})
    
    if len(sigla) > 15:
        return JsonResponse({'valid': False, 'error': 'Sigla deve ter no máximo 15 caracteres'})
    
    # Verificar duplicação
    query = Empresa.objects.filter(sigla=sigla)
    if empresa_sigla:
        query = query.exclude(sigla=empresa_sigla)
    
    if query.exists():
        return JsonResponse({'valid': False, 'error': 'Já existe uma empresa com esta sigla'})
    
    return JsonResponse({
        'valid': True,
        'sigla_formatada': sigla,
        'message': f'Sigla {sigla} disponível'
    })

@login_required
def api_validar_cnpj_empresa(request):
    """API para validar CNPJ de empresa em tempo real"""
    cnpj = request.GET.get('cnpj', '').strip()
    empresa_sigla = request.GET.get('atual', None)
    
    if not cnpj:
        return JsonResponse({'valid': False, 'error': 'CNPJ é obrigatório'})
    
    # Limpar formatação
    import re
    cnpj_limpo = re.sub(r'[^\d]', '', cnpj)
    
    if len(cnpj_limpo) != 14:
        return JsonResponse({'valid': False, 'error': 'CNPJ deve conter 14 dígitos'})
    
    # Verificar duplicação
    query = Empresa.objects.filter(cnpj__contains=cnpj_limpo)
    if empresa_sigla:
        query = query.exclude(sigla=empresa_sigla)
    
    if query.exists():
        empresa_existente = query.first()
        return JsonResponse({
            'valid': False, 
            'error': f'CNPJ já cadastrado para empresa: {empresa_existente.sigla} - {empresa_existente.razao_social}'
        })
    
    # Formatar CNPJ
    cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"
    
    return JsonResponse({
        'valid': True,
        'cnpj_formatado': cnpj_formatado,
        'message': 'CNPJ válido'
    })

@login_required
def api_empresa_info(request, sigla):
    """API para buscar informações de uma empresa"""
    try:
        empresa = Empresa.objects.get(sigla=sigla)
        
        data = {
            'success': True,
            'empresa': {
                'sigla': empresa.sigla,
                'razao_social': empresa.razao_social,
                'nome_fantasia': empresa.nome_fantasia,
                'nome_display': empresa.nome_display,
                'cnpj': empresa.cnpj_formatado,
                'ativa': empresa.ativa,
                'telefone': empresa.telefone,
                'email': empresa.email,
                'endereco_resumido': empresa.endereco_resumido,
            }
        }
        
        return JsonResponse(data)
        
    except Empresa.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Empresa não encontrada'})
    except Exception as e:
        logger.error(f'Erro na API de empresa: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Erro interno'})