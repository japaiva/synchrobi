# core/forms/empresa.py - FORMULÁRIO DE EMPRESA

from django import forms
from core.models import Empresa

class EmpresaForm(forms.ModelForm):
    """Formulário para criar/editar empresas"""
    
    class Meta:
        model = Empresa
        fields = [
            'sigla', 'razao_social', 'nome_fantasia', 'cnpj',
            'inscricao_estadual', 'inscricao_municipal', 'endereco', 
            'telefone', 'email', 'ativa'
        ]
        widgets = {
            'sigla': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '15'
            }),
            'razao_social': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'nome_fantasia': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'cnpj': forms.TextInput(attrs={
                'class': 'form-control cnpj-mask'
            }),
            'inscricao_estadual': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'inscricao_municipal': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'endereco': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control telefone-mask'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_sigla(self):
        """Validação específica para sigla da empresa"""
        sigla = self.cleaned_data.get('sigla', '').strip().upper()
        
        if not sigla:
            raise forms.ValidationError("Sigla é obrigatória.")
        
        # Verificar se já existe OUTRA empresa com esta sigla
        queryset = Empresa.objects.filter(sigla=sigla)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma empresa com esta sigla.")
        
        return sigla
    
    def clean_cnpj(self):
        """Validação para CNPJ"""
        cnpj = self.cleaned_data.get('cnpj', '').strip()
        
        if not cnpj:
            raise forms.ValidationError("CNPJ é obrigatório.")
        
        # Remover formatação
        import re
        cnpj_limpo = re.sub(r'[^\d]', '', cnpj)
        
        if len(cnpj_limpo) != 14:
            raise forms.ValidationError("CNPJ deve conter 14 dígitos.")
        
        # Verificar duplicação
        queryset = Empresa.objects.filter(cnpj__contains=cnpj_limpo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma empresa com este CNPJ.")
        
        return cnpj
    
    def save(self, commit=True):
        """Override do save com formatações automáticas"""
        empresa = super().save(commit=False)
        
        # Garantir sigla em maiúsculas
        if empresa.sigla:
            empresa.sigla = empresa.sigla.upper().strip()
        
        if commit:
            empresa.save()
        
        return empresa