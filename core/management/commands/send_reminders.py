import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Booking
from core.emails import send_booking_email

class Command(BaseCommand):
    help = 'Sends 12-hour reminder emails to customers with confirmed bookings.'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Get all confirmed bookings where a reminder has not been sent yet
        bookings = Booking.objects.filter(
            status='confirmed',
            reminder_sent=False
        )
        
        sent_count = 0
        for booking in bookings:
            # Combine pickup date and time
            pickup_dt = datetime.datetime.combine(booking.pickup_date, booking.pickup_time)
            
            # Make timezone aware if settings.USE_TZ is True
            if timezone.is_aware(now):
                pickup_dt = timezone.make_aware(pickup_dt)
                
            diff = pickup_dt - now
            
            # Send reminder if pickup is in the future and within 12 hours
            if datetime.timedelta(hours=0) <= diff <= datetime.timedelta(hours=12):
                try:
                    self.stdout.write(f"Sending 12h reminder for booking {booking.booking_reference}...")
                    send_booking_email(booking, 'reminder_12h')
                    booking.reminder_sent = True
                    booking.save(update_fields=['reminder_sent'])
                    sent_count += 1
                except Exception as e:
                    self.stderr.write(f"Error sending email for {booking.booking_reference}: {str(e)}")
                    
        self.stdout.write(self.style.SUCCESS(f"Successfully sent {sent_count} reminder email(s)."))
