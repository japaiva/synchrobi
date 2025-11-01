# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_contacontabil_relatorio_despesa'),
    ]

    operations = [
        migrations.AddField(
            model_name='centrocustoexterno',
            name='codigo_responsavel',
            field=models.ForeignKey(
                blank=True,
                help_text='Grupo CC responsável',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='centros_custo_responsavel',
                to='core.grupocc',
                verbose_name='Responsável'
            ),
        ),
        migrations.AddField(
            model_name='centrocustoexterno',
            name='codigo_beneficiado',
            field=models.ForeignKey(
                blank=True,
                help_text='Grupo CC beneficiado',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='centros_custo_beneficiado',
                to='core.grupocc',
                verbose_name='Beneficiado'
            ),
        ),
        migrations.AddIndex(
            model_name='centrocustoexterno',
            index=models.Index(fields=['codigo_responsavel'], name='centros_cus_codigo__resp_idx'),
        ),
        migrations.AddIndex(
            model_name='centrocustoexterno',
            index=models.Index(fields=['codigo_beneficiado'], name='centros_cus_codigo__benef_idx'),
        ),
    ]
