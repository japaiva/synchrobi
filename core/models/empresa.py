# core/models/empresa.py - MODELO DE EMPRESA CORRIGIDO

import logging
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger('synchrobi')

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
        """Override do save com formatações automáticas"""
        
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
    
    # REMOVIDO: Métodos relacionados a empresa_centros_custo que não existe mais
    # def get_centros_custo_ativos(self):
    # def get_centros_custo_vigentes(self):
    # def get_responsaveis_centros_custo(self):
    # @property def total_centros_custo(self):
    
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