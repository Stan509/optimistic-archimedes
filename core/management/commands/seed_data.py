"""
AeroLux Select — Seed Initial Data

Management command to populate the database with:
- Sites (NYC, DR)
- Airports for both regions
- Popular destinations
- Vehicle categories
- Premium add-ons
- Default pricing rules
- Sample CMS content
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Seed the database with initial data for AeroLux Select'

    def handle(self, *args, **options):
        from core.models import (
            Site, Airport, Destination, VehicleCategory, Vehicle,
            PremiumAddOn, PricingRule, AirportCategoryPrice, SiteContent, SiteSettings, Testimonial,
            WhatsAppTemplate
        )

        self.stdout.write(self.style.NOTICE('Seeding AeroLux Select database...'))

        # =====================================================================
        # 0. ADMIN SUPERUSER
        # =====================================================================
        from django.contrib.auth.models import User
        self.stdout.write('  Creating admin superuser...')
        admin_user, created = User.objects.get_or_create(
            username='DeeAdmin',
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'email': 'admin@aerolux.com',
            }
        )
        if created:
            admin_user.set_password('Dee@aerolux')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('  [OK] Superuser DeeAdmin created'))
        else:
            self.stdout.write(self.style.WARNING('  [SKIP] Superuser DeeAdmin already exists'))


        # =====================================================================
        # 1. SITES
        # =====================================================================
        self.stdout.write('  Creating sites...')

        nyc, _ = Site.objects.update_or_create(
            slug='nyc',
            defaults={
                'name': 'New York City',
                'domain': 'aeroluxselect.com',
                'tagline': 'Premium Airport Transfers & Luxury Car Service in NYC',
                'hero_title': 'NYC Premium Car Service & Airport Transfers',
                'hero_subtitle': 'Experience luxury transportation with flat rates, no surprises. JFK, LGA, EWR and beyond.',
                'primary_color': '#C9A84C',
                'secondary_color': '#0A0A0A',
                'is_active': True,
                'default_language': 'en',
            }
        )

        dr, _ = Site.objects.update_or_create(
            slug='dr',
            defaults={
                'name': 'Dominican Republic',
                'domain': 'aeroluxeselect-dr.com',
                'tagline': 'Luxury Airport Transfers & VIP Car Service in Dominican Republic',
                'hero_title': 'Dominican Republic VIP Car Service & Airport Transfers',
                'hero_subtitle': 'Arrive in style. Premium transfers from every major airport in the Dominican Republic.',
                'primary_color': '#C9A84C',
                'secondary_color': '#0A0A0A',
                'is_active': True,
                'default_language': 'en',
            }
        )
        self.stdout.write(self.style.SUCCESS('  [OK] Sites created'))

        # =====================================================================
        # 2. AIRPORTS — NEW YORK CITY
        # =====================================================================
        self.stdout.write('  Creating NYC airports...')

        nyc_airports_data = [
            {
                'code': 'JFK',
                'name': 'John F. Kennedy International Airport',
                'city': 'Queens, NY',
                'country': 'US',
                'description': 'New York\'s premier international gateway, serving over 60 million passengers annually. Located in Queens, JFK is the busiest international air passenger gateway in the United States.',
                'latitude': 40.6413,
                'longitude': -73.7781,
            },
            {
                'code': 'LGA',
                'name': 'LaGuardia Airport',
                'city': 'Queens, NY',
                'country': 'US',
                'description': 'Located in northern Queens, LaGuardia primarily serves domestic flights and is the closest airport to Midtown Manhattan.',
                'latitude': 40.7769,
                'longitude': -73.8740,
            },
            {
                'code': 'EWR',
                'name': 'Newark Liberty International Airport',
                'city': 'Newark, NJ',
                'country': 'US',
                'description': 'Located in Newark, New Jersey, EWR is a major United Airlines hub serving both domestic and international flights.',
                'latitude': 40.6895,
                'longitude': -74.1745,
            },
            {
                'code': 'SWF',
                'name': 'New York Stewart International Airport',
                'city': 'New Windsor, NY',
                'country': 'US',
                'description': 'Located in the Hudson Valley, Stewart serves as a convenient alternative to the busier NYC airports.',
                'latitude': 41.5041,
                'longitude': -74.1048,
            },
            {
                'code': 'HPN',
                'name': 'Westchester County Airport',
                'city': 'White Plains, NY',
                'country': 'US',
                'description': 'A convenient airport for travelers in Westchester County and southern Connecticut.',
                'latitude': 41.0670,
                'longitude': -73.7076,
            },
            {
                'code': 'ISP',
                'name': 'Long Island MacArthur Airport',
                'city': 'Ronkonkoma, NY',
                'country': 'US',
                'description': 'Serving Long Island, this airport provides easy access to the Hamptons and eastern Long Island.',
                'latitude': 40.7952,
                'longitude': -73.1002,
            },
            {
                'code': 'TEB',
                'name': 'Teterboro Airport',
                'city': 'Teterboro, NJ',
                'country': 'US',
                'description': 'An exclusive general aviation airport popular with private jet travelers, located just 12 miles from Midtown Manhattan.',
                'latitude': 40.8501,
                'longitude': -74.0608,
            },
        ]

        for data in nyc_airports_data:
            Airport.objects.update_or_create(
                code=data['code'],
                site=nyc,
                defaults={**data, 'is_active': True}
            )
        self.stdout.write(self.style.SUCCESS('  [OK] NYC airports created'))

        # =====================================================================
        # 3. AIRPORTS — DOMINICAN REPUBLIC
        # =====================================================================
        self.stdout.write('  Creating DR airports...')

        dr_airports_data = [
            {
                'code': 'PUJ',
                'name': 'Aeropuerto Internacional de Punta Cana',
                'city': 'Punta Cana',
                'country': 'DO',
                'description': 'The busiest airport in the Caribbean, serving millions of tourists visiting the world-famous Punta Cana resort area.',
                'latitude': 18.5674,
                'longitude': -68.3634,
            },
            {
                'code': 'SDQ',
                'name': 'Aeropuerto Internacional Las Américas',
                'city': 'Santo Domingo',
                'country': 'DO',
                'description': 'The main airport serving the capital city of Santo Domingo, named after the Americas in honor of the New World.',
                'latitude': 18.4297,
                'longitude': -69.6689,
            },
            {
                'code': 'STI',
                'name': 'Aeropuerto Internacional del Cibao',
                'city': 'Santiago de los Caballeros',
                'country': 'DO',
                'description': 'Serving Santiago, the second-largest city in the Dominican Republic and the heart of the Cibao Valley.',
                'latitude': 19.4061,
                'longitude': -70.6047,
            },
            {
                'code': 'POP',
                'name': 'Aeropuerto Internacional Gregorio Luperón',
                'city': 'Puerto Plata',
                'country': 'DO',
                'description': 'Gateway to the beautiful north coast of the Dominican Republic, including Puerto Plata\'s golden beaches.',
                'latitude': 19.7579,
                'longitude': -70.5700,
            },
            {
                'code': 'LRM',
                'name': 'Aeropuerto Internacional La Romana',
                'city': 'La Romana',
                'country': 'DO',
                'description': 'Serving the luxury resort area of Casa de Campo and the charming town of La Romana.',
                'latitude': 18.4507,
                'longitude': -68.9118,
            },
            {
                'code': 'BRX',
                'name': 'Aeropuerto Internacional María Montez',
                'city': 'Barahona',
                'country': 'DO',
                'description': 'The gateway to the stunning southwest region of the Dominican Republic, including Bahía de las Águilas.',
                'latitude': 18.2515,
                'longitude': -71.1204,
            },
            {
                'code': 'AZS',
                'name': 'Aeropuerto Internacional de Samaná El Catey',
                'city': 'Samaná',
                'country': 'DO',
                'description': 'Serving the Samaná Peninsula, famous for whale watching and pristine beaches like Playa Rincón.',
                'latitude': 19.2670,
                'longitude': -69.7420,
            },
        ]

        for data in dr_airports_data:
            Airport.objects.update_or_create(
                code=data['code'],
                site=dr,
                defaults={**data, 'is_active': True}
            )
        self.stdout.write(self.style.SUCCESS('  [OK] DR airports created'))

        # =====================================================================
        # 4. DESTINATIONS
        # =====================================================================
        self.stdout.write('  Creating popular destinations...')

        # NYC Destinations from JFK
        jfk = Airport.objects.get(code='JFK', site=nyc)
        nyc_destinations = [
            ('Manhattan — Midtown', 'Midtown Manhattan, New York, NY', 'NEIGHBORHOOD', 'The heart of NYC: Times Square, Broadway, Empire State Building.'),
            ('Manhattan — Downtown', 'Lower Manhattan, New York, NY', 'NEIGHBORHOOD', 'Financial District, Wall Street, World Trade Center.'),
            ('Manhattan — Upper East Side', 'Upper East Side, New York, NY', 'NEIGHBORHOOD', 'Museum Mile, Central Park, prestigious residences.'),
            ('Brooklyn — Downtown', 'Downtown Brooklyn, NY', 'NEIGHBORHOOD', 'Brooklyn Bridge, DUMBO, vibrant culture.'),
            ('The Hamptons', 'Southampton, NY', 'NEIGHBORHOOD', 'Exclusive beach communities on Long Island\'s South Fork.'),
            ('Jersey City', 'Jersey City, NJ', 'NEIGHBORHOOD', 'Waterfront views of Manhattan, convenient NJ location.'),
        ]

        for name, address, dtype, desc in nyc_destinations:
            Destination.objects.update_or_create(
                airport=jfk,
                name=name,
                defaults={
                    'address': address,
                    'destination_type': dtype,
                    'description': desc,
                    'is_active': True,
                }
            )

        # Also add to LGA and EWR
        lga = Airport.objects.get(code='LGA', site=nyc)
        ewr = Airport.objects.get(code='EWR', site=nyc)
        for airport in [lga, ewr]:
            for name, address, dtype, desc in nyc_destinations[:4]:
                Destination.objects.update_or_create(
                    airport=airport,
                    name=name,
                    defaults={
                        'address': address,
                        'destination_type': dtype,
                        'description': desc,
                        'is_active': True,
                    }
                )

        # DR Destinations from PUJ
        puj = Airport.objects.get(code='PUJ', site=dr)
        puj_destinations = [
            ('Bávaro — Hotel Zone', 'Bávaro, Punta Cana', 'HOTEL', 'World-famous resort area with all-inclusive hotels.'),
            ('Cap Cana', 'Cap Cana, Punta Cana', 'RESORT', 'Ultra-luxury gated community and resort.'),
            ('Punta Cana Village', 'Punta Cana Village', 'NEIGHBORHOOD', 'Local town center with shops and restaurants.'),
            ('Hard Rock Hotel', 'Hard Rock Hotel & Casino Punta Cana', 'HOTEL', 'Iconic all-inclusive resort experience.'),
            ('Casa de Campo', 'Casa de Campo, La Romana', 'RESORT', 'Legendary luxury resort with world-class amenities.'),
            ('Bayahíbe', 'Bayahíbe, La Altagracia', 'NEIGHBORHOOD', 'Charming fishing village and gateway to Saona Island.'),
        ]

        for name, address, dtype, desc in puj_destinations:
            Destination.objects.update_or_create(
                airport=puj,
                name=name,
                defaults={
                    'address': address,
                    'destination_type': dtype,
                    'description': desc,
                    'is_active': True,
                }
            )

        # DR Destinations from SDQ
        sdq = Airport.objects.get(code='SDQ', site=dr)
        sdq_destinations = [
            ('Zona Colonial', 'Ciudad Colonial, Santo Domingo', 'NEIGHBORHOOD', 'Historic colonial quarter, UNESCO World Heritage Site.'),
            ('Piantini', 'Piantini, Santo Domingo', 'NEIGHBORHOOD', 'Upscale district with fine dining and shopping.'),
            ('Naco', 'Naco, Santo Domingo', 'NEIGHBORHOOD', 'Modern residential and business area.'),
            ('Juan Dolio', 'Juan Dolio, San Pedro de Macorís', 'NEIGHBORHOOD', 'Beach town popular with locals and tourists.'),
            ('Boca Chica', 'Boca Chica, Santo Domingo', 'NEIGHBORHOOD', 'Beautiful beach closest to the capital.'),
        ]

        for name, address, dtype, desc in sdq_destinations:
            Destination.objects.update_or_create(
                airport=sdq,
                name=name,
                defaults={
                    'address': address,
                    'destination_type': dtype,
                    'description': desc,
                    'is_active': True,
                }
            )

        self.stdout.write(self.style.SUCCESS('  [OK] Destinations created'))

        # =====================================================================
        # 5. VEHICLE CATEGORIES & VEHICLES
        # =====================================================================
        self.stdout.write('  Creating vehicle fleet...')

        # Category 1: Executive SUV
        exec_suv, _ = VehicleCategory.objects.update_or_create(
            slug='executive-suv',
            defaults={
                'name': 'Executive SUV',
                'description': 'Premium full-size SUV for ultimate comfort and style. Spacious interior with leather seats, climate control, and ample luggage space.',
                'passengers_capacity': 6,
                'luggage_capacity': 6,
                'is_active': True,
                'order': 1,
            }
        )

        # Category 2: Business Sedan
        business_sedan, _ = VehicleCategory.objects.update_or_create(
            slug='business-sedan',
            defaults={
                'name': 'Business Sedan',
                'description': 'Elegant sedan for professional travel. Cadillac XTS, Chrysler 300, or similar.',
                'passengers_capacity': 3,
                'luggage_capacity': 2,
                'is_active': True,
                'order': 2,
            }
        )

        # Category 3: Luxury Sedan
        luxury_sedan, _ = VehicleCategory.objects.update_or_create(
            slug='luxury-sedan',
            defaults={
                'name': 'Luxury Sedan',
                'description': 'Top-of-the-line luxury sedan for first-class comfort. Mercedes-Benz S-Class, BMW 7 Series, or similar.',
                'passengers_capacity': 3,
                'luggage_capacity': 2,
                'is_active': True,
                'order': 3,
            }
        )

        # Category 4: Minivan
        minivan, _ = VehicleCategory.objects.update_or_create(
            slug='minivan',
            defaults={
                'name': 'Minivan',
                'description': 'Comfortable and spacious minivan for family and group travel. Toyota Sienna, Chevrolet Traverse, or similar.',
                'passengers_capacity': 4,
                'luggage_capacity': 4,
                'is_active': True,
                'order': 4,
            }
        )

        # Category 5: Sprinter Van
        sprinter, _ = VehicleCategory.objects.update_or_create(
            slug='sprinter-van',
            defaults={
                'name': 'Sprinter Van',
                'description': 'Mercedes-Benz Sprinter or Ford Transit for groups up to 14 passengers. Perfect for corporate transfers and large groups.',
                'passengers_capacity': 14,
                'luggage_capacity': 14,
                'is_active': True,
                'order': 5,
            }
        )

        # Category 6: Stretch Limousine
        limo, _ = VehicleCategory.objects.update_or_create(
            slug='limousine',
            defaults={
                'name': 'Stretch Limousine',
                'description': 'Classic stretch limousine for special occasions, weddings, and parties. Lincoln MKT, Jet Sprinter, or similar.',
                'passengers_capacity': 8,
                'luggage_capacity': 5,
                'is_active': True,
                'order': 6,
            }
        )

        # Vehicles
        # 1. Executive SUV
        escalade, _ = Vehicle.objects.update_or_create(
            name='Cadillac Escalade',
            defaults={
                'category': exec_suv,
                'model_year': 2024,
                'price_multiplier': 1.0,
                'features': {
                    'leather_seats': True,
                    'wifi': True,
                    'water_bottles': True,
                    'phone_charger': True,
                    'climate_control': True,
                    'tinted_windows': True,
                },
                'is_active': True,
            }
        )
        escalade.sites.set([nyc, dr])

        suburban, _ = Vehicle.objects.update_or_create(
            name='Chevrolet Suburban',
            defaults={
                'category': exec_suv,
                'model_year': 2024,
                'price_multiplier': 0.95,
                'features': {
                    'leather_seats': True,
                    'wifi': True,
                    'water_bottles': True,
                    'phone_charger': True,
                    'climate_control': True,
                },
                'is_active': True,
            }
        )
        suburban.sites.set([nyc, dr])

        yukon, _ = Vehicle.objects.update_or_create(
            name='GMC Yukon Denali',
            defaults={
                'category': exec_suv,
                'model_year': 2024,
                'price_multiplier': 0.95,
                'features': {
                    'leather_seats': True,
                    'wifi': True,
                    'water_bottles': True,
                    'climate_control': True,
                },
                'is_active': True,
            }
        )
        yukon.sites.set([nyc, dr])

        # 2. Business Sedan
        xts, _ = Vehicle.objects.update_or_create(
            name='Cadillac XTS',
            defaults={
                'category': business_sedan,
                'model_year': 2023,
                'price_multiplier': 0.85,
                'features': {
                    'leather_seats': True,
                    'water_bottles': True,
                    'phone_charger': True,
                },
                'is_active': True,
            }
        )
        xts.sites.set([nyc, dr])

        chrysler, _ = Vehicle.objects.update_or_create(
            name='Chrysler 300',
            defaults={
                'category': business_sedan,
                'model_year': 2023,
                'price_multiplier': 0.80,
                'features': {
                    'leather_seats': True,
                    'water_bottles': True,
                },
                'is_active': True,
            }
        )
        chrysler.sites.set([nyc, dr])

        # 3. Luxury Sedan
        s_class, _ = Vehicle.objects.update_or_create(
            name='Mercedes-Benz S-Class',
            defaults={
                'category': luxury_sedan,
                'model_year': 2024,
                'price_multiplier': 1.20,
                'features': {
                    'leather_seats': True,
                    'wifi': True,
                    'water_bottles': True,
                    'phone_charger': True,
                    'climate_control': True,
                    'rear_entertainment': True,
                },
                'is_active': True,
            }
        )
        s_class.sites.set([nyc, dr])

        bmw_7, _ = Vehicle.objects.update_or_create(
            name='BMW 7 Series',
            defaults={
                'category': luxury_sedan,
                'model_year': 2024,
                'price_multiplier': 1.15,
                'features': {
                    'leather_seats': True,
                    'wifi': True,
                    'water_bottles': True,
                    'phone_charger': True,
                    'climate_control': True,
                },
                'is_active': True,
            }
        )
        bmw_7.sites.set([nyc, dr])

        # 4. Minivan
        sienna, _ = Vehicle.objects.update_or_create(
            name='Toyota Sienna',
            defaults={
                'category': minivan,
                'model_year': 2023,
                'price_multiplier': 0.85,
                'features': {
                    'water_bottles': True,
                    'phone_charger': True,
                    'climate_control': True,
                },
                'is_active': True,
            }
        )
        sienna.sites.set([nyc, dr])

        traverse, _ = Vehicle.objects.update_or_create(
            name='Chevrolet Traverse',
            defaults={
                'category': minivan,
                'model_year': 2023,
                'price_multiplier': 0.85,
                'features': {
                    'water_bottles': True,
                    'phone_charger': True,
                },
                'is_active': True,
            }
        )
        traverse.sites.set([nyc, dr])

        # 5. Sprinter Van
        sprinter_vehicle, _ = Vehicle.objects.update_or_create(
            name='Mercedes-Benz Sprinter',
            defaults={
                'category': sprinter,
                'model_year': 2024,
                'price_multiplier': 1.40,
                'features': {
                    'wifi': True,
                    'water_bottles': True,
                    'phone_charger': True,
                    'climate_control': True,
                    'luggage_partition': True,
                    'high_roof': True,
                },
                'is_active': True,
            }
        )
        sprinter_vehicle.sites.set([nyc, dr])

        transit, _ = Vehicle.objects.update_or_create(
            name='Ford Transit',
            defaults={
                'category': sprinter,
                'model_year': 2023,
                'price_multiplier': 1.25,
                'features': {
                    'water_bottles': True,
                    'phone_charger': True,
                    'climate_control': True,
                },
                'is_active': True,
            }
        )
        transit.sites.set([nyc, dr])

        # 6. Limousine
        mkt_limo, _ = Vehicle.objects.update_or_create(
            name='Lincoln MKT Stretch Limo',
            defaults={
                'category': limo,
                'model_year': 2022,
                'price_multiplier': 1.50,
                'features': {
                    'leather_seats': True,
                    'water_bottles': True,
                    'phone_charger': True,
                    'bar_filled': True,
                    'mood_lighting': True,
                },
                'is_active': True,
            }
        )
        mkt_limo.sites.set([nyc, dr])

        self.stdout.write('  Linking vehicle images...')

        # ── Link images to vehicles ──
        # Map vehicle names to their image files in media/vehicles/
        import os
        from django.conf import settings

        vehicle_images = {
            'Cadillac Escalade': 'vehicles/escalade.jpg',
            'Chevrolet Suburban': 'vehicles/db5b0cd41b1ec2043d931d2eda123d47.jpg',
            'GMC Yukon Denali': 'vehicles/2023-gmc-yukon-trims-denali-xl.jpg',
            'Cadillac XTS': 'vehicles/2016-cadillac-xts-4-door-sedan-fwd-angular-front-exterior-view_100571416_m.jpg',
            'Chrysler 300': 'vehicles/7a62cc3a555fa543de597c474608489d.jpg',
            'Mercedes-Benz S-Class': 'vehicles/000000008395616.jpg',
            'BMW 7 Series': 'vehicles/P90491611_highRes_the-bmw-740i-in-sout.jpg',
            'Toyota Sienna': 'vehicles/Toyota_Sienna_2025_1.jpg',
            'Chevrolet Traverse': 'vehicles/13370820.jpg',
            'Mercedes-Benz Sprinter': 'vehicles/Mercedes-Sprinter-Hire.jpg',
            'Ford Transit': 'vehicles/eyJidWNrZXQiOiJkYXRhay1jZG4teHkiLCJrZXkiOiJjb25maWd1cmF0b3ItaW1ncy9jYXJzL2ttNzd_V6phpfo.jpg',
            'Lincoln MKT Stretch Limo': 'vehicles/MKT-1.jpg',
        }

        for vehicle_name, image_path in vehicle_images.items():
            try:
                vehicle = Vehicle.objects.get(name=vehicle_name)
                full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                if os.path.exists(full_path):
                    vehicle.image = image_path
                    vehicle.save(update_fields=['image'])
                    self.stdout.write(f'    {vehicle_name} -> {image_path}')
                else:
                    self.stdout.write(self.style.WARNING(f'    {vehicle_name} — image not found: {image_path}'))
            except Vehicle.DoesNotExist:
                pass

        # Link category images
        category_images = {
            'sprinter-van': 'vehicles/categories/van.jpg',
        }
        for cat_slug, image_path in category_images.items():
            try:
                cat = VehicleCategory.objects.get(slug=cat_slug)
                full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                if os.path.exists(full_path):
                    cat.image = image_path
                    cat.save(update_fields=['image'])
                    self.stdout.write(f'    Category {cat.name} -> {image_path}')
            except VehicleCategory.DoesNotExist:
                pass

        self.stdout.write(self.style.SUCCESS('  [OK] Vehicle images linked'))

        self.stdout.write(self.style.SUCCESS('  [OK] Vehicle fleet created'))

        # =====================================================================
        # 6. PREMIUM ADD-ONS
        # =====================================================================
        self.stdout.write('  Creating premium add-ons...')

        addons_data = [
            {
                'name': 'Fast-Track VIP',
                'slug': 'fast-track-vip',
                'description': 'Skip the lines at the airport with our VIP fast-track service. Dedicated agent meets you at the gate.',
                'price': 45.00,
                'icon': 'fa-bolt',
                'is_active': True,
            },
            {
                'name': 'Concierge Booking',
                'slug': 'concierge-booking',
                'description': 'Personal concierge to arrange restaurant reservations, event tickets, and local experiences.',
                'price': 35.00,
                'icon': 'fa-concierge-bell',
                'is_active': True,
            },
            {
                'name': 'Multi-Stop Service',
                'slug': 'multi-stop',
                'description': 'Add additional stops along your route. Perfect for group pickups or sightseeing.',
                'price': 25.00,
                'icon': 'fa-route',
                'is_active': True,
            },
            {
                'name': 'Real Estate Tour',
                'slug': 'real-estate-tour',
                'description': 'Dedicated vehicle and chauffeur for property viewings. Full day with unlimited stops.',
                'price': 150.00,
                'icon': 'fa-building',
                'is_active': True,
            },
            {
                'name': 'Child Safety Seat',
                'slug': 'child-seat',
                'description': 'FAA-approved child safety seat installed and ready for your little one.',
                'price': 15.00,
                'icon': 'fa-baby',
                'is_active': True,
            },
            {
                'name': 'Meet & Greet Sign',
                'slug': 'meet-greet',
                'description': 'Professional chauffeur with personalized name sign at arrivals.',
                'price': 0.00,
                'icon': 'fa-id-badge',
                'is_active': True,
            },
        ]

        for data in addons_data:
            PremiumAddOn.objects.update_or_create(
                slug=data['slug'],
                defaults=data
            )

        self.stdout.write(self.style.SUCCESS('  [OK] Premium add-ons created'))

        # =====================================================================
        # 7. PRICING RULES
        # =====================================================================
        self.stdout.write('  Creating pricing rules and zone vehicle prices...')
        
        from decimal import Decimal

        all_categories = [exec_suv, business_sedan, luxury_sedan, minivan, sprinter, limo]
        multipliers = {
            'executive-suv': Decimal('1.00'),
            'business-sedan': Decimal('0.80'),
            'luxury-sedan': Decimal('1.15'),
            'minivan': Decimal('0.85'),
            'sprinter-van': Decimal('1.40'),
            'limousine': Decimal('1.50'),
        }

        # NYC Pricing
        nyc_pricing = [
            ('JFK', 'Manhattan — Midtown', 85.00),
            ('JFK', 'Manhattan — Downtown', 80.00),
            ('JFK', 'Manhattan — Upper East Side', 90.00),
            ('JFK', 'Brooklyn — Downtown', 70.00),
            ('JFK', 'The Hamptons', 250.00),
            ('JFK', 'Jersey City', 95.00),
            ('LGA', 'Manhattan — Midtown', 65.00),
            ('LGA', 'Manhattan — Downtown', 70.00),
            ('LGA', 'Manhattan — Upper East Side', 60.00),
            ('LGA', 'Brooklyn — Downtown', 70.00),
            ('EWR', 'Manhattan — Midtown', 95.00),
            ('EWR', 'Manhattan — Downtown', 90.00),
            ('EWR', 'Manhattan — Upper East Side', 100.00),
            ('EWR', 'Brooklyn — Downtown', 100.00),
        ]

        # Seed AirportCategoryPrice (Airport Transfers base + per-km pricing)
        self.stdout.write('    Creating Airport Category Prices...')
        all_airports = Airport.objects.all()
        for airport in all_airports:
            # Determine standard base price for this airport
            if airport.site.slug == 'nyc':
                std_base = Decimal('80.00')
                std_base_km = 25
                std_per_km = Decimal('3.50')
            else:
                std_base = Decimal('100.00')
                std_base_km = 30
                std_per_km = Decimal('3.00')
                
            for category in all_categories:
                cat_multiplier = multipliers[category.slug]
                cat_base_price = std_base * cat_multiplier
                cat_per_km = std_per_km * cat_multiplier
                
                AirportCategoryPrice.objects.update_or_create(
                    airport=airport,
                    vehicle_category=category,
                    defaults={
                        'base_price': cat_base_price,
                        'base_km': std_base_km,
                        'price_per_km': cat_per_km,
                        'is_active': True,
                    }
                )

        # Seed Hourly/P2P rules
        self.stdout.write('    Creating Hourly and Point-to-Point pricing rules...')
        
        hourly_rates = {
            'executive-suv': Decimal('95.00'),
            'business-sedan': Decimal('75.00'),
            'luxury-sedan': Decimal('120.00'),
            'minivan': Decimal('80.00'),
            'sprinter-van': Decimal('150.00'),
            'limousine': Decimal('180.00'),
        }
        
        p2p_base_fares = {
            'executive-suv': Decimal('120.00'),
            'business-sedan': Decimal('90.00'),
            'luxury-sedan': Decimal('150.00'),
            'minivan': Decimal('100.00'),
            'sprinter-van': Decimal('200.00'),
            'limousine': Decimal('250.00'),
        }
        
        p2p_per_km_rates = {
            'executive-suv': Decimal('3.50'),
            'business-sedan': Decimal('2.50'),
            'luxury-sedan': Decimal('4.00'),
            'minivan': Decimal('3.00'),
            'sprinter-van': Decimal('5.00'),
            'limousine': Decimal('6.00'),
        }

        # Seed for both NYC and DR
        for s in [nyc, dr]:
            for category in all_categories:
                # 1. Hourly Rule
                hr_rate = hourly_rates.get(category.slug, Decimal('80.00'))
                PricingRule.objects.update_or_create(
                    site=s,
                    vehicle_category=category,
                    service_type='hourly',
                    vehicle=None,
                    defaults={
                        'base_price': hr_rate,
                        'minimum_price': hr_rate,
                        'is_active': True,
                    }
                )
                
                # 2. Point-to-Point Rule
                p2p_base = p2p_base_fares.get(category.slug, Decimal('100.00'))
                p2p_per_km = p2p_per_km_rates.get(category.slug, Decimal('3.00'))
                PricingRule.objects.update_or_create(
                    site=s,
                    vehicle_category=category,
                    service_type='point_to_point',
                    vehicle=None,
                    defaults={
                        'base_price': p2p_base,
                        'price_per_km': p2p_per_km,
                        'km_threshold': 25,
                        'minimum_price': p2p_base,
                        'is_active': True,
                    }
                )

        self.stdout.write(self.style.SUCCESS('  [OK] Pricing rules and zone vehicle prices created'))

        # =====================================================================
        # 8. SITE SETTINGS
        # =====================================================================
        self.stdout.write('  Creating site settings...')

        SiteSettings.objects.update_or_create(
            site=nyc,
            defaults={
                'company_name': 'AeroLux Select NYC',
                'developer_name': 'GABOOM',
                'developer_phone': '829 509 84 12',
                'contact_email': 'nyc@aeroluxeselect.com',
                'contact_phone': '+1 (212) 555-0199',
                'whatsapp_number': '+18295098412',
            }
        )

        SiteSettings.objects.update_or_create(
            site=dr,
            defaults={
                'company_name': 'AeroLux Select DR',
                'developer_name': 'GABOOM',
                'developer_phone': '829 509 84 12',
                'contact_email': 'dr@aeroluxeselect.com',
                'contact_phone': '+1 (809) 555-0188',
                'whatsapp_number': '+18295098412',
            }
        )

        self.stdout.write(self.style.SUCCESS('  [OK] Site settings created'))

        # =====================================================================
        # 8.5 WHATSAPP TEMPLATES
        # =====================================================================
        self.stdout.write('  Creating WhatsApp templates...')

        whatsapp_defaults = {
            'processing': 'Hello {customer_name}, thank you for choosing {company_name}. We have received your booking request {booking_reference}. We are currently processing it and will confirm shortly. Pickup: {pickup_address} on {pickup_date} at {pickup_time}.',
            'confirmed': 'Hello {customer_name}, your booking {booking_reference} with {company_name} is CONFIRMED. Your driver will meet you at {pickup_address} on {pickup_date} at {pickup_time}. Total price: {total_price}. Balance: {balance}. Thank you!',
            'reminder_12h': 'Hi {customer_name}, this is a reminder of your upcoming trip {booking_reference} with {company_name} in 12 hours. Pickup: {pickup_address} on {pickup_date} at {pickup_time}. We look forward to serving you!',
            'cancelled': 'Hello {customer_name}, we confirm that your booking {booking_reference} with {company_name} has been cancelled. If this was a mistake or you have questions, please contact us.'
        }

        for site in [nyc, dr]:
            comp_name = 'AeroLux Select NYC' if site == nyc else 'AeroLux Select DR'
            for trigger_type, text in whatsapp_defaults.items():
                formatted_text = text.replace('{company_name}', comp_name)
                WhatsAppTemplate.objects.update_or_create(
                    site=site,
                    trigger_type=trigger_type,
                    defaults={
                        'message_content': formatted_text
                    }
                )
        self.stdout.write(self.style.SUCCESS('  [OK] WhatsApp templates created'))

        # =====================================================================
        # 9. CMS CONTENT
        # =====================================================================
        self.stdout.write('  Creating CMS content...')

        # NYC CMS Content
        nyc_content = [
            ('hero_title', 'Hero Title', 'NYC Premium Car Service & Airport Transfers', 'HERO', 'en'),
            ('hero_subtitle', 'Hero Subtitle', 'Flat rates, no surprises. Professional chauffeurs. Direct driver contact.', 'HERO', 'en'),
            ('hero_cta', 'Hero CTA Button', 'Book Your Ride', 'HERO', 'en'),
            ('services_title', 'Services Title', 'Our Premium Services', 'SERVICES', 'en'),
            ('services_subtitle', 'Services Subtitle', 'Choose the perfect service for your travel needs', 'SERVICES', 'en'),
            ('about_title', 'About Title', 'Why Choose AeroLux Select NYC?', 'ABOUT', 'en'),
            ('about_text', 'About Text', 'We provide premium luxury transportation throughout the New York City metropolitan area. Our fleet of executive SUVs and professional chauffeurs ensure a first-class experience from airport to destination.', 'ABOUT', 'en'),
            ('fleet_title', 'Fleet Title', 'Our Executive Fleet', 'FLEET', 'en'),
            ('fleet_subtitle', 'Fleet Subtitle', 'Travel in style with our meticulously maintained vehicles', 'FLEET', 'en'),
            ('testimonials_title', 'Testimonials Title', 'What Our Clients Say', 'TESTIMONIALS', 'en'),
            ('footer_about', 'Footer About', 'AeroLux Select provides premium luxury car service and airport transfers in New York City. Professional, reliable, and always on time.', 'FOOTER', 'en'),
            ('contact_address', 'Contact Address', '347 Pacific St, Brooklyn, NY 11217', 'CONTACT', 'en'),
        ]

        for key, label, value, category, lang in nyc_content:
            SiteContent.objects.update_or_create(
                site=nyc,
                key=key,
                language=lang,
                defaults={
                    'label': label,
                    'value': value,
                    'category': category,
                    'order': 0,
                }
            )

        # DR CMS Content (English)
        dr_content_en = [
            ('hero_title', 'Hero Title', 'Dominican Republic VIP Car Service & Airport Transfers', 'HERO', 'en'),
            ('hero_subtitle', 'Hero Subtitle', 'Arrive in style. Premium transfers from every major airport.', 'HERO', 'en'),
            ('hero_cta', 'Hero CTA Button', 'Book Your Ride', 'HERO', 'en'),
            ('services_title', 'Services Title', 'Our Premium Services', 'SERVICES', 'en'),
            ('services_subtitle', 'Services Subtitle', 'Luxury transportation across the Dominican Republic', 'SERVICES', 'en'),
            ('about_title', 'About Title', 'Why Choose AeroLux Select DR?', 'ABOUT', 'en'),
            ('about_text', 'About Text', 'Experience the Dominican Republic in luxury. From Punta Cana to Santo Domingo, our executive SUVs and professional drivers ensure you travel in comfort and style.', 'ABOUT', 'en'),
            ('fleet_title', 'Fleet Title', 'Our Executive Fleet', 'FLEET', 'en'),
            ('fleet_subtitle', 'Fleet Subtitle', 'Travel in style with our premium vehicles', 'FLEET', 'en'),
            ('testimonials_title', 'Testimonials Title', 'What Our Clients Say', 'TESTIMONIALS', 'en'),
            ('footer_about', 'Footer About', 'AeroLux Select provides premium luxury car service and airport transfers across the Dominican Republic. Professional, reliable, always on time.', 'FOOTER', 'en'),
            ('contact_address', 'Contact Address', 'Punta Cana, Dominican Republic', 'CONTACT', 'en'),
        ]

        for key, label, value, category, lang in dr_content_en:
            SiteContent.objects.update_or_create(
                site=dr,
                key=key,
                language=lang,
                defaults={
                    'label': label,
                    'value': value,
                    'category': category,
                    'order': 0,
                }
            )

        # DR CMS Content (Spanish)
        dr_content_es = [
            ('hero_title', 'Título Hero', 'Servicio VIP de Autos en República Dominicana & Transfers al Aeropuerto', 'HERO', 'es'),
            ('hero_subtitle', 'Subtítulo Hero', 'Llegue con estilo. Transfers premium desde cada aeropuerto principal.', 'HERO', 'es'),
            ('hero_cta', 'Botón CTA Hero', 'Reserve Su Viaje', 'HERO', 'es'),
            ('services_title', 'Título Servicios', 'Nuestros Servicios Premium', 'SERVICES', 'es'),
            ('services_subtitle', 'Subtítulo Servicios', 'Transporte de lujo en toda la República Dominicana', 'SERVICES', 'es'),
            ('about_title', 'Título Nosotros', '¿Por qué elegir AeroLux Select DR?', 'ABOUT', 'es'),
            ('about_text', 'Texto Nosotros', 'Viva la República Dominicana con lujo. Desde Punta Cana hasta Santo Domingo, nuestros SUV ejecutivos y conductores profesionales aseguran que viaje con comodidad y estilo.', 'ABOUT', 'es'),
            ('fleet_title', 'Título Flota', 'Nuestra Flota Ejecutiva', 'FLEET', 'es'),
            ('fleet_subtitle', 'Subtítulo Flota', 'Viaje con estilo en nuestros vehículos premium', 'FLEET', 'es'),
            ('testimonials_title', 'Título Testimonios', 'Lo Que Dicen Nuestros Clientes', 'TESTIMONIALS', 'es'),
            ('footer_about', 'Footer Nosotros', 'AeroLux Select ofrece servicio premium de autos de lujo y transfers al aeropuerto en toda la República Dominicana.', 'FOOTER', 'es'),
            ('contact_address', 'Dirección de Contacto', 'Punta Cana, República Dominicana', 'CONTACT', 'es'),
        ]

        for key, label, value, category, lang in dr_content_es:
            SiteContent.objects.update_or_create(
                site=dr,
                key=key,
                language=lang,
                defaults={
                    'label': label,
                    'value': value,
                    'category': category,
                    'order': 0,
                }
            )

        self.stdout.write(self.style.SUCCESS('  [OK] CMS content created'))

        # =====================================================================
        # 10. SAMPLE TESTIMONIALS
        # =====================================================================
        self.stdout.write('  Creating sample testimonials...')

        testimonials = [
            (nyc, 'Sarah M.', 5, 'Incredible service from JFK to Manhattan. Driver was waiting with a name sign, car was spotless, and the ride was smooth. Will definitely use again!', 'airport_transfer'),
            (nyc, 'James T.', 5, 'Used the hourly service for a full day of meetings across Manhattan. Professional driver, comfortable Escalade, and always on time between stops.', 'hourly'),
            (nyc, 'Michael R.', 4, 'Great experience for our Newark airport transfer. Very competitive flat rate and the driver was very friendly. Highly recommend!', 'airport_transfer'),
            (dr, 'Carlos D.', 5, '¡Excelente servicio! El conductor nos recogió en PUJ y nos llevó al hotel en Bávaro. Vehículo de lujo y servicio impecable.', 'airport_transfer'),
            (dr, 'Emily W.', 5, 'Perfect transfer from Punta Cana airport to our resort in Cap Cana. The Escalade was beautiful and the driver very professional.', 'airport_transfer'),
            (dr, 'Roberto S.', 5, 'Usamos el servicio por horas para un tour inmobiliario. El conductor conocía todas las zonas y nos dio un servicio excelente.', 'hourly'),
        ]

        for site, name, rating, comment, service in testimonials:
            Testimonial.objects.update_or_create(
                site=site,
                customer_name=name,
                defaults={
                    'rating': rating,
                    'comment': comment,
                    'service_type': service,
                    'is_featured': True,
                }
            )

        self.stdout.write(self.style.SUCCESS('  [OK] Testimonials created'))

        # =====================================================================
        # DONE
        # =====================================================================
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('AeroLux Select database seeded successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  Sites: {Site.objects.count()}')
        self.stdout.write(f'  Airports: {Airport.objects.count()}')
        self.stdout.write(f'  Destinations: {Destination.objects.count()}')
        self.stdout.write(f'  Vehicle Categories: {VehicleCategory.objects.count()}')
        self.stdout.write(f'  Vehicles: {Vehicle.objects.count()}')
        self.stdout.write(f'  Add-ons: {PremiumAddOn.objects.count()}')
        self.stdout.write(f'  Pricing Rules: {PricingRule.objects.count()}')
        self.stdout.write(f'  Airport Category Prices: {AirportCategoryPrice.objects.count()}')
        self.stdout.write(f'  CMS Content: {SiteContent.objects.count()}')
        self.stdout.write(f'  Testimonials: {Testimonial.objects.count()}')
        self.stdout.write('')
