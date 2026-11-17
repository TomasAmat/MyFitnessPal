from django import template

register = template.Library()


@register.filter
def miles(valor):
    """1530 -> "1.530", como en el mockup."""
    return f"{int(valor):,}".replace(",", ".")
