# core/forms.py - Forms atualizados com Centro de Custo e Conta Contábil

from django import forms
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from core.models import Usuario, Unidade, CentroCusto, ContaContabil, ParametroSistema, Empresa, EmpresaCentroCusto

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

# core/forms.py - UsuarioForm Simplificado para seu modelo atual

from django import forms
from core.models import Usuario
from django.contrib.auth.hashers import make_password

class UsuarioForm(forms.ModelForm):
    """
    Formulário simplificado para usuários SynchroBI
    Compatível com o modelo atual, mas usando apenas campos essenciais
    """
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
            'username',     # código
            'first_name',   # nome (sem last_name para ser maior)
            'email', 
            'telefone',
            'nivel',        # admin/gestor/analista/contador/diretor  
            'is_active'     # status
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
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
        
        # Ajustar choices do nível conforme seu modelo atual
        # admin/gestor/analista/contador/diretor
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
        
        # Limpar campos não utilizados (opcional, para não interferir)
        # Manter os campos do modelo, mas não exibir no form
        if not usuario.centro_custo:
            usuario.centro_custo = ''
        if not usuario.unidade_negocio:
            usuario.unidade_negocio = ''
        if not usuario.last_name:
            usuario.last_name = ''
        
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
    """Formulário para criar/editar contas contábeis simplificado"""
    
    class Meta:
        model = ContaContabil
        fields = [
            'codigo', 'nome', 'descricao', 'ativa'
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
    
# core/forms.py - Adicionar ao final do arquivo

class EmpresaCentroCustoForm(forms.ModelForm):
    """Formulário para relacionar empresas com centros de custo e responsáveis"""
    
    class Meta:
        model = EmpresaCentroCusto
        fields = [
            'empresa', 'centro_custo', 'responsavel',
            'data_inicio', 'data_fim', 'observacoes', 'ativo'
        ]
        widgets = {
            'empresa': forms.Select(attrs={
                'class': 'form-select'
            }),
            'centro_custo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'responsavel': forms.Select(attrs={
                'class': 'form-select'
            }),
            'data_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_fim': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'empresa': 'Empresa',
            'centro_custo': 'Centro de Custo',
            'responsavel': 'Responsável',
            'data_inicio': 'Data de Início',
            'data_fim': 'Data de Fim (opcional)',
            'observacoes': 'Observações',
            'ativo': 'Ativo'
        }
    
    def __init__(self, *args, **kwargs):
        empresa_pk = kwargs.pop('empresa_pk', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar apenas empresas ativas
        self.fields['empresa'].queryset = Empresa.objects.filter(ativa=True).order_by('sigla')
        
        # Filtrar apenas centros de custo ativos e analíticos
        self.fields['centro_custo'].queryset = CentroCusto.objects.filter(
            ativo=True
        ).select_related().order_by('codigo')
        
        # Filtrar apenas usuários ativos
        self.fields['responsavel'].queryset = Usuario.objects.filter(
            is_active=True
        ).order_by('first_name')
        
        # Se empresa específica foi passada, pré-selecionar
        if empresa_pk:
            try:
                empresa = Empresa.objects.get(pk=empresa_pk)
                self.fields['empresa'].initial = empresa
                self.fields['empresa'].widget.attrs['readonly'] = True
            except Empresa.DoesNotExist:
                pass
        
        # Se editando, desabilitar campos chave
        if self.instance.pk:
            self.fields['empresa'].widget.attrs['readonly'] = True
            self.fields['centro_custo'].widget.attrs['readonly'] = True
            
            # Informação adicional
            self.fields['empresa'].help_text = "Para alterar empresa ou centro de custo, crie um novo relacionamento"
            self.fields['centro_custo'].help_text = "Para alterar empresa ou centro de custo, crie um novo relacionamento"
    
    def clean(self):
        """Validação customizada do formulário"""
        cleaned_data = super().clean()
        empresa = cleaned_data.get('empresa')
        centro_custo = cleaned_data.get('centro_custo')
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        ativo = cleaned_data.get('ativo')
        
        # Validar datas
        if data_fim and data_inicio and data_fim < data_inicio:
            self.add_error('data_fim', 'Data de fim não pode ser anterior à data de início')
        
        # Validar se já existe relacionamento ativo (apenas para novos registros)
        if empresa and centro_custo and ativo and not self.instance.pk:
            existe = EmpresaCentroCusto.objects.filter(
                empresa=empresa,
                centro_custo=centro_custo,
                ativo=True
            ).exists()
            
            if existe:
                raise forms.ValidationError(
                    f'Já existe um relacionamento ativo entre {empresa.sigla} e {centro_custo.codigo}. '
                    'Desative o relacionamento anterior antes de criar um novo.'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Override do save para adicionar informações extras"""
        instance = super().save(commit=False)
        
        # Se não tem data de início, usar hoje
        if not instance.data_inicio:
            instance.data_inicio = timezone.now().date()
        
        if commit:
            instance.save()
        
        return instance
# core/forms.py - Formulários simplificados para empresa centro custo

from django import forms
from django.utils import timezone
from core.models import Empresa, CentroCusto, Usuario, EmpresaCentroCusto

# ... outros formulários existentes mantidos ...

# ===== FORMULÁRIO EMPRESA CENTRO CUSTO (SIMPLIFICADO) =====

class EmpresaCentroCustoForm(forms.ModelForm):
    """Formulário simplificado para relacionar empresas com centros de custo"""
    
    class Meta:
        model = EmpresaCentroCusto
        fields = [
            'empresa', 'centro_custo', 'responsavel',
            'data_inicio', 'data_fim', 'observacoes', 'ativo'
        ]
        widgets = {
            'empresa': forms.Select(attrs={
                'class': 'form-select'
            }),
            'centro_custo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'responsavel': forms.Select(attrs={
                'class': 'form-select'
            }),
            'data_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_fim': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'empresa': 'Empresa',
            'centro_custo': 'Centro de Custo',
            'responsavel': 'Responsável',
            'data_inicio': 'Data de Início',
            'data_fim': 'Data de Fim (opcional)',
            'observacoes': 'Observações',
            'ativo': 'Ativo'
        }
    
    def __init__(self, *args, **kwargs):
        empresa_pk = kwargs.pop('empresa_pk', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar apenas empresas ativas
        self.fields['empresa'].queryset = Empresa.objects.filter(ativa=True).order_by('sigla')
        
        # Filtrar apenas centros de custo ativos
        self.fields['centro_custo'].queryset = CentroCusto.objects.filter(
            ativo=True
        ).order_by('codigo')
        
        # Filtrar apenas usuários ativos
        self.fields['responsavel'].queryset = Usuario.objects.filter(
            is_active=True
        ).order_by('first_name')
        
        # Se empresa específica foi passada, pré-selecionar
        if empresa_pk:
            try:
                empresa = Empresa.objects.get(pk=empresa_pk)
                self.fields['empresa'].initial = empresa
                self.fields['empresa'].widget.attrs['readonly'] = True
            except Empresa.DoesNotExist:
                pass
        
        # Se editando, desabilitar campos chave
        if self.instance.pk:
            self.fields['empresa'].widget.attrs['readonly'] = True
            self.fields['centro_custo'].widget.attrs['readonly'] = True
            
            # Informação adicional
            self.fields['empresa'].help_text = "Para alterar empresa ou centro de custo, crie um novo relacionamento"
            self.fields['centro_custo'].help_text = "Para alterar empresa ou centro de custo, crie um novo relacionamento"
    
    def clean(self):
        """Validação customizada do formulário"""
        cleaned_data = super().clean()
        empresa = cleaned_data.get('empresa')
        centro_custo = cleaned_data.get('centro_custo')
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        ativo = cleaned_data.get('ativo')
        
        # Validar datas
        if data_fim and data_inicio and data_fim < data_inicio:
            self.add_error('data_fim', 'Data de fim não pode ser anterior à data de início')
        
        # Validar se já existe relacionamento ativo (apenas para novos registros)
        if empresa and centro_custo and ativo and not self.instance.pk:
            existe = EmpresaCentroCusto.objects.filter(
                empresa=empresa,
                centro_custo=centro_custo,
                ativo=True
            ).exists()
            
            if existe:
                raise forms.ValidationError(
                    f'Já existe um relacionamento ativo entre {empresa.sigla} e {centro_custo.codigo}. '
                    'Desative o relacionamento anterior antes de criar um novo.'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Override do save para adicionar informações extras"""
        instance = super().save(commit=False)
        
        # Se não tem data de início, usar hoje
        if not instance.data_inicio:
            instance.data_inicio = timezone.now().date()
        
        if commit:
            instance.save()
        
        return instance

# ===== FORMULÁRIO PARA FILTROS (SIMPLIFICADO) =====

class EmpresaCentroCustoFiltroForm(forms.Form):
    """Formulário simplificado para filtrar relacionamentos empresa x centro de custo"""
    
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.filter(ativa=True).order_by('sigla'),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
        empty_label="Todas as empresas",
        label="Empresa"
    )
    
    centro_custo = forms.ModelChoiceField(
        queryset=CentroCusto.objects.filter(ativo=True).order_by('codigo'),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
        empty_label="Todos os centros de custo",
        label="Centro de Custo"
    )
    
    responsavel = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(is_active=True).order_by('first_name'),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
        empty_label="Todos os responsáveis",
        label="Responsável"
    )