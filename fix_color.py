with open('core/templates/core/booking_step2.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('<h3 class="text-base font-bold text-theme-text group-hover:text-luxe-gold transition-colors">{{ category.name }}</h3>', '<h3 class="text-base font-bold text-white group-hover:text-luxe-gold transition-colors">{{ category.name }}</h3>')

with open('core/templates/core/booking_step2.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed text color')
