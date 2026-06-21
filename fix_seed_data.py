import re

with open('core/management/commands/seed_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove Vehicle import
content = content.replace('VehicleCategory, Vehicle,', 'VehicleCategory,')

# Remove the entire block that creates Vehicles
# It starts at '# Vehicles' and goes to 'self.stdout.write('  Linking vehicle images...')'
content = re.sub(r'# Vehicles\n.*?self\.stdout\.write\(\'  Linking vehicle images\.\.\.\'\)', 'self.stdout.write(\'  Linking vehicle images...\')', content, flags=re.DOTALL)

# Remove the 'vehicle_images' dictionary and the loop
content = re.sub(r'# Map vehicle names.*?except Vehicle\.DoesNotExist:\n\s*pass\n', '', content, flags=re.DOTALL)

# Remove 'vehicle=None,' from PricingRule creation
content = content.replace('vehicle=None,\n', '')

# Remove summary print
content = re.sub(r'self\.stdout\.write\(f\'  Vehicles: \{Vehicle\.objects\.count\(\)\}\'\)\n', '', content)

with open('core/management/commands/seed_data.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed seed_data.py')
