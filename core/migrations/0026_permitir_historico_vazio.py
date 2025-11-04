# Generated manually on 2025-11-04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_grupofornecedor_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movimento',
            name='historico',
            field=models.TextField(blank=True, help_text='Histórico completo da movimentação', verbose_name='Histórico'),
        ),
    ]
