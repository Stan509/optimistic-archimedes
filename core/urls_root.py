"""
Root URL pattern — redirects to the default site (NYC).
"""

from django.urls import path
from django.shortcuts import redirect


def root_redirect(request):
    """Redirect root URL to the default site."""
    return redirect('/nyc/')


urlpatterns = [
    path('', root_redirect, name='root'),
]
