"""
AeroLux Select — Clear Site Cache
Management command to clear the in-memory site cache in the middleware.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Clear the in-memory site cache in the SiteMiddleware'

    def handle(self, *args, **options):
        from core.middleware import SiteMiddleware

        self.stdout.write('Clearing site cache...')
        SiteMiddleware.clear_cache()
        self.stdout.write(self.style.SUCCESS('  [OK] Site cache cleared'))
