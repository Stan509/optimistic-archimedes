"""
AeroLux Select — Public Site Views

Handles all client-facing pages for both NYC and DR sites.
The current site is determined by the SiteMiddleware.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_GET
from django.conf import settings
from datetime import date, timedelta, datetime
import json


def _get_site_or_404(request):
    """Get the current site from request, or return a default context."""
    site = getattr(request, 'current_site', None)
    slug = getattr(request, 'current_site_slug', 'nyc')
    return site, slug


def _get_language(request):
    """Get the current language from session."""
    slug = getattr(request, 'current_site_slug', 'nyc')
    if slug == 'nyc':
        return 'en'
    return request.session.get('language', 'en')


# =========================================================================
# HOME PAGE
# =========================================================================

def index(request):
    """
    Main landing page with:
    - Hero section with booking form
    - Services overview
    - Fleet carousel
    - Testimonials
    - Why choose us
    """
    site, slug = _get_site_or_404(request)

    try:
        from core.models import Airport, VehicleCategory, Testimonial, SiteContent
        airports = Airport.objects.filter(site=site, is_active=True) if site else Airport.objects.none()
        vehicle_categories = VehicleCategory.objects.filter(is_active=True).order_by('order')
        testimonials = Testimonial.objects.filter(site=site, is_featured=True) if site else Testimonial.objects.none()
    except Exception:
        airports = []
        vehicle_categories = []
        testimonials = []

    context = {
        'airports': airports,
        'vehicle_categories': vehicle_categories,
        'testimonials': testimonials,
        'today': date.today().strftime('%Y-%m-%d'),
        'min_time': '00:00',
        'site_slug': slug,
        'language': _get_language(request),
    }
    return render(request, 'core/index.html', context)


# =========================================================================
# SERVICES PAGES
# =========================================================================

def services(request):
    """Services overview page listing all three service types."""
    site, slug = _get_site_or_404(request)

    try:
        from core.models import PremiumAddOn
        addons = PremiumAddOn.objects.filter(is_active=True)
    except Exception:
        addons = []

    context = {
        'addons': addons,
        'site_slug': slug,
        'language': _get_language(request),
    }
    return render(request, 'core/services.html', context)


def airport_transfer(request):
    """Airport transfer service page with airport selection."""
    site, slug = _get_site_or_404(request)

    try:
        from core.models import Airport
        airports = Airport.objects.filter(site=site, is_active=True) if site else Airport.objects.none()
    except Exception:
        airports = []

    context = {
        'airports': airports,
        'site_slug': slug,
        'language': _get_language(request),
        'today': date.today().strftime('%Y-%m-%d'),
    }
    return render(request, 'core/airport_transfer.html', context)



def hourly_service(request):
    """Hourly service page."""
    site, slug = _get_site_or_404(request)

    try:
        from core.models import VehicleCategory
        categories = VehicleCategory.objects.filter(is_active=True).order_by('order')
    except Exception:
        categories = []

    context = {
        'categories': categories,
        'hourly_min': settings.HOURLY_MIN_HOURS,
        'hourly_rate_min': settings.HOURLY_RATE_RANGE['min'],
        'hourly_rate_max': settings.HOURLY_RATE_RANGE['max'],
        'site_slug': slug,
        'language': _get_language(request),
        'today': date.today().strftime('%Y-%m-%d'),
    }
    return render(request, 'core/hourly_service.html', context)


def luxury_rental(request):
    """Luxury rental service page."""
    site, slug = _get_site_or_404(request)

    try:
        from core.models import VehicleCategory
        categories = VehicleCategory.objects.filter(is_active=True).order_by('order')
    except Exception:
        categories = []

    context = {
        'categories': categories,
        'site_slug': slug,
        'language': _get_language(request),
        'today': date.today().strftime('%Y-%m-%d'),
    }
    return render(request, 'core/luxury_rental.html', context)


# =========================================================================
# FLEET PAGE
# =========================================================================

def fleet(request):
    """Fleet overview page with all vehicle categories."""
    site, slug = _get_site_or_404(request)

    try:
        from core.models import VehicleCategory, Vehicle
        categories = VehicleCategory.objects.filter(is_active=True).order_by('order')
        vehicles = Vehicle.objects.filter(
            is_active=True,
            sites=site
        ).select_related('category') if site else Vehicle.objects.none()
    except Exception:
        categories = []
        vehicles = []

    context = {
        'categories': categories,
        'vehicles': vehicles,
        'site_slug': slug,
        'language': _get_language(request),
    }
    return render(request, 'core/fleet.html', context)


def fleet_detail(request, slug):
    """Detailed view of a vehicle category."""
    site, site_slug = _get_site_or_404(request)

    try:
        from core.models import VehicleCategory, Vehicle
        category = get_object_or_404(VehicleCategory, slug=slug, is_active=True)
        vehicles = Vehicle.objects.filter(
            category=category,
            is_active=True,
            sites=site
        ) if site else Vehicle.objects.none()
    except Exception:
        category = None
        vehicles = []

    context = {
        'category': category,
        'vehicles': vehicles,
        'site_slug': site_slug,
        'language': _get_language(request),
    }
    return render(request, 'core/fleet_detail.html', context)


# =========================================================================
# BOOKING FLOW (Multi-step)
# =========================================================================

def booking_step1(request):
    """
    Step 1: Select service type, airport, destination, date/time.
    Data is stored in session for the multi-step flow.
    """
    site, slug = _get_site_or_404(request)

    if request.method == 'POST':
        service_type = request.POST.get('service_type', 'airport_transfer')
        round_trip = request.POST.get('round_trip') == 'on'
        
        # 1. Hourly validations
        if service_type == 'hourly':
            try:
                hours = int(request.POST.get('hours_requested', 3))
            except ValueError:
                hours = 3
            if hours < 3 or hours > 12:
                messages.error(request, 'Hourly service requires a minimum of 3 hours and is limited to a maximum of 12 hours.')
                return redirect(f'/{slug}/book/')

        # 2. Round-trip validations
        if round_trip and service_type in ['airport_transfer', 'point_to_point']:
            return_date = request.POST.get('return_date', '')
            return_time = request.POST.get('return_time', '')
            if not return_date or not return_time:
                messages.error(request, 'Return date and time are required for round-trip bookings.')
                return redirect(f'/{slug}/book/')

        # Store selections in session
        request.session['booking'] = {
            'service_type': service_type,
            'airport_id': request.POST.get('airport_id'),
            'destination_id': request.POST.get('destination_id', ''),
            'destination_address': request.POST.get('destination_address', ''),
            'transfer_direction': request.POST.get('transfer_direction', 'AIRPORT_TO_DEST'),
            'meeting_point': request.POST.get('meeting_point', ''),
            'pickup_address': request.POST.get('pickup_address', ''),
            'dropoff_address': request.POST.get('dropoff_address', ''),
            'pickup_date': request.POST.get('pickup_date'),
            'pickup_time': request.POST.get('pickup_time'),
            'flight_number': request.POST.get('flight_number', ''),
            'hours_requested': request.POST.get('hours_requested', '3'),
            'round_trip': round_trip,
            'return_date': request.POST.get('return_date', ''),
            'return_time': request.POST.get('return_time', ''),
            'number_of_stops': int(request.POST.get('number_of_stops', 0)) if request.POST.get('number_of_stops') else 0,
            'stop_addresses': request.POST.get('stop_addresses', ''),
            'site_slug': slug,
        }
        return redirect(f'/{slug}/book/vehicle/')

    try:
        from core.models import Airport
        airports = Airport.objects.filter(site=site, is_active=True) if site else Airport.objects.none()
    except Exception:
        airports = []

    context = {
        'airports': airports,
        'site_slug': slug,
        'today': date.today().strftime('%Y-%m-%d'),
        'language': _get_language(request),
    }
    return render(request, 'core/booking_step1.html', context)


def booking_step2(request):
    """
    Step 2: Select vehicle category.
    Shows available vehicles with pricing.
    """
    site, slug = _get_site_or_404(request)
    booking_data = request.session.get('booking', {})

    if not booking_data:
        messages.warning(request, 'Please start your booking from the beginning.')
        return redirect(f'/{slug}/book/')

    # Calculate pricing for each vehicle category
    try:
        from core.models import VehicleCategory, PricingRule, Airport, Destination
        categories = VehicleCategory.objects.filter(is_active=True).order_by('order')

        # Get pricing based on route
        airport_id = booking_data.get('airport_id')
        destination_id = booking_data.get('destination_id')
        service_type = booking_data.get('service_type', 'airport_transfer')

        category_prices = {}
        for cat in categories:
            # Check if there is at least one active vehicle in this category for the current site
            if not cat.vehicles.filter(is_active=True, sites=site).exists():
                category_prices[cat.id] = None
                continue

            if service_type == 'hourly':
                hours = int(booking_data.get('hours_requested', 3))
                if hours > 12:
                    hours = 12
                rule = PricingRule.objects.filter(
                    airport__site=site,
                    vehicle_category=cat,
                    service_type='hourly',
                    is_active=True
                ).first()
                hourly_rate = float(rule.base_price) if rule else float(settings.HOURLY_RATE_RANGE['min'])
                category_prices[cat.id] = hourly_rate * hours
            elif service_type == 'point_to_point':
                rule = PricingRule.objects.filter(
                    airport__site=site,
                    vehicle_category=cat,
                    service_type='point_to_point',
                    is_active=True
                ).first()
                base_price = float(rule.base_price) if rule else 80.0
                fare = base_price
                if booking_data.get('round_trip'):
                    fare = fare * 2.0
                stops = int(booking_data.get('number_of_stops', 0))
                category_prices[cat.id] = fare + (stops * 20.0)
            elif service_type == 'airport_transfer':
                # Address-based: use per-mile pricing from SiteSettings
                from core.models import SiteSettings
                site_settings = SiteSettings.get_settings(site)
                base_fee = float(site_settings.airport_base_fee) if site_settings else 15.0
                price_per_mile = float(site_settings.price_per_mile) if site_settings else 3.5

                # Check for fixed-price zone rules first
                zone_rule = PricingRule.objects.filter(
                    airport__site=site,
                    vehicle_category=cat,
                    service_type='airport_transfer',
                    is_active=True,
                    zone_min_distance_km__isnull=False,
                ).first()
                if zone_rule:
                    fare = float(zone_rule.base_price)
                else:
                    # Fallback: use a standard per-mile estimate (20 miles default)
                    fare = base_fee + (price_per_mile * 20)

                if booking_data.get('round_trip'):
                    fare = fare * 2.0
                category_prices[cat.id] = fare
            elif service_type == 'luxury_rental':
                rule = PricingRule.objects.filter(
                    airport__site=site,
                    vehicle_category=cat,
                    service_type='luxury_rental',
                    is_active=True
                ).first()
                base_price = float(rule.base_price) if rule else 150.0
                fare = base_price
                if booking_data.get('round_trip'):
                    fare = fare * 2.0
                category_prices[cat.id] = fare
            else:
                category_prices[cat.id] = None
    except Exception as e:
        categories = []
        category_prices = {}

    if request.method == 'POST':
        category_id = request.POST.get('vehicle_category_id')
        booking_data['vehicle_category_id'] = category_id
        
        # Save pure base price (before stops and round trip multiplier)
        pure_price = 0.0
        if service_type == 'hourly':
            rule = PricingRule.objects.filter(
                airport__site=site,
                vehicle_category_id=category_id,
                service_type='hourly',
                is_active=True
            ).first()
            pure_price = float(rule.base_price) if rule else float(settings.HOURLY_RATE_RANGE['min'])
        elif service_type == 'point_to_point':
            rule = PricingRule.objects.filter(
                airport__site=site,
                vehicle_category_id=category_id,
                service_type='point_to_point',
                is_active=True
            ).first()
            pure_price = float(rule.base_price) if rule else 80.0
        elif service_type == 'luxury_rental':
            rule = PricingRule.objects.filter(
                airport__site=site,
                vehicle_category_id=category_id,
                service_type='luxury_rental',
                is_active=True
            ).first()
            pure_price = float(rule.base_price) if rule else 150.0
        else:
            # Airport transfer - use per-mile pricing
            from core.models import SiteSettings
            site_settings = SiteSettings.get_settings(site)
            base_fee = float(site_settings.airport_base_fee) if site_settings else 15.0
            ppm = float(site_settings.price_per_mile) if site_settings else 3.5

            zone_rule = PricingRule.objects.filter(
                airport__site=site,
                vehicle_category_id=category_id,
                service_type='airport_transfer',
                is_active=True,
                zone_min_distance_km__isnull=False,
            ).first()
            if zone_rule:
                pure_price = float(zone_rule.base_price)
            else:
                pure_price = base_fee + (ppm * 20)

        booking_data['base_price'] = pure_price
        request.session['booking'] = booking_data
        return redirect(f'/{slug}/book/details/')

    context = {
        'categories': categories,
        'category_prices': category_prices,
        'booking_data': booking_data,
        'site_slug': slug,
        'language': _get_language(request),
    }
    return render(request, 'core/booking_step2.html', context)


def booking_step3(request):
    """
    Step 3: Enter customer details and select add-ons.
    """
    site, slug = _get_site_or_404(request)
    booking_data = request.session.get('booking', {})

    if not booking_data or not booking_data.get('vehicle_category_id'):
        messages.warning(request, 'Please select a vehicle first.')
        return redirect(f'/{slug}/book/vehicle/')

    try:
        from core.models import PremiumAddOn, VehicleCategory
        addons = PremiumAddOn.objects.filter(is_active=True)
        category = VehicleCategory.objects.get(id=booking_data['vehicle_category_id'])
    except Exception:
        addons = []
        category = None

    if request.method == 'POST':
        booking_data['customer_name'] = request.POST.get('customer_name', '')
        booking_data['customer_email'] = request.POST.get('customer_email', '')
        booking_data['customer_phone'] = request.POST.get('customer_phone', '')
        booking_data['customer_whatsapp'] = request.POST.get('customer_whatsapp', '')
        booking_data['customer_notes'] = request.POST.get('customer_notes', '')
        booking_data['selected_addons'] = request.POST.getlist('addons', [])
        request.session['booking'] = booking_data
        return redirect(f'/{slug}/book/payment/')

    # Calculate fare displaying on details step
    base_price = booking_data.get('base_price', 0) or 0
    fare = float(base_price)
    service_type = booking_data.get('service_type', 'airport_transfer')
    if service_type == 'hourly':
        hours = int(booking_data.get('hours_requested', 3))
        fare = fare * hours
    else:
        if booking_data.get('round_trip'):
            fare = fare * 2.0
        if service_type == 'point_to_point':
            stops = int(booking_data.get('number_of_stops', 0))
            fare = fare + (stops * 20.0)

    context = {
        'addons': addons,
        'category': category,
        'booking_data': booking_data,
        'base_price': fare,
        'site_slug': slug,
        'language': _get_language(request),
    }
    return render(request, 'core/booking_step3.html', context)


def booking_payment(request):
    """
    Step 4: Payment page (Stripe integration).
    Creates the booking and processes payment.
    """
    site, slug = _get_site_or_404(request)
    booking_data = request.session.get('booking', {})

    if not booking_data or not booking_data.get('customer_name'):
        messages.warning(request, 'Please fill in your details first.')
        return redirect(f'/{slug}/book/details/')

    try:
        from core.models import (
            Booking, VehicleCategory, Airport, Destination,
            PremiumAddOn, SiteSettings
        )

        if request.method == 'POST':
            # Verify terms validation
            if not request.POST.get('terms'):
                messages.error(request, 'You must accept the Terms & Conditions to complete your booking.')
                return redirect(f'/{slug}/book/payment/')

            # Enforce payment method validation
            payment_method = request.POST.get('payment_method')
            if payment_method not in ['STRIPE', 'CASH']:
                messages.error(request, 'Please select a valid payment method.')
                return redirect(f'/{slug}/book/payment/')

            if payment_method == 'STRIPE':
                cardholder_name = request.POST.get('cardholder_name', '').strip()
                card_number = ''.join(c for c in request.POST.get('card_number', '') if c.isdigit())
                card_expiry = request.POST.get('card_expiry', '').strip()
                card_cvc = ''.join(c for c in request.POST.get('card_cvc', '') if c.isdigit())

                if not cardholder_name:
                    messages.error(request, 'Cardholder name is required for credit card payment.')
                    return redirect(f'/{slug}/book/payment/')

                if len(card_number) != 16:
                    messages.error(request, 'Please enter a valid 16-digit card number.')
                    return redirect(f'/{slug}/book/payment/')

                import re
                expiry_match = re.match(r'^(0[1-9]|1[0-2])/([0-9]{2})$', card_expiry)
                if not expiry_match:
                    messages.error(request, 'Please enter expiration date in MM/YY format (e.g. 12/28).')
                    return redirect(f'/{slug}/book/payment/')

                exp_month = int(expiry_match.group(1))
                exp_year = int('20' + expiry_match.group(2))
                
                today_date = date.today()
                current_year = today_date.year
                current_month = today_date.month

                if exp_year < current_year or (exp_year == current_year and exp_month < current_month):
                    messages.error(request, 'The credit card has expired. Please use a valid card.')
                    return redirect(f'/{slug}/book/payment/')

                if len(card_cvc) not in [3, 4]:
                    messages.error(request, 'Please enter a valid 3 or 4-digit CVC code.')
                    return redirect(f'/{slug}/book/payment/')

            # Create the booking
            booking = Booking(
                site=site,
                service_type=booking_data.get('service_type', 'airport_transfer'),
                transfer_direction=booking_data.get('transfer_direction', 'AIRPORT_TO_DEST'),
                meeting_point=booking_data.get('meeting_point', ''),
                customer_name=booking_data['customer_name'],
                customer_email=booking_data['customer_email'],
                customer_phone=booking_data['customer_phone'],
                customer_whatsapp=booking_data.get('customer_whatsapp', ''),
                pickup_address=booking_data.get('pickup_address', ''),
                dropoff_address=booking_data.get('destination_address', '') or booking_data.get('dropoff_address', ''),
                pickup_date=booking_data.get('pickup_date'),
                pickup_time=booking_data.get('pickup_time'),
                flight_number=booking_data.get('flight_number', ''),
                customer_notes=booking_data.get('customer_notes', ''),
                booking_source='DIRECT',
                round_trip=booking_data.get('round_trip', False),
                return_date=booking_data.get('return_date') or None,
                return_time=booking_data.get('return_time') or None,
                number_of_stops=booking_data.get('number_of_stops', 0),
                stop_addresses=booking_data.get('stop_addresses', ''),
            )

            # Set foreign keys
            airport_id = booking_data.get('airport_id')
            if airport_id:
                booking.airport_id = int(airport_id)

            dest_id = booking_data.get('destination_id')
            if dest_id:
                booking.destination_id = int(dest_id)

            cat_id = booking_data.get('vehicle_category_id')
            if cat_id:
                booking.vehicle_category_id = int(cat_id)

            # Set hourly fields
            from decimal import Decimal
            if booking_data.get('service_type') == 'hourly':
                booking.hours_requested = int(booking_data.get('hours_requested', 3))
                from core.models import PricingRule
                rule = PricingRule.objects.filter(
                    airport__site=site,
                    vehicle_category_id=booking.vehicle_category_id,
                    service_type='hourly',
                    is_active=True
                ).first()
                booking.hourly_rate = Decimal(str(rule.base_price if rule else settings.HOURLY_RATE_RANGE['min']))

            # Set pricing
            base_price = booking_data.get('base_price', 0) or 0
            booking.base_price = Decimal(str(base_price))

            # Calculate add-ons total
            addon_ids = booking_data.get('selected_addons', [])
            addons_total = Decimal('0.00')
            if addon_ids:
                addons = PremiumAddOn.objects.filter(id__in=addon_ids)
                addons_total = sum(a.price for a in addons)
            booking.addons_total = addons_total

            booking.calculate_total()
            booking.payment_method = request.POST.get('payment_method', 'STRIPE')

            booking.save()

            # Add selected add-ons
            if addon_ids:
                booking.addons.set(addon_ids)

            # --- Trigger Automated Email Confirmations ---
            try:
                from core.emails import send_booking_emails
                send_booking_emails(booking)
            except Exception as email_err:
                print(f"Error triggering emails: {str(email_err)}")

            # Clear booking session
            if 'booking' in request.session:
                del request.session['booking']

            return redirect(f'/{slug}/book/success/{booking.booking_reference}/')

        # GET — Show payment form
        site_settings = SiteSettings.get_settings(site)
        base_price = booking_data.get('base_price', 0) or 0
        fare = float(base_price)
        service_type = booking_data.get('service_type', 'airport_transfer')
        if service_type == 'hourly':
            hours = int(booking_data.get('hours_requested', 3))
            fare = fare * hours
        else:
            if booking_data.get('round_trip'):
                fare = fare * 2.0
            if service_type == 'point_to_point':
                stops = int(booking_data.get('number_of_stops', 0))
                fare = fare + (stops * 20.0)

        # Calculate add-ons total
        addon_ids = booking_data.get('selected_addons', [])
        addons_total = 0
        selected_addons = []
        if addon_ids:
            selected_addons = list(PremiumAddOn.objects.filter(id__in=addon_ids))
            addons_total = sum(a.price for a in selected_addons)

        total = fare + float(addons_total)

        context = {
            'booking_data': booking_data,
            'base_price': fare,
            'addons_total': addons_total,
            'selected_addons': selected_addons,
            'total_price': total,
            'stripe_public_key': site_settings.stripe_public_key if site_settings else '',
            'stripe_enabled': site_settings.stripe_enabled if site_settings else False,
            'site_slug': slug,
            'language': _get_language(request),
        }
        return render(request, 'core/booking_payment.html', context)

    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect(f'/{slug}/')


def booking_success(request, reference):
    """Booking confirmation page."""
    site, slug = _get_site_or_404(request)

    try:
        from core.models import Booking
        booking = get_object_or_404(Booking, booking_reference=reference)
    except Exception:
        booking = None

    context = {
        'booking': booking,
        'site_slug': slug,
        'language': _get_language(request),
    }
    return render(request, 'core/booking_success.html', context)


# =========================================================================
# CONTACT PAGE
# =========================================================================

def contact(request):
    """Contact page."""
    site, slug = _get_site_or_404(request)

    try:
        from core.models import SiteSettings
        site_settings = SiteSettings.get_settings(site)
    except Exception:
        site_settings = None

    context = {
        'site_settings': site_settings,
        'site_slug': slug,
        'language': _get_language(request),
    }
    return render(request, 'core/contact.html', context)


# =========================================================================
# API ENDPOINTS (AJAX)
# =========================================================================

@require_GET
def api_airports(request):
    """Return airports for the current site as JSON."""
    site, slug = _get_site_or_404(request)

    try:
        from core.models import Airport
        airports = Airport.objects.filter(
            site=site, is_active=True
        ).values('id', 'name', 'code', 'city', 'description')
        return JsonResponse({'airports': list(airports)})
    except Exception:
        return JsonResponse({'airports': []})


@require_GET
def api_destinations(request, airport_id):
    """Return destinations for a specific airport as JSON."""
    try:
        from core.models import Destination
        destinations = Destination.objects.filter(
            airport_id=airport_id, is_active=True
        ).values('id', 'name', 'address', 'destination_type', 'description')
        return JsonResponse({'destinations': list(destinations)})
    except Exception:
        return JsonResponse({'destinations': []})


@require_GET
def api_pricing(request):
    """
    Return pricing for a route.
    Query params: airport_id, destination_id, vehicle_category_id, service_type
    """
    try:
        from core.models import PricingRule, Site, VehicleCategory

        airport_id = request.GET.get('airport_id')
        destination_id = request.GET.get('destination_id')
        category_id = request.GET.get('vehicle_category_id')
        service_type = request.GET.get('service_type', 'airport_transfer')
        round_trip = request.GET.get('round_trip') == 'true'

        site, slug = _get_site_or_404(request)

        if service_type == 'hourly':
            hours = int(request.GET.get('hours', 3))
            if hours > 12:
                hours = 12
            pricing = []
            categories = VehicleCategory.objects.filter(is_active=True).order_by('order')
            if category_id:
                categories = categories.filter(id=category_id)
            for cat in categories:
                rule = PricingRule.objects.filter(
                    airport__site=site,
                    vehicle_category=cat,
                    service_type='hourly',
                    is_active=True
                ).first()
                hourly_rate = float(rule.base_price) if rule else float(settings.HOURLY_RATE_RANGE['min'])
                pricing.append({
                    'vehicle_category': cat.name,
                    'vehicle_category_id': cat.id,
                    'base_price': hourly_rate * hours,
                    'hourly_rate': hourly_rate,
                    'hours': hours,
                    'service_type': 'hourly',
                })
            return JsonResponse({'pricing': pricing})

        elif service_type == 'point_to_point':
            stops = int(request.GET.get('number_of_stops', 0))
            pricing = []
            categories = VehicleCategory.objects.filter(is_active=True).order_by('order')
            if category_id:
                categories = categories.filter(id=category_id)
            for cat in categories:
                rule = PricingRule.objects.filter(
                    airport__site=site,
                    vehicle_category=cat,
                    service_type='point_to_point',
                    is_active=True
                ).first()
                base_price = float(rule.base_price) if rule else 80.0
                
                fare = base_price
                if round_trip:
                    fare = fare * 2.0
                total = fare + (stops * 20.0)
                
                pricing.append({
                    'vehicle_category': cat.name,
                    'vehicle_category_id': cat.id,
                    'base_price': total,
                    'starting_price': base_price,
                    'service_type': 'point_to_point',
                })
            return JsonResponse({'pricing': pricing})

        elif service_type == 'luxury_rental':
            pricing = []
            categories = VehicleCategory.objects.filter(is_active=True).order_by('order')
            if category_id:
                categories = categories.filter(id=category_id)
            for cat in categories:
                rule = PricingRule.objects.filter(
                    airport__site=site,
                    vehicle_category=cat,
                    service_type='luxury_rental',
                    is_active=True
                ).first()
                base_price = float(rule.base_price) if rule else 150.0
                
                fare = base_price
                if round_trip:
                    fare = fare * 2.0
                pricing.append({
                    'vehicle_category': cat.name,
                    'vehicle_category_id': cat.id,
                    'base_price': fare,
                    'starting_price': base_price,
                    'service_type': 'luxury_rental',
                })
            return JsonResponse({'pricing': pricing})

        if not all([airport_id, destination_id]):
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        filters = {
            'airport_id': airport_id,
            'destination_id': destination_id,
            'service_type': 'airport_transfer',
            'is_active': True,
        }
        if category_id:
            filters['vehicle_category_id'] = category_id

        rules = PricingRule.objects.filter(**filters)

        if rules.exists():
            pricing = []
            for rule in rules:
                base_price = float(rule.base_price)
                if round_trip:
                    base_price = base_price * 2.0
                pricing.append({
                    'vehicle_category': rule.vehicle_category.name,
                    'vehicle_category_id': rule.vehicle_category.id,
                    'base_price': base_price,
                    'minimum_price': float(rule.minimum_price),
                    'zone': rule.zone_name,
                })
            return JsonResponse({'pricing': pricing})
        else:
            return JsonResponse({'pricing': [], 'message': 'No pricing available for this route'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# =========================================================================
# LANGUAGE SWITCH
# =========================================================================

def set_language(request, lang):
    """Switch language for the current site."""
    site, slug = _get_site_or_404(request)
    available = settings.SITE_LANGUAGES.get(slug, ['en'])

    if lang in available:
        request.session['language'] = lang

    # Redirect back to referrer or home
    referer = request.META.get('HTTP_REFERER', f'/{slug}/')
    return redirect(referer)


from django.http import HttpResponse
from django.views.decorators.http import require_GET

@require_GET
def service_worker(request):
    """Serve the PWA Service Worker."""
    sw_code = """
const CACHE_NAME = 'aeroluxe-cache-v1';
self.addEventListener('install', event => {
    self.skipWaiting();
});
self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
"""
    return HttpResponse(sw_code, content_type="application/javascript")
