# core/models.py - Modelos base do SynchroBI

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

# ===== MODELOS DE ESTRUTURA ORGANIZACIONAL =====

class Empresa(models.Model):
    """Dados da empresa para cabeçalhos de relatórios"""
    codigo = models.CharField(max_length=10, primary_key=True)
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True)
    cnpj = models.CharField(max_length=18, unique=True)
    inscricao_estadual = models.CharField(max_length=30, blank=True)
    endereco = models.TextField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True)
    ativa = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nome_fantasia or self.razao_social
    
    class Meta:
        db_table = 'empresas'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

class Unidade(models.Model):
    """
    Modelo para estrutura organizacional hierárquica da empresa
    Baseado no All Strategy com códigos estruturados
    """
    
    TIPO_CHOICES = [
        ('S', 'Sintético'),  # Agrupador/Consolidador
        ('A', 'Analítico'),  # Unidade operacional
    ]
    
    # ===== CAMPOS PRINCIPAIS =====
    codigo_allstrategy = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Código All Strategy",
        help_text="Código estruturado do All Strategy (ex: 1.2.01.20.01.101)"
    )
    
    codigo_interno = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Código Interno",
        help_text="Código simplificado para uso interno (ex: 101)"
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
    
    # ===== TIPO E STATUS =====
    tipo = models.CharField(
        max_length=1,
        choices=TIPO_CHOICES,
        verbose_name="Tipo",
        help_text="S=Sintético (agrupador), A=Analítico (operacional)"
    )
    
    ativa = models.BooleanField(
        default=True,
        verbose_name="Ativa"
    )
    
    # ===== CAMPOS COMPLEMENTARES =====
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )
    
    responsavel = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Responsável"
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
        
        # Validar formato do código All Strategy
        if not re.match(r'^[\d\.]+$', self.codigo_allstrategy):
            raise ValidationError({
                'codigo_allstrategy': 'Código deve conter apenas números e pontos'
            })
        
        # Para unidades analíticas, extrair código interno automaticamente
        if self.tipo == 'A' and not self.codigo_interno:
            # Extrair último segmento numérico do código
            partes = self.codigo_allstrategy.split('.')
            ultimo_segmento = partes[-1]
            if ultimo_segmento.isdigit():
                self.codigo_interno = ultimo_segmento
    
    def save(self, *args, **kwargs):
        """Override do save para calcular nível automaticamente"""
        
        # Calcular nível baseado no número de pontos
        self.nivel = self.codigo_allstrategy.count('.') + 1
        
        # Buscar unidade pai baseada no código
        if '.' in self.codigo_allstrategy:
            # Código do pai é tudo menos o último segmento
            partes = self.codigo_allstrategy.split('.')
            codigo_pai = '.'.join(partes[:-1])
            
            try:
                self.unidade_pai = Unidade.objects.get(codigo_allstrategy=codigo_pai)
            except Unidade.DoesNotExist:
                # Se pai não existe, manter None
                pass
        
        # Validar antes de salvar
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
        for key in cache_keys:
            cache.delete(key)
    
    @property
    def codigo_display(self):
        """Código para exibição (interno se analítico, All Strategy se sintético)"""
        if self.tipo == 'A' and self.codigo_interno:
            return self.codigo_interno
        return self.codigo_allstrategy
    
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
    
    def get_todas_sub_unidades(self, include_self=False):
        """Retorna todas as sub-unidades recursivamente"""
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
        return [u for u in todas if u.tipo == 'A']
    
    def is_pai_de(self, unidade):
        """Verifica se esta unidade é pai (direto ou indireto) de outra"""
        unidade_atual = unidade.unidade_pai
        while unidade_atual:
            if unidade_atual == self:
                return True
            unidade_atual = unidade_atual.unidade_pai
        return False
    
    def get_nivel_display(self):
        """Retorna representação visual do nível"""
        return "  " * (self.nivel - 1) + "├─ " if self.nivel > 1 else ""
    
    @classmethod
    def get_arvore_completa(cls):
        """Retorna toda a árvore de unidades organizadas"""
        cache_key = 'unidades_ativas_tree'
        arvore = cache.get(cache_key)
        
        if arvore is None:
            # Buscar todas as unidades ativas ordenadas por código
            unidades = cls.objects.filter(ativa=True).order_by('codigo_allstrategy')
            arvore = list(unidades)
            cache.set(cache_key, arvore, 600)  # Cache por 10 minutos
        
        return arvore
    
    @classmethod
    def importar_do_allstrategy(cls, dados_excel):
        """
        Método para importar unidades de um Excel do All Strategy
        """
        unidades_criadas = 0
        unidades_atualizadas = 0
        erros = []
        
        # Ordenar por código para garantir que pais sejam criados antes dos filhos
        dados_ordenados = sorted(dados_excel, key=lambda x: x.get('Estrutura\r\nAllStrategy', ''))
        
        for linha in dados_ordenados:
            try:
                codigo = linha.get('Estrutura\r\nAllStrategy', '').strip()
                nome = linha.get('Nome da unidade', '').strip()
                tipo = linha.get('Sintético /\r\nAnalítico', '').strip().upper()
                
                if not codigo or not nome:
                    continue
                
                # Tentar encontrar unidade existente
                unidade, criada = cls.objects.get_or_create(
                    codigo_allstrategy=codigo,
                    defaults={
                        'nome': nome,
                        'tipo': tipo,
                        'ativa': True,
                        'sincronizado_allstrategy': True
                    }
                )
                
                if criada:
                    unidades_criadas += 1
                else:
                    # Atualizar dados existentes
                    unidade.nome = nome
                    unidade.tipo = tipo
                    unidade.sincronizado_allstrategy = True
                    unidade.save()
                    unidades_atualizadas += 1
                    
            except Exception as e:
                erros.append(f"Linha {linha}: {str(e)}")
        
        return {
            'criadas': unidades_criadas,
            'atualizadas': unidades_atualizadas,
            'erros': erros
        }
    
    def __str__(self):
        tipo_icon = "📁" if self.tipo == 'S' else "🏢"
        return f"{tipo_icon} {self.codigo_display} - {self.nome}"
    
    class Meta:
        db_table = 'unidades'
        verbose_name = 'Unidade Organizacional'
        verbose_name_plural = 'Unidades Organizacionais'
        ordering = ['codigo_allstrategy']
        indexes = [
            models.Index(fields=['codigo_allstrategy']),
            models.Index(fields=['codigo_interno']),
            models.Index(fields=['tipo', 'ativa']),
            models.Index(fields=['unidade_pai', 'ativa']),
            models.Index(fields=['nivel']),
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