"""
Aero Luxe Select — Custom Model Managers
Gestionnaires de modèles personnalisés pour le filtrage par site et par statut actif.

These managers provide automatic queryset filtering so that views and templates
never accidentally leak data from one site into another.
"""

from django.db import models


class ActiveManager(models.Manager):
    """
    Manager that returns only active records (is_active=True).

    Usage:
        class MyModel(models.Model):
            is_active = models.BooleanField(default=True)
            objects = models.Manager()       # default — all records
            active = ActiveManager()         # only active records

        MyModel.active.all()  # → only is_active=True
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class SiteFilterManager(models.Manager):
    """
    Manager that auto-filters querysets by the current site.

    Requires that the model has a ForeignKey named `site` pointing to
    core.Site.  The current site is resolved from the thread-local
    middleware storage (set by SiteMiddleware).

    Usage:
        class MyModel(models.Model):
            site = models.ForeignKey('core.Site', ...)
            objects = models.Manager()
            on_site = SiteFilterManager()

        MyModel.on_site.all()  # → filtered to current site
    """

    def get_queryset(self):
        from core.middleware import get_current_site
        qs = super().get_queryset()
        current_site = get_current_site()
        if current_site is not None:
            qs = qs.filter(site=current_site)
        return qs


class SiteFilterActiveManager(models.Manager):
    """
    Combined manager: filters by current site AND is_active=True.

    Usage:
        MyModel.site_active.all()
    """

    def get_queryset(self):
        from core.middleware import get_current_site
        qs = super().get_queryset().filter(is_active=True)
        current_site = get_current_site()
        if current_site is not None:
            qs = qs.filter(site=current_site)
        return qs
