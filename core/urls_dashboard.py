"""
Core app — Dashboard URL patterns.
Unified dashboard for managing both NYC and DR sites.
"""

from django.urls import path
from . import views_dashboard as views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard Authentication
    path('login/', views.dashboard_login, name='login'),
    path('logout/', views.dashboard_logout, name='logout'),

    # Dashboard Home
    path('', views.dashboard_index, name='index'),

    # Bookings Management
    path('bookings/', views.dashboard_bookings, name='bookings'),
    path('bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/status/<str:new_status>/', views.update_booking_status, name='update_booking_status'),

    # Fleet Management
    path('fleet/', views.dashboard_fleet, name='fleet'),
    path('fleet/categories/', views.fleet_categories, name='fleet_categories'),
    path('fleet/categories/add/', views.fleet_category_form, name='add_category'),
    path('fleet/categories/<slug:slug>/edit/', views.fleet_category_form, name='edit_category'),
    path('fleet/vehicles/', views.fleet_vehicles, name='fleet_vehicles'),
    path('fleet/vehicles/add/', views.fleet_vehicle_form, name='add_vehicle'),
    path('fleet/vehicles/<int:pk>/edit/', views.fleet_vehicle_form, name='edit_vehicle'),
    path('fleet/vehicles/<int:pk>/toggle/', views.toggle_vehicle_active, name='toggle_vehicle_active'),

    # Airports & Destinations Management
    path('airports/', views.dashboard_airports, name='airports'),
    path('airports/add/', views.airport_form, name='add_airport'),
    path('airports/<int:pk>/edit/', views.airport_form, name='edit_airport'),
    path('airports/<int:airport_id>/destinations/', views.dashboard_destinations, name='destinations'),
    path('airports/<int:airport_id>/destinations/add/', views.destination_form, name='add_destination'),
    path('destinations/<int:pk>/edit/', views.destination_form, name='edit_destination'),

    # Pricing Management
    path('pricing/', views.dashboard_pricing, name='pricing'),
    path('pricing/add/', views.pricing_form, name='add_pricing'),
    path('pricing/<int:pk>/edit/', views.pricing_form, name='edit_pricing'),

    # CMS - Site Content Editors
    path('cms/nyc/', views.cms_editor, {'site_slug': 'nyc'}, name='cms_nyc'),
    path('cms/dr/', views.cms_editor, {'site_slug': 'dr'}, name='cms_dr'),

    # Premium Add-Ons
    path('addons/', views.dashboard_addons, name='addons'),
    path('addons/add/', views.addon_form, name='add_addon'),
    path('addons/<int:pk>/edit/', views.addon_form, name='edit_addon'),

    # Profit Reports & Accounting
    path('reports/', views.dashboard_reports, name='reports'),
    path('reports/generate/', views.generate_report, name='generate_report'),

    # Settings
    path('settings/', views.dashboard_settings, name='settings'),

    # Stripe Configuration
    path('settings/stripe/', views.stripe_settings, name='stripe_settings'),

    # Email Configuration
    path('settings/email/', views.email_settings, name='email_settings'),
]
