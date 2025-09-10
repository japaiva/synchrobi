# core/utils/view_utils.py - VERSÃO COMPLETA ATUALIZADA

"""
Utilitários para views e templates
"""
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django import forms
from datetime import datetime

logger = logging.getLogger(__name__)

# ===== WIDGET PARA CAMPOS DE DATA =====

class CustomDateInput(forms.DateInput):
    """
    Widget customizado para campos DateField que converte automaticamente
    entre formato brasileiro (dd/MM/yyyy) e formato HTML5 (yyyy-MM-dd)
    """
    input_type = 'date'
    
    def format_value(self, value):
        if value is None:
            return None  # ← MUDANÇA AQUI: era '' agora é None
        
        # Se for string vazia, também retornar None
        if value == '':
            return None  # ← ADICIONADO: tratar string vazia
        
        # Se já for uma string, verificar se está no formato correto
        if isinstance(value, str):
            try:
                # Tentar converter para datetime e depois para o formato esperado
                parsed = datetime.strptime(value, '%Y-%m-%d')
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                # Se não for possível converter, retornar o valor como está
                return value
        # Se for um objeto date/datetime, converter para string no formato correto
        return value.strftime('%Y-%m-%d')


# ===== WIDGET PARA CAMPOS DE DATA E HORA =====

class CustomDateTimeInput(forms.DateTimeInput):
    """
    Widget customizado para campos DateTimeField que converte automaticamente
    entre formato brasileiro (dd/MM/yyyy HH:MM) e formato HTML5 (yyyy-MM-ddTHH:MM)
    """
    input_type = 'datetime-local'
    
    def format_value(self, value):
        # Se o valor for None, retornar vazio
        if value is None:
            return None  # ← MUDANÇA AQUI: era '' agora é None
        
        # Se for string vazia, também retornar None
        if value == '':
            return None  # ← ADICIONADO: tratar string vazia
        
        # Se for uma string, tentar converter diferentes formatos
        if isinstance(value, str):
            # Formato brasileiro com hora: dd/MM/yyyy HH:MM
            if '/' in value and ' ' in value:
                try:
                    parsed = datetime.strptime(value, '%d/%m/%Y %H:%M')
                    return parsed.strftime('%Y-%m-%dT%H:%M')
                except ValueError:
                    try:
                        # Tentar com segundos: dd/MM/yyyy HH:MM:SS
                        parsed = datetime.strptime(value, '%d/%m/%Y %H:%M:%S')
                        return parsed.strftime('%Y-%m-%dT%H:%M')
                    except ValueError:
                        pass
            
            # Formato brasileiro só com data: dd/MM/yyyy (assumir 00:00)
            elif '/' in value and ' ' not in value:
                try:
                    parsed = datetime.strptime(value, '%d/%m/%Y')
                    return parsed.strftime('%Y-%m-%dT00:00')
                except ValueError:
                    pass
            
            # Se já está no formato HTML5: yyyy-MM-ddTHH:MM
            if 'T' in value:
                try:
                    # Validar se é um formato datetime válido
                    if len(value) >= 16:  # yyyy-MM-ddTHH:MM
                        parsed = datetime.strptime(value[:16], '%Y-%m-%dT%H:%M')
                        return parsed.strftime('%Y-%m-%dT%H:%M')
                except ValueError:
                    pass
            
            # Formato ISO com segundos: yyyy-MM-dd HH:MM:SS
            if len(value) >= 19 and ' ' in value:
                try:
                    parsed = datetime.strptime(value[:19], '%Y-%m-%d %H:%M:%S')
                    return parsed.strftime('%Y-%m-%dT%H:%M')
                except ValueError:
                    pass
        
        # Se for um objeto datetime
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%dT%H:%M')
        
        # Se for um objeto date (sem hora, assumir 00:00)
        if hasattr(value, 'strftime') and not isinstance(value, datetime):
            # É um objeto date
            return value.strftime('%Y-%m-%dT00:00')
        
        # Fallback: usar o método padrão do Django
        try:
            return super().format_value(value)
        except:
            return str(value) if value else ''


# ===== CLASSE BASE PARA FORMULÁRIOS COM CAMPOS DE DATA =====

class DateAwareModelForm(forms.ModelForm):
    """
    Um ModelForm que trata automaticamente campos de data para garantir
    que eles sejam formatados corretamente para widgets HTML5.
    """
    def __init__(self, *args, **kwargs):
        super(DateAwareModelForm, self).__init__(*args, **kwargs)
        
        # Para cada campo, aplicar o widget apropriado
        for field_name, field in self.fields.items():
            # Para campos DateField, usar CustomDateInput
            if isinstance(field, forms.DateField) and not isinstance(field.widget, CustomDateInput):
                self.fields[field_name].widget = CustomDateInput(
                    attrs=getattr(field.widget, 'attrs', {'class': 'form-control'})
                )
            # Para campos DateTimeField, usar CustomDateTimeInput
            elif isinstance(field, forms.DateTimeField) and not isinstance(field.widget, CustomDateTimeInput):
                self.fields[field_name].widget = CustomDateTimeInput(
                    attrs=getattr(field.widget, 'attrs', {'class': 'form-control'})
                )


# ===== UTILITÁRIOS DE PAGINAÇÃO (mantidos iguais) =====

def paginar_lista(queryset, request, itens_por_pagina=10):
    """
    Função utilitária para paginação de querysets
    
    Args:
        queryset: QuerySet a ser paginado
        request: Objeto request do Django
        itens_por_pagina: Número de itens por página (padrão: 10)
    
    Returns:
        Objeto Page contendo os itens da página atual
    """
    paginator = Paginator(queryset, itens_por_pagina)
    page = request.GET.get('page', 1)
    
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # Se page não for um inteiro, retornar a primeira página
        items = paginator.page(1)
    except EmptyPage:
        # Se page estiver fora do intervalo, retornar a última página
        items = paginator.page(paginator.num_pages)
    
    return items

class PaginacaoMixin:
    """
    Mixin para adicionar funcionalidade de paginação a class-based views
    """
    itens_por_pagina = 10
    
    def paginar_queryset(self, queryset):
        """
        Pagina o queryset fornecido
        
        Args:
            queryset: QuerySet a ser paginado
            
        Returns:
            Objeto Page contendo os itens da página atual
        """
        return paginar_lista(queryset, self.request, self.itens_por_pagina)
