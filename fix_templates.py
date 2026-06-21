import os
import re

for filename in ['core/templates/core/booking_step2.html', 'core/templates/core/fleet.html', 'core/templates/core/booking_step3.html', 'core/templates/core/emails/booking_confirmation_en.html', 'core/templates/core/emails/booking_confirmation_es.html', 'core/templates/core/emails/booking_confirmation_fr.html']:
    if not os.path.exists(filename):
        continue
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # In templates, 'vehicle' object is often used. We just replaced the model name, but variables passed in context might still be 'category' or 'vehicle'.
    # In booking_step2.html, we iterate over 'categories' as 'cat'.
    # In fleet.html, we likely iterate over 'categories' as 'category'.
    # For booking_step3 and emails, 'booking.vehicle.name' -> 'booking.vehicle_category.name'
    
    content = content.replace('booking.vehicle.name', 'booking.vehicle_category.name')
    content = content.replace('booking.vehicle.category.name', 'booking.vehicle_category.name')
    content = content.replace('booking.vehicle', 'booking.vehicle_category')
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

print('Updated templates')
