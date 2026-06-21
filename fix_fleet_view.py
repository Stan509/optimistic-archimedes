import re

with open('core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from core.models import VehicleCategory, Vehicle', 'from core.models import VehicleCategory')

content = re.sub(r'vehicles\s*=\s*Vehicle\.objects.*?Vehicle\.objects\.none\(\)', '', content, flags=re.DOTALL)
content = content.replace('vehicles = []', '')
content = content.replace("'vehicles': vehicles,", "")

with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated fleet view')
