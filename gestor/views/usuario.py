# gestor/views/usuario.py - Views simplificadas para seu sistema atual

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from core.models import Usuario
from core.forms import UsuarioForm

@login_required
def usuario_list(request):
    """Lista de usuários - visão simplificada"""
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
    """Criar usuário"""
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request, 
                f'Usuário "{usuario.username}" ({usuario.first_name}) criado com sucesso!'
            )
            return redirect('gestor:usuario_list')
        else:
            messages.error(
                request, 
                'Erro ao criar usuário. Verifique os dados informados.'
            )
    else:
        form = UsuarioForm()
    
    context = {
        'form': form,
        'title': 'Novo Usuário',
        'is_create': True
    }
    return render(request, 'gestor/usuario_form.html', context)

@login_required
def usuario_update(request, pk):
    """Editar usuário"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request, 
                f'Usuário "{usuario.username}" ({usuario.first_name}) atualizado com sucesso!'
            )
            return redirect('gestor:usuario_list')
        else:
            messages.error(
                request, 
                'Erro ao atualizar usuário. Verifique os dados informados.'
            )
    else:
        form = UsuarioForm(instance=usuario)
    
    context = {
        'form': form,
        'usuario': usuario,
        'title': f'Editar Usuário - {usuario.username}',
        'is_create': False
    }
    return render(request, 'gestor/usuario_form.html', context)

@login_required
def usuario_delete(request, pk):
    """Deletar usuário"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    # Verificar se não é o último admin
    if usuario.nivel == 'admin':
        total_admins = Usuario.objects.filter(nivel='admin', is_active=True).count()
        if total_admins <= 1:
            messages.error(
                request, 
                'Não é possível excluir o último administrador do sistema!'
            )
            return redirect('gestor:usuario_list')
    
    # Verificar se não está tentando excluir a si mesmo
    if usuario.id == request.user.id:
        messages.error(
            request, 
            'Você não pode excluir seu próprio usuário!'
        )
        return redirect('gestor:usuario_list')
    
    if request.method == 'POST':
        username = usuario.username
        nome = usuario.first_name
        usuario.delete()
        messages.success(
            request, 
            f'Usuário "{username}" ({nome}) excluído com sucesso!'
        )
        return redirect('gestor:usuario_list')
    
    context = {
        'usuario': usuario
    }
    return render(request, 'gestor/usuario_confirm_delete.html', context)

@login_required 
def usuario_toggle_status(request, pk):
    """Ativar/desativar usuário via AJAX ou POST"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    # Verificar se não está tentando desativar a si mesmo
    if usuario.id == request.user.id and usuario.is_active:
        messages.error(request, 'Você não pode desativar seu próprio usuário!')
        return redirect('gestor:usuario_list')
    
    # Verificar se não é o último admin ativo
    if usuario.nivel == 'admin' and usuario.is_active:
        total_admins_ativos = Usuario.objects.filter(
            nivel='admin', 
            is_active=True
        ).count()
        if total_admins_ativos <= 1:
            messages.error(
                request, 
                'Não é possível desativar o último administrador ativo!'
            )
            return redirect('gestor:usuario_list')
    
    # Alternar status
    usuario.is_active = not usuario.is_active
    usuario.save()
    
    status_texto = 'ativado' if usuario.is_active else 'desativado'
    messages.success(
        request,
        f'Usuário "{usuario.username}" ({usuario.first_name}) {status_texto} com sucesso!'
    )
    
    return redirect('gestor:usuario_list')