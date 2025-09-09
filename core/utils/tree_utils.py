# core/utils/tree_utils.py - Utilitários genéricos para árvores hierárquicas

from django.db.models import Q
from django.http import JsonResponse
import json

class TreeViewMixin:
    """
    Mixin genérico para criar visualizações hierárquicas
    Pode ser usado em qualquer modelo que tenha estrutura hierárquica
    """
    
    # Configurações que devem ser definidas na view filha
    model = None                    # Modelo Django
    codigo_field = 'codigo'         # Campo que contém o código hierárquico
    nome_field = 'nome'            # Campo que contém o nome/descrição
    parent_field = None            # Campo que aponta para o pai (ex: 'conta_pai')
    active_field = 'ativa'         # Campo que indica se o registro está ativo
    tipo_field = 'tipo'            # Campo que indica o tipo (se houver)
    descricao_field = 'descricao'  # Campo de descrição (opcional)
    template_name = None           # Template a ser usado
    
    def get_tree_queryset(self):
        """Retorna queryset base para a árvore"""
        queryset = self.model.objects.all()
        
        # Filtrar apenas ativos se o campo existir
        if hasattr(self.model, self.active_field):
            filter_dict = {self.active_field: True}
            queryset = queryset.filter(**filter_dict)
        
        return queryset.order_by(self.codigo_field)
    
    def build_tree_structure(self, queryset=None):
        """Constrói a estrutura hierárquica genérica"""
        if queryset is None:
            queryset = self.get_tree_queryset()
        
        # Converter para dicionário
        items_dict = {}
        for item in queryset:
            codigo = getattr(item, self.codigo_field)
            nome = getattr(item, self.nome_field)
            
            item_data = {
                'id': item.pk, 
                'codigo': codigo,
                'nome': nome,
                'nivel': self.calculate_level(codigo),
                'filhos': []
            }
            
            # Adicionar campos opcionais se existirem
            if hasattr(item, self.tipo_field) and getattr(item, self.tipo_field):
                item_data['tipo'] = getattr(item, self.tipo_field)
            
            if hasattr(item, self.descricao_field):
                item_data['descricao'] = getattr(item, self.descricao_field) or ''
            
            if hasattr(item, self.active_field):
                item_data['ativo'] = getattr(item, self.active_field)
            
            items_dict[codigo] = item_data
        
        # Organizar hierarquia
        root_nodes = []
        
        for codigo, item_data in items_dict.items():
            if self.is_root_node(codigo):
                root_nodes.append(item_data)
            else:
                parent_codigo = self.get_parent_codigo(codigo)
                if parent_codigo in items_dict:
                    items_dict[parent_codigo]['filhos'].append(item_data)
        
        # Ordenar recursivamente
        self.sort_tree_recursive(root_nodes)
        return root_nodes
    
    def calculate_level(self, codigo):
        """Calcula o nível hierárquico baseado no código"""
        return codigo.count('.') + 1
    
    def is_root_node(self, codigo):
        """Verifica se é um nó raiz (nível 1)"""
        return '.' not in codigo
    
    def get_parent_codigo(self, codigo):
        """Retorna o código do pai baseado no código filho"""
        if '.' not in codigo:
            return None
        partes = codigo.split('.')
        return '.'.join(partes[:-1])
    
    def sort_tree_recursive(self, nodes):
        """Ordena a árvore recursivamente"""
        nodes.sort(key=lambda x: x['codigo'])
        for node in nodes:
            if node['filhos']:
                self.sort_tree_recursive(node['filhos'])
    
    def calculate_tree_stats(self, queryset=None):
        """Calcula estatísticas da árvore"""
        if queryset is None:
            queryset = self.get_tree_queryset()
        
        total = queryset.count()
        
        stats = {
            'total': total,
            'nivel_max': 0,
            'contas_por_nivel': {}
        }
        
        # Calcular níveis
        if total > 0:
            codigos = queryset.values_list(self.codigo_field, flat=True)
            niveis = [self.calculate_level(codigo) for codigo in codigos]
            stats['nivel_max'] = max(niveis) if niveis else 0
            
            # Contar por nível
            for nivel in range(1, stats['nivel_max'] + 1):
                count = sum(1 for n in niveis if n == nivel)
                stats['contas_por_nivel'][nivel] = count
        
        # Estatísticas por tipo (se aplicável)
        if hasattr(self.model, self.tipo_field):
            try:
                tipos = queryset.values_list(self.tipo_field, flat=True).distinct()
                for tipo in tipos:
                    if tipo:
                        stats[f'tipo_{tipo.lower()}'] = queryset.filter(**{self.tipo_field: tipo}).count()
            except:
                pass
        
        return stats
    
    def apply_filters(self, queryset, search=None, nivel=None, tipo=None):
        """Aplica filtros genéricos ao queryset"""
        if search:
            # Buscar em código e nome
            q_objects = Q(**{f'{self.codigo_field}__icontains': search})
            q_objects |= Q(**{f'{self.nome_field}__icontains': search})
            
            # Buscar em descrição se existir
            if hasattr(self.model, self.descricao_field):
                q_objects |= Q(**{f'{self.descricao_field}__icontains': search})
            
            queryset = queryset.filter(q_objects)
        
        if nivel:
            # Filtrar por nível (calculado dinamicamente)
            codigos_nivel = []
            for item in queryset:
                codigo = getattr(item, self.codigo_field)
                if self.calculate_level(codigo) == int(nivel):
                    codigos_nivel.append(codigo)
            
            queryset = queryset.filter(**{f'{self.codigo_field}__in': codigos_nivel})
        
        if tipo and hasattr(self.model, self.tipo_field):
            queryset = queryset.filter(**{self.tipo_field: tipo})
        
        return queryset

