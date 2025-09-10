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

# core/models.py - Substituir a classe Unidade existente

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
        db_index=True  # ÍNDICE ADICIONADO
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
    
    # MÉTODOS DE BUSCA OTIMIZADOS
    
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
    
    @classmethod
    def buscar_multiplas_para_movimentos(cls, codigos_unidades):
        """
        Busca múltiplas unidades de forma otimizada para importação em lote
        """
        codigos_str = [str(c) for c in codigos_unidades if c]
        
        # Buscar por All Strategy e código normal em uma só query
        unidades_all_strategy = list(cls.objects.filter(
            codigo_allstrategy__in=codigos_str, 
            ativa=True
        ).values('codigo_allstrategy', 'id', 'codigo', 'nome'))
        
        unidades_codigo = list(cls.objects.filter(
            codigo__in=codigos_str, 
            ativa=True
        ).values('codigo', 'id', 'codigo_allstrategy', 'nome'))
        
        # Criar mapa para retorno rápido
        mapa_unidades = {}
        
        # Priorizar busca por All Strategy
        for unidade in unidades_all_strategy:
            if unidade['codigo_allstrategy']:
                mapa_unidades[unidade['codigo_allstrategy']] = unidade
        
        # Complementar com busca por código normal
        for unidade in unidades_codigo:
            if unidade['codigo'] not in mapa_unidades:
                mapa_unidades[unidade['codigo']] = unidade
        
        return mapa_unidades
    
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
    
    @property
    def codigo_busca_display(self):
        """Mostra ambos códigos quando relevante"""
        if self.codigo_allstrategy and self.codigo_allstrategy != self.codigo:
            return f"{self.codigo} (AS: {self.codigo_allstrategy})"
        return self.codigo
    
    def __str__(self):
        tipo_icon = "📂" if self.e_sintetico else "🏢"
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

# Adicionar ao final do arquivo core/models.py

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
        help_text="Código da conta no sistema externo (ERP)"
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
            models.Index(fields=['codigo_externo']),
            models.Index(fields=['sistema_origem']),
            models.Index(fields=['ativa']),
            models.Index(fields=['sincronizado']),
        ]

# core/models.py - Adicionar ao final do arquivo

class Fornecedor(models.Model):
    """Cadastro de fornecedores com dados simplificados"""
    
    codigo = models.CharField(max_length=20, primary_key=True, verbose_name="Código")
    razao_social = models.CharField(max_length=255, verbose_name="Razão Social")
    nome_fantasia = models.CharField(max_length=255, blank=True, verbose_name="Nome Fantasia")
    cnpj_cpf = models.CharField(max_length=18, blank=True, verbose_name="CNPJ/CPF")
    
    # Dados de contato
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    email = models.EmailField(blank=True, verbose_name="E-mail")
    endereco = models.TextField(blank=True, verbose_name="Endereço")
    
    # Dados bancários removidos conforme solicitação
    
    # Controle
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_automaticamente = models.BooleanField(default=False, verbose_name="Criado Automaticamente")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    # Campos para rastreamento da origem
    origem_historico = models.TextField(
        blank=True, 
        verbose_name="Histórico de Origem",
        help_text="Histórico original de onde foi extraído"
    )
    
    def clean(self):
        """Validação customizada"""
        super().clean()
        
        # Limpar razão social
        if self.razao_social:
            self.razao_social = self.razao_social.strip().upper()
        
        # Validar CNPJ/CPF se fornecido
        if self.cnpj_cpf:
            import re
            cnpj_cpf_limpo = re.sub(r'[^\d]', '', self.cnpj_cpf)
            if len(cnpj_cpf_limpo) not in [11, 14]:
                raise ValidationError({
                    'cnpj_cpf': 'CNPJ deve ter 14 dígitos ou CPF deve ter 11 dígitos'
                })
    
    @property
    def nome_display(self):
        """Nome para exibição (nome fantasia se houver, senão razão social)"""
        return self.nome_fantasia or self.razao_social
    
    @property
    def cnpj_cpf_formatado(self):
        """CNPJ/CPF formatado"""
        if not self.cnpj_cpf:
            return ''
        
        import re
        numeros = re.sub(r'[^\d]', '', self.cnpj_cpf)
        
        if len(numeros) == 14:  # CNPJ
            return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:14]}"
        elif len(numeros) == 11:  # CPF
            return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:11]}"
        else:
            return self.cnpj_cpf
    
    @property
    def tipo_pessoa(self):
        """Retorna se é PF ou PJ baseado no CNPJ/CPF"""
        if not self.cnpj_cpf:
            return 'Não informado'
        
        import re
        numeros = re.sub(r'[^\d]', '', self.cnpj_cpf)
        
        if len(numeros) == 14:
            return 'Pessoa Jurídica'
        elif len(numeros) == 11:
            return 'Pessoa Física'
        else:
            return 'Inválido'
    
    @classmethod
    def extrair_do_historico(cls, historico, salvar=True):
        """
        Extrai fornecedor do histórico no padrão: "- 123456 NOME DO FORNECEDOR -"
        """
        import re
        
        # Padrão para capturar código e nome do fornecedor
        match = re.search(r'- (\d+)\s+([A-Z\s&\.\-_]+?) -', historico)
        
        if not match:
            return None
        
        codigo, nome = match.groups()
        codigo = codigo.strip()
        nome = nome.strip()
        
        if len(nome) < 3:  # Nome muito curto, provavelmente inválido
            return None
        
        # Verificar se já existe
        try:
            fornecedor = cls.objects.get(codigo=codigo)
            logger.info(f'Fornecedor existente encontrado: {codigo} - {nome}')
            return fornecedor
        except cls.DoesNotExist:
            pass
        
        # Criar novo fornecedor se não existe
        if salvar:
            try:
                fornecedor = cls.objects.create(
                    codigo=codigo,
                    razao_social=nome,
                    criado_automaticamente=True,
                    origem_historico=historico[:500]  # Limitar tamanho
                )
                logger.info(f'Novo fornecedor criado automaticamente: {codigo} - {nome}')
                return fornecedor
            except Exception as e:
                logger.error(f'Erro ao criar fornecedor {codigo}: {str(e)}')
                return None
        else:
            # Retornar instância não salva para preview
            return cls(
                codigo=codigo,
                razao_social=nome,
                criado_automaticamente=True,
                origem_historico=historico[:500]
            )
    
    def __str__(self):
        return f"{self.codigo} - {self.nome_display}"
    
    class Meta:
        db_table = 'fornecedores'
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['razao_social']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['razao_social']),
            models.Index(fields=['ativo']),
            models.Index(fields=['criado_automaticamente']),
        ]

# core/models.py - Adicionar ao final do arquivo

class Movimento(models.Model):
    """
    Movimentação financeira/contábil com relacionamentos para unidade, centro de custo, 
    conta contábil e fornecedor
    """
    
    NATUREZA_CHOICES = [
        ('D', 'Débito'),
        ('C', 'Crédito'),
        ('A', 'Ambas'),
    ]
    
    # Campos temporais
    mes = models.IntegerField(verbose_name="Mês")
    ano = models.IntegerField(verbose_name="Ano")
    data = models.DateField(verbose_name="Data do Movimento")
    
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
        """Validação customizada - VERSÃO CORRIGIDA"""
        super().clean()
        
        # Validar apenas se os valores existem (evita erro NoneType)
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
        """Save com cálculos automáticos - VERSÃO CORRIGIDA"""
        
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
    
    # MÉTODOS DE CONSULTA E ANÁLISE
    
    @classmethod
    def get_movimentos_periodo(cls, mes_inicio, ano_inicio, mes_fim=None, ano_fim=None):
        """
        Busca movimentos por período
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
        Remove movimentos de um período antes de nova importação
        """
        movimentos_periodo = cls.get_movimentos_periodo(mes_inicio, ano_inicio, mes_fim, ano_fim)
        count = movimentos_periodo.count()
        
        if count > 0:
            movimentos_periodo.delete()
            logger.info(f'{count} movimentos removidos do período {ano_inicio}-{mes_inicio:02d} a {ano_fim or ano_inicio}-{(mes_fim or mes_inicio):02d}')
        
        return count
    
    @classmethod
    def processar_linha_excel(cls, linha_dados, numero_linha, nome_arquivo):
        """
        Processa uma linha do Excel e cria o movimento
        """
        try:
            # Extrair dados da linha
            mes = int(linha_dados.get('Mês', 0))
            ano = int(linha_dados.get('Ano', 0))
            data = linha_dados.get('Data')
            codigo_unidade = linha_dados.get('Cód. da unidade')
            codigo_centro_custo = linha_dados.get('Cód. do centro de custo')
            codigo_conta_contabil = linha_dados.get('Cód. da conta contábil')
            documento = linha_dados.get('Documento', '')
            natureza = linha_dados.get('Natureza (D/C/A)', 'D')
            valor = linha_dados.get('Valor', 0)
            historico = linha_dados.get('Histórico', '')
            codigo_projeto = linha_dados.get('Cód. do projeto', '')
            gerador = linha_dados.get('Gerador', '')
            rateio = linha_dados.get('Rateio', 'N')
            
            # Buscar unidade
            unidade = Unidade.buscar_unidade_para_movimento(codigo_unidade)
            if not unidade:
                raise ValueError(f'Unidade não encontrada para código: {codigo_unidade}')
            
            # Buscar centro de custo
            try:
                centro_custo = CentroCusto.objects.get(codigo=codigo_centro_custo, ativo=True)
            except CentroCusto.DoesNotExist:
                raise ValueError(f'Centro de custo não encontrado: {codigo_centro_custo}')
            
            # Buscar conta contábil via código externo
            try:
                conta_externa = ContaExterna.objects.get(codigo_externo=str(codigo_conta_contabil), ativa=True)
                conta_contabil = conta_externa.conta_contabil
            except ContaExterna.DoesNotExist:
                raise ValueError(f'Conta contábil não encontrada para código externo: {codigo_conta_contabil}')
            
            # Extrair fornecedor do histórico
            fornecedor = None
            if historico:
                fornecedor = Fornecedor.extrair_do_historico(historico, salvar=True)
            
            # Converter data se necessário
            if isinstance(data, str):
                from datetime import datetime
                data = datetime.strptime(data, '%Y-%m-%d').date()
            elif hasattr(data, 'date'):
                data = data.date()
            
            # Criar movimento
            movimento = cls.objects.create(
                mes=mes,
                ano=ano,
                data=data,
                unidade=unidade,
                centro_custo=centro_custo,
                conta_contabil=conta_contabil,
                fornecedor=fornecedor,
                documento=str(documento) if documento else '',
                natureza=natureza,
                valor=float(valor) if valor else 0,
                historico=historico,
                codigo_projeto=str(codigo_projeto) if codigo_projeto else '',
                gerador=str(gerador) if gerador else '',
                rateio=str(rateio) if rateio else 'N',
                arquivo_origem=nome_arquivo,
                linha_origem=numero_linha
            )
            
            return movimento, None  # movimento, erro
            
        except Exception as e:
            error_msg = f'Linha {numero_linha}: {str(e)}'
            logger.error(f'Erro ao processar movimento: {error_msg}')
            return None, error_msg
    
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
        return f"{self.periodo_display} - {self.descricao_resumida}"
    
    class Meta:
        db_table = 'movimentos'
        verbose_name = 'Movimento'
        verbose_name_plural = 'Movimentos'
        ordering = ['-ano', '-mes', '-data', 'id']
        indexes = [
            models.Index(fields=['ano', 'mes']),
            models.Index(fields=['periodo_mes_ano']),
            models.Index(fields=['data']),
            models.Index(fields=['unidade']),
            models.Index(fields=['centro_custo']),
            models.Index(fields=['conta_contabil']),
            models.Index(fields=['fornecedor']),
            models.Index(fields=['natureza']),
            models.Index(fields=['valor']),
            models.Index(fields=['ano', 'mes', 'unidade']),  # Índice composto para relatórios
            models.Index(fields=['data_importacao']),
        ]