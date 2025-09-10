# core/forms.py - Forms simplificados para hierarquia dinâmica

from django import forms
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from core.models import Usuario, Unidade, CentroCusto, ContaContabil, ParametroSistema, Empresa,  ContaExterna

# ===== FORMULÁRIO UNIDADE SIMPLIFICADO =====


class UnidadeForm(forms.ModelForm):
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
        if codigo and '.' in codigo:
            temp_instance = Unidade(codigo=codigo)
            pai = temp_instance.encontrar_pai_hierarquico()
            
            if not pai:
                raise forms.ValidationError({
                    'codigo': f'Nenhuma unidade pai foi encontrada para o código "{codigo}". '
                             f'Certifique-se de que existe pelo menos uma unidade superior.'
                })
        
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

# ===== FORMULÁRIO CENTRO DE CUSTO SIMPLIFICADO =====
# Substituir em core/forms.py - Formulários corrigidos para tipo editável

class CentroCustoForm(forms.ModelForm):
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
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Validar formato
        import re
        if not re.match(r'^[\d\.]+$', codigo):
            raise forms.ValidationError("Código deve conter apenas números e pontos.")
        
        # Validações de formato
        if codigo.startswith('.') or codigo.endswith('.'):
            raise forms.ValidationError("Código não pode começar ou terminar com ponto.")
        
        if '..' in codigo:
            raise forms.ValidationError("Código não pode ter pontos consecutivos.")
        
        # Verificar duplicação
        queryset = CentroCusto.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(codigo=self.instance.codigo)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe um centro de custo com este código.")
        
        return codigo
    
    def clean_nome(self):
        """Validação para nome"""
        nome = self.cleaned_data.get('nome', '').strip()
        
        if not nome:
            raise forms.ValidationError("Nome é obrigatório.")
        
        if len(nome) < 3:
            raise forms.ValidationError("Nome deve ter pelo menos 3 caracteres.")
        
        return nome
    
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
        tipo = cleaned_data.get('tipo')
        
        # Verificar hierarquia
        if codigo and '.' in codigo:
            temp_instance = CentroCusto(codigo=codigo)
            pai = temp_instance.encontrar_pai_hierarquico()
            
            if not pai:
                partes = codigo.split('.')
                codigo_pai = '.'.join(partes[:-1])
                raise forms.ValidationError({
                    'codigo': f'Nenhum centro pai foi encontrado para o código "{codigo}". '
                             f'Certifique-se de que existe um centro com código "{codigo_pai}".'
                })
            
            # VALIDAÇÃO: pai deve ser sintético para aceitar filhos
            if pai.tipo == 'A':
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

class ContaContabilForm(forms.ModelForm):
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
        codigo = self.cleaned_data.get('codigo', '').strip()
        
        if not codigo:
            raise forms.ValidationError("Código é obrigatório.")
        
        # Validar formato
        import re
        if not re.match(r'^[\d\.]+$', codigo):
            raise forms.ValidationError("Código deve conter apenas números e pontos.")
        
        # Validações de formato
        if codigo.startswith('.') or codigo.endswith('.'):
            raise forms.ValidationError("Código não pode começar ou terminar com ponto.")
        
        if '..' in codigo:
            raise forms.ValidationError("Código não pode ter pontos consecutivos.")
        
        # Verificar duplicação
        queryset = ContaContabil.objects.filter(codigo=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(codigo=self.instance.codigo)
        
        if queryset.exists():
            raise forms.ValidationError("Já existe uma conta contábil com este código.")
        
        return codigo
    
    def clean_nome(self):
        """Validação para nome"""
        nome = self.cleaned_data.get('nome', '').strip()
        
        if not nome:
            raise forms.ValidationError("Nome é obrigatório.")
        
        if len(nome) < 3:
            raise forms.ValidationError("Nome deve ter pelo menos 3 caracteres.")
        
        return nome
    
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
        tipo = cleaned_data.get('tipo')
        
        # Verificar hierarquia
        if codigo and '.' in codigo:
            temp_instance = ContaContabil(codigo=codigo)
            pai = temp_instance.encontrar_pai_hierarquico()
            
            if not pai:
                partes = codigo.split('.')
                codigo_pai = '.'.join(partes[:-1])
                raise forms.ValidationError({
                    'codigo': f'Nenhuma conta pai foi encontrada para o código "{codigo}". '
                             f'Certifique-se de que existe uma conta com código "{codigo_pai}".'
                })
            
            # VALIDAÇÃO: pai deve ser sintético para aceitar filhos
            if pai.tipo == 'A':
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
    
# ===== FORMULÁRIOS MANTIDOS IGUAIS =====

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
    """Formulário simplificado para usuários SynchroBI"""
    
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
            'username', 'first_name', 'email', 'telefone',
            'nivel', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
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
        
        # Choices do nível
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
        
        # Limpar campos não utilizados
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

class ContaExternaForm(forms.ModelForm):
    """Formulário para criar/editar códigos de contas externas"""
    
    class Meta:
        model = ContaExterna
        fields = [
            'conta_contabil', 'codigo_externo', 'nome_externo', 
            'sistema_origem', 'empresas_utilizacao', 'observacoes', 'ativa'
        ]
        
        widgets = {
            'conta_contabil': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Selecione a conta contábil'
            }),
            'codigo_externo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 4210100001'
            }),
            'nome_externo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da conta no sistema externo'
            }),
            'sistema_origem': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Consinco, Protheus, SAP'
            }),
            'empresas_utilizacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Ex: CMC & EBC & Taiff & Action Motors'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações sobre esta conta externa'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        conta_contabil_codigo = kwargs.pop('conta_contabil_codigo', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar apenas contas contábeis ativas
        self.fields['conta_contabil'].queryset = ContaContabil.objects.filter(ativa=True).order_by('codigo')
        
        # Se foi passado um código de conta contábil, pré-selecionar
        if conta_contabil_codigo:
            try:
                conta = ContaContabil.objects.get(codigo=conta_contabil_codigo)
                self.fields['conta_contabil'].initial = conta
                self.fields['conta_contabil'].widget.attrs['readonly'] = True
            except ContaContabil.DoesNotExist:
                pass
        
        # Help texts personalizados
        self.fields['codigo_externo'].help_text = "Código da conta no sistema externo (ERP)"
        self.fields['nome_externo'].help_text = "Nome/descrição da conta conforme aparece no sistema externo"
        self.fields['sistema_origem'].help_text = "Nome do ERP ou sistema de origem"
        self.fields['empresas_utilizacao'].help_text = "Empresas que utilizam esta conta (separar com &)"
        
        # Campos obrigatórios
        self.fields['conta_contabil'].required = True
        self.fields['codigo_externo'].required = True
        self.fields['nome_externo'].required = True
    
    def clean_codigo_externo(self):
        """Validação do código externo"""
        codigo_externo = self.cleaned_data.get('codigo_externo', '').strip()
        conta_contabil = self.cleaned_data.get('conta_contabil')
        
        if not codigo_externo:
            raise forms.ValidationError("Código externo é obrigatório.")
        
        # Verificar duplicação para a mesma conta contábil
        if conta_contabil:
            queryset = ContaExterna.objects.filter(
                conta_contabil=conta_contabil,
                codigo_externo=codigo_externo,
                ativa=True
            )
            
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(
                    f'Já existe uma conta externa ativa com o código "{codigo_externo}" '
                    f'para a conta contábil "{conta_contabil.codigo}".'
                )
        
        return codigo_externo
    
    def clean_nome_externo(self):
        """Validação do nome externo"""
        nome_externo = self.cleaned_data.get('nome_externo', '').strip()
        
        if not nome_externo:
            raise forms.ValidationError("Nome externo é obrigatório.")
        
        if len(nome_externo) < 3:
            raise forms.ValidationError("Nome externo deve ter pelo menos 3 caracteres.")
        
        return nome_externo
    
    def clean(self):
        """Validação geral do formulário"""
        cleaned_data = super().clean()
        conta_contabil = cleaned_data.get('conta_contabil')
        ativa = cleaned_data.get('ativa')
        
        # Validação adicional: apenas contas analíticas podem ter códigos externos ativos
        # (esta regra pode ser flexibilizada se necessário)
        if conta_contabil and ativa and conta_contabil.e_sintetico:
            # Aviso, mas não erro (permitir flexibilidade)
            pass
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customizado"""
        conta_externa = super().save(commit=False)
        
        # Limpar campos
        if conta_externa.codigo_externo:
            conta_externa.codigo_externo = conta_externa.codigo_externo.strip()
        if conta_externa.nome_externo:
            conta_externa.nome_externo = conta_externa.nome_externo.strip()
        if conta_externa.sistema_origem:
            conta_externa.sistema_origem = conta_externa.sistema_origem.strip()
        
        if commit:
            conta_externa.save()
            
            # Log da operação
            import logging
            logger = logging.getLogger('synchrobi')
            action = "atualizada" if self.instance.pk else "criada"
            logger.info(
                f'Conta externa {action}: {conta_externa.codigo_externo} '
                f'→ {conta_externa.conta_contabil.codigo} por {getattr(self, "_user", "sistema")}'
            )
        
        return conta_externa

class ContaExternaFiltroForm(forms.Form):
    """Formulário para filtrar contas externas"""
    
    conta_contabil = forms.ModelChoiceField(
        queryset=ContaContabil.objects.filter(ativa=True).order_by('codigo'),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
        empty_label="Todas as contas contábeis",
        label="Conta Contábil"
    )
    
    sistema_origem = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Filtrar por sistema'
        }),
        required=False,
        label="Sistema"
    )
    
    codigo_externo = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Filtrar por código externo'
        }),
        required=False,
        label="Código Externo"
    )
    
    ativa = forms.ChoiceField(
        choices=[
            ('', 'Todas'),
            ('true', 'Ativas'),
            ('false', 'Inativas'),
        ],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
        label="Status"
    )

class ContaExternaBulkForm(forms.Form):
    """Formulário para operações em lote com contas externas"""
    
    ACTION_CHOICES = [
        ('ativar', 'Ativar selecionadas'),
        ('desativar', 'Desativar selecionadas'),
        ('sincronizar', 'Sincronizar selecionadas'),
        ('deletar', 'Deletar selecionadas'),
    ]
    
    contas_selecionadas = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    acao = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label="Ação"
    )
    
    confirmar = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=True,
        label="Confirmo que desejo executar esta ação"
    )
    
    def clean_contas_selecionadas(self):
        """Validar IDs das contas selecionadas"""
        ids_str = self.cleaned_data.get('contas_selecionadas', '')
        
        if not ids_str:
            raise forms.ValidationError("Nenhuma conta foi selecionada.")
        
        try:
            ids = [int(id_str.strip()) for id_str in ids_str.split(',') if id_str.strip()]
        except ValueError:
            raise forms.ValidationError("IDs inválidos selecionados.")
        
        if not ids:
            raise forms.ValidationError("Nenhuma conta foi selecionada.")
        
        # Verificar se todas as contas existem
        contas_existentes = ContaExterna.objects.filter(id__in=ids).count()
        if contas_existentes != len(ids):
            raise forms.ValidationError("Algumas contas selecionadas não foram encontradas.")
        
        return ids
    
    def execute_action(self, user=None):
        """Executar a ação selecionada"""
        acao = self.cleaned_data['acao']
        ids = self.cleaned_data['contas_selecionadas']
        
        queryset = ContaExterna.objects.filter(id__in=ids)
        count = queryset.count()
        
        if acao == 'ativar':
            queryset.update(ativa=True)
            return f"{count} conta(s) externa(s) ativada(s) com sucesso."
        
        elif acao == 'desativar':
            queryset.update(ativa=False)
            return f"{count} conta(s) externa(s) desativada(s) com sucesso."
        
        elif acao == 'sincronizar':
            from django.utils import timezone
            queryset.update(
                sincronizado=True,
                data_ultima_sincronizacao=timezone.now()
            )
            return f"{count} conta(s) externa(s) sincronizada(s) com sucesso."
        
        elif acao == 'deletar':
            queryset.delete()
            return f"{count} conta(s) externa(s) deletada(s) com sucesso."
        
        else:
            raise forms.ValidationError("Ação inválida selecionada.")