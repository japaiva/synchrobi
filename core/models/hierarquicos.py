# core/models/hierarquicos.py - MODELOS HIERÁRQUICOS

import logging
import re
from django.db import models
from django.core.cache import cache
from django.core.exceptions import ValidationError

from .base import HierarquiaDinamicaMixin
from .empresa import Empresa

logger = logging.getLogger('synchrobi')

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
    codigo_allstrategy = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Código All Strategy",
        db_index=True  # ÍNDICE PARA BUSCA RÁPIDA
    )
    nome = models.CharField(max_length=255, verbose_name="Nome da Unidade")
    
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
        
        # Validar código All Strategy se fornecido
        if self.codigo_allstrategy:
            # Verificar duplicação do código All Strategy apenas se não vazio
            query = Unidade.objects.filter(codigo_allstrategy=self.codigo_allstrategy, ativa=True)
            if self.pk:
                query = query.exclude(pk=self.pk)
            
            if query.exists():
                raise ValidationError({
                    'codigo_allstrategy': f'Já existe uma unidade ativa com código All Strategy "{self.codigo_allstrategy}"'
                })
    
    def save(self, *args, **kwargs):
        """Save simplificado - apenas calcula nível"""
        
        # Calcular nível baseado no número de pontos
        self.nivel = self.codigo.count('.') + 1
        
        # Limpar código All Strategy se vazio
        if not self.codigo_allstrategy:
            self.codigo_allstrategy = ''
        
        # Validar
        self.full_clean()
        
        super().save(*args, **kwargs)
        
        # Limpar cache relacionado
        self._limpar_cache()
    
    # MÉTODOS DE BUSCA OTIMIZADOS PARA IMPORTAÇÃO
    
    @classmethod
    def buscar_por_codigo_allstrategy(cls, codigo_allstrategy, apenas_ativas=True):
        """
        Busca unidade pelo código All Strategy (otimizado com índice)
        """
        if not codigo_allstrategy:
            return None
        
        try:
            query = cls.objects.filter(codigo_allstrategy=codigo_allstrategy)
            if apenas_ativas:
                query = query.filter(ativa=True)
            
            return query.first()  # Usar first() para evitar exceção se não encontrar
            
        except Exception as e:
            logger.error(f'Erro ao buscar unidade por código All Strategy {codigo_allstrategy}: {str(e)}')
            return None
    
    @classmethod
    def buscar_unidade_para_movimento(cls, codigo_unidade):
        """
        Busca unidade para movimentação - primeiro por All Strategy, depois por código normal
        """
        # Tentar primeiro por código All Strategy (mais comum para movimentos)
        unidade = cls.buscar_por_codigo_allstrategy(str(codigo_unidade))
        
        if unidade:
            return unidade
        
        # Se não encontrou, tentar por código normal
        try:
            return cls.objects.get(codigo=str(codigo_unidade), ativa=True)
        except cls.DoesNotExist:
            logger.warning(f'Unidade não encontrada para código: {codigo_unidade}')
            return None
    
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
        return f"{self.codigo_display} - {self.nome}"
    
    class Meta:
        db_table = 'unidades'
        verbose_name = 'Unidade Organizacional'
        verbose_name_plural = 'Unidades Organizacionais'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['codigo_allstrategy']),  # ÍNDICE PRINCIPAL PARA BUSCA
            models.Index(fields=['ativa']),
            models.Index(fields=['nivel']),
            models.Index(fields=['empresa']),
            models.Index(fields=['codigo_allstrategy', 'ativa']),  # ÍNDICE COMPOSTO OTIMIZADO
        ]

# ===== MODELO CENTRO DE CUSTO COM TIPO EDITÁVEL =====

class CentroCusto(models.Model, HierarquiaDinamicaMixin):
    """Centro de custo com hierarquia dinâmica baseada em código"""
    
    TIPO_CHOICES = [
        ('S', 'Sintético'),
        ('A', 'Analítico'),
    ]
    
    codigo = models.CharField(max_length=20, primary_key=True, verbose_name="Código")
    nome = models.CharField(max_length=255, verbose_name="Nome do Centro de Custo")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    # CAMPO TIPO EDITÁVEL - NÃO É CALCULADO
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
        """Validação baseada no código e regras de negócio"""
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
            
            # VALIDAÇÃO IMPORTANTE: pai deve ser sintético para aceitar filhos
            if pai.tipo == 'A':
                raise ValidationError({
                    'codigo': f'O centro pai "{pai.codigo} - {pai.nome}" é analítico e não pode ter sub-centros. '
                             f'Altere o tipo do centro pai para "Sintético" primeiro.'
                })
        
        # VALIDAÇÃO: não pode alterar para analítico se já tem filhos
        if self.pk and self.tipo == 'A' and self.tem_filhos:
            raise ValidationError({
                'tipo': 'Não é possível alterar para "Analítico" pois este centro possui sub-centros. '
                       'Remova os sub-centros primeiro ou mantenha como "Sintético".'
            })
    
    def save(self, *args, **kwargs):
        """Save com validação"""
        self.nivel = self.codigo.count('.') + 1
        self.full_clean()
        super().save(*args, **kwargs)
    
    # Propriedades baseadas APENAS no campo tipo (não em cálculos)
    @property
    def e_sintetico(self):
        """Verifica se é sintético (baseado APENAS no campo tipo)"""
        return self.tipo == 'S'
    
    @property
    def e_analitico(self):
        """Verifica se é analítico (baseado APENAS no campo tipo)"""
        return self.tipo == 'A'
    
    def get_tipo_display(self):
        """Retorna o nome do tipo para exibição"""
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
            models.Index(fields=['ativo']),
            models.Index(fields=['nivel']),
            models.Index(fields=['tipo']),
        ]

# ===== MODELO CONTA CONTÁBIL COM TIPO EDITÁVEL =====

class ContaContabil(models.Model, HierarquiaDinamicaMixin):
    """Conta contábil com hierarquia dinâmica baseada em código"""
    
    TIPO_CHOICES = [
        ('S', 'Sintético'),
        ('A', 'Analítico'),
    ]
    
    codigo = models.CharField(max_length=20, primary_key=True, verbose_name="Código")
    nome = models.CharField(max_length=255, verbose_name="Nome da Conta")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    # CAMPO TIPO EDITÁVEL - NÃO É CALCULADO
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
        """Validação baseada no código e regras de negócio"""
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
            
            # VALIDAÇÃO IMPORTANTE: pai deve ser sintético para aceitar filhos
            if pai.tipo == 'A':
                raise ValidationError({
                    'codigo': f'A conta pai "{pai.codigo} - {pai.nome}" é analítica e não pode ter sub-contas. '
                             f'Altere o tipo da conta pai para "Sintético" primeiro.'
                })
        
        # VALIDAÇÃO: não pode alterar para analítico se já tem filhos
        if self.pk and self.tipo == 'A' and self.tem_filhos:
            raise ValidationError({
                'tipo': 'Não é possível alterar para "Analítico" pois esta conta possui sub-contas. '
                       'Remova as sub-contas primeiro ou mantenha como "Sintético".'
            })
    
    def save(self, *args, **kwargs):
        """Save com validação"""
        self.nivel = self.codigo.count('.') + 1
        self.full_clean()
        super().save(*args, **kwargs)
    
    # Propriedades baseadas APENAS no campo tipo (não em cálculos)
    @property
    def e_sintetico(self):
        """Verifica se é sintético (baseado APENAS no campo tipo)"""
        return self.tipo == 'S'
    
    @property
    def e_analitico(self):
        """Verifica se é analítico (baseado APENAS no campo tipo)"""
        return self.tipo == 'A'
    
    def get_tipo_display(self):
        """Retorna o nome do tipo para exibição"""
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
        """Apenas contas analíticas aceitam lançamento"""
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
            models.Index(fields=['ativa']),
            models.Index(fields=['nivel']),
            models.Index(fields=['tipo']),
        ]