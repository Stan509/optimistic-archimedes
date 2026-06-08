"""
Aero Luxe Select — URL Configuration

Routes are organized as:
- /nyc/     → NYC public site (development prefix)
- /dr/      → Dominican Republic public site (development prefix)
- /dashboard/  → Unified admin dashboard
- /admin/   → Django admin (fallback)
- /api/     → API endpoints (future)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin (fallback)
    path('admin/', admin.site.urls),

    # Unified Dashboard
    path('dashboard/', include('core.urls_dashboard', namespace='dashboard')),

    # Public sites with URL prefix routing (development mode)
    path('nyc/', include('core.urls', namespace='site_nyc')),
    path('dr/', include('core.urls', namespace='site_dr')),

    # Root URL — redirect to default site
    path('', include('core.urls_root')),
]

# Serve media files in development AND production fallback
# In production, media is primarily served from DigitalOcean Spaces (S3 CDN),
# but this fallback ensures locally-seeded images work during initial deployment.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # In production, serve media from local filesystem as fallback
    # (primary serving is via Spaces CDN, but seed images may be local initially)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customize Django admin
admin.site.site_header = 'Aero Luxe Select — Administration'
admin.site.site_title = 'Aero Luxe Select Admin'
admin.site.index_title = 'System Administration'
