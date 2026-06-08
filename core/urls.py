"""
Core app — Public site URL patterns.
These URLs are included twice with different namespace prefixes (site_nyc, site_dr).
The SiteMiddleware determines which site content to serve.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Home
    path('', views.index, name='index'),

    # Services
    path('services/', views.services, name='services'),
    path('services/airport-transfer/', views.airport_transfer, name='airport_transfer'),
    path('services/hourly/', views.hourly_service, name='hourly_service'),
    path('services/luxury-rental/', views.luxury_rental, name='luxury_rental'),

    # Fleet
    path('fleet/', views.fleet, name='fleet'),
    path('fleet/<slug:slug>/', views.fleet_detail, name='fleet_detail'),

    # Booking flow
    path('book/', views.booking_step1, name='booking_step1'),
    path('book/vehicle/', views.booking_step2, name='booking_step2'),
    path('book/details/', views.booking_step3, name='booking_step3'),
    path('book/payment/', views.booking_payment, name='booking_payment'),
    path('book/success/<str:reference>/', views.booking_success, name='booking_success'),

    # Contact
    path('contact/', views.contact, name='contact'),

    # API-like endpoints for AJAX
    path('api/airports/', views.api_airports, name='api_airports'),
    path('api/destinations/<int:airport_id>/', views.api_destinations, name='api_destinations'),
    path('api/pricing/', views.api_pricing, name='api_pricing'),

    # Language switch
    path('set-language/<str:lang>/', views.set_language, name='set_language'),

    # PWA service worker
    path('sw.js', views.service_worker, name='service_worker'),
]
