"""
Root URL pattern — redirects to the default site (NYC).
"""

from django.urls import path
from django.shortcuts import redirect


def root_redirect(request):
    """Redirect root URL to the current site determined by SiteMiddleware."""
    slug = getattr(request, 'current_site_slug', 'nyc')
    return redirect(f'/{slug}/')


urlpatterns = [
    path('', root_redirect, name='root'),
]
