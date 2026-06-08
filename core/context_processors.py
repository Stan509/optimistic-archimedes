"""
Aero Luxe Select — Template Context Processors
Processeurs de contexte pour injecter les variables globales dans tous les templates.

Provides:
  - current_site:    The resolved Site instance for this request
  - site_settings:   SiteSettings singleton for the current site
  - available_sites: All active sites (for site-switcher dropdown)
  - service_types:   ServiceType choices for menus/forms
"""

from core.models import Site, SiteSettings, ServiceType


def site_context(request):
    """
    Inject site-related variables into every template context.

    Relies on SiteMiddleware having set ``request.current_site`` first.
    If the middleware has not run (e.g. in management commands that render
    templates), the values will be None / empty.
    """
    current_site = getattr(request, 'current_site', None)
    current_site_slug = getattr(request, 'current_site_slug', 'nyc')

    # Build context
    ctx = {
        'current_site': current_site,
        'current_site_slug': current_site_slug,
        'site_settings': None,
        'available_sites': Site.active.all(),
        'service_types': ServiceType.choices,
    }

    if current_site is not None:
        ctx['site_settings'] = SiteSettings.get_settings(current_site)

    return ctx
