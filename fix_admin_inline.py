import re

with open('core/admin.py', 'r', encoding='utf-8') as f:
    admin_content = f.read()

inline_regex = re.compile(r'class VehicleInline\(admin\.TabularInline\):.*?(?=@admin)', re.DOTALL)
admin_content = inline_regex.sub('', admin_content)

with open('core/admin.py', 'w', encoding='utf-8') as f:
    f.write(admin_content)
