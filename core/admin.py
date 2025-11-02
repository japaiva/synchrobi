from django.contrib import admin
from core.models import (
    Usuario, Empresa, Unidade, CentroCusto, ContaContabil,
    GrupoCC, GrupoFornecedor, Fornecedor, Movimento
)

# Register your models here.

@admin.register(GrupoFornecedor)
class GrupoFornecedorAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'total_fornecedores', 'ativo', 'data_criacao')
    list_filter = ('ativo', 'data_criacao')
    search_fields = ('codigo', 'nome', 'descricao')
    ordering = ('nome',)
    readonly_fields = ('data_criacao', 'data_alteracao')

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('codigo', 'nome', 'descricao')
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_alteracao'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'razao_social', 'cnpj_cpf_formatado', 'grupo', 'ativo', 'criado_automaticamente')
    list_filter = ('ativo', 'criado_automaticamente', 'grupo', 'data_criacao')
    search_fields = ('codigo', 'razao_social', 'nome_fantasia', 'cnpj_cpf', 'email')
    ordering = ('razao_social',)
    readonly_fields = ('data_criacao', 'data_alteracao', 'tipo_pessoa')

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('codigo', 'razao_social', 'nome_fantasia', 'cnpj_cpf', 'tipo_pessoa')
        }),
        ('Agrupamento', {
            'fields': ('grupo',)
        }),
        ('Contato', {
            'fields': ('telefone', 'email', 'endereco')
        }),
        ('Status', {
            'fields': ('ativo', 'criado_automaticamente')
        }),
        ('Rastreamento', {
            'fields': ('origem_historico', 'data_criacao', 'data_alteracao'),
            'classes': ('collapse',)
        }),
    )
