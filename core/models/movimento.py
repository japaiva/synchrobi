# core/models/movimento.py - MODELO DE MOVIMENTO ATUALIZADO

import logging
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal

from .hierarquicos import Unidade, CentroCusto, ContaContabil
from .fornecedor import Fornecedor

logger = logging.getLogger('synchrobi')

class Movimento(models.Model):
    """
    Movimentação financeira/contábil com relacionamentos para unidade, centro de custo, 
    conta contábil e fornecedor - VERSÃO ATUALIZADA PARA IMPORTAÇÃO POR PERÍODO
    """
    
    NATUREZA_CHOICES = [
        ('D', 'Débito'),
        ('C', 'Crédito'),
        ('A', 'Ambas'),
    ]
    
    # Campos temporais
    mes = models.IntegerField(verbose_name="Mês")
    ano = models.IntegerField(verbose_name="Ano")
    data = models.DateField(verbose_name="Data do Movimento", db_index=True)  # ÍNDICE PARA BUSCA POR DATA
    
    # Relacionamentos principais (FKs)
    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        related_name='movimentos',
        verbose_name="Unidade",
        help_text="Unidade organizacional"
    )
    
    centro_custo = models.ForeignKey(
        CentroCusto,
        on_delete=models.PROTECT,
        related_name='movimentos',
        verbose_name="Centro de Custo"
    )
    
    conta_contabil = models.ForeignKey(
        ContaContabil,
        on_delete=models.PROTECT,
        related_name='movimentos',
        verbose_name="Conta Contábil"
    )
    
    fornecedor = models.ForeignKey(
        Fornecedor,
        on_delete=models.PROTECT,
        related_name='movimentos',
        verbose_name="Fornecedor",
        null=True,
        blank=True,
        help_text="Fornecedor extraído do histórico (quando aplicável)"
    )
    
    # Campos do movimento
    documento = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name="Documento",
        help_text="Número do documento"
    )
    
    natureza = models.CharField(
        max_length=1, 
        choices=NATUREZA_CHOICES,
        verbose_name="Natureza",
        help_text="D=Débito, C=Crédito, A=Ambas"
    )
    
    valor = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name="Valor",
        help_text="Valor do movimento"
    )
    
    historico = models.TextField(
        verbose_name="Histórico",
        help_text="Histórico completo da movimentação"
    )
    
    # Campos opcionais
    codigo_projeto = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Código do Projeto"
    )
    
    gerador = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Gerador",
        help_text="Sistema ou processo que gerou o movimento"
    )
    
    rateio = models.CharField(
        max_length=1, 
        default='N',
        verbose_name="Rateio",
        help_text="S=Sim, N=Não"
    )
    
    # Campos de controle
    data_importacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Importação"
    )
    
    arquivo_origem = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Arquivo de Origem",
        help_text="Nome do arquivo Excel de origem"
    )
    
    linha_origem = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Linha de Origem",
        help_text="Linha no arquivo Excel de origem"
    )
    
    # Campos calculados para otimização
    periodo_mes_ano = models.CharField(
        max_length=7,
        verbose_name="Período",
        help_text="Formato YYYY-MM para indexação rápida",
        db_index=True
    )
    
    valor_absoluto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Valor Absoluto",
        help_text="Valor sem sinal para totalizações"
    )
    
    def clean(self):
        """Validação customizada"""
        super().clean()
        
        if self.data:
            # Extrair mês e ano da data automaticamente
            self.mes = self.data.month
            self.ano = self.data.year
            
            # Validar limites do ano
            if self.ano < 2000 or self.ano > 2100:
                raise ValidationError({
                    'data': 'Ano deve estar entre 2000 e 2100'
                })

    def save(self, *args, **kwargs):
        """Save com cálculos automáticos"""
        
        # Se tem data, extrair mês e ano automaticamente
        if self.data:
            self.mes = self.data.month
            self.ano = self.data.year
            
            # Calcular período para indexação
            self.periodo_mes_ano = f"{self.ano}-{self.mes:02d}"
        
        # Calcular valor absoluto
        self.valor_absoluto = abs(self.valor) if self.valor else 0
        
        # Validar
        self.full_clean()
        
        super().save(*args, **kwargs)
    
    # MÉTODOS DE CONSULTA POR PERÍODO DE DATAS
    
    @classmethod
    def get_movimentos_periodo_datas(cls, data_inicio, data_fim):
        """
        Busca movimentos por período de datas
        """
        return cls.objects.filter(
            data__gte=data_inicio,
            data__lte=data_fim
        ).select_related(
            'unidade', 'centro_custo', 'conta_contabil', 'fornecedor'
        ).order_by('data', 'id')
    
    @classmethod
    def limpar_periodo_datas(cls, data_inicio, data_fim):
        """
        Remove movimentos de um período de datas antes de nova importação
        """
        movimentos_periodo = cls.get_movimentos_periodo_datas(data_inicio, data_fim)
        count = movimentos_periodo.count()
        
        if count > 0:
            movimentos_periodo.delete()
            logger.info(f'{count} movimentos removidos do período {data_inicio} a {data_fim}')
        
        return count
    
    @classmethod
    def get_movimentos_periodo(cls, mes_inicio, ano_inicio, mes_fim=None, ano_fim=None):
        """
        Busca movimentos por período - MÉTODO MANTIDO PARA COMPATIBILIDADE
        """
        if mes_fim is None:
            mes_fim = mes_inicio
        if ano_fim is None:
            ano_fim = ano_inicio
        
        periodo_inicio = f"{ano_inicio}-{mes_inicio:02d}"
        periodo_fim = f"{ano_fim}-{mes_fim:02d}"
        
        return cls.objects.filter(
            periodo_mes_ano__gte=periodo_inicio,
            periodo_mes_ano__lte=periodo_fim
        ).select_related(
            'unidade', 'centro_custo', 'conta_contabil', 'fornecedor'
        ).order_by('data', 'id')
    
    @classmethod
    def limpar_periodo(cls, mes_inicio, ano_inicio, mes_fim=None, ano_fim=None):
        """
        Remove movimentos de um período antes de nova importação - MÉTODO MANTIDO
        """
        movimentos_periodo = cls.get_movimentos_periodo(mes_inicio, ano_inicio, mes_fim, ano_fim)
        count = movimentos_periodo.count()
        
        if count > 0:
            movimentos_periodo.delete()
            logger.info(f'{count} movimentos removidos do período {ano_inicio}-{mes_inicio:02d} a {ano_fim or ano_inicio}-{(mes_fim or mes_inicio):02d}')
        
        return count
    
    # PROPRIEDADES CALCULADAS
    
    @property
    def periodo_display(self):
        """Período formatado para exibição"""
        return f"{self.mes:02d}/{self.ano}"
    
    @property
    def valor_formatado(self):
        """Valor formatado em reais"""
        return f"R$ {self.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    @property
    def natureza_display(self):
        """Natureza por extenso"""
        return dict(self.NATUREZA_CHOICES).get(self.natureza, self.natureza)
    
    @property
    def tem_fornecedor(self):
        """Verifica se tem fornecedor associado"""
        return self.fornecedor is not None
    
    @property
    def descricao_resumida(self):
        """Descrição resumida para listagens"""
        return f"{self.unidade.codigo_display} | {self.centro_custo.codigo} | {self.conta_contabil.codigo} | {self.valor_formatado}"
    
    def __str__(self):
        return f"{self.data.strftime('%d/%m/%Y')} - {self.descricao_resumida}"
    
    class Meta:
        db_table = 'movimentos'
        verbose_name = 'Movimento'
        verbose_name_plural = 'Movimentos'
        ordering = ['-data', '-id']
        indexes = [
            models.Index(fields=['ano', 'mes']),
            models.Index(fields=['periodo_mes_ano']),
            models.Index(fields=['data']),  # ÍNDICE PRINCIPAL PARA BUSCA POR DATA
            models.Index(fields=['data', 'unidade']),  # ÍNDICE COMPOSTO PARA RELATÓRIOS
            models.Index(fields=['unidade']),
            models.Index(fields=['centro_custo']),
            models.Index(fields=['conta_contabil']),
            models.Index(fields=['fornecedor']),
            models.Index(fields=['natureza']),
            models.Index(fields=['valor']),
            models.Index(fields=['data_importacao']),
            models.Index(fields=['arquivo_origem']),
        ]