# core/models/relacionamentos.py - MODELOS AUXILIARES E RELACIONAMENTOS

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from .usuario import Usuario
from .empresa import Empresa
from .hierarquicos import CentroCusto, ContaContabil

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

class UsuarioCentroCusto(models.Model):
    """Relacionamento de usuários com centros de custo permitidos"""
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='centros_custo_permitidos')
    centro_custo = models.ForeignKey(CentroCusto, on_delete=models.CASCADE, related_name='usuarios_com_acesso')
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'usuario_centros_custo'
        unique_together = ['usuario', 'centro_custo']
        verbose_name = 'Permissão Centro de Custo'
        verbose_name_plural = 'Permissões Centros de Custo'

class EmpresaCentroCusto(models.Model):
    """Relacionamento entre empresas e centros de custo"""
    
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
        
        if hasattr(self, 'data_fim') and self.data_fim and hoje > self.data_fim:
            return "Vencido"
        elif hasattr(self, 'data_inicio') and self.data_inicio > hoje:
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

class ContaExterna(models.Model):
    """
    Modelo para mapear códigos de contas externas (ERPs) às contas contábeis internas
    """
    
    # Relacionamento com conta contábil interna
    conta_contabil = models.ForeignKey(
        ContaContabil,
        on_delete=models.CASCADE,
        related_name='contas_externas',
        verbose_name="Conta Contábil Interna"
    )
    
    # Dados da conta externa
    codigo_externo = models.CharField(
        max_length=50,
        verbose_name="Código Externo",
        help_text="Código da conta no sistema externo (ERP)",
        db_index=True  # ÍNDICE PARA BUSCA RÁPIDA
    )
    
    nome_externo = models.CharField(
        max_length=255,
        verbose_name="Nome no Sistema Externo",
        help_text="Nome/descrição da conta no sistema externo"
    )
    
    # Sistema/empresa origem
    sistema_origem = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Sistema de Origem",
        help_text="Nome do ERP/sistema de origem (ex: Consinco, Protheus)"
    )
    
    empresas_utilizacao = models.TextField(
        blank=True,
        verbose_name="Empresas de Utilização",
        help_text="Empresas que utilizam esta conta (ex: CMC & EBC & Taiff & Action Motors)"
    )
    
    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações",
        help_text="Observações sobre a conta externa"
    )
    
    # Campos de controle
    ativa = models.BooleanField(
        default=True,
        verbose_name="Ativa",
        help_text="Se a conta externa está ativa"
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    # Campos para sincronização
    sincronizado = models.BooleanField(
        default=False,
        verbose_name="Sincronizado",
        help_text="Se a conta foi sincronizada com o sistema externo"
    )
    
    data_ultima_sincronizacao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última Sincronização"
    )
    
    def clean(self):
        """Validação customizada"""
        super().clean()
        
        # Verificar se não há duplicação do código externo para a mesma conta interna
        duplicatas = ContaExterna.objects.filter(
            conta_contabil=self.conta_contabil,
            codigo_externo=self.codigo_externo,
            ativa=True
        )
        
        if self.pk:
            duplicatas = duplicatas.exclude(pk=self.pk)
        
        if duplicatas.exists():
            raise ValidationError({
                'codigo_externo': f'Já existe uma conta externa ativa com este código para a conta {self.conta_contabil.codigo}'
            })
    
    @property
    def codigo_display(self):
        """Código para exibição"""
        return f"{self.codigo_externo} ({self.sistema_origem})" if self.sistema_origem else self.codigo_externo
    
    @property
    def empresas_lista(self):
        """Retorna lista de empresas que utilizam esta conta"""
        if not self.empresas_utilizacao:
            return []
        
        # Dividir por & e limpar espaços
        empresas = [emp.strip() for emp in self.empresas_utilizacao.split('&')]
        return [emp for emp in empresas if emp]
    
    def sincronizar_dados(self):
        """Sincroniza dados com o sistema externo"""
        # Implementar lógica de sincronização
        self.sincronizado = True
        self.data_ultima_sincronizacao = timezone.now()
        self.save()
    
    def __str__(self):
        sistema = f" ({self.sistema_origem})" if self.sistema_origem else ""
        return f"{self.codigo_externo}{sistema} → {self.conta_contabil.codigo}"
    
    class Meta:
        db_table = 'contas_externas'
        verbose_name = 'Conta Externa'
        verbose_name_plural = 'Contas Externas'
        ordering = ['conta_contabil__codigo', 'codigo_externo']
        unique_together = ['conta_contabil', 'codigo_externo', 'ativa']  # Evita duplicatas ativas
        indexes = [
            models.Index(fields=['conta_contabil']),
            models.Index(fields=['codigo_externo']),  # ÍNDICE PRINCIPAL PARA BUSCA
            models.Index(fields=['sistema_origem']),
            models.Index(fields=['ativa']),
            models.Index(fields=['sincronizado']),
            models.Index(fields=['codigo_externo', 'ativa']),  # ÍNDICE COMPOSTO
        ]