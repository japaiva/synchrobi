# core/models/grupocc.py - MODELO DE GRUPO CC

import logging
from django.db import models
from django.core.exceptions import ValidationError

logger = logging.getLogger('synchrobi')

class GrupoCC(models.Model):
    """Modelo para cadastro de Grupos de Centro de Custo"""

    codigo = models.CharField(max_length=10, primary_key=True, verbose_name="Código")
    descricao = models.CharField(max_length=30, verbose_name="Descrição")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validação customizada"""
        super().clean()

        # Validar código
        if not self.codigo or not self.codigo.strip():
            raise ValidationError({
                'codigo': 'Código é obrigatório'
            })

        # Validar descrição
        if not self.descricao or not self.descricao.strip():
            raise ValidationError({
                'descricao': 'Descrição é obrigatória'
            })

    def save(self, *args, **kwargs):
        """Override do save com validação"""

        # Limpar espaços
        if self.codigo:
            self.codigo = self.codigo.strip()
        if self.descricao:
            self.descricao = self.descricao.strip()

        # Validar antes de salvar
        self.full_clean()

        super().save(*args, **kwargs)

        # Log da operação
        logger.info(f'Grupo CC {"atualizado" if self.pk else "criado"}: {self.codigo} - {self.descricao}')

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"

    class Meta:
        db_table = 'grupos_cc'
        verbose_name = 'Grupo CC'
        verbose_name_plural = 'Grupos CC'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['ativa']),
        ]
