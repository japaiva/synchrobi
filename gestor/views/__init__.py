# gestor/views/__init__.py
# Imports centralizados para facilitar o uso

from .dashboard import home, dashboard
from .usuario import usuario_list, usuario_create, usuario_update, usuario_delete
from .unidade import (
    unidade_list, unidade_create, unidade_detail, unidade_update, 
    unidade_delete, unidade_arvore, api_unidade_filhas, api_validar_codigo
)
from .empresa import (
    empresa_list, empresa_create, empresa_update, empresa_delete,
    api_validar_sigla_empresa, api_validar_cnpj_empresa, api_empresa_info
)
from .parametro import (
    parametro_list, parametro_create, parametro_detail, parametro_update,
    parametro_delete, api_parametro_valor
)
from .centrocusto import (
    centrocusto_list, centrocusto_create, centrocusto_update, centrocusto_delete,
    api_validar_codigo_centrocusto
)
from .contacontabil import (
    contacontabil_list, contacontabil_create, contacontabil_update, contacontabil_delete,
    api_validar_codigo_contacontabil
)

__all__ = [
    # Dashboard
    'home', 'dashboard',
    
    # Usuários
    'usuario_list', 'usuario_create', 'usuario_update', 'usuario_delete',
    
    # Unidades
    'unidade_list', 'unidade_create', 'unidade_detail', 'unidade_update', 
    'unidade_delete', 'unidade_arvore', 'api_unidade_filhas', 'api_validar_codigo',
    
    # Empresas
    'empresa_list', 'empresa_create', 'empresa_update', 'empresa_delete',
    'api_validar_sigla_empresa', 'api_validar_cnpj_empresa', 'api_empresa_info',
    
    # Parâmetros
    'parametro_list', 'parametro_create', 'parametro_detail', 'parametro_update',
    'parametro_delete', 'api_parametro_valor',
    
    # Centros de Custo
    'centrocusto_list', 'centrocusto_create', 'centrocusto_update', 'centrocusto_delete',
    'api_validar_codigo_centrocusto',
    
    # Contas Contábeis
    'contacontabil_list', 'contacontabil_create', 'contacontabil_update', 'contacontabil_delete',
    'api_validar_codigo_contacontabil',
]