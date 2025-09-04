# core/models.py - Modelos base do SynchroBI - ORDEM CORRIGIDA

import logging
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from decimal import Decimal
import re

logger = logging.getLogger('synchrobi')

# ===== MODELO USUARIO (deve vir antes dos outros) =====

class Usuario(AbstractUser):
    """
    Modelo de usuário customizado para o SynchroBI
    Baseado no portalcomercial com foco em gestão financeira
    """
    NIVEL_CHOICES = [
        ('admin', 'Administrador'),
        ('gestor', 'Gestor Financeiro'),
        ('analista', 'Analista Financeiro'),
        ('contador', 'Contador'),
        ('diretor', 'Diretor'),
    ]

    # Desabilitar relacionamentos explicitamente
    groups = None  # Remove o relacionamento com grupos
    user_permissions = None  # Remove o relacionamento com permissões individuais
    
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='analista')
    is_superuser = models.BooleanField(default=False)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    
    # Campos específicos para controle financeiro
    centro_custo = models.CharField(max_length=20, blank=True, null=True,
                                   help_text="Centro de custo do usuário")
    unidade_negocio = models.CharField(max_length=50, blank=True, null=True,
                                      help_text="Unidade de negócio")
    
    def __str__(self):
        nome_completo = f"{self.first_name} {self.last_name}".strip()
        return nome_completo or self.username
    
    def get_centros_custo_permitidos(self):
        """
        Retorna queryset dos centros de custo que este usuário pode visualizar
        """
        # Admin e Diretor veem todos
        if self.nivel in ['admin', 'diretor']:
            return CentroCusto.objects.filter(ativo=True).order_by('codigo')
        
        # Gestor vê centros de custo da sua unidade + os que tem acesso específico
        if self.nivel == 'gestor':
            return CentroCusto.objects.filter(
                models.Q(unidade_negocio=self.unidade_negocio) |
                models.Q(usuarios_com_acesso__usuario=self),
                ativo=True
            ).distinct().order_by('codigo')
        
        # Outros usuários veem apenas os permitidos especificamente
        try:
            return CentroCusto.objects.filter(
                usuarios_com_acesso__usuario=self,
                usuarios_com_acesso__ativo=True,
                ativo=True
            ).distinct().order_by('codigo')
        except:
            return CentroCusto.objects.none()
    
    def pode_visualizar_centro_custo(self, centro_custo_codigo):
        """
        Verifica se o usuário pode visualizar um centro de custo específico
        """
        if self.nivel in ['admin', 'diretor']:
            return True
        
        return self.get_centros_custo_permitidos().filter(
            codigo=centro_custo_codigo
        ).exists()
    
    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

class Unidade(models.Model):
    """
    Modelo para estrutura organizacional hierárquica da empresa
    O tipo (Sintético/Analítico) é determinado automaticamente:
    - Sintético: tem sub-unidades
    - Analítico: não tem sub-unidades (folha da árvore)
    """
    
    # ===== CAMPOS PRINCIPAIS =====
    codigo = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Código",
        help_text="Código hierárquico da unidade (ex: 1.2.01.20.01.101)"
    )
    
    codigo_allstrategy = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Código All Strategy",
        help_text="Código original/interno da unidade (ex: 101, 102, etc)"
    )
    
    nome = models.CharField(
        max_length=255,
        verbose_name="Nome da Unidade"
    )
    
    # ===== HIERARQUIA =====
    unidade_pai = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_unidades',
        verbose_name="Unidade Superior"
    )
    
    nivel = models.IntegerField(
        verbose_name="Nível Hierárquico",
        help_text="Nível na hierarquia (calculado automaticamente)"
    )
    
    # ===== STATUS =====
    ativa = models.BooleanField(
        default=True,
        verbose_name="Ativa"
    )
    
    # ===== CAMPOS COMPLEMENTARES =====
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )
    
    # ===== CAMPOS DE CONTROLE =====
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    # ===== METADADOS ALL STRATEGY =====
    sincronizado_allstrategy = models.BooleanField(
        default=False,
        verbose_name="Sincronizado All Strategy"
    )
    
    data_ultima_sincronizacao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última Sincronização"
    )
    
    @property
    def tipo(self):
        """
        Tipo determinado dinamicamente:
        - 'S' (Sintético) se tem sub-unidades
        - 'A' (Analítico) se não tem sub-unidades
        """
        # Se não tem PK ainda (está sendo criado), é analítico por padrão
        if not self.pk:
            return 'A'
        
        # Usar cache para evitar múltiplas queries
        if not hasattr(self, '_cached_tipo'):
            self._cached_tipo = 'S' if self.tem_sub_unidades else 'A'
        return self._cached_tipo
    
    def get_tipo_display(self):
        """Retorna o nome do tipo para exibição"""
        return 'Sintético' if self.tipo == 'S' else 'Analítico'
    
    @property
    def e_sintetico(self):
        """Verifica se é sintético (tem sub-unidades)"""
        return self.tipo == 'S'
    
    @property
    def e_analitico(self):
        """Verifica se é analítico (folha da árvore)"""
        return self.tipo == 'A'
    
    def clean(self):
        """Validação customizada"""
        super().clean()
        
        # Validar formato do código principal
        if not re.match(r'^[\d\.]+$', self.codigo):
            raise ValidationError({
                'codigo': 'Código deve conter apenas números e pontos'
            })
        
        # Se não tem pai e não é o nível 1, deve ter pai
        if '.' in self.codigo and not self.unidade_pai:
            # Tentar encontrar o pai baseado no código
            partes = self.codigo.split('.')
            codigo_pai = '.'.join(partes[:-1])
            
            try:
                self.unidade_pai = Unidade.objects.get(codigo=codigo_pai)
            except Unidade.DoesNotExist:
                raise ValidationError({
                    'codigo': f'Unidade pai com código "{codigo_pai}" não existe'
                })
        
        # Para unidades novas (sem PK), sugerir código All Strategy se não fornecido
        if not self.pk and not self.codigo_allstrategy and self.codigo:
            # Extrair último segmento numérico do código
            partes = self.codigo.split('.')
            ultimo_segmento = partes[-1]
            if ultimo_segmento.isdigit():
                self.codigo_allstrategy = ultimo_segmento
    
    def save(self, *args, **kwargs):
        """Override do save para calcular nível e pai automaticamente"""
        
        # Calcular nível baseado no número de pontos no código
        self.nivel = self.codigo.count('.') + 1
        
        # Buscar unidade pai baseada no código se não foi definida
        if not self.unidade_pai and '.' in self.codigo:
            partes = self.codigo.split('.')
            codigo_pai = '.'.join(partes[:-1])
            
            try:
                self.unidade_pai = Unidade.objects.get(codigo=codigo_pai)
            except Unidade.DoesNotExist:
                pass  # Será validado no clean()
        
        # Validar antes de salvar
        self.full_clean()
        
        super().save(*args, **kwargs)
        
        # Limpar cache relacionado
        self._limpar_cache()
    
    def _limpar_cache(self):
        """Limpa cache relacionado a esta unidade"""
        from django.core.cache import cache
        
        # Limpar cache próprio
        if hasattr(self, '_cached_tipo'):
            del self._cached_tipo
        
        # Limpar cache do Django
        cache_keys = [
            f'unidade_hierarchy_{self.id}',
            f'unidade_children_{self.id}',
            'unidades_ativas_tree'
        ]
        
        # Limpar cache da unidade pai também (pois o tipo dela pode ter mudado)
        if self.unidade_pai:
            cache_keys.append(f'unidade_children_{self.unidade_pai.id}')
            if hasattr(self.unidade_pai, '_cached_tipo'):
                del self.unidade_pai._cached_tipo
        
        for key in cache_keys:
            cache.delete(key)
    
    @property
    def codigo_display(self):
        """Código para exibição (All Strategy se analítico, codigo se sintético)"""
        if self.e_analitico and self.codigo_allstrategy:
            return self.codigo_allstrategy
        return self.codigo
    
    @property
    def nome_completo(self):
        """Nome com hierarquia completa"""
        if self.unidade_pai:
            return f"{self.unidade_pai.nome_completo} > {self.nome}"
        return self.nome
    
    @property
    def caminho_hierarquico(self):
        """Lista com toda a hierarquia até esta unidade"""
        caminho = []
        unidade_atual = self
        
        while unidade_atual:
            caminho.insert(0, unidade_atual)
            unidade_atual = unidade_atual.unidade_pai
        
        return caminho
    
    @property
    def tem_sub_unidades(self):
        """Verifica se tem sub-unidades ativas"""
        # Se não tem PK, não pode ter sub-unidades
        if not self.pk:
            return False
        return self.sub_unidades.filter(ativa=True).exists()
    
    def get_todas_sub_unidades(self, include_self=False):
        """Retorna todas as sub-unidades recursivamente"""
        # Se não tem PK, retorna lista vazia
        if not self.pk:
            return []
            
        from django.core.cache import cache
        cache_key = f'unidade_children_{self.id}_{include_self}'
        resultado = cache.get(cache_key)
        
        if resultado is None:
            unidades = []
            
            if include_self:
                unidades.append(self)
            
            # Buscar filhos diretos
            for filho in self.sub_unidades.filter(ativa=True):
                unidades.append(filho)
                # Recursão para sub-unidades dos filhos
                unidades.extend(filho.get_todas_sub_unidades(include_self=False))
            
            resultado = unidades
            cache.set(cache_key, resultado, 300)  # Cache por 5 minutos
        
        return resultado
    
    def get_unidades_operacionais(self):
        """Retorna apenas unidades analíticas (operacionais) desta árvore"""
        todas = self.get_todas_sub_unidades(include_self=True)
        return [u for u in todas if u.e_analitico]
    
    def delete(self, *args, **kwargs):
        """Override do delete para limpar cache do pai"""
        pai = self.unidade_pai
        super().delete(*args, **kwargs)
        
        # Se tinha pai, limpar cache dele pois pode ter mudado de sintético para analítico
        if pai:
            if hasattr(pai, '_cached_tipo'):
                del pai._cached_tipo
            from django.core.cache import cache
            cache.delete(f'unidade_children_{pai.id}_True')
            cache.delete(f'unidade_children_{pai.id}_False')
    
    def __str__(self):
        tipo_icon = "📁" if self.e_sintetico else "🏢"
        return f"{tipo_icon} {self.codigo_display} - {self.nome}"
    
    class Meta:
        db_table = 'unidades'
        verbose_name = 'Unidade Organizacional'
        verbose_name_plural = 'Unidades Organizacionais'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['codigo_allstrategy']),
            models.Index(fields=['ativa']),
            models.Index(fields=['unidade_pai', 'ativa']),
            models.Index(fields=['nivel']),
        ]

class Empresa(models.Model):
    """Modelo para cadastro de empresas do grupo"""
    
    # ===== CAMPOS PRINCIPAIS =====
    sigla = models.CharField(
        max_length=15, 
        primary_key=True,
        verbose_name="Sigla"
    )
    
    razao_social = models.CharField(
        max_length=255,
        verbose_name="Razão Social"
    )
    
    nome_fantasia = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name="Nome Fantasia"
    )
    
    # ===== IDENTIFICAÇÃO FISCAL =====
    cnpj = models.CharField(
        max_length=18, 
        unique=True,
        verbose_name="CNPJ"
    )
    
    inscricao_estadual = models.CharField(
        max_length=30, 
        blank=True,
        verbose_name="Inscrição Estadual"
    )
    
    inscricao_municipal = models.CharField(
        max_length=30, 
        blank=True,
        verbose_name="Inscrição Municipal"
    )
    
    # ===== CONTATOS =====
    endereco = models.TextField(
        blank=True,
        verbose_name="Endereço"
    )
    
    telefone = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Telefone"
    )
    
    email = models.EmailField(
        blank=True,
        verbose_name="E-mail"
    )
    
    # ===== CONFIGURAÇÕES =====
    ativa = models.BooleanField(
        default=True,
        verbose_name="Ativa"
    )
    
    # ===== CAMPOS DE CONTROLE =====
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    # ===== METADADOS ALL STRATEGY =====
    sincronizado_allstrategy = models.BooleanField(
        default=False,
        verbose_name="Sincronizado All Strategy"
    )
    
    data_ultima_sincronizacao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última Sincronização"
    )
    
    def clean(self):
        """Validação customizada"""
        super().clean()
        
        # Validar CNPJ (formato básico)
        import re
        cnpj_limpo = re.sub(r'[^\d]', '', self.cnpj)
        if len(cnpj_limpo) != 14:
            raise ValidationError({
                'cnpj': 'CNPJ deve conter 14 dígitos'
            })
    
    def save(self, *args, **kwargs):
        """Override do save para formatação automática"""
        
        # Formatar CNPJ automaticamente
        if self.cnpj:
            import re
            cnpj_limpo = re.sub(r'[^\d]', '', self.cnpj)
            if len(cnpj_limpo) == 14:
                self.cnpj = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"
        
        # Validar antes de salvar
        self.full_clean()
        
        super().save(*args, **kwargs)
        
        # Log da operação
        logger.info(f'Empresa {"atualizada" if self.pk else "criada"}: {self.sigla} - {self.razao_social}')
    
    @property
    def nome_display(self):
        """Nome para exibição (nome fantasia se houver, senão razão social)"""
        return self.nome_fantasia or self.razao_social
    
    @property
    def cnpj_formatado(self):
        """CNPJ já formatado para exibição"""
        return self.cnpj
    
    @property
    def cnpj_limpo(self):
        """CNPJ apenas com números"""
        import re
        return re.sub(r'[^\d]', '', self.cnpj)
    
    @property
    def endereco_resumido(self):
        """Endereço resumido para listas"""
        if not self.endereco:
            return ""
        return self.endereco[:50] + "..." if len(self.endereco) > 50 else self.endereco
    
    def get_unidades_vinculadas(self):
        """Retorna unidades vinculadas a esta empresa (se houver relacionamento futuro)"""
        # Placeholder para futuras integrações
        return []
    
    def __str__(self):
        return f"{self.sigla} - {self.nome_display}"
    
    class Meta:
        db_table = 'empresas'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['sigla']
        indexes = [
            models.Index(fields=['sigla']),
            models.Index(fields=['cnpj']),
            models.Index(fields=['ativa']),
        ]

class CentroCusto(models.Model):
    """Centros de custo para controle gerencial"""
    codigo = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, 
                               related_name='centros_custo', null=True, blank=True)
    responsavel = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='centros_custo_responsavel')
    tipo = models.CharField(max_length=50, choices=[
        ('operacional', 'Operacional'),
        ('administrativo', 'Administrativo'),
        ('comercial', 'Comercial'),
        ('financeiro', 'Financeiro'),
        ('ti', 'Tecnologia da Informação'),
        ('rh', 'Recursos Humanos'),
        ('projeto', 'Projeto Específico'),
    ], default='operacional')
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    # Campos para orçamento
    orcamento_anual = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    orcamento_mensal = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"
    
    class Meta:
        db_table = 'centros_custo'
        verbose_name = 'Centro de Custo'
        verbose_name_plural = 'Centros de Custo'
        ordering = ['codigo']

class ContaContabil(models.Model):
    """Plano de contas contábil"""
    codigo = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    
    # Hierarquia
    conta_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='subcontas')
    nivel = models.IntegerField()
    
    # Classificação DRE
    tipo_conta = models.CharField(max_length=50, choices=[
        ('receita', 'Receita'),
        ('custo', 'Custo'),
        ('despesa', 'Despesa'),
        ('ativo', 'Ativo'),
        ('passivo', 'Passivo'),
        ('patrimonio', 'Patrimônio Líquido'),
    ])
    
    # Classificação para relatórios gerenciais
    categoria_dre = models.CharField(max_length=100, blank=True, help_text="Ex: Receita Bruta, CMV, Despesas Operacionais")
    subcategoria_dre = models.CharField(max_length=100, blank=True, help_text="Ex: Vendas, Material, Pessoal")
    
    ativa = models.BooleanField(default=True)
    aceita_lancamento = models.BooleanField(default=True, help_text="Se False, é conta sintética")
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"
    
    class Meta:
        db_table = 'contas_contabeis'
        verbose_name = 'Conta Contábil'
        verbose_name_plural = 'Contas Contábeis'
        ordering = ['codigo']

class Fornecedor(models.Model):
    """Cadastro de fornecedores"""
    codigo = models.CharField(max_length=20, primary_key=True)
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True)
    cnpj_cpf = models.CharField(max_length=18)
    inscricao_estadual = models.CharField(max_length=30, blank=True)
    endereco = models.TextField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Dados bancários
    banco = models.CharField(max_length=100, blank=True)
    agencia = models.CharField(max_length=10, blank=True)
    conta = models.CharField(max_length=20, blank=True)
    pix = models.CharField(max_length=100, blank=True)
    
    ativo = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.codigo} - {self.razao_social}"
    
    class Meta:
        db_table = 'fornecedores'
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['razao_social']

# Modelo para parâmetros globais do sistema
class ParametroSistema(models.Model):
    """Parâmetros globais de configuração do sistema"""
    
    TIPO_CHOICES = [
        ('texto', 'Texto'),
        ('numero', 'Número'),
        ('decimal', 'Decimal'),
        ('boolean', 'Verdadeiro/Falso'),
        ('data', 'Data'),
        ('json', 'JSON'),
    ]
    
    codigo = models.CharField(max_length=50, primary_key=True, 
                             help_text="Código único do parâmetro")
    nome = models.CharField(max_length=255, verbose_name="Nome")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='texto')
    valor = models.TextField(verbose_name="Valor", 
                            help_text="Valor do parâmetro (será convertido conforme o tipo)")
    valor_padrao = models.TextField(blank=True, verbose_name="Valor Padrão")
    
    categoria = models.CharField(max_length=50, default='geral',
                               help_text="Categoria para organização (ex: financeiro, sistema, etc)")
    
    editavel = models.BooleanField(default=True, 
                                  help_text="Se False, parâmetro não pode ser editado via interface")
    ativo = models.BooleanField(default=True)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    usuario_alteracao = models.ForeignKey(Usuario, on_delete=models.SET_NULL, 
                                         null=True, blank=True)
    
    def get_valor_convertido(self):
        """Retorna o valor convertido para o tipo apropriado"""
        if not self.valor:
            return None
            
        try:
            if self.tipo == 'numero':
                return int(self.valor)
            elif self.tipo == 'decimal':
                return float(self.valor)
            elif self.tipo == 'boolean':
                return self.valor.lower() in ['true', '1', 'sim', 'verdadeiro']
            elif self.tipo == 'data':
                from datetime import datetime
                return datetime.strptime(self.valor, '%Y-%m-%d').date()
            elif self.tipo == 'json':
                import json
                return json.loads(self.valor)
            else:
                return self.valor
        except (ValueError, TypeError):
            return self.valor_padrao if self.valor_padrao else None
    
    def set_valor(self, valor):
        """Define o valor convertendo para string"""
        if valor is None:
            self.valor = ''
        elif self.tipo == 'json':
            import json
            self.valor = json.dumps(valor)
        else:
            self.valor = str(valor)
    
    @classmethod
    def get_parametro(cls, codigo, default=None):
        """Método utilitário para buscar parâmetro"""
        try:
            param = cls.objects.get(codigo=codigo, ativo=True)
            return param.get_valor_convertido()
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_parametro(cls, codigo, valor, usuario=None):
        """Método utilitário para definir parâmetro"""
        param, created = cls.objects.get_or_create(
            codigo=codigo,
            defaults={'valor': str(valor), 'usuario_alteracao': usuario}
        )
        if not created:
            param.set_valor(valor)
            param.usuario_alteracao = usuario
            param.save()
        return param
    
    def __str__(self):
        return f"{self.nome} ({self.codigo})"
    
    class Meta:
        db_table = 'parametros_sistema'
        verbose_name = 'Parâmetro do Sistema'
        verbose_name_plural = 'Parâmetros do Sistema'
        ordering = ['categoria', 'nome']

# Modelo para gerenciar permissões de centro de custo por usuário
# AGORA O CentroCusto JÁ FOI DEFINIDO ACIMA, ENTÃO PODE SER REFERENCIADO
class UsuarioCentroCusto(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='centros_custo_permitidos')
    centro_custo = models.ForeignKey(CentroCusto, on_delete=models.CASCADE, related_name='usuarios_com_acesso')
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'usuario_centros_custo'
        unique_together = ['usuario', 'centro_custo']
        verbose_name = 'Permissão Centro de Custo'
        verbose_name_plural = 'Permissões Centros de Custo'