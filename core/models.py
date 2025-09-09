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

# ===== MIXIN PARA HIERARQUIA DINÂMICA COMPLETO =====

class HierarquiaDinamicaMixin:
    """Mixin para hierarquia baseada apenas no código, OTIMIZADO E COMPLETO"""
    
    @property
    def pai(self):
        """Retorna o pai baseado no código, com cache"""
        if not hasattr(self, '_cached_pai'):
            self._cached_pai = self.encontrar_pai_hierarquico()
        return self._cached_pai
    
    def encontrar_pai_hierarquico(self):
        """Encontra o pai baseado no código hierárquico"""
        if not self.codigo or '.' not in self.codigo:
            return None
        
        # Buscar pai pelos códigos hierárquicos possíveis
        partes = self.codigo.split('.')
        
        # Tentar encontrar pai de forma hierárquica
        for i in range(len(partes) - 1, 0, -1):
            codigo_pai_candidato = '.'.join(partes[:i])
            try:
                pai = self.__class__.objects.get(codigo=codigo_pai_candidato)
                return pai
            except self.__class__.DoesNotExist:
                continue
        
        return None
    
    def get_filhos_diretos(self):
        """Retorna apenas filhos diretos (OTIMIZADO)"""
        if not self.pk:
            return self.__class__.objects.none()
        
        active_field = 'ativo' if hasattr(self, 'ativo') else 'ativa'
        
        # OTIMIZAÇÃO: Filtrar diretamente no banco por nível
        codigo_base = self.codigo + '.'
        nivel_filho = self.nivel + 1
        
        return self.__class__.objects.filter(
            codigo__startswith=codigo_base,
            nivel=nivel_filho,  # ← Filtro direto no banco
            **{active_field: True}
        ).order_by('codigo')
    
    @property
    def tem_filhos(self):
        """Verifica se tem filhos diretos"""
        return self.get_filhos_diretos().exists()
    
    def get_todos_filhos_recursivo(self, include_self=False):
        """Retorna todos os filhos recursivamente"""
        active_field = 'ativo' if hasattr(self, 'ativo') else 'ativa'
        
        if include_self:
            # Buscar todos com código que começa com o código atual
            queryset = self.__class__.objects.filter(
                codigo__startswith=self.codigo,
                **{active_field: True}
            ).order_by('codigo')
        else:
            # Buscar todos com código que começa com o código atual + ponto
            codigo_base = self.codigo + '.'
            queryset = self.__class__.objects.filter(
                codigo__startswith=codigo_base,
                **{active_field: True}
            ).order_by('codigo')
        
        return list(queryset)
    
    def get_caminho_hierarquico(self):
        """Retorna lista com o caminho hierárquico da raiz até este item"""
        caminho = []
        item_atual = self
        
        # Construir caminho de baixo para cima
        while item_atual:
            caminho.insert(0, item_atual)
            item_atual = item_atual.pai
        
        return caminho
    
    def get_raiz(self):
        """Retorna o item raiz da hierarquia"""
        caminho = self.get_caminho_hierarquico()
        return caminho[0] if caminho else self
    
    def get_descendentes_por_nivel(self, nivel_max=None):
        """Retorna descendentes agrupados por nível"""
        todos_filhos = self.get_todos_filhos_recursivo(include_self=False)
        
        if nivel_max:
            todos_filhos = [f for f in todos_filhos if f.nivel <= nivel_max]
        
        # Agrupar por nível
        por_nivel = {}
        for filho in todos_filhos:
            nivel = filho.nivel
            if nivel not in por_nivel:
                por_nivel[nivel] = []
            por_nivel[nivel].append(filho)
        
        return por_nivel
    
    @classmethod
    def build_hierarchy_map(cls, queryset=None):
        """Constrói mapa da hierarquia em uma única query (OTIMIZADO)"""
        if queryset is None:
            active_field = 'ativo' if hasattr(cls(), 'ativo') else 'ativa'
            queryset = cls.objects.filter(**{active_field: True})
        
        # Buscar todos os itens de uma vez
        items = list(queryset.select_related().order_by('codigo'))
        
        # Criar mapa de relacionamentos
        hierarchy_map = {}
        root_items = []
        
        for item in items:
            hierarchy_map[item.codigo] = {
                'item': item,
                'children': []
            }
        
        # Estabelecer relacionamentos pai-filho
        for item in items:
            if '.' in item.codigo:
                # Encontrar pai
                partes = item.codigo.split('.')
                for i in range(len(partes) - 1, 0, -1):
                    codigo_pai_candidato = '.'.join(partes[:i])
                    if codigo_pai_candidato in hierarchy_map:
                        hierarchy_map[codigo_pai_candidato]['children'].append(item)
                        break
            else:
                root_items.append(item)
        
        return hierarchy_map, root_items
    
    @classmethod
    def get_hierarchy_tree(cls, queryset=None):
        """Retorna estrutura de árvore hierárquica"""
        hierarchy_map, root_items = cls.build_hierarchy_map(queryset)
        
        def build_tree_node(item):
            children_data = hierarchy_map.get(item.codigo, {}).get('children', [])
            return {
                'item': item,
                'children': [build_tree_node(child) for child in sorted(children_data, key=lambda x: x.codigo)]
            }
        
        return [build_tree_node(root) for root in sorted(root_items, key=lambda x: x.codigo)]
    
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

# core/models.py - Apenas as partes do CentroCusto e ContaContabil que precisam ser alteradas

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
    
    # Métodos de validação de regras de negócio
    def pode_ter_filhos(self):
        """Apenas centros sintéticos podem ter filhos"""
        return self.tipo == 'S'
    
    def pode_alterar_tipo_para_analitico(self):
        """Verifica se pode alterar para analítico"""
        return not self.tem_filhos
    
    def pode_alterar_tipo_para_sintetico(self):
        """Sempre pode alterar para sintético"""
        return True
    
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
    
    # Métodos de validação de regras de negócio
    def pode_ter_filhos(self):
        """Apenas contas sintéticas podem ter filhos"""
        return self.tipo == 'S'
    
    def pode_alterar_tipo_para_analitico(self):
        """Verifica se pode alterar para analítico"""
        return not self.tem_filhos
    
    def pode_alterar_tipo_para_sintetico(self):
        """Sempre pode alterar para sintético"""
        return True
    
    def pode_receber_lancamento(self):
        """Verifica se pode receber lançamentos"""
        return self.e_analitico and not self.tem_filhos
    
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