# gestor/views/movimento_import.py - SISTEMA DE IMPORTAÇÃO COMPLETO

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime, date, timedelta
import logging
import pandas as pd
import decimal
import re
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

from core.models import Movimento, Unidade, CentroCusto, ContaContabil, ContaExterna, Fornecedor

logger = logging.getLogger('synchrobi')


# === CLASSE MELHORADA PARA EXTRAÇÃO DE FORNECEDORES ===

class FornecedorExtractorAvancado:
    """Extrator avançado de fornecedores com múltiplos padrões e limpeza de blacklist"""
    
    @staticmethod
    def limpar_blacklist_do_historico(historico):
        """Remove palavras da blacklist antes de tentar extrair fornecedor"""
        if not historico or not isinstance(historico, str):
            return ''
        
        palavras_blacklist = [
            'LANÇAMENTO', 'INTEGRAÇÃO', 'ORÇAMENTO', 'SERVICO', 'DESPESA',
            'MATERIAL', 'ESCRITORIO', 'VENDAS', 'LOJAS', 'DANFE', 'NFSERV',
            'VARIAVEIS', 'DESP', 'ACOES', 'REDES', 'SOCIAIS', 'SITES',
            'ANTIFRAUDE', 'ND'  # Adicionado ND conforme solicitado
        ]
        
        historico_limpo = historico
        for palavra in palavras_blacklist:
            # Remove a palavra mas mantém a estrutura
            historico_limpo = re.sub(rf'\b{palavra}\b', '', historico_limpo, flags=re.IGNORECASE)
        
        # Limpar espaços extras e pontuações órfãs
        historico_limpo = re.sub(r'\s+', ' ', historico_limpo)
        historico_limpo = re.sub(r'\s*-\s*-\s*', ' - ', historico_limpo)  # Corrigir traços duplos
        
        return historico_limpo.strip()

    @staticmethod
    def extrair_numero_documento_melhorado(historico):
        """
        Extrai número do documento com padrões múltiplos - COM PROTEÇÃO
        """
        if not historico or not isinstance(historico, str) or not historico.strip():
            return ''
        
        try:
            # PADRÃO 1: - NÚMERO NOME -
            matches = re.findall(r'[-–]\s*(\d+)[\s\.]*[A-ZÀ-Ÿ]', historico, re.IGNORECASE)
            if matches:
                return matches[-1].strip()
            
            # PADRÃO 2: NOME NÚMERO - NÚMERO NOME (número repetido)
            matches = re.findall(r'([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&\.\-_]+?)\s+(\d+)\s*[-–]\s*\2\s+', historico, re.IGNORECASE)
            if matches:
                return matches[-1][1].strip()
            
            # PADRÃO 3: Número isolado no final após nome
            matches = re.findall(r'([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&\.\-_]+?)\s+(\d{4,})\s*$', historico.strip())
            if matches:
                return matches[-1][1].strip()
            
            # PADRÃO 4: número NOME número_longo
            matches = re.findall(r'\b(\d+)\s+[A-ZÀ-Ÿ][A-ZÀ-Ÿ\s]{3,}?\s+\d{8,}', historico, re.IGNORECASE)
            if matches:
                return matches[-1].strip()
            
            # PADRÃO 5: - número CPF NOME - (pessoas físicas - pegar o primeiro número)
            matches = re.findall(r'[-–]\s*(\d+)\s+\d{2}\.\d{3}\.\d{3}\s+[A-ZÀ-Ÿ]', historico, re.IGNORECASE)
            if matches:
                return matches[-1].strip()
            
            # FALLBACK: Qualquer sequência de 3+ dígitos
            numeros = re.findall(r'\b(\d{3,})\b', historico)
            if numeros:
                numeros_filtrados = [n for n in numeros if 4 <= len(n) <= 8]
                if numeros_filtrados:
                    return numeros_filtrados[-1]
                else:
                    return max(numeros, key=len)
            
            return ''
            
        except Exception as e:
            logger.warning(f'Erro na extração de documento: {str(e)}')
            return ''

    @staticmethod
    def extrair_fornecedor_melhorado(historico):
        """
        Extrai fornecedor APÓS limpar blacklist - VERSÃO OTIMIZADA
        """
        if not historico or not isinstance(historico, str) or not historico.strip():
            return None
        
        try:
            # PRIMEIRO: Limpar palavras da blacklist
            historico_limpo = FornecedorExtractorAvancado.limpar_blacklist_do_historico(historico)
            
            if not historico_limpo or len(historico_limpo.strip()) < 10:
                return None
            
            nome_fornecedor = None
            
            # PADRÃO PRINCIPAL: Fornecedor após número e/ou ponto e vírgula
            # Padrão 1: - número; NOME; (mais comum)
            if not nome_fornecedor:
                matches = re.findall(r'[-–]\s*\d+;\s*([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&/\.\-_]+?);\s*', historico_limpo, re.IGNORECASE)
                if matches:
                    candidato = matches[-1].strip()
                    if FornecedorExtractorAvancado.validar_nome_fornecedor_flexivel(candidato):
                        nome_fornecedor = candidato
                        logger.debug(f"Padrão 1 (após número;) capturou: {nome_fornecedor}")
            
            # Padrão 2: ; NOME; (sem número inicial)
            if not nome_fornecedor:
                matches = re.findall(r';\s*([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&/\.\-_]{8,}?);\s*', historico_limpo, re.IGNORECASE)
                if matches:
                    candidato = matches[-1].strip()
                    if FornecedorExtractorAvancado.validar_nome_fornecedor_flexivel(candidato):
                        nome_fornecedor = candidato
                        logger.debug(f"Padrão 2 (;NOME;) capturou: {nome_fornecedor}")
            
            # Padrão 3: - número NOME (sem ponto e vírgula)
            if not nome_fornecedor:
                matches = re.findall(r'[-–]\s*\d+\s+([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&/\.\-_]{8,}?)(?:\s*[-–]|$)', historico_limpo, re.IGNORECASE)
                if matches:
                    candidato = matches[-1].strip()
                    if FornecedorExtractorAvancado.validar_nome_fornecedor_flexivel(candidato):
                        nome_fornecedor = candidato
                        logger.debug(f"Padrão 3 (após número) capturou: {nome_fornecedor}")
            
            # Padrão 4: número NOME número_longo (padrão original mantido)
            if not nome_fornecedor:
                matches = re.findall(r'\b\d+\s+([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&/\.\-_]{8,}?)\s+\d{8,}', historico_limpo, re.IGNORECASE)
                if matches:
                    candidato = matches[-1].strip()
                    if FornecedorExtractorAvancado.validar_nome_fornecedor_flexivel(candidato):
                        nome_fornecedor = candidato
                        logger.debug(f"Padrão 4 (número longo) capturou: {nome_fornecedor}")
            
            # Padrão 5: Nome repetido (NOME número - número NOME)
            if not nome_fornecedor:
                matches = re.findall(r'([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&/\.\-_]{8,}?)\s+\d+\s*[-–]\s*\d+\s+\1', historico_limpo, re.IGNORECASE)
                if matches:
                    candidato = matches[-1].strip()
                    if FornecedorExtractorAvancado.validar_nome_fornecedor_flexivel(candidato):
                        nome_fornecedor = candidato
                        logger.debug(f"Padrão 5 (repetido) capturou: {nome_fornecedor}")
            
            if nome_fornecedor:
                nome_final = FornecedorExtractorAvancado.limpar_nome_fornecedor(nome_fornecedor)
                if FornecedorExtractorAvancado.validar_nome_fornecedor_flexivel(nome_final):
                    return nome_final
            
            return None
            
        except Exception as e:
            logger.warning(f'Erro na extração de fornecedor: {str(e)}')
            return None

    @staticmethod
    def limpar_nome_fornecedor(nome):
        """Limpa e padroniza nome do fornecedor"""
        if not nome:
            return ''
        
        # Remover caracteres especiais, mas manter essenciais
        nome_limpo = re.sub(r'[^\w\s&\.\-/]', ' ', nome)
        
        # Remover múltiplos espaços
        nome_limpo = re.sub(r'\s+', ' ', nome_limpo)
        
        # Converter para maiúsculo e remover espaços das bordas
        nome_limpo = nome_limpo.upper().strip()
        
        return nome_limpo

    @staticmethod
    def validar_nome_fornecedor_flexivel(nome):
        """
        Validação mais flexível para nomes de fornecedor
        """
        if not nome or not isinstance(nome, str) or len(nome.strip()) < 5:
            return False
        
        try:
            nome = nome.strip()
            
            # Deve ter pelo menos 2 palavras com 2+ caracteres
            palavras = [p for p in nome.split() if len(p) >= 2]
            if len(palavras) < 2:
                return False
            
            # Não deve ser apenas números
            if nome.replace(' ', '').replace('.', '').replace('-', '').replace('/', '').isdigit():
                return False
            
            # Não deve ter mais de 80% de números (mais flexível)
            total_chars = len(nome.replace(' ', ''))
            digit_chars = sum(1 for c in nome if c.isdigit())
            if total_chars > 0 and (digit_chars / total_chars) > 0.8:
                return False
            
            # Blacklist reduzida - apenas termos técnicos
            palavras_blacklist_validacao = [
                'SISTEMA', 'AUTOMATICO', 'PROCESSAMENTO', 'CALCULO'
            ]
            
            nome_upper = nome.upper()
            for palavra in palavras_blacklist_validacao:
                if palavra in nome_upper:
                    return False
            
            # Aceitar qualquer nome que passe nos critérios básicos
            return True
            
        except Exception as e:
            logger.warning(f'Erro na validação de nome: {str(e)}')
            return False

    @staticmethod
    def buscar_fornecedor_existente(nome_limpo):
        """Busca fornecedor existente com fuzzy matching básico"""
        
        # Busca exata primeiro
        try:
            return Fornecedor.objects.get(razao_social=nome_limpo, ativo=True)
        except Fornecedor.DoesNotExist:
            pass
        
        # Busca por similaridade
        inicio = nome_limpo[:20]
        
        candidatos = Fornecedor.objects.filter(
            razao_social__istartswith=inicio,
            ativo=True
        )
        
        for candidato in candidatos:
            # Similaridade básica baseada em palavras comuns
            palavras_originais = set(nome_limpo.split())
            palavras_candidato = set(candidato.razao_social.split())
            
            if palavras_originais and palavras_candidato:
                intersecao = len(palavras_originais & palavras_candidato)
                uniao = len(palavras_originais | palavras_candidato)
                similaridade = intersecao / uniao if uniao > 0 else 0
                
                if similaridade > 0.7:
                    logger.info(f"Fornecedor similar encontrado: {candidato.codigo} (similaridade: {similaridade:.2f})")
                    return candidato
        
        return None

    @staticmethod
    def criar_fornecedor_automatico(nome_limpo, historico_original=''):
        """Cria novo fornecedor com código otimizado"""
        
        # Gerar código baseado no nome
        palavras = [p for p in nome_limpo.split() if len(p) >= 2]
        iniciais = ''.join([palavra[0] for palavra in palavras[:4]])
        
        if len(iniciais) < 3:
            iniciais = (nome_limpo.replace(' ', '')[:4]).ljust(4, 'X')
        
        # Hash do nome para evitar conflitos
        import hashlib
        hash_nome = hashlib.md5(nome_limpo.encode()).hexdigest()[:3].upper()
        codigo_base = f"{iniciais}{hash_nome}"
        
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
        
        try:
            fornecedor = Fornecedor.objects.create(
                codigo=codigo_final,
                razao_social=nome_limpo,
                criado_automaticamente=True,
                origem_historico=historico_original[:500]
            )
            
            logger.info(f"Novo fornecedor criado: {codigo_final} - {nome_limpo}")
            return fornecedor
            
        except Exception as e:
            logger.error(f"Erro ao criar fornecedor {nome_limpo}: {str(e)}")
            return None


# === FUNÇÕES ATUALIZADAS DE PROCESSAMENTO ===

def extrair_numero_documento_do_historico(historico):
    """Função atualizada usando novo extrator com proteção"""
    if not historico or not historico.strip():
        return ''
    
    try:
        return FornecedorExtractorAvancado.extrair_numero_documento_melhorado(historico)
    except Exception as e:
        logger.warning(f'Erro na extração de documento: {str(e)}')
        return ''

def extrair_fornecedor_do_historico(historico):
    """Função atualizada com melhor extração de fornecedores e proteção contra erros"""
    
    if not historico or not historico.strip():
        return None
    
    try:
        # Extrair nome do fornecedor
        nome_fornecedor = FornecedorExtractorAvancado.extrair_fornecedor_melhorado(historico)
        
        if not nome_fornecedor:
            return None
        
        # Buscar fornecedor existente
        fornecedor_existente = FornecedorExtractorAvancado.buscar_fornecedor_existente(nome_fornecedor)
        if fornecedor_existente:
            return fornecedor_existente
        
        # Criar novo fornecedor
        return FornecedorExtractorAvancado.criar_fornecedor_automatico(nome_fornecedor, historico)
        
    except Exception as e:
        logger.warning(f'Erro na extração de fornecedor: {str(e)}')
        return None


# === CLASSE PARA COLETA DETALHADA DE ERROS ===

class ErrosDetalhados:
    """Classe para coletar e organizar erros detalhados com códigos específicos"""
    
    def __init__(self):
        self.contas_nao_encontradas = defaultdict(int)
        self.centros_nao_encontrados = defaultdict(int)
        self.unidades_nao_encontradas = defaultdict(int)
        self.outros_erros = defaultdict(int)
        self.linhas_fora_periodo = 0
        self.valores_invalidos = defaultdict(int)
        self.datas_invalidas = defaultdict(int)
    
    def adicionar_conta_nao_encontrada(self, codigo):
        """Registra código de conta contábil não encontrado"""
        self.contas_nao_encontradas[str(codigo)] += 1
    
    def adicionar_centro_nao_encontrado(self, codigo):
        """Registra código de centro de custo não encontrado"""
        self.centros_nao_encontrados[str(codigo)] += 1
    
    def adicionar_unidade_nao_encontrada(self, codigo):
        """Registra código de unidade não encontrado"""
        self.unidades_nao_encontradas[str(codigo)] += 1
    
    def adicionar_valor_invalido(self, valor, linha):
        """Registra valor inválido"""
        chave = f"Valor '{valor}' na linha {linha}"
        self.valores_invalidos[chave] += 1
    
    def adicionar_data_invalida(self, data, linha):
        """Registra data inválida"""
        chave = f"Data '{data}' na linha {linha}"
        self.datas_invalidas[chave] += 1
    
    def adicionar_outro_erro(self, erro):
        """Registra outros tipos de erro"""
        # Limpar número da linha para agrupar erros similares
        erro_limpo = re.sub(r'Linha \d+:', 'Linha X:', erro)
        erro_limpo = re.sub(r'linha \d+', 'linha X', erro_limpo)
        self.outros_erros[erro_limpo] += 1
    
    def linha_fora_periodo(self):
        """Incrementa contador de linhas fora do período"""
        self.linhas_fora_periodo += 1
    
    def get_total_erros(self):
        """Retorna total de erros"""
        return (
            sum(self.contas_nao_encontradas.values()) +
            sum(self.centros_nao_encontrados.values()) +
            sum(self.unidades_nao_encontradas.values()) +
            sum(self.valores_invalidos.values()) +
            sum(self.datas_invalidas.values()) +
            sum(self.outros_erros.values())
        )
    
    def get_resumo_detalhado(self):
        """Retorna resumo detalhado para a interface"""
        resumo = {
            'total_erros': self.get_total_erros(),
            'linhas_fora_periodo': self.linhas_fora_periodo,
            'categorias': []
        }
        
        # CONTAS CONTÁBEIS NÃO ENCONTRADAS - COM TODOS OS CÓDIGOS
        if self.contas_nao_encontradas:
            contas_ordenadas = sorted(
                self.contas_nao_encontradas.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            categoria_contas = {
                'tipo': 'Contas Contábeis Não Encontradas',
                'total_ocorrencias': sum(self.contas_nao_encontradas.values()),
                'total_codigos': len(self.contas_nao_encontradas),
                'detalhes': [
                    {
                        'codigo': codigo,
                        'ocorrencias': count,
                        'descricao': f"Código {codigo}: {count} movimento{'s' if count > 1 else ''}"
                    }
                    for codigo, count in contas_ordenadas
                ]
            }
            resumo['categorias'].append(categoria_contas)
        
        # CENTROS DE CUSTO NÃO ENCONTRADOS - COM TODOS OS CÓDIGOS
        if self.centros_nao_encontrados:
            centros_ordenados = sorted(
                self.centros_nao_encontrados.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            categoria_centros = {
                'tipo': 'Centros de Custo Não Encontrados',
                'total_ocorrencias': sum(self.centros_nao_encontrados.values()),
                'total_codigos': len(self.centros_nao_encontrados),
                'detalhes': [
                    {
                        'codigo': codigo,
                        'ocorrencias': count,
                        'descricao': f"Código {codigo}: {count} movimento{'s' if count > 1 else ''}"
                    }
                    for codigo, count in centros_ordenados
                ]
            }
            resumo['categorias'].append(categoria_centros)
        
        # UNIDADES NÃO ENCONTRADAS - COM TODOS OS CÓDIGOS
        if self.unidades_nao_encontradas:
            unidades_ordenadas = sorted(
                self.unidades_nao_encontradas.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            categoria_unidades = {
                'tipo': 'Unidades Não Encontradas',
                'total_ocorrencias': sum(self.unidades_nao_encontradas.values()),
                'total_codigos': len(self.unidades_nao_encontradas),
                'detalhes': [
                    {
                        'codigo': codigo,
                        'ocorrencias': count,
                        'descricao': f"Código {codigo}: {count} movimento{'s' if count > 1 else ''}"
                    }
                    for codigo, count in unidades_ordenadas
                ]
            }
            resumo['categorias'].append(categoria_unidades)
        
        # VALORES INVÁLIDOS
        if self.valores_invalidos:
            valores_ordenados = sorted(
                self.valores_invalidos.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            categoria_valores = {
                'tipo': 'Valores Inválidos',
                'total_ocorrencias': sum(self.valores_invalidos.values()),
                'total_codigos': len(self.valores_invalidos),
                'detalhes': [
                    {
                        'codigo': erro,
                        'ocorrencias': count,
                        'descricao': f"{erro}: {count} ocorrência{'s' if count > 1 else ''}"
                    }
                    for erro, count in valores_ordenados
                ]
            }
            resumo['categorias'].append(categoria_valores)
        
        # DATAS INVÁLIDAS
        if self.datas_invalidas:
            datas_ordenadas = sorted(
                self.datas_invalidas.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            categoria_datas = {
                'tipo': 'Datas Inválidas',
                'total_ocorrencias': sum(self.datas_invalidas.values()),
                'total_codigos': len(self.datas_invalidas),
                'detalhes': [
                    {
                        'codigo': erro,
                        'ocorrencias': count,
                        'descricao': f"{erro}: {count} ocorrência{'s' if count > 1 else ''}"
                    }
                    for erro, count in datas_ordenadas
                ]
            }
            resumo['categorias'].append(categoria_datas)
        
        # OUTROS ERROS
        if self.outros_erros:
            outros_ordenados = sorted(
                self.outros_erros.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            categoria_outros = {
                'tipo': 'Outros Erros',
                'total_ocorrencias': sum(self.outros_erros.values()),
                'total_codigos': len(self.outros_erros),
                'detalhes': [
                    {
                        'codigo': erro,
                        'ocorrencias': count,
                        'descricao': f"{erro}: {count} ocorrência{'s' if count > 1 else ''}"
                    }
                    for erro, count in outros_ordenados
                ]
            }
            resumo['categorias'].append(categoria_outros)
        
        return resumo


def processar_linha_excel_com_coleta_erros(linha_dados, numero_linha, nome_arquivo, data_inicio, data_fim, coletores_erros):
    """
    Versão melhorada que coleta erros detalhados por código específico
    """
    try:
        # Função auxiliar para limpar campos
        def limpar_campo_seguro(campo):
            if campo is None or pd.isna(campo):
                return ''
            campo_str = str(campo).strip()
            if campo_str.lower() in ['nan', 'none', '']:
                return ''
            return campo_str
        
        # Extrair dados básicos com proteção
        mes = int(linha_dados.get('Mês', 0)) if pd.notna(linha_dados.get('Mês')) else 0
        ano = int(linha_dados.get('Ano', 0)) if pd.notna(linha_dados.get('Ano')) else 0
        data = linha_dados.get('Data')
        codigo_unidade = limpar_campo_seguro(linha_dados.get('Cód. da unidade'))
        codigo_centro_custo = limpar_campo_seguro(linha_dados.get('Cód. do centro de custo'))
        codigo_conta_contabil = limpar_campo_seguro(linha_dados.get('Cód. da conta contábil'))
        natureza = limpar_campo_seguro(linha_dados.get('Natureza (D/C/A)')) or 'D'
        valor_bruto = linha_dados.get('Valor', 0)
        
        # Campos do histórico com validação mais rigorosa
        historico = linha_dados.get('Histórico')
        if historico is None or pd.isna(historico):
            historico = ''
        else:
            historico = str(historico).strip()
            # Se após strip ainda está vazio, definir como string vazia
            if not historico:
                historico = ''
        
        # Campos opcionais
        codigo_projeto = limpar_campo_seguro(linha_dados.get('Cód. do projeto'))
        gerador = limpar_campo_seguro(linha_dados.get('Gerador'))
        rateio = limpar_campo_seguro(linha_dados.get('Rateio')) or 'N'
        
        # Converter e validar data
        try:
            if isinstance(data, str):
                try:
                    data = datetime.strptime(data, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        data = datetime.strptime(data, '%Y-%m-%d %H:%M:%S').date()
                    except ValueError:
                        coletores_erros.adicionar_data_invalida(data, numero_linha)
                        return None
            elif hasattr(data, 'date'):
                data = data.date()
            elif isinstance(data, datetime):
                data = data.date()
            elif isinstance(data, (int, float)) and not pd.isna(data):
                try:
                    excel_epoch = date(1900, 1, 1)
                    data = excel_epoch + timedelta(days=int(data) - 2)
                except:
                    coletores_erros.adicionar_data_invalida(data, numero_linha)
                    return None
            else:
                coletores_erros.adicionar_data_invalida(data, numero_linha)
                return None
        except Exception:
            coletores_erros.adicionar_data_invalida(data, numero_linha)
            return None
        
        # Validar período
        if not (data_inicio <= data <= data_fim):
            coletores_erros.linha_fora_periodo()
            return None
        
        # Converter valor
        try:
            if valor_bruto is None or valor_bruto == '' or pd.isna(valor_bruto):
                valor = Decimal('0.00')
            else:
                valor_decimal = Decimal(str(valor_bruto))
                valor = abs(valor_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (ValueError, decimal.InvalidOperation):
            coletores_erros.adicionar_valor_invalido(valor_bruto, numero_linha)
            return None
        
        # Validar códigos obrigatórios (histórico NÃO é obrigatório)
        if not codigo_unidade:
            coletores_erros.adicionar_outro_erro(f'Linha {numero_linha}: Código da unidade não informado')
            return None
        if not codigo_centro_custo:
            coletores_erros.adicionar_outro_erro(f'Linha {numero_linha}: Código do centro de custo não informado')
            return None
        if not codigo_conta_contabil:
            coletores_erros.adicionar_outro_erro(f'Linha {numero_linha}: Código da conta contábil não informado')
            return None
        
        # Buscar entidades relacionadas COM COLETA DETALHADA DE ERROS
        unidade = Unidade.buscar_unidade_para_movimento(codigo_unidade)
        if not unidade:
            coletores_erros.adicionar_unidade_nao_encontrada(codigo_unidade)
            return None
        
        try:
            centro_custo = CentroCusto.objects.get(codigo=codigo_centro_custo, ativo=True)
        except CentroCusto.DoesNotExist:
            coletores_erros.adicionar_centro_nao_encontrado(codigo_centro_custo)
            return None
        
        try:
            conta_externa = ContaExterna.objects.get(codigo_externo=codigo_conta_contabil, ativa=True)
            conta_contabil = conta_externa.conta_contabil
        except ContaExterna.DoesNotExist:
            coletores_erros.adicionar_conta_nao_encontrada(codigo_conta_contabil)
            return None
        
        # Extrair fornecedor com proteção contra histórico vazio - NOVA LÓGICA
        numero_documento = ''
        fornecedor = None
        
        # Se histórico está em branco, não busca nada - apenas prossegue
        if historico and historico.strip():
            try:
                numero_documento = extrair_numero_documento_do_historico(historico)
                fornecedor = extrair_fornecedor_do_historico(historico)
            except Exception as e:
                logger.warning(f'Erro na extração do histórico linha {numero_linha}: {str(e)}')
                # Continua sem fornecedor se houver erro na extração
        # Se histórico em branco, simplesmente continua sem tentar extrair nada
        
        # Criar movimento
        movimento = Movimento.objects.create(
            mes=mes,
            ano=ano,
            data=data,
            unidade=unidade,
            centro_custo=centro_custo,
            conta_contabil=conta_contabil,
            fornecedor=fornecedor,
            documento=numero_documento,
            natureza=natureza,
            valor=valor,
            historico=historico,
            codigo_projeto=codigo_projeto,
            gerador=gerador,
            rateio=rateio,
            arquivo_origem=nome_arquivo,
            linha_origem=numero_linha
        )
        
        return movimento
        
    except Exception as e:
        coletores_erros.adicionar_outro_erro(f'Linha {numero_linha}: Erro inesperado - {str(e)}')
        logger.error(f'Erro ao processar movimento linha {numero_linha}: {str(e)}')
        return None


# === VIEWS DE IMPORTAÇÃO ===

@login_required
def movimento_importar(request):
    """Interface para importação de movimentos"""

    stats = {
        'unidades_ativas': Unidade.objects.filter(ativa=True).count(),
        'unidades_com_allstrategy': Unidade.objects.filter(
            ativa=True, 
            codigo_allstrategy__isnull=False
        ).exclude(codigo_allstrategy='').count(),
        'contas_externas_ativas': ContaExterna.objects.filter(ativa=True).count(),
        'centros_custo_ativos': CentroCusto.objects.filter(ativo=True).count(),
        'fornecedores_ativos': Fornecedor.objects.filter(ativo=True).count(),
        'total_movimentos': Movimento.objects.count(),
        'sistema_pronto': all([
            Unidade.objects.filter(ativa=True).exists(),
            CentroCusto.objects.filter(ativo=True).exists(),
            ContaExterna.objects.filter(ativa=True).exists(),
        ])
    }

    if stats['unidades_ativas'] > 0:
        stats['percentual_unidades_preparadas'] = round(
            (stats['unidades_com_allstrategy'] / stats['unidades_ativas'] * 100), 1
        )
    else:
        stats['percentual_unidades_preparadas'] = 0
    
    context = {
        'stats': stats,
        'ano_atual': datetime.now().year,
        'mes_atual': datetime.now().month
    }
    
    return render(request, 'gestor/movimento_importar.html', context)


@login_required
@require_POST
def api_preview_movimentos_excel(request):
    """API para preview dos movimentos com tratamento robusto de erros"""
    
    try:
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Nenhum arquivo foi enviado'})
        
        arquivo = request.FILES['arquivo']
        data_inicio_str = request.POST.get('data_inicio')
        data_fim_str = request.POST.get('data_fim')
        
        if not data_inicio_str or not data_fim_str:
            return JsonResponse({'success': False, 'error': 'Período não informado'})
        
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError as e:
            return JsonResponse({'success': False, 'error': f'Formato de data inválido: {str(e)}'})
        
        if not arquivo.name.endswith(('.xlsx', '.xls')):
            return JsonResponse({'success': False, 'error': 'Arquivo deve ser Excel (.xlsx ou .xls)'})
        
        try:
            df = pd.read_excel(arquivo, engine='openpyxl', header=0)
            df = df.dropna(how='all')
        except Exception as e:
            logger.error(f'Erro ao ler Excel: {str(e)}')
            return JsonResponse({'success': False, 'error': f'Erro na estrutura do arquivo: {str(e)}'})
        
        # Verificar se há dados
        if df.empty:
            return JsonResponse({'success': False, 'error': 'Arquivo está vazio ou não contém dados válidos'})
        
        # Preview das primeiras 15 linhas
        preview_linhas = df.head(15).to_dict('records')
        preview_results = []
        erros_encontrados = []
        fornecedores_novos = []
        linhas_no_periodo = 0
        linhas_serao_ignoradas = 0
        
        for idx, linha in enumerate(preview_linhas, 1):
            try:
                resultado = {
                    'linha': idx,
                    'dados': {
                        'mes': linha.get('Mês'),
                        'ano': linha.get('Ano'),
                        'data': linha.get('Data'),
                        'codigo_unidade': linha.get('Cód. da unidade'),
                        'codigo_centro': linha.get('Cód. do centro de custo'),
                        'codigo_conta': linha.get('Cód. da conta contábil'),
                        'valor': linha.get('Valor'),
                        'natureza': linha.get('Natureza (D/C/A)'),
                        'documento_extraido': '',
                        'fornecedor_extraido': ''
                    },
                    'validacoes': {},
                    'errors': [],
                    'warnings': [],
                    'no_periodo': False,
                    'sera_ignorada': False
                }
                
                # Verificar período
                try:
                    data_linha = linha.get('Data')
                    if isinstance(data_linha, str):
                        data_linha = datetime.strptime(data_linha, '%Y-%m-%d').date()
                    elif hasattr(data_linha, 'date'):
                        data_linha = data_linha.date()
                    elif isinstance(data_linha, datetime):
                        data_linha = data_linha.date()
                    
                    if data_inicio <= data_linha <= data_fim:
                        resultado['no_periodo'] = True
                        linhas_no_periodo += 1
                    else:
                        resultado['warnings'].append(f'Data {data_linha} fora do período - SERÁ IGNORADA')
                        resultado['sera_ignorada'] = True
                        linhas_serao_ignoradas += 1
                except Exception as e:
                    resultado['errors'].append(f'Data inválida: {str(e)} - SERÁ IGNORADA')
                    resultado['sera_ignorada'] = True
                    linhas_serao_ignoradas += 1
                
                # Usar NOVA EXTRAÇÃO para preview
                historico = linha.get('Histórico', '')
                if historico:
                    try:
                        numero_documento = extrair_numero_documento_do_historico(historico)
                        resultado['dados']['documento_extraido'] = numero_documento
                        
                        nome_fornecedor = FornecedorExtractorAvancado.extrair_fornecedor_melhorado(historico)
                        
                        if nome_fornecedor:
                            try:
                                fornecedor_existente = FornecedorExtractorAvancado.buscar_fornecedor_existente(nome_fornecedor)
                                
                                if fornecedor_existente:
                                    resultado['validacoes']['fornecedor'] = {
                                        'sera_criado': False,
                                        'detalhes': f"EXISTENTE: {fornecedor_existente.codigo} - {fornecedor_existente.razao_social}"
                                    }
                                    resultado['dados']['fornecedor_extraido'] = f"EXISTENTE: {fornecedor_existente.razao_social}"
                                else:
                                    resultado['validacoes']['fornecedor'] = {
                                        'sera_criado': True,
                                        'detalhes': f"NOVO: {nome_fornecedor}"
                                    }
                                    resultado['dados']['fornecedor_extraido'] = f"NOVO: {nome_fornecedor}"
                                    fornecedores_novos.append(nome_fornecedor)
                            except Exception as e:
                                logger.warning(f'Erro ao buscar fornecedor existente: {str(e)}')
                                resultado['warnings'].append('Erro ao verificar fornecedor existente')
                        else:
                            resultado['warnings'].append('Nenhum fornecedor identificado no histórico')
                    except Exception as e:
                        logger.warning(f'Erro na extração do histórico: {str(e)}')
                        resultado['warnings'].append(f'Erro na extração: {str(e)}')
                
                # Validações das outras entidades
                try:
                    codigo_unidade = linha.get('Cód. da unidade')
                    if codigo_unidade:
                        unidade = Unidade.buscar_unidade_para_movimento(str(codigo_unidade))
                        resultado['validacoes']['unidade'] = {
                            'encontrada': unidade is not None,
                            'detalhes': f"{unidade.codigo_display} - {unidade.nome}" if unidade else None
                        }
                        if not unidade:
                            resultado['errors'].append(f'Unidade não encontrada: {codigo_unidade}')
                            resultado['sera_ignorada'] = True
                            linhas_serao_ignoradas += 1
                    else:
                        resultado['errors'].append('Código da unidade não informado')
                        resultado['sera_ignorada'] = True
                        linhas_serao_ignoradas += 1
                except Exception as e:
                    resultado['errors'].append(f'Erro ao validar unidade: {str(e)}')
                    resultado['sera_ignorada'] = True
                    linhas_serao_ignoradas += 1
                
                # Validar centro de custo
                try:
                    codigo_centro = linha.get('Cód. do centro de custo')
                    if codigo_centro:
                        try:
                            centro = CentroCusto.objects.get(codigo=str(codigo_centro), ativo=True)
                            resultado['validacoes']['centro_custo'] = {
                                'encontrado': True,
                                'detalhes': f"{centro.codigo} - {centro.nome}"
                            }
                        except CentroCusto.DoesNotExist:
                            resultado['validacoes']['centro_custo'] = {'encontrado': False}
                            resultado['errors'].append(f'Centro de custo não encontrado: {codigo_centro}')
                            resultado['sera_ignorada'] = True
                            linhas_serao_ignoradas += 1
                    else:
                        resultado['errors'].append('Código do centro de custo não informado')
                        resultado['sera_ignorada'] = True
                        linhas_serao_ignoradas += 1
                except Exception as e:
                    resultado['errors'].append(f'Erro ao validar centro de custo: {str(e)}')
                    resultado['sera_ignorada'] = True
                    linhas_serao_ignoradas += 1
                
                # Validar conta contábil
                try:
                    codigo_conta = linha.get('Cód. da conta contábil')
                    if codigo_conta:
                        try:
                            conta_externa = ContaExterna.objects.get(codigo_externo=str(codigo_conta), ativa=True)
                            resultado['validacoes']['conta_contabil'] = {
                                'encontrada': True,
                                'detalhes': f"{conta_externa.conta_contabil.codigo} - {conta_externa.conta_contabil.nome}"
                            }
                        except ContaExterna.DoesNotExist:
                            resultado['validacoes']['conta_contabil'] = {'encontrada': False}
                            resultado['errors'].append(f'Conta contábil não encontrada: {codigo_conta}')
                            resultado['sera_ignorada'] = True
                            linhas_serao_ignoradas += 1
                    else:
                        resultado['errors'].append('Código da conta contábil não informado')
                        resultado['sera_ignorada'] = True
                        linhas_serao_ignoradas += 1
                except Exception as e:
                    resultado['errors'].append(f'Erro ao validar conta contábil: {str(e)}')
                    resultado['sera_ignorada'] = True
                    linhas_serao_ignoradas += 1
                
                if resultado['errors']:
                    erros_encontrados.extend(resultado['errors'])
                
                preview_results.append(resultado)
                
            except Exception as e:
                logger.error(f'Erro ao processar linha {idx}: {str(e)}')
                erros_encontrados.append(f'Linha {idx}: {str(e)}')
        
        # Contar total de linhas no período no arquivo inteiro
        total_linhas_periodo = 0
        try:
            for _, linha in df.iterrows():
                try:
                    data_linha = linha.get('Data')
                    if isinstance(data_linha, str):
                        data_linha = datetime.strptime(data_linha, '%Y-%m-%d').date()
                    elif hasattr(data_linha, 'date'):
                        data_linha = data_linha.date()
                    elif isinstance(data_linha, datetime):
                        data_linha = data_linha.date()
                    
                    if data_inicio <= data_linha <= data_fim:
                        total_linhas_periodo += 1
                except:
                    continue
        except Exception as e:
            logger.warning(f'Erro ao contar linhas no período: {str(e)}')
            total_linhas_periodo = 0
        
        # Remover duplicatas de fornecedores novos
        fornecedores_novos = list(set(fornecedores_novos))
        
        return JsonResponse({
            'success': True,
            'preview_results': preview_results,
            'stats': {
                'total_linhas_arquivo': len(df),
                'total_linhas_periodo': total_linhas_periodo,
                'linhas_preview': len(preview_results),
                'linhas_preview_periodo': linhas_no_periodo,
                'linhas_serao_ignoradas': linhas_serao_ignoradas,
                'total_erros': len(erros_encontrados),
                'fornecedores_novos': len(fornecedores_novos),
                'pode_importar': len(preview_results) > 0,
                'extrator_melhorado': True
            },
            'fornecedores_novos': fornecedores_novos[:10],
            'nome_arquivo': arquivo.name,
            'periodo': f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
            'erros_encontrados': erros_encontrados[:10]
        })
        
    except Exception as e:
        logger.error(f'Erro crítico no preview: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Erro interno no servidor: {str(e)}'
        })


@login_required
def api_validar_periodo_importacao(request):
    """API para validar período"""
    
    try:
        data_inicio_str = request.GET.get('data_inicio')
        data_fim_str = request.GET.get('data_fim')
        
        if not data_inicio_str or not data_fim_str:
            return JsonResponse({'success': False, 'error': 'Período não informado'})
        
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Formato de data inválido'})
        
        movimentos_existentes = Movimento.objects.filter(
            data__gte=data_inicio,
            data__lte=data_fim
        ).count()
        
        return JsonResponse({
            'success': True,
            'periodo_valido': True,
            'movimentos_existentes': movimentos_existentes,
            'mensagem': f'Período {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")} - {movimentos_existentes} movimentos existentes serão removidos'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro na validação: {str(e)}'
        })


@login_required
@require_POST
def api_importar_movimentos_detalhado(request):
    """API de importação com detalhamento COMPLETO de todos os erros"""
    
    try:
        data_inicio_str = request.POST.get('data_inicio')
        data_fim_str = request.POST.get('data_fim')
        
        if not data_inicio_str or not data_fim_str:
            return JsonResponse({'success': False, 'error': 'Período não informado'})
        
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Formato de data inválido'})
        
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Arquivo não encontrado'})
        
        arquivo = request.FILES['arquivo']
        
        # Limpar período
        logger.info(f'Limpando período {data_inicio} a {data_fim}')
        movimentos_removidos = Movimento.objects.filter(
            data__gte=data_inicio,
            data__lte=data_fim
        ).count()
        
        Movimento.objects.filter(
            data__gte=data_inicio,
            data__lte=data_fim
        ).delete()
        
        # Processar arquivo
        try:
            df = pd.read_excel(arquivo, engine='openpyxl', header=0)
            df = df.dropna(how='all')
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Erro na estrutura: {str(e)}'})
        
        logger.info(f'Iniciando importação DETALHADA de {len(df)} linhas')
        
        # INICIALIZAR COLETOR DE ERROS DETALHADOS
        coletores_erros = ErrosDetalhados()
        
        # Contadores
        movimentos_criados = 0
        fornecedores_criados = 0
        fornecedores_encontrados = 0
        fornecedores_novos = set()
        
        for idx, linha in df.iterrows():
            try:
                linha_dict = linha.to_dict()
                
                movimento = processar_linha_excel_com_coleta_erros(
                    linha_dict, idx + 2, arquivo.name, data_inicio, data_fim, coletores_erros
                )
                
                if movimento:
                    movimentos_criados += 1
                    
                    if movimento.fornecedor:
                        if movimento.fornecedor.criado_automaticamente:
                            if movimento.fornecedor.codigo not in fornecedores_novos:
                                fornecedores_novos.add(movimento.fornecedor.codigo)
                                fornecedores_criados += 1
                        else:
                            fornecedores_encontrados += 1
                    
                    if movimentos_criados % 100 == 0:
                        logger.info(f'Processados {movimentos_criados} movimentos...')
                        
            except Exception as e:
                coletores_erros.adicionar_outro_erro(f'Linha {idx + 2}: Erro crítico - {str(e)}')
                logger.error(f'Erro crítico linha {idx + 2}: {str(e)}')
        
        # GERAR RESUMO DETALHADO COMPLETO
        resumo_detalhado = coletores_erros.get_resumo_detalhado()
        
        logger.info(
            f'Importação DETALHADA concluída: {movimentos_criados} movimentos, '
            f'{fornecedores_criados} fornecedores novos, {resumo_detalhado["total_erros"]} erros'
        )
        
        return JsonResponse({
            'success': True,
            'resultado': {
                'movimentos_removidos': movimentos_removidos,
                'movimentos_criados': movimentos_criados,
                'fornecedores_criados': fornecedores_criados,
                'fornecedores_encontrados': fornecedores_encontrados,
                'total_erros': resumo_detalhado['total_erros'],
                'linhas_fora_periodo': resumo_detalhado['linhas_fora_periodo'],
                'nome_arquivo': arquivo.name,
                'detalhamento_completo': True
            },
            'erros_detalhados': resumo_detalhado,
            'tem_detalhamento': True
        })
        
    except Exception as e:
        logger.error(f'Erro na importação detalhada: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': f'Erro na importação: {str(e)}'
        })


@login_required
def api_validar_periodo_simples(request):
    """Validação simples de período"""
    try:
        data_inicio_str = request.GET.get('data_inicio')
        data_fim_str = request.GET.get('data_fim')
        
        if not data_inicio_str or not data_fim_str:
            return JsonResponse({'success': False, 'periodo_valido': False})
        
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        
        movimentos_existentes = Movimento.objects.filter(
            data__gte=data_inicio, data__lte=data_fim
        ).count()
        
        return JsonResponse({
            'success': True,
            'movimentos_existentes': movimentos_existentes,
            'periodo_valido': True
        })
        
    except Exception:
        return JsonResponse({'success': False, 'periodo_valido': False})


@login_required
@require_POST
def api_importar_movimentos_simples(request):
    """API simplificada de fallback"""
    try:
        # Validar entrada
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Arquivo não enviado'})
        
        arquivo = request.FILES['arquivo']
        data_inicio_str = request.POST.get('data_inicio')
        data_fim_str = request.POST.get('data_fim')
        
        if not data_inicio_str or not data_fim_str:
            return JsonResponse({'success': False, 'error': 'Período não informado'})
        
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        
        # Ler arquivo
        df = pd.read_excel(arquivo, engine='openpyxl', header=0)
        df = df.dropna(how='all')
        
        # Verificar colunas essenciais
        colunas_obrigatorias = ['Data', 'Cód. da unidade', 'Cód. do centro de custo', 
                               'Cód. da conta contábil', 'Valor', 'Histórico']
        
        faltando = [col for col in colunas_obrigatorias if col not in df.columns]
        if faltando:
            return JsonResponse({
                'success': False, 
                'error': f'Colunas obrigatórias faltando: {", ".join(faltando)}'
            })
        
        # Usar a versão detalhada como padrão
        return api_importar_movimentos_detalhado(request)
        
    except Exception as e:
        logger.error(f"Erro na importação simples: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erro durante importação: {str(e)}'
        })