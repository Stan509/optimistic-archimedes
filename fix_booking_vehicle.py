import re

with open('core/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace any occurrence of 'vehicle = models.ForeignKey(Vehicle' with 'vehicle_category = models.ForeignKey(VehicleCategory'
# Just match 'vehicle = models.ForeignKey(' and change it if it's pointing to Vehicle
content = re.sub(r'vehicle\s*=\s*models\.ForeignKey\(\s*\'?Vehicle\'?,', r'vehicle_category = models.ForeignKey(VehicleCategory,', content)

with open('core/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated Booking vehicle to vehicle_category')
