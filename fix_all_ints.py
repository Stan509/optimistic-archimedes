import re

with open('core/views_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix km_threshold
content = re.sub(r"int\(request\.POST\.get\('km_threshold',\s*25\)\)", r"int(request.POST.get('km_threshold') or 25)", content)

# Fix base_km
content = re.sub(r"int\(request\.POST\.get\('base_km',\s*25\)\)", r"int(request.POST.get('base_km') or 25)", content)

# Fix email_port
content = re.sub(r"int\(request\.POST\.get\('email_port',\s*587\)\)", r"int(request.POST.get('email_port') or 587)", content)

# Fix year GET
content = re.sub(r"int\(request\.GET\.get\('year',\s*date\.today\(\)\.year\)\)", r"int(request.GET.get('year') or date.today().year)", content)

# Fix year POST
content = re.sub(r"int\(request\.POST\.get\('year',\s*date\.today\(\)\.year\)\)", r"int(request.POST.get('year') or date.today().year)", content)

# Fix month POST
content = re.sub(r"int\(request\.POST\.get\('month',\s*date\.today\(\)\.month\)\)", r"int(request.POST.get('month') or date.today().month)", content)

with open('core/views_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed all int conversions')
