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

# Conta Contabil com Códigos Externos - Árvore especializada  
# NOTA: As views da árvore com externos estão temporariamente comentadas
# até serem movidas para o arquivo correto
# from .contacontabil_external import (
#     contacontabil_tree_with_external_view,
#     api_contacontabil_tree_with_external_data,
# )

# Conta Externa - Edição inline moderna
from .contaexterna_inline import (
    # CRUD com edição inline
    contaexterna_list,                        # Lista com edição inline
    contaexterna_create,                      # Criar via inline/modal
    contaexterna_update,                      # Editar inline
    
    # APIs para operações inline
    api_contaexterna_delete,                  # Excluir via AJAX
    api_validar_codigo_externo,               # Validação em tempo real
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

# ===== ESTRUTURA DE ARQUIVOS DA NOVA ARQUITETURA =====
# 
# ARQUIVOS DE VIEWS:
# - dashboard.py → Dashboard e home
# - empresa.py → Gestão de empresas
# - unidade.py → CRUD modais para unidades
# - unidade_tree.py → Árvore hierárquica de unidades
# - centrocusto.py → CRUD modais e árvore de centros de custo
# - contacontabil.py → CRUD modais e árvore de contas contábeis
# - contacontabil_external.py → Árvore com códigos externos
# - contaexterna_inline.py → CRUD inline para códigos externos (NOVO)
# - usuario.py → Gestão de usuários
# - parametro.py → Gestão de parâmetros
#
# PADRÃO DA NOVA ARQUITETURA PARA CÓDIGOS EXTERNOS:
# 1. Visualização hierárquica integrada (contacontabil_external.py)
# 2. Edição inline direta na lista (contaexterna_inline.py)
# 3. APIs específicas para validação e operações AJAX
# 4. Templates responsivos e modernos
# 5. JavaScript otimizado para UX fluida
#
# FUNCIONALIDADES DOS CÓDIGOS EXTERNOS:
# ✅ Lista com filtros por conta contábil
# ✅ Edição inline de código e nome
# ✅ Criação inline direta na lista
# ✅ Exclusão com confirmação via AJAX
# ✅ Validação em tempo real
# ✅ Interface limpa sem modais desnecessários
# ✅ Integração total com árvore de contas contábeis
#
# BENEFÍCIOS DA IMPLEMENTAÇÃO INLINE:
# - Edição mais rápida e intuitiva
# - Menos cliques para o usuário
# - Interface mais limpa
# - Performance melhorada
# - Código mais simples e maintível
# - UX moderna e responsiva