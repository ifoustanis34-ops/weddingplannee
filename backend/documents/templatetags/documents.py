from __future__ import annotations

from django import template
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


@register.filter
def split(value: str, separator: str = ",") -> list[str]:
    """`"10mm,63mm"|split` → a list, for the column widths of the shared table."""
    return [part.strip() for part in str(value).split(separator)]


@register.filter
def tint(svg: str, color: str) -> SafeString:
    """Colour an icon: WeasyPrint's SVG renderer ignores the CSS `color` of the page."""
    return mark_safe(  # noqa: S308 - icons come from documents.icons, colours from palettes
        str(svg).replace('stroke="currentColor"', f'stroke="{color}"')
    )
