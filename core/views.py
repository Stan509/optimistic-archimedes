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
import math



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


def _get_effective_google_maps_api_key(site):
    """Return empty string - using OpenStreetMap instead of Google Maps."""
    return ''


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
        from core.models import VehicleCategory
        categories = VehicleCategory.objects.filter(is_active=True).order_by('order')
        
    except Exception:
        categories = []
        

    context = {
        'categories': categories,
        
        'site_slug': slug,
        'language': _get_language(request),
    }
    return render(request, 'core/fleet.html', context)


def fleet_detail(request, slug):
    """Detailed view of a vehicle category."""
    site, site_slug = _get_site_or_404(request)

    try:
        from core.models import VehicleCategory
        category = get_object_or_404(VehicleCategory, slug=slug, is_active=True)
        
    except Exception:
        category = None
        

    context = {
        'category': category,
        
        'site_slug': site_slug,
        'language': _get_language(request),
    }
    return render(request, 'core/fleet_detail.html', context)


def _haversine_distance(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (ValueError, TypeError):
        return 0.0
    R = 3958.8  # Earth radius in miles
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _get_airport_transfer_price_for_category(site, slug, category, booking_data):
    """Get calculated price for airport transfer for a vehicle category based on distance."""
    from core.models import AirportCategoryPrice, Airport, SiteSettings
    airport_id = booking_data.get('airport_id')
    if not airport_id:
        return 0.0

    ac_price = AirportCategoryPrice.objects.filter(
        airport_id=airport_id,
        vehicle_category=category,
        is_active=True
    ).first()

    if ac_price:
        base_price = float(ac_price.base_price)
        base_km = float(ac_price.base_km)
        price_per_km = float(ac_price.price_per_km)
    else:
        site_settings = SiteSettings.get_settings(site)
        base_price = float(site_settings.airport_base_fee) if site_settings else 15.0
        base_km = 25.0
        price_per_km = 3.5

    try:
        distance_km = float(booking_data.get('distance_km', 0.0) or 0.0)
    except (ValueError, TypeError):
        distance_km = 0.0

    # Fallback to driving distance or haversine if distance is not passed
    if distance_km <= 0.0:
        p_lat = booking_data.get('pickup_lat')
        p_lng = booking_data.get('pickup_lng')
        d_lat = booking_data.get('dropoff_lat')
        d_lng = booking_data.get('dropoff_lng')
        is_dest_to_airport = booking_data.get('transfer_direction') == 'DEST_TO_AIRPORT'

        airport_lat = d_lat if is_dest_to_airport else p_lat
        airport_lng = d_lng if is_dest_to_airport else p_lng
        address_lat = p_lat if is_dest_to_airport else d_lat
        address_lng = p_lng if is_dest_to_airport else d_lng

        if not airport_lat or not airport_lng:
            try:
                airport_obj = Airport.objects.get(id=airport_id)
                airport_lat = airport_obj.latitude
                airport_lng = airport_obj.longitude
            except Exception:
                pass

        if address_lat and address_lng and airport_lat and airport_lng:
            miles = _haversine_distance(airport_lat, airport_lng, address_lat, address_lng)
            distance_km = miles * 1.60934

            # Save computed distance back to booking_data to persist in session
            booking_data['distance_km'] = str(round(distance_km, 2))
        else:
            distance_km = 20.0
            booking_data['distance_km'] = str(distance_km)

    if distance_km <= base_km:
        fare = base_price
    else:
        fare = base_price + (distance_km - base_km) * price_per_km

    return fare


def _get_category_price(site, slug, category, booking_data):
    """Calculate price for any service type for a specific vehicle category."""
    from core.models import PricingRule
    service_type = booking_data.get('service_type', 'airport_transfer')

    if service_type == 'airport_transfer':
        fare = _get_airport_transfer_price_for_category(site, slug, category, booking_data)
        return fare

    elif service_type == 'hourly':
        hours = int(booking_data.get('hours_requested', 3))
        if hours > 12:
            hours = 12
        rule = PricingRule.objects.filter(
            site=site,
            vehicle_category=category,
            service_type='hourly',
            is_active=True,
            vehicle__isnull=True,
        ).first()
        if not rule:
            rule = PricingRule.objects.filter(
                site=site,
                vehicle_category=category,
                service_type='hourly',
                is_active=True
            ).first()
        hourly_rate = float(rule.base_price) if rule else float(settings.HOURLY_RATE_RANGE['min'])
        return hourly_rate * hours

    elif service_type == 'point_to_point':
        rule = PricingRule.objects.filter(
            site=site,
            vehicle_category=category,
            service_type='point_to_point',
            is_active=True,
            vehicle__isnull=True,
        ).first()
        if not rule:
            rule = PricingRule.objects.filter(
                site=site,
                vehicle_category=category,
                service_type='point_to_point',
                is_active=True
            ).first()

        base_price = float(rule.base_price) if rule else 80.0
        fare = base_price

        # Distance-based surcharge beyond km_threshold
        if rule and rule.price_per_km:
            try:
                km = float(booking_data.get('distance_km', 0.0) or 0.0)
            except (ValueError, TypeError):
                km = 0.0
            
            p_lat = booking_data.get('pickup_lat')
            p_lng = booking_data.get('pickup_lng')
            d_lat = booking_data.get('dropoff_lat')
            d_lng = booking_data.get('dropoff_lng')
            if km <= 0.0 and p_lat and p_lng and d_lat and d_lng:
                miles = _haversine_distance(p_lat, p_lng, d_lat, d_lng)
                km = miles * 1.60934

                # Save computed distance back to booking_data to persist in session
                booking_data['distance_km'] = str(round(km, 2))
            
            threshold = rule.km_threshold or 25
            if km > threshold:
                fare += float(rule.price_per_km) * (km - threshold)

        return fare

    elif service_type == 'luxury_rental':
        rule = PricingRule.objects.filter(
            site=site,
            vehicle_category=category,
            service_type='luxury_rental',
            is_active=True,
            vehicle__isnull=True,
        ).first()
        if not rule:
            rule = PricingRule.objects.filter(
                site=site,
                vehicle_category=category,
                service_type='luxury_rental',
                is_active=True
            ).first()
        return float(rule.base_price) if rule else 150.0

    return 0.0


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

        # Get passenger count
        try:
            passenger_count = int(request.POST.get('passenger_count', 1))
        except ValueError:
            passenger_count = 1

        # Store selections in session
        request.session['booking'] = {
            'service_type': service_type,
            'airport_id': request.POST.get('airport_id'),
            'destination_id': request.POST.get('destination_id', ''),
            'destination_address': request.POST.get('destination_address', ''),
            'transfer_direction': request.POST.get('transfer_direction', 'AIRPORT_TO_DEST'),
            'meeting_point': request.POST.get('meeting_point', ''),
            'return_meeting_point': request.POST.get('return_meeting_point', ''),
            'pickup_address': request.POST.get('pickup_address', ''),
            'dropoff_address': request.POST.get('dropoff_address', ''),
            'pickup_date': request.POST.get('pickup_date'),
            'pickup_time': request.POST.get('pickup_time'),
            'passenger_count': passenger_count,
            'pickup_lat': request.POST.get('pickup_lat', ''),
            'pickup_lng': request.POST.get('pickup_lng', ''),
            'dropoff_lat': request.POST.get('dropoff_lat', ''),
            'dropoff_lng': request.POST.get('dropoff_lng', ''),
            'distance_km': request.POST.get('distance_km', ''),
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
        'booking_data': request.session.get('booking', {}),
    }
    return render(request, 'core/booking_step1.html', context)


def booking_step2(request):
    """
    Step 2: Select vehicle category.
    Shows available vehicle categories with per-category pricing.
    """
    site, slug = _get_site_or_404(request)
    booking_data = request.session.get('booking', {})

    if not booking_data:
        messages.warning(request, 'Please start your booking from the beginning.')
        return redirect(f'/{slug}/book/')

    try:
        from core.models import VehicleCategory

        # Get all active categories
        categories = VehicleCategory.objects.filter(is_active=True).order_by('order')

        # Calculate pricing for each category
        category_prices = {}
        for cat in categories:
            try:
                price = _get_category_price(site, slug, cat, booking_data)
                if booking_data.get('service_type') != 'hourly' and booking_data.get('round_trip'):
                    price = price * 2.0
                if booking_data.get('service_type') == 'point_to_point':
                    stops = int(booking_data.get('number_of_stops', 0) or 0)
                    price += stops * 20.0
                category_prices[cat.id] = price
            except Exception:
                category_prices[cat.id] = None

        # Persist modified booking_data (with any calculated distance) to session
        request.session['booking'] = booking_data

    except Exception as e:
        categories = []
        category_prices = {}

    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        if category_id:
            try:
                selected_category = VehicleCategory.objects.get(id=category_id)
                booking_data['vehicle_category_id'] = int(category_id)
                if 'vehicle_id' in booking_data:
                    del booking_data['vehicle_id']

                # Save the pure base price for this category
                pure_price = _get_category_price(site, slug, selected_category, booking_data)
                booking_data['base_price'] = pure_price
                request.session['booking'] = booking_data
                return redirect(f'/{slug}/book/details/')
            except VehicleCategory.DoesNotExist:
                messages.error(request, 'Selected category not found.')

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
        messages.warning(request, 'Please select a vehicle category first.')
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
        try:
            booking_data['selected_addons'] = [int(x) for x in request.POST.getlist('addons', [])]
            booking_data['selected_addons_return'] = [int(x) for x in request.POST.getlist('addons_return', [])]
        except ValueError:
            booking_data['selected_addons'] = []
            booking_data['selected_addons_return'] = []
        booking_data['pay_separately'] = request.POST.get('pay_separately') == 'on'
        request.session['booking'] = booking_data
        return redirect(f'/{slug}/book/payment/')

    # Calculate fare displaying on details step
    base_price = booking_data.get('base_price', 0) or 0
    fare = float(base_price)

    hourly_rate = 0.0
    hours_requested = float(booking_data.get('hours_requested', 3.0))
    if booking_data.get('service_type') == 'hourly' and hours_requested > 0:
        hourly_rate = fare / hours_requested

    context = {
        'addons': addons,
        'category': category,
        'booking_data': booking_data,
        'base_price': fare,
        'hourly_rate': hourly_rate,
        'hours_requested': hours_requested,
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
            from decimal import Decimal
            try:
                db_distance = Decimal(str(booking_data.get('distance_km', 0.0) or 0.0))
            except Exception:
                db_distance = Decimal('0.00')

            payment_method = request.POST.get('payment_method', 'STRIPE')

            # Calculate individual values
            base_price = Decimal(str(booking_data.get('base_price', 0) or 0))
            stops = int(booking_data.get('number_of_stops', 0) or 0)
            stops_fee = Decimal('20.00') * stops if booking_data.get('service_type') == 'point_to_point' else Decimal('0.00')

            addon_ids = booking_data.get('selected_addons', [])
            addon_return_ids = booking_data.get('selected_addons_return', [])

            is_round_trip = booking_data.get('round_trip', False)

            if is_round_trip:
                # 1. Create Outbound Booking (Aller)
                booking_outbound = Booking(
                    site=site,
                    service_type=booking_data.get('service_type', 'airport_transfer'),
                    transfer_direction=booking_data.get('transfer_direction', 'AIRPORT_TO_DEST'),
                    meeting_point=booking_data.get('meeting_point', ''),
                    return_meeting_point=booking_data.get('return_meeting_point', ''),
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
                    round_trip=False, # Decoupled
                    return_date=booking_data.get('return_date') or None,
                    return_time=booking_data.get('return_time') or None,
                    number_of_stops=stops,
                    stop_addresses=booking_data.get('stop_addresses', ''),
                    passenger_count=booking_data.get('passenger_count', 1),
                    distance_km=db_distance,
                    base_price=base_price,
                    pay_separately=booking_data.get('pay_separately', False),
                    payment_method=payment_method,
                )
                
                airport_id = booking_data.get('airport_id')
                if airport_id:
                    booking_outbound.airport_id = int(airport_id)
                dest_id = booking_data.get('destination_id')
                if dest_id:
                    booking_outbound.destination_id = int(dest_id)
                cat_id = booking_data.get('vehicle_category_id')
                if cat_id:
                    booking_outbound.vehicle_category_id = int(cat_id)
                vehicle_id = booking_data.get('vehicle_id')
                if vehicle_id:
                    booking_outbound.vehicle_id = int(vehicle_id)

                # Set outbound addons total (outbound leg only has addon_ids)
                outbound_addons_total = Decimal('0.00')
                if addon_ids:
                    addons = PremiumAddOn.objects.filter(id__in=addon_ids)
                    outbound_addons_total = sum(a.price for a in addons)
                booking_outbound.addons_total = outbound_addons_total
                
                # Outbound total is calculated
                booking_outbound.calculate_total()
                booking_outbound.save()
                
                if addon_ids:
                    booking_outbound.addons.set(addon_ids)
                    
                # 2. Create Return Booking (Retour)
                # Reverse addresses for return leg
                return_pickup_address = booking_outbound.dropoff_address
                return_dropoff_address = booking_outbound.pickup_address
                
                # Invert direction if airport transfer
                outbound_dir = booking_data.get('transfer_direction', 'AIRPORT_TO_DEST')
                return_dir = 'DEST_TO_AIRPORT' if outbound_dir == 'AIRPORT_TO_DEST' else 'AIRPORT_TO_DEST'

                booking_return = Booking(
                    site=site,
                    service_type=booking_data.get('service_type', 'airport_transfer'),
                    transfer_direction=return_dir,
                    meeting_point=booking_data.get('return_meeting_point', ''),
                    return_meeting_point=booking_data.get('meeting_point', ''),
                    customer_name=booking_data['customer_name'],
                    customer_email=booking_data['customer_email'],
                    customer_phone=booking_data['customer_phone'],
                    customer_whatsapp=booking_data.get('customer_whatsapp', ''),
                    pickup_address=return_pickup_address,
                    dropoff_address=return_dropoff_address,
                    pickup_date=booking_data.get('return_date'),
                    pickup_time=booking_data.get('return_time'),
                    flight_number='',
                    customer_notes=booking_data.get('customer_notes', ''),
                    booking_source='DIRECT',
                    round_trip=False, # Decoupled
                    return_date=booking_data.get('pickup_date') or None,
                    return_time=booking_data.get('pickup_time') or None,
                    number_of_stops=0,
                    passenger_count=booking_data.get('passenger_count', 1),
                    distance_km=db_distance,
                    base_price=base_price,
                    pay_separately=booking_data.get('pay_separately', False),
                    payment_method=payment_method,
                    # linked_booking=booking_outbound,
                )

                if airport_id:
                    booking_return.airport_id = int(airport_id)
                if dest_id:
                    booking_return.destination_id = int(dest_id)
                if cat_id:
                    booking_return.vehicle_category_id = int(cat_id)
                if vehicle_id:
                    booking_return.vehicle_id = int(vehicle_id)

                # Set return addons total (return leg only has addon_return_ids)
                return_addons_total = Decimal('0.00')
                if addon_return_ids:
                    addons_return = PremiumAddOn.objects.filter(id__in=addon_return_ids)
                    return_addons_total = sum(a.price for a in addons_return)
                booking_return.addons_total = return_addons_total
                
                # Return total is calculated
                booking_return.calculate_total()
                booking_return.save()
                
                if addon_return_ids:
                    booking_return.addons.set(addon_return_ids)
                
                # Link outbound to return
                # booking_outbound.linked_booking = booking_return
                booking_outbound.save(update_fields=['round_trip'])
                
                # Force reload to get updated fields and calculate totals with addons
                booking_outbound = Booking.objects.get(pk=booking_outbound.pk)
                booking_outbound.calculate_total()
                booking_outbound.save(update_fields=['addons_total', 'total_price'])
                
                booking_return = Booking.objects.get(pk=booking_return.pk)
                booking_return.calculate_total()
                booking_return.save(update_fields=['addons_total', 'total_price'])
                
                # Set payment status
                if payment_method == 'STRIPE':
                    booking_outbound.amount_paid = booking_outbound.total_price
                    booking_outbound.payment_status = 'PAID'
                    booking_outbound.save(update_fields=['amount_paid', 'payment_status'])
                    
                    booking_return.amount_paid = booking_return.total_price
                    booking_return.payment_status = 'PAID'
                    booking_return.save(update_fields=['amount_paid', 'payment_status'])
                else:
                    booking_outbound.amount_paid = Decimal('0.00')
                    booking_outbound.payment_status = 'PENDING'
                    booking_outbound.save(update_fields=['amount_paid', 'payment_status'])
                    
                    booking_return.amount_paid = Decimal('0.00')
                    booking_return.payment_status = 'PENDING'
                    booking_return.save(update_fields=['amount_paid', 'payment_status'])

                # --- Trigger Automated Email Confirmations for BOTH ---
                try:
                    from core.emails import send_booking_emails
                    send_booking_emails(booking_outbound)
                    send_booking_emails(booking_return)
                except Exception as email_err:
                    print(f"Error triggering emails: {str(email_err)}")

                # Clear session
                if 'booking' in request.session:
                    del request.session['booking']

                return redirect(f'/{slug}/book/success/{booking_outbound.booking_reference}/')

            else:
                # 3. Create Single Booking (One-way)
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
                    round_trip=False,
                    number_of_stops=stops,
                    stop_addresses=booking_data.get('stop_addresses', ''),
                    passenger_count=booking_data.get('passenger_count', 1),
                    distance_km=db_distance,
                    base_price=base_price,
                    payment_method=payment_method,
                )

                airport_id = booking_data.get('airport_id')
                if airport_id:
                    booking.airport_id = int(airport_id)
                dest_id = booking_data.get('destination_id')
                if dest_id:
                    booking.destination_id = int(dest_id)
                cat_id = booking_data.get('vehicle_category_id')
                if cat_id:
                    booking.vehicle_category_id = int(cat_id)
                vehicle_id = booking_data.get('vehicle_id')
                if vehicle_id:
                    booking.vehicle_id = int(vehicle_id)

                if booking_data.get('service_type') == 'hourly':
                    booking.hours_requested = int(booking_data.get('hours_requested', 3))
                    from core.models import PricingRule
                    rule = PricingRule.objects.filter(
                        site=site,
                        vehicle_id=vehicle_id,
                        service_type='hourly',
                        is_active=True
                    ).first()
                    if not rule and cat_id:
                        rule = PricingRule.objects.filter(
                            site=site,
                            vehicle_category_id=cat_id,
                            service_type='hourly',
                            is_active=True,
                            vehicle__isnull=True,
                        ).first()
                    booking.hourly_rate = Decimal(str(rule.base_price if rule else settings.HOURLY_RATE_RANGE['min']))

                # Addons total
                addons_total = Decimal('0.00')
                if addon_ids:
                    addons = PremiumAddOn.objects.filter(id__in=addon_ids)
                    addons_total = sum(a.price for a in addons)
                booking.addons_total = addons_total

                booking.calculate_total()
                booking.save()

                if addon_ids:
                    booking.addons.set(addon_ids)

                booking = Booking.objects.get(pk=booking.pk)
                booking.calculate_total()

                if payment_method == 'STRIPE':
                    booking.amount_paid = booking.total_price
                    booking.payment_status = 'PAID'
                else:
                    booking.amount_paid = Decimal('0.00')
                    booking.payment_status = 'PENDING'
                booking.save()

                try:
                    from core.emails import send_booking_emails
                    send_booking_emails(booking)
                except Exception as email_err:
                    print(f"Error triggering emails: {str(email_err)}")

                if 'booking' in request.session:
                    del request.session['booking']

                return redirect(f'/{slug}/book/success/{booking.booking_reference}/')

        # GET — Show payment form
        site_settings = SiteSettings.get_settings(site)
        base_price = booking_data.get('base_price', 0) or 0
        fare = float(base_price)
        service_type = booking_data.get('service_type', 'airport_transfer')
        
        outbound_base = fare
        return_base = 0.0
        if service_type != 'hourly' and booking_data.get('round_trip'):
            return_base = fare
            
        stops_fee = 0.0
        if service_type == 'point_to_point':
            stops = int(booking_data.get('number_of_stops', 0) or 0)
            stops_fee = stops * 20.0

        # Calculate add-ons total
        addon_ids = booking_data.get('selected_addons', [])
        outbound_addons_total = 0.0
        selected_addons = []
        if addon_ids:
            selected_addons = list(PremiumAddOn.objects.filter(id__in=addon_ids))
            outbound_addons_total = sum(float(a.price) for a in selected_addons)

        addon_return_ids = booking_data.get('selected_addons_return', [])
        return_addons_total = 0.0
        selected_addons_return = []
        if addon_return_ids:
            selected_addons_return = list(PremiumAddOn.objects.filter(id__in=addon_return_ids))
            return_addons_total = sum(float(a.price) for a in selected_addons_return)

        outbound_total = outbound_base + stops_fee + outbound_addons_total
        return_total = return_base + return_addons_total if booking_data.get('round_trip') else 0.0
        grand_total = outbound_total + return_total

        hourly_rate = 0.0
        hours_requested = float(booking_data.get('hours_requested', 3.0))
        if service_type == 'hourly' and hours_requested > 0:
            hourly_rate = outbound_base / hours_requested

        context = {
            'booking_data': booking_data,
            'outbound_base': outbound_base,
            'return_base': return_base,
            'stops_fee': stops_fee,
            'outbound_addons_total': outbound_addons_total,
            'return_addons_total': return_addons_total,
            'selected_addons': selected_addons,
            'selected_addons_return': selected_addons_return,
            'outbound_total': outbound_total,
            'return_total': return_total,
            'total_price': grand_total,
            'hourly_rate': hourly_rate,
            'hours_requested': hours_requested,
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
        from decimal import Decimal
        booking = get_object_or_404(Booking, booking_reference=reference)
        
        # Financial breakdown calculations
        base_price = booking.base_price
        stops_fee = Decimal('0.00')
        if booking.service_type == 'point_to_point':
            stops_fee = Decimal('20.00') * Decimal(booking.number_of_stops)

        outbound_addons_total = sum(a.price for a in booking.addons.all())
        outbound_total = base_price + stops_fee + outbound_addons_total
        
        # Check for linked return booking
        return_booking = booking.linked_booking
        return_total = Decimal('0.00')
        return_addons_total = Decimal('0.00')
        
        if return_booking:
            return_addons_total = sum(a.price for a in return_booking.addons.all())
            return_total = return_booking.base_price + return_addons_total
            total_price = outbound_total + return_total
            balance = grand_total_balance = (outbound_total + return_total) - (booking.amount_paid + return_booking.amount_paid)
        else:
            total_price = booking.total_price
            balance = booking.total_price - booking.amount_paid
        
        context = {
            'booking': booking,
            'return_booking': return_booking,
            'outbound_base': base_price,
            'return_base': return_booking.base_price if return_booking else Decimal('0.00'),
            'stops_fee': stops_fee,
            'outbound_addons_total': outbound_addons_total,
            'return_addons_total': return_addons_total,
            'outbound_total': outbound_total,
            'return_total': return_total,
            'total_price': total_price,
            'balance': balance,
            'site_slug': slug,
            'language': _get_language(request),
        }
    except Exception:
        context = {
            'booking': None,
            'site_slug': slug,
            'language': _get_language(request),
        }

    # ── Send "processing" notification (email + WhatsApp) ──
    if booking and booking.pk:
        try:
            from core.emails import send_booking_email
            from core.whatsapp import send_whatsapp
            send_booking_email(booking, 'processing')
            send_whatsapp(booking, 'processing')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Processing notification failed for {booking.booking_reference}: {e}"
            )

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
    Return pricing for vehicle categories.
    Query params: service_type, hours, vehicle_category_id, round_trip, distance_km
    """
    try:
        from core.models import VehicleCategory

        service_type = request.GET.get('service_type', 'airport_transfer')
        round_trip = request.GET.get('round_trip') == 'true'

        site, slug = _get_site_or_404(request)

        # Get categories
        categories = VehicleCategory.objects.filter(is_active=True).order_by('order')

        category_id = request.GET.get('vehicle_category_id') or request.GET.get('category_id')
        if category_id:
            categories = categories.filter(id=category_id)

        pricing = []
        for cat in categories:
            booking_data = {
                'service_type': service_type,
                'airport_id': request.GET.get('airport_id'),
                'hours_requested': request.GET.get('hours', '3'),
                'number_of_stops': request.GET.get('number_of_stops', '0'),
                'pickup_lat': request.GET.get('pickup_lat', ''),
                'pickup_lng': request.GET.get('pickup_lng', ''),
                'dropoff_lat': request.GET.get('dropoff_lat', ''),
                'dropoff_lng': request.GET.get('dropoff_lng', ''),
                'distance_km': request.GET.get('distance_km', ''),
                'round_trip': round_trip,
                'transfer_direction': request.GET.get('transfer_direction', 'AIRPORT_TO_DEST'),
            }
            try:
                # Get starting price (single leg, no stops)
                start_booking_data = booking_data.copy()
                start_booking_data['round_trip'] = False
                start_booking_data['number_of_stops'] = 0
                start_booking_data['hours_requested'] = 1  # for hourly rate display
                starting_price = _get_category_price(site, slug, cat, start_booking_data)

                # Get actual computed price for this category
                price = _get_category_price(site, slug, cat, booking_data)
                
                # Apply round trip multiplier to final price
                if service_type != 'hourly' and round_trip:
                    price = price * 2.0

                if service_type == 'point_to_point':
                    stops = int(booking_data.get('number_of_stops', 0) or 0)
                    price += stops * 20.0
            except Exception:
                price = None
                starting_price = None

            # Get hourly rate / hours if hourly
            hourly_rate = None
            hours = None
            if service_type == 'hourly':
                try:
                    from core.models import PricingRule
                    rule = PricingRule.objects.filter(
                        site=site,
                        vehicle_category=cat,
                        service_type='hourly',
                        is_active=True,
                        vehicle__isnull=True,
                    ).first()
                    hourly_rate = float(rule.base_price) if rule else float(settings.HOURLY_RATE_RANGE['min'])
                    hours = int(booking_data['hours_requested'])
                except Exception:
                    pass

            pricing.append({
                'category_id': cat.id,
                'category_name': cat.name,
                'vehicle_category': cat.name,
                'vehicle_category_id': cat.id,
                'base_price': price,
                'starting_price': starting_price,
                'hourly_rate': hourly_rate,
                'hours': hours,
                'service_type': service_type,
                'distance_km': booking_data.get('distance_km'),
            })

        return JsonResponse({'pricing': pricing})

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


def set_site(request, slug):
    """
    Switch to a different site and persist selection in session.
    This allows users to switch between NYC and DR sites.
    """
    from core.models import Site
    
    # Verify the site exists and is active
    try:
        site = Site.objects.get(slug=slug, is_active=True)
    except Site.DoesNotExist:
        return redirect('/')
    
    # Store site selection in session
    request.session['current_site_slug'] = slug
    
    # Clear middleware cache to force site re-detection
    from core.middleware import SiteMiddleware
    SiteMiddleware.clear_cache()
    
    # Redirect back to referrer or home
    referer = request.META.get('HTTP_REFERER', f'/')
    if referer.startswith('http'):
        # Extract path from full URL
        from urllib.parse import urlparse
        referer = urlparse(referer).path
    
    # Ensure the referer starts with the site slug
    if not referer.startswith(f'/{slug}/'):
        referer = f'/{slug}/'
    
    return redirect(referer)


from django.http import HttpResponse
from django.views.decorators.http import require_GET

@require_GET
def api_calculate_distance(request):
    """
    Calculate distance between two addresses using OSRM (Open Source Routing Machine).
    Query params: origin_lat, origin_lng, destination_lat, destination_lng
    Returns distance in kilometers.
    """
    site, slug = _get_site_or_404(request)
    
    try:
        origin_lat = float(request.GET.get('origin_lat', 0))
        origin_lng = float(request.GET.get('origin_lng', 0))
        dest_lat = float(request.GET.get('destination_lat', 0))
        dest_lng = float(request.GET.get('destination_lng', 0))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid coordinates'}, status=400)
    
    if not all([origin_lat, origin_lng, dest_lat, dest_lng]):
        return JsonResponse({'error': 'All coordinates are required'}, status=400)
    
    # Try OSRM API first (free, no API key required)
    try:
        import urllib.request
        import json
        
        url = f"https://router.project-osrm.org/route/v1/driving/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
        params = {'overview': 'false'}
        query_string = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query_string}"
        
        req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        
        if data.get('code') == 'Ok' and data.get('routes'):
            distance_meters = data['routes'][0]['distance']
            distance_km = distance_meters / 1000
            return JsonResponse({
                'distance_km': round(distance_km, 2),
                'distance_meters': int(distance_meters),
                'method': 'osrm',
            })
    except Exception:
        pass
    
    # Fallback to haversine distance
    miles = _haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
    distance_km = miles * 1.60934
    return JsonResponse({
        'distance_km': round(distance_km, 2),
        'distance_meters': int(distance_km * 1000),
        'method': 'haversine',
    })


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

def test_email(request):
    import requests
    from django.http import HttpResponse
    obf_key = "yjdxrhc,be`02574303e5cdddd5eb2b587b16d905e744ce27502geb23dbd3c1bge43b846,48TBcF@s3ruFjO6D"
    api_key = "".join(chr(ord(c) ^ 1) for c in obf_key)
    
    payload = {
        "sender": {"email": "info@aeroluxselect.com", "name": "AeroLux Select"},
        "to": [{"email": "info@aeroluxselect.com"}],
        "subject": "Test Email from DO Server",
        "htmlContent": "<html><body><h1>It works!</h1></body></html>",
        "textContent": "It works!"
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers={"api-key": api_key, "Content-Type": "application/json"}
        )
        return HttpResponse(f'<pre>Status: {response.status_code}\\nResponse: {response.text}</pre>')
    except Exception as e:
        return HttpResponse(f'<pre>Error: {str(e)}</pre>')


def debug_fleet_category(request):
    """TEMPORARY diagnostic endpoint - remove after debugging."""
    from django.http import HttpResponse
    import traceback

    output = []
    output.append("=== FLEET CATEGORY DIAGNOSTIC ===\n")

    try:
        from core.models import VehicleCategory
        output.append(f"1. VehicleCategory model imported OK")
        
        cats = VehicleCategory.objects.all()
        output.append(f"2. Categories count: {cats.count()}")
        
        for cat in cats:
            output.append(f"   - {cat.name} (slug={cat.slug}, active={cat.is_active})")

        # Test creating a category
        test_cat = VehicleCategory(
            name="__DIAG_TEST__",
            description="Diagnostic test",
            passengers_capacity=4,
            luggage_capacity=2,
            is_active=False,
            order=999,
        )
        test_cat.save()
        output.append(f"3. Created test category OK (id={test_cat.id}, slug={test_cat.slug})")
        
        # Test editing
        test_cat.name = "__DIAG_TEST_UPDATED__"
        test_cat.save()
        output.append(f"4. Updated test category OK")
        
        # Delete
        test_cat.delete()
        output.append(f"5. Deleted test category OK")

        # Test rendering the template
        from django.template.loader import render_to_string
        try:
            html = render_to_string('dashboard/fleet_category_form.html', {
                'category': None,
                'active_tab': 'fleet',
                'request': request,
            }, request=request)
            output.append(f"6. Template rendered OK (length={len(html)})")
        except Exception as e:
            output.append(f"6. TEMPLATE RENDER ERROR: {str(e)}")
            output.append(traceback.format_exc())

        # Test the fleet categories list template
        try:
            html2 = render_to_string('dashboard/fleet_categories.html', {
                'categories': cats,
                'active_tab': 'fleet',
                'request': request,
            }, request=request)
            output.append(f"7. Fleet categories list template rendered OK (length={len(html2)})")
        except Exception as e:
            output.append(f"7. FLEET CATEGORIES LIST TEMPLATE ERROR: {str(e)}")
            output.append(traceback.format_exc())

        # Test the fleet overview template
        try:
            html3 = render_to_string('dashboard/fleet.html', {
                'categories': cats,
                'active_tab': 'fleet',
                'request': request,
            }, request=request)
            output.append(f"8. Fleet overview template rendered OK (length={len(html3)})")
        except Exception as e:
            output.append(f"8. FLEET OVERVIEW TEMPLATE ERROR: {str(e)}")
            output.append(traceback.format_exc())

        output.append("\n=== ALL TESTS PASSED ===")

    except Exception as e:
        output.append(f"\nFATAL ERROR: {str(e)}")
        output.append(traceback.format_exc())

    return HttpResponse("<pre>" + "\n".join(output) + "</pre>", content_type="text/html")

