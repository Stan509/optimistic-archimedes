from .models import SiteSettings, SiteElement

def site_context(request):
    # Récupérer les paramètres généraux
    settings = SiteSettings.get_settings()
    
    # Récupérer tous les éléments du site sous forme de dictionnaire clé -> objet
    elements = {elem.key: elem for elem in SiteElement.objects.all()}
    
    return {
        'settings': settings,
        'elements': elements
    }
