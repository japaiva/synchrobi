# core/views.py - Views básicas do SynchroBI

from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

class PortalLoginView(LoginView):
    """
    View de login inteligente que redireciona baseado no nível do usuário
    """
    template_name = 'auth/login.html'  # Vamos criar este template
    
    def form_valid(self, form):
        user = form.get_user()
        print(f"Login bem-sucedido para: {user.username} (nível: {getattr(user, 'nivel', 'N/A')})")
        return super().form_valid(form)
    
    def get_success_url(self):
        """Determina URL de redirecionamento baseado no nível do usuário"""
        user = self.request.user
        
        print(f"Determinando redirecionamento para usuário: {user.username}")
        
        # Se é superuser, vai para gestor
        if user.is_superuser:
            print("Superuser - redirecionando para /gestor/")
            return '/gestor/'
        
        # Se não tem nível definido, vai para gestor (fallback seguro)
        if not hasattr(user, 'nivel') or not user.nivel:
            print("Usuário sem nível - redirecionando para /gestor/")
            return '/gestor/'
        
        # Redirecionamento baseado no nível
        if user.nivel in ['admin', 'gestor', 'diretor']:
            print(f"{user.nivel} - redirecionando para /gestor/")
            return '/gestor/'
        elif user.nivel in ['analista', 'contador']:
            print(f"{user.nivel} - redirecionando para /gestor/")
            return '/gestor/'  # Por enquanto todos vão para gestor
        else:
            print(f"Nível desconhecido ({user.nivel}) - redirecionando para /gestor/")
            return '/gestor/'
 
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'SynchroBI'
        return context

def home_view(request):
    """View da página inicial"""
    # Se usuário está logado, redirecionar para dashboard
    if request.user.is_authenticated:
        return redirect('gestor:home')
    
    return render(request, 'core/home.html')

@login_required
def perfil(request):
    """View do perfil do usuário"""
    # Determinar URL de volta baseada no nível do usuário
    if hasattr(request.user, 'nivel'):
        if request.user.nivel in ['admin', 'gestor', 'diretor']:
            back_url = 'gestor:home'
        elif request.user.nivel in ['analista', 'contador']:
            back_url = 'gestor:home'
        else:
            back_url = 'home'
    else:
        back_url = 'home'
    
    if request.method == 'POST':
        # Processar alterações do perfil
        usuario = request.user
        
        # Atualizar campos básicos
        usuario.first_name = request.POST.get('first_name', '')
        usuario.last_name = request.POST.get('last_name', '')
        usuario.email = request.POST.get('email', '')
        usuario.telefone = request.POST.get('telefone', '')
        
        # Processar nova senha se fornecida
        nova_senha = request.POST.get('nova_senha', '')
        if nova_senha:
            usuario.set_password(nova_senha)
        
        # Processar upload de foto se fornecida
        foto = request.FILES.get('foto')
        if foto:
            # Implementar upload de foto no futuro
            pass
        
        usuario.save()
        messages.success(request, 'Perfil atualizado com sucesso!')
        return redirect('perfil')
    
    context = {
        'usuario': request.user,
        'back_url': back_url,
    }
    
    return render(request, 'core/perfil.html', context)

def logout_view(request):
    """View de logout personalizada"""
    user_nivel = getattr(request.user, 'nivel', None) if request.user.is_authenticated else None
    logout(request)
    
    # Mensagem personalizada baseada no nível
    if user_nivel in ['analista', 'contador']:
        messages.success(request, 'Logout realizado com sucesso! Volte sempre.')
    elif user_nivel in ['admin', 'gestor', 'diretor']:
        messages.success(request, 'Sessão encerrada com sucesso!')
    else:
        messages.success(request, 'Até logo!')
    
    return redirect('login')