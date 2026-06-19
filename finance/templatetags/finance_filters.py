from django import template

register = template.Library()


@register.filter
def currency(value):
    """Format a number as currency"""
    if value is None:
        return "TSH 0"
    try:
        return f"TSH {float(value):,.0f}"
    except (ValueError, TypeError):
        return "TSH 0"


@register.filter
def div(value, arg):
    """Divide value by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def mul(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def intcomma(value):
    """Format a number with commas as thousands separator"""
    if value is None:
        return "0"
    try:
        return "{:,}".format(int(float(value)))
    except (ValueError, TypeError):
        return str(value)
