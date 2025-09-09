# gestor/views/__init__.py

# Dashboard
from .dashboard import dashboard, home

# Empresa Centro Custo
from .empresa_centro_custo import (
    empresa_centro_custo_list, 
    empresa_centro_custo_create, 
    empresa_centro_custo_update, 
    empresa_centro_custo_delete,
    api_empresa_centros_custo, 
    api_centro_custo_empresas
)

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

# Centro Custo
from .centrocusto import (
    centrocusto_list, 
    centrocusto_create, 
    centrocusto_update, 
    centrocusto_delete,
    api_validar_codigo_centrocusto
)

# Conta Contabil
from .contacontabil import (
    contacontabil_list, 
    contacontabil_create, 
    contacontabil_update, 
    contacontabil_delete,
    api_validar_codigo_contacontabil
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

# ===== VIEWS REMOVIDAS DA ARQUITETURA ANTIGA =====
# 
# As seguintes views foram removidas da arquitetura de unidades:
# - unidade_list (substituída por unidade_tree_view)
# - unidade_create (substituída por unidade_create_modal)
# - unidade_detail (substituída por unidade_detail_modal)
# - unidade_update (substituída por unidade_update_modal)
# - unidade_delete (substituída por unidade_delete_ajax)
# - unidade_arvore (integrada em unidade_tree_view)
# - api_unidade_filhas (substituída por api_unidade_tree_data)
#
# A nova arquitetura usa:
# 1. View principal única (unidade_tree_view) para visualização hierárquica
# 2. Modais para operações CRUD (create_modal, update_modal, detail_modal)
# 3. AJAX para exclusões (delete_ajax)
# 4. APIs modernas para dados da árvore (api_unidade_tree_data)
# 5. APIs especializadas (search, export) para funcionalidades avançadas