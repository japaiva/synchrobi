# gestor/views/contacontabil.py - CRUD de Contas Contábeis

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
import logging

from core.models import ContaContabil
from core.forms import ContaContabilForm

logger = logging.getLogger('synchrobi')

@login_required
def contacontabil_list(request):
    """Lista de contas contábeis com filtros"""
    search = request.GET.get('search', '')
    nivel = request.GET.get('nivel', '')
    ativa = request.GET.get('ativa', '')
    
    contas = ContaContabil.objects.select_related('conta_pai').filter(ativa=True)
    
    if search:
        contas = contas.filter(
            Q(codigo__icontains=search) |
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )
    
    if nivel:
        contas = contas.filter(nivel=nivel)
    
    if ativa:
        contas = contas.filter(ativa=(ativa == 'true'))
    
    # Ordenar por código para manter hierarquia
    contas = contas.order_by('codigo')
    
    # Paginação
    paginator = Paginator(contas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opções para filtros
    niveis_disponiveis = sorted(set(ContaContabil.objects.values_list('nivel', flat=True)))
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'nivel': nivel,
        'ativa': ativa,
        'niveis_disponiveis': niveis_disponiveis,
    }
    return render(request, 'gestor/contacontabil_list.html', context)

@login_required
def contacontabil_create(request):
    """Criar nova conta contábil"""
    if request.method == 'POST':
        form = ContaContabilForm(request.POST)
        if form.is_valid():
            try:
                conta = form.save()
                messages.success(request, f'Conta contábil "{conta.nome}" criada com sucesso!')
                
                # Informar sobre o tipo determinado automaticamente
                tipo_msg = "Sintética (agrupadora)" if conta.e_sintetico else "Analítica (aceita lançamentos)"
                messages.info(request, f'Tipo determinado automaticamente: {tipo_msg}')
                
                logger.info(f'Conta contábil criada: {conta.codigo} - {conta.nome} por {request.user}')
                return redirect('gestor:contacontabil_list')
            except Exception as e:
                messages.error(request, f'Erro ao criar conta contábil: {str(e)}')
                logger.error(f'Erro ao criar conta contábil: {str(e)}')
        else:
            messages.error(request, 'Erro ao criar conta contábil. Verifique os dados.')
    else:
        form = ContaContabilForm()
    
    context = {
        'form': form, 
        'title': 'Nova Conta Contábil',
        'is_create': True
    }
    return render(request, 'gestor/contacontabil_form.html', context)

@login_required
def contacontabil_update(request, codigo):
    """Editar conta contábil"""
    conta = get_object_or_404(ContaContabil, codigo=codigo)
    
    # Guardar valores originais para log
    valores_originais = {
        'codigo': conta.codigo,
        'nome': conta.nome,
        'tipo': conta.get_tipo_display(),
        'ativa': conta.ativa
    }
    
    if request.method == 'POST':
        form = ContaContabilForm(request.POST, instance=conta)
        if form.is_valid():
            try:
                conta_atualizada = form.save()
                
                # Log de alterações
                alteracoes = []
                for campo, valor_original in valores_originais.items():
                    if campo == 'tipo':
                        valor_novo = conta_atualizada.get_tipo_display()
                    else:
                        valor_novo = getattr(conta_atualizada, campo)
                    
                    if valor_original != valor_novo:
                        alteracoes.append(f"{campo}: {valor_original} → {valor_novo}")
                
                if alteracoes:
                    logger.info(f'Conta contábil {conta.codigo} alterada por {request.user}: {", ".join(alteracoes)}')
                
                messages.success(request, f'Conta contábil "{conta_atualizada.nome}" atualizada com sucesso!')
                
                # Se o tipo mudou, informar
                if valores_originais['tipo'] != conta_atualizada.get_tipo_display():
                    messages.info(request, 
                        f'Tipo alterado automaticamente de {valores_originais["tipo"]} '
                        f'para {conta_atualizada.get_tipo_display()}')
                
                return redirect('gestor:contacontabil_list')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar conta contábil: {str(e)}')
                logger.error(f'Erro ao atualizar conta contábil {conta.codigo}: {str(e)}')
        else:
            messages.error(request, 'Erro ao atualizar conta contábil. Verifique os dados.')
    else:
        form = ContaContabilForm(instance=conta)
    
    context = {
        'form': form, 
        'title': 'Editar Conta Contábil', 
        'conta': conta,
        'is_create': False
    }
    return render(request, 'gestor/contacontabil_form.html', context)

@login_required
def contacontabil_delete(request, codigo):
    """Deletar conta contábil"""
    conta = get_object_or_404(ContaContabil, codigo=codigo)
    
    # Verificar se tem subcontas
    tem_subcontas = conta.tem_subcontas
    
    if request.method == 'POST':
        if tem_subcontas:
            messages.error(request, 
                f'Não é possível excluir a conta contábil "{conta.nome}" pois ela possui {conta.subcontas.count()} subconta(s).')
            return redirect('gestor:contacontabil_list')
        
        nome = conta.nome
        codigo_conta = conta.codigo
        tipo = conta.get_tipo_display()
        
        # Se tem pai, ele pode mudar de sintético para analítico
        conta_pai = conta.conta_pai
        
        try:
            conta.delete()
            messages.success(request, f'Conta contábil "{nome}" (código: {codigo_conta}, tipo: {tipo}) excluída com sucesso!')
            
            # Verificar se o pai mudou de tipo
            if conta_pai:
                conta_pai.refresh_from_db()
                if conta_pai.e_analitico:
                    messages.info(request, 
                        f'A conta pai "{conta_pai.nome}" foi automaticamente '
                        f'alterada para Analítica por não ter mais subcontas.')
            
            logger.info(f'Conta contábil excluída: {codigo_conta} - {nome} por {request.user}')
            return redirect('gestor:contacontabil_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir conta contábil: {str(e)}')
            logger.error(f'Erro ao excluir conta contábil {codigo_conta}: {str(e)}')
            return redirect('gestor:contacontabil_list')
    
    context = {
        'conta': conta,
        'tem_subcontas': tem_subcontas,
    }
    return render(request, 'gestor/contacontabil_delete.html', context)

# ===== API ENDPOINT =====

@login_required
def api_validar_codigo_contacontabil(request):
    """API para validar código de conta contábil em tempo real"""
    codigo = request.GET.get('codigo', '').strip()
    conta_codigo = request.GET.get('atual', None)
    
    if not codigo:
        return JsonResponse({'valid': False, 'error': 'Código é obrigatório'})
    
    # Verificar formato
    import re
    if not re.match(r'^[\d\.]+$', codigo):
        return JsonResponse({'valid': False, 'error': 'Código deve conter apenas números e pontos'})
    
    # Verificar duplicação
    query = ContaContabil.objects.filter(codigo=codigo)
    if conta_codigo:
        query = query.exclude(codigo=conta_codigo)
    
    if query.exists():
        return JsonResponse({'valid': False, 'error': 'Já existe uma conta contábil com este código'})
    
    # Verificar hierarquia
    info = {'valid': True}
    
    if '.' in codigo:
        partes = codigo.split('.')
        codigo_pai = '.'.join(partes[:-1])
        
        try:
            conta_pai = ContaContabil.objects.get(codigo=codigo_pai)
            info['pai'] = {
                'codigo': conta_pai.codigo,
                'nome': conta_pai.nome,
                'tipo_display': conta_pai.get_tipo_display()
            }
                
        except ContaContabil.DoesNotExist:
            info['valid'] = False
            info['error'] = f'Conta contábil pai com código "{codigo_pai}" não existe'
    else:
        info['pai'] = None
    
    # Calcular nível
    info['nivel'] = codigo.count('.') + 1
    
    return JsonResponse(info)