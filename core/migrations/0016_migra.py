# migrations/XXXX_add_tipo_centrocusto_contacontabil.py

from django.db import migrations, models

def calcular_tipos_existentes(apps, schema_editor):
    """
    Função para calcular e definir os tipos dos registros existentes
    baseado na estrutura hierárquica atual
    """
    CentroCusto = apps.get_model('core', 'CentroCusto')
    ContaContabil = apps.get_model('core', 'ContaContabil')
    
    # Atualizar tipos dos Centros de Custo existentes
    for centro in CentroCusto.objects.all():
        # Verificar se tem sub-centros
        tem_filhos = CentroCusto.objects.filter(centro_pai=centro).exists()
        centro.tipo = 'S' if tem_filhos else 'A'
        centro.save(update_fields=['tipo'])
    
    # Atualizar tipos das Contas Contábeis existentes
    for conta in ContaContabil.objects.all():
        # Verificar se tem subcontas
        tem_filhos = ContaContabil.objects.filter(conta_pai=conta).exists()
        conta.tipo = 'S' if tem_filhos else 'A'
        conta.save(update_fields=['tipo'])

def reverter_tipos(apps, schema_editor):
    """Função para reverter (não faz nada, pois vamos apagar o campo)"""
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_unidade_tipo'),  # Substitua pelo número da migração anterior
    ]

    operations = [
        # Adicionar campo tipo ao CentroCusto
        migrations.AddField(
            model_name='centrocusto',
            name='tipo',
            field=models.CharField(
                choices=[('S', 'Sintético'), ('A', 'Analítico')], 
                default='A', 
                max_length=1, 
                verbose_name='Tipo'
            ),
        ),
        
        # Adicionar campo tipo ao ContaContabil  
        migrations.AddField(
            model_name='contacontabil',
            name='tipo',
            field=models.CharField(
                choices=[('S', 'Sintético'), ('A', 'Analítico')], 
                default='A', 
                max_length=1, 
                verbose_name='Tipo'
            ),
        ),
        
        # Executar função para calcular tipos dos registros existentes
        migrations.RunPython(
            calcular_tipos_existentes,
            reverter_tipos,
        ),
        
        # Adicionar índices para melhorar performance
        migrations.AddIndex(
            model_name='centrocusto',
            index=models.Index(fields=['tipo'], name='centrocusto_tipo_idx'),
        ),
        
        migrations.AddIndex(
            model_name='contacontabil', 
            index=models.Index(fields=['tipo'], name='contacontabil_tipo_idx'),
        ),
    ]