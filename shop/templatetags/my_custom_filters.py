from django import template

register=template.Library()

@register.filter
def ceiling(nom,denom):
    return nom//denom