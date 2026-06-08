"""
Aero Luxe Select — Custom Template Tags

Provides site-specific template functionality.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def site_url(context, url_name, *args, **kwargs):
    """
    Generate a URL prefixed with the current site slug.
    Usage: {% site_url 'core:services' %}
    """
    from django.urls import reverse
    current_slug = context.get('current_site_slug', 'nyc')
    namespace = f'site_{current_slug}'
    try:
        return reverse(f'{namespace}:{url_name}', args=args, kwargs=kwargs)
    except Exception:
        return f'/{current_slug}/'


@register.simple_tag(takes_context=True)
def site_content(context, key, default=''):
    """
    Fetch CMS content by key for the current site.
    Usage: {% site_content 'hero_title' 'Default Title' %}
    """
    current_site = context.get('current_site')
    if not current_site:
        return default

    try:
        from core.models import SiteContent
        # Get language from session or default
        request = context.get('request')
        lang = 'en'
        if request:
            slug = getattr(request, 'current_site_slug', 'nyc')
            if slug == 'dr':
                lang = request.session.get('language', 'en')

        content = SiteContent.objects.filter(
            site=current_site,
            key=key,
            language=lang
        ).first()

        if content:
            return content.value
        
        # Fallback to English if no translation found
        content = SiteContent.objects.filter(
            site=current_site,
            key=key,
            language='en'
        ).first()
        
        if content:
            return content.value
    except Exception:
        pass

    return default


@register.simple_tag(takes_context=True)
def site_image(context, key):
    """
    Fetch CMS image URL by key for the current site.
    Usage: {% site_image 'hero_background' %}
    """
    current_site = context.get('current_site')
    if not current_site:
        return ''

    try:
        from core.models import SiteContent
        content = SiteContent.objects.filter(
            site=current_site,
            key=key
        ).first()
        if content and content.image:
            return content.image.url
    except Exception:
        pass
    return ''


@register.filter
def currency(value, symbol='$'):
    """
    Format a number as currency.
    Usage: {{ price|currency }}  →  $120.00
    """
    try:
        return f'{symbol}{float(value):,.2f}'
    except (ValueError, TypeError):
        return f'{symbol}0.00'


@register.filter
def get_item(dictionary, key):
    """
    Get value from dictionary dynamically.
    Usage: {{ dict|get_item:key }}
    """
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError, KeyError):
        try:
            return dictionary.get(str(key))
        except Exception:
            return None


@register.filter
def star_rating(value):
    """
    Convert a rating number to star icons.
    Usage: {{ rating|star_rating }}
    """
    try:
        rating = int(float(value))
        full_stars = '★' * rating
        empty_stars = '☆' * (5 - rating)
        return mark_safe(f'<span class="text-luxe-gold">{full_stars}</span>'
                        f'<span class="text-gray-400">{empty_stars}</span>')
    except (ValueError, TypeError):
        return ''


@register.inclusion_tag('core/components/_site_switcher.html', takes_context=True)
def site_switcher(context):
    """Render the floating site switcher button."""
    return context


@register.simple_tag(takes_context=True)
def get_site_prefix(context):
    """Return the current site URL prefix."""
    slug = context.get('current_site_slug', 'nyc')
    return f'/{slug}'
