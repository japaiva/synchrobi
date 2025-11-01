# core/models/__init__.py - IMPORTAÇÕES CENTRALIZADAS

# Imports base
from .base import HierarquiaDinamicaMixin

# Modelos principais
from .usuario import Usuario
from .empresa import Empresa
from .hierarquicos import Unidade, CentroCusto, ContaContabil
from .grupocc import GrupoCC
from .fornecedor import Fornecedor
from .movimento import Movimento

# Modelos auxiliares e relacionamentos
from .relacionamentos import (
    ParametroSistema,
    UsuarioCentroCusto,
    EmpresaCentroCusto,
    ContaExterna,
    CentroCustoExterno
)

# Garantir que todos os modelos sejam exportados
__all__ = [
    # Base
    'HierarquiaDinamicaMixin',

    # Principais
    'Usuario',
    'Empresa',
    'Unidade',
    'CentroCusto',
    'ContaContabil',
    'GrupoCC',
    'Fornecedor',
    'Movimento',

    # Auxiliares
    'ParametroSistema',
    'UsuarioCentroCusto',
    'EmpresaCentroCusto',
    'ContaExterna',
    'CentroCustoExterno'
]