# gestor/views.py - Views completas do SynchroBI

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import logging

from core.models import Usuario, Unidade, ParametroSistema, Empresa
from core.forms import UsuarioForm, UnidadeForm, ParametroSistemaForm, EmpresaForm

logger = logging.getLogger('synchrobi')

# ===== DASHBOARD =====
@login_required
def home(request):
    """Dashboard principal do gestor"""
    
    # Estatísticas básicas
    unidades_ativas = list(Unidade.objects.filter(ativa=True).prefetch_related('sub_unidades'))
    total_unidades = len(unidades_ativas)
    
    # Contar sintéticas e analíticas
    unidades_sinteticas = sum(1 for u in unidades_ativas if u.tem_sub_unidades)
    unidades_analiticas = total_unidades - unidades_sinteticas
    
    total_usuarios = Usuario.objects.filter(is_active=True).count()
    total_parametros = ParametroSistema.objects.filter(ativo=True).count()
    
    # Unidades recentes
    unidades_recentes = Unidade.objects.filter(ativa=True).order_by('-data_criacao')[:5]
    
    # Parâmetros críticos
    parametros_criticos = ParametroSistema.objects.filter(
        ativo=True, categoria='financeiro'
    ).order_by('nome')[:5]
    
    context = {
        'total_unidades': total_unidades,
        'unidades_sinteticas': unidades_sinteticas,
        'unidades_analiticas': unidades_analiticas,
        'total_usuarios': total_usuarios,
        'total_parametros': total_parametros,
        'unidades_recentes': unidades_recentes,
        'parametros_criticos': parametros_criticos,
    }
    
    return render(request, 'gestor/dashboard.html', context)

@login_required
def dashboard(request):
    """Alias para home"""
    return home(request)

# ===== CRUD UNIDADES =====

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

# ===== CRUD USUÁRIOS =====

@login_required
def usuario_list(request):
    """Lista de usuários"""
    search = request.GET.get('search', '')
    nivel = request.GET.get('nivel', '')
    ativo = request.GET.get('ativo', '')
    
    usuarios = Usuario.objects.all().order_by('first_name', 'last_name')
    
    if search:
        usuarios = usuarios.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    if nivel:
        usuarios = usuarios.filter(nivel=nivel)
        
    if ativo:
        usuarios = usuarios.filter(is_active=(ativo == 'true'))
    
    # Paginação
    paginator = Paginator(usuarios, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opções para filtros
    niveis_disponiveis = Usuario.NIVEL_CHOICES
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'nivel': nivel,
        'ativo': ativo,
        'niveis_disponiveis': niveis_disponiveis,
    }
    return render(request, 'gestor/usuario_list.html', context)

@login_required
def usuario_create(request):
    """Criar novo usuário"""
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário criado com sucesso!')
            return redirect('gestor:usuario_list')
        else:
            messages.error(request, 'Erro ao criar usuário. Verifique os dados.')
    else:
        form = UsuarioForm()
    
    context = {'form': form, 'title': 'Novo Usuário'}
    return render(request, 'gestor/usuario_form.html', context)

@login_required
def usuario_detail(request, pk):
    """Detalhes do usuário"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    context = {'usuario': usuario}
    return render(request, 'gestor/usuario_detail.html', context)

@login_required
def usuario_update(request, pk):
    """Editar usuário"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário atualizado com sucesso!')
            return redirect('gestor:usuario_list')
        else:
            messages.error(request, 'Erro ao atualizar usuário. Verifique os dados.')
    else:
        form = UsuarioForm(instance=usuario)
    
    context = {'form': form, 'title': 'Editar Usuário', 'usuario': usuario}
    return render(request, 'gestor/usuario_form.html', context)

@login_required
def usuario_delete(request, pk):
    """Deletar usuário"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        # Não permitir excluir superuser ou o próprio usuário
        if usuario.is_superuser:
            messages.error(request, 'Não é possível excluir um superusuário.')
            return redirect('gestor:usuario_detail', pk=pk)
        
        if usuario == request.user:
            messages.error(request, 'Não é possível excluir seu próprio usuário.')
            return redirect('gestor:usuario_detail', pk=pk)
        
        nome = usuario.get_full_name() or usuario.username
        usuario.delete()
        messages.success(request, f'Usuário "{nome}" excluído com sucesso!')
        return redirect('gestor:usuario_list')
    
    context = {'usuario': usuario}
    return render(request, 'gestor/usuario_confirm_delete.html', context)

# ===== CRUD PARÂMETROS =====

@login_required
def parametro_list(request):
    """Lista de parâmetros do sistema"""
    search = request.GET.get('search', '')
    categoria = request.GET.get('categoria', '')
    tipo = request.GET.get('tipo', '')
    
    parametros = ParametroSistema.objects.all().order_by('categoria', 'nome')
    
    if search:
        parametros = parametros.filter(
            Q(codigo__icontains=search) |
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )
    
    if categoria:
        parametros = parametros.filter(categoria=categoria)
    
    if tipo:
        parametros = parametros.filter(tipo=tipo)
    
    # Paginação
    paginator = Paginator(parametros, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opções para filtros
    categorias_disponiveis = ParametroSistema.objects.values_list(
        'categoria', flat=True
    ).distinct().order_by('categoria')
    tipos_disponiveis = ParametroSistema.TIPO_CHOICES
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'categoria': categoria,
        'tipo': tipo,
        'categorias_disponiveis': categorias_disponiveis,
        'tipos_disponiveis': tipos_disponiveis,
    }
    return render(request, 'gestor/parametro_list.html', context)

@login_required
def parametro_create(request):
    """Criar novo parâmetro"""
    if request.method == 'POST':
        form = ParametroSistemaForm(request.POST)
        if form.is_valid():
            parametro = form.save(commit=False)
            parametro.usuario_alteracao = request.user
            parametro.save()
            messages.success(request, f'Parâmetro "{parametro.nome}" criado com sucesso!')
            return redirect('gestor:parametro_list')
        else:
            messages.error(request, 'Erro ao criar parâmetro. Verifique os dados.')
    else:
        form = ParametroSistemaForm()
    
    context = {'form': form, 'title': 'Novo Parâmetro'}
    return render(request, 'gestor/parametro_form.html', context)

@login_required
def parametro_detail(request, codigo):
    """Detalhes do parâmetro"""
    parametro = get_object_or_404(ParametroSistema, codigo=codigo)
    
    context = {'parametro': parametro}
    return render(request, 'gestor/parametro_detail.html', context)

@login_required
def parametro_update(request, codigo):
    """Editar parâmetro"""
    parametro = get_object_or_404(ParametroSistema, codigo=codigo)
    
    if request.method == 'POST':
        form = ParametroSistemaForm(request.POST, instance=parametro)
        if form.is_valid():
            parametro = form.save(commit=False)
            parametro.usuario_alteracao = request.user
            parametro.save()
            messages.success(request, f'Parâmetro "{parametro.nome}" atualizado com sucesso!')
            return redirect('gestor:parametro_list')
        else:
            messages.error(request, 'Erro ao atualizar parâmetro. Verifique os dados.')
    else:
        form = ParametroSistemaForm(instance=parametro)
    
    context = {'form': form, 'title': 'Editar Parâmetro', 'parametro': parametro}
    return render(request, 'gestor/parametro_form.html', context)

@login_required
def parametro_delete(request, codigo):
    """Deletar parâmetro"""
    parametro = get_object_or_404(ParametroSistema, codigo=codigo)
    
    # Verificar se parâmetro é editável
    if not parametro.editavel:
        messages.error(request, 'Este parâmetro não pode ser excluído.')
        return redirect('gestor:parametro_detail', codigo=codigo)
    
    if request.method == 'POST':
        nome = parametro.nome
        parametro.delete()
        messages.success(request, f'Parâmetro "{nome}" excluído com sucesso!')
        return redirect('gestor:parametro_list')
    
    context = {'parametro': parametro}
    return render(request, 'gestor/parametro_confirm_delete.html', context)

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
def api_parametro_valor(request, codigo):
    """API para buscar valor de um parâmetro"""
    try:
        valor = ParametroSistema.get_parametro(codigo)
        if valor is None:
            return JsonResponse({'success': False, 'error': 'Parâmetro não encontrado'})
        
        return JsonResponse({
            'success': True, 
            'codigo': codigo,
            'valor': valor
        })
        
    except Exception as e:
        logger.error(f'Erro na API de parâmetro: {str(e)}')
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


# ===== CRUD EMPRESAS =====
# Adicionar ao gestor/views.py - Views para CRUD de Empresas Simplificadas
# Adicionar ao gestor/views.py - Views para CRUD de Empresas Simplificadas

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