# core/models/base.py - MIXINS E CLASSES BASE

import logging
from django.db import models
from django.core.cache import cache
from django.core.exceptions import ValidationError

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