"""
AeroLux Select — Site Detection Middleware
Middleware de detection du site courant.

Resolution order:
  1. Domain-based     — matches Site.domain against HTTP_HOST  (production)
  2. URL prefix       — /nyc/ or /dr/ in the path              (development)
  3. Session override — 'current_site_slug' stored in session   (preview / testing)
  4. Default          — falls back to the NYC site (slug='nyc')

The resolved Site instance is stored on ``request.current_site`` and in
thread-local storage so that SiteFilterManager can access it from the
model layer without needing the request object.
"""

import threading

from django.utils.deprecation import MiddlewareMixin

# ──────────────────────────────────────────────
#  Thread-local storage for current site
# ──────────────────────────────────────────────

_thread_locals = threading.local()


def get_current_site():
    """
    Return the current Site instance from thread-local storage, or None.
    Called by SiteFilterManager to auto-scope querysets.
    """
    return getattr(_thread_locals, 'current_site', None)


def set_current_site(site):
    """Store a Site instance in thread-local storage."""
    _thread_locals.current_site = site


# ──────────────────────────────────────────────
#  Middleware
# ──────────────────────────────────────────────

class SiteMiddleware(MiddlewareMixin):
    """
    Detects the current site on every request and attaches it to
    ``request.current_site``.

    Also stores it in thread-local storage for model-layer access.
    """

    # Cache of domain -> Site and slug -> Site to avoid DB hits on every request.
    _domain_cache = {}
    _slug_cache = {}

    # -- URL prefix mapping (development convenience) --
    URL_PREFIX_MAP = {
        'nyc': 'nyc',
        'dr': 'dr',
    }

    DEFAULT_SLUG = 'nyc'

    def process_request(self, request):
        """Resolve and attach the current site."""
        from core.models import Site  # Lazy import to avoid AppRegistryNotReady

        site = None

        # 1. Domain-based detection (production)
        host = request.get_host().split(':')[0]  # strip port
        site = self._get_site_by_domain(host)

        # 2. URL prefix detection (development)
        if site is None:
            path = request.path_info.strip('/')
            first_segment = path.split('/')[0] if path else ''
            slug = self.URL_PREFIX_MAP.get(first_segment)
            if slug:
                site = self._get_site_by_slug(slug)

        # 3. Session override
        if site is None:
            session_slug = request.session.get('current_site_slug')
            if session_slug:
                site = self._get_site_by_slug(session_slug)

        # 4. Default fallback
        if site is None:
            site = self._get_site_by_slug(self.DEFAULT_SLUG)

        # Attach to request and thread-local
        request.current_site = site
        request.current_site_slug = site.slug if site else 'nyc'
        set_current_site(site)

    def process_response(self, request, response):
        """Clean up thread-local after the response is sent."""
        set_current_site(None)
        return response

    # -- Helpers --

    @classmethod
    def _get_site_by_domain(cls, domain):
        """Look up a site by domain, with in-memory caching."""
        # Normalize: strip port (done in caller) and strip 'www.' prefix
        domain_normalized = domain.lower()
        if domain_normalized.startswith('www.'):
            domain_normalized = domain_normalized[4:]

        if domain_normalized in cls._domain_cache:
            return cls._domain_cache[domain_normalized]

        from core.models import Site
        try:
            # Try to look up by normalized domain (e.g. aeroluxselect.com)
            site = Site.objects.get(domain=domain_normalized, is_active=True)
            cls._domain_cache[domain_normalized] = site
            return site
        except Site.DoesNotExist:
            # Fallback: try lookup with original domain if different
            if domain != domain_normalized:
                try:
                    site = Site.objects.get(domain=domain, is_active=True)
                    cls._domain_cache[domain_normalized] = site
                    return site
                except Site.DoesNotExist:
                    pass
            cls._domain_cache[domain_normalized] = None
            return None

    @classmethod
    def _get_site_by_slug(cls, slug):
        """Look up a site by slug, with in-memory caching."""
        if slug in cls._slug_cache:
            return cls._slug_cache[slug]

        from core.models import Site
        try:
            site = Site.objects.get(slug=slug, is_active=True)
            cls._slug_cache[slug] = site
            return site
        except Site.DoesNotExist:
            cls._slug_cache[slug] = None
            return None

    @classmethod
    def clear_cache(cls):
        """
        Clear the in-memory site caches.
        Call this after updating Site records to force re-lookup.
        """
        cls._domain_cache.clear()
        cls._slug_cache.clear()
