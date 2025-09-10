# core/forms/fornecedor.py - FORMULÁRIO DE FORNECEDOR

from django import forms
from core.models import Fornecedor

class FornecedorForm(forms.ModelForm):
    """Formulário para criar/editar fornecedores"""
    
    class Meta:
        model = Fornecedor
        fields = [
            'codigo', 'razao_social', 'nome_fantasia', 'cnpj_cpf',
            'telefone', 'email', 'endereco', 'ativo'
        ]
        
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'razao_social': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'nome_fantasia': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'cnpj_cpf': forms.TextInput(attrs={
                'class': 'form-control cnpj-cpf-mask'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control telefone-mask'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'endereco': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos obrigatórios
        self.fields['codigo'].required = True
        self.fields['razao_social'].required = True
        
        # Se estiver editando, código não pode ser alterado
        if self.instance.pk:
            self.fields['codigo'].widget.attrs['readonly'] = True
            self.fields['codigo'].help_text = "Código não pode ser alterado após criação"
            
            # Mostrar informação sobre criação automática
            if self.instance.criado_automaticamente:
                self.fields['codigo'].help_text += " (Criado automaticamente do histórico)"
    
    def clean_codigo(self):
        """Validação do código do fornecedor"""
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Verificar duplicação
        queryset = Fornecedor.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe um fornecedor com este código.")
        
        return codigo
    
    def clean_razao_social(self):
        """Validação da razão social"""
        razao_social = self.cleaned_data.get('razao_social', '').strip()
        
        if not razao_social:
            raise forms.ValidationError("Razão social é obrigatória.")
        
        if len(razao_social) < 3:
            raise forms.ValidationError("Razão social deve ter pelo menos 3 caracteres.")
        
        return razao_social.upper()
    
    def clean_cnpj_cpf(self):
        """Validação do CNPJ/CPF"""
        cnpj_cpf = self.cleaned_data.get('cnpj_cpf', '').strip()
        
        if not cnpj_cpf:
            return ''  # Campo opcional
        
        # Remover formatação
        import re
        cnpj_cpf_limpo = re.sub(r'[^\d]', '', cnpj_cpf)
        
        if len(cnpj_cpf_limpo) not in [11, 14]:
            raise forms.ValidationError("CNPJ deve ter 14 dígitos ou CPF deve ter 11 dígitos.")
        
        # Verificar duplicação (apenas se não vazio)
        queryset = Fornecedor.objects.filter(cnpj_cpf__icontains=cnpj_cpf_limpo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            fornecedor_existente = queryset.first()
            raise forms.ValidationError(
                f'CNPJ/CPF já cadastrado para: {fornecedor_existente.codigo} - {fornecedor_existente.razao_social}'
            )
        
        return cnpj_cpf
    
    def clean_email(self):
        """Validação do email"""
        email = self.cleaned_data.get('email', '').strip().lower()
        
        if not email:
            return ''  # Campo opcional
        
        # Verificar duplicação (apenas se não vazio)
        queryset = Fornecedor.objects.filter(email=email)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Email já cadastrado para outro fornecedor.")
        
        return email
    
    def save(self, commit=True):
        """Save customizado"""
        fornecedor = super().save(commit=False)
        
        # Limpar campos
        if fornecedor.codigo:
            fornecedor.codigo = fornecedor.codigo.strip()
        if fornecedor.razao_social:
            fornecedor.razao_social = fornecedor.razao_social.strip().upper()
        if fornecedor.nome_fantasia:
            fornecedor.nome_fantasia = fornecedor.nome_fantasia.strip()
        
        if commit:
            fornecedor.save()
            
            # Log da operação
            import logging
            logger = logging.getLogger('synchrobi')
            action = "atualizado" if self.instance.pk else "criado"
            logger.info(f'Fornecedor {action}: {fornecedor.codigo} - {fornecedor.razao_social}')
        
        return fornecedor