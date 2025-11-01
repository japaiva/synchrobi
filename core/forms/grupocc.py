# core/forms/grupocc.py - FORMULÁRIO DE GRUPO CC

from django import forms
from core.models import GrupoCC

class GrupoCCForm(forms.ModelForm):
    """Formulário para criar/editar grupos de centro de custo"""

    class Meta:
        model = GrupoCC
        fields = ['codigo', 'descricao', 'ativa']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '10'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '30'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Readonly se editando
        if self.instance.pk:
            self.fields['codigo'].widget.attrs['readonly'] = True

    def clean_codigo(self):
        """Validação específica para código"""
        codigo = self.cleaned_data.get('codigo', '').strip().upper()

        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")

        # Verificar se já existe OUTRO grupo com este código
        queryset = GrupoCC.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError("Já existe um Grupo CC com este código.")

        return codigo

    def clean_descricao(self):
        """Validação para descrição"""
        descricao = self.cleaned_data.get('descricao', '').strip()

        if not descricao:
            raise forms.ValidationError("Descrição é obrigatória.")

        return descricao

    def save(self, commit=True):
        """Override do save com formatações automáticas"""
        grupocc = super().save(commit=False)

        # Garantir código em maiúsculas
        if grupocc.codigo:
            grupocc.codigo = grupocc.codigo.upper().strip()

        # Limpar descrição
        if grupocc.descricao:
            grupocc.descricao = grupocc.descricao.strip()

        if commit:
            grupocc.save()

        return grupocc
