import os
import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from decimal import Decimal
from core.models import SiteSettings, ServiceType

def send_booking_emails(booking):
    """
    Sends two confirmation emails upon booking validation:
    1. One to the Customer (customer_email).
    2. One to the Dispatch team (dispatch_email).
    """
    site = booking.site
    settings_obj = SiteSettings.get_settings(site)
    
    # Recipient addresses
    customer_to = booking.customer_email
    dispatch_to = settings_obj.dispatch_email or 'dispatch@aeroluxeselect.com'
    
    # Sender address
    from_email = settings_obj.email_from or 'no-reply@aeroluxeselect.com'
    
    # ── EMAIL HTML CONTENTS ──
    # HTML template common parts
    title_text = f"Booking Confirmation — {booking.booking_reference}"
    
    # Round-trip details string
    rt_html = ""
    if booking.round_trip:
        rt_html = f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Return Leg</td>
            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.return_date} at {booking.return_time}</td>
        </tr>
        """
        
    # Stops details string
    stops_html = ""
    if booking.number_of_stops > 0:
        stops_html = f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Intermediate Stops</td>
            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.number_of_stops} Stop(s)<br/><small style="color: #888;">{booking.stop_addresses}</small></td>
        </tr>
        """
        
    # Service specific coordinates
    coords_html = ""
    if booking.service_type == ServiceType.AIRPORT_TRANSFER:
        direction = getattr(booking, 'transfer_direction', 'AIRPORT_TO_DEST')
        if direction == 'DEST_TO_AIRPORT':
            coords_html = f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Pickup Location (Hotel/Address)</td>
                <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.destination.name if booking.destination else 'N/A'}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Destination Airport</td>
                <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.airport.name if booking.airport else 'N/A'}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Flight Number</td>
                <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.flight_number or 'N/A'}</td>
            </tr>
            """
        else:
            coords_html = f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Origin Airport</td>
                <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.airport.name if booking.airport else 'N/A'}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Destination (Hotel/Address)</td>
                <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.destination.name if booking.destination else 'N/A'}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Flight Number</td>
                <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.flight_number or 'N/A'}</td>
            </tr>
            """
    elif booking.service_type == ServiceType.HOURLY:
        coords_html = f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Pick up Location</td>
            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.pickup_address}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Hours Requested</td>
            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.hours_requested} Hour(s) (Max 12)</td>
        </tr>
        """
    elif booking.service_type == ServiceType.POINT_TO_POINT:
        coords_html = f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Pick up Location</td>
            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.pickup_address}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Drop-off Location</td>
            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.dropoff_address}</td>
        </tr>
        """

    # Common HTML wrapper
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title_text}</title>
    </head>
    <body style="background-color: #0A0A0A; color: #FFFFFF; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 20px; margin: 0;">
        <div style="max-w: 600px; margin: 0 auto; background-color: #111; border: 1px solid #222; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
            <!-- Header -->
            <div style="background-color: #0D0D0D; padding: 30px; text-align: center; border-bottom: 1px solid #C9A84C;">
                <h1 style="color: #C9A84C; font-size: 24px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin: 0;">AEROLUX SELECT</h1>
                <p style="color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 5px 0 0 0;">Chauffeur Service Confirmation</p>
            </div>
            
            <!-- Body -->
            <div style="padding: 30px;">
                <h2 style="color: #fff; font-size: 18px; margin-top: 0; margin-bottom: 20px; font-weight: 600; text-align: center;">CONFIRMATION DETAILS</h2>
                
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                    <tbody>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C; width: 35%;">Booking Ref</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #fff;">{booking.booking_reference}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Service Type</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; text-transform: capitalize; color: #fff;">{booking.get_service_type_display()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Customer Name</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.customer_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Customer Email</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.customer_email}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Customer Phone</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.customer_phone}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Pickup Date/Time</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.pickup_date} at {booking.pickup_time}</td>
                        </tr>
                        {coords_html}
                        {rt_html}
                        {stops_html}
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Vehicle Class</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.vehicle_category.name if booking.vehicle_category else 'Luxury Class'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Payment Method</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.get_payment_method_display()} ({booking.get_payment_status_display()})</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Meeting Point</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.meeting_point or 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #222; font-weight: bold; color: #C9A84C;">Special Requests</td>
                            <td style="padding: 10px; border-bottom: 1px solid #222; color: #fff;">{booking.customer_notes or 'None'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; font-weight: bold; color: #C9A84C; font-size: 16px;">Total Price</td>
                            <td style="padding: 10px; font-weight: bold; color: #C9A84C; font-size: 16px;">${booking.total_price:.2f} USD</td>
                        </tr>
                    </tbody>
                </table>
                
                <div style="margin-top: 30px; text-align: center; font-size: 12px; color: #888; border-top: 1px solid #222; padding-top: 20px;">
                    <p style="margin: 0 0 10px 0;">This is an automated operational alert regarding the reservation #{booking.booking_reference}.</p>
                    <p style="margin: 0;">&copy; {booking.site.name} — Chauffeur Service Platform</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # ── DISPATCH & CUSTOMER SPECIFIC SUBJECTS ──
    subject_dispatch = f"[DISPATCH ALERT] New Booking Confirmation: {booking.booking_reference}"
    subject_customer = f"Your AeroLux Select Booking Confirmation: {booking.booking_reference}"
    
    # Plain text alternative
    text_content = f"""
    AEROLUX SELECT - BOOKING CONFIRMATION
    --------------------------------------
    Booking Reference: {booking.booking_reference}
    Service Type: {booking.get_service_type_display()}
    Customer: {booking.customer_name} ({booking.customer_email} / {booking.customer_phone})
    Pickup Date/Time: {booking.pickup_date} at {booking.pickup_time}
    Meeting Point: {booking.meeting_point or 'N/A'}
    Vehicle Class: {booking.vehicle_category.name if booking.vehicle_category else 'Luxury Class'}
    Payment: {booking.get_payment_method_display()} ({booking.get_payment_status_display()})
    Total Fare: ${booking.total_price:.2f} USD
    """
    
    # Helper to send email to one recipient
    def _send_email_to(to_email, subject):
        provider = settings_obj.email_provider.upper()
        
        # 1. SMTP Provider
        if provider == 'SMTP':
            if settings_obj.email_host:
                backend = EmailBackend(
                    host=settings_obj.email_host,
                    port=settings_obj.email_port,
                    username=settings_obj.email_username,
                    password=settings_obj.email_password,
                    use_tls=settings_obj.email_use_tls,
                )
            else:
                backend = None  # Fallback to Django settings configuration
                
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[to_email]
            )
            email.attach_alternative(html_template, "text/html")
            if backend:
                email.connection = backend
            email.send()
            
        # 2. SendGrid Provider
        elif provider == 'SENDGRID':
            api_key = settings_obj.email_api_key
            if not api_key:
                raise ValueError("SendGrid API key not configured in SiteSettings")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_email, "name": "AeroLux Select"},
                "subject": subject,
                "content": [
                    {"type": "text/plain", "value": text_content},
                    {"type": "text/html", "value": html_template}
                ]
            }
            response = requests.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
        # 3. Resend Provider
        elif provider == 'RESEND':
            api_key = settings_obj.email_api_key
            if not api_key:
                raise ValueError("Resend API key not configured in SiteSettings")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": f"AeroLux Select <{from_email}>",
                "to": [to_email],
                "subject": subject,
                "text": text_content,
                "html": html_template
            }
            response = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
        # 4. Mailgun Provider
        elif provider == 'MAILGUN':
            api_key = settings_obj.email_api_key
            domain = settings_obj.email_domain
            if not api_key or not domain:
                raise ValueError("Mailgun API key or Domain not configured in SiteSettings")
            
            auth = ("api", api_key)
            payload = {
                "from": f"AeroLux Select <{from_email}>",
                "to": to_email,
                "subject": subject,
                "text": text_content,
                "html": html_template
            }
            response = requests.post(
                f"https://api.mailgun.net/v3/{domain}/messages",
                auth=auth,
                data=payload,
                timeout=10
            )
            response.raise_for_status()

        # 5. Brevo Provider
        elif provider == 'BREVO':
            api_key = settings_obj.email_api_key
            if not api_key:
                raise ValueError("Brevo API key not configured in SiteSettings")
            
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "sender": {"email": from_email, "name": "AeroLux Select"},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_template,
                "textContent": text_content
            }
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
        else:
            raise ValueError(f"Unknown email provider: {provider}")

    # Send Dispatch Alert
    try:
        _send_email_to(dispatch_to, subject_dispatch)
    except Exception as e:
        print(f"Error sending dispatch email: {str(e)}")
        
    # Send Customer Confirmation
    try:
        _send_email_to(customer_to, subject_customer)
    except Exception as e:
        print(f"Error sending customer confirmation email: {str(e)}")
