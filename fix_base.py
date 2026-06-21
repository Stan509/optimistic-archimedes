import re

with open('core/templates/dashboard/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'<a href="\{% url \'dashboard:fleet\' %\}.*?Overview</a>\n\s*', '', content)
content = re.sub(r'<a href="\{% url \'dashboard:fleet_vehicles\' %\}.*?Vehicles</a>\n\s*', '', content)

with open('core/templates/dashboard/base.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed base.html')
