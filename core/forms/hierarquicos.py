# core/forms/hierarquicos.py - FORMULÁRIOS HIERÁRQUICOS

from django import forms
from django.core.exceptions import ValidationError

from core.models import Unidade, CentroCusto, ContaContabil, Empresa
from .base import HierarchicalFormMixin

# ===== FORMULÁRIO UNIDADE SIMPLIFICADO =====

class UnidadeForm(forms.ModelForm, HierarchicalFormMixin):
    """Formulário para criar/editar unidades organizacionais com hierarquia dinâmica"""
    
    class Meta:
        model = Unidade
        fields = [
            'codigo', 'codigo_allstrategy', 'nome', 
            'tipo', 'empresa', 'descricao', 'ativa'
        ]

        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'codigo_allstrategy': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'empresa': forms.Select(attrs={
                'class': 'form-select'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3
            }),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popular lista de empresas ativas
        self.fields['empresa'].queryset = Empresa.objects.filter(ativa=True).order_by('sigla')
        
        # Adicionar help texts diferenciados por tipo
        self.fields['codigo'].help_text = "Use pontos para separar níveis (ex: 1.2.01.30.00.110)"
        self.fields['tipo'].help_text = "S=Sintético (agrupador), A=Analítico (operacional)"
        self.fields['codigo_allstrategy'].help_text = "Obrigatório para unidades analíticas, opcional para sintéticas"
    
    def clean_codigo(self):
        """Validação específica para código principal"""
        codigo = super().clean_codigo()
        
        # Verificar se já existe OUTRO registro com este código
        queryset = Unidade.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma unidade com este código.")
        
        return codigo
    
    def clean_codigo_allstrategy(self):
        """Validação para código All Strategy - ajustada para sintéticos"""
        codigo_allstrategy = self.cleaned_data.get('codigo_allstrategy', '').strip()
        tipo = self.cleaned_data.get('tipo')
        
        # Para unidades sintéticas, código All Strategy é opcional
        if tipo == 'S':
            # Se vazio, retornar vazio (sem erro)
            if not codigo_allstrategy:
                return ''
        
        # Para unidades analíticas, código All Strategy é obrigatório
        elif tipo == 'A':
            if not codigo_allstrategy:
                raise forms.ValidationError("Código All Strategy é obrigatório para unidades analíticas.")
        
        # Se foi fornecido um código, verificar duplicação
        if codigo_allstrategy:
            queryset = Unidade.objects.filter(codigo_allstrategy=codigo_allstrategy)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError("Já existe uma unidade com este código All Strategy.")
        
        return codigo_allstrategy
    
    def clean(self):
        """Validação customizada"""
        cleaned_data = super().clean()
        codigo = cleaned_data.get('codigo')
        tipo = cleaned_data.get('tipo')
        codigo_allstrategy = cleaned_data.get('codigo_allstrategy')
        
        # Verificar se pai existe (apenas para códigos com pontos)
        if codigo:
            self.validar_hierarquia_pai(codigo, Unidade)
        
        # Validação adicional: unidades sintéticas não devem ter código All Strategy se não fornecido
        if tipo == 'S' and not codigo_allstrategy:
            # Limpar qualquer valor que possa ter sido herdado
            cleaned_data['codigo_allstrategy'] = ''
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save ajustado para sintéticos"""
        unidade = super().save(commit=False)
        
        # Para unidades sintéticas, garantir que código All Strategy fique vazio se não fornecido
        if unidade.tipo == 'S' and not unidade.codigo_allstrategy:
            unidade.codigo_allstrategy = ''
        
        # Para unidades analíticas, sugerir código All Strategy se não fornecido
        elif unidade.tipo == 'A' and not unidade.codigo_allstrategy and unidade.codigo:
            partes = unidade.codigo.split('.')
            ultimo_segmento = partes[-1]
            if ultimo_segmento.isdigit():
                unidade.codigo_allstrategy = ultimo_segmento
        
        if commit:
            unidade.save()
        
        return unidade

# ===== FORMULÁRIO CENTRO DE CUSTO COM TIPO EDITÁVEL =====

class CentroCustoForm(forms.ModelForm, HierarchicalFormMixin):
    """Formulário para criar/editar centros de custo com tipo completamente editável"""
    
    class Meta:
        model = CentroCusto
        fields = [
            'codigo', 'nome', 'tipo', 'descricao', 'ativo'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 1.1.01'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do centro de custo'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Help texts
        self.fields['codigo'].help_text = "Use pontos para separar níveis (ex: 1.1.01)"
        self.fields['tipo'].help_text = "S=Sintético (pode ter sub-centros), A=Analítico (não pode ter sub-centros)"
        
        # Configurar choices do tipo - SEMPRE EDITÁVEL
        self.fields['tipo'].choices = [
            ('', '--- Selecione ---'),
            ('S', 'Sintético'),
            ('A', 'Analítico'),
        ]
        
        # Se estiver editando um centro existente
        if self.instance.pk:
            # Código não pode ser alterado após criação
            self.fields['codigo'].widget.attrs['readonly'] = True
            self.fields['codigo'].help_text = "Código não pode ser alterado após criação"
            
            # VERIFICAR se pode alterar tipo
            if self.instance.tem_sub_centros and self.instance.tipo == 'S':
                # Se tem filhos, avisar sobre limitação de alterar para analítico
                self.fields['tipo'].help_text = f"⚠️ Este centro possui {self.instance.get_filhos_diretos().count()} sub-centro(s). " \
                                               f"Não pode ser alterado para 'Analítico' enquanto tiver sub-centros."
            else:
                # Se não tem filhos, pode alterar livremente
                self.fields['tipo'].help_text = "Tipo pode ser alterado livremente pois não possui sub-centros"
        
        # Campos obrigatórios
        self.fields['codigo'].required = True
        self.fields['nome'].required = True
        self.fields['tipo'].required = True
    
    def clean_codigo(self):
        """Validação específica para código do centro de custo"""
        codigo = super().clean_codigo()
        
        # Verificar duplicação
        queryset = CentroCusto.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(codigo=self.instance.codigo)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe um centro de custo com este código.")
        
        return codigo
    
    def clean_tipo(self):
        """Validação para tipo"""
        tipo = self.cleaned_data.get('tipo')
        
        if not tipo:
            raise forms.ValidationError("Tipo é obrigatório.")
        
        if tipo not in ['S', 'A']:
            raise forms.ValidationError("Tipo deve ser 'S' (Sintético) ou 'A' (Analítico).")
        
        # VALIDAÇÃO IMPORTANTE: se está alterando para analítico, verificar se tem filhos
        if self.instance.pk and tipo == 'A' and self.instance.tem_sub_centros:
            filhos_count = self.instance.get_filhos_diretos().count()
            raise forms.ValidationError(
                f"Não é possível alterar para 'Analítico' pois este centro possui {filhos_count} sub-centro(s). "
                f"Remova os sub-centros primeiro ou mantenha como 'Sintético'."
            )
        
        return tipo
    
    def clean(self):
        """Validação geral"""
        cleaned_data = super().clean()
        codigo = cleaned_data.get('codigo')
        
        # Verificar hierarquia
        if codigo:
            pai = self.validar_hierarquia_pai(codigo, CentroCusto)
            
            # VALIDAÇÃO: pai deve ser sintético para aceitar filhos
            if pai and pai.tipo == 'A':
                raise forms.ValidationError({
                    'codigo': f'O centro pai "{pai.codigo} - {pai.nome}" é analítico e não pode ter sub-centros. '
                             f'Altere o tipo do centro pai para "Sintético" primeiro.'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customizado"""
        centro = super().save(commit=False)
        
        # Limpar dados
        if centro.codigo:
            centro.codigo = centro.codigo.strip()
        if centro.nome:
            centro.nome = centro.nome.strip()
        
        if commit:
            centro.save()
            
            # Log
            import logging
            logger = logging.getLogger('synchrobi')
            action = "atualizado" if self.instance.pk else "criado"
            logger.info(f'Centro de custo {action}: {centro.codigo} - {centro.nome} ({centro.get_tipo_display()})')
        
        return centro

# ===== FORMULÁRIO CONTA CONTÁBIL COM TIPO EDITÁVEL =====

class ContaContabilForm(forms.ModelForm, HierarchicalFormMixin):
    """Formulário para criar/editar contas contábeis com tipo completamente editável"""
    
    class Meta:
        model = ContaContabil
        fields = [
            'codigo', 'nome', 'tipo', 'descricao', 'ativa'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 1.1.01.001'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da conta contábil'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Help texts
        self.fields['codigo'].help_text = "Use pontos para separar níveis (ex: 1.1.01.001)"
        self.fields['tipo'].help_text = "S=Sintético (pode ter sub-contas), A=Analítico (aceita lançamentos)"
        
        # Configurar choices do tipo - SEMPRE EDITÁVEL
        self.fields['tipo'].choices = [
            ('', '--- Selecione ---'),
            ('S', 'Sintético'),
            ('A', 'Analítico'),
        ]
        
        # Se estiver editando uma conta existente
        if self.instance.pk:
            # Código não pode ser alterado após criação
            self.fields['codigo'].widget.attrs['readonly'] = True
            self.fields['codigo'].help_text = "Código não pode ser alterado após criação"
            
            # VERIFICAR se pode alterar tipo
            if self.instance.tem_subcontas and self.instance.tipo == 'S':
                # Se tem filhos, avisar sobre limitação de alterar para analítico
                self.fields['tipo'].help_text = f"⚠️ Esta conta possui {self.instance.get_filhos_diretos().count()} sub-conta(s). " \
                                               f"Não pode ser alterada para 'Analítico' enquanto tiver sub-contas."
            else:
                # Se não tem filhos, pode alterar livremente
                self.fields['tipo'].help_text = "Tipo pode ser alterado livremente pois não possui sub-contas"
        
        # Campos obrigatórios
        self.fields['codigo'].required = True
        self.fields['nome'].required = True
        self.fields['tipo'].required = True
    
    def clean_codigo(self):
        """Validação específica para código da conta contábil"""
        codigo = super().clean_codigo()
        
        # Verificar duplicação
        queryset = ContaContabil.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(codigo=self.instance.codigo)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma conta contábil com este código.")
        
        return codigo
    
    def clean_tipo(self):
        """Validação para tipo"""
        tipo = self.cleaned_data.get('tipo')
        
        if not tipo:
            raise forms.ValidationError("Tipo é obrigatório.")
        
        if tipo not in ['S', 'A']:
            raise forms.ValidationError("Tipo deve ser 'S' (Sintético) ou 'A' (Analítico).")
        
        # VALIDAÇÃO IMPORTANTE: se está alterando para analítico, verificar se tem filhos
        if self.instance.pk and tipo == 'A' and self.instance.tem_subcontas:
            filhos_count = self.instance.get_filhos_diretos().count()
            raise forms.ValidationError(
                f"Não é possível alterar para 'Analítico' pois esta conta possui {filhos_count} sub-conta(s). "
                f"Remova as sub-contas primeiro ou mantenha como 'Sintético'."
            )
        
        return tipo
    
    def clean(self):
        """Validação geral"""
        cleaned_data = super().clean()
        codigo = cleaned_data.get('codigo')
        
        # Verificar hierarquia
        if codigo:
            pai = self.validar_hierarquia_pai(codigo, ContaContabil)
            
            # VALIDAÇÃO: pai deve ser sintético para aceitar filhos
            if pai and pai.tipo == 'A':
                raise forms.ValidationError({
                    'codigo': f'A conta pai "{pai.codigo} - {pai.nome}" é analítica e não pode ter sub-contas. '
                             f'Altere o tipo da conta pai para "Sintético" primeiro.'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customizado"""
        conta = super().save(commit=False)
        
        # Limpar dados
        if conta.codigo:
            conta.codigo = conta.codigo.strip()
        if conta.nome:
            conta.nome = conta.nome.strip()
        
        if commit:
            conta.save()
            
            # Log
            import logging
            logger = logging.getLogger('synchrobi')
            action = "atualizada" if self.instance.pk else "criada"
            logger.info(f'Conta contábil {action}: {conta.codigo} - {conta.nome} ({conta.get_tipo_display()})')
        
        return conta