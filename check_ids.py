import re

with open('core/templates/core/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

ids_to_check = [
    'rad-transfer', 'rad-hourly', 'rad-p2p', 'lbl-transfer', 'lbl-hourly', 'lbl-p2p',
    'icon-transfer', 'icon-hourly', 'icon-p2p', 'span-transfer', 'span-hourly', 'span-p2p',
    'div-airport-transfer-wrapper', 'div-hourly', 'div-flight', 'div-custom-addresses',
    'div-dropoff-location', 'div-stops-section', 'div-stops-count-wrapper', 'div-round-trip',
    'div-return-fields', 'airport_id', 'destination_address', 'pickup_address', 'dropoff_address',
    'round_trip', 'return_date', 'return_time', 'submit-btn', 'geocode-status', 'geocode-status-text'
]

missing = []
for id_val in ids_to_check:
    if f'id="{id_val}"' not in html and f"id='{id_val}'" not in html:
        missing.append(id_val)

print('Missing IDs:', missing)
