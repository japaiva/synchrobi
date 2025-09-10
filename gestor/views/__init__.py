# gestor/views/__init__.py

# Dashboard
from .dashboard import dashboard, home

# Empresa
from .empresa import (
    empresa_list, 
    empresa_create, 
    empresa_update, 
    empresa_delete,
    api_validar_sigla_empresa, 
    api_validar_cnpj_empresa, 
    api_empresa_info
)

# Unidade - Nova arquitetura focada na árvore
from .unidade import (
    unidade_create_modal,            # Criar via modal
    unidade_update_modal,            # Editar via modal
    unidade_detail_modal,            # Detalhes via modal
    unidade_delete_ajax,             # Excluir via AJAX
    api_unidade_tree_data,           # API básica para dados da árvore
    api_validar_codigo,              # API para validação de código
)

# Unidade Tree - View principal e APIs especializadas
from .unidade_tree import (
    unidade_tree_view,               # View principal da árvore (PRINCIPAL)
    unidade_tree_data,               # API com filtros avançados
    unidade_tree_search,             # API de busca rápida
    unidade_tree_export,             # API de export
    build_tree_structure,            # Função auxiliar (compatibilidade)
    calculate_tree_stats             # Função auxiliar (compatibilidade)
)

# Centro Custo - Nova arquitetura focada na árvore
from .centrocusto import (
    # Views modais CRUD
    centrocusto_create_modal,        # Criar via modal
    centrocusto_update_modal,        # Editar via modal
    centrocusto_delete_ajax,         # Excluir via AJAX
    
    # View principal da árvore
    centrocusto_tree_view,           # View principal da árvore (PRINCIPAL)
    
    # APIs para árvore
    api_centrocusto_tree_data,       # API com filtros avançados
    api_validar_codigo_centrocusto,  # API para validação de código
    
    # Views mantidas para compatibilidade (redirecionam)
    centrocusto_list,                # Redireciona para árvore
    centrocusto_create,              # Redireciona para modal
    centrocusto_update,              # Redireciona para modal
    centrocusto_delete,              # Redireciona para AJAX
)

# Conta Contabil - Nova arquitetura focada na árvore
from .contacontabil import (
    # Views modais CRUD
    contacontabil_create_modal,      # Criar via modal
    contacontabil_update_modal,      # Editar via modal
    contacontabil_delete_ajax,       # Excluir via AJAX
    
    # View principal da árvore
    contacontabil_tree_view,         # View principal da árvore (PRINCIPAL)
    
    # APIs para árvore
    api_contacontabil_tree_data,     # API com filtros avançados
    api_validar_codigo_contacontabil, # API para validação de código
    
    # Views mantidas para compatibilidade (redirecionam)
    contacontabil_list,              # Redireciona para árvore
    contacontabil_create,            # Redireciona para modal
    contacontabil_update,            # Redireciona para modal
    contacontabil_delete,            # Redireciona para AJAX
)

# Conta Contabil com Códigos Externos - Nova funcionalidade
from .contacontabil_external import (
    # View principal da árvore com externos
    contacontabil_tree_with_external_view,    # View principal com códigos externos
    
    # API para dados da árvore com externos
    api_contacontabil_tree_with_external_data, # API da árvore com códigos externos
    
    # CRUD para contas externas
    contaexterna_list,                        # Lista de códigos externos
    contaexterna_create,                      # Criar código externo
    # contaexterna_update,                    # Editar código externo (implementar)
    # contaexterna_delete,                    # Excluir código externo (implementar)
)

# Usuario
from .usuario import (
    usuario_list, 
    usuario_create, 
    usuario_update, 
    usuario_delete
)

# Parametro
from .parametro import (
    parametro_list, 
    parametro_create, 
    parametro_detail, 
    parametro_update, 
    parametro_delete,
    api_parametro_valor
)

# ===== VIEWS REMOVIDAS/ATUALIZADAS NA NOVA ARQUITETURA =====
# 
# UNIDADES (já migradas):
# - unidade_list → unidade_tree_view
# - unidade_create → unidade_create_modal
# - unidade_detail → unidade_detail_modal
# - unidade_update → unidade_update_modal
# - unidade_delete → unidade_delete_ajax
# - unidade_arvore → integrada em unidade_tree_view
# - api_unidade_filhas → api_unidade_tree_data
#
# CENTROS DE CUSTO (migrados):
# - centrocusto_list → centrocusto_tree_view (principal) + redirect (compatibilidade)
# - centrocusto_create → centrocusto_create_modal (principal) + redirect (compatibilidade)
# - centrocusto_update → centrocusto_update_modal (principal) + redirect (compatibilidade)
# - centrocusto_delete → centrocusto_delete_ajax (principal) + redirect (compatibilidade)
# + api_centrocusto_tree_data → nova API para dados da árvore
#
# CONTAS CONTÁBEIS (migradas):
# - contacontabil_list → contacontabil_tree_view (principal) + redirect (compatibilidade)
# - contacontabil_create → contacontabil_create_modal (principal) + redirect (compatibilidade)
# - contacontabil_update → contacontabil_update_modal (principal) + redirect (compatibilidade)
# - contacontabil_delete → contacontabil_delete_ajax (principal) + redirect (compatibilidade)
# + api_contacontabil_tree_data → nova API para dados da árvore
# + api_validar_codigo_contacontabil → nova API para validação
#
# CONTAS CONTÁBEIS COM CÓDIGOS EXTERNOS (nova funcionalidade):
# + contacontabil_tree_with_external_view → árvore principal com códigos externos
# + api_contacontabil_tree_with_external_data → API da árvore com códigos externos
# + contaexterna_list → gerenciar códigos externos
# + contaexterna_create → criar códigos externos
#
# PADRÃO DA NOVA ARQUITETURA:
# 1. View principal única (*_tree_view) para visualização hierárquica
# 2. Modais para operações CRUD (*_create_modal, *_update_modal, *_detail_modal*)
# 3. AJAX para exclusões (*_delete_ajax)
# 4. APIs modernas para dados da árvore (api_*_tree_data)
# 5. APIs de validação específicas (api_validar_codigo_*)
# 6. Views antigas mantidas para compatibilidade com redirecionamentos
# 7. Funcionalidades especializadas (*_with_external_*) para recursos avançados
#
# BENEFÍCIOS DA NOVA ARQUITETURA:
# - Interface consistente e moderna
# - Performance otimizada com renderização em lotes
# - Validação em tempo real
# - Hierarquia dinâmica baseada em código
# - Compatibilidade total com código existente
# - Manutenibilidade aprimorada
# - Suporte a códigos externos integrado