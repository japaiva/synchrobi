# core/forms.py - Forms para SynchroBI

from django import forms
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from core.models import Usuario, Unidade, CentroCusto, ContaContabil, Fornecedor, ParametroSistema

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

class UnidadeForm(forms.ModelForm):
    """Formulário para criar/editar unidades organizacionais"""
    
    class Meta:
        model = Unidade
        fields = [
            'codigo_allstrategy', 'codigo_interno', 'nome', 
            'unidade_pai', 'tipo', 'descricao', 'responsavel', 'ativa'
        ]
        widgets = {
            'codigo_allstrategy': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: 1.2.01.20.01'
            }),
            'codigo_interno': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: 101 (para unidades analíticas)'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nome da unidade organizacional'
            }),
            'unidade_pai': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Descrição adicional da unidade...'
            }),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar queryset para unidade pai (só unidades sintéticas)
        self.fields['unidade_pai'].queryset = Unidade.objects.filter(
            tipo='S', ativa=True
        ).order_by('codigo_allstrategy')
        self.fields['unidade_pai'].empty_label = "Nenhuma (Unidade Raiz)"
        
        # Configurar queryset para responsável
        self.fields['responsavel'].queryset = Usuario.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name')
        self.fields['responsavel'].empty_label = "Nenhum responsável"
        
        # Se estiver editando, não permitir alterar para pai de si mesmo
        if self.instance.pk:
            # Excluir a própria unidade e suas sub-unidades das opções de pai
            excluir_ids = [self.instance.pk]
            sub_unidades = self.instance.get_todas_sub_unidades()
            excluir_ids.extend([u.pk for u in sub_unidades])
            
            self.fields['unidade_pai'].queryset = self.fields['unidade_pai'].queryset.exclude(
                pk__in=excluir_ids
            )
    
    def clean_codigo_allstrategy(self):
        """Validação específica para código All Strategy"""
        codigo = self.cleaned_data.get('codigo_allstrategy', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código All Strategy é obrigatório.")
        
        # Validar formato (números e pontos apenas)
        import re
        if not re.match(r'^[\d\.]+$', codigo):
            raise forms.ValidationError("Código deve conter apenas números e pontos.")
        
        # Verificar se já existe (excluindo a instância atual se estiver editando)
        queryset = Unidade.objects.filter(codigo_allstrategy=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma unidade com este código All Strategy.")
        
        return codigo
    
    def clean_codigo_interno(self):
        """Validação para código interno"""
        codigo_interno = self.cleaned_data.get('codigo_interno', '').strip()
        tipo = self.cleaned_data.get('tipo')
        
        # Se é analítica e não tem código interno, tentar extrair do All Strategy
        if tipo == 'A' and not codigo_interno:
            codigo_allstrategy = self.cleaned_data.get('codigo_allstrategy', '')
            if codigo_allstrategy:
                partes = codigo_allstrategy.split('.')
                ultimo_segmento = partes[-1]
                if ultimo_segmento.isdigit():
                    codigo_interno = ultimo_segmento
        
        # Verificar duplicação de código interno (se fornecido)
        if codigo_interno:
            queryset = Unidade.objects.filter(codigo_interno=codigo_interno)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError("Já existe uma unidade com este código interno.")
        
        return codigo_interno
    
    def clean(self):
        """Validação geral do formulário"""
        cleaned_data = super().clean()
        unidade_pai = cleaned_data.get('unidade_pai')
        codigo_allstrategy = cleaned_data.get('codigo_allstrategy', '')
        
        # Validar hierarquia baseada no código
        if unidade_pai and codigo_allstrategy:
            # O código deve começar com o código do pai
            if not codigo_allstrategy.startswith(unidade_pai.codigo_allstrategy + '.'):
                self.add_error('unidade_pai', 
                    f"Para ser filha de '{unidade_pai.codigo_allstrategy}', "
                    f"o código deve começar com '{unidade_pai.codigo_allstrategy}.'")
        
        return cleaned_data

class ImportarUnidadesForm(forms.Form):
    """Formulário para importar unidades do All Strategy via Excel"""
    
    arquivo_excel = forms.FileField(
        label="Arquivo Excel do All Strategy",
        help_text="Selecione o arquivo Excel com a estrutura organizacional",
        widget=forms.FileInput(attrs={
            'class': 'form-control', 
            'accept': '.xlsx,.xls'
        })
    )
    
    atualizar_existentes = forms.BooleanField(
        label="Atualizar unidades existentes",
        required=False,
        initial=True,
        help_text="Se marcado, os registros existentes serão atualizados com os novos dados",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    limpar_base_antes = forms.BooleanField(
        label="Limpar base antes da importação",
        required=False,
        initial=False,
        help_text="ATENÇÃO: Remove todas as unidades existentes antes de importar",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_arquivo_excel(self):
        arquivo = self.cleaned_data['arquivo_excel']
        
        # Verificar extensão
        if not arquivo.name.lower().endswith(('.xlsx', '.xls')):
            raise forms.ValidationError("Arquivo deve ser Excel (.xlsx ou .xls)")
        
        # Verificar tamanho (máximo 10MB)
        if arquivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Arquivo muito grande (máximo 10MB)")
        
        return arquivo
        
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