import re

with open('core/views_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'def vehicle_create\(request\):.*?return redirect\(\'dashboard_fleet\'\)', '', content, flags=re.DOTALL)
content = re.sub(r'def vehicle_edit\(request, pk\):.*?return redirect\(\'dashboard_fleet\'\)', '', content, flags=re.DOTALL)
content = re.sub(r'def vehicle_toggle\(request, pk\):.*?return redirect\(\'dashboard_fleet\'\)', '', content, flags=re.DOTALL)

content = content.replace('    from core.models import VehicleCategory, Vehicle', '    from core.models import VehicleCategory')
content = re.sub(r'vehicles\s*=\s*Vehicle\.objects\.all\(\)\.select_related\(\'category\'\)', '', content)
content = content.replace("'vehicles': vehicles,", "")

content = content.replace('    from core.models import PricingRule, Site, Vehicle, VehicleCategory', '    from core.models import PricingRule, Site, VehicleCategory')
content = re.sub(r'vehicles\s*=\s*Vehicle\.objects\.filter\(is_active=True\)\.select_related\(\'category\'\)', '', content)

with open('core/views_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Cleaned up core/views_dashboard.py')
