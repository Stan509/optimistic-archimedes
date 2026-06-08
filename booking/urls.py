from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # -------------------------------------------------------------
    # ROUTES PUBLIQUES (CLIENT)
    # -------------------------------------------------------------
    path('', views.index, name='index'),
    path('chambre/<slug:slug>/', views.room_detail, name='room_detail'),
    path('chambre/<slug:slug>/reserver/', views.checkout, name='checkout'),
    path('reservation-succes/', views.booking_success, name='booking_success'),
    
    # -------------------------------------------------------------
    # ROUTES D'ADMINISTRATION (CUSTOM DASHBOARD)
    # -------------------------------------------------------------
    path('dashboard/', views.dashboard_index, name='dashboard_index'),
    path('dashboard/reservations/', views.dashboard_bookings, name='dashboard_bookings'),
    path('dashboard/reservations/<int:booking_id>/statut/<str:new_status>/', views.update_booking_status, name='update_booking_status'),
    path('dashboard/chambres/', views.dashboard_rooms, name='dashboard_rooms'),
    path('dashboard/chambres/ajouter/', views.room_form, name='add_room'),
    path('dashboard/chambres/editer/<slug:slug>/', views.room_form, name='edit_room'),
    path('dashboard/chambres/supprimer/<slug:slug>/', views.delete_room, name='delete_room'),
    path('dashboard/editeur/', views.dashboard_site_editor, name='dashboard_site_editor'),
]
