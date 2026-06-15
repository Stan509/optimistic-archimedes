"""
AeroLux Select — Core Models
Modèles principaux du système de location de voitures de luxe et transferts aéroport.

This module contains every model for the AeroLux Select platform:
  • Site / SiteSettings / SiteContent  — Multi-site CMS
  • Airport / Destination / PricingRule — Geography & pricing engine
  • VehicleCategory / Vehicle          — Fleet management
  • PremiumAddOn                       — Upsell products
  • Booking                            — Reservation & payment tracking
  • Testimonial                        — Social proof
  • ProfitReport                       — Dashboard accounting

Business context (DR pricing tiers):
  PUJ → Hotels:          $120 – $150
  SDQ → Santo Domingo:   $95  – $130
  Remote zones:          $160 – $220
  Hourly service:        $65  – $90/hr (min 3 h)

Platform commission: 20-30% markup for Viator / Expedia sales.
Developer credit: GABOOM (Tel: 829 509 84 12)
"""

import uuid
import string
import random
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
)
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from core.managers import ActiveManager, SiteFilterManager, SiteFilterActiveManager


# ──────────────────────────────────────────────
# Choices / Enums (not separate models)
# ──────────────────────────────────────────────

class ServiceType(models.TextChoices):
    """
    Types de service proposés par AeroLux Select.
    """
    AIRPORT_TRANSFER = 'airport_transfer', 'Airport Transfer'
    POINT_TO_POINT = 'point_to_point', 'Point-to-Point'
    HOURLY = 'hourly', 'Hourly Service'
    LUXURY_RENTAL = 'luxury_rental', 'Luxury Rental'


class BookingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PARTIALLY_PAID = 'partially_paid', 'Partially Paid'
    PAID = 'paid', 'Paid'
    REFUNDED = 'refunded', 'Refunded'


class PaymentMethod(models.TextChoices):
    STRIPE = 'stripe', 'Stripe'
    CASH = 'cash', 'Cash'
    INVOICE = 'invoice', 'Invoice'


class BookingSource(models.TextChoices):
    DIRECT = 'direct', 'Direct'
    VIATOR = 'viator', 'Viator'
    EXPEDIA = 'expedia', 'Expedia'
    OTHER = 'other', 'Other'


class DestinationType(models.TextChoices):
    HOTEL = 'hotel', 'Hotel'
    NEIGHBORHOOD = 'neighborhood', 'Neighborhood'
    AIRBNB = 'airbnb', 'Airbnb'
    RESORT = 'resort', 'Resort'
    CUSTOM = 'custom', 'Custom Address'


class ContentCategory(models.TextChoices):
    HERO = 'hero', 'Hero Section'
    SERVICES = 'services', 'Services'
    ABOUT = 'about', 'About'
    FLEET = 'fleet', 'Fleet'
    TESTIMONIALS = 'testimonials', 'Testimonials'
    FOOTER = 'footer', 'Footer'
    CONTACT = 'contact', 'Contact'


class LanguageChoice(models.TextChoices):
    EN = 'en', 'English'
    ES = 'es', 'Español'


class PricingZone(models.TextChoices):
    """Zones tarifaires pour le pricing basé sur la zone (République Dominicaine & NYC)."""
    HOTEL_ZONE = 'hotel_zone', 'Hotel Zone'
    CITY_CENTER = 'city_center', 'City Center'
    REMOTE = 'remote', 'Remote Area'
    MANHATTAN_DOWNTOWN = 'manhattan_downtown', 'Manhattan Downtown'
    MANHATTAN_MIDTOWN = 'manhattan_midtown', 'Manhattan Midtown'
    MANHATTAN_UPTOWN = 'manhattan_uptown', 'Manhattan Uptown'


# ──────────────────────────────────────────────
# Validators
# ──────────────────────────────────────────────

hex_color_validator = RegexValidator(
    regex=r'^#(?:[0-9a-fA-F]{3}){1,2}$',
    message='Enter a valid hex color code (e.g. #1A2B3C).',
)

iata_code_validator = RegexValidator(
    regex=r'^[A-Z]{3}$',
    message='Enter a valid 3-letter IATA airport code (uppercase).',
)

phone_validator = RegexValidator(
    regex=r'^\+?[\d\s\-()]{7,20}$',
    message='Enter a valid phone number.',
)


# ═══════════════════════════════════════════════
#  SITE  — Multi-site configuration
# ═══════════════════════════════════════════════

class Site(models.Model):
    """
    Represents a distinct AeroLux Select website (e.g. NYC, Dominican Republic).
    Each site has its own branding, domain, hero content, and default language.
    """

    name = models.CharField(
        max_length=100,
        help_text='Display name of the site (e.g. "AeroLux Select NYC").',
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        help_text='URL-safe identifier (e.g. "nyc", "dr").',
    )
    domain = models.CharField(
        max_length=255,
        unique=True,
        help_text='Primary domain for this site (e.g. "nyc.aeroluxeselect.com").',
    )
    tagline = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Short tagline shown in header or meta description.',
    )

    # ── Hero section ──
    hero_title = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Main heading on the hero banner.',
    )
    hero_subtitle = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Sub-heading on the hero banner.',
    )
    hero_video_url = models.URLField(
        blank=True,
        default='',
        help_text='URL to a background video (YouTube, Vimeo, or direct MP4).',
    )

    # ── Branding ──
    logo = models.ImageField(
        upload_to='sites/logos/',
        blank=True,
        null=True,
        help_text='Site logo image.',
    )
    primary_color = models.CharField(
        max_length=7,
        default='#0D0D0D',
        validators=[hex_color_validator],
        help_text='Primary brand color in hex.',
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#C9A84C',
        validators=[hex_color_validator],
        help_text='Secondary / accent brand color in hex.',
    )

    # ── Status ──
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this site is publicly accessible.',
    )
    default_language = models.CharField(
        max_length=2,
        choices=LanguageChoice.choices,
        default=LanguageChoice.EN,
        help_text='Default display language for this site.',
    )

    # ── Managers ──
    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Site'
        verbose_name_plural = 'Sites'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_content(self, key, language=None):
        """
        Fetch a CMS content value for this site by key.

        Args:
            key:      Unique content key (e.g. 'hero_cta_text').
            language: 'en' or 'es'.  Defaults to the site's default_language.

        Returns:
            The SiteContent instance, or None if not found.
        """
        lang = language or self.default_language
        return self.contents.filter(key=key, language=lang).first()


# ═══════════════════════════════════════════════
#  AIRPORT  — Airport definitions per site
# ═══════════════════════════════════════════════

class Airport(models.Model):
    """
    An airport serviced by a site.

    NYC airports: JFK, LGA, EWR, SWF, HPN, ISP, TEB
    DR airports:  PUJ, SDQ, STI, POP, LRM, BRX, EPS
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='airports',
        help_text='The site this airport belongs to.',
    )
    name = models.CharField(
        max_length=200,
        help_text='Full airport name (e.g. "John F. Kennedy International Airport").',
    )
    code = models.CharField(
        max_length=3,
        validators=[iata_code_validator],
        help_text='3-letter IATA code (e.g. "JFK").',
    )
    city = models.CharField(
        max_length=100,
        help_text='City where the airport is located.',
    )
    country = models.CharField(
        max_length=100,
        default='United States',
        help_text='Country of the airport.',
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Short description for display on the booking form.',
    )
    image = models.ImageField(
        upload_to='airports/',
        blank=True,
        null=True,
        help_text='Photo of the airport or terminal.',
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text='GPS latitude.',
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text='GPS longitude.',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this airport is offered for bookings.',
    )

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Airport'
        verbose_name_plural = 'Airports'
        ordering = ['site', 'code']
        unique_together = [['site', 'code']]

    def __str__(self):
        return f'{self.code} — {self.name}'

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.upper()


# ═══════════════════════════════════════════════
#  DESTINATION  — Hotels, neighborhoods, resorts
# ═══════════════════════════════════════════════

class Destination(models.Model):
    """
    A destination reachable from an airport (hotel, resort, neighborhood, etc.).
    Used to build the pickup/dropoff selector and tie into PricingRules.
    """

    airport = models.ForeignKey(
        Airport,
        on_delete=models.CASCADE,
        related_name='destinations',
        help_text='The airport this destination is served from.',
    )
    name = models.CharField(
        max_length=255,
        help_text='Destination name (e.g. "Hard Rock Hotel Punta Cana").',
    )
    address = models.TextField(
        blank=True,
        default='',
        help_text='Full street address.',
    )
    destination_type = models.CharField(
        max_length=20,
        choices=DestinationType.choices,
        default=DestinationType.HOTEL,
        help_text='Category of destination.',
    )
    description = models.TextField(
        blank=True,
        default='',
    )
    image = models.ImageField(
        upload_to='destinations/',
        blank=True,
        null=True,
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Destination'
        verbose_name_plural = 'Destinations'
        ordering = ['airport', 'name']

    def __str__(self):
        return f'{self.name} (via {self.airport.code})'


# ═══════════════════════════════════════════════
#  VEHICLE CATEGORY & VEHICLE
# ═══════════════════════════════════════════════

class VehicleCategory(models.Model):
    """
    A class of vehicle (e.g. Executive SUV, Luxury Sedan).

    Phase 1 fleet: Executive SUV — Cadillac Escalade / Chevrolet Suburban.
    The spline_scene_url field supports embedding a Spline 3D scene on the website.
    """

    name = models.CharField(
        max_length=100,
        help_text='Category name (e.g. "Executive SUV").',
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
    )
    description = models.TextField(
        blank=True,
        default='',
    )
    passengers_capacity = models.PositiveIntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text='Maximum passenger count.',
    )
    luggage_capacity = models.PositiveIntegerField(
        default=6,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        help_text='Maximum luggage pieces.',
    )
    image = models.ImageField(
        upload_to='vehicles/categories/',
        blank=True,
        null=True,
    )
    spline_scene_url = models.URLField(
        blank=True,
        default='',
        help_text='Spline 3D scene embed URL for interactive vehicle display.',
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(
        default=0,
        help_text='Display order (lower = first).',
    )

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Vehicle Category'
        verbose_name_plural = 'Vehicle Categories'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Vehicle(models.Model):
    """
    A specific vehicle within a category, optionally available on multiple sites.
    """

    category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.CASCADE,
        related_name='vehicles',
        help_text='Vehicle category (e.g. Executive SUV).',
    )
    sites = models.ManyToManyField(
        Site,
        related_name='vehicles',
        blank=True,
        help_text='Sites where this vehicle is available.',
    )
    name = models.CharField(
        max_length=200,
        help_text='Vehicle name (e.g. "Cadillac Escalade ESV").',
    )
    model_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(2000), MaxValueValidator(2050)],
        help_text='Model year.',
    )
    image = models.ImageField(
        upload_to='vehicles/',
        blank=True,
        null=True,
    )
    price_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.50')), MaxValueValidator(Decimal('5.00'))],
        help_text='Price multiplier relative to the category base price (1.0 = standard).',
    )
    features = models.JSONField(
        default=dict,
        blank=True,
        help_text='JSON dict of features (e.g. {"wifi": true, "minibar": true, "leather_seats": true}).',
    )
    is_active = models.BooleanField(default=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        ordering = ['category', 'name']

    def __str__(self):
        year = f' {self.model_year}' if self.model_year else ''
        return f'{self.name}{year}'


# ═══════════════════════════════════════════════
#  PRICING RULE  — Hourly & Point-to-Point pricing
# ═══════════════════════════════════════════════

class PricingRule(models.Model):
    """
    Pricing rule for Hourly and Point-to-Point services.

    For Airport Transfers, use ZoneVehiclePrice instead.

    Hourly:        base_price per hour × hours
    Point-to-Point: base_price + (price_per_km × km beyond km_threshold)
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='pricing_rules',
        help_text='Site this rule applies to.',
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='pricing_rules',
        blank=True,
        null=True,
        help_text='Specific vehicle this price applies to.',
    )
    vehicle_category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.CASCADE,
        related_name='pricing_rules',
        help_text='Vehicle category (used as fallback if no vehicle-specific rule).',
    )
    service_type = models.CharField(
        max_length=20,
        choices=[
            ('hourly', 'Hourly Service'),
            ('point_to_point', 'Point-to-Point'),
        ],
        default='hourly',
        help_text='Type of service (Hourly or Point-to-Point only).',
    )

    # ── Pricing fields ──
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Base price in USD (hourly rate or P2P base fare).',
    )
    price_per_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Price per km for Point-to-Point (applied beyond km_threshold).',
    )
    km_threshold = models.PositiveIntegerField(
        default=25,
        help_text='Distance threshold in km. Per-km pricing starts beyond this distance.',
    )
    minimum_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Minimum charge (floor).',
    )

    is_active = models.BooleanField(default=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Pricing Rule'
        verbose_name_plural = 'Pricing Rules'
        ordering = ['site', 'service_type', 'base_price']

    def __str__(self):
        vehicle_name = self.vehicle.name if self.vehicle else self.vehicle_category.name
        return f'[{self.get_service_type_display()}] {self.site.slug.upper()} — {vehicle_name}: ${self.base_price}'

    def get_effective_price(self, distance_km=None):
        """
        Calculate effective price for Point-to-Point based on distance.
        Per-km charge applies only beyond km_threshold.
        """
        price = self.base_price
        if self.price_per_km and distance_km and distance_km > self.km_threshold:
            extra_km = Decimal(str(distance_km - self.km_threshold))
            price += self.price_per_km * extra_km
        return max(price, self.minimum_price)


# ═══════════════════════════════════════════════
#  ZONE VEHICLE PRICE  — Airport transfer fixed pricing
# ═══════════════════════════════════════════════

class AirportCategoryPrice(models.Model):
    """
    Base pricing configuration for airport transfers based on:
      Airport → VehicleCategory → Base Price, Base KM, Price per extra KM
    """

    airport = models.ForeignKey(
        Airport,
        on_delete=models.CASCADE,
        related_name='category_prices',
        help_text='Airport for this pricing.',
    )
    vehicle_category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.CASCADE,
        related_name='airport_prices',
        help_text='Vehicle category for this pricing.',
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Base price in USD for this airport and category.',
    )
    base_km = models.PositiveIntegerField(
        default=25,
        help_text='Base distance in kilometers included in the base price.',
    )
    price_per_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Price per extra kilometer beyond the base distance.',
    )
    is_active = models.BooleanField(default=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Airport Category Price'
        verbose_name_plural = 'Airport Category Prices'
        ordering = ['airport', 'vehicle_category']
        unique_together = [['airport', 'vehicle_category']]

    def __str__(self):
        return f'{self.airport.code} -> {self.vehicle_category.name}: ${self.base_price} (up to {self.base_km} km + ${self.price_per_km}/km)'


# ═══════════════════════════════════════════════
#  PREMIUM ADD-ON  — Upsell products
# ═══════════════════════════════════════════════

class PremiumAddOn(models.Model):
    """
    Premium upsell products available during booking.

    Default catalogue:
      • Fast-track VIP        — $45
      • Concierge booking     — $35
      • Multi-stop            — +$25/stop
      • Real estate tour      — $150/hr
    """

    name = models.CharField(
        max_length=150,
        help_text='Add-on name.',
    )
    slug = models.SlugField(
        max_length=150,
        unique=True,
    )
    description = models.TextField(
        blank=True,
        default='',
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Price in USD.',
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='CSS icon class (e.g. "fas fa-star", "heroicon-bolt").',
    )
    is_active = models.BooleanField(default=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Premium Add-On'
        verbose_name_plural = 'Premium Add-Ons'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} (${self.price})'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════
#  BOOKING  — Core reservation model
# ═══════════════════════════════════════════════

class Booking(models.Model):
    """
    Central booking / reservation model.

    Covers all three service types:
      • Airport Transfer  — airport → destination or reverse
      • Luxury Rental     — vehicle rental by the day
      • Hourly Service    — chauffeur service billed per hour (min 3 h)

    Commission logic:
      If booking_source != DIRECT, the displayed total is multiplied by
      (1 + platform_commission_rate) so the platform margin is baked in.
    """

    # ── Identifiers ──
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.AIRPORT_TRANSFER,
    )
    booking_reference = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text='Auto-generated unique reference code.',
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
    )

    # ── Customer details ──
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(
        max_length=30,
        validators=[phone_validator],
    )
    customer_whatsapp = models.CharField(
        max_length=30,
        blank=True,
        default='',
        validators=[phone_validator],
        help_text='WhatsApp number for dispatch notifications.',
    )

    # ── Trip details ──
    airport = models.ForeignKey(
        Airport,
        on_delete=models.SET_NULL,
        related_name='bookings',
        blank=True,
        null=True,
        help_text='Airport for transfer bookings.',
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.SET_NULL,
        related_name='bookings',
        blank=True,
        null=True,
        help_text='Destination for transfer bookings.',
    )
    pickup_address = models.TextField(
        blank=True,
        default='',
        help_text='Free-text pickup address.',
    )
    dropoff_address = models.TextField(
        blank=True,
        default='',
        help_text='Free-text drop-off address.',
    )
    pickup_date = models.DateField(
        help_text='Scheduled pickup date.',
    )
    pickup_time = models.TimeField(
        help_text='Scheduled pickup time.',
    )
    flight_number = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text='Flight number for airport transfers (e.g. "AA1234").',
    )
    round_trip = models.BooleanField(
        default=False,
        help_text='Whether the booking includes a return leg.',
    )
    transfer_direction = models.CharField(
        max_length=20,
        choices=[
            ('AIRPORT_TO_DEST', 'Airport to Destination'),
            ('DEST_TO_AIRPORT', 'Destination to Airport')
        ],
        default='AIRPORT_TO_DEST',
        help_text='Direction of travel for Airport Transfers.'
    )
    meeting_point = models.TextField(
        blank=True,
        default='',
        help_text='Specific instructions for chauffeur meeting point (e.g. Exit Gate B).'
    )
    return_meeting_point = models.TextField(
        blank=True,
        default='',
        help_text='Specific instructions for return leg chauffeur meeting point.'
    )
    passenger_count = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text='Number of passengers for this ride.'
    )
    linked_booking = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='return_bookings',
        blank=True,
        null=True,
        help_text='Reference to the linked leg of a round-trip booking.'
    )
    return_date = models.DateField(
        null=True,
        blank=True,
        help_text='Scheduled return date for round-trip bookings.',
    )
    return_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Scheduled return time for round-trip bookings.',
    )
    number_of_stops = models.PositiveIntegerField(
        default=0,
        help_text='Number of intermediate stops.',
    )
    stop_addresses = models.TextField(
        blank=True,
        default='',
        help_text='Descriptions / addresses of intermediate stops.',
    )

    # ── Hourly service ──
    hours_requested = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('3.0'),
        validators=[MinValueValidator(Decimal('3.0'))],
        help_text='Hours requested for hourly service (minimum 3).',
    )
    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Rate per hour in USD.',
    )

    # ── Vehicle ──
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        related_name='bookings',
        blank=True,
        null=True,
        help_text='Specific vehicle selected for this booking.',
    )
    vehicle_category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.SET_NULL,
        related_name='bookings',
        blank=True,
        null=True,
    )

    # ── Add-ons ──
    addons = models.ManyToManyField(
        PremiumAddOn,
        related_name='bookings',
        blank=True,
    )
    addons_return = models.ManyToManyField(
        PremiumAddOn,
        related_name='return_bookings',
        blank=True,
        help_text='Add-ons selected specifically for the return leg.'
    )

    # ── Pricing ──
    distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Calculated distance in kilometers."
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    addons_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Calculated platform commission amount.',
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    pay_separately = models.BooleanField(
        default=False,
        help_text='Whether the customer requested to pay for outbound and return legs separately.'
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='The amount currently paid by the customer.'
    )
    reminder_sent = models.BooleanField(
        default=False,
        help_text='Whether the 12-hour reminder email has been sent.'
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text='ISO 4217 currency code.',
    )

    # ── Platform / source ──
    booking_source = models.CharField(
        max_length=20,
        choices=BookingSource.choices,
        default=BookingSource.DIRECT,
    )
    platform_commission_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('1.00'))],
        help_text='Commission rate as a decimal (e.g. 0.25 = 25%).',
    )

    # ── Payment ──
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    stripe_payment_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Stripe PaymentIntent or Checkout Session ID.',
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.STRIPE,
    )

    # ── Notes ──
    customer_notes = models.TextField(
        blank=True,
        default='',
        help_text='Notes from the customer.',
    )
    internal_notes = models.TextField(
        blank=True,
        default='',
        help_text='Internal staff notes (not visible to customer).',
    )
    driver_notes = models.TextField(
        blank=True,
        default='',
        help_text='Notes visible to the assigned driver.',
    )

    # ── Timestamps ──
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Managers ──
    objects = models.Manager()
    on_site = SiteFilterManager()
    site_active = SiteFilterActiveManager()

    class Meta:
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.booking_reference} — {self.customer_name} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        # Enforce status constraints relative to date bounds
        from django.utils import timezone
        today_date = timezone.now().date()
        if self.status in ['in_progress', 'IN_PROGRESS', 'completed', 'COMPLETED']:
            if self.pickup_date and self.pickup_date > today_date:
                raise ValidationError("A booking cannot be in progress or completed if the pickup date has not arrived yet.")
        if self.status in ['completed', 'COMPLETED'] and self.round_trip and self.return_date:
            if self.return_date > today_date:
                raise ValidationError("A round-trip booking cannot be completed if the return date has not arrived yet.")

        if not self.booking_reference:
            self.booking_reference = self.generate_reference()
        super().save(*args, **kwargs)

    # ── Business logic ──

    @staticmethod
    def generate_reference():
        """
        Generate a unique booking reference.
        Format: ALS-XXXXXXXX  (ALS = AeroLux Select, 8 alphanumeric chars)
        """
        chars = string.ascii_uppercase + string.digits
        while True:
            ref = 'ALS-' + ''.join(random.choices(chars, k=8))
            if not Booking.objects.filter(booking_reference=ref).exists():
                return ref

    def calculate_total(self):
        """
        Recalculate all pricing fields and save.

        Commission logic:
          If booking is from a platform (Viator, Expedia, etc.), the
          platform_fee = base_price * platform_commission_rate
          and total_price includes this fee.

        Hourly logic:
          base_price = hourly_rate * hours_requested

        Returns:
            Decimal: the computed total_price.
        """
        # --- Base price for hourly service ---
        if self.service_type == ServiceType.HOURLY and self.hourly_rate > 0:
            self.base_price = self.hourly_rate * self.hours_requested

        # --- Add-ons total ---
        if self.pk:
            self.addons_total = sum(
                addon.price for addon in self.addons.all()
            )
            self.addons_total += sum(
                addon.price for addon in self.addons_return.all()
            )
        else:
            self.addons_total = Decimal('0.00')

        # --- Platform commission ---
        if self.booking_source != BookingSource.DIRECT and self.platform_commission_rate > 0:
            self.platform_fee = self.base_price * self.platform_commission_rate
        else:
            self.platform_fee = Decimal('0.00')

        # --- Total ---
        fare = self.base_price
        
        # Round trip doubles base fare
        if (self.service_type in [ServiceType.AIRPORT_TRANSFER, ServiceType.POINT_TO_POINT, ServiceType.LUXURY_RENTAL]) and self.round_trip:
            fare = fare * Decimal('2.00')
            
        # Point to Point stops fee
        stops_fee = Decimal('0.00')
        if self.service_type == ServiceType.POINT_TO_POINT:
            stops_fee = Decimal('20.00') * Decimal(self.number_of_stops)

        self.total_price = fare + stops_fee + self.addons_total + self.platform_fee

        return self.total_price

    @property
    def number_of_hours(self):
        """Convenience property — hours_requested as a float."""
        return float(self.hours_requested)

    @property
    def is_platform_booking(self):
        """True if the booking came from Viator, Expedia, or other external platform."""
        return self.booking_source != BookingSource.DIRECT

    @property
    def is_return_alert_active(self):
        """
        True if booking is a round trip, status is CONFIRMED or IN_PROGRESS,
        and return date/time is within 12 hours from now and in the future.
        """
        if not self.round_trip or not self.return_date or not self.return_time:
            return False
        if self.status not in ['CONFIRMED', 'IN_PROGRESS', 'confirmed', 'in_progress']:
            return False
        try:
            from datetime import datetime, timedelta
            from django.utils import timezone
            return_datetime = datetime.combine(self.return_date, self.return_time)
            if timezone.is_aware(timezone.now()):
                return_datetime = timezone.make_aware(return_datetime, timezone.get_current_timezone())
            now = timezone.now()
            time_diff = return_datetime - now
            return timedelta(hours=0) <= time_diff <= timedelta(hours=12)
        except Exception:
            return False

    def clean(self):
        super().clean()
        # Hourly bookings must request at least 3 hours
        if self.service_type == ServiceType.HOURLY:
            if self.hours_requested < Decimal('3.0'):
                raise ValidationError({
                    'hours_requested': 'Hourly service requires a minimum of 3 hours.'
                })
            if self.hours_requested > Decimal('12.0'):
                raise ValidationError({
                    'hours_requested': 'Hourly service is limited to a maximum of 12 hours.'
                })
        # Airport transfers should have an airport
        if self.service_type == ServiceType.AIRPORT_TRANSFER and not self.airport:
            raise ValidationError({
                'airport': 'Airport transfer bookings require an airport.'
            })
        # Validate return date/time if round-trip is selected
        if self.round_trip:
            if not self.return_date or not self.return_time:
                raise ValidationError({
                    'return_date': 'Return date and time are required for round-trip bookings.'
                })

        # Enforce date constraints on status
        from django.utils import timezone
        today_date = timezone.now().date()
        if self.status in ['in_progress', 'IN_PROGRESS', 'completed', 'COMPLETED']:
            if self.pickup_date and self.pickup_date > today_date:
                raise ValidationError({
                    'status': 'A booking cannot be in progress or completed if the pickup date has not arrived yet.'
                })
        if self.status in ['completed', 'COMPLETED'] and self.round_trip and self.return_date:
            if self.return_date > today_date:
                raise ValidationError({
                    'status': 'A round-trip booking cannot be completed if the return date has not arrived yet.'
                })


# ═══════════════════════════════════════════════
#  CMS — Site Content
# ═══════════════════════════════════════════════

class SiteContent(models.Model):
    """
    Key-value CMS content tied to a site and language.
    Allows the dashboard to edit hero text, service descriptions, etc.
    without touching templates.
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='contents',
    )
    key = models.CharField(
        max_length=100,
        help_text='Unique content key within this site+language (e.g. "hero_cta_text").',
    )
    label = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='Human-readable label for the dashboard editor.',
    )
    value = models.TextField(
        blank=True,
        default='',
        help_text='The actual content (HTML allowed).',
    )
    image = models.ImageField(
        upload_to='cms/',
        blank=True,
        null=True,
        help_text='Optional image associated with this content block.',
    )
    category = models.CharField(
        max_length=20,
        choices=ContentCategory.choices,
        default=ContentCategory.HERO,
        help_text='Section of the site this content belongs to.',
    )
    language = models.CharField(
        max_length=2,
        choices=LanguageChoice.choices,
        default=LanguageChoice.EN,
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text='Display order within the category.',
    )

    objects = models.Manager()
    on_site = SiteFilterManager()

    class Meta:
        verbose_name = 'Site Content'
        verbose_name_plural = 'Site Contents'
        ordering = ['site', 'category', 'order']
        unique_together = [['site', 'key', 'language']]

    def __str__(self):
        return f'[{self.site.slug}] {self.key} ({self.get_language_display()})'


# ═══════════════════════════════════════════════
#  TESTIMONIAL
# ═══════════════════════════════════════════════

class Testimonial(models.Model):
    """
    Customer testimonial / review displayed on the site.
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='testimonials',
    )
    customer_name = models.CharField(max_length=200)
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Star rating from 1 to 5.',
    )
    comment = models.TextField()
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        blank=True,
        default='',
        help_text='Which service this testimonial relates to.',
    )
    is_featured = models.BooleanField(
        default=False,
        help_text='Featured testimonials appear prominently on the homepage.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    on_site = SiteFilterManager()

    class Meta:
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.customer_name} — {"⭐" * self.rating}'

    def clean(self):
        super().clean()
        if self.rating < 1 or self.rating > 5:
            raise ValidationError({
                'rating': 'Rating must be between 1 and 5.',
            })


# ═══════════════════════════════════════════════
#  SITE SETTINGS  — Singleton configuration per site
# ═══════════════════════════════════════════════

class SiteSettings(models.Model):
    """
    Singleton-per-site settings: company info, Stripe keys, social links, etc.
    Access via SiteSettings.get_settings(site).
    """

    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        related_name='settings',
    )

    # ── Company info ──
    company_name = models.CharField(
        max_length=200,
        default='AeroLux Select',
    )
    developer_name = models.CharField(
        max_length=200,
        default='GABOOM',
        help_text='Developer credit displayed in the footer.',
    )
    developer_phone = models.CharField(
        max_length=30,
        default='829 509 84 12',
        help_text='Developer contact phone.',
    )

    # ── Contact ──
    contact_email = models.EmailField(
        blank=True,
        default='',
    )
    contact_phone = models.CharField(
        max_length=30,
        blank=True,
        default='',
        validators=[phone_validator],
    )
    whatsapp_number = models.CharField(
        max_length=30,
        blank=True,
        default='',
        validators=[phone_validator],
        help_text='WhatsApp number for customer inquiries & dispatch.',
    )

    # ── Stripe ──
    stripe_public_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Stripe publishable key (pk_live_… or pk_test_…).',
    )
    stripe_secret_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Stripe secret key (sk_live_… or sk_test_…). Never expose in templates.',
    )
    stripe_enabled = models.BooleanField(
        default=False,
        help_text='Enable Stripe payment processing for this site.',
    )

    # ── Social media ──
    social_facebook = models.URLField(blank=True, default='')
    social_instagram = models.URLField(blank=True, default='')
    social_twitter = models.URLField(blank=True, default='')
    social_tiktok = models.URLField(blank=True, default='')

    # ── Analytics ──
    google_analytics_id = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text='Google Analytics measurement ID (G-XXXXXXXXXX).',
    )
    google_maps_api_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Google Maps API key for distance calculation and map routing.',
    )

    # ── Email Service Configuration ──
    email_provider = models.CharField(
        max_length=20,
        choices=[
            ('SMTP', 'SMTP'),
            ('SENDGRID', 'SendGrid'),
            ('RESEND', 'Resend'),
            ('MAILGUN', 'Mailgun'),
            ('BREVO', 'Brevo'),
        ],
        default='SMTP',
        help_text='Third-party provider or SMTP for sending notifications.',
    )
    email_host = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='SMTP Host (e.g. smtp.gmail.com).',
    )
    email_port = models.IntegerField(
        default=587,
        help_text='SMTP Port (e.g. 587 or 465).',
    )
    email_username = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='SMTP Username / API User.',
    )
    email_password = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='SMTP Password / API Key secret.',
    )
    email_use_tls = models.BooleanField(
        default=True,
        help_text='Use TLS for secure SMTP connection.',
    )
    email_api_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='API key for SendGrid / Resend / Mailgun.',
    )
    email_domain = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='API Domain for Mailgun / Resend (e.g. mg.yourdomain.com).',
    )
    email_from = models.EmailField(
        blank=True,
        default='no-reply@aeroluxeselect.com',
        help_text='From email address for confirmations.',
    )
    dispatch_email = models.EmailField(
        blank=True,
        default='dispatch@aeroluxeselect.com',
        help_text='Recipient email address for dispatch alerts.',
    )
    terms_and_conditions = models.TextField(
        blank=True,
        default='',
        help_text='Terms and conditions text displayed during checkout.'
    )

    # ── Airport Transfer Distance Pricing ──
    price_per_mile = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('3.50'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Rate per mile for airport transfer distance-based pricing.',
    )
    airport_base_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('15.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Base pickup/dropoff fee added to every airport transfer.',
    )

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return f'Settings for {self.site.name}'

    @classmethod
    def get_settings(cls, site):
        """
        Retrieve (or create) the SiteSettings singleton for the given site.

        Args:
            site: A Site instance.

        Returns:
            SiteSettings instance.
        """
        settings, _created = cls.objects.get_or_create(site=site)
        return settings


# ═══════════════════════════════════════════════
#  PROFIT REPORT  — Dashboard accounting
# ═══════════════════════════════════════════════

class ProfitReport(models.Model):
    """
    Monthly profit/loss summary per site — powers the dashboard analytics view.
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='profit_reports',
    )
    month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text='Month number (1–12).',
    )
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(2024), MaxValueValidator(2100)],
    )

    total_bookings = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    platform_fees = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total platform commissions earned.',
    )
    net_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Revenue after platform fees.',
    )
    expenses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    on_site = SiteFilterManager()

    class Meta:
        verbose_name = 'Profit Report'
        verbose_name_plural = 'Profit Reports'
        ordering = ['-year', '-month']
        unique_together = [['site', 'month', 'year']]

    def __str__(self):
        return f'{self.site.name} — {self.month:02d}/{self.year}'

    def clean(self):
        super().clean()
        if self.month < 1 or self.month > 12:
            raise ValidationError({'month': 'Month must be between 1 and 12.'})


class BookingPayment(models.Model):
    """
    Tracks manual cash/stripe payments logged for a booking to form a ledger history.
    """
    booking = models.ForeignKey(
        'Booking',
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('CASH', 'Cash on Delivery'),
            ('STRIPE', 'Stripe Card'),
            ('MANUAL', 'Manual Logged'),
        ],
        default='CASH',
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Booking Payment'
        verbose_name_plural = 'Booking Payments'
        ordering = ['-payment_date']

    def __str__(self):
        return f"${self.amount} for {self.booking.booking_reference} on {self.payment_date.strftime('%Y-%m-%d %H:%M')}"


class EmailTemplate(models.Model):
    """
    Customizable email templates (skeletons) for different notification triggers.
    """
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='email_templates',
    )
    email_type = models.CharField(
        max_length=20,
        choices=[
            ('processing', 'Booking Processing'),
            ('confirmed', 'Booking Confirmed'),
            ('reminder_12h', '12h Pickup Reminder'),
            ('cancelled', 'Booking Cancelled'),
        ],
    )
    subject = models.CharField(max_length=255)
    html_content = models.TextField(
        help_text='HTML template content. Placeholders: {customer_name}, {booking_reference}, {pickup_date}, {pickup_time}, {return_date}, {return_time}, {total_price}, {amount_paid}, {balance}, {pickup_address}, {dropoff_address}, {service_type}, {flight_number}'
    )
    text_content = models.TextField(
        help_text='Plain text template content. Placeholders same as HTML.'
    )

    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
        unique_together = [['site', 'email_type']]

    def __str__(self):
        return f"{self.get_email_type_display()} ({self.site.slug.upper()})"


class WhatsAppTemplate(models.Model):
    """
    Customizable WhatsApp templates for different notification triggers.
    """
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='whatsapp_templates',
    )
    trigger_type = models.CharField(
        max_length=20,
        choices=[
            ('processing', 'Booking Processing'),
            ('confirmed', 'Booking Confirmed'),
            ('reminder_12h', '12h Pickup Reminder'),
            ('cancelled', 'Booking Cancelled'),
        ],
    )
    message_content = models.TextField(
        help_text='WhatsApp message content. Placeholders: {customer_name}, {booking_reference}, {pickup_date}, {pickup_time}, {return_date}, {return_time}, {total_price}, {amount_paid}, {balance}, {pickup_address}, {dropoff_address}, {service_type}, {flight_number}'
    )

    class Meta:
        verbose_name = 'WhatsApp Template'
        verbose_name_plural = 'WhatsApp Templates'
        unique_together = [['site', 'trigger_type']]

    def __str__(self):
        return f"{self.get_trigger_type_display()} ({self.site.slug.upper()})"

