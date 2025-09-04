# core/forms.py - Forms atualizados com Centro de Custo e Conta Contábil

from django import forms
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from core.models import Usuario, Unidade, CentroCusto, ContaContabil, ParametroSistema, Empresa

# ===== FORMULÁRIOS EXISTENTES (mantidos) =====

class UnidadeForm(forms.ModelForm):
    """Formulário para criar/editar unidades organizacionais"""
    
    # Campo para exibir unidade pai (somente leitura, calculado automaticamente)
    unidade_pai_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': True
        }),
        label="Unidade Superior"
    )
    
    class Meta:
        model = Unidade
        fields = [
            'codigo', 'codigo_allstrategy', 'nome', 
             'empresa','descricao', 'ativa'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'codigo_allstrategy': forms.TextInput(attrs={
                'class': 'form-control'
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
        
        # Se está editando, mostrar a unidade pai atual
        if self.instance.pk and self.instance.unidade_pai:
            self.fields['unidade_pai_display'].initial = f"{self.instance.unidade_pai.codigo} - {self.instance.unidade_pai.nome}"
        elif self.instance.pk:
            self.fields['unidade_pai_display'].initial = "Unidade Raiz (sem superior)"
    
    def clean_codigo(self):
        """Validação específica para código principal"""
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Validar formato (números e pontos apenas)
        import re
        if not re.match(r'^[\d\.]+$', codigo):
            raise forms.ValidationError("Código deve conter apenas números e pontos.")
        
        # Verificar se já existe OUTRO registro com este código
        queryset = Unidade.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma unidade com este código.")
        
        return codigo
    
    def clean_codigo_allstrategy(self):
        """Validação para código All Strategy"""
        codigo_allstrategy = self.cleaned_data.get('codigo_allstrategy', '').strip()
        
        # Verificar duplicação de código all strategy (se fornecido)
        if codigo_allstrategy:
            queryset = Unidade.objects.filter(codigo_allstrategy=codigo_allstrategy)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError("Já existe uma unidade com este código All Strategy.")
        
        return codigo_allstrategy
    
    def save(self, commit=True):
        """Override do save - o modelo cuida da hierarquia automaticamente"""
        unidade = super().save(commit=False)
        
        # Se não tem código All Strategy, sugerir baseado no código
        if not unidade.codigo_allstrategy and unidade.codigo:
            partes = unidade.codigo.split('.')
            ultimo_segmento = partes[-1]
            if ultimo_segmento.isdigit():
                unidade.codigo_allstrategy = ultimo_segmento
        
        if commit:
            unidade.save()
        
        return unidade

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

class UsuarioForm(forms.ModelForm):
    """Formulário para criar/editar usuários do SynchroBI"""
    
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
            'username', 'first_name', 'last_name', 'email', 'nivel', 
            'telefone', 'centro_custo', 'unidade_negocio', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'centro_custo': forms.TextInput(attrs={'class': 'form-control'}),
            'unidade_negocio': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se estiver editando, não exigir senha
        if self.instance.pk:
            self.fields['password'].required = False
            self.fields['confirm_password'].required = False
        else:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True
    
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
        
        if commit:
            usuario.save()
        
        return usuario

class ParametroSistemaForm(forms.ModelForm):
    """Formulário para criar/editar parâmetros do sistema"""
    
    class Meta:
        model = ParametroSistema
        fields = [
            'codigo', 'nome', 'descricao', 'tipo', 'valor', 
            'valor_padrao', 'categoria', 'editavel', 'ativo'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: taxa_juros_mensal'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nome descritivo do parâmetro'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Descrição detalhada do parâmetro...'
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'Valor atual do parâmetro'
            }),
            'valor_padrao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'Valor padrão (opcional)'
            }),
            'categoria': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: financeiro, sistema, integracao'
            }),
            'editavel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se estiver editando um parâmetro não editável, desabilitar campos
        if self.instance.pk and not self.instance.editavel:
            self.fields['codigo'].widget.attrs['readonly'] = True
            self.fields['tipo'].widget.attrs['disabled'] = True
    
    def clean_codigo(self):
        """Validação específica para código do parâmetro"""
        codigo = self.cleaned_data.get('codigo', '').strip().lower()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Validar formato (apenas letras, números e underscore)
        import re
        if not re.match(r'^[a-z0-9_]+$', codigo):
            raise forms.ValidationError("Código deve conter apenas letras minúsculas, números e underscore.")
        
        # Verificar se já existe (excluindo a instância atual se estiver editando)
        queryset = ParametroSistema.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe um parâmetro com este código.")
        
        return codigo
    
    def clean_valor(self):
        """Validação do valor baseada no tipo"""
        valor = self.cleaned_data.get('valor', '').strip()
        tipo = self.cleaned_data.get('tipo')
        
        if not valor:
            return valor
        
        # Validar conforme o tipo
        try:
            if tipo == 'numero':
                int(valor)
            elif tipo == 'decimal':
                float(valor)
            elif tipo == 'boolean':
                if valor.lower() not in ['true', 'false', '1', '0', 'sim', 'não', 'verdadeiro', 'falso']:
                    raise forms.ValidationError("Valor booleano deve ser: true, false, 1, 0, sim, não, verdadeiro ou falso")
            elif tipo == 'data':
                from datetime import datetime
                datetime.strptime(valor, '%Y-%m-%d')
            elif tipo == 'json':
                import json
                json.loads(valor)
        except (ValueError, TypeError):
            raise forms.ValidationError(f"Valor inválido para o tipo '{tipo}'.")
        
        return valor

# ===== FORMULÁRIO CENTRO DE CUSTO (SIMPLIFICADO) =====

class CentroCustoForm(forms.ModelForm):
    """Formulário para criar/editar centros de custo"""
    
    class Meta:
        model = CentroCusto
        fields = [
            'codigo', 'nome', 'descricao', 'ativo'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_codigo(self):
        """Validação específica para código do centro de custo"""
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Validar formato (números e pontos apenas)
        import re
        if not re.match(r'^[\d\.]+$', codigo):
            raise forms.ValidationError("Código deve conter apenas números e pontos.")
        
        # Verificar se já existe OUTRO registro com este código
        queryset = CentroCusto.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe um centro de custo com este código.")
        
        return codigo

# ===== FORMULÁRIO CONTA CONTÁBIL =====

class ContaContabilForm(forms.ModelForm):
    """Formulário para criar/editar contas contábeis"""
    
    class Meta:
        model = ContaContabil
        fields = [
            'codigo', 'nome', 'descricao', 'tipo_conta', 
            'categoria_dre', 'subcategoria_dre', 'ativa'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 010.010.01'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da conta contábil'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Descrição da conta...'
            }),
            'tipo_conta': forms.Select(attrs={
                'class': 'form-select'
            }),
            'categoria_dre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Receita Bruta, CMV, Despesas Operacionais'
            }),
            'subcategoria_dre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Vendas, Material, Pessoal'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_codigo(self):
        """Validação específica para código da conta contábil"""
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Validar formato (números e pontos apenas)
        import re
        if not re.match(r'^[\d\.]+$', codigo):
            raise forms.ValidationError("Código deve conter apenas números e pontos.")
        
        # Verificar se já existe OUTRO registro com este código
        queryset = ContaContabil.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma conta contábil com este código.")
        
        return codigo
    
    def clean(self):
        """Validação geral do formulário"""
        cleaned_data = super().clean()
        tipo_conta = cleaned_data.get('tipo_conta')
        categoria_dre = cleaned_data.get('categoria_dre', '').strip()
        
        # Se é conta de resultado (receita, custo, despesa), categoria DRE é recomendada
        if tipo_conta in ['receita', 'custo', 'despesa'] and not categoria_dre:
            self.add_error('categoria_dre', 
                'Categoria DRE é recomendada para contas de resultado.')
        
        return cleaned_data