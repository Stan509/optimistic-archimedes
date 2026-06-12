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

    # Fallback to haversine if distance is not passed
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
        else:
            distance_km = 20.0

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
            Booking, VehicleCategory, Vehicle, Airport, Destination,
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
                passenger_count=booking_data.get('passenger_count', 1),
            )

            # Set foreign keys
            airport_id = booking_data.get('airport_id')
            if airport_id:
                booking.airport_id = int(airport_id)

            dest_id = booking_data.get('destination_id')
            if dest_id:
                booking.destination_id = int(dest_id)

            # Set vehicle (individual) and category
            vehicle_id = booking_data.get('vehicle_id')
            if vehicle_id:
                booking.vehicle_id = int(vehicle_id)
            cat_id = booking_data.get('vehicle_category_id')
            if cat_id:
                booking.vehicle_category_id = int(cat_id)

            # Set hourly fields
            from decimal import Decimal
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

            # Set pricing
            base_price = booking_data.get('base_price', 0) or 0
            booking.base_price = Decimal(str(base_price))

            # Set pay_separately
            booking.pay_separately = booking_data.get('pay_separately', False)

            # Calculate add-ons total
            addon_ids = booking_data.get('selected_addons', [])
            addon_return_ids = booking_data.get('selected_addons_return', [])
            addons_total = Decimal('0.00')
            if addon_ids:
                addons = PremiumAddOn.objects.filter(id__in=addon_ids)
                addons_total += sum(a.price for a in addons)
            if addon_return_ids:
                addons_return = PremiumAddOn.objects.filter(id__in=addon_return_ids)
                addons_total += sum(a.price for a in addons_return)
            booking.addons_total = addons_total

            booking.calculate_total()
            booking.payment_method = request.POST.get('payment_method', 'STRIPE')

            # Save to get PK
            booking.save()

            # Add selected add-ons
            if addon_ids:
                booking.addons.set(addon_ids)
            if addon_return_ids:
                booking.addons_return.set(addon_return_ids)

            # Force reload from database to clear relation cache
            booking = Booking.objects.get(pk=booking.pk)
            # Recalculate total after addons are set
            booking.calculate_total()
            
            if booking.payment_method == 'STRIPE':
                booking.amount_paid = booking.total_price
                booking.payment_status = 'PAID'
            else:
                booking.amount_paid = Decimal('0.00')
                booking.payment_status = 'PENDING'
            booking.save()

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
        return_addons_total = sum(a.price for a in booking.addons_return.all())

        outbound_total = base_price + stops_fee + outbound_addons_total
        return_total = base_price + return_addons_total if booking.round_trip else Decimal('0.00')
        balance = booking.total_price - booking.amount_paid
        
        context = {
            'booking': booking,
            'outbound_base': base_price,
            'return_base': base_price if booking.round_trip else Decimal('0.00'),
            'stops_fee': stops_fee,
            'outbound_addons_total': outbound_addons_total,
            'return_addons_total': return_addons_total,
            'outbound_total': outbound_total,
            'return_total': return_total,
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
