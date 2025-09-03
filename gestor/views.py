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

from core.models import Usuario, Unidade, ParametroSistema
from core.forms import UsuarioForm, UnidadeForm, ImportarUnidadesForm, ParametroSistemaForm

logger = logging.getLogger('synchrobi')

# ===== DASHBOARD =====

@login_required
def home(request):
    """Dashboard principal do gestor"""
    
    # Estatísticas básicas
    total_unidades = Unidade.objects.filter(ativa=True).count()
    unidades_sinteticas = Unidade.objects.filter(ativa=True, tipo='S').count()
    unidades_analiticas = Unidade.objects.filter(ativa=True, tipo='A').count()
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

# ===== CRUD UNIDADES =====

@login_required
def unidade_list(request):
    """Lista de unidades organizacionais"""
    search = request.GET.get('search', '')
    tipo = request.GET.get('tipo', '')
    nivel = request.GET.get('nivel', '')
    
    # Buscar todas as unidades com hierarquia
    unidades = Unidade.objects.select_related('unidade_pai', 'responsavel').filter(ativa=True)
    
    if search:
        unidades = unidades.filter(
            Q(codigo_allstrategy__icontains=search) |
            Q(codigo_interno__icontains=search) |
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )
    
    if tipo:
        unidades = unidades.filter(tipo=tipo)
    
    if nivel:
        unidades = unidades.filter(nivel=nivel)
    
    # Ordenar por código All Strategy para manter hierarquia
    unidades = unidades.order_by('codigo_allstrategy')
    
    # Paginação
    paginator = Paginator(unidades, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opções para filtros
    tipos_disponiveis = Unidade.TIPO_CHOICES
    niveis_disponiveis = sorted(set(Unidade.objects.values_list('nivel', flat=True)))
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'tipo': tipo,
        'nivel': nivel,
        'tipos_disponiveis': tipos_disponiveis,
        'niveis_disponiveis': niveis_disponiveis,
    }
    return render(request, 'gestor/unidade_list.html', context)

@login_required
def unidade_create(request):
    """Criar nova unidade"""
    if request.method == 'POST':
        form = UnidadeForm(request.POST)
        if form.is_valid():
            unidade = form.save()
            messages.success(request, f'Unidade "{unidade.nome}" criada com sucesso!')
            return redirect('gestor:unidade_list')
        else:
            messages.error(request, 'Erro ao criar unidade. Verifique os dados.')
    else:
        form = UnidadeForm()
    
    context = {'form': form, 'title': 'Nova Unidade'}
    return render(request, 'gestor/unidade_form.html', context)

@login_required
def unidade_detail(request, pk):
    """Detalhes da unidade"""
    unidade = get_object_or_404(Unidade, pk=pk)
    
    # Buscar sub-unidades diretas
    sub_unidades = unidade.sub_unidades.filter(ativa=True).order_by('codigo_allstrategy')
    
    # Caminho hierárquico
    caminho = unidade.caminho_hierarquico
    
    context = {
        'unidade': unidade,
        'sub_unidades': sub_unidades,
        'caminho': caminho,
    }
    return render(request, 'gestor/unidade_detail.html', context)

@login_required
def unidade_update(request, pk):
    """Editar unidade"""
    unidade = get_object_or_404(Unidade, pk=pk)
    
    if request.method == 'POST':
        form = UnidadeForm(request.POST, instance=unidade)
        if form.is_valid():
            form.save()
            messages.success(request, f'Unidade "{unidade.nome}" atualizada com sucesso!')
            return redirect('gestor:unidade_list')
        else:
            messages.error(request, 'Erro ao atualizar unidade. Verifique os dados.')
    else:
        form = UnidadeForm(instance=unidade)
    
    context = {'form': form, 'title': 'Editar Unidade', 'unidade': unidade}
    return render(request, 'gestor/unidade_form.html', context)

@login_required
def unidade_delete(request, pk):
    """Deletar unidade"""
    unidade = get_object_or_404(Unidade, pk=pk)
    
    # Verificar se tem sub-unidades
    tem_sub_unidades = unidade.sub_unidades.exists()
    
    if request.method == 'POST':
        if tem_sub_unidades:
            messages.error(request, 'Não é possível excluir uma unidade que possui sub-unidades.')
            return redirect('gestor:unidade_detail', pk=pk)
        
        nome = unidade.nome
        unidade.delete()
        messages.success(request, f'Unidade "{nome}" excluída com sucesso!')
        return redirect('gestor:unidade_list')
    
    context = {
        'unidade': unidade,
        'tem_sub_unidades': tem_sub_unidades,
    }
    return render(request, 'gestor/unidade_confirm_delete.html', context)

# ===== IMPORTAÇÃO DE UNIDADES =====

@login_required
def unidade_importar(request):
    """Importar unidades do All Strategy via Excel"""
    if request.method == 'POST':
        form = ImportarUnidadesForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = request.FILES['arquivo_excel']
            atualizar_existentes = form.cleaned_data['atualizar_existentes']
            limpar_base_antes = form.cleaned_data['limpar_base_antes']
            
            try:
                # Processar arquivo Excel
                import pandas as pd
                
                # Ler Excel
                df = pd.read_excel(arquivo)
                
                # Converter para formato esperado pelo método de importação
                dados_excel = df.to_dict('records')
                
                # Limpar base se solicitado
                if limpar_base_antes:
                    Unidade.objects.all().delete()
                    messages.info(request, 'Base de unidades limpa antes da importação.')
                
                # Importar
                resultado = Unidade.importar_do_allstrategy(dados_excel)
                
                # Mensagens de resultado
                messages.success(request, 
                    f'Importação concluída! '
                    f'{resultado["criadas"]} criadas, '
                    f'{resultado["atualizadas"]} atualizadas.'
                )
                
                if resultado['erros']:
                    messages.warning(request, 
                        f'{len(resultado["erros"])} erros encontrados. '
                        'Verifique o log para detalhes.'
                    )
                    logger.warning(f'Erros na importação de unidades: {resultado["erros"]}')
                
                return redirect('gestor:unidade_list')
                
            except Exception as e:
                logger.error(f'Erro na importação de unidades: {str(e)}')
                messages.error(request, f'Erro na importação: {str(e)}')
    else:
        form = ImportarUnidadesForm()
    
    context = {'form': form, 'title': 'Importar Unidades'}
    return render(request, 'gestor/unidade_importar.html', context)

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
    paginator = Paginator(parametros, 20)
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
def api_unidade_por_codigo(request, codigo):
    """API para buscar unidade por código (All Strategy ou interno)"""
    try:
        # Tentar por código All Strategy primeiro
        unidade = Unidade.objects.filter(
            Q(codigo_allstrategy=codigo) | Q(codigo_interno=codigo),
            ativa=True
        ).first()
        
        if not unidade:
            return JsonResponse({'success': False, 'error': 'Unidade não encontrada'})
        
        data = {
            'success': True,
            'unidade': {
                'id': unidade.id,
                'codigo_allstrategy': unidade.codigo_allstrategy,
                'codigo_interno': unidade.codigo_interno or '',
                'nome': unidade.nome,
                'tipo': unidade.tipo,
                'tipo_display': unidade.get_tipo_display(),
                'nivel': unidade.nivel,
                'nome_completo': unidade.nome_completo,
                'unidade_pai': {
                    'id': unidade.unidade_pai.id,
                    'nome': unidade.unidade_pai.nome,
                    'codigo': unidade.unidade_pai.codigo_allstrategy
                } if unidade.unidade_pai else None,
                'responsavel': {
                    'id': unidade.responsavel.id,
                    'nome': unidade.responsavel.get_full_name() or unidade.responsavel.username
                } if unidade.responsavel else None
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f'Erro na API de unidade por código: {str(e)}')
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
def unidade_arvore_json(request):
    """API para retornar árvore de unidades em JSON"""
    try:
        # Buscar todas as unidades ativas organizadas hierarquicamente
        unidades = Unidade.objects.filter(ativa=True).select_related('unidade_pai').order_by('codigo_allstrategy')
        
        # Construir estrutura hierárquica
        def build_tree_node(unidade):
            return {
                'id': unidade.id,
                'codigo_allstrategy': unidade.codigo_allstrategy,
                'codigo_interno': unidade.codigo_interno or '',
                'nome': unidade.nome,
                'tipo': unidade.tipo,
                'tipo_display': unidade.get_tipo_display(),
                'nivel': unidade.nivel,
                'text': f"{unidade.codigo_display} - {unidade.nome}",  # Para jsTree
                'parent': unidade.unidade_pai.id if unidade.unidade_pai else '#',  # Para jsTree
                'state': {
                    'opened': unidade.nivel <= 2,  # Abrir primeiros 2 níveis por padrão
                    'selected': False
                },
                'icon': 'folder' if unidade.tipo == 'S' else 'file',
                'li_attr': {
                    'data-codigo': unidade.codigo_allstrategy,
                    'data-tipo': unidade.tipo
                }
            }
        
        # Converter para formato jsTree
        tree_data = [build_tree_node(unidade) for unidade in unidades]
        
        return JsonResponse({
            'success': True,
            'data': tree_data,
            'total': len(tree_data)
        })
        
    except Exception as e:
        logger.error(f'Erro na API de árvore de unidades: {str(e)}')
        return JsonResponse({
            'success': False, 
            'error': 'Erro ao carregar árvore de unidades',
            'data': []
        })