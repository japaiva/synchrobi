# core/forms/movimento.py - FORMULÁRIOS DE MOVIMENTO

from django import forms
from django.db.models import Q

from core.models import Movimento, Unidade, CentroCusto, ContaContabil, Fornecedor
from core.utils.view_utils import CustomDateInput, CustomDateTimeInput, DateAwareModelForm


class MovimentoForm(DateAwareModelForm):
    """Formulário para criar/editar movimentos - VERSÃO CORRIGIDA"""
    
    class Meta:
        model = Movimento
        fields = [
            'data', 'natureza', 'valor', 'unidade', 'centro_custo', 'conta_contabil',
            'fornecedor', 'documento', 'historico', 'codigo_projeto', 'gerador'
        ]
        
        widgets = {
            # Data no formato brasileiro
            'data': CustomDateInput(attrs={
                'class': 'form-control'
            }),

            'unidade': forms.Select(attrs={'class': 'form-select'}),
            'centro_custo': forms.Select(attrs={'class': 'form-select'}),
            'conta_contabil': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'documento': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'natureza': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'historico': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'codigo_projeto': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'gerador': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar choices da natureza - APENAS D e C
        self.fields['natureza'].choices = [
            ('', '--- Selecione ---'),
            ('D', 'Débito'),
            ('C', 'Crédito'),
        ]
        
        # Filtrar querysets para apenas registros ativos
        self.fields['unidade'].queryset = Unidade.objects.filter(ativa=True).order_by('codigo')
        self.fields['centro_custo'].queryset = CentroCusto.objects.filter(ativo=True).order_by('codigo')
        self.fields['conta_contabil'].queryset = ContaContabil.objects.filter(ativa=True).order_by('codigo')
        self.fields['fornecedor'].queryset = Fornecedor.objects.filter(ativo=True).order_by('razao_social')
        
        # Campos obrigatórios
        self.fields['data'].required = True
        self.fields['unidade'].required = True
        self.fields['centro_custo'].required = True
        self.fields['conta_contabil'].required = True
        self.fields['natureza'].required = True
        self.fields['valor'].required = True
        self.fields['historico'].required = True
        
         
        # Empty labels para campos obrigatórios
        self.fields['unidade'].empty_label = "--- Selecione a Unidade ---"
        self.fields['centro_custo'].empty_label = "--- Selecione o Centro de Custo ---"
        self.fields['conta_contabil'].empty_label = "--- Selecione a Conta Contábil ---"
        self.fields['fornecedor'].empty_label = "--- Selecione o Fornecedor (opcional) ---"
        
        # Data padrão
        if not self.instance.pk:
            from datetime import date
            self.fields['data'].initial = date.today()
    
    def clean_valor(self):
        """Validação do valor"""
        valor = self.cleaned_data.get('valor')
        
        if valor is None:
            raise forms.ValidationError("Valor é obrigatório.")
        
        if valor == 0:
            raise forms.ValidationError("Valor não pode ser zero.")
        
        return valor
    
    def clean_natureza(self):
        """Validação da natureza"""
        natureza = self.cleaned_data.get('natureza')
        
        if not natureza:
            raise forms.ValidationError("Natureza é obrigatória.")
        
        if natureza not in ['D', 'C']:
            raise forms.ValidationError("Natureza deve ser 'D' (Débito) ou 'C' (Crédito).")
        
        return natureza
    
    def clean(self):
        """Validação geral"""
        cleaned_data = super().clean()
        
        # Campos obrigatórios
        data = cleaned_data.get('data')
        valor = cleaned_data.get('valor')
        historico = cleaned_data.get('historico')
        
        if not data:
            raise forms.ValidationError({'data': 'Data é obrigatória.'})
        
        if valor is None:
            raise forms.ValidationError({'valor': 'Valor é obrigatório.'})
        
        if not historico:
            raise forms.ValidationError({'historico': 'Histórico é obrigatório.'})
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customizado"""
        movimento = super().save(commit=False)
        
        # Limpar dados
        if movimento.historico:
            movimento.historico = movimento.historico.strip()
        
        # Data já define mês e ano automaticamente no modelo
        
        if commit:
            movimento.save()
            
            # Log
            import logging
            logger = logging.getLogger('synchrobi')
            action = "atualizado" if self.instance.pk else "criado"
            logger.info(f'Movimento {action}: {movimento.id} - {movimento.valor_formatado}')
        
        return movimento

class MovimentoFiltroForm(forms.Form):
    """Formulário para filtros da lista de movimentos"""
    
    ano = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label="Ano"
    )
    
    mes = forms.ChoiceField(
        choices=[
            ('', 'Todos os meses'),
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
            (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
            (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label="Mês"
    )
    
    unidade = forms.ModelChoiceField(
        queryset=Unidade.objects.filter(ativa=True).order_by('codigo'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        empty_label="Todas as unidades",
        label="Unidade"
    )
    
    centro_custo = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Código do centro'
        }),
        label="Centro de Custo"
    )
    
    fornecedor = forms.ModelChoiceField(
        queryset=Fornecedor.objects.filter(ativo=True).order_by('razao_social'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        empty_label="Todos os fornecedores",
        label="Fornecedor"
    )
    
    natureza = forms.ChoiceField(
        choices=[
            ('', 'Todas'),
            ('D', 'Débito'),
            ('C', 'Crédito'),
            ('A', 'Ambas')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label="Natureza"
    )
    
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Buscar no histórico, documento...'
        }),
        label="Busca Livre"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Preencher anos disponíveis dinamicamente
        anos_disponiveis = Movimento.objects.values_list('ano', flat=True).distinct().order_by('-ano')
        ano_choices = [('', 'Todos os anos')] + [(ano, str(ano)) for ano in anos_disponiveis]
        self.fields['ano'].choices = ano_choices