# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_grupocc'),
    ]

    operations = [
        migrations.AddField(
            model_name='contacontabil',
            name='relatorio_despesa',
            field=models.BooleanField(default=True, verbose_name='Relatório Despesa'),
        ),
        migrations.AddIndex(
            model_name='contacontabil',
            index=models.Index(fields=['relatorio_despesa'], name='contas_cont_relator_idx'),
        ),
    ]
