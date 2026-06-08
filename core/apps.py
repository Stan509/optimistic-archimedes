from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Aero Luxe Select — Core'

    def ready(self):
        """Import signal handlers when app is ready."""
        pass
