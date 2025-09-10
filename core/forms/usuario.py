# core/forms/usuario.py - FORMULÁRIO DE USUÁRIO

from django import forms
from django.contrib.auth.hashers import make_password

from core.models import Usuario

class UsuarioForm(forms.ModelForm):
    """Formulário simplificado para usuários SynchroBI"""
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        required=False,
        label="Confirmar Senha"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        required=False,
        label="Senha"
    )
    
    class Meta:
        model = Usuario
        fields = [
            'username', 'first_name', 'email', 'telefone',
            'nivel', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'data-mask': '(00) 00000-0000'
            }),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        labels = {
            'username': 'Código',
            'first_name': 'Nome',
            'email': 'Email',
            'telefone': 'Telefone',
            'nivel': 'Nível',
            'is_active': 'Ativo'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se estiver editando um usuário existente, não exigir senha
        if self.instance.pk:
            self.fields['password'].required = False
            self.fields['confirm_password'].required = False
            self.fields['password'].help_text = "Deixe em branco para manter a senha atual"
        else:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True
        
        # Tornar campos obrigatórios
        self.fields['username'].required = True
        self.fields['first_name'].required = True
        self.fields['nivel'].required = True
        
        # Choices do nível
        self.fields['nivel'].choices = [
            ('', '--- Selecione ---'),
            ('admin', 'Administrador'),
            ('gestor', 'Gestor'), 
            ('diretor', 'Diretor'),
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "As senhas não coincidem.")
        
        return cleaned_data
    
    def save(self, commit=True):
        usuario = super().save(commit=False)
        
        # Se uma senha foi fornecida, codificá-la
        password = self.cleaned_data.get('password')
        if password:
            usuario.password = make_password(password)
        
        # Limpar campos não utilizados
        if not usuario.centro_custo:
            usuario.centro_custo = ''
        if not usuario.unidade_negocio:
            usuario.unidade_negocio = ''
        if not usuario.last_name:
            usuario.last_name = ''
        
        if commit:
            usuario.save()
        
        return usuario