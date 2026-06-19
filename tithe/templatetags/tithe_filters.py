from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get a value from a dictionary by key.
    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def month_filter(payment_list, month_num):
    """
    Template filter to get total amount for a specific month from a payment list.
    Usage: {{ payments|month_filter:1 }} for January
    """
    if payment_list is None:
        return 0
    total = 0
    for payment in payment_list:
        if payment.date.month == int(month_num):
            total += payment.amount
    return total

@register.filter
def total_amount(payment_list):
    """
    Template filter to get total amount from a payment list.
    Usage: {{ payments|total_amount }}
    """
    if payment_list is None:
        return 0
    total = 0
    for payment in payment_list:
        total += payment.amount
    return total
