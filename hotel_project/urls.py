"""
Aero Luxe Select -- URL Configuration

Routes are organized as:
- /nyc/     -> NYC public site (development prefix)
- /dr/      -> Dominican Republic public site (development prefix)
- /dashboard/  -> Unified admin dashboard
- /admin/   -> Django admin (fallback)
- /api/     -> API endpoints (future)
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    # Django admin (fallback)
    path('admin/', admin.site.urls),

    # Unified Dashboard
    path('dashboard/', include('core.urls_dashboard', namespace='dashboard')),

    # Public sites with URL prefix routing (development mode)
    path('nyc/', include('core.urls', namespace='site_nyc')),
    path('dr/', include('core.urls', namespace='site_dr')),

    # Root URL -- redirect to default site
    path('', include('core.urls_root')),
]

# Serve media files - always serve from local filesystem
# In production without Spaces, this is the primary source.
# With Spaces configured, Django's storage backend serves from CDN,
# but we keep this as fallback for locally-seeded images.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # In production, django.conf.urls.static returns [] when DEBUG=False.
    # Use an explicit URL pattern to serve media files from disk.
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]

# Customize Django admin
admin.site.site_header = 'Aero Luxe Select -- Administration'
admin.site.site_title = 'Aero Luxe Select Admin'
admin.site.index_title = 'System Administration'
