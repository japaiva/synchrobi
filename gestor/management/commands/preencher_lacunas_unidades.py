# gestor/management/commands/preencher_lacunas_unidades.py
# Script para identificar e preencher lacunas na hierarquia de unidades

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Unidade
from django.utils import timezone
import logging

logger = logging.getLogger('synchrobi')

class Command(BaseCommand):
    help = 'Identifica e preenche lacunas na hierarquia de unidades organizacionais'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra as lacunas sem criar as unidades',
        )
        parser.add_argument(
            '--empresa',
            type=str,
            help='Sigla da empresa para processar (opcional)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        empresa_sigla = options.get('empresa')
        
        self.stdout.write("=" * 60)
        self.stdout.write("ANÁLISE DE LACUNAS NA HIERARQUIA DE UNIDADES")
        self.stdout.write("=" * 60)
        
        # Buscar unidades existentes
        queryset = Unidade.objects.filter(ativa=True).order_by('codigo')
        if empresa_sigla:
            queryset = queryset.filter(empresa__sigla=empresa_sigla)
            self.stdout.write(f"Analisando apenas empresa: {empresa_sigla}")
        
        codigos_existentes = list(queryset.values_list('codigo', flat=True))
        
        self.stdout.write(f"\nTotal de unidades ativas: {len(codigos_existentes)}")
        self.stdout.write(f"Códigos existentes: {codigos_existentes[:10]}..." if len(codigos_existentes) > 10 else f"Códigos existentes: {codigos_existentes}")
        
        # Encontrar lacunas
        lacunas = self.encontrar_lacunas(codigos_existentes)
        
        if not lacunas:
            self.stdout.write(self.style.SUCCESS("\n✅ Nenhuma lacuna encontrada! Hierarquia está completa."))
            return
        
        self.stdout.write(self.style.WARNING(f"\n❌ {len(lacunas)} lacuna(s) encontrada(s):"))
        self.stdout.write("\nLACUNAS IDENTIFICADAS:")
        self.stdout.write("-" * 40)
        
        lacunas_detalhadas = []
        for i, lacuna in enumerate(lacunas, 1):
            nivel = lacuna.count('.') + 1
            nome_sugerido = f"Nível {nivel} - {lacuna}"
            
            lacunas_detalhadas.append({
                'codigo': lacuna,
                'nome': nome_sugerido,
                'nivel': nivel,
                'tipo': 'S',
                'descricao': '---'
            })
            
            self.stdout.write(f"{i:2d}. Código: '{lacuna}' (Nível {nivel})")
            self.stdout.write(f"    Nome: '{nome_sugerido}'")
            self.stdout.write(f"    Tipo: Sintético")
            self.stdout.write("")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 MODE DRY-RUN: Nenhuma unidade será criada."))
            self.stdout.write("\nPara criar as unidades, execute:")
            comando = "python manage.py preencher_lacunas_unidades"
            if empresa_sigla:
                comando += f" --empresa {empresa_sigla}"
            self.stdout.write(f"  {comando}")
            return
        
        # Confirmar criação
        confirmacao = input(f"\nDeseja criar estas {len(lacunas)} unidades? (s/N): ")
        if confirmacao.lower() not in ['s', 'sim', 'y', 'yes']:
            self.stdout.write("Operação cancelada.")
            return
        
        # Criar unidades
        self.stdout.write("\n🔧 Criando unidades intermediárias...")
        unidades_criadas = self.criar_unidades_intermediarias(lacunas_detalhadas, empresa_sigla)
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ {unidades_criadas} unidade(s) criada(s) com sucesso!"))
        
        # Verificar se ainda há lacunas
        novos_codigos = list(Unidade.objects.filter(ativa=True).values_list('codigo', flat=True))
        lacunas_restantes = self.encontrar_lacunas(novos_codigos)
        
        if lacunas_restantes:
            self.stdout.write(self.style.WARNING(f"⚠️  Ainda existem {len(lacunas_restantes)} lacuna(s). Execute novamente se necessário."))
        else:
            self.stdout.write(self.style.SUCCESS("🎉 Hierarquia completamente preenchida!"))

    def encontrar_lacunas(self, codigos_existentes):
        """Encontra códigos de unidades pai que estão faltando"""
        lacunas = set()
        
        for codigo in codigos_existentes:
            if '.' not in codigo:
                continue  # Códigos raiz não precisam de pai
                
            partes = codigo.split('.')
            
            # Verificar cada nível pai
            for i in range(1, len(partes)):
                codigo_pai = '.'.join(partes[:i])
                
                if codigo_pai not in codigos_existentes:
                    lacunas.add(codigo_pai)
        
        return sorted(list(lacunas))

    def criar_unidades_intermediarias(self, lacunas_detalhadas, empresa_sigla=None):
        """Cria as unidades intermediárias necessárias"""
        unidades_criadas = 0
        
        # Determinar empresa padrão se necessário
        empresa = None
        if empresa_sigla:
            from core.models import Empresa
            try:
                empresa = Empresa.objects.get(sigla=empresa_sigla)
            except Empresa.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Empresa '{empresa_sigla}' não encontrada"))
                return 0
        
        # Ordenar por nível para criar pais antes dos filhos
        lacunas_ordenadas = sorted(lacunas_detalhadas, key=lambda x: x['nivel'])
        
        with transaction.atomic():
            for lacuna in lacunas_ordenadas:
                try:
                    # Verificar se já existe (pode ter sido criado em iteração anterior)
                    if Unidade.objects.filter(codigo=lacuna['codigo']).exists():
                        self.stdout.write(f"  • '{lacuna['codigo']}' já existe, pulando...")
                        continue
                    
                    unidade = Unidade.objects.create(
                        codigo=lacuna['codigo'],
                        nome=lacuna['nome'],
                        tipo=lacuna['tipo'],
                        nivel=lacuna['nivel'],
                        descricao=lacuna['descricao'],
                        ativa=True,
                        empresa=empresa,
                        data_criacao=timezone.now(),
                        data_alteracao=timezone.now()
                    )
                    
                    unidades_criadas += 1
                    self.stdout.write(f"  ✅ Criada: '{unidade.codigo}' - {unidade.nome}")
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Erro ao criar '{lacuna['codigo']}': {str(e)}"))
                    logger.error(f"Erro ao criar unidade intermediária {lacuna['codigo']}: {str(e)}")
        
        return unidades_criadas

    def validar_hierarquia_completa(self):
        """Valida se a hierarquia está completa"""
        codigos = list(Unidade.objects.filter(ativa=True).values_list('codigo', flat=True))
        lacunas = self.encontrar_lacunas(codigos)
        return len(lacunas) == 0, lacunas


# Arquivo alternativo: gestor/utils/hierarquia.py
# Utilitário para usar em views ou outras partes do sistema

def analisar_lacunas_unidades(empresa_sigla=None):
    """
    Analisa lacunas na hierarquia de unidades
    Retorna: (total_lacunas, lacunas_detalhadas, codigos_existentes)
    """
    queryset = Unidade.objects.filter(ativa=True).order_by('codigo')
    if empresa_sigla:
        queryset = queryset.filter(empresa__sigla=empresa_sigla)
    
    codigos_existentes = list(queryset.values_list('codigo', flat=True))
    lacunas = encontrar_lacunas_hierarquia(codigos_existentes)
    
    lacunas_detalhadas = []
    for lacuna in lacunas:
        nivel = lacuna.count('.') + 1
        lacunas_detalhadas.append({
            'codigo': lacuna,
            'nome': f"Nível {nivel} - {lacuna}",
            'nivel': nivel,
            'tipo': 'S',
            'descricao': '---'
        })
    
    return len(lacunas), lacunas_detalhadas, codigos_existentes

def encontrar_lacunas_hierarquia(codigos_existentes):
    """Encontra códigos de unidades pai que estão faltando"""
    lacunas = set()
    
    for codigo in codigos_existentes:
        if '.' not in codigo:
            continue
            
        partes = codigo.split('.')
        for i in range(1, len(partes)):
            codigo_pai = '.'.join(partes[:i])
            if codigo_pai not in codigos_existentes:
                lacunas.add(codigo_pai)
    
    return sorted(list(lacunas))

def criar_unidades_intermediarias_programatico(lacunas_detalhadas, empresa=None):
    """
    Cria unidades intermediárias programaticamente
    Para uso em views ou outros contextos
    """
    unidades_criadas = 0
    
    lacunas_ordenadas = sorted(lacunas_detalhadas, key=lambda x: x['nivel'])
    
    with transaction.atomic():
        for lacuna in lacunas_ordenadas:
            if not Unidade.objects.filter(codigo=lacuna['codigo']).exists():
                Unidade.objects.create(
                    codigo=lacuna['codigo'],
                    nome=lacuna['nome'],
                    tipo=lacuna['tipo'],
                    nivel=lacuna['nivel'],
                    descricao=lacuna['descricao'],
                    ativa=True,
                    empresa=empresa,
                    data_criacao=timezone.now(),
                    data_alteracao=timezone.now()
                )
                unidades_criadas += 1
    
    return unidades_criadas


# EXEMPLO DE USO EM VIEW:
"""
# gestor/views/unidade_lacunas.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .utils.hierarquia import analisar_lacunas_unidades, criar_unidades_intermediarias_programatico

@login_required
def analisar_lacunas_view(request):
    empresa_sigla = request.GET.get('empresa')
    
    total_lacunas, lacunas_detalhadas, codigos_existentes = analisar_lacunas_unidades(empresa_sigla)
    
    context = {
        'total_lacunas': total_lacunas,
        'lacunas': lacunas_detalhadas,
        'total_unidades': len(codigos_existentes),
        'empresa_sigla': empresa_sigla
    }
    
    return render(request, 'gestor/unidade_lacunas.html', context)

@login_required  
def preencher_lacunas_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'})
    
    empresa_sigla = request.POST.get('empresa')
    
    try:
        total_lacunas, lacunas_detalhadas, _ = analisar_lacunas_unidades(empresa_sigla)
        
        if total_lacunas == 0:
            return JsonResponse({'success': True, 'message': 'Nenhuma lacuna encontrada'})
        
        # Determinar empresa
        empresa = None
        if empresa_sigla:
            empresa = Empresa.objects.get(sigla=empresa_sigla)
        
        unidades_criadas = criar_unidades_intermediarias_programatico(lacunas_detalhadas, empresa)
        
        return JsonResponse({
            'success': True,
            'message': f'{unidades_criadas} unidade(s) intermediária(s) criada(s)',
            'lacunas_preenchidas': unidades_criadas
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
"""