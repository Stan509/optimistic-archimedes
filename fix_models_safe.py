import re

with open('core/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove class Vehicle
# It starts at 'class Vehicle(models.Model):' and ends right before '# -----------------------------------------------\n#  PRICING RULE'
content = re.sub(r'class Vehicle\(models\.Model\):.*?# -----------------------------------------------\s*#  PRICING RULE', '# -----------------------------------------------\n#  PRICING RULE', content, flags=re.DOTALL)

# 2. Replace vehicle FK in PricingRule
pricing_rule_regex = re.compile(r'vehicle\s*=\s*models\.ForeignKey\(\s*Vehicle,\s*on_delete=models\.CASCADE,\s*related_name=\'pricing_rules\',\s*blank=True,\s*null=True,\s*help_text=\'Specific vehicle this price applies to\.\',\s*\)', re.DOTALL)
content = pricing_rule_regex.sub('', content)

# 3. Replace vehicle FK in Booking
booking_vehicle_regex = re.compile(r'vehicle\s*=\s*models\.ForeignKey\(\s*Vehicle,', re.DOTALL)
content = booking_vehicle_regex.sub('vehicle_category = models.ForeignKey(\n        VehicleCategory,', content)

with open('core/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated models.py safely')
