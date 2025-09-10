# core/forms/auxiliares.py - FORMULÁRIOS AUXILIARES

from django import forms
from django.core.exceptions import ValidationError

from core.models import ParametroSistema, ContaExterna, ContaContabil, Usuario

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