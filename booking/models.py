from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from datetime import date

class Room(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom de la chambre")
    slug = models.SlugField(unique=True, blank=True, verbose_name="Slug (URL)")
    room_number = models.CharField(max_length=10, unique=True, verbose_name="Numéro de chambre")
    description = models.TextField(verbose_name="Description")
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Prix par nuit (€)")
    capacity = models.IntegerField(default=2, verbose_name="Capacité (Personnes)")
    image = models.ImageField(upload_to="rooms/", blank=True, null=True, verbose_name="Image de la chambre")
    is_available = models.BooleanField(default=True, verbose_name="Disponible")
    
    # Équipements individuels pour filtres faciles
    has_wifi = models.BooleanField(default=True, verbose_name="Wi-Fi Gratuit")
    has_jacuzzi = models.BooleanField(default=False, verbose_name="Jacuzzi Privé")
    has_balcony = models.BooleanField(default=False, verbose_name="Balcon / Terrasse")
    has_ac = models.BooleanField(default=True, verbose_name="Climatisation")
    has_tv = models.BooleanField(default=True, verbose_name="TV Écran Plat")
    has_minibar = models.BooleanField(default=False, verbose_name="Minibar Premium")
    has_room_service = models.BooleanField(default=False, verbose_name="Service d'étage 24/7")

    class Meta:
        verbose_name = "Chambre"
        verbose_name_plural = "Chambres"
        ordering = ['price_per_night']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (N°{self.room_number})"

    @property
    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        # Fallback vers des images premium d'Unsplash si aucune image n'est téléversée
        fallback_images = {
            "suite": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80",
            "deluxe": "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=800&q=80",
            "standard": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80",
        }
        name_lower = self.name.lower()
        if "suite" in name_lower:
            return fallback_images["suite"]
        elif "deluxe" in name_lower:
            return fallback_images["deluxe"]
        return fallback_images["standard"]


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('CONFIRMED', 'Confirmée'),
        ('CANCELLED', 'Annulée'),
    ]

    customer_name = models.CharField(max_length=100, verbose_name="Nom du client")
    customer_email = models.EmailField(verbose_name="Email du client")
    customer_phone = models.CharField(max_length=20, verbose_name="Téléphone")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="reservations", verbose_name="Chambre")
    check_in = models.DateField(verbose_name="Date d'arrivée")
    check_out = models.DateField(verbose_name="Date de départ")
    guests = models.IntegerField(default=1, verbose_name="Nombre de convives")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Statut")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix total (€)")
    special_requests = models.TextField(blank=True, null=True, verbose_name="Demandes particulières")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
        ordering = ['-created_at']

    def clean(self):
        # Vérification logique des dates
        if self.check_in and self.check_out:
            if self.check_in >= self.check_out:
                raise ValidationError("La date d'arrivée doit être strictement antérieure à la date de départ.")
            if self.check_in < date.today():
                raise ValidationError("La date d'arrivée ne peut pas être dans le passé.")
                
            # Vérifier les chevauchements de réservations (uniquement les réservations confirmées ou en attente)
            overlapping_reservations = Reservation.objects.filter(
                room=self.room,
                check_in__lt=self.check_out,
                check_out__gt=self.check_in
            ).exclude(status='CANCELLED')
            
            if self.pk:
                overlapping_reservations = overlapping_reservations.exclude(pk=self.pk)
                
            if overlapping_reservations.exists():
                raise ValidationError("La chambre n'est pas disponible pour ces dates (chevauchement avec une autre réservation).")

    def save(self, *args, **kwargs):
        # Calcul automatique du prix si non fourni
        if self.check_in and self.check_out and self.room:
            nights = (self.check_out - self.check_in).days
            self.total_price = self.room.price_per_night * nights
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Réservation #{self.id} - {self.customer_name} ({self.room.name})"

    @property
    def number_of_nights(self):
        if self.check_in and self.check_out:
            return (self.check_out - self.check_in).days
        return 0


class SiteElement(models.Model):
    CATEGORY_CHOICES = [
        ('ACCUEIL', 'Page d\'Accueil'),
        ('ABOUT', 'À Propos de l\'Hôtel'),
        ('SERVICES', 'Nos Services & Charme'),
        ('CONTACT', 'Contact & Pied de Page'),
    ]

    key = models.CharField(max_length=50, unique=True, verbose_name="Clé unique")
    label = models.CharField(max_length=100, verbose_name="Label éditeur")
    value = models.TextField(verbose_name="Valeur textuelle")
    image = models.ImageField(upload_to="site_elements/", blank=True, null=True, verbose_name="Image associée")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='ACCUEIL', verbose_name="Catégorie")

    class Meta:
        verbose_name = "Élément du Site"
        verbose_name_plural = "Éléments du Site"
        ordering = ['category', 'label']

    def __str__(self):
        return f"{self.label} ({self.key})"

    @property
    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return None


class SiteSettings(models.Model):
    hotel_name = models.CharField(max_length=100, default="L'Horizon Impérial", verbose_name="Nom de l'Hôtel")
    contact_email = models.EmailField(default="contact@horizon-imperial.com", verbose_name="Email de contact")
    contact_phone = models.CharField(max_length=20, default="+33 (0)4 93 00 00 00", verbose_name="Téléphone de contact")
    address = models.CharField(max_length=255, default="12 Boulevard de la Croisette, 06400 Cannes, France", verbose_name="Adresse")
    social_facebook = models.URLField(blank=True, default="https://facebook.com", verbose_name="Lien Facebook")
    social_instagram = models.URLField(blank=True, default="https://instagram.com", verbose_name="Lien Instagram")
    social_twitter = models.URLField(blank=True, default="https://twitter.com", verbose_name="Lien Twitter")

    class Meta:
        verbose_name = "Paramètres Généraux"

    def __str__(self):
        return f"Configuration - {self.hotel_name}"

    def save(self, *args, **kwargs):
        # Empêcher la création de plusieurs lignes de configuration
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("Il ne peut y avoir qu'une seule instance de configuration générale.")
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        # Récupérer l'unique instance ou en créer une par défaut
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
