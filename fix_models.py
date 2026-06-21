import re

with open('core/models.py', 'r', encoding='utf-8') as f:
    models_content = f.read()

# 1. Delete Vehicle class
# The Vehicle class spans from 'class Vehicle(models.Model):' to the end of its save method or before the next class.
vehicle_regex = re.compile(r'class Vehicle\(models\.Model\):.*?def save\(self, \*args, \*\*kwargs\):.*?super\(\)\.save\(\*args, \*\*kwargs\)', re.DOTALL)
models_content = vehicle_regex.sub('', models_content)

# 2. Replace 'vehicle = models.ForeignKey(Vehicle,...' with 'vehicle_category' in PricingRule
pricing_rule_regex = re.compile(r'vehicle\s*=\s*models\.ForeignKey\(\s*Vehicle,\s*on_delete=models\.CASCADE,\s*\)', re.DOTALL)
models_content = pricing_rule_regex.sub('vehicle_category = models.ForeignKey(\n        VehicleCategory,\n        on_delete=models.CASCADE,\n        null=True, blank=True\n    )', models_content)

# 3. Replace 'vehicle = models.ForeignKey(Vehicle,...' in Booking
booking_vehicle_regex = re.compile(r'vehicle\s*=\s*models\.ForeignKey\(\s*Vehicle,\s*on_delete=models\.SET_NULL,\s*null=True,\s*blank=True,\s*related_name=\'bookings\',\s*help_text=\'Vehicle assigned to this booking\.\',\s*\)', re.DOTALL)
models_content = booking_vehicle_regex.sub('vehicle_category = models.ForeignKey(\n        VehicleCategory,\n        on_delete=models.SET_NULL,\n        null=True,\n        blank=True,\n        related_name=\'bookings\',\n        help_text=\'Vehicle category assigned to this booking.\',\n    )', models_content)

with open('core/models.py', 'w', encoding='utf-8') as f:
    f.write(models_content)
print('Updated models.py')
