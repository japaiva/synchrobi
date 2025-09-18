# gestor/services/fornecedor_extractor_service.py
# Serviço especializado em extração de fornecedores de históricos contábeis
# Versão atualizada com novas empresas na whitelist e padronização de nomes

import re
import hashlib
import logging
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from core.models import Fornecedor

logger = logging.getLogger('synchrobi')


@dataclass
class FornecedorExtraido:
    """Resultado da extração de fornecedor"""
    nome: str
    documento: str
    tipo: str  # 'PJ' ou 'PF'
    padrao_usado: str
    confianca: float  # 0.0 a 1.0


@dataclass
class ErroExtracao:
    """Estrutura para armazenar erros de extração"""
    data: str
    valor: Decimal
    documento: str
    historico: str
    motivo_erro: str
    tentativas: List[str]


class FornecedorExtractorService:
    """
    Serviço especializado na extração inteligente de fornecedores 
    de históricos contábeis brasileiros
    """
    
    # Lista para acumular erros da sessão
    _erros_sessao: List[ErroExtracao] = []
    
    # Whitelist - fornecedores conhecidos que devem sempre ser reconhecidos
    # ATUALIZADA COM NOVAS EMPRESAS
    WHITELIST_FORNECEDORES = [
        'CHOSEI',
        'SHOPPING METRO TATUAPE',
        'CENTER NORTE',
        'INMEO',
        'HDI SEGUROS',
        'REC 2016',
        # NOVAS EMPRESAS ADICIONADAS
        'BEAUTY FAIR',
        'TAIFF',
        'EMPRESA BRASILEIRA DE COSMETICOS',
        'EBC',  # Sigla de Empresa Brasileira de Cosméticos
        'CENTRO METROPOLITANO DE COSMETICOS',
        'CMC',  # Sigla de Centro Metropolitano de Cosméticos
        'ACTION TECHNOLOGY',
        'ACTION'  # Forma curta de Action Technology
    ]
    
    # Configuração das listas otimizadas
    IGNORAR_COMPLETAMENTE = [
        'INTEGRAÇÃO MÓDULO FISCAL',
        'INTEGRAÇÃO MÓDULO FINANCEIRO', 
        'INTEGRAÇÃO MÓDULO ORÇAMENTO',
        'CRÉDITO DE ICMS',
        'CREDITO DE ICMS',
        'ESTORNO - LANÇADO VIA REQUISIÇÃO',
        'RECLASSIFICAÇÃO',
        'REEDIV',
        'DESPESA DESLOCAMENTO',
        'VLR REF FRETES_RATEIO',
        'ESTORNO PARA ABERTURA POR RATEIO',
        'PROVISÃO DESP',
        'PROVISAO DESP',
        'TRANSF AUTORIZ ENTRE AGS',
        'Recuperação desp fornecedores PIX'
    ]
    
    # Lista de casos que devem sempre ser ignorados (não são fornecedores)
    # REMOVIDOS: 'RECEITA - ND', 'ALUGUEL - BEAUTY FAIR', 'ALUGUEL - TAIFF'
    IGNORAR_HISTORICOS = [
        # 'RECEITA - ND',  # REMOVIDO - agora processa normalmente
        'ALUGUEL CHOSEI - LOJA',  # Mas não "ALUGUEL CHOSEI" sozinho
        'SERVICOS DE CONSERVACAO E REPARO',
        # 'ALUGUEL - BEAUTY FAIR',  # REMOVIDO - Beauty Fair é fornecedor válido
        # 'ALUGUEL - TAIFF'  # REMOVIDO - Taiff é fornecedor válido
    ]
    
    PREFIXOS_CONTAMINACAO = [
        'IPTU_TERCEIRO',
        'SERVICOS ANTIFRAUDE',
        'MATERIAL DE ESCRITORIO', 
        'DESP VARIAVEIS DE VENDAS_LOJAS',
        'DESP VARIAVEIS DE VENDAS_TI', 
        'DESP VARIAVEIS DE VENDAS_LOG',
        'DESP C/ CAMPANHAS _ MKT',
        'DESP C/ ACOES LOJA _ MKT',
        'DESP C/ SONORIZACAO & IDENTIDADE',
        'DESP C/ SERVICOS DE TRANSPORTE VALORES',
        'PUBLICIDADE E PROPAGANDA DIGITAL',
        'SERVICOS DE SEGURANCA E VIGILANCIA',
        'MANUTENCAO DE EQUIPAMENTOS',
        'LOCACAO DE EQUIPAMENTOS / UTENSILIOS',
        'SUPRIMENTOS DE INFORMATICA',
        'EQUIPAMENTOS DE INFORMATICA',
        'SERVICOS PRESTADOS _ RESTRITO',
        'IMPOSTOS E TAXAS ESTADUAIS',
        'ENERGIA ELETRICA',
        'INTERNET',
        'CONDOMINIO E OUTROS',
        'CESTA DE NATAL',
        'FRETE SOBRE VENDAS',
        'SERVICOS TEC&CONTEUDO _ MKT'
    ]
    
    TERMINACOES_PJ = [
        'LTDA.', 'LTDA', 'S.A.', 'S/A', 'SA', 'ME', 'EPP', 'EIRELI',
        'MICROEMPRESA', 'EMPRESA INDIVIDUAL', 'PARTICIPACAO', 'PARTICIPACOES'
    ]
    
    # Palavras que indicam empresa mesmo sem terminação formal
    INDICADORES_EMPRESA = [
        'COMERCIO', 'SERVICOS', 'TECNOLOGIA', 'SOLUCOES', 'CONSULTORIA',
        'EMPREENDIMENTOS', 'CONSTRUCAO', 'INDUSTRIA', 'DISTRIBUIDORA',
        'TRANSPORTES', 'LOGISTICA', 'SISTEMAS', 'SOFTWARE', 'INFORMATICA',
        'SHOPPING', 'CENTER', 'CLINICA', 'MEDICINA', 'LABORATORIO',
        'ASSESSORIA', 'ADVOGADOS', 'ADVOCACIA', 'CONTABILIDADE',
        'CONSORCIO', 'FACILITIES', 'GESTAO',
        # ADICIONADOS INDICADORES RELACIONADOS ÀS NOVAS EMPRESAS
        'COSMETICOS', 'COSMETICA', 'FAIR', 'TECHNOLOGY', 'TECH'
    ]
    
    PALAVRAS_CONECTIVAS = [
        'DE', 'DO', 'DA', 'DOS', 'DAS', 'E', '&', 'COM', 'PARA',
        'EM', 'NO', 'NA', 'NOS', 'NAS', 'A', 'O', 'AS', 'OS'
    ]
    
    PADROES_REGEX = [
        {
            'nome': 'WHITELIST_CHECK',
            'regex': None,  # Será checado de forma especial
            'grupo_fornecedor': None,
            'grupo_documento': None,
            'prioridade': 0,
            'confianca': 1.0
        },
        {
            'nome': 'PREFIXO_REPETIDO',
            'regex': r'([A-Z\s]+) - .* - \1\s+(\d+)\s+([A-Z\s]+(?:LTDA|S/?A|ME|EPP)[^-]*)',
            'grupo_fornecedor': 3,  # Pega apenas o nome da empresa
            'grupo_documento': 2,    # O número
            'prioridade': 1,
            'confianca': 0.96
        },
        {
            'nome': 'DUPLO_COMPLETO',
            'regex': r'- (\d+)[:\s;]+([^;]+(?:LTDA|S/?A|ME|EPP|EIRELI|PARTICIPACAO)[^;]*)[;\s]*- \1[:\s;]+\2',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 1,
            'confianca': 0.98
        },
        {
            'nome': 'ROCKET_SELLER_PATTERN',
            'regex': r'- (\d+)[:\s;]*([A-Z][^;]+(?:LTDA|S/?A|ME|EPP)[^;]*)[;\s]*- \1[^;]+\2\s+\2',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 1,
            'confianca': 0.97
        },
        {
            'nome': 'DUPLO_LIMPO',
            'regex': r'- (\d+)[:\s]+([^-]+(?:LTDA\.?|S\.?A\.?|S/A|ME|EPP|EIRELI|PARTICIPACAO)[^-]*) - \1[:\s]+\2',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 2,
            'confianca': 0.96
        },
        {
            'nome': 'NOME_COMPOSTO_PJ',
            'regex': r'[-;]\s*(\d+)[;:\s]+([A-Z][A-Z\s\-\.&]+)\s*[-;]\s*([A-Z][A-Z\s]+(?:LTDA|S/?A|ME|EPP|EIRELI|PARTICIPACAO)[^;]*)',
            'grupo_fornecedor': lambda m: f"{m.group(2).strip()} {m.group(3).strip()}",
            'grupo_documento': 1,
            'prioridade': 2,
            'confianca': 0.95
        },
        {
            'nome': 'CENTER_NORTE_PATTERN',
            'regex': r'- (\d+)[:\s;]*[/\s]*([^/;]+CENTER NORTE[^/;]+)',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 2,
            'confianca': 0.95
        },
        {
            'nome': 'IPTU_ESPECIFICO',
            'regex': r'IPTU[_\s]TERCEIRO[^-]*- (\d+)[:\s;]+([^-]+(?:S/A|SA|LTDA|CONSTRUCAO|EMPREEND|ADM|PARTICIPACAO)[^-]*)',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 3,
            'confianca': 0.94
        },
        {
            'nome': 'DOCUMENTO_SEGUIDO_EMPRESA',
            'regex': r'(\d{4,8})[:\s;]+([A-Z][A-Z0-9\s\-\.&]+(?:LTDA|S/?A|ME|EPP|EIRELI|COMERCIO|SERVICOS|TECNOLOGIA|EMPREENDIMENTOS|CONSORCIO|SHOPPING|CENTER)[^-;]*)',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 3,
            'confianca': 0.93
        },
        {
            'nome': 'CNPJ_PESSOA',
            'regex': r'(\d{2}\.\d{3}\.\d{3})[/\s\-]*([A-Z][A-Z\s]+(?:LTDA|S/?A|ME|EPP|SILVA|SANTOS|SOUZA|OLIVEIRA)[^;]*)',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 3,
            'confianca': 0.92
        },
        {
            'nome': 'SIMPLES_FLEXIVEL',
            'regex': r'[-;]\s*(\d*)[:\s;]*([A-Z][A-Z0-9\s\-\.&]{3,}(?:LTDA|S/?A|ME|EPP|TI|COMERCIO|SERVICOS|TECNOLOGIA)?[^-;]*)',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 4,
            'confianca': 0.90
        },
        {
            'nome': 'SIMPLES_LIMPO',
            'regex': r'- (\d+)[:\s]+([^-]+(?:LTDA\.?|S\.?A\.?|S/A|ME|EPP|EIRELI)[^-]*?)(?:\s*$|(?=\s*-(?!\s*\1)))',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 5,
            'confianca': 0.89
        },
        {
            'nome': 'TRACO_DUPLO',
            'regex': r'- - (\d+)[:\s]+([^-]+(?:LTDA\.?|S\.?A\.?|S/A|ME|EPP|EIRELI)[^-]*?)(?:\s*$)',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 6,
            'confianca': 0.88
        },
        {
            'nome': 'CONTAMINADO_DUPLO',
            'regex': r'([A-Z][A-Z\s&\.]+(?:LTDA\.?|S\.?A\.?|S/A|ME|EPP|EIRELI))\s+(\d+)\s*-\s*\2\s+\1',
            'grupo_fornecedor': 1,
            'grupo_documento': 2,
            'prioridade': 7,
            'confianca': 0.87
        },
        {
            'nome': 'PESSOA_FISICA_FLEXIVEL',
            'regex': r'[-;]\s*(\d*)[:\s;]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 8,
            'confianca': 0.85,
            'validar_pf': True
        },
        {
            'nome': 'PESSOA_FISICA',
            'regex': r'- (\d+)[:\s]+([A-Z][A-Za-z\s]{8,40}) - \1[:\s]+\2',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 9,
            'confianca': 0.84,
            'validar_pf': True
        }
    ]

    @classmethod
    def extrair_fornecedor(cls, historico: str, contexto_movimento: Dict = None) -> Optional[FornecedorExtraido]:
        """
        Método principal para extrair fornecedor do histórico
        
        Args:
            historico: String do histórico contábil
            contexto_movimento: Dicionário com data, valor e documento do movimento
            
        Returns:
            FornecedorExtraido ou None se não encontrar
        """
        if not historico or not isinstance(historico, str):
            cls._registrar_erro(historico, contexto_movimento, "Histórico vazio ou inválido", [])
            return None
            
        # Verificar se deve ignorar completamente
        if cls._deve_ignorar_completamente(historico):
            # Não registra erro para ignorados intencionalmente
            return None
        
        tentativas = []
        
        # Tentar extrair por padrões priorizados
        for padrao in sorted(cls.PADROES_REGEX, key=lambda x: x['prioridade']):
            tentativas.append(f"Tentou padrão {padrao['nome']}")
            resultado = cls._tentar_padrao(historico, padrao)
            if resultado:
                # Removido o log de sucesso aqui
                return resultado
        
        # Se chegou aqui, nenhum padrão funcionou
        cls._registrar_erro(historico, contexto_movimento, "Nenhum padrão conseguiu extrair", tentativas)
        return None
    
    @classmethod
    def _registrar_erro(cls, historico: str, contexto: Dict, motivo: str, tentativas: List[str]):
        """Registra erro de extração com contexto completo"""
        erro = ErroExtracao(
            data=contexto.get('data', '') if contexto else '',
            valor=contexto.get('valor', Decimal('0')) if contexto else Decimal('0'),
            documento=contexto.get('documento', '') if contexto else '',
            historico=historico[:200] if historico else '',
            motivo_erro=motivo,
            tentativas=tentativas
        )
        
        cls._erros_sessao.append(erro)
        
        # Log apenas erros importantes (não os ignorados)
        if "ignorar" not in motivo.lower():
            logger.warning(
                f"❌ ERRO EXTRAÇÃO | "
                f"Data: {erro.data} | "
                f"Valor: R$ {erro.valor:,.2f} | "
                f"Doc: {erro.documento} | "
                f"Histórico: '{erro.historico}' | "
                f"Motivo: {erro.motivo_erro}"
            )
    
    @classmethod
    def listar_erros_sessao(cls) -> List[ErroExtracao]:
        """Retorna lista de erros da sessão atual"""
        return cls._erros_sessao
    
    @classmethod
    def limpar_erros_sessao(cls):
        """Limpa lista de erros da sessão"""
        cls._erros_sessao = []
    
    @classmethod
    def relatorio_erros(cls) -> str:
        """Gera relatório formatado dos erros"""
        if not cls._erros_sessao:
            return "✅ Nenhum erro de extração encontrado na sessão."
        
        relatorio = [
            "\n" + "="*80,
            "📊 RELATÓRIO DE ERROS DE EXTRAÇÃO DE FORNECEDORES",
            "="*80,
            f"Total de erros: {len(cls._erros_sessao)}",
            "-"*80
        ]
        
        for i, erro in enumerate(cls._erros_sessao, 1):
            relatorio.extend([
                f"\n❌ Erro #{i}:",
                f"   Data: {erro.data}",
                f"   Valor: R$ {erro.valor:,.2f}",
                f"   Documento: {erro.documento}",
                f"   Histórico: {erro.historico}",
                f"   Motivo: {erro.motivo_erro}",
                f"   Tentativas: {', '.join(erro.tentativas) if erro.tentativas else 'Nenhuma'}"
            ])
        
        relatorio.append("="*80)
        return "\n".join(relatorio)
    
    @classmethod
    def extrair_documento(cls, historico: str) -> str:
        """
        Extrai número do documento do histórico
        
        Args:
            historico: String do histórico contábil
            
        Returns:
            Número do documento ou string vazia
        """
        if not historico:
            return ''
        
        # Padrão 1: número repetido "- NÚMERO NOME - NÚMERO NOME"
        match = re.search(r'- (\d+)[:\s]+[^-]+ - \1[:\s]+', historico)
        if match:
            return match.group(1)
        
        # Padrão 2: após terminação PJ "EMPRESA LTDA 123456"
        match = re.search(r'(?:LTDA\.?|S\.?A\.?|S/A|ME|EPP|EIRELI|PARTICIPACAO)\s+(\d{4,10})', 
                         historico, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Padrão 3: número após dois pontos ou ponto-vírgula
        match = re.search(r'[:\s;]\s*(\d{4,8})\s*[:\s;]', historico)
        if match:
            return match.group(1)
        
        # Padrão 4: qualquer número 4-8 dígitos
        matches = re.findall(r'\b(\d{4,8})\b', historico)
        return matches[0] if matches else ''
    
    @classmethod
    def buscar_ou_criar_fornecedor(cls, fornecedor_extraido: FornecedorExtraido, 
                                  historico_original: str = '') -> Optional[Fornecedor]:
        """
        Busca fornecedor existente ou cria novo
        
        Args:
            fornecedor_extraido: Dados do fornecedor extraído
            historico_original: Histórico original para referência
            
        Returns:
            Instância de Fornecedor ou None
        """
        # Buscar fornecedor existente
        fornecedor_existente = cls._buscar_fornecedor_existente(fornecedor_extraido.nome)
        if fornecedor_existente:
            # Removido log de sucesso
            return fornecedor_existente
        
        # Criar novo fornecedor
        novo_fornecedor = cls._criar_fornecedor_automatico(fornecedor_extraido.nome, historico_original)
        # Log apenas na criação (já existe no método _criar_fornecedor_automatico)
        return novo_fornecedor
    
    @classmethod
    def _deve_ignorar_completamente(cls, historico: str) -> bool:
        """Verifica se deve ignorar sem tentar extrair"""
        historico_upper = historico.upper()
        
        # Primeiro verifica se deve ignorar baseado em padrões específicos
        for pattern in cls.IGNORAR_HISTORICOS:
            if pattern.upper() in historico_upper:
                return True
        
        # Depois verifica a lista original
        for pattern in cls.IGNORAR_COMPLETAMENTE:
            if pattern.upper() in historico_upper:
                return True
        
        return False
    
    @classmethod
    def _tentar_padrao(cls, historico: str, padrao: dict) -> Optional[FornecedorExtraido]:
        """Tenta extrair fornecedor usando um padrão específico"""
        
        # Tratamento especial para whitelist
        if padrao['nome'] == 'WHITELIST_CHECK':
            return cls._verificar_whitelist(historico)
        
        match = re.search(padrao['regex'], historico, re.IGNORECASE)
        
        if not match:
            return None
        
        # Tratamento para grupo_fornecedor como função (para nomes compostos)
        if callable(padrao['grupo_fornecedor']):
            nome = padrao['grupo_fornecedor'](match).strip()
        else:
            nome = match.group(padrao['grupo_fornecedor']).strip()
        
        documento = ''
        if padrao.get('grupo_documento'):
            try:
                documento = match.group(padrao['grupo_documento']).strip()
            except:
                documento = ''
        
        # Validação específica por tipo
        if padrao.get('validar_pf'):
            if cls._validar_pessoa_fisica(nome):
                return FornecedorExtraido(
                    nome=nome.upper(),
                    documento=documento,
                    tipo='PF',
                    padrao_usado=padrao['nome'],
                    confianca=padrao['confianca']
                )
        else:
            # Limpar e validar pessoa jurídica
            nome_limpo = cls._limpar_fornecedor(nome)
            if cls._validar_pessoa_juridica(nome_limpo):
                return FornecedorExtraido(
                    nome=nome_limpo,
                    documento=documento,
                    tipo='PJ',
                    padrao_usado=padrao['nome'],
                    confianca=padrao['confianca']
                )
        
        return None
    
    @classmethod
    def _verificar_whitelist(cls, historico: str) -> Optional[FornecedorExtraido]:
        """Verifica se há fornecedor da whitelist no histórico com padronização de nomes"""
        historico_upper = historico.upper()
        
        # Mapeamento de nomes para padronização
        # Quando encontrar a chave, salva como o valor
        NOME_PADRONIZADO = {
            'ACTION': 'ACTION TECHNOLOGY',
            'ACTION TECHNOLOGY': 'ACTION TECHNOLOGY',
            'EBC': 'EMPRESA BRASILEIRA DE COSMETICOS',
            'EMPRESA BRASILEIRA DE COSMETICOS': 'EMPRESA BRASILEIRA DE COSMETICOS',
            'CMC': 'CENTRO METROPOLITANO DE COSMETICOS',
            'CENTRO METROPOLITANO DE COSMETICOS': 'CENTRO METROPOLITANO DE COSMETICOS',
            'BEAUTY FAIR': 'BEAUTY FAIR',
            'TAIFF': 'TAIFF',
            'CHOSEI': 'CHOSEI',
            'SHOPPING METRO TATUAPE': 'SHOPPING METRO TATUAPE',
            'CENTER NORTE': 'CENTER NORTE',
            'INMEO': 'INMEO',
            'HDI SEGUROS': 'HDI SEGUROS',
            'REC 2016': 'REC 2016'
        }
        
        for fornecedor_white in cls.WHITELIST_FORNECEDORES:
            if fornecedor_white.upper() in historico_upper:
                # Tentar extrair o nome completo ao redor da whitelist
                patterns = [
                    rf'(\d+)[:\s;]+([^;-]*{re.escape(fornecedor_white)}[^;-]*)',
                    rf'([^;-]*{re.escape(fornecedor_white)}[^;-]*)',
                    rf'{re.escape(fornecedor_white)}[^;-]*'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, historico, re.IGNORECASE)
                    if match:
                        if len(match.groups()) >= 2:
                            nome = match.group(2).strip()
                            documento = match.group(1).strip() if match.group(1) else ''
                        else:
                            nome = match.group(0).strip()
                            documento = cls.extrair_documento(historico)
                        
                        # Limpar o nome
                        nome_limpo = cls._limpar_fornecedor(nome)
                        
                        # PADRONIZAÇÃO: Se o nome está no mapeamento, usar o nome padronizado
                        nome_upper = nome_limpo.upper() if nome_limpo else ''
                        if nome_upper in NOME_PADRONIZADO:
                            nome_limpo = NOME_PADRONIZADO[nome_upper]
                        
                        if nome_limpo:
                            return FornecedorExtraido(
                                nome=nome_limpo,
                                documento=documento,
                                tipo='PJ',
                                padrao_usado='WHITELIST',
                                confianca=0.99
                            )
        
        return None
    
    @classmethod
    def _limpar_fornecedor(cls, nome: str) -> str:
        """Remove contaminação do nome do fornecedor"""
        if not nome:
            return ''
        
        nome_limpo = nome.strip()
        
        # NOVA LÓGICA: Se o nome É IGUAL a um prefixo de contaminação, retornar vazio
        if nome_limpo.upper() in [p.upper() for p in cls.PREFIXOS_CONTAMINACAO]:
            return ''  # Não é um fornecedor, é só a descrição
        
        # Remover caracteres especiais do início e fim (/, -, etc)
        nome_limpo = re.sub(r'^[/\-\s]+|[/\-\s]+$', '', nome_limpo)
        
        # Remover CNPJ/CPF do início (formato XX.XXX.XXX)
        nome_limpo = re.sub(r'^\d{2}\.\d{3}\.\d{3}[\s/\-]*', '', nome_limpo, flags=re.IGNORECASE)
        
        # Remover prefixos de contaminação
        for prefixo in cls.PREFIXOS_CONTAMINACAO:
            if nome_limpo.upper().startswith(prefixo.upper()):
                nome_limpo = nome_limpo[len(prefixo):].strip()
                # Remove também traços e espaços extras após o prefixo
                nome_limpo = re.sub(r'^[-\s:;]+', '', nome_limpo).strip()
                break
        
        # Truncar nome em palavras-chave (REEMB, REF, DESPESAS, etc)
        palavras_truncar = [
            'REEMB', 'REF ', 'REFERENTE', 'RELATIVO',
            'DESPESAS', 'DESPESA ', 'DESP ', 
            'CUSTOS', 'CUSTO ', 
            'PAGAMENTO', 'PGTO',
            'VALOR', 'VLR'
        ]
        for palavra in palavras_truncar:
            if palavra in nome_limpo.upper():
                pos = nome_limpo.upper().find(palavra)
                nome_limpo = nome_limpo[:pos].strip()
        
        # Remover padrões com regex - REMOVIDO 'ND' DA LISTA
        patterns_limpeza = [
            r'^(?:DESP|MATERIAL|SERVICOS|PUBLICIDADE)\s+\w*\s*',
            r'^\w*\s*\((?:DANFE|NFSERV|CTE)\)\s*',
            r'^(?:VARIAVEIS|CAMPANHAS|ACOES)\s+\w*\s*',
            r'^Lançamento integração Orçamento\.\s*-\s*',
            r'^ESTORNO\s+',
            # r'^ND\s+',  # REMOVIDO - agora processa ND normalmente
        ]
        
        for pattern in patterns_limpeza:
            nome_limpo = re.sub(pattern, '', nome_limpo, flags=re.IGNORECASE).strip()
        
        # Limpeza geral - preserva alguns caracteres especiais importantes mas remove / no início/fim
        nome_limpo = re.sub(r'^[/]+|[/]+$', '', nome_limpo)
        nome_limpo = re.sub(r'[^\w\s&\.\-]', ' ', nome_limpo)
        nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip().upper()
        
        return nome_limpo
    
    @classmethod
    def _validar_pessoa_juridica(cls, nome: str) -> bool:
        """Valida se é pessoa jurídica válida"""
        if not nome or len(nome) < 5:
            return False
        
        # Verifica whitelist primeiro
        for fornecedor_white in cls.WHITELIST_FORNECEDORES:
            if fornecedor_white.upper() in nome.upper():
                return True
        
        # Verifica terminações PJ tradicionais
        tem_terminacao_pj = any(term.upper() in nome.upper() for term in cls.TERMINACOES_PJ)
        
        # Verifica indicadores de empresa (mais flexível)
        tem_indicador = any(ind.upper() in nome.upper() for ind in cls.INDICADORES_EMPRESA)
        
        # Aceita se tem terminação OU indicador
        if tem_terminacao_pj or tem_indicador:
            # Deve ter palavras significativas
            palavras = nome.split()
            palavras_validas = [p for p in palavras 
                              if len(p) >= 2 
                              and p.upper() not in cls.PALAVRAS_CONECTIVAS]
            
            return len(palavras_validas) >= 1
        
        return False
    
    @classmethod
    def _validar_pessoa_fisica(cls, nome: str) -> bool:
        """Valida se é pessoa física válida - mais flexível"""
        if not nome or len(nome) < 5:
            return False
        
        palavras = nome.split()
        if len(palavras) < 2 or len(palavras) > 7:
            return False
        
        # Verificar se não é empresa
        for term in cls.TERMINACOES_PJ + cls.INDICADORES_EMPRESA:
            if term.upper() in nome.upper():
                return False
        
        # Verificar formato de nomes próprios (mais flexível)
        nomes_validos = 0
        for palavra in palavras:
            # Aceita nomes com maiúscula inicial ou conectivos
            if (len(palavra) >= 2 and palavra[0].isupper()) or palavra.upper() in cls.PALAVRAS_CONECTIVAS:
                nomes_validos += 1
        
        return nomes_validos >= len(palavras) * 0.6
    
    @classmethod
    def _buscar_fornecedor_existente(cls, nome_limpo: str) -> Optional[Fornecedor]:
        """Busca fornecedor existente por similaridade"""
        # Busca exata
        try:
            return Fornecedor.objects.get(razao_social=nome_limpo, ativo=True)
        except Fornecedor.DoesNotExist:
            pass
        
        # Busca por similaridade
        palavras_chave = nome_limpo.split()[:3]
        if len(palavras_chave) >= 2:
            filtro_busca = ' '.join(palavras_chave[:2])
            
            candidatos = Fornecedor.objects.filter(
                razao_social__icontains=filtro_busca,
                ativo=True
            )[:10]
            
            for candidato in candidatos:
                similaridade = cls._calcular_similaridade(nome_limpo, candidato.razao_social)
                
                if similaridade > 0.75:
                    return candidato
        
        return None
    
    @classmethod
    def _calcular_similaridade(cls, nome1: str, nome2: str) -> float:
        """Calcula similaridade entre dois nomes"""
        set1 = set(nome1.split())
        set2 = set(nome2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersecao = len(set1 & set2)
        uniao = len(set1 | set2)
        
        # Jaccard similarity
        return intersecao / uniao if uniao > 0 else 0.0
    
    @classmethod
    def _gerar_codigo_fornecedor(cls, nome_limpo: str) -> str:
        """Gera código único para fornecedor"""
        # Código baseado em iniciais + hash
        palavras = [p for p in nome_limpo.split() 
                   if len(p) >= 2 and p not in cls.PALAVRAS_CONECTIVAS]
        
        iniciais = ''.join(p[0] for p in palavras[:3])
        
        if len(iniciais) < 2:
            iniciais = nome_limpo.replace(' ', '')[:3]
        
        # Hash para unicidade
        hash_codigo = hashlib.md5(nome_limpo.encode()).hexdigest()[:3].upper()
        codigo_base = f"{iniciais}{hash_codigo}"
        
        # Garantir unicidade
        codigo_final = codigo_base
        contador = 1
        
        while Fornecedor.objects.filter(codigo=codigo_final).exists():
            codigo_final = f"{codigo_base}{contador:02d}"
            contador += 1
            if contador > 99:
                import time
                codigo_final = f"AUTO{int(time.time()) % 10000:04d}"
                break
        
        return codigo_final
    
    @classmethod
    def _criar_fornecedor_automatico(cls, nome_limpo: str, 
                                   historico_original: str = '') -> Optional[Fornecedor]:
        """Cria novo fornecedor automaticamente"""
        # Gerar código único
        codigo_final = cls._gerar_codigo_fornecedor(nome_limpo)
        
        try:
            fornecedor = Fornecedor.objects.create(
                codigo=codigo_final,
                razao_social=nome_limpo,
                criado_automaticamente=True,
                origem_historico=historico_original[:500] if historico_original else ''
            )
            
            # Manter apenas log de criação de novos fornecedores
            logger.info(f"🆕 Fornecedor criado: {codigo_final} - {nome_limpo}")
            return fornecedor
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar fornecedor {nome_limpo}: {str(e)}")
            return None


# Funções de conveniência para compatibilidade
def extrair_fornecedor_do_historico(historico: str, contexto_movimento: Dict = None) -> Optional[Fornecedor]:
    """
    Função de conveniência para extrair e buscar/criar fornecedor
    
    Args:
        historico: String do histórico contábil
        contexto_movimento: Dict com data, valor, documento do movimento
        
    Returns:
        Instância de Fornecedor ou None
    """
    fornecedor_extraido = FornecedorExtractorService.extrair_fornecedor(historico, contexto_movimento)
    
    if not fornecedor_extraido:
        return None
    
    return FornecedorExtractorService.buscar_ou_criar_fornecedor(
        fornecedor_extraido, historico
    )


def extrair_numero_documento_do_historico(historico: str) -> str:
    """
    Função de conveniência para extrair número do documento
    
    Args:
        historico: String do histórico contábil
        
    Returns:
        Número do documento ou string vazia
    """
    return FornecedorExtractorService.extrair_documento(historico)


def gerar_relatorio_erros() -> str:
    """
    Gera relatório de erros da sessão atual
    
    Returns:
        String formatada com o relatório
    """
    return FornecedorExtractorService.relatorio_erros()


def limpar_erros() -> None:
    """Limpa a lista de erros da sessão"""
    FornecedorExtractorService.limpar_erros_sessao()


# Exemplo de uso com contexto
if __name__ == "__main__":
    # Testes com as novas empresas
    testes = [
        "RECEITA - ND 12345 EMPRESA BRASILEIRA DE COSMETICOS LTDA",
        "ALUGUEL - BEAUTY FAIR - 2024/07",
        "PAGAMENTO - TAIFF INDUSTRIA E COMERCIO LTDA",
        "SERVICOS - EBC - EMPRESA BRASILEIRA DE COSMETICOS",
        "COMPRA - CMC - CENTRO METROPOLITANO DE COSMETICOS",
        "SISTEMA - ACTION TECHNOLOGY LTDA",
        "DESENVOLVIMENTO - ACTION SOFTWARE",
        "PAGAMENTO - ACTION - 2024",
        "NOTA FISCAL - EBC LTDA"
    ]
    
    print("="*60)
    print("TESTE DE EXTRAÇÃO COM PADRONIZAÇÃO")
    print("="*60)
    
    for historico in testes:
        fornecedor = extrair_fornecedor_do_historico(historico)
        if fornecedor:
            print(f"✅ Histórico: {historico[:40]}")
            print(f"   Extraído: {fornecedor.codigo} - {fornecedor.razao_social}")
        else:
            print(f"❌ Não extraído: {historico}")
        print("-"*60)