# core/models/grupo_fornecedor.py - MODELO DE GRUPO DE FORNECEDORES

import logging
from django.db import models
from django.core.exceptions import ValidationError

logger = logging.getLogger('synchrobi')

class GrupoFornecedor(models.Model):
    """Grupo para consolidar múltiplos fornecedores em relatórios"""

    codigo = models.CharField(
        max_length=20,
        primary_key=True,
        verbose_name="Código"
    )
    nome = models.CharField(
        max_length=255,
        verbose_name="Nome do Grupo",
        db_index=True
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição",
        help_text="Descrição do grupo de fornecedores"
    )

    # Controle
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validação customizada"""
        super().clean()

        # Limpar e padronizar nome
        if self.nome:
            self.nome = self.nome.strip().upper()

        # Limpar e padronizar código
        if self.codigo:
            self.codigo = self.codigo.strip().upper()

    @property
    def total_fornecedores(self):
        """Retorna quantidade de fornecedores no grupo"""
        return self.fornecedores.count()

    @property
    def total_fornecedores_ativos(self):
        """Retorna quantidade de fornecedores ativos no grupo"""
        return self.fornecedores.filter(ativo=True).count()

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    class Meta:
        db_table = 'grupos_fornecedores'
        verbose_name = 'Grupo de Fornecedor'
        verbose_name_plural = 'Grupos de Fornecedores'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['nome']),
            models.Index(fields=['ativo']),
        ]
