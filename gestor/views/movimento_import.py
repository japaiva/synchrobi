# gestor/views/movimento_import.py - SISTEMA DE IMPORTAÇÃO CORRIGIDO

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

from core.models import Movimento, Unidade, CentroCusto, ContaContabil, ContaExterna, Fornecedor

logger = logging.getLogger('synchrobi')


# === CLASSE MELHORADA PARA EXTRAÇÃO DE FORNECEDORES ===

class FornecedorExtractorAvancado:
    """Extrator avançado de fornecedores com múltiplos padrões"""
    
    @staticmethod
    def extrair_numero_documento_melhorado(historico):
        """
        Extrai número do documento com padrões múltiplos
        """
        if not historico:
            return ''
        
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
    
    @staticmethod
    def extrair_fornecedor_melhorado(historico):
        """
        Extrai fornecedor com múltiplos padrões - VERSÃO APRIMORADA
        """
        if not historico:
            return None
        
        nome_fornecedor = None
        
        # PADRÃO 1: - NÚMERO NOME_FORNECEDOR -
        matches = re.findall(r'[-–]\s*\d+[\s\.]*([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&\.\-_]+?)[-–]', historico, re.IGNORECASE)
        if matches:
            candidato = matches[-1].strip()
            if FornecedorExtractorAvancado.validar_nome_fornecedor(candidato):
                nome_fornecedor = candidato
                logger.debug(f"Padrão 1 capturou: {nome_fornecedor}")
        
        # PADRÃO 2: NOME_FORNECEDOR NÚMERO - NÚMERO NOME_FORNECEDOR (repetição)
        if not nome_fornecedor:
            matches = re.findall(r'([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&\.\-_]{5,}?)\s+\d+\s*[-–]\s*\d+\s+\1', historico, re.IGNORECASE)
            if matches:
                candidato = matches[-1].strip()
                if FornecedorExtractorAvancado.validar_nome_fornecedor(candidato):
                    nome_fornecedor = candidato
                    logger.debug(f"Padrão 2 capturou: {nome_fornecedor}")
        
        # PADRÃO 3: - DESCRIÇÃO NOME_FORNECEDOR número
        if not nome_fornecedor:
            matches = re.findall(r'[-–]\s*(?:SERVICOS?\s+)?([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&\.\-_]+?)\s+(\d{4,})\s*$', historico, re.IGNORECASE)
            if matches:
                candidato = matches[-1][0].strip()
                if not re.search(r'SERVICOS?\s+ANTIFRAUDE|LANÇAMENTO|INTEGRAÇÃO', candidato, re.IGNORECASE):
                    if FornecedorExtractorAvancado.validar_nome_fornecedor(candidato):
                        nome_fornecedor = candidato
                        logger.debug(f"Padrão 3 capturou: {nome_fornecedor}")
        
        # PADRÃO 4: número NOME_FORNECEDOR número_longo
        if not nome_fornecedor:
            matches = re.findall(r'\b\d+\s+([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s]{8,}?)\s+\d{8,}', historico, re.IGNORECASE)
            if matches:
                candidato = matches[-1].strip()
                if FornecedorExtractorAvancado.validar_nome_fornecedor(candidato):
                    nome_fornecedor = candidato
                    logger.debug(f"Padrão 4 capturou: {nome_fornecedor}")
        
        # PADRÃO 5: Nome no final após traço (fallback)
        if not nome_fornecedor:
            matches = re.findall(r'[-–]\s*([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s&\.\-_]{10,}?)(?:\s+\d+)?\s*$', historico, re.IGNORECASE)
            if matches:
                candidato = matches[-1].strip()
                if FornecedorExtractorAvancado.validar_nome_fornecedor(candidato):
                    nome_fornecedor = candidato
                    logger.debug(f"Padrão 5 capturou: {nome_fornecedor}")
        
        if nome_fornecedor:
            nome_final = FornecedorExtractorAvancado.limpar_nome_fornecedor(nome_fornecedor)
            if FornecedorExtractorAvancado.validar_nome_fornecedor(nome_final):
                return nome_final
        
        return None
    
    @staticmethod
    def limpar_nome_fornecedor(nome):
        """Limpa e padroniza nome do fornecedor"""
        if not nome:
            return ''
        
        # Remover caracteres especiais, mas manter essenciais
        nome_limpo = re.sub(r'[^\w\s&\.\-]', ' ', nome)
        
        # Remover múltiplos espaços
        nome_limpo = re.sub(r'\s+', ' ', nome_limpo)
        
        # Converter para maiúsculo e remover espaços das bordas
        nome_limpo = nome_limpo.upper().strip()
        
        return nome_limpo
    
    @staticmethod
    def validar_nome_fornecedor(nome):
        """
        Validação rigorosa para nome de fornecedor
        """
        if not nome or len(nome) < 5:
            return False
        
        # Deve ter pelo menos 2 palavras significativas
        palavras = [p for p in nome.split() if len(p) >= 2]
        if len(palavras) < 2:
            return False
        
        # Não deve ser apenas números
        if nome.replace(' ', '').replace('.', '').replace('-', '').isdigit():
            return False
        
        # Não deve ter mais de 70% de números
        total_chars = len(nome.replace(' ', ''))
        digit_chars = sum(1 for c in nome if c.isdigit())
        if total_chars > 0 and (digit_chars / total_chars) > 0.7:
            return False
        
        # Lista de palavras que indicam que NÃO é um fornecedor
        palavras_blacklist = [
            'LANÇAMENTO', 'INTEGRAÇÃO', 'ORÇAMENTO', 'SERVICO', 'DESPESA',
            'MATERIAL', 'ESCRITORIO', 'VENDAS', 'LOJAS', 'DANFE', 'NFSERV',
            'VARIAVEIS', 'DESP', 'ACOES', 'REDES', 'SOCIAIS', 'SITES',
            'ANTIFRAUDE'
        ]
        
        nome_upper = nome.upper()
        for palavra in palavras_blacklist:
            if palavra in nome_upper:
                return False
        
        # Deve ter pelo menos uma palavra com 3+ caracteres
        palavras_longas = [p for p in palavras if len(p) >= 3]
        if len(palavras_longas) < 1:
            return False
        
        return True
    
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
    """Função atualizada usando novo extrator"""
    return FornecedorExtractorAvancado.extrair_numero_documento_melhorado(historico)

def extrair_fornecedor_do_historico(historico):
    """Função atualizada com melhor extração de fornecedores"""
    
    if not historico:
        return None
    
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

def processar_linha_excel_atualizada(linha_dados, numero_linha, nome_arquivo, data_inicio, data_fim):
    """
    Versão melhorada do processamento de linha Excel com proteção contra tipos incorretos
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
        historico = limpar_campo_seguro(linha_dados.get('Histórico'))
        
        # Campos opcionais
        codigo_projeto = limpar_campo_seguro(linha_dados.get('Cód. do projeto'))
        gerador = limpar_campo_seguro(linha_dados.get('Gerador'))
        rateio = limpar_campo_seguro(linha_dados.get('Rateio')) or 'N'
        
        # Converter e validar data
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, '%Y-%m-%d').date()
            except ValueError:
                try:
                    data = datetime.strptime(data, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    raise ValueError(f'Formato de data inválido: {data}')
        elif hasattr(data, 'date'):
            data = data.date()
        elif isinstance(data, datetime):
            data = data.date()
        elif isinstance(data, (int, float)) and not pd.isna(data):
            try:
                excel_epoch = date(1900, 1, 1)
                data = excel_epoch + timedelta(days=int(data) - 2)
            except:
                raise ValueError(f'Formato de data inválido: {data}')
        else:
            raise ValueError(f'Data não informada ou inválida: {data}')
        
        # Validar período
        if not (data_inicio <= data <= data_fim):
            return None, f'Data {data} fora do período {data_inicio} a {data_fim} - linha ignorada'
        
        # Converter valor
        if valor_bruto is None or valor_bruto == '' or pd.isna(valor_bruto):
            valor = Decimal('0.00')
        else:
            try:
                valor_decimal = Decimal(str(valor_bruto))
                valor = abs(valor_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except (ValueError, decimal.InvalidOperation):
                raise ValueError(f'Valor inválido: {valor_bruto}')
        
        # Validar códigos obrigatórios
        if not codigo_unidade:
            raise ValueError('Código da unidade não informado')
        if not codigo_centro_custo:
            raise ValueError('Código do centro de custo não informado')
        if not codigo_conta_contabil:
            raise ValueError('Código da conta contábil não informado')
        
        # Buscar entidades relacionadas
        unidade = Unidade.buscar_unidade_para_movimento(codigo_unidade)
        if not unidade:
            raise ValueError(f'Unidade não encontrada: {codigo_unidade}')
        
        try:
            centro_custo = CentroCusto.objects.get(codigo=codigo_centro_custo, ativo=True)
        except CentroCusto.DoesNotExist:
            return None, f'Centro de custo não encontrado: {codigo_centro_custo} - linha ignorada'
        
        try:
            conta_externa = ContaExterna.objects.get(codigo_externo=codigo_conta_contabil, ativa=True)
            conta_contabil = conta_externa.conta_contabil
        except ContaExterna.DoesNotExist:
            return None, f'Conta contábil não encontrada: {codigo_conta_contabil} - linha ignorada'
        
        # USAR NOVA EXTRAÇÃO MELHORADA com proteção
        numero_documento = extrair_numero_documento_do_historico(historico) if historico else ''
        fornecedor = extrair_fornecedor_do_historico(historico) if historico else None
        
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
        
        return movimento, None
        
    except Exception as e:
        error_msg = f'Linha {numero_linha}: {str(e)}'
        logger.error(f'Erro ao processar movimento: {error_msg}')
        return None, error_msg

def corrigir_estrutura_excel(arquivo):
    """Corrige problemas na estrutura do Excel"""
    try:
        df = pd.read_excel(arquivo, engine='openpyxl', header=0)
        
        # Verificar colunas necessárias
        colunas_necessarias = [
            'Mês', 'Ano', 'Data', 'Cód. da unidade', 'Cód. do centro de custo',
            'Cód. da conta contábil', 'Natureza (D/C/A)', 'Valor', 'Histórico'
        ]
        
        colunas_faltando = [col for col in colunas_necessarias if col not in df.columns]
        if colunas_faltando:
            raise ValueError(f'Colunas obrigatórias faltando: {", ".join(colunas_faltando)}')
        
        # Corrigir valores
        if 'Valor' in df.columns:
            df['Valor'] = df['Valor'].apply(lambda x: round(abs(float(x)), 2) if pd.notna(x) else 0.00)
        
        # Remover linhas vazias
        df = df.dropna(how='all')
        
        return df
        
    except Exception as e:
        logger.error(f'Erro ao corrigir estrutura do Excel: {str(e)}')
        raise

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
        # ADICIONE ESTA LINHA:
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
            df = corrigir_estrutura_excel(arquivo)
        except Exception as e:
            logger.error(f'Erro ao corrigir estrutura do Excel: {str(e)}')
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
                        unidade = Unidade.buscar_por_codigo_allstrategy(str(codigo_unidade))
                        if not unidade:
                            try:
                                unidade = Unidade.objects.get(codigo=str(codigo_unidade), ativa=True)
                            except Unidade.DoesNotExist:
                                pass
                        
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
@require_POST
def api_importar_movimentos_excel(request):
    """API para importação real dos movimentos"""
    
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
            df = corrigir_estrutura_excel(arquivo)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Erro na estrutura: {str(e)}'})
        
        logger.info(f'Iniciando importação MELHORADA de {len(df)} linhas')
        
        # Contadores
        movimentos_criados = 0
        fornecedores_criados = 0
        fornecedores_encontrados = 0
        erros = []
        erros_tipos = {}  # Dicionário para agrupar tipos de erro
        
        fornecedores_novos = set()
        
        for idx, linha in df.iterrows():
            try:
                linha_dict = linha.to_dict()
                
                movimento, erro = processar_linha_excel_atualizada(
                    linha_dict, idx + 2, arquivo.name, data_inicio, data_fim
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
                    
                    if movimentos_criados % 50 == 0:
                        logger.info(f'Processados {movimentos_criados} movimentos...')
                        
                elif erro:
                    # Agrupar erros similares de forma inteligente
                    if 'Conta contábil não encontrada:' in erro:
                        tipo_base = 'Conta contábil não encontrada'
                        codigo = erro.split(':')[1].strip().split(' ')[0]
                        chave_erro = f"{tipo_base}:{codigo}"
                    elif 'Centro de custo não encontrado:' in erro:
                        tipo_base = 'Centro de custo não encontrado'
                        codigo = erro.split(':')[1].strip().split(' ')[0]
                        chave_erro = f"{tipo_base}:{codigo}"
                    elif 'Unidade não encontrada:' in erro:
                        tipo_base = 'Unidade não encontrada'
                        codigo = erro.split(':')[1].strip().split(' ')[0]
                        chave_erro = f"{tipo_base}:{codigo}"
                    else:
                        tipo_base = erro.split(' - linha')[0] if ' - linha' in erro else erro.split(':')[0] if ':' in erro else erro
                        chave_erro = tipo_base
                    
                    if chave_erro not in erros_tipos:
                        erros_tipos[chave_erro] = {
                            'count': 1,
                            'exemplo': erro,
                            'tipo': tipo_base
                        }
                    else:
                        erros_tipos[chave_erro]['count'] += 1
                    
            except Exception as e:
                erro_msg = f'Linha {idx + 2}: Erro inesperado - {str(e)}'
                tipo_erro = 'Erro inesperado'
                
                if tipo_erro not in erros_tipos:
                    erros_tipos[tipo_erro] = {
                        'count': 1,
                        'exemplo': erro_msg,
                        'tipo': tipo_erro
                    }
                    logger.error(erro_msg)
                else:
                    erros_tipos[tipo_erro]['count'] += 1
        
        # Converter erros agrupados para lista final
        for chave, info in erros_tipos.items():
            if info['count'] == 1:
                erros.append(info['exemplo'])
            else:
                # Para múltiplas ocorrências, mostrar resumo
                if info['tipo'] == 'Conta contábil não encontrada':
                    codigo = chave.split(':')[1]
                    erros.append(f"Conta contábil não encontrada: {codigo} ({info['count']} ocorrências)")
                elif info['tipo'] == 'Centro de custo não encontrado':
                    codigo = chave.split(':')[1]
                    erros.append(f"Centro de custo não encontrado: {codigo} ({info['count']} ocorrências)")
                elif info['tipo'] == 'Unidade não encontrada':
                    codigo = chave.split(':')[1]
                    erros.append(f"Unidade não encontrada: {codigo} ({info['count']} ocorrências)")
                else:
                    erros.append(f"{info['tipo']} ({info['count']} ocorrências)")
        
        logger.info(
            f'Importação MELHORADA concluída: {movimentos_criados} movimentos, '
            f'{fornecedores_criados} fornecedores novos, {fornecedores_encontrados} existentes'
        )
        
        return JsonResponse({
            'success': True,
            'resultado': {
                'movimentos_removidos': movimentos_removidos,
                'movimentos_criados': movimentos_criados,
                'fornecedores_criados': fornecedores_criados,
                'fornecedores_encontrados': fornecedores_encontrados,
                'total_erros': len(erros),
                'nome_arquivo': arquivo.name,
                'melhorias_aplicadas': True
            },
            'erros': erros[:20],
            'tem_mais_erros': len(erros) > 20
        })
        
    except Exception as e:
        logger.error(f'Erro na importação: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': f'Erro na importação: {str(e)}'
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
    """API simplificada que mostra TODOS os códigos específicos que falharam"""
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
        
        # Limpar período existente
        movimentos_removidos = Movimento.objects.filter(
            data__gte=data_inicio, data__lte=data_fim
        ).count()
        
        Movimento.objects.filter(data__gte=data_inicio, data__lte=data_fim).delete()
        
        # Processar linhas
        total_linhas = len(df)
        movimentos_criados = 0
        fornecedores_criados = 0
        
        # Sets para coletar códigos únicos que falharam
        contas_nao_encontradas = set()
        centros_nao_encontrados = set()
        unidades_nao_encontradas = set()
        outros_erros = []
        
        for idx, linha in df.iterrows():
            try:
                linha_dict = linha.to_dict()
                
                movimento, erro = processar_linha_excel_atualizada(
                    linha_dict, idx + 2, arquivo.name, data_inicio, data_fim
                )
                
                if movimento:
                    movimentos_criados += 1
                    if movimento.fornecedor and movimento.fornecedor.criado_automaticamente:
                        fornecedores_criados += 1
                elif erro:
                    if 'fora do período' in erro:
                        continue  # Ignorar silenciosamente
                    
                    # Extrair código específico do erro
                    if 'Conta contábil não encontrada:' in erro:
                        codigo = erro.split(':')[1].strip().split(' ')[0]
                        contas_nao_encontradas.add(codigo)
                    elif 'Centro de custo não encontrado:' in erro:
                        codigo = erro.split(':')[1].strip().split(' ')[0]
                        centros_nao_encontrados.add(codigo)
                    elif 'Unidade não encontrada:' in erro:
                        codigo = erro.split(':')[1].strip().split(' ')[0]
                        unidades_nao_encontradas.add(codigo)
                    else:
                        outros_erros.append(erro)
                        
            except Exception as e:
                outros_erros.append(f"Linha {idx + 2}: {str(e)}")
        
        # Montar lista de erros com todos os códigos
        erros_resumo = []
        
        if contas_nao_encontradas:
            erros_resumo.append(f"Contas contábeis não encontradas ({len(contas_nao_encontradas)}): {', '.join(sorted(contas_nao_encontradas))}")
        
        if centros_nao_encontrados:
            erros_resumo.append(f"Centros de custo não encontrados ({len(centros_nao_encontrados)}): {', '.join(sorted(centros_nao_encontrados))}")
        
        if unidades_nao_encontradas:
            erros_resumo.append(f"Unidades não encontradas ({len(unidades_nao_encontradas)}): {', '.join(sorted(unidades_nao_encontradas))}")
        
        if outros_erros:
            erros_resumo.append(f"Outros erros ({len(outros_erros)}): {', '.join(outros_erros[:10])}")
        
        # Calcular total estimado de erros
        total_erros_estimado = len(contas_nao_encontradas) * 50 + len(centros_nao_encontrados) * 10 + len(unidades_nao_encontradas) * 5 + len(outros_erros)
        
        # Resultado final
        resultado = {
            'success': True,
            'movimentos_removidos': movimentos_removidos,
            'movimentos_criados': movimentos_criados,
            'fornecedores_criados': fornecedores_criados,
            'total_processado': total_linhas,
            'erros_count': total_erros_estimado,
            'erros_resumo': erros_resumo,
            'arquivo': arquivo.name
        }
        
        logger.info(f"Importação concluída: {movimentos_criados} movimentos, {total_erros_estimado} erros")
        
        return JsonResponse(resultado)
        
    except Exception as e:
        logger.error(f"Erro na importação: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erro durante importação: {str(e)}'
        })