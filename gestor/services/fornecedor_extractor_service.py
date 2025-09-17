# gestor/services/fornecedor_extractor_service.py
# Serviço especializado em extração de fornecedores de históricos contábeis

import re
import hashlib
import logging
from typing import Tuple, Optional
from dataclasses import dataclass

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


class FornecedorExtractorService:
    """
    Serviço especializado na extração inteligente de fornecedores 
    de históricos contábeis brasileiros
    """
    
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
    
    PREFIXOS_CONTAMINACAO = [
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
        'LTDA.', 'LTDA', 'S.A.', 'S/A', 'ME', 'EPP', 'EIRELI',
        'MICROEMPRESA', 'EMPRESA INDIVIDUAL'
    ]
    
    PALAVRAS_CONECTIVAS = [
        'DE', 'DO', 'DA', 'DOS', 'DAS', 'E', '&', 'COM', 'PARA',
        'EM', 'NO', 'NA', 'NOS', 'NAS', 'A', 'O', 'AS', 'OS'
    ]
    
    PADROES_REGEX = [
        {
            'nome': 'DUPLO_LIMPO',
            'regex': r'- (\d+) ([^-]+(?:LTDA\.?|S\.A\.?|S/A|ME|EPP|EIRELI)[^-]*) - \1 \2',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 1,
            'confianca': 0.98
        },
        {
            'nome': 'SIMPLES_LIMPO',
            'regex': r'- (\d+) ([^-]+(?:LTDA\.?|S\.A\.?|S/A|ME|EPP|EIRELI)[^-]*?)(?:\s*$|(?=\s*-(?!\s*\1)))',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 2,
            'confianca': 0.95
        },
        {
            'nome': 'TRACO_DUPLO',
            'regex': r'- - (\d+) ([^-]+(?:LTDA\.?|S\.A\.?|S/A|ME|EPP|EIRELI)[^-]*?)(?:\s*$)',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 3,
            'confianca': 0.92
        },
        {
            'nome': 'CONTAMINADO_DUPLO',
            'regex': r'([A-Z][A-Z\s&\.]+(?:LTDA\.?|S\.A\.?|S/A|ME|EPP|EIRELI))\s+(\d+)\s*-\s*\2\s+\1',
            'grupo_fornecedor': 1,
            'grupo_documento': 2,
            'prioridade': 4,
            'confianca': 0.88
        },
        {
            'nome': 'PESSOA_FISICA',
            'regex': r'- (\d+) ([A-Z][A-Za-z\s]{8,40}) - \1 \2',
            'grupo_fornecedor': 2,
            'grupo_documento': 1,
            'prioridade': 5,
            'confianca': 0.85,
            'validar_pf': True
        }
    ]

    @classmethod
    def extrair_fornecedor(cls, historico: str) -> Optional[FornecedorExtraido]:
        """
        Método principal para extrair fornecedor do histórico
        
        Args:
            historico: String do histórico contábil
            
        Returns:
            FornecedorExtraido ou None se não encontrar
        """
        if not historico or not isinstance(historico, str):
            return None
            
        # Verificar se deve ignorar completamente
        if cls._deve_ignorar_completamente(historico):
            logger.debug(f"Histórico ignorado: {historico[:50]}...")
            return None
        
        # Tentar extrair por padrões priorizados
        for padrao in sorted(cls.PADROES_REGEX, key=lambda x: x['prioridade']):
            resultado = cls._tentar_padrao(historico, padrao)
            if resultado:
                return resultado
        
        return None
    
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
        match = re.search(r'- (\d+) [^-]+ - \1 ', historico)
        if match:
            return match.group(1)
        
        # Padrão 2: após terminação PJ "EMPRESA LTDA 123456"
        match = re.search(r'(?:LTDA\.?|S\.A\.?|S/A|ME|EPP|EIRELI)\s+(\d{4,10})', 
                         historico, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Padrão 3: qualquer número 4-8 dígitos
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
            return fornecedor_existente
        
        # Criar novo fornecedor
        return cls._criar_fornecedor_automatico(fornecedor_extraido.nome, historico_original)
    
    # Métodos privados de implementação
    
    @classmethod
    def _deve_ignorar_completamente(cls, historico: str) -> bool:
        """Verifica se deve ignorar sem tentar extrair"""
        historico_upper = historico.upper()
        
        for pattern in cls.IGNORAR_COMPLETAMENTE:
            if pattern.upper() in historico_upper:
                return True
        
        return False
    
    @classmethod
    def _tentar_padrao(cls, historico: str, padrao: dict) -> Optional[FornecedorExtraido]:
        """Tenta extrair fornecedor usando um padrão específico"""
        match = re.search(padrao['regex'], historico, re.IGNORECASE)
        
        if not match:
            return None
        
        nome = match.group(padrao['grupo_fornecedor']).strip()
        documento = match.group(padrao['grupo_documento']).strip() if padrao.get('grupo_documento') else ''
        
        logger.debug(f"Padrão {padrao['nome']} capturou: {nome}")
        
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
    def _limpar_fornecedor(cls, nome: str) -> str:
        """Remove contaminação do nome do fornecedor"""
        if not nome:
            return ''
        
        nome_limpo = nome.strip()
        
        # Remover prefixos de contaminação
        for prefixo in cls.PREFIXOS_CONTAMINACAO:
            if nome_limpo.upper().startswith(prefixo.upper()):
                nome_limpo = nome_limpo[len(prefixo):].strip()
                break
        
        # Remover padrões com regex
        patterns_limpeza = [
            r'^(?:DESP|MATERIAL|SERVICOS|PUBLICIDADE)\s+\w*\s*',
            r'^\w*\s*\((?:DANFE|NFSERV|CTE)\)\s*',
            r'^(?:VARIAVEIS|CAMPANHAS|ACOES)\s+\w*\s*'
        ]
        
        for pattern in patterns_limpeza:
            nome_limpo = re.sub(pattern, '', nome_limpo, flags=re.IGNORECASE).strip()
        
        # Limpeza geral
        nome_limpo = re.sub(r'[^\w\s&\.\-]', ' ', nome_limpo)
        nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip().upper()
        
        return nome_limpo
    
    @classmethod
    def _validar_pessoa_juridica(cls, nome: str) -> bool:
        """Valida se é pessoa jurídica válida"""
        if not nome or len(nome) < 7:
            return False
        
        # Deve ter terminação PJ
        tem_terminacao = any(term.upper() in nome.upper() for term in cls.TERMINACOES_PJ)
        if not tem_terminacao:
            return False
        
        # Deve ter palavras significativas
        palavras = nome.split()
        palavras_validas = [p for p in palavras 
                          if len(p) >= 2 
                          and p.upper() not in cls.TERMINACOES_PJ
                          and p.upper() not in cls.PALAVRAS_CONECTIVAS]
        
        return len(palavras_validas) >= 1
    
    @classmethod
    def _validar_pessoa_fisica(cls, nome: str) -> bool:
        """Valida se é pessoa física válida"""
        if not nome or len(nome) < 8:
            return False
        
        palavras = nome.split()
        if len(palavras) < 2 or len(palavras) > 6:
            return False
        
        # Verificar formato de nomes próprios
        nomes_validos = 0
        for palavra in palavras:
            if (re.match(r'^[A-Z][a-zA-Z]{1,20}$', palavra) or 
                palavra.upper() in cls.PALAVRAS_CONECTIVAS):
                nomes_validos += 1
        
        return nomes_validos >= len(palavras) * 0.75
    
    @classmethod
    def _buscar_fornecedor_existente(cls, nome_limpo: str) -> Optional[Fornecedor]:
        """Busca fornecedor existente por similaridade"""
        # Busca exata
        try:
            return Fornecedor.objects.get(razao_social=nome_limpo, ativo=True)
        except Fornecedor.DoesNotExist:
            pass
        
        # Busca por similaridade
        palavras_chave = nome_limpo.split()[:2]
        if len(palavras_chave) >= 2:
            filtro_busca = ' '.join(palavras_chave)
            
            candidatos = Fornecedor.objects.filter(
                razao_social__istartswith=filtro_busca,
                ativo=True
            )[:5]
            
            for candidato in candidatos:
                similaridade = cls._calcular_similaridade(nome_limpo, candidato.razao_social)
                
                if similaridade > 0.8:  # 80% de similaridade
                    logger.info(f"Fornecedor similar encontrado: {candidato.codigo} "
                              f"(similaridade: {similaridade:.2f})")
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
        return intersecao / min(len(set1), len(set2))
    
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
                origem_historico=historico_original[:500]
            )
            
            logger.info(f"Fornecedor criado automaticamente: {codigo_final} - {nome_limpo}")
            return fornecedor
            
        except Exception as e:
            logger.error(f"Erro ao criar fornecedor {nome_limpo}: {str(e)}")
            return None
    
    @classmethod
    def _gerar_codigo_fornecedor(cls, nome_limpo: str) -> str:
        """Gera código único para fornecedor"""
        # Código baseado em iniciais + hash
        palavras = [p for p in nome_limpo.split() if len(p) >= 2]
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


# Funções de conveniência para compatibilidade
def extrair_fornecedor_do_historico(historico: str) -> Optional[Fornecedor]:
    """
    Função de conveniência para extrair e buscar/criar fornecedor
    
    Args:
        historico: String do histórico contábil
        
    Returns:
        Instância de Fornecedor ou None
    """
    fornecedor_extraido = FornecedorExtractorService.extrair_fornecedor(historico)
    
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