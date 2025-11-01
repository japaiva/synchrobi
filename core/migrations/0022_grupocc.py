# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_alter_contaexterna_options_alter_contaexterna_ativa_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='GrupoCC',
            fields=[
                ('codigo', models.CharField(max_length=10, primary_key=True, serialize=False, verbose_name='Código')),
                ('descricao', models.CharField(max_length=30, verbose_name='Descrição')),
                ('ativa', models.BooleanField(default=True, verbose_name='Ativa')),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_alteracao', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Grupo CC',
                'verbose_name_plural': 'Grupos CC',
                'db_table': 'grupos_cc',
                'ordering': ['codigo'],
            },
        ),
        migrations.AddIndex(
            model_name='grupocc',
            index=models.Index(fields=['codigo'], name='grupos_cc_codigo_idx'),
        ),
        migrations.AddIndex(
            model_name='grupocc',
            index=models.Index(fields=['ativa'], name='grupos_cc_ativa_idx'),
        ),
    ]
