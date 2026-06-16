"""
AeroLux Select — Dashboard Views

Unified admin dashboard for managing both NYC and DR sites.
All views require admin authentication.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum, Q, Count, Avg
from django.http import JsonResponse
from datetime import date, timedelta
import json


def is_admin(user):
    """Check if user is authenticated and is staff/superuser."""
    return user.is_authenticated and (user.is_superuser or user.is_staff)


def dashboard_login(request):
    """Modern custom login view that completely hides Django brandings."""
    from django.contrib.auth import authenticate, login
    
    if request.user.is_authenticated and is_admin(request.user):
        return redirect('dashboard:index')
        
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '')
        
        user = authenticate(request, username=u, password=p)
        if user is not None:
            if user.is_superuser or user.is_staff:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}.')
                return redirect('dashboard:index')
            else:
                messages.error(request, 'Access denied. Administrator privileges required.')
        else:
            messages.error(request, 'Invalid username or password combination.')
            
    return render(request, 'dashboard/login.html')


def dashboard_logout(request):
    """Custom logout view."""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have logged out successfully.')
    return redirect('dashboard:login')


# =========================================================================
# DASHBOARD HOME
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def dashboard_index(request):
    """Dashboard overview with KPIs and charts."""
    from core.models import Booking, Site, VehicleCategory

    # Get filter parameters
    site_filter = request.GET.get('site', '')
    period = request.GET.get('period', '30')  # days

    bookings = Booking.objects.all()
    if site_filter:
        bookings = bookings.filter(site__slug=site_filter)

    # KPIs
    today = date.today()
    start_date = today - timedelta(days=int(period))

    total_bookings = bookings.filter(created_at__date__gte=start_date).count()
    total_revenue = bookings.filter(
        status__in=['CONFIRMED', 'COMPLETED'],
        created_at__date__gte=start_date
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0

    pending_count = bookings.filter(status='PENDING').count()
    confirmed_count = bookings.filter(
        status='CONFIRMED',
        created_at__date__gte=start_date
    ).count()

    # Platform revenue breakdown
    direct_revenue = bookings.filter(
        booking_source='DIRECT',
        status__in=['CONFIRMED', 'COMPLETED'],
        created_at__date__gte=start_date
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0

    platform_revenue = bookings.filter(
        booking_source__in=['VIATOR', 'EXPEDIA', 'OTHER'],
        status__in=['CONFIRMED', 'COMPLETED'],
        created_at__date__gte=start_date
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0

    # Revenue chart data (last 6 months)
    chart_labels = []
    chart_data_nyc = []
    chart_data_dr = []
    for i in range(5, -1, -1):
        target_date = today - timedelta(days=i * 30)
        month_label = target_date.strftime('%B %Y')
        chart_labels.append(month_label)

        nyc_rev = bookings.filter(
            site__slug='nyc',
            status__in=['CONFIRMED', 'COMPLETED'],
            created_at__month=target_date.month,
            created_at__year=target_date.year
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0

        dr_rev = bookings.filter(
            site__slug='dr',
            status__in=['CONFIRMED', 'COMPLETED'],
            created_at__month=target_date.month,
            created_at__year=target_date.year
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0

        chart_data_nyc.append(float(nyc_rev))
        chart_data_dr.append(float(dr_rev))

    # Recent bookings
    recent_bookings = bookings.order_by('-created_at')[:10]

    # Pending bookings
    pending_bookings = bookings.filter(status='PENDING').order_by('-created_at')

    # Active round trips whose return leg has not passed yet
    active_round_trips = bookings.filter(
        round_trip=True,
        status__in=['CONFIRMED', 'IN_PROGRESS'],
        return_date__gte=today
    ).order_by('return_date', 'return_time')

    # Site stats
    sites = Site.objects.filter(is_active=True)

    context = {
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'direct_revenue': direct_revenue,
        'platform_revenue': platform_revenue,
        'chart_labels': json.dumps(chart_labels),
        'chart_data_nyc': json.dumps(chart_data_nyc),
        'chart_data_dr': json.dumps(chart_data_dr),
        'recent_bookings': recent_bookings,
        'pending_bookings': pending_bookings,
        'active_round_trips': active_round_trips,
        'sites': sites,
        'site_filter': site_filter,
        'period': period,
        'active_tab': 'home',
    }
    return render(request, 'dashboard/index.html', context)


# =========================================================================
# BOOKINGS MANAGEMENT
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def dashboard_bookings(request):
    """List and manage bookings with filters."""
    from core.models import Booking

    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    site_filter = request.GET.get('site', '')
    service_filter = request.GET.get('service', '')
    round_trip_filter = request.GET.get('round_trip', '')

    bookings = Booking.objects.all().select_related(
        'site', 'airport', 'destination', 'vehicle_category'
    )

    if round_trip_filter == 'active':
        bookings = bookings.filter(
            round_trip=True,
            status__in=['CONFIRMED', 'IN_PROGRESS'],
            return_date__gte=date.today()
        )
    elif round_trip_filter == 'all':
        bookings = bookings.filter(round_trip=True)

    if query:
        bookings = bookings.filter(
            Q(customer_name__icontains=query) |
            Q(customer_email__icontains=query) |
            Q(booking_reference__icontains=query) |
            Q(customer_phone__icontains=query)
        )

    if status_filter:
        bookings = bookings.filter(status=status_filter)

    if site_filter:
        bookings = bookings.filter(site__slug=site_filter)

    if service_filter:
        bookings = bookings.filter(service_type=service_filter)

    # Sort by pickup date (closest to furthest), then by pickup time
    bookings = bookings.order_by('pickup_date', 'pickup_time')

    context = {
        'bookings': bookings,
        'query': query,
        'status_filter': status_filter,
        'site_filter': site_filter,
        'service_filter': service_filter,
        'round_trip_filter': round_trip_filter,
        'active_tab': 'bookings',
    }
    return render(request, 'dashboard/bookings.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def booking_detail(request, booking_id):
    """Detailed view of a single booking."""
    from core.models import Booking
    from decimal import Decimal
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST':
        # Update internal notes
        booking.internal_notes = request.POST.get('internal_notes', '')
        booking.driver_notes = request.POST.get('driver_notes', '')
        booking.save()
        messages.success(request, 'Booking notes updated.')

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

    # WhatsApp links generation
    from urllib.parse import quote
    from core.emails import get_formatted_whatsapp_message
    
    whatsapp_links = {}
    phone_raw = booking.customer_whatsapp or booking.customer_phone or ""
    phone_digits = "".join(c for c in phone_raw if c.isdigit())
    
    for t_type in ['processing', 'confirmed', 'reminder_12h', 'cancelled']:
        try:
            msg_text = get_formatted_whatsapp_message(booking, t_type)
            whatsapp_links[t_type] = f"https://wa.me/{phone_digits}?text={quote(msg_text)}"
        except Exception as e:
            whatsapp_links[t_type] = "#"

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
        'whatsapp_links': whatsapp_links,
        'active_tab': 'bookings',
    }
    return render(request, 'dashboard/booking_detail.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def update_booking_status(request, booking_id, new_status):
    """Quick status update for a booking."""
    from core.models import Booking
    booking = get_object_or_404(Booking, id=booking_id)

    valid_statuses = ['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
    if new_status in valid_statuses:
        # Check date constraints
        today = date.today()
        if new_status in ['IN_PROGRESS', 'COMPLETED'] and booking.pickup_date > today:
            messages.error(request, f"Cannot update booking #{booking.booking_reference} to {new_status} because the pickup date has not arrived yet.")
            return redirect('dashboard:bookings')

        if new_status == 'COMPLETED' and booking.round_trip and booking.return_date and booking.return_date > today:
            messages.error(request, f"Cannot update booking #{booking.booking_reference} to COMPLETED because the return date ({booking.return_date}) has not arrived yet.")
            return redirect('dashboard:bookings')

        booking.status = new_status
        booking.save()

        # Enforce status synchronization for linked booking legs only for CONFIRMED and CANCELLED
        # This allows completing one leg while keeping the other leg pending
        if new_status in ['CONFIRMED', 'CANCELLED']:
            if booking.linked_booking:
                try:
                    booking.linked_booking.status = new_status
                    booking.linked_booking.save()
                except Exception:
                    pass
            for return_b in booking.return_bookings.all():
                try:
                    return_b.status = new_status
                    return_b.save()
                except Exception:
                    pass

        messages.success(request, f'Booking #{booking.booking_reference} updated to {new_status}.')
        
        # Trigger dynamic emails on confirmation or cancellation
        try:
            from core.emails import send_booking_email
            if new_status == 'CONFIRMED':
                send_booking_email(booking, 'confirmed')
            elif new_status == 'CANCELLED':
                send_booking_email(booking, 'cancelled')
        except Exception as email_err:
            print(f"Error triggering dashboard status email: {str(email_err)}")

    return redirect('dashboard:bookings')


# =========================================================================
# FLEET MANAGEMENT
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def dashboard_fleet(request):
    """Fleet overview page."""
    from core.models import VehicleCategory, Vehicle

    categories = VehicleCategory.objects.all().order_by('order')
    vehicles = Vehicle.objects.all().select_related('category')

    context = {
        'categories': categories,
        'vehicles': vehicles,
        'active_tab': 'fleet',
    }
    return render(request, 'dashboard/fleet.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def fleet_categories(request):
    """Manage vehicle categories."""
    from core.models import VehicleCategory
    categories = VehicleCategory.objects.all().order_by('order')

    context = {
        'categories': categories,
        'active_tab': 'fleet',
    }
    return render(request, 'dashboard/fleet_categories.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def fleet_category_form(request, slug=None):
    """Add or edit a vehicle category."""
    from core.models import VehicleCategory

    category = None
    if slug:
        category = get_object_or_404(VehicleCategory, slug=slug)

    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'description': request.POST.get('description'),
            'passengers_capacity': int(request.POST.get('passengers_capacity', 4)),
            'luggage_capacity': int(request.POST.get('luggage_capacity', 4)),
            'spline_scene_url': request.POST.get('spline_scene_url', ''),
            'is_active': request.POST.get('is_active') == 'on',
            'order': int(request.POST.get('order', 0)),
        }

        if category:
            for key, value in data.items():
                setattr(category, key, value)
            if request.FILES.get('image'):
                category.image = request.FILES['image']
            category.save()
            messages.success(request, f'Category "{category.name}" updated.')
        else:
            category = VehicleCategory(**data)
            if request.FILES.get('image'):
                category.image = request.FILES['image']
            category.save()
            messages.success(request, f'Category "{category.name}" created.')

        return redirect('dashboard:fleet_categories')

    context = {
        'category': category,
        'active_tab': 'fleet',
    }
    return render(request, 'dashboard/fleet_category_form.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def fleet_vehicles(request):
    """Manage individual vehicles."""
    from core.models import Vehicle
    vehicles = Vehicle.objects.all().select_related('category')

    context = {
        'vehicles': vehicles,
        'active_tab': 'fleet',
    }
    return render(request, 'dashboard/fleet_vehicles.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def fleet_vehicle_form(request, pk=None):
    """Add or edit a vehicle."""
    from core.models import Vehicle, VehicleCategory, Site

    vehicle = None
    if pk:
        vehicle = get_object_or_404(Vehicle, pk=pk)

    categories = VehicleCategory.objects.all()
    sites = Site.objects.filter(is_active=True)

    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'category_id': int(request.POST.get('category')),
            'model_year': int(request.POST.get('model_year', 2024)),
            'price_multiplier': float(request.POST.get('price_multiplier', 1.0)),
            'is_active': request.POST.get('is_active') == 'on',
        }
        site_ids = request.POST.getlist('sites')

        if vehicle:
            for key, value in data.items():
                setattr(vehicle, key, value)
            if request.FILES.get('image'):
                vehicle.image = request.FILES['image']
            vehicle.save()
            vehicle.sites.set(site_ids)
            messages.success(request, f'Vehicle "{vehicle.name}" updated.')
        else:
            vehicle = Vehicle(**data)
            if request.FILES.get('image'):
                vehicle.image = request.FILES['image']
            vehicle.save()
            vehicle.sites.set(site_ids)
            messages.success(request, f'Vehicle "{vehicle.name}" created.')

        return redirect('dashboard:fleet_vehicles')

    context = {
        'vehicle': vehicle,
        'categories': categories,
        'sites': sites,
        'active_tab': 'fleet',
    }
    return render(request, 'dashboard/fleet_vehicle_form.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def toggle_vehicle_active(request, pk):
    """Toggle the availability/is_active status of a vehicle from the fleet list."""
    from core.models import Vehicle
    vehicle = get_object_or_404(Vehicle, pk=pk)
    vehicle.is_active = not vehicle.is_active
    vehicle.save()
    messages.success(request, f'Vehicle "{vehicle.name}" availability status updated to {"Active" if vehicle.is_active else "Inactive"}.')
    return redirect('dashboard:fleet_vehicles')


# =========================================================================
# AIRPORTS & DESTINATIONS MANAGEMENT
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def dashboard_airports(request):
    """Manage airports for both sites."""
    from core.models import Airport
    site_filter = request.GET.get('site', '')

    airports = Airport.objects.all().select_related('site')
    if site_filter:
        airports = airports.filter(site__slug=site_filter)

    context = {
        'airports': airports.order_by('site__slug', 'code'),
        'site_filter': site_filter,
        'active_tab': 'airports',
    }
    return render(request, 'dashboard/airports.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def airport_form(request, pk=None):
    """Add or edit an airport."""
    from core.models import Airport, Site

    airport = None
    if pk:
        airport = get_object_or_404(Airport, pk=pk)

    sites = Site.objects.filter(is_active=True)

    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'code': request.POST.get('code', '').upper(),
            'city': request.POST.get('city'),
            'country': request.POST.get('country'),
            'description': request.POST.get('description', ''),
            'latitude': float(request.POST.get('latitude', 0)),
            'longitude': float(request.POST.get('longitude', 0)),
            'site_id': int(request.POST.get('site')),
            'is_active': request.POST.get('is_active') == 'on',
        }

        if airport:
            for key, value in data.items():
                setattr(airport, key, value)
            if request.FILES.get('image'):
                airport.image = request.FILES['image']
            airport.save()
            messages.success(request, f'Airport "{airport.name}" updated.')
        else:
            airport = Airport(**data)
            if request.FILES.get('image'):
                airport.image = request.FILES['image']
            airport.save()
            messages.success(request, f'Airport "{airport.name}" created.')

        return redirect('dashboard:airports')

    context = {
        'airport': airport,
        'sites': sites,
        'active_tab': 'airports',
    }
    return render(request, 'dashboard/airport_form.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def dashboard_destinations(request, airport_id):
    """Manage destinations for a specific airport."""
    from core.models import Airport, Destination

    airport = get_object_or_404(Airport, pk=airport_id)
    destinations = Destination.objects.filter(airport=airport).order_by('name')

    context = {
        'airport': airport,
        'destinations': destinations,
        'active_tab': 'airports',
    }
    return render(request, 'dashboard/destinations.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def destination_form(request, airport_id=None, pk=None):
    """Add or edit a destination."""
    from core.models import Destination, Airport

    destination = None
    airport = None

    if pk:
        destination = get_object_or_404(Destination, pk=pk)
        airport = destination.airport
    elif airport_id:
        airport = get_object_or_404(Airport, pk=airport_id)

    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'address': request.POST.get('address', ''),
            'destination_type': request.POST.get('destination_type', 'NEIGHBORHOOD'),
            'description': request.POST.get('description', ''),
            'is_active': request.POST.get('is_active') == 'on',
        }

        if destination:
            for key, value in data.items():
                setattr(destination, key, value)
            if request.FILES.get('image'):
                destination.image = request.FILES['image']
            destination.save()
            messages.success(request, f'Destination "{destination.name}" updated.')
        else:
            destination = Destination(airport=airport, **data)
            if request.FILES.get('image'):
                destination.image = request.FILES['image']
            destination.save()
            messages.success(request, f'Destination "{destination.name}" created.')

        return redirect('dashboard:destinations', airport_id=airport.pk)

    context = {
        'destination': destination,
        'airport': airport,
        'active_tab': 'airports',
    }
    return render(request, 'dashboard/destination_form.html', context)


# =========================================================================
# PRICING MANAGEMENT (Hourly & Point-to-Point)
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def dashboard_pricing(request):
    """Manage pricing rules for Hourly and Point-to-Point services."""
    from core.models import PricingRule

    site_filter = request.GET.get('site', '')

    rules = PricingRule.objects.all().select_related(
        'site', 'vehicle', 'vehicle_category'
    )

    if site_filter:
        rules = rules.filter(site__slug=site_filter)

    context = {
        'rules': rules.order_by('site__slug', 'service_type', 'base_price'),
        'site_filter': site_filter,
        'active_tab': 'pricing',
    }
    return render(request, 'dashboard/pricing.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def pricing_form(request, pk=None):
    """Add or edit a pricing rule (Hourly/P2P only)."""
    from core.models import PricingRule, Site, Vehicle, VehicleCategory

    rule = None
    if pk:
        rule = get_object_or_404(PricingRule, pk=pk)

    sites = Site.objects.filter(is_active=True)
    vehicles = Vehicle.objects.filter(is_active=True).select_related('category')
    categories = VehicleCategory.objects.filter(is_active=True)

    if request.method == 'POST':
        data = {
            'site_id': int(request.POST.get('site')),
            'vehicle_category_id': int(request.POST.get('vehicle_category')),
            'service_type': request.POST.get('service_type', 'hourly'),
            'base_price': float(request.POST.get('base_price', 0)),
            'minimum_price': float(request.POST.get('minimum_price', 0)),
            'km_threshold': int(request.POST.get('km_threshold', 25)),
            'is_active': request.POST.get('is_active') == 'on',
        }

        vehicle_id = request.POST.get('vehicle')
        if vehicle_id:
            data['vehicle_id'] = int(vehicle_id)
        else:
            data['vehicle_id'] = None

        price_per_km = request.POST.get('price_per_km')
        if price_per_km:
            data['price_per_km'] = float(price_per_km)
        else:
            data['price_per_km'] = None

        if rule:
            for key, value in data.items():
                setattr(rule, key, value)
            rule.save()
            messages.success(request, 'Pricing rule updated.')
        else:
            rule = PricingRule(**data)
            rule.save()
            messages.success(request, 'Pricing rule created.')

        return redirect('dashboard:pricing')

    context = {
        'rule': rule,
        'sites': sites,
        'vehicles': vehicles,
        'categories': categories,
        'active_tab': 'pricing',
    }
    return render(request, 'dashboard/pricing_form.html', context)


# =========================================================================
# ZONE VEHICLE PRICING (Airport Transfer Fixed Prices)
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def airport_pricing_list(request):
    """List category-based pricing for airport transfers."""
    from core.models import AirportCategoryPrice, Airport

    site_filter = request.GET.get('site', '')
    airport_filter = request.GET.get('airport', '')

    prices = AirportCategoryPrice.objects.all().select_related(
        'airport', 'airport__site', 'vehicle_category'
    )

    if site_filter:
        prices = prices.filter(airport__site__slug=site_filter)
    if airport_filter:
        prices = prices.filter(airport_id=airport_filter)

    airports = Airport.objects.filter(is_active=True).select_related('site')

    context = {
        'prices': prices.order_by('airport__site__slug', 'airport__code', 'vehicle_category__name'),
        'airports': airports,
        'site_filter': site_filter,
        'airport_filter': airport_filter,
        'active_tab': 'airport_pricing',
    }
    return render(request, 'dashboard/airport_pricing.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def airport_pricing_form(request, pk=None):
    """Add or edit an airport category price."""
    from core.models import AirportCategoryPrice, Airport, VehicleCategory
    from django.db import IntegrityError

    price_obj = None
    if pk:
        price_obj = get_object_or_404(AirportCategoryPrice, pk=pk)

    airports = Airport.objects.filter(is_active=True).select_related('site')
    categories = VehicleCategory.objects.filter(is_active=True)

    if request.method == 'POST':
        airport_id = int(request.POST.get('airport'))
        category_id = int(request.POST.get('vehicle_category'))
        base_price = float(request.POST.get('base_price', 0))
        base_km = int(request.POST.get('base_km', 25))
        price_per_km = float(request.POST.get('price_per_km', 0))
        is_active = request.POST.get('is_active') == 'on'

        if price_obj:
            price_obj.airport_id = airport_id
            price_obj.vehicle_category_id = category_id
            price_obj.base_price = base_price
            price_obj.base_km = base_km
            price_obj.price_per_km = price_per_km
            price_obj.is_active = is_active
            try:
                price_obj.save()
                messages.success(request, f'Airport price updated successfully.')
                return redirect('dashboard:airport_pricing')
            except IntegrityError:
                messages.error(request, 'A pricing rule for this airport and vehicle category already exists.')
        else:
            try:
                price_obj = AirportCategoryPrice.objects.create(
                    airport_id=airport_id,
                    vehicle_category_id=category_id,
                    base_price=base_price,
                    base_km=base_km,
                    price_per_km=price_per_km,
                    is_active=is_active
                )
                messages.success(request, f'Airport price rule created successfully.')
                return redirect('dashboard:airport_pricing')
            except IntegrityError:
                messages.error(request, 'A pricing rule for this airport and vehicle category already exists.')

    context = {
        'price_obj': price_obj,
        'airports': airports,
        'categories': categories,
        'active_tab': 'airport_pricing',
    }
    return render(request, 'dashboard/airport_pricing_form.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def airport_pricing_delete(request, pk):
    """Delete an airport category price rule."""
    from core.models import AirportCategoryPrice
    price_obj = get_object_or_404(AirportCategoryPrice, pk=pk)
    price_obj.delete()
    messages.success(request, 'Airport category pricing rule deleted.')
    return redirect('dashboard:airport_pricing')




# =========================================================================
# CMS EDITOR
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def cms_editor(request, site_slug):
    """CMS content editor for a specific site."""
    from core.models import Site, SiteContent

    site = get_object_or_404(Site, slug=site_slug)
    elements = SiteContent.objects.filter(site=site).order_by('category', 'order', 'key')
    if site_slug == 'nyc':
        elements = elements.filter(language='en')

    if request.method == 'POST':
        # Update site basic info
        site.hero_title = request.POST.get('hero_title', site.hero_title)
        site.hero_subtitle = request.POST.get('hero_subtitle', site.hero_subtitle)
        site.tagline = request.POST.get('tagline', site.tagline)
        site.save()

        # Update CMS elements
        for elem in elements:
            val = request.POST.get(f'elem_{elem.id}')
            if val is not None:
                elem.value = val

            file = request.FILES.get(f'file_{elem.id}')
            if file:
                elem.image = file

            elem.save()

        messages.success(request, f'Content for {site.name} updated successfully!')
        return redirect('dashboard:cms_nyc' if site_slug == 'nyc' else 'dashboard:cms_dr')

    # Group by category
    categories = {}
    for elem in elements:
        cat = elem.get_category_display()
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(elem)

    # Group by language
    languages = {}
    for elem in elements:
        lang = elem.language
        if lang not in languages:
            languages[lang] = {}
        cat = elem.get_category_display()
        if cat not in languages[lang]:
            languages[lang][cat] = []
        languages[lang][cat].append(elem)

    context = {
        'site': site,
        'categories': categories,
        'languages': languages,
        'active_tab': f'cms_{site_slug}',
    }
    return render(request, 'dashboard/cms_editor.html', context)


# =========================================================================
# PREMIUM ADD-ONS
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def dashboard_addons(request):
    """Manage premium add-ons."""
    from core.models import PremiumAddOn
    addons = PremiumAddOn.objects.all()

    context = {
        'addons': addons,
        'active_tab': 'addons',
    }
    return render(request, 'dashboard/addons.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def addon_form(request, pk=None):
    """Add or edit a premium add-on."""
    from core.models import PremiumAddOn

    addon = None
    if pk:
        addon = get_object_or_404(PremiumAddOn, pk=pk)

    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'slug': request.POST.get('slug'),
            'description': request.POST.get('description', ''),
            'price': float(request.POST.get('price', 0)),
            'icon': request.POST.get('icon', 'fa-star'),
            'is_active': request.POST.get('is_active') == 'on',
        }

        if addon:
            for key, value in data.items():
                setattr(addon, key, value)
            addon.save()
            messages.success(request, f'Add-on "{addon.name}" updated.')
        else:
            addon = PremiumAddOn(**data)
            addon.save()
            messages.success(request, f'Add-on "{addon.name}" created.')

        return redirect('dashboard:addons')

    context = {
        'addon': addon,
        'active_tab': 'addons',
    }
    return render(request, 'dashboard/addon_form.html', context)


# =========================================================================
# PROFIT REPORTS
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def dashboard_reports(request):
    """Monthly profit reports and accounting."""
    from core.models import ProfitReport, Booking, Site

    site_filter = request.GET.get('site', '')
    year = int(request.GET.get('year', date.today().year))

    reports = ProfitReport.objects.filter(year=year)
    if site_filter:
        reports = reports.filter(site__slug=site_filter)

    reports = reports.order_by('site__slug', 'month')

    # Calculate totals
    totals = reports.aggregate(
        total_revenue=Sum('total_revenue'),
        total_fees=Sum('platform_fees'),
        total_net=Sum('net_revenue'),
        total_profit=Sum('profit'),
        total_bookings=Sum('total_bookings'),
    )

    sites = Site.objects.filter(is_active=True)

    context = {
        'reports': reports,
        'totals': totals,
        'sites': sites,
        'site_filter': site_filter,
        'year': year,
        'years': range(2024, date.today().year + 2),
        'active_tab': 'reports',
    }
    return render(request, 'dashboard/reports.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def generate_report(request):
    """Generate/update profit report for a specific month."""
    from core.models import ProfitReport, Booking, Site

    if request.method == 'POST':
        month = int(request.POST.get('month', date.today().month))
        year = int(request.POST.get('year', date.today().year))

        for site in Site.objects.filter(is_active=True):
            bookings = Booking.objects.filter(
                site=site,
                status__in=['CONFIRMED', 'COMPLETED'],
                created_at__month=month,
                created_at__year=year,
            )

            total_bookings = bookings.count()
            total_revenue = bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0
            platform_fees = bookings.aggregate(Sum('platform_fee'))['platform_fee__sum'] or 0
            net_revenue = float(total_revenue) - float(platform_fees)

            ProfitReport.objects.update_or_create(
                site=site,
                month=month,
                year=year,
                defaults={
                    'total_bookings': total_bookings,
                    'total_revenue': total_revenue,
                    'platform_fees': platform_fees,
                    'net_revenue': net_revenue,
                    'expenses': 0,
                    'profit': net_revenue,
                }
            )

        messages.success(request, f'Report for {month}/{year} generated successfully.')

    return redirect('dashboard:reports')


# =========================================================================
# SETTINGS
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def dashboard_settings(request):
    """General system settings."""
    from core.models import Site, SiteSettings
    site_slug = request.GET.get('site', 'nyc')
    site = get_object_or_404(Site, slug=site_slug)
    settings_obj = SiteSettings.get_settings(site)

    if request.method == 'POST':
        settings_obj.company_name = request.POST.get('company_name', settings_obj.company_name)
        settings_obj.contact_email = request.POST.get('contact_email', settings_obj.contact_email)
        settings_obj.contact_phone = request.POST.get('contact_phone', settings_obj.contact_phone)
        settings_obj.whatsapp_number = request.POST.get('whatsapp_number', settings_obj.whatsapp_number)
        settings_obj.social_facebook = request.POST.get('social_facebook', '')
        settings_obj.social_instagram = request.POST.get('social_instagram', '')
        settings_obj.social_twitter = request.POST.get('social_twitter', '')
        settings_obj.social_tiktok = request.POST.get('social_tiktok', '')
        settings_obj.google_analytics_id = request.POST.get('google_analytics_id', '')
        settings_obj.terms_and_conditions = request.POST.get('terms_and_conditions', '')
        settings_obj.google_maps_api_key = request.POST.get('google_maps_api_key', '').strip()
        # Airport Transfer Pricing
        ppm = request.POST.get('price_per_mile', '')
        abf = request.POST.get('airport_base_fee', '')
        if ppm:
            settings_obj.price_per_mile = ppm
        if abf:
            settings_obj.airport_base_fee = abf
        settings_obj.save()
        messages.success(request, f'Settings for {site.name} updated successfully.')

    context = {
        'settings': settings_obj,
        'sites': Site.objects.filter(is_active=True),
        'current_site': site,
        'active_tab': 'settings',
    }
    return render(request, 'dashboard/settings.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def stripe_settings(request):
    """Stripe payment configuration."""
    from core.models import Site, SiteSettings
    site_slug = request.GET.get('site', 'nyc')
    site = get_object_or_404(Site, slug=site_slug)
    settings_obj = SiteSettings.get_settings(site)

    if request.method == 'POST':
        settings_obj.stripe_public_key = request.POST.get('stripe_public_key', '')
        settings_obj.stripe_secret_key = request.POST.get('stripe_secret_key', '')
        settings_obj.stripe_enabled = request.POST.get('stripe_enabled') == 'on'
        settings_obj.save()
        messages.success(request, f'Stripe settings for {site.name} updated successfully.')

    context = {
        'settings': settings_obj,
        'sites': Site.objects.filter(is_active=True),
        'current_site': site,
        'active_tab': 'settings',
    }
    return render(request, 'dashboard/stripe_settings.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def email_settings(request):
    """Email service configuration settings."""
    from core.models import Site, SiteSettings
    site_slug = request.GET.get('site', 'nyc')
    site = get_object_or_404(Site, slug=site_slug)
    settings_obj = SiteSettings.get_settings(site)

    if request.method == 'POST':
        settings_obj.email_provider = request.POST.get('email_provider', 'SMTP')
        settings_obj.email_host = request.POST.get('email_host', '')
        try:
            settings_obj.email_port = int(request.POST.get('email_port', 587))
        except ValueError:
            settings_obj.email_port = 587
        settings_obj.email_username = request.POST.get('email_username', '')
        settings_obj.email_password = request.POST.get('email_password', '')
        settings_obj.email_use_tls = request.POST.get('email_use_tls') == 'on'
        settings_obj.email_api_key = request.POST.get('email_api_key', '')
        settings_obj.email_domain = request.POST.get('email_domain', '')
        settings_obj.email_from = request.POST.get('email_from', '')
        settings_obj.dispatch_email = request.POST.get('dispatch_email', '')
        settings_obj.save()
        messages.success(request, f'Email settings for {site.name} updated successfully.')

    context = {
        'settings': settings_obj,
        'sites': Site.objects.filter(is_active=True),
        'current_site': site,
        'active_tab': 'settings',
    }
    return render(request, 'dashboard/email_settings.html', context)


# =========================================================================
# ADMIN USER MANAGEMENT
# =========================================================================

@user_passes_test(is_admin, login_url='dashboard:login')
def admin_users_list(request):
    """List all admin/staff users."""
    from django.contrib.auth.models import User
    admins = User.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True)
    ).order_by('-is_superuser', 'username')

    context = {
        'admins': admins,
        'active_tab': 'admins',
    }
    return render(request, 'dashboard/admin_users.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def admin_user_form(request, pk=None):
    """Add or edit an admin user."""
    from django.contrib.auth.models import User

    admin_user = None
    if pk:
        admin_user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        is_superuser = request.POST.get('is_superuser') == 'on'

        if admin_user:
            # Edit existing
            admin_user.username = username
            admin_user.email = email
            admin_user.is_superuser = is_superuser
            admin_user.is_staff = True
            if password:
                admin_user.set_password(password)
            admin_user.save()
            messages.success(request, f'Admin "{username}" updated successfully.')
        else:
            # Create new
            if User.objects.filter(username=username).exists():
                messages.error(request, f'Username "{username}" already exists.')
                return render(request, 'dashboard/admin_user_form.html', {
                    'admin_user': admin_user,
                    'active_tab': 'admins',
                })
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password or 'changeme123',
            )
            new_user.is_staff = True
            new_user.is_superuser = is_superuser
            new_user.save()
            messages.success(request, f'Admin "{username}" created successfully.')

        return redirect('dashboard:admin_users')

    context = {
        'admin_user': admin_user,
        'active_tab': 'admins',
    }
    return render(request, 'dashboard/admin_user_form.html', context)


@user_passes_test(is_admin, login_url='dashboard:login')
def admin_user_delete(request, pk):
    """Delete an admin user."""
    from django.contrib.auth.models import User
    admin_user = get_object_or_404(User, pk=pk)

    if admin_user == request.user:
        messages.error(request, 'You cannot delete your own account.')
    else:
        username = admin_user.username
        admin_user.delete()
        messages.success(request, f'Admin "{username}" deleted.')

    return redirect('dashboard:admin_users')


@user_passes_test(is_admin, login_url='dashboard:login')
def record_payment(request, booking_id):
    """Logs a manual cash/other payment towards a booking."""
    from core.models import Booking, BookingPayment
    from decimal import Decimal
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0.00'))
        except (ValueError, TypeError):
            amount = Decimal('0.00')
            
        notes = request.POST.get('notes', '').strip()
        method = request.POST.get('payment_method', 'CASH')
        
        if amount <= 0:
            messages.error(request, 'Please enter a valid positive payment amount.')
        else:
            BookingPayment.objects.create(
                booking=booking,
                amount=amount,
                payment_method=method,
                notes=notes
            )
            
            # Sum all payments
            total_paid = booking.payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            booking.amount_paid = total_paid
            
            # Update payment status
            if booking.amount_paid >= booking.total_price:
                booking.payment_status = 'paid'
            elif booking.amount_paid > 0:
                booking.payment_status = 'partially_paid'
            else:
                booking.payment_status = 'pending'
                
            booking.save()
            messages.success(request, f'Manual payment of ${amount:.2f} recorded for booking #{booking.booking_reference}.')
            
    return redirect('dashboard:booking_detail', booking_id=booking.id)


@user_passes_test(is_admin, login_url='dashboard:login')
def email_template_editor(request):
    """View to list, edit and seed customizable Brevo email templates and WhatsApp templates."""
    from core.models import Site, EmailTemplate, WhatsAppTemplate
    from core.emails import get_default_email_template, get_default_whatsapp_template
    
    site_slug = request.GET.get('site', 'nyc')
    site = get_object_or_404(Site, slug=site_slug)
    
    email_type = request.GET.get('type', 'processing')
    if email_type not in ['processing', 'confirmed', 'reminder_12h', 'cancelled']:
        email_type = 'processing'
        
    tab = request.GET.get('tab', 'email')
    if tab not in ['email', 'whatsapp']:
        tab = 'email'
        
    template_obj = EmailTemplate.objects.filter(site=site, email_type=email_type).first()
    whatsapp_template_obj = WhatsAppTemplate.objects.filter(site=site, trigger_type=email_type).first()
    
    # Email Template values
    if not template_obj:
        default_subj, default_html, default_text = get_default_email_template(email_type, site.name)
        subject_val = default_subj
        html_val = default_html
        text_val = default_text
    else:
        subject_val = template_obj.subject
        html_val = template_obj.html_content
        text_val = template_obj.text_content
        
    # WhatsApp Template values
    if not whatsapp_template_obj:
        whatsapp_message_val = get_default_whatsapp_template(email_type, site.name)
    else:
        whatsapp_message_val = whatsapp_template_obj.message_content
        
    if request.method == 'POST':
        if tab == 'email':
            subject_val = request.POST.get('subject', '').strip()
            html_val = request.POST.get('html_content', '').strip()
            text_val = request.POST.get('text_content', '').strip()
            
            if not template_obj:
                template_obj = EmailTemplate(
                    site=site,
                    email_type=email_type,
                    subject=subject_val,
                    html_content=html_val,
                    text_content=text_val
                )
            else:
                template_obj.subject = subject_val
                template_obj.html_content = html_val
                template_obj.text_content = text_val
                
            template_obj.save()
            messages.success(request, f'Email template "{email_type}" for {site.name} updated successfully.')
        elif tab == 'whatsapp':
            whatsapp_message_val = request.POST.get('whatsapp_message', '').strip()
            
            if not whatsapp_template_obj:
                whatsapp_template_obj = WhatsAppTemplate(
                    site=site,
                    trigger_type=email_type,
                    message_content=whatsapp_message_val
                )
            else:
                whatsapp_template_obj.message_content = whatsapp_message_val
                
            whatsapp_template_obj.save()
            messages.success(request, f'WhatsApp template "{email_type}" for {site.name} updated successfully.')
        
    context = {
        'sites': Site.objects.filter(is_active=True),
        'current_site': site,
        'email_type': email_type,
        'active_sub_tab': tab,
        
        # Email fields
        'subject': subject_val,
        'html_content': html_val,
        'text_content': text_val,
        'template_obj': template_obj,
        
        # WhatsApp fields
        'whatsapp_message': whatsapp_message_val,
        'whatsapp_template_obj': whatsapp_template_obj,
        
        'active_tab': 'notifications',
    }
    return render(request, 'dashboard/email_templates.html', context)
