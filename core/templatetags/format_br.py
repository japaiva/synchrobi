from django import template
from decimal import Decimal
import locale

register = template.Library()

@register.filter
def formato_br(value):
    """
    Formata número no padrão brasileiro: 1.234.567,89
    """
    if value is None:
        return "0,00"
    
    try:
        # Converter para float se necessário
        if isinstance(value, str):
            value = float(value.replace(',', '.'))
        elif isinstance(value, Decimal):
            value = float(value)
        
        # Formatação brasileira
        formatted = f"{value:,.2f}"
        
        # Trocar . por vírgula e vírgula por ponto
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return formatted
        
    except (ValueError, TypeError):
        return str(value)

@register.filter  
def moeda_br(value):
    """
    Formata como moeda brasileira: R$ 1.234.567,89
    """
    if value is None:
        return "R$ 0,00"
    
    formatted = formato_br(value)
    return f"R$ {formatted}"
