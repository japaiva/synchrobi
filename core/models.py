# core/models.py - Modelos com hierarquia dinâmica baseada em código

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

# ===== MIXIN PARA HIERARQUIA DINÂMICA =====

# ===== MIXIN PARA HIERARQUIA DINÂMICA CORRIGIDO =====

class HierarquiaDinamicaMixin:
    """Mixin para hierarquia baseada apenas no código, sem campos pai físicos"""
    
    @property
    def pai(self):
        """Retorna o pai baseado no código, calculado dinamicamente"""
        return self.encontrar_pai_hierarquico()
    
    def get_filhos_diretos(self):
        """Retorna apenas filhos diretos (um nível abaixo)"""
        if not self.pk:
            return self.__class__.objects.none()
        
        # Para modelo com campo 'ativo' ou 'ativa'
        active_field = 'ativo' if hasattr(self, 'ativo') else 'ativa'
        
        # Buscar todos os registros que começam com este código + ponto
        codigo_base = self.codigo + '.'
        candidatos = self.__class__.objects.filter(
            codigo__startswith=codigo_base,
            **{active_field: True}
        )
        
        # Filtrar apenas os filhos diretos (próximo nível)
        filhos_diretos = []
        nivel_atual = self.nivel
        
        for candidato in candidatos:
            if candidato.nivel == nivel_atual + 1:  # Apenas um nível abaixo
                filhos_diretos.append(candidato.pk)
        
        # Retornar queryset dos filhos diretos
        return self.__class__.objects.filter(pk__in=filhos_diretos)
    
    def encontrar_pai_hierarquico(self):
        """Encontra o pai mais próximo na hierarquia baseado no código"""
        if '.' not in self.codigo:
            return None
        
        partes = self.codigo.split('.')
        
        # Procura pai removendo segmentos do final até encontrar um que existe
        for i in range(len(partes) - 1, 0, -1):
            codigo_pai_candidato = '.'.join(partes[:i])
            try:
                return self.__class__.objects.get(codigo=codigo_pai_candidato)
            except self.__class__.DoesNotExist:
                continue
        
        return None
    
    def get_caminho_hierarquico(self):
        """Retorna caminho completo da hierarquia até este item"""
        caminho = [self]
        pai_atual = self.pai
        
        while pai_atual:
            caminho.insert(0, pai_atual)
            pai_atual = pai_atual.pai
        
        return caminho
    
    def get_todos_filhos_recursivo(self, include_self=False):
        """Retorna todos os filhos recursivamente"""
        filhos = []
        
        if include_self:
            filhos.append(self)
        
        for filho in self.get_filhos_diretos():
            filhos.append(filho)
            filhos.extend(filho.get_todos_filhos_recursivo(include_self=False))
        
        return filhos
    
    @property
    def tem_filhos(self):
        """Verifica se tem filhos diretos"""
        return self.get_filhos_diretos().exists()
    
    @property
    def nome_completo(self):
        """Nome com hierarquia completa"""
        pai = self.pai
        if pai:
            return f"{pai.nome_completo} > {self.nome}"
        return self.nome

# ===== MODELO USUARIO (deve vir primeiro) =====

class Usuario(AbstractUser):
    """
    Modelo de usuário customizado para o SynchroBI
    Baseado no portalcomercial com foco em gestão financeira
    """
    NIVEL_CHOICES = [
        ('admin', 'Administrador'),
        ('gestor', 'Gestor'),
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
    
    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

# ===== MODELO EMPRESA (deve vir antes de Unidade) =====

class Empresa(models.Model):
    """Modelo para cadastro de empresas do grupo"""
    
    sigla = models.CharField(max_length=15, primary_key=True, verbose_name="Sigla")
    razao_social = models.CharField(max_length=255, verbose_name="Razão Social")
    nome_fantasia = models.CharField(max_length=255, blank=True, verbose_name="Nome Fantasia")
    cnpj = models.CharField(max_length=18, unique=True, verbose_name="CNPJ")
    inscricao_estadual = models.CharField(max_length=30, blank=True, verbose_name="Inscrição Estadual")
    inscricao_municipal = models.CharField(max_length=30, blank=True, verbose_name="Inscrição Municipal")
    endereco = models.TextField(blank=True, verbose_name="Endereço")
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    email = models.EmailField(blank=True, verbose_name="E-mail")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    sincronizado_allstrategy = models.BooleanField(default=False, verbose_name="Sincronizado All Strategy")
    data_ultima_sincronizacao = models.DateTimeField(null=True, blank=True, verbose_name="Última Sincronização")
    
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
        """Retorna unidades vinculadas a esta empresa"""
        return self.unidades.filter(ativa=True)
    
    # MÉTODOS PARA CENTROS DE CUSTO (integrados na classe principal)
    def get_centros_custo_ativos(self):
        """Retorna centros de custo ativos desta empresa"""
        return self.centros_custo_empresa.filter(ativo=True).select_related(
            'centro_custo', 'responsavel'
        )
    
    def get_centros_custo_vigentes(self):
        """Retorna apenas centros de custo vigentes hoje"""
        hoje = timezone.now().date()
        return self.centros_custo_empresa.filter(
            ativo=True,
            data_inicio__lte=hoje
        ).filter(
            models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=hoje)
        ).select_related('centro_custo', 'responsavel')
    
    def get_responsaveis_centros_custo(self):
        """Retorna lista de responsáveis pelos centros de custo desta empresa"""
        return Usuario.objects.filter(
            centros_custo_responsavel__empresa=self,
            centros_custo_responsavel__ativo=True
        ).distinct()
    
    @property
    def total_centros_custo(self):
        """Total de centros de custo ativos"""
        return self.centros_custo_empresa.filter(ativo=True).count()
    
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

# ===== MODELO UNIDADE COM HIERARQUIA DINÂMICA =====

class Unidade(models.Model, HierarquiaDinamicaMixin):
    """Unidade organizacional com hierarquia dinâmica baseada em código"""

    TIPO_CHOICES = [
        ('S', 'Sintético'),
        ('A', 'Analítico'),
    ]

    tipo = models.CharField(
        max_length=1, 
        choices=TIPO_CHOICES, 
        default='A',
        verbose_name="Tipo"
    )

    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    codigo_allstrategy = models.CharField(max_length=20, blank=True, verbose_name="Código All Strategy")
    nome = models.CharField(max_length=255, verbose_name="Nome da Unidade")
    
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='unidades',
        verbose_name="Empresa",
        null=True,
        blank=True
    )
    
    # REMOVIDO: unidade_pai (agora dinâmico via HierarquiaDinamicaMixin)
    
    nivel = models.IntegerField(verbose_name="Nível Hierárquico")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    sincronizado_allstrategy = models.BooleanField(default=False, verbose_name="Sincronizado All Strategy")
    data_ultima_sincronizacao = models.DateTimeField(null=True, blank=True, verbose_name="Última Sincronização")
    
    def clean(self):
        """Validação baseada apenas no código"""
        super().clean()
        
        # Validar formato do código
        if not re.match(r'^[\d\.]+$', self.codigo):
            raise ValidationError({
                'codigo': 'Código deve conter apenas números e pontos'
            })
        
        # Verificar se pai existe (se código tem pontos)
        if '.' in self.codigo:
            pai = self.encontrar_pai_hierarquico()
            if not pai:
                raise ValidationError({
                    'codigo': f'Nenhuma unidade pai foi encontrada para o código "{self.codigo}". '
                             f'Certifique-se de que existe pelo menos uma unidade superior.'
                })
        
        # Para unidades novas (sem PK), sugerir código All Strategy se não fornecido
        if not self.pk and not self.codigo_allstrategy and self.codigo:
            partes = self.codigo.split('.')
            ultimo_segmento = partes[-1]
            if ultimo_segmento.isdigit():
                self.codigo_allstrategy = ultimo_segmento
    
    def save(self, *args, **kwargs):
        """Save simplificado - apenas calcula nível"""
        
        # Calcular nível baseado no número de pontos
        self.nivel = self.codigo.count('.') + 1
        
        # Validar
        self.full_clean()
        
        super().save(*args, **kwargs)
        
        # Limpar cache relacionado
        self._limpar_cache()
    
    def _limpar_cache(self):
        """Limpa cache relacionado a esta unidade"""
        cache_keys = [
            f'unidade_hierarchy_{self.id}',
            f'unidade_children_{self.id}',
            'unidades_ativas_tree'
        ]
        
        pai = self.pai
        if pai:
            cache_keys.append(f'unidade_children_{pai.id}')
        
        for key in cache_keys:
            cache.delete(key)
    
    # Propriedades para compatibilidade com código existente
    @property
    def unidade_pai(self):
        """Compatibilidade: retorna pai dinâmico"""
        return self.pai
    
    @property
    def sub_unidades(self):
        """Compatibilidade: retorna filhos diretos como queryset"""
        return self.get_filhos_diretos()
    
    @property
    def tem_sub_unidades(self):
        """Compatibilidade: verifica se tem filhos"""
        return self.tem_filhos
    
    @property
    def caminho_hierarquico(self):
        """Compatibilidade: retorna caminho hierárquico"""
        return self.get_caminho_hierarquico()
    
    def get_todas_sub_unidades(self, include_self=False):
        """Compatibilidade: retorna todos os filhos recursivamente"""
        return self.get_todos_filhos_recursivo(include_self=include_self)
    
    def get_unidades_operacionais(self):
        """Retorna apenas unidades analíticas (operacionais) desta árvore"""
        todas = self.get_todas_sub_unidades(include_self=True)
        return [u for u in todas if u.e_analitico]
    
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
    
    @property
    def codigo_display(self):
        """Código para exibição (All Strategy se analítico, codigo se sintético)"""
        if self.e_analitico and self.codigo_allstrategy:
            return self.codigo_allstrategy
        return self.codigo
    
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
            models.Index(fields=['nivel']),
            models.Index(fields=['empresa']),
        ]

# ===== MODELO CENTRO DE CUSTO COM HIERARQUIA DINÂMICA =====

class CentroCusto(models.Model, HierarquiaDinamicaMixin):
    """Centro de custo com hierarquia dinâmica baseada em código"""
    
    TIPO_CHOICES = [
        ('S', 'Sintético'),
        ('A', 'Analítico'),
    ]
    
    codigo = models.CharField(max_length=20, primary_key=True, verbose_name="Código")
    nome = models.CharField(max_length=255, verbose_name="Nome do Centro de Custo")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    tipo = models.CharField(
        max_length=1, 
        choices=TIPO_CHOICES, 
        default='A',
        verbose_name="Tipo"
    )
    
    # REMOVIDO: centro_pai (agora dinâmico via HierarquiaDinamicaMixin)
    
    nivel = models.IntegerField(verbose_name="Nível Hierárquico")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Validação baseada apenas no código"""
        super().clean()
        
        if not re.match(r'^[\d\.]+$', self.codigo):
            raise ValidationError({
                'codigo': 'Código deve conter apenas números e pontos'
            })
        
        if '.' in self.codigo:
            pai = self.encontrar_pai_hierarquico()
            if not pai:
                raise ValidationError({
                    'codigo': f'Nenhum centro pai foi encontrado para o código "{self.codigo}".'
                })
    
    def save(self, *args, **kwargs):
        """Save simplificado"""
        self.nivel = self.codigo.count('.') + 1
        self.full_clean()
        super().save(*args, **kwargs)
    
    # Propriedades para compatibilidade com código existente
    @property
    def centro_pai(self):
        """Compatibilidade: retorna pai dinâmico"""
        return self.pai
    
    @property
    def sub_centros(self):
        """Compatibilidade: retorna filhos diretos como queryset"""
        return self.get_filhos_diretos()
    
    @property
    def tem_sub_centros(self):
        """Compatibilidade: verifica se tem filhos"""
        return self.tem_filhos
    
    def get_tipo_display(self):
        """Retorna o nome do tipo para exibição"""
        return 'Sintético' if self.tipo == 'S' else 'Analítico'
    
    @property
    def e_sintetico(self):
        """Verifica se é sintético"""
        return self.tipo == 'S'
    
    @property
    def e_analitico(self):
        """Verifica se é analítico"""
        return self.tipo == 'A'
    
    # MÉTODOS PARA EMPRESAS VINCULADAS (integrados na classe principal)
    def get_empresas_vinculadas(self):
        """Retorna empresas vinculadas a este centro de custo"""
        return self.empresas_vinculadas.filter(ativo=True).select_related('empresa', 'responsavel')
    
    def get_responsaveis(self):
        """Retorna responsáveis por este centro de custo"""
        return Usuario.objects.filter(
            centros_custo_responsavel__centro_custo=self,
            centros_custo_responsavel__ativo=True
        ).distinct()
    
    @property
    def empresas_ativas_count(self):
        """Quantidade de empresas ativas vinculadas"""
        return self.empresas_vinculadas.filter(ativo=True).count()
    
    def __str__(self):
        tipo_icon = "💼" if self.e_sintetico else "🎯"
        return f"{tipo_icon} {self.codigo} - {self.nome}"
    
    class Meta:
        db_table = 'centros_custo'
        verbose_name = 'Centro de Custo'
        verbose_name_plural = 'Centros de Custo'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['ativo']),
            models.Index(fields=['nivel']),
            models.Index(fields=['tipo']),
        ]

# ===== MODELO CONTA CONTÁBIL COM HIERARQUIA DINÂMICA =====

class ContaContabil(models.Model, HierarquiaDinamicaMixin):
    """Conta contábil com hierarquia dinâmica baseada em código"""
    
    TIPO_CHOICES = [
        ('S', 'Sintético'),
        ('A', 'Analítico'),
    ]
    
    codigo = models.CharField(max_length=20, primary_key=True, verbose_name="Código")
    nome = models.CharField(max_length=255, verbose_name="Nome da Conta")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    tipo = models.CharField(
        max_length=1, 
        choices=TIPO_CHOICES, 
        default='A',
        verbose_name="Tipo"
    )
    
    # REMOVIDO: conta_pai (agora dinâmico via HierarquiaDinamicaMixin)
    
    nivel = models.IntegerField(verbose_name="Nível Hierárquico")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Validação baseada apenas no código"""
        super().clean()
        
        if not re.match(r'^[\d\.]+$', self.codigo):
            raise ValidationError({
                'codigo': 'Código deve conter apenas números e pontos'
            })
        
        if '.' in self.codigo:
            pai = self.encontrar_pai_hierarquico()
            if not pai:
                raise ValidationError({
                    'codigo': f'Nenhuma conta pai foi encontrada para o código "{self.codigo}".'
                })
    
    def save(self, *args, **kwargs):
        """Save simplificado"""
        self.nivel = self.codigo.count('.') + 1
        self.full_clean()
        super().save(*args, **kwargs)
    
    # Propriedades para compatibilidade com código existente
    @property
    def conta_pai(self):
        """Compatibilidade: retorna pai dinâmico"""
        return self.pai
    
    @property
    def subcontas(self):
        """Compatibilidade: retorna filhos diretos como queryset"""
        return self.get_filhos_diretos()
    
    @property
    def tem_subcontas(self):
        """Compatibilidade: verifica se tem filhos"""
        return self.tem_filhos
    
    @property
    def aceita_lancamento(self):
        """Contas analíticas aceitam lançamento, sintéticas não"""
        return self.e_analitico
    
    def get_tipo_display(self):
        """Retorna o nome do tipo para exibição"""
        return 'Sintético' if self.tipo == 'S' else 'Analítico'
    
    @property
    def e_sintetico(self):
        """Verifica se é sintético"""
        return self.tipo == 'S'
    
    @property
    def e_analitico(self):
        """Verifica se é analítico"""
        return self.tipo == 'A'
    
    def __str__(self):
        tipo_icon = "📊" if self.e_sintetico else "📋"
        return f"{tipo_icon} {self.codigo} - {self.nome}"
    
    class Meta:
        db_table = 'contas_contabeis'
        verbose_name = 'Conta Contábil'
        verbose_name_plural = 'Contas Contábeis'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['ativa']),
            models.Index(fields=['nivel']),
            models.Index(fields=['tipo']),
        ]

# ===== MODELO FORNECEDOR (mantido como estava) =====

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

# ===== MODELO PARÂMETRO SISTEMA (mantido como estava) =====

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

# ===== MODELO USUÁRIO CENTRO CUSTO =====

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

# ===== MODELO EMPRESA CENTRO CUSTO (relacionamento principal) =====

class EmpresaCentroCusto(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='centros_custo_empresa',
        verbose_name="Empresa"
    )
    
    centro_custo = models.ForeignKey(
        CentroCusto,
        on_delete=models.CASCADE,
        related_name='empresas_vinculadas',
        verbose_name="Centro de Custo"
    )
    
    responsavel = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='centros_custo_responsavel',
        verbose_name="Responsável"
    )

    
    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações"
    )
    
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )
    
    # Campos de controle
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    usuario_criacao = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empresa_centro_custo_criados',
        verbose_name="Criado por"
    )
    
    def clean(self):
        """Validação customizada"""
        super().clean()
        
        # Verificar se já existe relacionamento ativo para essa combinação
        if self.ativo:
            query = EmpresaCentroCusto.objects.filter(
                empresa=self.empresa,
                centro_custo=self.centro_custo,
                ativo=True
            )
            
            if self.pk:
                query = query.exclude(pk=self.pk)
            
            if query.exists():
                raise ValidationError({
                    '__all__': f'Já existe um relacionamento ativo entre {self.empresa.sigla} e {self.centro_custo.codigo}'
                })

    @property
    def status_display(self):
        """Status atual do relacionamento"""
        if not self.ativo:
            return "Inativo"
        
        hoje = timezone.now().date()
        
        if self.data_fim and hoje > self.data_fim:
            return "Vencido"
        elif self.data_inicio > hoje:
            return "Futuro"
        else:
            return "Ativo"
        
    def __str__(self):
        return f"{self.empresa.sigla} → {self.centro_custo.codigo} ({self.responsavel.first_name})"
    
    class Meta:
        db_table = 'empresa_centros_custo'
        verbose_name = 'Centro de Custo da Empresa'
        verbose_name_plural = 'Centros de Custo das Empresas'
        ordering = ['empresa__sigla', 'centro_custo__codigo']
        unique_together = ['empresa', 'centro_custo', 'ativo']  # Evita duplicatas ativas
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['centro_custo', 'ativo']),
            models.Index(fields=['responsavel']),
            models.Index(fields=['ativo']),
        ]