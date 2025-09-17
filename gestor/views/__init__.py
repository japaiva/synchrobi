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
    api_buscar_unidade_multiplos_criterios,  # API busca avançada
    api_buscar_unidade_para_movimento,       # API busca para movimento
)

# Unidade Tree - View principal e APIs especializadas
from .unidade_tree import (
    unidade_tree_view,               # View principal da árvore (PRINCIPAL)
    unidade_tree_data,               # API com filtros avançados
    unidade_tree_search,             # API de busca rápida
    unidade_tree_export,             # API de exportação para Excel
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
    api_centro_custo_detalhes,       # API para detalhes do centro de custo
    
    # Views mantidas para compatibilidade (redirecionam)
    centrocusto_list,                # Redireciona para árvore
    centrocusto_create,              # Redireciona para modal
    centrocusto_update,              # Redireciona para modal
    centrocusto_delete,              # Redireciona para AJAX
)

# Conta Contábil - Nova arquitetura focada na árvore
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

# Usuário
from .usuario import (
    usuario_list, 
    usuario_create, 
    usuario_update, 
    usuario_delete
)

# Parâmetro
from .parametro import (
    parametro_list, 
    parametro_create, 
    parametro_detail, 
    parametro_update, 
    parametro_delete,
    api_parametro_valor
)

# Movimento - CRUD básico separado das funções de importação
from .movimento import (
    # CRUD básico de movimentos
    movimento_list,                      # Lista de movimentos com filtros
    movimento_create,                    # Criar movimento
    movimento_update,                    # Editar movimento
    movimento_delete,                    # Excluir movimento
    
    # Exportação
    movimento_export_excel,              # Exportar para Excel
)

# Movimento Import - CORRIGIDO COM FUNÇÕES QUE REALMENTE EXISTEM
from .movimento_import import (
    # Interface e validações
    movimento_importar,                  # Interface de importação
    api_preview_movimentos_excel,        # Preview antes da importação
    api_validar_periodo_importacao,      # Validação completa de período
    api_validar_periodo_simples,         # Validação simples de período
    
    # Importação (mantendo nomes atuais para compatibilidade)
    api_importar_movimentos_detalhado,   # ✅ NOME CORRETO da função principal
    api_importar_movimentos_simples,     # Importação simplificada
)

# Fornecedor - Gestão de fornecedores
from .fornecedor import (
    fornecedor_list,                     # Lista de fornecedores
    fornecedor_create,                   # Criar fornecedor
    fornecedor_update,                   # Editar fornecedor
    fornecedor_delete,                   # Excluir fornecedor
    
    # APIs para fornecedores
    api_validar_codigo_fornecedor,       # Validação de código
    api_buscar_fornecedor,               # Busca de fornecedores
    api_fornecedor_info,                 # Informações do fornecedor
    api_extrair_fornecedor_historico,    # Extração do histórico
)