import re

with open('core/views_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'site', 'vehicle', 'vehicle_category'", "'site', 'vehicle_category'")

# Remove any lines containing "vehicle_id = request.POST.get('vehicle')"
content = re.sub(r"vehicle_id\s*=\s*request\.POST\.get\('vehicle'\)", "", content)
content = content.replace("'vehicle_id': vehicle_id,", "")

with open('core/views_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed pricing form')
