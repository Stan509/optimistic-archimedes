from django.test import TestCase, Client
from django.conf import settings
from django.urls import reverse
from decimal import Decimal
from datetime import date, time
from core.models import (
    Site, Airport, Destination, VehicleCategory, Vehicle,
    PremiumAddOn, PricingRule, Booking, SiteSettings, SiteContent
)

class MultiSiteMiddlewareTestCase(TestCase):
    def setUp(self):
        # Create sites
        self.nyc = Site.objects.create(
            slug='nyc',
            name='New York City',
            domain='aeroluxeselect-nyc.com',
            is_active=True
        )
        self.dr = Site.objects.create(
            slug='dr',
            name='Dominican Republic',
            domain='aeroluxeselect-dr.com',
            is_active=True
        )

    def test_default_site_nyc(self):
        """Standard request defaults to NYC site."""
        client = Client()
        response = client.get('/nyc/')
        self.assertEqual(response.status_code, 200)

    def test_dev_prefix_site_routing(self):
        """URL prefix determines the active site in development."""
        client = Client()
        response_nyc = client.get('/nyc/')
        self.assertEqual(response_nyc.context['current_site'], self.nyc)
        
        response_dr = client.get('/dr/')
        self.assertEqual(response_dr.context['current_site'], self.dr)

    def test_site_settings_singleton_retrieval(self):
        """Retrieving settings for a site creates or returns the singleton settings."""
        settings_nyc = SiteSettings.get_settings(self.nyc)
        self.assertEqual(settings_nyc.site, self.nyc)
        self.assertEqual(settings_nyc.company_name, 'AeroLux Select')
        
        settings_nyc_2 = SiteSettings.get_settings(self.nyc)
        self.assertEqual(settings_nyc.id, settings_nyc_2.id)


class DynamicPricingAndCommissionTestCase(TestCase):
    def setUp(self):
        # Setup site
        self.nyc = Site.objects.create(
            slug='nyc',
            name='New York City',
            domain='aeroluxeselect-nyc.com',
            is_active=True
        )
        # Create airport and destination
        self.jfk = Airport.objects.create(
            site=self.nyc,
            code='JFK',
            name='John F. Kennedy International Airport',
            city='Queens',
            country='US',
            is_active=True
        )
        self.midtown = Destination.objects.create(
            airport=self.jfk,
            name='Manhattan — Midtown',
            address='Midtown Manhattan',
            destination_type='NEIGHBORHOOD',
            is_active=True
        )
        # Create vehicle category
        self.exec_suv = VehicleCategory.objects.create(
            slug='executive-suv',
            name='Executive SUV',
            description='Premium SUV',
            passengers_capacity=6,
            luggage_capacity=6,
            is_active=True,
            order=1
        )
        # Create pricing rule
        self.rule = PricingRule.objects.create(
            site=self.nyc,
            vehicle_category=self.exec_suv,
            service_type='hourly',
            base_price=Decimal('85.00'),
            minimum_price=Decimal('85.00'),
            is_active=True
        )
        from core.models import AirportCategoryPrice
        self.airport_price = AirportCategoryPrice.objects.create(
            airport=self.jfk,
            vehicle_category=self.exec_suv,
            base_price=Decimal('85.00'),
            base_km=25,
            price_per_km=Decimal('3.50'),
            is_active=True
        )
        # Create add-ons
        self.fast_track = PremiumAddOn.objects.create(
            name='Fast-Track VIP',
            slug='fast-track-vip',
            price=Decimal('45.00'),
            is_active=True
        )
        self.concierge = PremiumAddOn.objects.create(
            name='Concierge Booking',
            slug='concierge-booking',
            price=Decimal('35.00'),
            is_active=True
        )

    def test_direct_booking_pricing(self):
        """Direct booking has no platform commission and sums total correctly."""
        booking = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='John Doe',
            customer_email='john@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            destination=self.midtown,
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            vehicle_category=self.exec_suv,
            base_price=Decimal('85.00'),
            booking_source='DIRECT'
        )
        booking.addons.add(self.fast_track, self.concierge)
        
        # Calculate totals
        total = booking.calculate_total()
        self.assertEqual(booking.addons_total, Decimal('80.00'))  # 45 + 35
        self.assertEqual(booking.platform_fee, Decimal('0.00'))
        self.assertEqual(total, Decimal('165.00'))  # 85 base + 80 addons

    def test_viator_commission_markup(self):
        """Viator booking automatically applies 25% platform markup."""
        booking = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Viator Guest',
            customer_email='viator@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            destination=self.midtown,
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),  # Ease of percentage checking
            booking_source='VIATOR',
            platform_commission_rate=Decimal('0.25')
        )
        total = booking.calculate_total()
        self.assertEqual(booking.platform_fee, Decimal('25.00'))  # 25% of 100
        self.assertEqual(total, Decimal('125.00'))  # 100 base + 25 commission

    def test_expedia_commission_markup(self):
        """Expedia booking automatically applies 20% platform markup."""
        booking = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Expedia Guest',
            customer_email='expedia@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            destination=self.midtown,
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            booking_source='EXPEDIA',
            platform_commission_rate=Decimal('0.20')
        )
        total = booking.calculate_total()
        self.assertEqual(booking.platform_fee, Decimal('20.00'))  # 20% of 100
        self.assertEqual(total, Decimal('120.00'))  # 100 base + 20 commission

    def test_hourly_service_duration_validation(self):
        """Hourly bookings are validated to require between 3 and 12 hours."""
        booking = Booking(
            site=self.nyc,
            service_type='hourly',
            customer_name='Hourly Guest',
            customer_email='hourly@example.com',
            customer_phone='+12125550199',
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            hours_requested=Decimal('2.0'),  # Invalid (minimum is 3.0)
            hourly_rate=Decimal('70.00')
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            booking.full_clean()

        # Invalid (maximum is 12.0)
        booking.hours_requested = Decimal('13.0')
        with self.assertRaises(ValidationError):
            booking.full_clean()

        # Valid duration
        booking.hours_requested = Decimal('12.0')
        booking.full_clean()  # Should not raise exception
        total = booking.calculate_total()
        self.assertEqual(booking.base_price, Decimal('840.00'))  # 12 hrs * $70/hr
        self.assertEqual(total, Decimal('840.00'))

    def test_round_trip_validation(self):
        """Bookings with round_trip=True must have a return date and time."""
        booking = Booking(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Round Trip Guest',
            customer_email='rt@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            destination=self.midtown,
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            round_trip=True,
            # return_date and return_time are missing
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            booking.full_clean()

        booking.return_date = date.today()
        booking.return_time = time(18, 0)
        booking.full_clean()  # Should be valid now

    def test_point_to_point_pricing(self):
        """Point-to-Point pricing correctly computes base_price + stops_fee and double fare if round-trip."""
        booking = Booking.objects.create(
            site=self.nyc,
            service_type='point_to_point',
            customer_name='P2P Guest',
            customer_email='p2p@example.com',
            customer_phone='+12125550199',
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            base_price=Decimal('80.00'),
            number_of_stops=2,
            stop_addresses='Stop 1, Stop 2',
            round_trip=True,
            return_date=date.today(),
            return_time=time(18, 0),
            booking_source='DIRECT'
        )
        total = booking.calculate_total()
        # total_price = (base_price * 2.0) + (stops * 20.0) + addons + platform_fee
        # total_price = (80 * 2) + (2 * 20) = 160 + 40 = 200
        self.assertEqual(total, Decimal('200.00'))


class BookingFlowViewsTestCase(TestCase):
    def setUp(self):
        # Create site and configurations
        self.nyc = Site.objects.create(
            slug='nyc',
            name='New York City',
            domain='aeroluxeselect-nyc.com',
            is_active=True
        )
        self.jfk = Airport.objects.create(
            site=self.nyc,
            code='JFK',
            name='JFK Airport',
            is_active=True
        )
        self.midtown = Destination.objects.create(
            airport=self.jfk,
            name='Midtown',
            is_active=True
        )
        self.exec_suv = VehicleCategory.objects.create(
            slug='executive-suv',
            name='Executive SUV',
            is_active=True,
            order=1
        )
        # Setup pricing rules
        self.p2p_rule = PricingRule.objects.create(
            site=self.nyc,
            vehicle_category=self.exec_suv,
            service_type='point_to_point',
            base_price=Decimal('100.00'),
            is_active=True
        )
        self.hourly_rule = PricingRule.objects.create(
            site=self.nyc,
            vehicle_category=self.exec_suv,
            service_type='hourly',
            base_price=Decimal('75.00'),
            is_active=True
        )
        from core.models import AirportCategoryPrice
        self.airport_price = AirportCategoryPrice.objects.create(
            airport=self.jfk,
            vehicle_category=self.exec_suv,
            base_price=Decimal('85.00'),
            base_km=25,
            price_per_km=Decimal('3.50'),
            is_active=True
        )

    def test_api_pricing_p2p(self):
        """api_pricing returns correct pricing for Point-to-Point bookings."""
        client = Client()
        response = client.get(
            reverse('site_nyc:api_pricing'),
            {
                'service_type': 'point_to_point',
                'vehicle_category_id': self.exec_suv.id,
                'number_of_stops': 3,
                'round_trip': 'true'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        pricing_info = data['pricing'][0]
        # base_price = (100 * 2) + (3 * 20) = 260
        self.assertEqual(pricing_info['base_price'], 260.0)
        self.assertEqual(pricing_info['starting_price'], 100.0)

    def test_api_pricing_hourly(self):
        """api_pricing returns correct pricing for Hourly bookings."""
        client = Client()
        response = client.get(
            reverse('site_nyc:api_pricing'),
            {
                'service_type': 'hourly',
                'vehicle_category_id': self.exec_suv.id,
                'hours': 5
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        pricing_info = data['pricing'][0]
        # base_price = 75 * 5 = 375
        self.assertEqual(pricing_info['base_price'], 375.0)
        self.assertEqual(pricing_info['hourly_rate'], 75.0)
        self.assertEqual(pricing_info['hours'], 5)

    def test_booking_transfer_direction_saving(self):
        """Booking flow views preserve and save the transfer_direction and meeting_point parameters."""
        # 1. Start session by POSTing to step 1
        client = Client()
        response = client.post(
            reverse('site_nyc:booking_step1'),
            {
                'service_type': 'airport_transfer',
                'airport_id': self.jfk.id,
                'destination_id': self.midtown.id,
                'transfer_direction': 'DEST_TO_AIRPORT',
                'meeting_point': 'Terminal B gate 3',
                'pickup_date': date.today().strftime('%Y-%m-%d'),
                'pickup_time': '12:00'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify session is populated
        session_data = client.session['booking']
        self.assertEqual(session_data['transfer_direction'], 'DEST_TO_AIRPORT')
        self.assertEqual(session_data['meeting_point'], 'Terminal B gate 3')

    def test_booking_meeting_point_persistence(self):
        """Booking model saves and preserves the meeting_point field."""
        booking = Booking.objects.create(
            site=self.nyc,
            service_type='point_to_point',
            customer_name='John Doe',
            customer_email='john@example.com',
            customer_phone='+12125550199',
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            meeting_point='Meet inside the hotel main lobby next to the fountain.',
            base_price=Decimal('100.00')
        )
        saved_booking = Booking.objects.get(id=booking.id)
        self.assertEqual(saved_booking.meeting_point, 'Meet inside the hotel main lobby next to the fountain.')


from django.contrib.auth.models import User

class DashboardViewsTestCase(TestCase):
    def setUp(self):
        # Create site and configurations
        self.nyc = Site.objects.create(
            slug='nyc',
            name='New York City',
            domain='aeroluxeselect-nyc.com',
            is_active=True
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123'
        )

    def test_email_settings_get(self):
        """Dashboard email settings page loads successfully for authenticated admin."""
        client = Client()
        client.login(username='admin', password='password123')
        
        response = client.get(
            reverse('dashboard:email_settings') + '?site=nyc',
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email Server Configuration')

    def test_email_settings_post(self):
        """Dashboard email settings can be updated via POST."""
        client = Client()
        client.login(username='admin', password='password123')
        
        response = client.post(
            reverse('dashboard:email_settings') + '?site=nyc',
            {
                'email_provider': 'SENDGRID',
                'email_from': 'test@yourdomain.com',
                'dispatch_email': 'dispatch@yourdomain.com',
                'email_api_key': 'SG.test_key_123',
                'email_domain': 'yourdomain.com'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify settings updated in DB
        settings_obj = SiteSettings.get_settings(self.nyc)
        self.assertEqual(settings_obj.email_provider, 'SENDGRID')
        self.assertEqual(settings_obj.email_from, 'test@yourdomain.com')
        self.assertEqual(settings_obj.email_api_key, 'SG.test_key_123')

    def test_settings_terms_saving(self):
        """Verify terms and conditions text is saved via the dashboard setting POST."""
        client = Client()
        client.login(username='admin', password='password123')
        
        response = client.post(
            reverse('dashboard:settings') + '?site=nyc',
            {
                'company_name': 'New Luxe NYC',
                'contact_email': 'nyc@aeroluxe.com',
                'contact_phone': '829 509 84 12',
                'whatsapp_number': '18295098412',
                'terms_and_conditions': 'These are the updated terms and conditions.'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 200)
        settings_obj = SiteSettings.get_settings(self.nyc)
        self.assertEqual(settings_obj.terms_and_conditions, 'These are the updated terms and conditions.')

    def test_toggle_vehicle_active_view(self):
        """Verify that toggle_vehicle_active view toggles the is_active attribute."""
        exec_suv = VehicleCategory.objects.create(
            slug='executive-suv-2',
            name='Executive SUV 2',
            is_active=True,
            order=2
        )
        vehicle = Vehicle.objects.create(
            category=exec_suv,
            name='Cadillac Escalade 2026',
            is_active=True
        )
        vehicle.sites.add(self.nyc)
        
        client = Client()
        client.login(username='admin', password='password123')
        
        # Initial status is True
        self.assertTrue(vehicle.is_active)
        
        response = client.get(
            reverse('dashboard:toggle_vehicle_active', kwargs={'pk': vehicle.pk}),
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302) # redirects back to fleet list
        
        vehicle.refresh_from_db()
        self.assertFalse(vehicle.is_active)
        
        # Toggle back to active
        client.get(
            reverse('dashboard:toggle_vehicle_active', kwargs={'pk': vehicle.pk}),
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        vehicle.refresh_from_db()
        self.assertTrue(vehicle.is_active)

    def test_payment_post_validation(self):
        """Verify that payment POST strictly validates card format and method."""
        exec_suv = VehicleCategory.objects.create(
            slug='executive-suv-3',
            name='Executive SUV 3',
            is_active=True,
            order=3
        )
        vehicle = Vehicle.objects.create(
            category=exec_suv,
            name='Escalade',
            is_active=True
        )
        vehicle.sites.add(self.nyc)
        
        jfk = Airport.objects.create(
            site=self.nyc,
            code='JFK',
            name='JFK Airport',
            is_active=True
        )
        midtown = Destination.objects.create(
            airport=jfk,
            name='Midtown',
            is_active=True
        )
        
        client = Client()
        # Set up active booking session data
        session = client.session
        session['booking'] = {
            'service_type': 'airport_transfer',
            'airport_id': jfk.id,
            'destination_id': midtown.id,
            'vehicle_category_id': exec_suv.id,
            'base_price': 100.0,
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'customer_phone': '+12125550199',
            'pickup_date': date.today().strftime('%Y-%m-%d'),
            'pickup_time': '12:00',
        }
        session.save()
        
        # 1. Post with terms missing
        response = client.post(
            reverse('site_nyc:booking_payment'),
            {
                'payment_method': 'STRIPE',
                'cardholder_name': 'John Doe',
                'card_number': '4242424242424242',
                'card_expiry': '12/28',
                'card_cvc': '123'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        # Should redirect back to payment page due to validation failure
        self.assertEqual(response.status_code, 302)
        
        # 2. Post with invalid card format (e.g. 15 digit number)
        response = client.post(
            reverse('site_nyc:booking_payment'),
            {
                'payment_method': 'STRIPE',
                'cardholder_name': 'John Doe',
                'card_number': '424242424242424', # 15 digits
                'card_expiry': '12/28',
                'card_cvc': '123',
                'terms': 'on'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302)
        
        # 3. Post with expired card (e.g. 12/20)
        response = client.post(
            reverse('site_nyc:booking_payment'),
            {
                'payment_method': 'STRIPE',
                'cardholder_name': 'John Doe',
                'card_number': '4242424242424242',
                'card_expiry': '12/20', # expired
                'card_cvc': '123',
                'terms': 'on'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302)

        # 4. Post with valid data (Stripe)
        response = client.post(
            reverse('site_nyc:booking_payment'),
            {
                'payment_method': 'STRIPE',
                'cardholder_name': 'John Doe',
                'card_number': '4242424242424242',
                'card_expiry': '12/30',
                'card_cvc': '123',
                'terms': 'on'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        # Should redirect to success page
        self.assertRedirects(response, reverse('site_nyc:booking_success', kwargs={'reference': Booking.objects.first().booking_reference}))


class LuxuryRentalIntegrationTestCase(TestCase):
    def setUp(self):
        from core.middleware import SiteMiddleware
        SiteMiddleware.clear_cache()
        # Create sites
        self.nyc = Site.objects.create(
            slug='nyc',
            name='New York City',
            domain='aeroluxeselect-nyc.com',
            is_active=True
        )
        self.dr = Site.objects.create(
            slug='dr',
            name='Dominican Republic',
            domain='aeroluxeselect-dr.com',
            is_active=True
        )
        # Create vehicle category
        self.exec_suv = VehicleCategory.objects.create(
            slug='executive-suv',
            name='Executive SUV',
            description='Premium SUV',
            passengers_capacity=6,
            luggage_capacity=6,
            is_active=True,
            order=1
        )
        # Add vehicle to sites
        self.vehicle_nyc = Vehicle.objects.create(
            category=self.exec_suv,
            name='NYC Escalade',
            is_active=True
        )
        self.vehicle_nyc.sites.add(self.nyc)
        
        self.vehicle_dr = Vehicle.objects.create(
            category=self.exec_suv,
            name='DR Escalade',
            is_active=True
        )
        self.vehicle_dr.sites.add(self.dr)

    def test_luxury_rental_presence_on_dr_but_not_nyc(self):
        """Verify luxury rental service is shown on DR index and booking page but not NYC."""
        client = Client()
        
        # DR Index
        response = client.get('/dr/', HTTP_HOST='aeroluxeselect-dr.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luxury Car Rental')
        self.assertContains(response, 'rad-rental')
        
        # NYC Index
        response = client.get('/nyc/', HTTP_HOST='aeroluxeselect-nyc.com')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'rad-rental')
        
        # DR Booking Step 1
        response = client.get('/dr/book/', HTTP_HOST='aeroluxeselect-dr.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'rad-rental')

        # NYC Booking Step 1
        response = client.get('/nyc/book/', HTTP_HOST='aeroluxeselect-nyc.com')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'rad-rental')

    def test_luxury_rental_pricing_and_session(self):
        """Verify luxury rental booking session saving and pricing calculations."""
        from datetime import timedelta
        client = Client()
        
        # 1. Post to DR Booking Step 1 with luxury_rental
        response = client.post(
            reverse('site_dr:booking_step1'),
            {
                'service_type': 'luxury_rental',
                'pickup_address': 'Santo Domingo Airport',
                'dropoff_address': 'Punta Cana Resort',
                'pickup_date': date.today().strftime('%Y-%m-%d'),
                'pickup_time': '14:00',
                'round_trip': 'on',
                'return_date': (date.today() + timedelta(days=2)).strftime('%Y-%m-%d'),
                'return_time': '16:00',
            },
            HTTP_HOST='aeroluxeselect-dr.com'
        )
        # Verify redirect to vehicle selection
        self.assertEqual(response.status_code, 302)
        
        # Verify session stores luxury_rental
        booking_data = client.session.get('booking')
        self.assertEqual(booking_data['service_type'], 'luxury_rental')
        self.assertEqual(booking_data['pickup_address'], 'Santo Domingo Airport')
        self.assertEqual(booking_data['dropoff_address'], 'Punta Cana Resort')
        self.assertTrue(booking_data['round_trip'])
        
        # 2. Get step 2 pricing (default pricing is $150, round trip multiplier is 2.0 -> $300)
        response = client.get(
            reverse('site_dr:booking_step2'),
            HTTP_HOST='aeroluxeselect-dr.com'
        )
        self.assertEqual(response.status_code, 200)
        category_prices = response.context['category_prices']
        # The pricing should be double of default $150 = $300
        self.assertEqual(category_prices[self.exec_suv.id], 300.0)

        # 3. Get api pricing endpoint for luxury_rental
        # Without round_trip
        response = client.get(
            '/dr/api/pricing/?service_type=luxury_rental',
            HTTP_HOST='aeroluxeselect-dr.com'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['pricing'][0]['base_price'], 150.0)

        # With round_trip
        response = client.get(
            '/dr/api/pricing/?service_type=luxury_rental&round_trip=true',
            HTTP_HOST='aeroluxeselect-dr.com'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['pricing'][0]['base_price'], 300.0)


class LanguageAndTranslationTestCase(TestCase):
    def setUp(self):
        # Create sites
        self.nyc = Site.objects.create(
            slug='nyc',
            name='New York City',
            domain='aeroluxeselect-nyc.com',
            is_active=True
        )
        self.dr = Site.objects.create(
            slug='dr',
            name='Dominican Republic',
            domain='aeroluxeselect-dr.com',
            is_active=True
        )
        # Create CMS contents
        SiteContent.objects.create(
            site=self.dr,
            key='hero_title',
            language='en',
            value='Dominican Republic English'
        )
        SiteContent.objects.create(
            site=self.dr,
            key='hero_title',
            language='es',
            value='República Dominicana Español'
        )
        SiteContent.objects.create(
            site=self.nyc,
            key='hero_title',
            language='en',
            value='NYC English Only'
        )
        SiteContent.objects.create(
            site=self.nyc,
            key='hero_title',
            language='es',
            value='NYC Spanish Attempt'
        )

    def test_dr_language_selection(self):
        """Verify DR site defaults to 'en', can switch to 'es', and displays translations."""
        client = Client()
        # Default is English
        response = client.get('/dr/', HTTP_HOST='aeroluxeselect-dr.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['language'], 'en')
        self.assertContains(response, 'Dominican Republic English')

        # Set to Spanish
        response = client.get('/dr/set-language/es/', HTTP_HOST='aeroluxeselect-dr.com', follow=True)
        self.assertEqual(response.status_code, 200)
        # Check language in context
        self.assertEqual(response.context['language'], 'es')
        # Check Spanish content loaded
        self.assertContains(response, 'República Dominicana Español')

    def test_nyc_language_restriction(self):
        """Verify NYC site is strictly English even if session is set to 'es'."""
        client = Client()
        
        # 1. Access default nyc
        response = client.get('/nyc/', HTTP_HOST='aeroluxeselect-nyc.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['language'], 'en')
        self.assertContains(response, 'NYC English Only')

        # 2. Try to set language to 'es' on NYC (should be ignored/stay 'en')
        response = client.get('/nyc/set-language/es/', HTTP_HOST='aeroluxeselect-nyc.com', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['language'], 'en')
        self.assertContains(response, 'NYC English Only')

        # 3. Simulate session having 'es' from DR site visit
        session = client.session
        session['language'] = 'es'
        session.save()
        
        # Access NYC now - should ignore session language 'es' and load 'en'
        response = client.get('/nyc/', HTTP_HOST='aeroluxeselect-nyc.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['language'], 'en')
        self.assertContains(response, 'NYC English Only')
        self.assertNotContains(response, 'NYC Spanish Attempt')

    def test_pwa_service_worker(self):
        """Verify the service worker is served with the correct content type."""
        client = Client()
        response = client.get('/nyc/sw.js', HTTP_HOST='aeroluxeselect-nyc.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertContains(response, 'CACHE_NAME')


class RoundTripSplitTestCase(TestCase):
    def setUp(self):
        self.nyc = Site.objects.create(
            slug='nyc',
            name='New York City',
            domain='aeroluxeselect-nyc.com',
            is_active=True
        )
        self.jfk = Airport.objects.create(
            site=self.nyc,
            code='JFK',
            name='JFK Airport',
            is_active=True
        )
        self.midtown = Destination.objects.create(
            airport=self.jfk,
            name='Midtown',
            is_active=True
        )
        self.exec_suv = VehicleCategory.objects.create(
            slug='executive-suv',
            name='Executive SUV',
            is_active=True,
            order=1
        )
        self.meet_greet = PremiumAddOn.objects.create(
            name='Meet & Greet',
            slug='meet-greet',
            price=Decimal('25.00'),
            is_active=True
        )

    def test_round_trip_split_on_payment(self):
        """A round-trip booking should split into two separate records during checkout."""
        client = Client()
        session = client.session
        session['booking'] = {
            'service_type': 'airport_transfer',
            'airport_id': self.jfk.id,
            'destination_id': self.midtown.id,
            'vehicle_category_id': self.exec_suv.id,
            'base_price': 100.0,
            'customer_name': 'Alice Smith',
            'customer_email': 'alice@example.com',
            'customer_phone': '+12125550199',
            'pickup_date': '2026-06-12',
            'pickup_time': '12:00',
            'passenger_count': 4,
            'pickup_address': 'JFK Airport Terminal 4',
            'destination_address': 'Times Square Hotel',
            'transfer_direction': 'AIRPORT_TO_DEST',
            'round_trip': True,
            'return_date': '2026-06-15',
            'return_time': '15:00',
            'selected_addons': [self.meet_greet.id],
        }
        session.save()

        # Submit valid payment to trigger creation of both legs
        response = client.post(
            reverse('site_nyc:booking_payment'),
            {
                'payment_method': 'CASH',
                'terms': 'on'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302)

        # Check that we have exactly 2 bookings in the database
        bookings = Booking.objects.all().order_by('id')
        self.assertEqual(bookings.count(), 2)

        outbound = bookings[0]
        inbound = bookings[1]

        # Verify outbound booking
        self.assertEqual(outbound.customer_name, 'Alice Smith')
        self.assertEqual(outbound.passenger_count, 4)
        self.assertEqual(outbound.round_trip, True)
        self.assertEqual(outbound.pickup_address, 'JFK Airport Terminal 4')
        self.assertEqual(outbound.dropoff_address, 'Times Square Hotel')
        self.assertEqual(outbound.transfer_direction, 'AIRPORT_TO_DEST')
        self.assertEqual(outbound.base_price, Decimal('100.00'))
        self.assertEqual(outbound.addons_total, Decimal('25.00'))
        self.assertEqual(outbound.total_price, Decimal('225.00')) # (100 * 2) + 25

        # Verify inbound/return booking
        self.assertEqual(inbound.customer_name, 'Alice Smith')
        self.assertEqual(inbound.passenger_count, 4)
        self.assertEqual(inbound.round_trip, False)
        # Swapped addresses
        self.assertEqual(inbound.pickup_address, 'Times Square Hotel')
        self.assertEqual(inbound.dropoff_address, 'JFK Airport Terminal 4')
        self.assertEqual(inbound.transfer_direction, 'DEST_TO_AIRPORT')
        # Free fare
        self.assertEqual(inbound.base_price, Decimal('0.00'))
        self.assertEqual(inbound.total_price, Decimal('0.00'))
        self.assertEqual(inbound.linked_booking, outbound)

        # Add-ons should be copied
        self.assertIn(self.meet_greet, inbound.addons.all())





