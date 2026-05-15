from django import template

register = template.Library()

@register.filter
def get_range(value, current_page=1):
    """Returns a range for pagination display"""
    if not value:
        return []
    
    try:
        total_pages = int(value)
        current_page = int(current_page)
    except (ValueError, TypeError):
        return []
    
    delta = 2  # Number of pages to show on each side of current
    page_range = []
    
    for i in range(1, total_pages + 1):
        if i == 1 or i == total_pages or (i >= current_page - delta and i <= current_page + delta):
            page_range.append(i)
        elif page_range and page_range[-1] != -1:
            page_range.append(-1)  # Ellipsis marker
    
    return page_range

@register.filter
def range_filter(value):
    """Returns a simple range from 1 to value"""
    try:
        return range(1, int(value) + 1) if value else []
    except (ValueError, TypeError):
        return []

@register.filter
def subtract(value, arg):
    """Subtracts arg from value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """Multiplies value by arg"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary by key"""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None