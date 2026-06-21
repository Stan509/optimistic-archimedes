import re

with open('core/views_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'passengers_capacity': int(request.POST.get('passengers_capacity', 4)),", "'passengers_capacity': int(request.POST.get('passengers_capacity') or 4),")
content = content.replace("'luggage_capacity': int(request.POST.get('luggage_capacity', 4)),", "'luggage_capacity': int(request.POST.get('luggage_capacity') or 4),")
content = content.replace("'order': int(request.POST.get('order', 0)),", "'order': int(request.POST.get('order') or 0),")

with open('core/views_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed int conversion')
