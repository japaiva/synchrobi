# core/forms/hierarquicos.py - FORMULÁRIOS COM CAMPO PAI POR PESQUISA

from django import forms
from django.core.exceptions import ValidationError

from core.models import Unidade, CentroCusto, ContaContabil, Empresa

# ===== FORMULÁRIO BASE PARA HIERARQUIA DECLARADA =====

class HierarchiaDeclaradaFormMixin:
    """Mixin para formulários com hierarquia declarada"""
    
    def configurar_campo_pai_texto(self, modelo, campo_pai_name='codigo_pai'):
        """Configura campo pai como texto com pesquisa"""
        campo_pai = self.fields[campo_pai_name]
        
        # Mudar para TextInput com autocomplete
        campo_pai.widget = forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite código do pai (deixe vazio para raiz)',
            'autocomplete': 'off',
            'data-bs-toggle': 'tooltip',
            'title': 'Digite parte do código ou nome para pesquisar'
        })
    
    def clean_codigo_pai(self):
        """Validação genérica para código pai"""
        codigo_pai = self.cleaned_data.get('codigo_pai', '').strip()
        
        if not codigo_pai:
            return ''  # Vazio = item raiz
        
        # Verificar se o pai existe
        modelo = self._meta.model
        field_names = [f.name for f in modelo._meta.fields]
        active_field = 'ativo' if 'ativo' in field_names else 'ativa'
        
        try:
            filter_dict = {'codigo': codigo_pai, active_field: True}
            pai = modelo.objects.get(**filter_dict)
        except modelo.DoesNotExist:
            raise forms.ValidationError(f"Centro de custo pai '{codigo_pai}' não encontrado.")
        
        # Verificar se pai é sintético (se campo tipo existir)
        if hasattr(pai, 'tipo') and pai.tipo == 'A':
            raise forms.ValidationError(
                f'O item pai "{pai.codigo} - {pai.nome}" é analítico e não pode ter sub-itens. '
                f'Use um centro sintético como pai.'
            )
        
        # Se estiver editando, verificar ciclos
        if self.instance.pk:
            if codigo_pai == self.instance.codigo:
                raise forms.ValidationError("Um item não pode ser pai de si mesmo.")
            
            # Verificar se não está tentando usar um descendente como pai
            try:
                descendentes = self.instance.get_todos_filhos()
                if descendentes:
                    codigos_descendentes = [desc.codigo for desc in descendentes]
                    if codigo_pai in codigos_descendentes:
                        raise forms.ValidationError(
                            f"Não é possível usar '{codigo_pai}' como pai pois é um descendente deste item."
                        )
            except:
                pass
        
        return codigo_pai

# ===== FORMULÁRIO CENTRO DE CUSTO =====

class CentroCustoForm(forms.ModelForm, HierarchiaDeclaradaFormMixin):
    """Formulário para centro de custo com hierarquia declarada"""
    
    class Meta:
        model = CentroCusto
        fields = ['codigo', 'nome', 'codigo_pai', 'tipo', 'descricao', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_pai': forms.TextInput(attrs={'class': 'form-control'}),  # Agora é TextInput
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar campo pai como texto
        self.configurar_campo_pai_texto(CentroCusto)
        
        # Help texts
        self.fields['codigo'].help_text = "Código do centro de custo"
        self.fields['codigo_pai'].help_text = "Digite o código do centro pai (deixe vazio se for raiz)"
        self.fields['tipo'].help_text = "S=Sintético (pode ter sub-centros), A=Analítico"
        
        # Readonly se editando
        if self.instance.pk:
            self.fields['codigo'].widget.attrs['readonly'] = True
            
            # Mostrar informação do pai atual se existir
            if self.instance.codigo_pai:
                try:
                    pai = CentroCusto.objects.get(codigo=self.instance.codigo_pai)
                    self.fields['codigo_pai'].help_text = f"Pai atual: {pai.codigo} - {pai.nome}"
                except CentroCusto.DoesNotExist:
                    pass
    
    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Verificar duplicação
        queryset = CentroCusto.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(codigo=self.instance.codigo)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe um centro de custo com este código.")
        
        return codigo

# ===== FORMULÁRIO UNIDADE =====

class UnidadeForm(forms.ModelForm, HierarchiaDeclaradaFormMixin):
    """Formulário para unidades com hierarquia declarada"""
    
    class Meta:
        model = Unidade
        fields = [
            'codigo', 'nome', 'codigo_pai', 'codigo_allstrategy', 
            'tipo', 'empresa', 'descricao', 'ativa'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_pai': forms.TextInput(attrs={'class': 'form-control'}),  # Agora é TextInput
            'codigo_allstrategy': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar empresa
        self.fields['empresa'].queryset = Empresa.objects.filter(ativa=True).order_by('sigla')
        
        # Configurar campo pai como texto
        self.configurar_campo_pai_texto(Unidade)
        
        # Help texts
        self.fields['codigo'].help_text = "Código da unidade (ex: 1.2.01.30)"
        self.fields['codigo_pai'].help_text = "Digite o código da unidade pai (deixe vazio se for raiz)"
        self.fields['codigo_allstrategy'].help_text = "Código All Strategy (opcional para sintéticos)"
        
        # Readonly se editando
        if self.instance.pk:
            self.fields['codigo'].widget.attrs['readonly'] = True
    
    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Verificar duplicação
        queryset = Unidade.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma unidade com este código.")
        
        return codigo

# ===== FORMULÁRIO CONTA CONTÁBIL =====

class ContaContabilForm(forms.ModelForm, HierarchiaDeclaradaFormMixin):
    """Formulário para conta contábil com hierarquia declarada"""
    
    class Meta:
        model = ContaContabil
        fields = ['codigo', 'nome', 'codigo_pai', 'tipo', 'descricao', 'ativa']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_pai': forms.TextInput(attrs={'class': 'form-control'}),  # Agora é TextInput
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar campo pai como texto
        self.configurar_campo_pai_texto(ContaContabil)
        
        # Help texts
        self.fields['codigo'].help_text = "Código da conta contábil (ex: 1.1.01.001)"
        self.fields['codigo_pai'].help_text = "Digite o código da conta pai (deixe vazio se for raiz)"
        self.fields['tipo'].help_text = "S=Sintético (pode ter sub-contas), A=Analítico"
        
        # Readonly se editando
        if self.instance.pk:
            self.fields['codigo'].widget.attrs['readonly'] = True
    
    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Verificar duplicação
        queryset = ContaContabil.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(codigo=self.instance.codigo)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma conta contábil com este código.")
        
        return codigo