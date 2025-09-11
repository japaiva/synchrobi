# gestor/views/movimento.py - VERSÃO COMPLETA CORRIGIDA

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, date, timedelta
import logging
import pandas as pd
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import io
import decimal
from decimal import Decimal, ROUND_HALF_UP

from core.models import Movimento, Unidade, CentroCusto, ContaContabil, ContaExterna, Fornecedor
from core.forms import MovimentoForm

logger = logging.getLogger('synchrobi')

# === FUNÇÕES AUXILIARES PARA IMPORTAÇÃO ===

def extrair_fornecedor_do_historico(historico):
    """
    Extrai fornecedor do histórico ignorando números (que são documentos).
    Exemplo: "... - 826498 AUTOPEL AUTOMACAO COMERCIAL E INFORMATICA LTDA - ..."
    Extrai apenas: "AUTOPEL AUTOMACAO COMERCIAL E INFORMATICA LTDA"
    """
    import re
    import hashlib
    
    if not historico:
        return None
    
    # Busca por "- NÚMERO NOME_COMPLETO -" mas pega apenas o NOME
    matches = re.findall(r'- \d+\s+([A-Z\s&\.\-_]+?) -', historico)
    
    if not matches:
        return None
    
    # Pegar o último match (mais provável de ser o fornecedor principal)
    nome = matches[-1].strip()
    
    if len(nome) < 3:  # Nome muito curto
        return None
    
    # Limpar e normalizar o nome
    nome_limpo = nome.upper().strip()
    
    # Gerar código automático baseado no nome (primeiras letras + hash)
    # Pegar primeiras letras de cada palavra
    palavras = nome_limpo.split()
    iniciais = ''.join([palavra[0] for palavra in palavras if palavra])[:4]
    
    # Adicionar hash do nome para evitar duplicatas
    hash_nome = hashlib.md5(nome_limpo.encode()).hexdigest()[:4].upper()
    codigo_auto = f"{iniciais}{hash_nome}"
    
    # Verificar se fornecedor já existe pelo nome
    try:
        fornecedor = Fornecedor.objects.get(razao_social=nome_limpo)
        logger.info(f'Fornecedor existente encontrado por nome: {fornecedor.codigo} - {nome_limpo}')
        return fornecedor
    except Fornecedor.DoesNotExist:
        pass
    
    # Verificar se código gerado já existe
    codigo_final = codigo_auto
    contador = 1
    while Fornecedor.objects.filter(codigo=codigo_final).exists():
        codigo_final = f"{codigo_auto}{contador:02d}"
        contador += 1
        if contador > 99:  # Limite de segurança
            break
    
    # Criar novo fornecedor
    try:
        fornecedor = Fornecedor.objects.create(
            codigo=codigo_final,
            razao_social=nome_limpo,
            criado_automaticamente=True,
            origem_historico=historico[:500]  # Limitar tamanho
        )
        logger.info(f'Novo fornecedor criado: {codigo_final} - {nome_limpo}')
        return fornecedor
    except Exception as e:
        logger.error(f'Erro ao criar fornecedor {codigo_final}: {str(e)}')
        return None

def processar_linha_excel_atualizada(linha_dados, numero_linha, nome_arquivo):
    """
    Processa uma linha do Excel com a estrutura correta identificada
    CORRIGIDA PARA TRATAR VALORES DECIMAIS CORRETAMENTE
    
    REGRA SIMPLES:
    - Converter valores para positivo (usar abs)
    - Manter natureza do arquivo (D/C)
    - Garantir 2 casas decimais
    """
    try:
        # Extrair dados da linha baseado na estrutura real
        mes = int(linha_dados.get('Mês', 0))
        ano = int(linha_dados.get('Ano', 0))
        data = linha_dados.get('Data')
        codigo_unidade = linha_dados.get('Cód. da unidade')  # Ex: 106, 108, 115
        codigo_centro_custo = linha_dados.get('Cód. do centro de custo')  # Ex: "20.02.02"
        codigo_conta_contabil = linha_dados.get('Cód. da conta contábil')  # Ex: 6303010017
        documento = linha_dados.get('Documento', '')
        natureza = linha_dados.get('Natureza (D/C/A)', 'D')
        valor_bruto = linha_dados.get('Valor', 0)
        historico = linha_dados.get('Histórico', '')
        codigo_projeto = linha_dados.get('Cód. do projeto', '')
        gerador = linha_dados.get('Gerador', '')
        rateio = linha_dados.get('Rateio', 'N')
        
        # === CORREÇÃO SIMPLES DE VALOR ===
        # Apenas converter valor para positivo e garantir 2 casas decimais
        if valor_bruto is None or valor_bruto == '':
            valor = Decimal('0.00')
        else:
            try:
                # Converter para Decimal, usar valor absoluto e arredondar para 2 casas
                valor_decimal = Decimal(str(valor_bruto))
                valor = abs(valor_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except (ValueError, decimal.InvalidOperation):
                raise ValueError(f'Valor inválido: {valor_bruto}')
        
        # Manter natureza original do arquivo
        natureza_final = natureza or 'D'
        
        # === BUSCAR UNIDADE PELO CÓDIGO ALL STRATEGY ===
        unidade = Unidade.buscar_por_codigo_allstrategy(str(codigo_unidade))
        if not unidade:
            # Se não encontrou por All Strategy, tentar por código normal
            try:
                unidade = Unidade.objects.get(codigo=str(codigo_unidade), ativa=True)
            except Unidade.DoesNotExist:
                raise ValueError(f'Unidade não encontrada para código: {codigo_unidade}')
        
        # === BUSCAR CENTRO DE CUSTO ===
        try:
            centro_custo = CentroCusto.objects.get(codigo=str(codigo_centro_custo), ativo=True)
        except CentroCusto.DoesNotExist:
            raise ValueError(f'Centro de custo não encontrado: {codigo_centro_custo}')
        
        # === BUSCAR CONTA CONTÁBIL VIA CÓDIGO EXTERNO ===
        try:
            conta_externa = ContaExterna.objects.get(
                codigo_externo=str(codigo_conta_contabil), 
                ativa=True
            )
            conta_contabil = conta_externa.conta_contabil
        except ContaExterna.DoesNotExist:
            raise ValueError(f'Conta contábil não encontrada para código externo: {codigo_conta_contabil}')
        
        # === EXTRAIR FORNECEDOR DO HISTÓRICO ===
        fornecedor = extrair_fornecedor_do_historico(historico) if historico else None
        
        # === CONVERTER DATA ===
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
        elif isinstance(data, (int, float)):
            # Excel pode retornar data como número serial
            try:
                # Excel serial date (1 = 1900-01-01)
                excel_epoch = date(1900, 1, 1)
                data = excel_epoch + timedelta(days=int(data) - 2)  # -2 para corrigir o bug do Excel
            except:
                raise ValueError(f'Formato de data inválido: {data}')
        
        # === CRIAR MOVIMENTO ===
        movimento = Movimento.objects.create(
            mes=mes,
            ano=ano,
            data=data,
            unidade=unidade,
            centro_custo=centro_custo,
            conta_contabil=conta_contabil,
            fornecedor=fornecedor,
            documento=str(documento) if documento else '',
            natureza=natureza_final,  # Usar a natureza do arquivo
            valor=valor,  # Usar o valor já convertido (sempre positivo)
            historico=historico,
            codigo_projeto=str(codigo_projeto) if codigo_projeto else '',
            gerador=str(gerador) if gerador else '',
            rateio=str(rateio) if rateio else 'N',
            arquivo_origem=nome_arquivo,
            linha_origem=numero_linha
        )
        
        return movimento, None  # movimento, erro
        
    except Exception as e:
        error_msg = f'Linha {numero_linha}: {str(e)}'
        logger.error(f'Erro ao processar movimento: {error_msg}')
        return None, error_msg

def corrigir_estrutura_excel(arquivo):
    """
    Corrige problemas na estrutura do Excel antes do processamento
    """
    try:
        # Ler arquivo com cabeçalho na linha 1 (baseado na análise do arquivo real)
        df = pd.read_excel(arquivo, engine='openpyxl', header=0)
        
        # Verificar se as colunas necessárias existem
        colunas_necessarias = [
            'Mês', 'Ano', 'Data', 'Cód. da unidade', 'Cód. do centro de custo',
            'Cód. da conta contábil', 'Natureza (D/C/A)', 'Valor', 'Histórico'
        ]
        
        colunas_faltando = [col for col in colunas_necessarias if col not in df.columns]
        if colunas_faltando:
            raise ValueError(f'Colunas obrigatórias faltando: {", ".join(colunas_faltando)}')
        
        # Corrigir apenas os valores para positivo, manter natureza
        if 'Valor' in df.columns:
            # Converter todos os valores para positivo com 2 casas decimais
            df['Valor'] = df['Valor'].apply(lambda x: round(abs(float(x)), 2) if pd.notna(x) else 0.00)
        
        # Remover linhas completamente vazias
        df = df.dropna(how='all')
        
        return df
        
    except Exception as e:
        logger.error(f'Erro ao corrigir estrutura do Excel: {str(e)}')
        raise

# === VIEWS PRINCIPAIS ===

@login_required
def movimento_list(request):
    """Lista de movimentos com filtros"""
    search = request.GET.get('search', '')
    ano = request.GET.get('ano', '')
    mes = request.GET.get('mes', '')
    unidade = request.GET.get('unidade', '')
    centro_custo = request.GET.get('centro_custo', '')
    
    movimentos = Movimento.objects.select_related(
        'unidade', 'centro_custo', 'conta_contabil', 'fornecedor'
    ).order_by('-data', '-id')
    
    if search:
        movimentos = movimentos.filter(
            Q(historico__icontains=search) |
            Q(documento__icontains=search) |
            Q(fornecedor__razao_social__icontains=search) |
            Q(fornecedor__codigo__icontains=search)
        )
    
    if ano:
        movimentos = movimentos.filter(ano=int(ano))
    
    if mes:
        movimentos = movimentos.filter(mes=int(mes))
    
    if unidade:
        movimentos = movimentos.filter(unidade_id=unidade)
    
    if centro_custo:
        movimentos = movimentos.filter(centro_custo__codigo__icontains=centro_custo)
    
    # Calcular totais
    total_movimentos = movimentos.count()
    total_valor = movimentos.aggregate(total=Sum('valor'))['total'] or 0
    
    # Paginação
    paginator = Paginator(movimentos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Preparar dados para os dropdowns
    anos_disponiveis = list(Movimento.objects.values_list('ano', flat=True).distinct().order_by('-ano'))
    unidades_disponiveis = Unidade.objects.filter(ativa=True).order_by('codigo')
    
    meses = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]
    
    context = {
        'page_obj': page_obj,
        'total_movimentos': total_movimentos,
        'total_valor': total_valor,
        'search': search,
        'anos_disponiveis': anos_disponiveis,
        'unidades_disponiveis': unidades_disponiveis,
        'meses': meses,
        'filtros': {
            'ano': ano,
            'mes': mes,
            'unidade_id': unidade,
            'centro_custo': centro_custo,
            'search': search,
        }
    }
    
    return render(request, 'gestor/movimento_list.html', context)

@login_required
def movimento_create(request):
    """Criar novo movimento"""
    if request.method == 'POST':
        form = MovimentoForm(request.POST)
        if form.is_valid():
            try:
                movimento = form.save()
                messages.success(request, f'Movimento criado com sucesso! Valor: {movimento.valor_formatado}')
                logger.info(f'Movimento criado: {movimento.id} - {movimento.valor_formatado} por {request.user}')
                return redirect('gestor:movimento_list')
            except Exception as e:
                messages.error(request, f'Erro ao criar movimento: {str(e)}')
                logger.error(f'Erro ao criar movimento: {str(e)}')
        else:
            messages.error(request, 'Erro ao criar movimento. Verifique os dados.')
    else:
        form = MovimentoForm()
        
        # Pré-popular com mês/ano atual se fornecido
        mes_inicial = request.GET.get('mes')
        ano_inicial = request.GET.get('ano')
        if mes_inicial:
            form.fields['mes'].initial = mes_inicial
        if ano_inicial:
            form.fields['ano'].initial = ano_inicial
    
    context = {
        'form': form,
        'title': 'Novo Movimento',
        'is_create': True
    }
    return render(request, 'gestor/movimento_form.html', context)

@login_required
def movimento_update(request, pk):
    """Editar movimento"""
    movimento = get_object_or_404(Movimento, pk=pk)
    
    # Guardar valores originais para log
    valores_originais = {
        'valor': movimento.valor,
        'historico': movimento.historico,
        'fornecedor': movimento.fornecedor,
        'natureza': movimento.natureza
    }
    
    if request.method == 'POST':
        form = MovimentoForm(request.POST, instance=movimento)
        if form.is_valid():
            try:
                movimento_atualizado = form.save()
                
                # Log de alterações
                alteracoes = []
                for campo, valor_original in valores_originais.items():
                    valor_novo = getattr(movimento_atualizado, campo)
                    if valor_original != valor_novo:
                        alteracoes.append(f"{campo}: {valor_original} → {valor_novo}")
                
                if alteracoes:
                    logger.info(f'Movimento {movimento.id} alterado por {request.user}: {", ".join(alteracoes)}')
                
                messages.success(request, f'Movimento atualizado com sucesso! Valor: {movimento_atualizado.valor_formatado}')
                return redirect('gestor:movimento_list')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar movimento: {str(e)}')
                logger.error(f'Erro ao atualizar movimento {movimento.id}: {str(e)}')
        else:
            messages.error(request, 'Erro ao atualizar movimento. Verifique os dados.')
    else:
        form = MovimentoForm(instance=movimento)
    
    context = {
        'form': form,
        'title': 'Editar Movimento',
        'movimento': movimento,
        'is_create': False
    }
    return render(request, 'gestor/movimento_form.html', context)

@login_required
def movimento_delete(request, pk):
    """Deletar movimento"""
    movimento = get_object_or_404(Movimento, pk=pk)
    
    if request.method == 'POST':
        periodo_display = movimento.periodo_display
        valor_formatado = movimento.valor_formatado
        historico_resumido = movimento.historico[:50]
        movimento_id = movimento.id
        
        try:
            movimento.delete()
            messages.success(
                request, 
                f'Movimento excluído com sucesso! '
                f'Período: {periodo_display}, Valor: {valor_formatado}'
            )
            logger.info(f'Movimento excluído: {movimento_id} - {valor_formatado} por {request.user}')
            return redirect('gestor:movimento_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir movimento: {str(e)}')
            logger.error(f'Erro ao excluir movimento {movimento_id}: {str(e)}')
            return redirect('gestor:movimento_list')
    
    context = {
        'movimento': movimento
    }
    return render(request, 'gestor/movimento_delete.html', context)

@login_required
def movimento_export_excel(request):
    """Exportar movimentos para Excel"""
    
    try:
        # Aplicar os mesmos filtros da listagem
        search = request.GET.get('search', '')
        ano = request.GET.get('ano', '')
        mes = request.GET.get('mes', '')
        unidade = request.GET.get('unidade', '')
        centro_custo = request.GET.get('centro_custo', '')
        
        movimentos = Movimento.objects.select_related(
            'unidade', 'centro_custo', 'conta_contabil', 'fornecedor'
        ).order_by('-data', '-id')
        
        # Aplicar filtros
        if search:
            movimentos = movimentos.filter(
                Q(historico__icontains=search) |
                Q(documento__icontains=search) |
                Q(fornecedor__razao_social__icontains=search) |
                Q(fornecedor__codigo__icontains=search)
            )
        
        if ano:
            movimentos = movimentos.filter(ano=int(ano))
        
        if mes:
            movimentos = movimentos.filter(mes=int(mes))
        
        if unidade:
            movimentos = movimentos.filter(unidade_id=unidade)
        
        if centro_custo:
            movimentos = movimentos.filter(centro_custo__codigo__icontains=centro_custo)
        
        # Limitar exportação para evitar problemas de memória
        total_movimentos = movimentos.count()
        if total_movimentos > 50000:
            messages.warning(
                request, 
                f'Muitos registros para exportar ({total_movimentos:,}). '
                f'Use filtros para reduzir o volume ou exporte por partes.'
            )
            return redirect('gestor:movimento_list')
        
        # Criar workbook Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Movimentos"
        
        # Definir estilos
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        border_thin = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Cabeçalhos
        headers = [
            'Data', 'Mês', 'Ano', 'Período',
            'Código Unidade', 'Nome Unidade', 'Código All Strategy',
            'Código Centro Custo', 'Nome Centro Custo',
            'Código Conta Contábil', 'Nome Conta Contábil',
            'Código Fornecedor', 'Razão Social Fornecedor',
            'Documento', 'Natureza', 'Valor', 'Histórico',
            'Código Projeto', 'Gerador', 'Rateio',
            'Data Importação', 'Arquivo Origem', 'Linha Origem'
        ]
        
        # Escrever cabeçalhos
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border_thin
        
        # Escrever dados
        for row, movimento in enumerate(movimentos, 2):
            data_row = [
                movimento.data.strftime('%d/%m/%Y') if movimento.data else '',
                movimento.mes,
                movimento.ano,
                movimento.periodo_display,
                movimento.unidade.codigo if movimento.unidade else '',
                movimento.unidade.nome if movimento.unidade else '',
                movimento.unidade.codigo_allstrategy if movimento.unidade else '',
                movimento.centro_custo.codigo if movimento.centro_custo else '',
                movimento.centro_custo.nome if movimento.centro_custo else '',
                movimento.conta_contabil.codigo if movimento.conta_contabil else '',
                movimento.conta_contabil.nome if movimento.conta_contabil else '',
                movimento.fornecedor.codigo if movimento.fornecedor else '',
                movimento.fornecedor.razao_social if movimento.fornecedor else '',
                movimento.documento,
                movimento.natureza,
                float(movimento.valor) if movimento.valor else 0,
                movimento.historico,
                movimento.codigo_projeto,
                movimento.gerador,
                movimento.rateio,
                movimento.data_importacao.strftime('%d/%m/%Y %H:%M') if movimento.data_importacao else '',
                movimento.arquivo_origem,
                movimento.linha_origem
            ]
            
            for col, value in enumerate(data_row, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = border_thin
                
                # Formatação especial para valores monetários
                if col == 16:  # Coluna Valor
                    cell.number_format = '#,##0.00'
                    if value < 0:
                        cell.font = Font(color="FF0000")  # Vermelho para negativos
        
        # Ajustar largura das colunas
        column_widths = [
            12, 8, 8, 10,  # Data, Mês, Ano, Período
            15, 30, 15,     # Unidade
            15, 30,         # Centro Custo
            15, 30,         # Conta Contábil
            15, 40,         # Fornecedor
            15, 8, 15,      # Documento, Natureza, Valor
            50,             # Histórico
            15, 15, 8,      # Projeto, Gerador, Rateio
            20, 25, 8       # Importação info
        ]
        
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width
        
        # Adicionar aba de resumo
        ws_resumo = wb.create_sheet(title="Resumo")
        
        # Estatísticas para resumo
        stats = {
            'Total de Movimentos': total_movimentos,
            'Soma de Valores': float(movimentos.aggregate(Sum('valor'))['valor__sum'] or 0),
            'Movimentos Débito': movimentos.filter(natureza='D').count(),
            'Movimentos Crédito': movimentos.filter(natureza='C').count(),
            'Fornecedores Únicos': movimentos.exclude(fornecedor__isnull=True).values('fornecedor').distinct().count(),
            'Unidades Únicas': movimentos.values('unidade').distinct().count(),
            'Data de Exportação': timezone.now().strftime('%d/%m/%Y %H:%M:%S'),
            'Exportado por': request.user.get_full_name() or request.user.username
        }
        
        # Escrever resumo
        for row, (label, value) in enumerate(stats.items(), 1):
            ws_resumo.cell(row=row, column=1, value=label).font = Font(bold=True)
            ws_resumo.cell(row=row, column=2, value=value)
        
        # Salvar em memory
        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        # Criar resposta HTTP
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Nome do arquivo baseado nos filtros
        filename_parts = ['movimentos']
        if ano:
            filename_parts.append(str(ano))
        if mes:
            filename_parts.append(f"mes_{int(mes):02d}")
        
        filename = '_'.join(filename_parts) + '_' + timezone.now().strftime('%Y%m%d_%H%M%S') + '.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f'Exportação Excel realizada por {request.user}: {total_movimentos} movimentos')
        messages.success(request, f'Exportação concluída! {total_movimentos:,} movimentos exportados.')
        
        return response
        
    except Exception as e:
        logger.error(f'Erro na exportação Excel: {str(e)}')
        messages.error(request, f'Erro na exportação: {str(e)}')
        return redirect('gestor:movimento_list')

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
        'total_movimentos': Movimento.objects.count()
    }
    
    # Calcular percentual de preparação
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

# === APIs PARA IMPORTAÇÃO POR DATAS ===

@login_required
@require_POST
def api_preview_movimentos_excel(request):
    """API para preview dos movimentos - CORRIGIDA PARA VALORES DECIMAIS"""
    
    try:
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Nenhum arquivo foi enviado'})
        
        arquivo = request.FILES['arquivo']
        data_inicio_str = request.POST.get('data_inicio')
        data_fim_str = request.POST.get('data_fim')
        
        if not data_inicio_str or not data_fim_str:
            return JsonResponse({'success': False, 'error': 'Período não informado'})
        
        # Converter datas
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Formato de data inválido'})
        
        if not arquivo.name.endswith(('.xlsx', '.xls')):
            return JsonResponse({'success': False, 'error': 'Arquivo deve ser Excel (.xlsx ou .xls)'})
        
        # Usar função para corrigir estrutura do Excel
        try:
            df = corrigir_estrutura_excel(arquivo)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Erro na estrutura do arquivo: {str(e)}'})
        
        # Filtrar dados pelo período especificado (verificar apenas as primeiras 15 linhas para preview)
        preview_linhas = df.head(15).to_dict('records')
        preview_results = []
        erros_encontrados = []
        fornecedores_novos = []
        linhas_no_periodo = 0
        
        for idx, linha in enumerate(preview_linhas, 1):
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
                    'natureza': linha.get('Natureza (D/C/A)')
                },
                'validacoes': {},
                'errors': [],
                'warnings': [],
                'no_periodo': False
            }
            
            # Verificar se a linha está no período
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
                    resultado['warnings'].append(f'Data {data_linha} fora do período {data_inicio} a {data_fim}')
            except:
                resultado['errors'].append('Data inválida')
            
            # Verificar e corrigir valor (simples: converter para positivo)
            valor_linha = linha.get('Valor', 0)
            natureza_linha = linha.get('Natureza (D/C/A)', 'D')
            
            try:
                if valor_linha is not None:
                    valor_float = float(valor_linha)
                    valor_corrigido = round(abs(valor_float), 2)  # Sempre positivo
                    
                    explicacao = f"Valor {valor_float} → {valor_corrigido} (natureza: {natureza_linha})"
                else:
                    valor_corrigido = 0.00
                    explicacao = "Valor vazio → 0.00"
                
                resultado['dados']['valor'] = valor_corrigido
                resultado['dados']['natureza'] = natureza_linha
                resultado['validacoes']['valor'] = {
                    'valido': True,
                    'valor_original': valor_linha,
                    'valor_corrigido': valor_corrigido,
                    'explicacao': explicacao
                }
            except (ValueError, TypeError):
                resultado['errors'].append(f'Valor inválido: {valor_linha}')
                resultado['validacoes']['valor'] = {'valido': False}
            
            # Validar unidade pelo código All Strategy
            codigo_unidade = linha.get('Cód. da unidade')
            unidade = Unidade.buscar_por_codigo_allstrategy(str(codigo_unidade)) if codigo_unidade else None
            if not unidade and codigo_unidade:
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
            
            # Validar centro de custo
            codigo_centro = linha.get('Cód. do centro de custo')
            try:
                centro = CentroCusto.objects.get(codigo=str(codigo_centro), ativo=True)
                resultado['validacoes']['centro_custo'] = {
                    'encontrado': True,
                    'detalhes': f"{centro.codigo} - {centro.nome}"
                }
            except CentroCusto.DoesNotExist:
                resultado['validacoes']['centro_custo'] = {'encontrado': False}
                resultado['errors'].append(f'Centro de custo não encontrado: {codigo_centro}')
            
            # Validar conta contábil via código externo
            codigo_conta = linha.get('Cód. da conta contábil')
            try:
                conta_externa = ContaExterna.objects.get(codigo_externo=str(codigo_conta), ativa=True)
                resultado['validacoes']['conta_contabil'] = {
                    'encontrada': True,
                    'detalhes': f"{conta_externa.conta_contabil.codigo} - {conta_externa.conta_contabil.nome}"
                }
            except ContaExterna.DoesNotExist:
                resultado['validacoes']['conta_contabil'] = {'encontrada': False}
                resultado['errors'].append(f'Conta contábil não encontrada: {codigo_conta}')
            
            # Preview de fornecedor do histórico
            historico = linha.get('Histórico', '')
            fornecedor = extrair_fornecedor_do_historico(historico) if historico else None
            if fornecedor:
                eh_novo = not Fornecedor.objects.filter(codigo=fornecedor.codigo).exists()
                resultado['validacoes']['fornecedor'] = {
                    'sera_criado': eh_novo,
                    'detalhes': f"{fornecedor.codigo} - {fornecedor.razao_social}"
                }
                if eh_novo:
                    fornecedores_novos.append(f"{fornecedor.codigo} - {fornecedor.razao_social}")
            else:
                resultado['validacoes']['fornecedor'] = {'encontrado': False}
                resultado['warnings'].append('Nenhum fornecedor identificado no histórico')
            
            if resultado['errors']:
                erros_encontrados.extend(resultado['errors'])
            
            preview_results.append(resultado)
        
        # Contar total de linhas no período no arquivo inteiro
        total_linhas_periodo = 0
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
                'total_erros': len(erros_encontrados),
                'linhas_com_erro': len([r for r in preview_results if r['errors']]),
                'fornecedores_novos': len(fornecedores_novos),
                'pode_importar': len(erros_encontrados) == 0
            },
            'fornecedores_novos': fornecedores_novos[:10],
            'nome_arquivo': arquivo.name,
            'periodo': f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
            'erros_encontrados': erros_encontrados[:10]
        })
        
    except Exception as e:
        logger.error(f'Erro no preview: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': f'Erro ao processar arquivo: {str(e)}'
        })

@login_required
@require_POST
def api_importar_movimentos_excel(request):
    """API para importação real dos movimentos - CORRIGIDA PARA VALORES DECIMAIS"""
    
    try:
        # Receber parâmetros
        data_inicio_str = request.POST.get('data_inicio')
        data_fim_str = request.POST.get('data_fim')
        
        if not data_inicio_str or not data_fim_str:
            return JsonResponse({'success': False, 'error': 'Período não informado'})
        
        # Converter datas
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Formato de data inválido'})
        
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Arquivo não encontrado'})
        
        arquivo = request.FILES['arquivo']
        
        # Limpar período antes de importar
        logger.info(f'Iniciando limpeza do período {data_inicio} a {data_fim}')
        movimentos_removidos = Movimento.objects.filter(
            data__gte=data_inicio,
            data__lte=data_fim
        ).count()
        
        Movimento.objects.filter(
            data__gte=data_inicio,
            data__lte=data_fim
        ).delete()
        
        # Ler e corrigir arquivo
        try:
            df = corrigir_estrutura_excel(arquivo)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Erro na estrutura do arquivo: {str(e)}'})
        
        logger.info(f'Iniciando importação de {len(df)} linhas do arquivo {arquivo.name}')
        
        movimentos_criados = 0
        fornecedores_criados = 0
        erros = []
        linhas_fora_periodo = 0
        
        # Acompanhar fornecedores criados
        fornecedores_novos = set()
        
        for idx, linha in df.iterrows():
            try:
                # Processar linha
                linha_dict = linha.to_dict()
                movimento, erro = processar_linha_excel_atualizada(linha_dict, idx + 2, arquivo.name)
                
                if movimento:
                    # Verificar se está no período
                    if data_inicio <= movimento.data <= data_fim:
                        movimentos_criados += 1
                        
                        # Rastrear fornecedores novos
                        if movimento.fornecedor and movimento.fornecedor.criado_automaticamente:
                            if movimento.fornecedor.codigo not in fornecedores_novos:
                                fornecedores_novos.add(movimento.fornecedor.codigo)
                                fornecedores_criados += 1
                        
                        # Log a cada 50 movimentos
                        if movimentos_criados % 50 == 0:
                            logger.info(f'Processados {movimentos_criados} movimentos...')
                    else:
                        # Remover movimento fora do período
                        movimento.delete()
                        linhas_fora_periodo += 1
                else:
                    erros.append(erro)
                    
            except Exception as e:
                erro_msg = f'Linha {idx + 2}: Erro inesperado - {str(e)}'
                erros.append(erro_msg)
                logger.error(erro_msg)
        
        logger.info(f'Importação concluída: {movimentos_criados} movimentos, {fornecedores_criados} fornecedores novos, {len(erros)} erros, {linhas_fora_periodo} linhas fora do período')
        
        return JsonResponse({
            'success': True,
            'resultado': {
                'movimentos_removidos': movimentos_removidos,
                'movimentos_criados': movimentos_criados,
                'fornecedores_criados': fornecedores_criados,
                'linhas_fora_periodo': linhas_fora_periodo,
                'total_erros': len(erros),
                'periodo': f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
                'nome_arquivo': arquivo.name
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
    """API para validar período - ATUALIZADA PARA DATAS"""
    
    try:
        data_inicio_str = request.GET.get('data_inicio')
        data_fim_str = request.GET.get('data_fim')
        
        if not data_inicio_str or not data_fim_str:
            return JsonResponse({'success': False, 'error': 'Período não informado'})
        
        # Converter datas
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Formato de data inválido'})
        
        # Verificar se há movimentos no período
        movimentos_existentes = Movimento.objects.filter(
            data__gte=data_inicio,
            data__lte=data_fim
        ).count()
        
        return JsonResponse({
            'success': True,
            'periodo_valido': True,
            'movimentos_existentes': movimentos_existentes,
            'mensagem': f'Período {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")} - {movimentos_existentes} movimentos existentes que serão removidos'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro na validação: {str(e)}'
        })