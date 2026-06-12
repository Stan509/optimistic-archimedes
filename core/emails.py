import os
import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from decimal import Decimal
from core.models import SiteSettings, ServiceType, EmailTemplate

def get_email_context(booking):
    """Generates standard context variables for email templates."""
    base_price = booking.base_price
    stops_fee = Decimal('0.00')
    if booking.service_type == 'point_to_point':
        stops_fee = Decimal('20.00') * Decimal(booking.number_of_stops)
        
    outbound_addons_total = sum(addon.price for addon in booking.addons.all()) if booking.pk else Decimal('0.00')
    return_addons_total = sum(addon.price for addon in booking.addons_return.all()) if booking.pk else Decimal('0.00')
    
    outbound_total = base_price + stops_fee + outbound_addons_total
    return_total = base_price + return_addons_total if booking.round_trip else Decimal('0.00')
    
    balance = booking.total_price - booking.amount_paid
    
    return {
        'customer_name': booking.customer_name,
        'booking_reference': booking.booking_reference,
        'pickup_date': str(booking.pickup_date),
        'pickup_time': str(booking.pickup_time),
        'return_date': str(booking.return_date) if booking.return_date else 'N/A',
        'return_time': str(booking.return_time) if booking.return_time else 'N/A',
        'total_price': f"${booking.total_price:.2f}",
        'amount_paid': f"${booking.amount_paid:.2f}",
        'balance': f"${balance:.2f}",
        'outbound_total': f"${outbound_total:.2f}",
        'return_total': f"${return_total:.2f}",
        'pickup_address': booking.pickup_address or (booking.airport.name if booking.airport else 'N/A'),
        'dropoff_address': booking.dropoff_address or (booking.destination.name if booking.destination else 'N/A'),
        'service_type': booking.get_service_type_display(),
        'flight_number': booking.flight_number or 'N/A',
    }

def format_template(text, context):
    """Replaces placeholders in format {variable_name} with context values."""
    if not text:
        return ""
    for k, v in context.items():
        text = text.replace(f'{{{k}}}', str(v))
    return text

def get_default_email_template(email_type, company_name="AeroLux Select"):
    """Returns default professional HTML and plain text skeletons for emails."""
    
    if email_type == 'processing':
        subject = f"Reservation Received & Processing — {company_name}"
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reservation Received</title>
</head>
<body style="background-color: #0A0A0A; color: #FFFFFF; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 20px; margin: 0;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #111; border: 1px solid #222; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
        <div style="background-color: #0D0D0D; padding: 30px; text-align: center; border-bottom: 1px solid #C9A84C;">
            <h1 style="color: #C9A84C; font-size: 24px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin: 0;">AEROLUX SELECT</h1>
            <p style="color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin: 5px 0 0 0;">Under Review / En cours de traitement</p>
        </div>
        <div style="padding: 30px;">
            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">Dear {customer_name},</p>
            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">We have received your chauffeur booking request. Your reservation reference is <strong>{booking_reference}</strong>. Our dispatch command desk is currently reviewing the itinerary and vehicle availability.</p>
            
            <div style="background-color: #1a1a1a; padding: 20px; border-radius: 8px; margin: 25px 0; border: 1px solid #333;">
                <h3 style="color: #C9A84C; margin-top: 0; font-size: 14px; uppercase; letter-spacing: 1px;">Itinerary Summary</h3>
                <table style="width: 100%; font-size: 13px; color: #ccc; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; color: #888; width: 35%;">Service Type:</td>
                        <td style="padding: 6px 0; color: #fff;">{service_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Pickup Date/Time:</td>
                        <td style="padding: 6px 0; color: #fff;">{pickup_date} at {pickup_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Pickup Address:</td>
                        <td style="padding: 6px 0; color: #fff;">{pickup_address}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Drop-off Address:</td>
                        <td style="padding: 6px 0; color: #fff;">{dropoff_address}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Flight Number:</td>
                        <td style="padding: 6px 0; color: #fff;">{flight_number}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Outbound Fare:</td>
                        <td style="padding: 6px 0; color: #fff;">{outbound_total}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Return Fare:</td>
                        <td style="padding: 6px 0; color: #fff;">{return_total}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888; font-weight: bold; border-top: 1px solid #333;">Grand Total:</td>
                        <td style="padding: 6px 0; color: #C9A84C; font-weight: bold; border-top: 1px solid #333;">{total_price}</td>
                    </tr>
                </table>
            </div>

            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">A confirmation email will be sent once our dispatch team validates your trip. If you have chosen to pay cash on delivery, please have the correct amount ready for your chauffeur.</p>
            <p style="font-size: 14px; line-height: 1.6; color: #ccc; margin-bottom: 0;">Kind regards,<br>AeroLux Select Command Desk</p>
        </div>
        <div style="background-color: #0D0D0D; padding: 20px; text-align: center; font-size: 11px; color: #666; border-top: 1px solid #222;">
            &copy; AeroLux Select &bull; Luxury Chauffeur Logistics
        </div>
    </div>
</body>
</html>"""
        text_content = """Dear {customer_name},

We have received your reservation request {booking_reference} and it is currently being processed.

Itinerary Summary:
Service: {service_type}
Pickup: {pickup_date} at {pickup_time}
From: {pickup_address}
To: {dropoff_address}
Flight: {flight_number}
Outbound total: {outbound_total}
Return total: {return_total}
Grand total: {total_price}

We will send another confirmation email once validated.

Best regards,
AeroLux Select Desk"""

    elif email_type == 'confirmed':
        subject = f"Reservation Confirmed & Secured — {company_name} [{{booking_reference}}]"
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reservation Confirmed</title>
</head>
<body style="background-color: #0A0A0A; color: #FFFFFF; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 20px; margin: 0;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #111; border: 1px solid #222; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
        <div style="background-color: #0D0D0D; padding: 30px; text-align: center; border-bottom: 1px solid #C9A84C;">
            <h1 style="color: #C9A84C; font-size: 24px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin: 0;">AEROLUX SELECT</h1>
            <p style="color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin: 5px 0 0 0;">Reservation Confirmed & Secured</p>
        </div>
        <div style="padding: 30px;">
            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">Dear {customer_name},</p>
            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">We are pleased to inform you that your reservation <strong>{booking_reference}</strong> has been officially confirmed and a professional chauffeur has been allocated to your schedule.</p>
            
            <div style="background-color: #1a1a1a; padding: 20px; border-radius: 8px; margin: 25px 0; border: 1px solid #333;">
                <h3 style="color: #C9A84C; margin-top: 0; font-size: 14px; uppercase; letter-spacing: 1px;">Trip Receipt & Ledger</h3>
                <table style="width: 100%; font-size: 13px; color: #ccc; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; color: #888; width: 35%;">Pickup Date/Time:</td>
                        <td style="padding: 6px 0; color: #fff;">{pickup_date} at {pickup_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Return Date/Time:</td>
                        <td style="padding: 6px 0; color: #fff;">{return_date} at {return_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Pickup Location:</td>
                        <td style="padding: 6px 0; color: #fff;">{pickup_address}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Drop-off Location:</td>
                        <td style="padding: 6px 0; color: #fff;">{dropoff_address}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888; font-weight: bold; border-top: 1px solid #333;">Total Fare:</td>
                        <td style="padding: 6px 0; color: #fff; font-weight: bold; border-top: 1px solid #333;">{total_price}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888; font-weight: bold;">Amount Paid:</td>
                        <td style="padding: 6px 0; color: #fff; font-weight: bold;">{amount_paid}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888; font-weight: bold; border-top: 1px solid #333;">Outstanding Balance:</td>
                        <td style="padding: 6px 0; color: #C9A84C; font-weight: bold; border-top: 1px solid #333;">{balance}</td>
                    </tr>
                </table>
            </div>

            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">Your chauffeur will contact you prior to pickup. For airport pickups, our dispatch tracks flights and coordinates coordinates automatically.</p>
            <p style="font-size: 14px; line-height: 1.6; color: #ccc; margin-bottom: 0;">We look forward to welcoming you on board.<br>AeroLux Select Operations</p>
        </div>
        <div style="background-color: #0D0D0D; padding: 20px; text-align: center; font-size: 11px; color: #666; border-top: 1px solid #222;">
            &copy; AeroLux Select &bull; Luxury Chauffeur Logistics
        </div>
    </div>
</body>
</html>"""
        text_content = """Dear {customer_name},

Your reservation {booking_reference} is confirmed!

Ledger Details:
Pickup: {pickup_date} at {pickup_time}
Return: {return_date} at {return_time}
From: {pickup_address}
To: {dropoff_address}
Total: {total_price}
Paid: {amount_paid}
Balance: {balance}

Your chauffeur will coordinate prior to pickup.

Best regards,
AeroLux Select Desk"""

    elif email_type == 'reminder_12h':
        subject = f"Upcoming Service Reminder — {company_name} [{{booking_reference}}]"
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Chauffeur Service Reminder</title>
</head>
<body style="background-color: #0A0A0A; color: #FFFFFF; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 20px; margin: 0;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #111; border: 1px solid #222; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
        <div style="background-color: #0D0D0D; padding: 30px; text-align: center; border-bottom: 1px solid #C9A84C;">
            <h1 style="color: #C9A84C; font-size: 24px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin: 0;">AEROLUX SELECT</h1>
            <p style="color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin: 5px 0 0 0;">Upcoming Chauffeur Service Reminder</p>
        </div>
        <div style="padding: 30px;">
            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">Dear {customer_name},</p>
            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">This is a friendly reminder that your scheduled private chauffeur transfer <strong>{booking_reference}</strong> is in approximately 12 hours.</p>
            
            <div style="background-color: #1a1a1a; padding: 20px; border-radius: 8px; margin: 25px 0; border: 1px solid #333;">
                <h3 style="color: #C9A84C; margin-top: 0; font-size: 14px; uppercase; letter-spacing: 1px;">Upcoming Ride Details</h3>
                <table style="width: 100%; font-size: 13px; color: #ccc; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; color: #888; width: 35%;">Pickup Date/Time:</td>
                        <td style="padding: 6px 0; color: #fff;">{pickup_date} at {pickup_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Pickup Location:</td>
                        <td style="padding: 6px 0; color: #fff;">{pickup_address}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Drop-off Location:</td>
                        <td style="padding: 6px 0; color: #fff;">{dropoff_address}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Outstanding Balance:</td>
                        <td style="padding: 6px 0; color: #C9A84C; font-weight: bold;">{balance}</td>
                    </tr>
                </table>
            </div>

            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">Our team is tracking your itinerary. If there are any updates, please communicate them to our operations desk on WhatsApp as soon as possible.</p>
            <p style="font-size: 14px; line-height: 1.6; color: #ccc; margin-bottom: 0;">Have a pleasant journey,<br>AeroLux Select Dispatch</p>
        </div>
        <div style="background-color: #0D0D0D; padding: 20px; text-align: center; font-size: 11px; color: #666; border-top: 1px solid #222;">
            &copy; AeroLux Select &bull; Luxury Chauffeur Logistics
        </div>
    </div>
</body>
</html>"""
        text_content = """Dear {customer_name},

This is a reminder that your private transfer {booking_reference} is in approximately 12 hours.

Pickup: {pickup_date} at {pickup_time}
From: {pickup_address}
To: {dropoff_address}
Outstanding Balance: {balance}

If you need any changes, please notify us immediately.

Best regards,
AeroLux Select Desk"""

    elif email_type == 'cancelled':
        subject = f"Reservation Cancelled — {company_name} [{{booking_reference}}]"
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reservation Cancelled</title>
</head>
<body style="background-color: #0A0A0A; color: #FFFFFF; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 20px; margin: 0;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #111; border: 1px solid #222; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
        <div style="background-color: #0D0D0D; padding: 30px; text-align: center; border-bottom: 1px solid #ea4335;">
            <h1 style="color: #ea4335; font-size: 24px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin: 0;">AEROLUX SELECT</h1>
            <p style="color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin: 5px 0 0 0;">Reservation Cancelled</p>
        </div>
        <div style="padding: 30px;">
            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">Dear {customer_name},</p>
            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">We confirm that your reservation <strong>{booking_reference}</strong> has been cancelled. If this is a mistake or you need to reschedule, please contact our support team immediately.</p>
            
            <div style="background-color: #1a1a1a; padding: 20px; border-radius: 8px; margin: 25px 0; border: 1px solid #333;">
                <h3 style="color: #ea4335; margin-top: 0; font-size: 14px; uppercase; letter-spacing: 1px;">Cancelled Ride Summary</h3>
                <table style="width: 100%; font-size: 13px; color: #ccc; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; color: #888; width: 35%;">Reference:</td>
                        <td style="padding: 6px 0; color: #fff;">{booking_reference}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Pickup Date/Time:</td>
                        <td style="padding: 6px 0; color: #fff;">{pickup_date} at {pickup_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #888;">Pickup Location:</td>
                        <td style="padding: 6px 0; color: #fff;">{pickup_address}</td>
                    </tr>
                </table>
            </div>

            <p style="font-size: 14px; line-height: 1.6; color: #ccc;">If any prepayment was made via credit card, refunds are processed according to our cancellation policies.</p>
            <p style="font-size: 14px; line-height: 1.6; color: #ccc; margin-bottom: 0;">Thank you,<br>AeroLux Select Desk</p>
        </div>
        <div style="background-color: #0D0D0D; padding: 20px; text-align: center; font-size: 11px; color: #666; border-top: 1px solid #222;">
            &copy; AeroLux Select &bull; Luxury Chauffeur Logistics
        </div>
    </div>
</body>
</html>"""
        text_content = """Dear {customer_name},

We confirm that your reservation {booking_reference} has been cancelled.

If you have questions, please contact us.

Best regards,
AeroLux Select Desk"""
        
    return subject, html_content, text_content


def send_booking_email(booking, email_type):
    """
    Sends customized transactional emails using database templates or fallbacks via Brevo.
    Supports email_types: 'processing', 'confirmed', 'reminder_12h', 'cancelled'
    """
    site = booking.site
    settings_obj = SiteSettings.get_settings(site)
    
    # Recipient addresses
    customer_to = booking.customer_email
    dispatch_to = settings_obj.dispatch_email or 'dispatch@aeroluxeselect.com'
    
    # Sender address
    from_email = settings_obj.email_from or 'no-reply@aeroluxeselect.com'
    
    # Load template from DB if exists, otherwise fallback to defaults
    db_template = EmailTemplate.objects.filter(site=site, email_type=email_type).first()
    if db_template:
        subject_tpl = db_template.subject
        html_tpl = db_template.html_content
        text_tpl = db_template.text_content
    else:
        subject_tpl, html_tpl, text_tpl = get_default_email_template(email_type, settings_obj.company_name)

    # Context formatting
    context = get_email_context(booking)
    subject = format_template(subject_tpl, context)
    html_content = format_template(html_tpl, context)
    text_content = format_template(text_tpl, context)

    # Subject prefix for dispatch alerts
    subject_dispatch = f"[DISPATCH ALERT] {email_type.upper()}: {subject}"

    # Helper to send to a specific recipient
    def _send_to(to_email, sub):
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
                backend = None
                
            email = EmailMultiAlternatives(
                subject=sub,
                body=text_content,
                from_email=from_email,
                to=[to_email]
            )
            email.attach_alternative(html_content, "text/html")
            if backend:
                email.connection = backend
            email.send()
            
        # 2. SendGrid Provider
        elif provider == 'SENDGRID':
            api_key = settings_obj.email_api_key
            if not api_key:
                raise ValueError("SendGrid API key not configured")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_email, "name": settings_obj.company_name},
                "subject": sub,
                "content": [
                    {"type": "text/plain", "value": text_content},
                    {"type": "text/html", "value": html_content}
                ]
            }
            response = requests.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
        # 3. Resend Provider
        elif provider == 'RESEND':
            api_key = settings_obj.email_api_key
            if not api_key:
                raise ValueError("Resend API key not configured")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": f"{settings_obj.company_name} <{from_email}>",
                "to": [to_email],
                "subject": sub,
                "text": text_content,
                "html": html_content
            }
            response = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
        # 4. Mailgun Provider
        elif provider == 'MAILGUN':
            api_key = settings_obj.email_api_key
            domain = settings_obj.email_domain
            if not api_key or not domain:
                raise ValueError("Mailgun API key or Domain not configured")
            
            auth = ("api", api_key)
            payload = {
                "from": f"{settings_obj.company_name} <{from_email}>",
                "to": to_email,
                "subject": sub,
                "text": text_content,
                "html": html_content
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
                raise ValueError("Brevo API key not configured")
            
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "sender": {"email": from_email, "name": settings_obj.company_name},
                "to": [{"email": to_email}],
                "subject": sub,
                "htmlContent": html_content,
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

    # Send Dispatch Alert (For processing and cancellation)
    if email_type in ['processing', 'cancelled']:
        try:
            _send_to(dispatch_to, subject_dispatch)
        except Exception as e:
            print(f"Error sending dispatch email alert: {str(e)}")
        
    # Send Customer Notification
    try:
        _send_to(customer_to, subject)
    except Exception as e:
        print(f"Error sending customer notification email: {str(e)}")

    # Prepare/Log WhatsApp notification
    try:
        whatsapp_msg = get_formatted_whatsapp_message(booking, email_type)
        import logging
        logging.getLogger(__name__).info(
            f"Prepared WhatsApp notification for Booking {booking.booking_reference} ({email_type}): {whatsapp_msg}"
        )
        print(f"[WHATSAPP PREPARED] To: {booking.customer_phone or booking.customer_whatsapp} - Message: {whatsapp_msg}")
    except Exception as wa_err:
        import logging
        logging.getLogger(__name__).warning(
            f"Failed to prepare WhatsApp notification for Booking {booking.booking_reference}: {str(wa_err)}"
        )
        print(f"[WHATSAPP ERROR] Failed to prepare WhatsApp notification: {str(wa_err)}")


def send_booking_emails(booking):
    """Legacy backward compatibility method. Maps to processing phase."""
    send_booking_email(booking, 'processing')


def get_default_whatsapp_template(trigger_type, company_name="AeroLux Select"):
    """
    Returns default text for WhatsApp templates if not customized in the DB.
    """
    whatsapp_defaults = {
        'processing': 'Hello {customer_name}, thank you for choosing {company_name}. We have received your booking request {booking_reference}. We are currently processing it and will confirm shortly. Pickup: {pickup_address} on {pickup_date} at {pickup_time}.',
        'confirmed': 'Hello {customer_name}, your booking {booking_reference} with {company_name} is CONFIRMED. Your driver will meet you at {pickup_address} on {pickup_date} at {pickup_time}. Total price: {total_price}. Balance: {balance}. Thank you!',
        'reminder_12h': 'Hi {customer_name}, this is a reminder of your upcoming trip {booking_reference} with {company_name} in 12 hours. Pickup: {pickup_address} on {pickup_date} at {pickup_time}. We look forward to serving you!',
        'cancelled': 'Hello {customer_name}, we confirm that your booking {booking_reference} with {company_name} has been cancelled. If this was a mistake or you have questions, please contact us.'
    }
    return whatsapp_defaults.get(trigger_type, "").replace('{company_name}', company_name)


def get_formatted_whatsapp_message(booking, trigger_type):
    """
    Loads and formats the WhatsApp template for the given trigger type.
    """
    from core.models import WhatsAppTemplate
    site = booking.site
    company_name = site.name
    
    template = WhatsAppTemplate.objects.filter(site=site, trigger_type=trigger_type).first()
    if not template:
        template_text = get_default_whatsapp_template(trigger_type, company_name)
    else:
        template_text = template.message_content
        
    context = get_email_context(booking)
    return format_template(template_text, context)
