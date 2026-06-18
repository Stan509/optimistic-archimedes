from django.test import TestCase, Client
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from decimal import Decimal
from datetime import date, time
import datetime
from django.utils import timezone
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
        # With the new design, round-trip doubling on a single booking record is disabled.
        # Doubling is handled by creating two separate bookings.
        # Thus, a single leg fare is base_price (80) + (2 * 20) = 120
        self.assertEqual(total, Decimal('120.00'))


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
        """A round-trip booking should be stored as a single booking record in the database."""
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
            'selected_addons_return': [self.meet_greet.id],
            'pay_separately': True,
        }
        session.save()

        # Submit valid payment to trigger creation of the booking
        response = client.post(
            reverse('site_nyc:booking_payment'),
            {
                'payment_method': 'CASH',
                'terms': 'on'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302)

        # Check that we have exactly 2 bookings in the database (split round trip)
        bookings = Booking.objects.all().order_by('id')
        self.assertEqual(bookings.count(), 2)

        booking_outbound = bookings[0]
        booking_return = bookings[1]

        # Verify linked bookings
        self.assertEqual(booking_outbound.linked_booking, booking_return)
        self.assertEqual(booking_return.linked_booking, booking_outbound)

        # Verify outbound leg details
        self.assertEqual(booking_outbound.customer_name, 'Alice Smith')
        self.assertEqual(booking_outbound.passenger_count, 4)
        self.assertEqual(booking_outbound.round_trip, True)
        self.assertEqual(booking_outbound.pickup_address, 'JFK Airport Terminal 4')
        self.assertEqual(booking_outbound.dropoff_address, 'Times Square Hotel')
        self.assertEqual(booking_outbound.transfer_direction, 'AIRPORT_TO_DEST')
        self.assertEqual(booking_outbound.base_price, Decimal('100.00'))
        self.assertEqual(booking_outbound.addons_total, Decimal('25.00'))  # only outbound addon
        self.assertEqual(booking_outbound.total_price, Decimal('125.00'))  # 100 + 25
        self.assertTrue(booking_outbound.pay_separately)
        self.assertEqual(booking_outbound.return_date.strftime('%Y-%m-%d'), '2026-06-15')
        self.assertEqual(booking_outbound.return_time.strftime('%H:%M'), '15:00')
        self.assertIn(self.meet_greet, booking_outbound.addons.all())

        # Verify return leg details
        self.assertEqual(booking_return.customer_name, 'Alice Smith')
        self.assertEqual(booking_return.passenger_count, 4)
        self.assertEqual(booking_return.round_trip, True)
        self.assertEqual(booking_return.pickup_address, 'Times Square Hotel')
        self.assertEqual(booking_return.dropoff_address, 'JFK Airport Terminal 4')
        self.assertEqual(booking_return.transfer_direction, 'DEST_TO_AIRPORT')
        self.assertEqual(booking_return.base_price, Decimal('100.00'))
        self.assertEqual(booking_return.addons_total, Decimal('25.00'))  # only return addon
        self.assertEqual(booking_return.total_price, Decimal('125.00'))  # 100 + 25
        self.assertIn(self.meet_greet, booking_return.addons.all())


class ManualPaymentsAndRemindersTestCase(TestCase):
    def setUp(self):
        import datetime
        self.nyc = Site.objects.create(
            slug='nyc',
            name='New York City',
            domain='aeroluxeselect-nyc.com',
            is_active=True
        )
        self.site_settings = SiteSettings.objects.create(
            site=self.nyc,
            company_name='AeroLux Select',
            email_provider='SMTP',
            email_from='test@aeroluxeselect.com',
            dispatch_email='dispatch@aeroluxeselect.com'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        self.jfk = Airport.objects.create(
            site=self.nyc,
            code='JFK',
            name='JFK Airport',
            is_active=True
        )
        self.exec_suv = VehicleCategory.objects.create(
            slug='executive-suv',
            name='Executive SUV',
            is_active=True,
            order=1
        )
        self.booking = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Bob Jones',
            customer_email='bob@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            payment_status='pending',
            status='confirmed',
            reminder_sent=False
        )

    def test_record_payment_ledger(self):
        """Test recording a manual cash payment through the dashboard."""
        client = Client()
        client.login(username='admin', password='password123')

        # 1. Post a partial payment
        response = client.post(
            reverse('dashboard:record_payment', kwargs={'booking_id': self.booking.id}),
            {
                'amount': '40.00',
                'payment_method': 'CASH',
                'notes': 'Partial cash payment'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302)
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.amount_paid, Decimal('40.00'))
        self.assertEqual(self.booking.payment_status, 'partially_paid')
        self.assertEqual(self.booking.payments.count(), 1)
        self.assertEqual(self.booking.payments.first().amount, Decimal('40.00'))

        # 2. Post the remaining payment
        response = client.post(
            reverse('dashboard:record_payment', kwargs={'booking_id': self.booking.id}),
            {
                'amount': '60.00',
                'payment_method': 'CASH',
                'notes': 'Final cash payment'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.amount_paid, Decimal('100.00'))
        self.assertEqual(self.booking.payment_status, 'paid')
        self.assertEqual(self.booking.payments.count(), 2)

    def test_send_reminders_command(self):
        """Test that send_reminders command runs and marks bookings correctly."""
        from django.core.management import call_command
        from django.utils import timezone
        import datetime
        
        # 1. Create a booking that is 14 hours away - should NOT get reminded
        booking_far = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Far Passenger',
            customer_email='far@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            pickup_date=(timezone.now() + datetime.timedelta(hours=14)).date(),
            pickup_time=(timezone.now() + datetime.timedelta(hours=14)).time(),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            status='confirmed',
            reminder_sent=False
        )

        # 2. Create a booking that is 8 hours away - should get reminded
        booking_near = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Near Passenger',
            customer_email='near@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            pickup_date=(timezone.now() + datetime.timedelta(hours=8)).date(),
            pickup_time=(timezone.now() + datetime.timedelta(hours=8)).time(),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            status='confirmed',
            reminder_sent=False
        )

        # 3. Call the management command
        call_command('send_reminders')

        # 4. Assert statuses
        booking_far.refresh_from_db()
        booking_near.refresh_from_db()

        self.assertFalse(booking_far.reminder_sent)
        self.assertTrue(booking_near.reminder_sent)

    def test_whatsapp_template_editor_view(self):
        """Verify dashboard:email_template_editor works for WhatsApp tab."""
        client = Client()
        client.login(username='admin', password='password123')
        
        # 1. GET request for whatsapp tab
        response = client.get(
            reverse('dashboard:email_template_editor') + '?site=nyc&type=confirmed&tab=whatsapp',
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WhatsApp Message')
        
        # 2. POST request to save whatsapp template
        from core.models import WhatsAppTemplate
        # Delete any seeded template to verify creation
        WhatsAppTemplate.objects.filter(site=self.nyc, trigger_type='confirmed').delete()
        
        response = client.post(
            reverse('dashboard:email_template_editor') + '?site=nyc&type=confirmed&tab=whatsapp',
            {
                'whatsapp_message': 'Custom confirm template: {customer_name}'
            },
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check database
        tpl = WhatsAppTemplate.objects.filter(site=self.nyc, trigger_type='confirmed').first()
        self.assertIsNotNone(tpl)
        self.assertEqual(tpl.message_content, 'Custom confirm template: {customer_name}')

    def test_get_formatted_whatsapp_message(self):
        """Test the get_formatted_whatsapp_message function formats placeholders."""
        from core.emails import get_formatted_whatsapp_message
        
        # Call formatting with self.booking
        formatted = get_formatted_whatsapp_message(self.booking, 'confirmed')
        self.assertIn('Bob Jones', formatted)
        self.assertIn('JFK Airport', formatted)
        self.assertIn('$100.00', formatted)

    def test_booking_detail_whatsapp_links(self):
        """Verify that booking_detail page generates the correct whatsapp links in context."""
        client = Client()
        client.login(username='admin', password='password123')
        
        response = client.get(
            reverse('dashboard:booking_detail', kwargs={'booking_id': self.booking.id}),
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('whatsapp_links', response.context)
        links = response.context['whatsapp_links']
        self.assertIn('processing', links)
        self.assertIn('confirmed', links)
        self.assertTrue(links['confirmed'].startswith('https://wa.me/12125550199'))


class ChauffeurSystemRefinementTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.nyc = Site.objects.create(
            slug='nyc',
            name='New York City',
            domain='aeroluxeselect-nyc.com',
            is_active=True
        )
        self.jfk = Airport.objects.create(
            site=self.nyc,
            code='JFK',
            name='John F. Kennedy International Airport',
            is_active=True
        )
        self.midtown = Destination.objects.create(
            airport=self.jfk,
            name='Manhattan — Midtown',
            is_active=True
        )
        self.exec_suv = VehicleCategory.objects.create(
            slug='executive-suv',
            name='Executive SUV',
            is_active=True,
            order=1
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123'
        )

    def test_return_meeting_point_saving(self):
        """Test that return_meeting_point is successfully saved to the Booking model."""
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
            round_trip=True,
            return_date=date.today(),
            return_time=time(18, 0),
            meeting_point='At terminal 4 arrival lobby',
            return_meeting_point='In hotel lobby under the clock',
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            booking_source='DIRECT'
        )
        self.assertEqual(booking.return_meeting_point, 'In hotel lobby under the clock')

    def test_is_return_alert_active(self):
        """Test is_return_alert_active returns True only when within 12h of return leg and status is active."""
        # 1. More than 12 hours away
        future_return = date.today() + datetime.timedelta(days=2)
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
            round_trip=True,
            return_date=future_return,
            return_time=time(18, 0),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            status='CONFIRMED'
        )
        self.assertFalse(booking.is_return_alert_active)

        # 2. Within 12 hours away, status CONFIRMED
        booking.return_date = date.today()
        # Set return time to 3 hours from now
        now_dt = timezone.localtime(timezone.now())
        alert_time = (now_dt + datetime.timedelta(hours=3))
        booking.return_date = alert_time.date()
        booking.return_time = alert_time.time()
        booking.save()
        self.assertTrue(booking.is_return_alert_active)

        # 3. Within 12 hours away, status CANCELLED (should be False)
        booking.status = 'CANCELLED'
        booking.save()
        self.assertFalse(booking.is_return_alert_active)

    def test_status_update_date_restrictions(self):
        """Test that update_booking_status view blocks future status transitions."""
        client = Client()
        client.login(username='admin', password='password123')

        future_date = date.today() + datetime.timedelta(days=2)
        booking = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Future Guest',
            customer_email='future@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            destination=self.midtown,
            pickup_date=future_date,
            pickup_time=time(12, 0),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            status='CONFIRMED'
        )

        # Attempt to set IN_PROGRESS (should fail and redirect with error)
        response = client.get(
            reverse('dashboard:update_booking_status', kwargs={'booking_id': booking.id, 'new_status': 'IN_PROGRESS'}),
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CONFIRMED')

        # Create a booking with today's pickup but future return
        booking2 = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Today Guest',
            customer_email='today@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            destination=self.midtown,
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            round_trip=True,
            return_date=future_date,
            return_time=time(12, 0),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            status='IN_PROGRESS'
        )

        # Attempt to set COMPLETED (should fail due to future return date)
        response2 = client.get(
            reverse('dashboard:update_booking_status', kwargs={'booking_id': booking2.id, 'new_status': 'COMPLETED'}),
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response2.status_code, 302)
        booking2.refresh_from_db()
        self.assertEqual(booking2.status, 'IN_PROGRESS')

    def test_linked_bookings_status_synchronization(self):
        """Test status synchronization automatically confirms or cancels linked legs."""
        client = Client()
        client.login(username='admin', password='password123')

        outbound = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Linked Legs',
            customer_email='linked@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            destination=self.midtown,
            pickup_date=date.today(),
            pickup_time=time(12, 0),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            status='PENDING'
        )
        return_leg = Booking.objects.create(
            site=self.nyc,
            service_type='airport_transfer',
            customer_name='Linked Legs',
            customer_email='linked@example.com',
            customer_phone='+12125550199',
            airport=self.jfk,
            destination=self.midtown,
            pickup_date=date.today(),
            pickup_time=time(18, 0),
            vehicle_category=self.exec_suv,
            base_price=Decimal('100.00'),
            status='PENDING',
            linked_booking=outbound
        )
        outbound.return_bookings.add(return_leg)

        # Confirm outbound via view
        response = client.get(
            reverse('dashboard:update_booking_status', kwargs={'booking_id': outbound.id, 'new_status': 'CONFIRMED'}),
            HTTP_HOST='aeroluxeselect-nyc.com'
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify both are now CONFIRMED
        outbound.refresh_from_db()
        return_leg.refresh_from_db()
        self.assertEqual(outbound.status, 'CONFIRMED')
        self.assertEqual(return_leg.status, 'CONFIRMED')


from unittest.mock import patch, MagicMock
import json

class DistanceCalculationAndStorageTestCase(TestCase):
    def setUp(self):
        from core.models import Site, Airport, Destination, VehicleCategory
        self.nyc = Site.objects.create(name='New York City', slug='nyc', domain='aeroluxeselect-nyc.com')
        self.jfk = Airport.objects.create(site=self.nyc, code='JFK', name='JFK Airport', city='New York', latitude=40.6413, longitude=-73.7781)
        self.midtown = Destination.objects.create(airport=self.jfk, name='Midtown', address='Manhattan, NY', latitude=40.7549, longitude=-73.9840)
        self.exec_suv = VehicleCategory.objects.create(slug='executive-suv', name='Executive SUV', is_active=True, order=1)

    @patch('urllib.request.urlopen')
    def test_google_directions_distance_calculation(self, mock_urlopen):
        # Mock Google Directions API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'status': 'OK',
            'routes': [{
                'legs': [{
                    'distance': {'value': 28500}  # 28.5 km
                }]
            }]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        from core.views import _get_google_driving_distance
        dist = _get_google_driving_distance(40.6413, -73.7781, 40.7549, -73.9840, 'mock_key')
        self.assertEqual(dist, 28.5)

    def test_booking_page_uses_single_real_maps_loader(self):
        settings_obj = SiteSettings.get_settings(self.nyc)
        settings_obj.google_maps_api_key = 'AIzaTestKey'
        settings_obj.save()

        response = self.client.get('/nyc/book/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn('https://maps.googleapis.com/maps/api/js?key=AIzaTestKey', html)
        self.assertNotIn('AIzaSyDummyKey', html)
        self.assertNotIn('core/js/booking-maps.js', html)

    @override_settings(
        GOOGLE_MAPS_API_KEY='fallback_maps_key',
        GOOGLE_MAPS_API_KEYS={'nyc': 'fallback_maps_key', 'dr': 'fallback_maps_key'},
    )
    def test_booking_page_and_api_use_settings_maps_key_fallback(self):
        settings_obj = SiteSettings.get_settings(self.nyc)
        settings_obj.google_maps_api_key = ''
        settings_obj.save()

        response = self.client.get('/nyc/book/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'https://maps.googleapis.com/maps/api/js?key=fallback_maps_key',
            response.content.decode(),
        )

        api_response = self.client.get('/nyc/api/google-maps-key/')
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(api_response.json()['api_key'], 'fallback_maps_key')

    @patch('urllib.request.urlopen')
    def test_address_autocomplete_api_returns_predictions(self, mock_urlopen):
        settings_obj = SiteSettings.get_settings(self.nyc)
        settings_obj.google_maps_api_key = 'mock_key'
        settings_obj.save()

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'status': 'OK',
            'predictions': [{
                'place_id': 'place_123',
                'description': 'The Plaza Hotel, 5th Avenue, New York, NY',
                'structured_formatting': {
                    'main_text': 'The Plaza Hotel',
                    'secondary_text': '5th Avenue, New York, NY',
                },
            }]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.get('/nyc/api/address-autocomplete/?input=Plaza')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['predictions'][0]['place_id'], 'place_123')
        self.assertEqual(data['predictions'][0]['description'], 'The Plaza Hotel, 5th Avenue, New York, NY')

    @patch('urllib.request.urlopen')
    def test_place_details_api_returns_coordinates(self, mock_urlopen):
        settings_obj = SiteSettings.get_settings(self.nyc)
        settings_obj.google_maps_api_key = 'mock_key'
        settings_obj.save()

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'status': 'OK',
            'result': {
                'formatted_address': 'The Plaza Hotel, New York, NY',
                'geometry': {
                    'location': {'lat': 40.7645, 'lng': -73.9743}
                },
            }
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.get('/nyc/api/place-details/?place_id=place_123')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['latitude'], 40.7645)
        self.assertEqual(data['longitude'], -73.9743)

    @patch('urllib.request.urlopen')
    def test_airport_transfer_pricing_fetches_google_distance(self, mock_urlopen):
        # Mock Google Directions API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'status': 'OK',
            'routes': [{
                'legs': [{
                    'distance': {'value': 30000}  # 30.0 km
                }]
            }]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Set google maps key
        from core.models import SiteSettings
        settings = SiteSettings.get_settings(self.nyc)
        settings.google_maps_api_key = 'mock_key'
        settings.save()

        from core.views import _get_airport_transfer_price_for_category
        booking_data = {
            'airport_id': self.jfk.id,
            'pickup_lat': 40.6413,
            'pickup_lng': -73.7781,
            'dropoff_lat': 40.7549,
            'dropoff_lng': -73.9840,
            'transfer_direction': 'AIRPORT_TO_DEST',
            'distance_km': '' # trigger fallback
        }

        # Call price function
        price = _get_airport_transfer_price_for_category(self.nyc, 'nyc', self.exec_suv, booking_data)
        
        # Verify distance was written to booking_data and used
        self.assertEqual(booking_data['distance_km'], '30.0')

    def test_booking_saves_distance_km_in_db(self):
        # Create a booking with distance_km explicitly passed
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
            base_price=Decimal('100.00'),
            distance_km=Decimal('28.50'),
            booking_source='DIRECT'
        )
        self.assertEqual(booking.distance_km, Decimal('28.50'))








