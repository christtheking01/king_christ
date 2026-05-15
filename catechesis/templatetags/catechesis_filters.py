from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key - used for attendance form"""
    return dictionary.get(key)
