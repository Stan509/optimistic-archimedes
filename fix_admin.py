import re

with open('core/admin.py', 'r', encoding='utf-8') as f:
    admin_content = f.read()

# 1. Remove VehicleInline from core/admin.py
inline_regex = re.compile(r'class VehicleInline\(admin\.StackedInline\):.*?(?=@admin)', re.DOTALL)
admin_content = inline_regex.sub('', admin_content)

# 2. Remove VehicleAdmin from core/admin.py
admin_regex = re.compile(r'@admin\.register\(Vehicle\)\s*class VehicleAdmin\(admin\.ModelAdmin\):.*?(?=@admin)', re.DOTALL)
admin_content = admin_regex.sub('', admin_content)

# 3. Remove from imports
admin_content = admin_content.replace(', Vehicle, ', ', ')

# 4. Remove 'inlines = [VehicleInline]' from VehicleCategoryAdmin
admin_content = admin_content.replace('inlines = [VehicleInline]', '')

with open('core/admin.py', 'w', encoding='utf-8') as f:
    f.write(admin_content)
print('Cleaned up admin.py')
