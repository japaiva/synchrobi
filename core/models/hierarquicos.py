# core/models/hierarquicos.py - HIERARQUIA DECLARADA SIMPLES PARA TODOS

import logging
import re
from django.db import models
from django.core.cache import cache
from django.core.exceptions import ValidationError

from .empresa import Empresa

logger = logging.getLogger('synchrobi')

# ===== CLASSE BASE PARA HIERARQUIA DECLARADA =====

class HierarchiaDeclaradaMixin:
    """Mixin para modelos com hierarquia declarada (campo pai explícito)"""
    
    @property
    def pai(self):
        """Retorna o item pai baseado no campo codigo_pai"""
        if not hasattr(self, 'codigo_pai') or not self.codigo_pai:
            return None
        
        try:
            return self.__class__.objects.get(codigo=self.codigo_pai)
        except self.__class__.DoesNotExist:
            return None
    
    def get_filhos_diretos(self):
        """Retorna filhos diretos"""
        # CORREÇÃO MÍNIMA: detectar campo ativo correto
        active_field = 'ativo' if hasattr(self, 'ativo') else 'ativa'
        filter_dict = {'codigo_pai': self.codigo, active_field: True}
        return self.__class__.objects.filter(**filter_dict).order_by('codigo')
    
    def get_todos_filhos(self):
        """Retorna todos os descendentes (recursivo)"""
        filhos = []
        
        def coletar_filhos(item):
            filhos_diretos = item.get_filhos_diretos()
            for filho in filhos_diretos:
                filhos.append(filho)
                coletar_filhos(filho)
        
        coletar_filhos(self)
        return filhos
    
    def get_caminho_completo(self):
        """Retorna caminho da raiz até este item"""
        caminho = []
        atual = self
        
        while atual:
            caminho.insert(0, atual)
            atual = atual.pai
        
        return caminho
    
    @property
    def tem_filhos(self):
        """Verifica se tem filhos"""
        # CORREÇÃO MÍNIMA: detectar campo ativo correto
        active_field = 'ativo' if hasattr(self, 'ativo') else 'ativa'
        filter_dict = {'codigo_pai': self.codigo, active_field: True}
        return self.__class__.objects.filter(**filter_dict).exists()
    
    def deduzir_pai_automaticamente(self):
        """Deduz pai baseado no código (para preenchimento automático)"""
        if '.' not in self.codigo:
            return None  # É raiz
        
        partes = self.codigo.split('.')
        
        # Tentar diferentes possibilidades de pai
        for i in range(len(partes) - 1, 0, -1):
            codigo_pai_candidato = '.'.join(partes[:i])
            
            try:
                pai = self.__class__.objects.get(codigo=codigo_pai_candidato)
                return pai.codigo
            except self.__class__.DoesNotExist:
                continue
        
        return None

# ===== MODELO UNIDADE COM HIERARQUIA DECLARADA =====

class Unidade(models.Model, HierarchiaDeclaradaMixin):
    """Unidade organizacional com hierarquia declarada"""

    TIPO_CHOICES = [
        ('S', 'Sintético'),
        ('A', 'Analítico'),
    ]

    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nome = models.CharField(max_length=255, verbose_name="Nome da Unidade")
    
    # HIERARQUIA DECLARADA
    codigo_pai = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Código da Unidade Pai",
        help_text="Código da unidade superior na hierarquia (deixe vazio para raiz)"
    )
    
    codigo_allstrategy = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Código All Strategy",
        db_index=True
    )
    
    tipo = models.CharField(
        max_length=1, 
        choices=TIPO_CHOICES, 
        default='A',
        verbose_name="Tipo"
    )
    
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='unidades',
        verbose_name="Empresa",
        null=True,
        blank=True
    )
    
    nivel = models.IntegerField(verbose_name="Nível Hierárquico")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Validação"""
        super().clean()
        
        if not re.match(r'^[\d\.]+$', self.codigo):
            raise ValidationError({
                'codigo': 'Código deve conter apenas números e pontos'
            })
        
        # Validar pai se fornecido
        if self.codigo_pai:
            try:
                pai = Unidade.objects.get(codigo=self.codigo_pai)
                if pai.tipo == 'A':
                    raise ValidationError({
                        'codigo_pai': f'A unidade pai "{pai.codigo} - {pai.nome}" é analítica e não pode ter sub-unidades.'
                    })
            except Unidade.DoesNotExist:
                raise ValidationError({
                    'codigo_pai': f'Unidade pai com código "{self.codigo_pai}" não existe'
                })
    
    def save(self, *args, **kwargs):
        """Save com preenchimento automático do pai"""
        
        # PREENCHIMENTO AUTOMÁTICO: se codigo_pai está vazio, tentar deduzir
        if not self.codigo_pai:
            pai_deduzido = self.deduzir_pai_automaticamente()
            if pai_deduzido:
                self.codigo_pai = pai_deduzido
        
        # Calcular nível baseado na hierarquia
        if self.codigo_pai:
            try:
                pai = Unidade.objects.get(codigo=self.codigo_pai)
                self.nivel = pai.nivel + 1
            except Unidade.DoesNotExist:
                self.nivel = 1
        else:
            self.nivel = 1
        
        # Limpar código All Strategy se vazio
        if not self.codigo_allstrategy:
            self.codigo_allstrategy = ''
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    @classmethod
    def buscar_por_codigo_allstrategy(cls, codigo_allstrategy, apenas_ativas=True):
        """Busca unidade pelo código All Strategy"""
        if not codigo_allstrategy:
            return None
        
        try:
            query = cls.objects.filter(codigo_allstrategy=codigo_allstrategy)
            if apenas_ativas:
                query = query.filter(ativa=True)
            return query.first()
        except Exception as e:
            logger.error(f'Erro ao buscar unidade por código All Strategy {codigo_allstrategy}: {str(e)}')
            return None
    
    @classmethod
    def buscar_unidade_para_movimento(cls, codigo_unidade):
        """Busca unidade para movimentação"""
        unidade = cls.buscar_por_codigo_allstrategy(str(codigo_unidade))
        if unidade:
            return unidade
        
        try:
            return cls.objects.get(codigo=str(codigo_unidade), ativa=True)
        except cls.DoesNotExist:
            logger.warning(f'Unidade não encontrada para código: {codigo_unidade}')
            return None
    
    # Propriedades para compatibilidade
    @property
    def unidade_pai(self):
        return self.pai
    
    @property
    def sub_unidades(self):
        return self.get_filhos_diretos()
    
    @property
    def tem_sub_unidades(self):
        return self.tem_filhos
    
    @property
    def e_sintetico(self):
        return self.tipo == 'S'
    
    @property
    def e_analitico(self):
        return self.tipo == 'A'
    
    @property
    def codigo_display(self):
        if self.e_analitico and self.codigo_allstrategy:
            return self.codigo_allstrategy
        return self.codigo
    
    def __str__(self):
        return f"{self.codigo_display} - {self.nome}"
    
    class Meta:
        db_table = 'unidades'
        verbose_name = 'Unidade Organizacional'
        verbose_name_plural = 'Unidades Organizacionais'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['codigo_pai']),
            models.Index(fields=['codigo_allstrategy']),
            models.Index(fields=['ativa']),
            models.Index(fields=['nivel']),
            models.Index(fields=['empresa']),
        ]

# ===== MODELO CENTRO DE CUSTO COM HIERARQUIA DECLARADA =====

class CentroCusto(models.Model, HierarchiaDeclaradaMixin):
    """Centro de custo com hierarquia declarada"""
    
    TIPO_CHOICES = [
        ('S', 'Sintético'),
        ('A', 'Analítico'),
    ]
    
    codigo = models.CharField(max_length=20, primary_key=True, verbose_name="Código")
    nome = models.CharField(max_length=255, verbose_name="Nome do Centro de Custo")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    # HIERARQUIA DECLARADA
    codigo_pai = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name="Código do Centro Pai",
        help_text="Código do centro de custo superior na hierarquia (deixe vazio para raiz)"
    )
    
    tipo = models.CharField(
        max_length=1, 
        choices=TIPO_CHOICES, 
        default='A',
        verbose_name="Tipo",
        help_text="S=Sintético (agrupador), A=Analítico (operacional)"
    )
    
    nivel = models.IntegerField(verbose_name="Nível Hierárquico")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Validação"""
        super().clean()
        
        if not re.match(r'^[\w\.-]+$', self.codigo):
            raise ValidationError({
                'codigo': 'Código deve conter apenas letras, números, pontos e hífens'
            })
        
        # Validar pai se fornecido
        if self.codigo_pai:
            try:
                pai = CentroCusto.objects.get(codigo=self.codigo_pai)
                if pai.tipo == 'A':
                    raise ValidationError({
                        'codigo_pai': f'O centro pai "{pai.codigo} - {pai.nome}" é analítico e não pode ter sub-centros.'
                    })
            except CentroCusto.DoesNotExist:
                raise ValidationError({
                    'codigo_pai': f'Centro de custo pai com código "{self.codigo_pai}" não existe'
                })
    
    def save(self, *args, **kwargs):
        """Save com preenchimento automático do pai"""
        
        # PREENCHIMENTO AUTOMÁTICO: se codigo_pai está vazio, tentar deduzir
        if not self.codigo_pai:
            pai_deduzido = self.deduzir_pai_automaticamente()
            if pai_deduzido:
                self.codigo_pai = pai_deduzido
        
        # Calcular nível baseado na hierarquia
        if self.codigo_pai:
            try:
                pai = CentroCusto.objects.get(codigo=self.codigo_pai)
                self.nivel = pai.nivel + 1
            except CentroCusto.DoesNotExist:
                self.nivel = 1
        else:
            self.nivel = 1
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    # Propriedades baseadas no campo tipo
    @property
    def e_sintetico(self):
        return self.tipo == 'S'
    
    @property
    def e_analitico(self):
        return self.tipo == 'A'
    
    def get_tipo_display(self):
        return 'Sintético' if self.tipo == 'S' else 'Analítico'
    
    # Propriedades para compatibilidade
    @property
    def centro_pai(self):
        return self.pai
    
    @property
    def sub_centros(self):
        return self.get_filhos_diretos()
    
    @property
    def tem_sub_centros(self):
        return self.tem_filhos
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"
    
    class Meta:
        db_table = 'centros_custo'
        verbose_name = 'Centro de Custo'
        verbose_name_plural = 'Centros de Custo'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['codigo_pai']),
            models.Index(fields=['ativo']),
            models.Index(fields=['nivel']),
            models.Index(fields=['tipo']),
        ]

# ===== MODELO CONTA CONTÁBIL COM HIERARQUIA DECLARADA =====

class ContaContabil(models.Model, HierarchiaDeclaradaMixin):
    """Conta contábil com hierarquia declarada"""
    
    TIPO_CHOICES = [
        ('S', 'Sintético'),
        ('A', 'Analítico'),
    ]
    
    codigo = models.CharField(max_length=20, primary_key=True, verbose_name="Código")
    nome = models.CharField(max_length=255, verbose_name="Nome da Conta")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    # HIERARQUIA DECLARADA
    codigo_pai = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name="Código da Conta Pai",
        help_text="Código da conta contábil superior na hierarquia (deixe vazio para raiz)"
    )
    
    tipo = models.CharField(
        max_length=1, 
        choices=TIPO_CHOICES, 
        default='A',
        verbose_name="Tipo",
        help_text="S=Sintético (agrupador), A=Analítico (aceita lançamentos)"
    )
    
    nivel = models.IntegerField(verbose_name="Nível Hierárquico")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Validação"""
        super().clean()
        
        if not re.match(r'^[\d\.]+$', self.codigo):
            raise ValidationError({
                'codigo': 'Código deve conter apenas números e pontos'
            })
        
        # Validar pai se fornecido
        if self.codigo_pai:
            try:
                pai = ContaContabil.objects.get(codigo=self.codigo_pai)
                if pai.tipo == 'A':
                    raise ValidationError({
                        'codigo_pai': f'A conta pai "{pai.codigo} - {pai.nome}" é analítica e não pode ter sub-contas.'
                    })
            except ContaContabil.DoesNotExist:
                raise ValidationError({
                    'codigo_pai': f'Conta contábil pai com código "{self.codigo_pai}" não existe'
                })
    
    def save(self, *args, **kwargs):
        """Save com preenchimento automático do pai"""
        
        # PREENCHIMENTO AUTOMÁTICO: se codigo_pai está vazio, tentar deduzir
        if not self.codigo_pai:
            pai_deduzido = self.deduzir_pai_automaticamente()
            if pai_deduzido:
                self.codigo_pai = pai_deduzido
        
        # Calcular nível baseado na hierarquia
        if self.codigo_pai:
            try:
                pai = ContaContabil.objects.get(codigo=self.codigo_pai)
                self.nivel = pai.nivel + 1
            except ContaContabil.DoesNotExist:
                self.nivel = 1
        else:
            self.nivel = 1
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    # Propriedades baseadas no campo tipo
    @property
    def e_sintetico(self):
        return self.tipo == 'S'
    
    @property
    def e_analitico(self):
        return self.tipo == 'A'
    
    def get_tipo_display(self):
        return 'Sintético' if self.tipo == 'S' else 'Analítico'
    
    # Propriedades para compatibilidade
    @property
    def conta_pai(self):
        return self.pai
    
    @property
    def subcontas(self):
        return self.get_filhos_diretos()
    
    @property
    def tem_subcontas(self):
        return self.tem_filhos
    
    @property
    def aceita_lancamento(self):
        return self.e_analitico
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"
    
    class Meta:
        db_table = 'contas_contabeis'
        verbose_name = 'Conta Contábil'
        verbose_name_plural = 'Contas Contábeis'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['codigo_pai']),
            models.Index(fields=['ativa']),
            models.Index(fields=['nivel']),
            models.Index(fields=['tipo']),
        ]