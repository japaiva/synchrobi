# core/forms/grupo_fornecedor.py - FORMULÁRIO DE GRUPO DE FORNECEDORES

from django import forms
from core.models import GrupoFornecedor

class GrupoFornecedorForm(forms.ModelForm):
    """Formulário para criar/editar grupos de fornecedores"""

    class Meta:
        model = GrupoFornecedor
        fields = ['codigo', 'nome', 'descricao', 'ativo']

        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: GRTI, GPAP'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: FORNECEDORES DE TI'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do grupo (opcional)'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Campos obrigatórios
        self.fields['codigo'].required = True
        self.fields['nome'].required = True

        # Se estiver editando, código não pode ser alterado
        if self.instance.pk:
            self.fields['codigo'].widget.attrs['readonly'] = True
            self.fields['codigo'].help_text = "Código não pode ser alterado após criação"

    def clean_codigo(self):
        """Validação do código do grupo"""
        codigo = self.cleaned_data.get('codigo', '').strip().upper()

        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")

        # Verificar duplicação
        queryset = GrupoFornecedor.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError("Já existe um grupo com este código.")

        return codigo

    def clean_nome(self):
        """Validação do nome do grupo"""
        nome = self.cleaned_data.get('nome', '').strip().upper()

        if not nome:
            raise forms.ValidationError("Nome é obrigatório.")

        if len(nome) < 3:
            raise forms.ValidationError("Nome deve ter pelo menos 3 caracteres.")

        # Verificar duplicação
        queryset = GrupoFornecedor.objects.filter(nome=nome)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError("Já existe um grupo com este nome.")

        return nome

    def save(self, commit=True):
        """Save customizado"""
        grupo = super().save(commit=False)

        # Limpar campos
        if grupo.codigo:
            grupo.codigo = grupo.codigo.strip().upper()
        if grupo.nome:
            grupo.nome = grupo.nome.strip().upper()

        if commit:
            grupo.save()

            # Log da operação
            import logging
            logger = logging.getLogger('synchrobi')
            action = "atualizado" if self.instance.pk else "criado"
            logger.info(f'Grupo de Fornecedor {action}: {grupo.codigo} - {grupo.nome}')

        return grupo
