from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum, Q, Count
from django.core.exceptions import ValidationError
from datetime import datetime, date, timedelta
import json

from .models import Room, Reservation, SiteElement, SiteSettings

# =========================================================================
# VIEWS CLIENT-FACING (PUBLIC SITE)
# =========================================================================

def index(request):
    """Page d'accueil publique avec catalogue des chambres et recherche de disponibilité."""
    rooms = Room.objects.filter(is_available=True)
    
    # Paramètres de recherche
    check_in_str = request.GET.get('check_in')
    check_out_str = request.GET.get('check_out')
    guests_str = request.GET.get('guests')
    
    check_in = None
    check_out = None
    guests = 1
    
    if check_in_str and check_out_str:
        try:
            check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
            check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
            if guests_str:
                guests = int(guests_str)
                
            if check_in >= check_out or check_in < date.today():
                messages.error(request, "Veuillez entrer des dates valides (l'arrivée doit être dans le futur et avant le départ).")
            else:
                # Filtrer les chambres disponibles pour ces dates
                # Une chambre est indisponible si elle a une réservation confirmée ou en attente qui chevauche
                reserved_room_ids = Reservation.objects.filter(
                    check_in__lt=check_out,
                    check_out__gt=check_in
                ).exclude(status='CANCELLED').values_list('room_id', flat=True)
                
                rooms = rooms.exclude(id__in=reserved_room_ids)
                
                # Filtrer aussi par capacité
                rooms = rooms.filter(capacity__gte=guests)
                
                messages.success(request, f"Nous avons trouvé {rooms.count()} hébergement(s) disponible(s) pour votre séjour !")
        except ValueError:
            messages.error(request, "Format de date incorrect. Veuillez utiliser le calendrier.")
            
    context = {
        'rooms': rooms,
        'check_in': check_in_str,
        'check_out': check_out_str,
        'guests': guests_str,
        'today': date.today().strftime("%Y-%m-%d"),
        'tomorrow': (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
    }
    return render(request, 'booking/index.html', context)


def room_detail(request, slug):
    """Détails d'une chambre avec descriptif premium et sélecteur de réservation."""
    room = get_object_or_404(Room, slug=slug)
    
    # Récupérer les paramètres passés depuis l'accueil
    check_in = request.GET.get('check_in', '')
    check_out = request.GET.get('check_out', '')
    guests = request.GET.get('guests', '2')
    
    context = {
        'room': room,
        'check_in': check_in,
        'check_out': check_out,
        'guests': guests,
        'today': date.today().strftime("%Y-%m-%d"),
    }
    return render(request, 'booking/room_detail.html', context)


def checkout(request, slug):
    """Tunnel de réservation final."""
    room = get_object_or_404(Room, slug=slug)
    
    check_in_str = request.GET.get('check_in')
    check_out_str = request.GET.get('check_out')
    guests_str = request.GET.get('guests', '1')
    
    if not check_in_str or not check_out_str:
        messages.error(request, "Veuillez d'abord sélectionner vos dates de séjour.")
        return redirect('booking:room_detail', slug=room.slug)
        
    try:
        check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
        guests = int(guests_str)
        nights = (check_out - check_in).days
        total_price = room.price_per_night * nights
    except ValueError:
        messages.error(request, "Dates invalides.")
        return redirect('booking:room_detail', slug=room.slug)

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        special_requests = request.POST.get('special_requests')
        
        # Création et validation
        res = Reservation(
            customer_name=name,
            customer_email=email,
            customer_phone=phone,
            room=room,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            special_requests=special_requests
        )
        
        try:
            res.clean()  # Lance la validation des doublons
            res.save()
            # Rediriger vers la page de succès
            request.session['last_booking_id'] = res.id
            return redirect('booking:booking_success')
        except ValidationError as e:
            for message in e.messages:
                messages.error(request, message)
                
    context = {
        'room': room,
        'check_in': check_in,
        'check_out': check_out,
        'guests': guests,
        'nights': nights,
        'total_price': total_price,
    }
    return render(request, 'booking/checkout.html', context)


def booking_success(request):
    """Page de confirmation de réservation réussie."""
    booking_id = request.session.get('last_booking_id')
    if not booking_id:
        return redirect('booking:index')
        
    res = get_object_or_404(Reservation, id=booking_id)
    context = {
        'reservation': res
    }
    return render(request, 'booking/booking_success.html', context)


# =========================================================================
# VIEWS D'ADMINISTRATION (CUSTOM DASHBOARD)
# =========================================================================

def is_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_admin, login_url='admin:login')
def dashboard_index(request):
    """Accueil du Dashboard avec statistiques clés et graphiques."""
    reservations = Reservation.objects.all()
    rooms_count = Room.objects.count()
    
    # 1. Statistiques Clés
    # Revenus totaux sur les réservations confirmées
    total_revenue = reservations.filter(status='CONFIRMED').aggregate(Sum('total_price'))['total_price__sum'] or 0.0
    # Nombre de réservations en attente
    pending_count = reservations.filter(status='PENDING').count()
    # Nombre total de clients uniques
    unique_clients = reservations.values('customer_email').distinct().count()
    
    # 2. Taux d'occupation actuel (Chambres occupées aujourd'hui)
    today = date.today()
    occupied_today = Reservation.objects.filter(
        check_in__lte=today,
        check_out__gt=today,
        status='CONFIRMED'
    ).values('room_id').distinct().count()
    
    occupancy_rate = int((occupied_today / rooms_count * 100)) if rooms_count > 0 else 0

    # 3. Données pour le Graphique Chart.js (Ventes par mois sur l'année en cours)
    # Pour la démo, on simule des données de vente sur les derniers mois
    sales_data = []
    sales_labels = []
    for i in range(5, -1, -1):
        target_date = today - timedelta(days=i*30)
        month_label = target_date.strftime("%B")
        # Revenus réels ou simulés pour ce mois
        month_revenue = reservations.filter(
            status='CONFIRMED', 
            created_at__month=target_date.month,
            created_at__year=target_date.year
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        # Simuler un fond de données s'il n'y a pas de ventes pour rendre le graphe vivant
        if month_revenue == 0:
            month_revenue = float(1200 + (i * 350))
            
        sales_labels.append(month_label)
        sales_data.append(float(month_revenue))

    # 4. Dernières Réservations
    recent_bookings = reservations.order_by('-created_at')[:5]

    context = {
        'total_revenue': total_revenue,
        'pending_count': pending_count,
        'unique_clients': unique_clients,
        'occupancy_rate': occupancy_rate,
        'recent_bookings': recent_bookings,
        'sales_labels_json': json.dumps(sales_labels),
        'sales_data_json': json.dumps(sales_data),
        'active_tab': 'home'
    }
    return render(request, 'booking/dashboard/index.html', context)


@user_passes_test(is_admin, login_url='admin:login')
def dashboard_bookings(request):
    """Gestion et liste des réservations avec filtres."""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    bookings_list = Reservation.objects.all()
    
    if query:
        bookings_list = bookings_list.filter(
            Q(customer_name__icontains=query) | 
            Q(customer_email__icontains=query) |
            Q(room__name__icontains=query)
        )
        
    if status_filter:
        bookings_list = bookings_list.filter(status=status_filter)
        
    context = {
        'bookings': bookings_list,
        'query': query,
        'status_filter': status_filter,
        'active_tab': 'bookings'
    }
    return render(request, 'booking/dashboard/bookings.html', context)


@user_passes_test(is_admin, login_url='admin:login')
def update_booking_status(request, booking_id, new_status):
    """Mise à jour rapide du statut d'une réservation (Confirmer / Annuler)."""
    booking = get_object_or_404(Reservation, id=booking_id)
    if new_status in ['CONFIRMED', 'CANCELLED', 'PENDING']:
        booking.status = new_status
        booking.save()
        messages.success(request, f"La réservation #{booking.id} a été mise à jour avec succès : Statut '{booking.get_status_display()}'.")
    return redirect('booking:dashboard_bookings')


@user_passes_test(is_admin, login_url='admin:login')
def dashboard_rooms(request):
    """Gestion du catalogue des chambres."""
    rooms = Room.objects.all()
    context = {
        'rooms': rooms,
        'active_tab': 'rooms'
    }
    return render(request, 'booking/dashboard/rooms.html', context)


@user_passes_test(is_admin, login_url='admin:login')
def room_form(request, slug=None):
    """Formulaire d'ajout ou modification d'une chambre."""
    room = None
    if slug:
        room = get_object_or_404(Room, slug=slug)
        
    if request.method == 'POST':
        name = request.POST.get('name')
        room_number = request.POST.get('room_number')
        description = request.POST.get('description')
        price = request.POST.get('price_per_night')
        capacity = request.POST.get('capacity')
        image = request.FILES.get('image')
        
        is_available = request.POST.get('is_available') == 'on'
        wifi = request.POST.get('has_wifi') == 'on'
        jacuzzi = request.POST.get('has_jacuzzi') == 'on'
        balcony = request.POST.get('has_balcony') == 'on'
        ac = request.POST.get('has_ac') == 'on'
        tv = request.POST.get('has_tv') == 'on'
        minibar = request.POST.get('has_minibar') == 'on'
        room_service = request.POST.get('has_room_service') == 'on'
        
        if room:
            # Mode Édition
            room.name = name
            room.room_number = room_number
            room.description = description
            room.price_per_night = price
            room.capacity = capacity
            if image:
                room.image = image
            room.is_available = is_available
            room.has_wifi = wifi
            room.has_jacuzzi = jacuzzi
            room.has_balcony = balcony
            room.has_ac = ac
            room.has_tv = tv
            room.has_minibar = minibar
            room.has_room_service = room_service
            
            try:
                room.save()
                messages.success(request, f"La chambre '{room.name}' a été modifiée avec succès.")
                return redirect('booking:dashboard_rooms')
            except Exception as e:
                messages.error(request, f"Erreur lors de l'enregistrement : {e}")
        else:
            # Mode Ajout
            new_room = Room(
                name=name,
                room_number=room_number,
                description=description,
                price_per_night=price,
                capacity=capacity,
                image=image,
                is_available=is_available,
                has_wifi=wifi,
                has_jacuzzi=jacuzzi,
                has_balcony=balcony,
                has_ac=ac,
                has_tv=tv,
                has_minibar=minibar,
                has_room_service=room_service
            )
            try:
                new_room.save()
                messages.success(request, f"La chambre '{new_room.name}' a été créée avec succès.")
                return redirect('booking:dashboard_rooms')
            except Exception as e:
                messages.error(request, f"Erreur lors de l'enregistrement : {e}")

    context = {
        'room': room,
        'active_tab': 'rooms'
    }
    return render(request, 'booking/dashboard/room_form.html', context)


@user_passes_test(is_admin, login_url='admin:login')
def delete_room(request, slug):
    """Suppression d'une chambre."""
    room = get_object_or_404(Room, slug=slug)
    room_name = room.name
    room.delete()
    messages.success(request, f"La chambre '{room_name}' a été supprimée avec succès.")
    return redirect('booking:dashboard_rooms')


@user_passes_test(is_admin, login_url='admin:login')
def dashboard_site_editor(request):
    """L'éditeur dynamique du site !"""
    settings = SiteSettings.get_settings()
    elements = SiteElement.objects.all()
    
    if request.method == 'POST':
        # 1. Enregistrer les paramètres généraux
        settings.hotel_name = request.POST.get('hotel_name', settings.hotel_name)
        settings.contact_email = request.POST.get('contact_email', settings.contact_email)
        settings.contact_phone = request.POST.get('contact_phone', settings.contact_phone)
        settings.address = request.POST.get('address', settings.address)
        settings.social_facebook = request.POST.get('social_facebook', settings.social_facebook)
        settings.social_instagram = request.POST.get('social_instagram', settings.social_instagram)
        settings.social_twitter = request.POST.get('social_twitter', settings.social_twitter)
        settings.save()
        
        # 2. Enregistrer tous les éléments de site dynamiques
        for elem in elements:
            input_val = request.POST.get(f'elem_{elem.key}')
            if input_val is not None:
                elem.value = input_val
            
            # Gestion des images téléversées pour les éléments
            input_file = request.FILES.get(f'file_{elem.key}')
            if input_file:
                elem.image = input_file
                
            elem.save()
            
        messages.success(request, "Tous les éléments du site internet ont été mis à jour avec succès. Les modifications sont visibles immédiatement !")
        return redirect('booking:dashboard_site_editor')
        
    # Trier les éléments par catégorie pour un bel affichage à onglets dans l'éditeur
    categories = {
        'ACCUEIL': [e for e in elements if e.category == 'ACCUEIL'],
        'ABOUT': [e for e in elements if e.category == 'ABOUT'],
        'SERVICES': [e for e in elements if e.category == 'SERVICES'],
        'CONTACT': [e for e in elements if e.category == 'CONTACT'],
    }
    
    context = {
        'settings': settings,
        'categories': categories,
        'active_tab': 'editor'
    }
    return render(request, 'booking/dashboard/site_editor.html', context)
