# core/management/commands/preencher_pais.py
# Comando para preencher automaticamente os campos codigo_pai

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Unidade, CentroCusto, ContaContabil

class Command(BaseCommand):
    help = 'Preenche automaticamente os campos codigo_pai baseado na estrutura existente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--modelo',
            type=str,
            choices=['unidade', 'centro', 'conta', 'todos'],
            default='todos',
            help='Modelo a processar'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula o processo sem salvar no banco'
        )

    def handle(self, *args, **options):
        modelo = options['modelo']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== MODO SIMULAÇÃO (DRY RUN) ==='))
        else:
            self.stdout.write(self.style.SUCCESS('=== PREENCHENDO PAIS AUTOMATICAMENTE ==='))
        
        total_atualizado = 0
        
        if modelo in ['unidade', 'todos']:
            total_atualizado += self.processar_unidades(dry_run)
        
        if modelo in ['centro', 'todos']:
            total_atualizado += self.processar_centros(dry_run)
        
        if modelo in ['conta', 'todos']:
            total_atualizado += self.processar_contas(dry_run)
        
        self.stdout.write(
            self.style.SUCCESS(f'\n=== RESUMO ===')
        )
        self.stdout.write(f'Total de itens atualizados: {total_atualizado}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Execute novamente sem --dry-run para aplicar as mudanças')
            )

    def processar_unidades(self, dry_run=False):
        self.stdout.write('\n1. Processando Unidades...')
        
        # Buscar todas as unidades ordenadas por código
        unidades = list(Unidade.objects.all().order_by('codigo'))
        unidades_dict = {u.codigo: u for u in unidades}
        
        atualizado = 0
        
        with transaction.atomic():
            for unidade in unidades:
                pai_codigo = self.deduzir_pai(unidade.codigo, unidades_dict)
                
                if pai_codigo and pai_codigo != unidade.codigo_pai:
                    self.stdout.write(f'  {unidade.codigo} -> pai: {pai_codigo}')
                    
                    if not dry_run:
                        unidade.codigo_pai = pai_codigo
                        unidade.save(update_fields=['codigo_pai'])
                    
                    atualizado += 1
                elif unidade.codigo_pai:
                    # Já tem pai, só mostrar se verbose
                    pass
                else:
                    # É raiz
                    self.stdout.write(f'  {unidade.codigo} -> RAIZ')
        
        self.stdout.write(f'Unidades processadas: {atualizado}/{len(unidades)}')
        return atualizado

    def processar_centros(self, dry_run=False):
        self.stdout.write('\n2. Processando Centros de Custo...')
        
        centros = list(CentroCusto.objects.all().order_by('codigo'))
        centros_dict = {c.codigo: c for c in centros}
        
        atualizado = 0
        
        with transaction.atomic():
            for centro in centros:
                pai_codigo = self.deduzir_pai(centro.codigo, centros_dict)
                
                if pai_codigo and pai_codigo != centro.codigo_pai:
                    self.stdout.write(f'  {centro.codigo} -> pai: {pai_codigo}')
                    
                    if not dry_run:
                        centro.codigo_pai = pai_codigo
                        centro.save(update_fields=['codigo_pai'])
                    
                    atualizado += 1
                elif centro.codigo_pai:
                    # Já tem pai
                    pass
                else:
                    # É raiz
                    self.stdout.write(f'  {centro.codigo} -> RAIZ')
        
        self.stdout.write(f'Centros processados: {atualizado}/{len(centros)}')
        return atualizado

    def processar_contas(self, dry_run=False):
        self.stdout.write('\n3. Processando Contas Contábeis...')
        
        contas = list(ContaContabil.objects.all().order_by('codigo'))
        contas_dict = {c.codigo: c for c in contas}
        
        atualizado = 0
        
        with transaction.atomic():
            for conta in contas:
                pai_codigo = self.deduzir_pai(conta.codigo, contas_dict)
                
                if pai_codigo and pai_codigo != conta.codigo_pai:
                    self.stdout.write(f'  {conta.codigo} -> pai: {pai_codigo}')
                    
                    if not dry_run:
                        conta.codigo_pai = pai_codigo
                        conta.save(update_fields=['codigo_pai'])
                    
                    atualizado += 1
                elif conta.codigo_pai:
                    # Já tem pai
                    pass
                else:
                    # É raiz
                    self.stdout.write(f'  {conta.codigo} -> RAIZ')
        
        self.stdout.write(f'Contas processadas: {atualizado}/{len(contas)}')
        return atualizado

    def deduzir_pai(self, codigo, items_dict):
        """
        Deduz o pai de um código baseado na estrutura existente
        Tenta diferentes possibilidades do mais específico para o mais geral
        """
        if '.' not in codigo:
            return None  # É raiz
        
        partes = codigo.split('.')
        
        # Tentar diferentes possibilidades de pai
        for i in range(len(partes) - 1, 0, -1):
            codigo_pai_candidato = '.'.join(partes[:i])
            
            if codigo_pai_candidato in items_dict:
                return codigo_pai_candidato
        
        return None