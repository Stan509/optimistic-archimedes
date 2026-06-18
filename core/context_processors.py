"""
AeroLux Select — Template Context Processors
Processeurs de contexte pour injecter les variables globales dans tous les templates.

Provides:
  - current_site:        The resolved Site instance for this request
  - site_settings:       SiteSettings singleton for the current site
  - available_sites:     All active sites (for site-switcher dropdown)
  - service_types:       ServiceType choices for menus/forms
  - Google Maps key      (per-site or fallback)
  - Google reCAPTCHA key (for form protection)
  - Google Analytics ID  (for tracking)
  - Google Tag Manager   (for GTM container)
"""

from django.conf import settings as django_settings
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

    # Resolve the Google Maps API key for this specific site
    site_keys = getattr(django_settings, 'GOOGLE_MAPS_API_KEYS', {})
    google_maps_key = site_keys.get(
        current_site_slug,
        getattr(django_settings, 'GOOGLE_MAPS_API_KEY', '')
    )

    # Build context
    ctx = {
        'current_site': current_site,
        'current_site_slug': current_site_slug,
        'site_settings': None,
        'available_sites': Site.active.all(),
        'service_types': ServiceType.choices,
        # Google Maps
        'google_maps_api_key': google_maps_key,
        'use_leaflet_fallback': getattr(django_settings, 'USE_LEAFLET_FALLBACK', True),
        # Google reCAPTCHA
        'recaptcha_site_key': getattr(django_settings, 'RECAPTCHA_SITE_KEY', ''),
        # Google Analytics
        'google_analytics_id': getattr(django_settings, 'GOOGLE_ANALYTICS_ID', ''),
        # Google Tag Manager
        'gtm_container_id': getattr(django_settings, 'GTM_CONTAINER_ID', ''),
    }

    if current_site is not None:
        ctx['site_settings'] = SiteSettings.get_settings(current_site)

    return ctx
