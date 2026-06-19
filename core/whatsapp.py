"""
AeroLux Select — WhatsApp Notification Module
Envoie des messages WhatsApp automatiques sans API (via WhatsApp Web + pywhatkit).

Prérequis :
  1. pip install pywhatkit
  2. Être connecté à WhatsApp Web (une fois) sur le serveur
  3. Avoir un navigateur graphique (ou Xvfb pour serveur headless)

Fallback : si pywhatkit échoue, le message est loggé avec un lien wa.me.

Mécanisme :
  - processing  : "Votre réservation est en cours d'analyse..."
  - confirmed   : "Votre réservation est confirmée !"
  - cancelled   : "Votre réservation a été annulée."
  - completed   : "Merci d'avoir choisi AeroLux Select !"
  - reminder_12h: "Rappel : votre service est dans 12h."
"""

import logging
import urllib.parse
import time
from django.conf import settings

logger = logging.getLogger(__name__)

# Flag: set to True if pywhatkit is installed
try:
    import pywhatkit
    PYWHATKIT_AVAILABLE = True
except ImportError:
    PYWHATKIT_AVAILABLE = False
    try:
        import webbrowser
    except ImportError:
        webbrowser = None


# ──────────────────────────────────────────────
#  Message templates
# ──────────────────────────────────────────────

WHATSAPP_TEMPLATES = {
    'processing': (
        "Hello {customer_name},\\n\\n"
        "Thank you for choosing AeroLux Select! 🚗✨\\n"
        "We have received your booking request **{booking_reference}**.\\n"
        "Our dispatch team is currently reviewing your itinerary.\\n"
        "We will confirm your reservation shortly.\\n\\n"
        "📅 Pickup: {pickup_date} at {pickup_time}\\n"
        "📍 From: {pickup_address}\\n"
        "📍 To: {dropoff_address}\\n\\n"
        "Stay tuned! - AeroLux Select Concierge"
    ),
    'confirmed': (
        "Hello {customer_name}, ✅\\n\\n"
        "Your booking **{booking_reference}** is CONFIRMED! 🎉\\n"
        "A professional chauffeur has been assigned to you.\\n\\n"
        "📅 {pickup_date} at {pickup_time}\\n"
        "📍 Pickup: {pickup_address}\\n"
        "📍 Drop-off: {dropoff_address}\\n"
        "💰 Total: {total_price}\\n"
        "💳 Paid: {amount_paid}\\n"
        "⚖️ Balance: {balance}\\n\\n"
        "Your driver will meet you at the designated meeting point.\\n"
        "For questions, reply to this message.\\n"
        "— AeroLux Select Operations"
    ),
    'cancelled': (
        "Hello {customer_name},\\n\\n"
        "We confirm that your booking **{booking_reference}** has been CANCELLED. ❌\\n"
        "If this was a mistake or you need to rebook, please contact us immediately.\\n\\n"
        "We apologize for any inconvenience.\\n"
        "— AeroLux Select Support"
    ),
    'completed': (
        "Hello {customer_name}, ⭐\\n\\n"
        "Thank you for riding with AeroLux Select!\\n"
        "We hope your experience was exceptional.\\n\\n"
        "If you enjoyed your service, we would love a 5-star review! 🌟\\n"
        "We look forward to serving you again.\\n\\n"
        "Warm regards,\\n"
        "The AeroLux Select Team"
    ),
    'reminder_12h': (
        "Hi {customer_name}, ⏰\\n\\n"
        "This is a friendly reminder that your AeroLux Select service\\n"
        "is in approximately 12 hours!\\n\\n"
        "📅 {pickup_date} at {pickup_time}\\n"
        "📍 From: {pickup_address}\\n"
        "📍 To: {dropoff_address}\\n"
        "⚖️ Balance due: {balance}\\n\\n"
        "Your chauffeur will be on time. Sit back and relax.\\n"
        "— AeroLux Select Dispatch"
    ),
}


def format_whatsapp_message(template_key, context):
    """Format a WhatsApp message with the given context."""
    template = WHATSAPP_TEMPLATES.get(template_key, "")
    if not template:
        return ""
    msg = template
    for k, v in context.items():
        placeholder = "{" + k + "}"
        msg = msg.replace(placeholder, str(v))
    return msg


def get_phone_number(booking):
    """Return the WhatsApp number or phone number from a booking."""
    raw = booking.customer_whatsapp or booking.customer_phone or ""
    # Strip everything except digits and leading +
    cleaned = raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def send_whatsapp_pywhatkit(phone_number, message):
    """
    Send WhatsApp via pywhatkit (WhatsApp Web automation).
    Requires a logged-in WhatsApp Web session and a graphical environment.
    On headless servers, use Xvfb: `xvfb-run python manage.py ...`
    """
    if not PYWHATKIT_AVAILABLE:
        return False

    try:
        # pywhatkit.sendwhatmsg(phone, message, hour, minute)
        # Send immediately by scheduling 2 minutes in the future
        now = time.localtime()
        hour = now.tm_hour
        minute = now.tm_min + 2
        if minute >= 60:
            minute -= 60
            hour += 1
        if hour >= 24:
            hour -= 24

        pywhatkit.sendwhatmsg(phone_number, message, hour, minute, wait_time=15)
        logger.info(f"[WHATSAPP SENT] To: {phone_number}")
        return True
    except Exception as e:
        logger.warning(f"[WHATSAPP ERROR] pywhatkit failed for {phone_number}: {e}")
        return False


def send_whatsapp_wa_link(phone_number, message):
    """
    Fallback: generate a wa.me deep link. The message is logged.
    The admin or customer can click the link to open WhatsApp.
    """
    encoded = urllib.parse.quote(message)
    link = f"https://wa.me/{phone_number.lstrip('+')}?text={encoded}"
    logger.info(f"[WHATSAPP LINK] To: {phone_number} — {link}")
    return link


def send_whatsapp(booking, trigger_type):
    """
    Main entry point. Attempts to send a WhatsApp notification.
    Returns True if sent, False if only logged/linked.

    Flow:
      1. Format message from context
      2. Get phone number
      3. Try pywhatkit (auto-send via WhatsApp Web)
      4. Fallback: generate wa.me link + log
    """
    from core.emails import get_email_context

    context = get_email_context(booking)
    message = format_whatsapp_message(trigger_type, context)
    phone = get_phone_number(booking)

    if not phone or not message:
        logger.warning(f"[WHATSAPP SKIP] No phone or message for booking {booking.booking_reference}")
        return False

    logger.info(f"[WHATSAPP PREPARE] Booking {booking.booking_reference} | Type: {trigger_type} | To: {phone}")

    # Attempt auto-send via pywhatkit
    sent = send_whatsapp_pywhatkit(phone, message)
    if sent:
        return True

    # Fallback: generate wa.me link
    link = send_whatsapp_wa_link(phone, message)
    logger.info(f"[WHATSAPP LINK READY] {link}")
    return False