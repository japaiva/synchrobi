# core/forms/base.py - UTILITÁRIOS E CLASSES BASE

from django import forms
from django.utils import timezone

class CustomDateInput(forms.DateInput):
    """Widget de data customizado para formulários"""
    input_type = 'date'

class CustomDateTimeInput(forms.DateTimeInput):
    """Widget de data/hora customizado para formulários"""
    input_type = 'datetime-local'

class DateAwareModelForm(forms.ModelForm):
    """
    Form base que automaticamente configura campos de data
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Aplicar CustomDateInput para campos DateField
        for field_name, field in self.fields.items():
            if isinstance(field, forms.DateField):
                field.widget = CustomDateInput(attrs={
                    'class': 'form-control',
                    **field.widget.attrs
                })
            elif isinstance(field, forms.DateTimeField):
                field.widget = CustomDateTimeInput(attrs={
                    'class': 'form-control',
                    **field.widget.attrs
                })

class HierarchicalFormMixin:
    """
    Mixin para formulários de modelos hierárquicos
    Fornece validações e métodos comuns
    """
    
    def clean_codigo(self):
        """Validação padrão para códigos hierárquicos"""
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Validar formato (números e pontos apenas)
        import re
        if not re.match(r'^[\d\.]+$', codigo):
            raise forms.ValidationError("Código deve conter apenas números e pontos.")
        
        # Validações de formato
        if codigo.startswith('.') or codigo.endswith('.'):
            raise forms.ValidationError("Código não pode começar ou terminar com ponto.")
        
        if '..' in codigo:
            raise forms.ValidationError("Código não pode ter pontos consecutivos.")
        
        return codigo
    
    def clean_nome(self):
        """Validação padrão para nomes"""
        nome = self.cleaned_data.get('nome', '').strip()
        
        if not nome:
            raise forms.ValidationError("Nome é obrigatório.")
        
        if len(nome) < 3:
            raise forms.ValidationError("Nome deve ter pelo menos 3 caracteres.")
        
        return nome
    
    def validar_hierarquia_pai(self, codigo, model_class):
        """
        Valida se o pai existe na hierarquia
        """
        if '.' in codigo:
            # Criar instância temporária para encontrar pai
            temp_instance = model_class(codigo=codigo)
            pai = temp_instance.encontrar_pai_hierarquico()
            
            if not pai:
                partes = codigo.split('.')
                codigo_pai = '.'.join(partes[:-1])
                raise forms.ValidationError({
                    'codigo': f'Nenhum item pai foi encontrado para o código "{codigo}". '
                             f'Certifique-se de que existe um item com código "{codigo_pai}".'
                })
            
            return pai
        
        return None