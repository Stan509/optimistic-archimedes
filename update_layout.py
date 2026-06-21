import re

with open('core/templates/core/booking_step1.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Spacing and centering
content = content.replace('class="relative min-h-[85vh] flex items-center justify-center overflow-hidden py-16"', 'class="relative min-h-[100dvh] flex items-center justify-center overflow-hidden pt-40 pb-16 md:py-24"')

# 2. Width padding on mobile
content = content.replace('class="max-w-3xl w-full mx-auto px-4 sm:px-6 relative z-20"', 'class="max-w-3xl w-full mx-auto px-8 sm:px-12 md:px-6 relative z-20"')

# 3. Service type side-by-side
content = content.replace('class="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3', 'class="grid grid-cols-3 gap-1 sm:gap-3')

# 4. Map square and shorter
content = content.replace('class="relative w-full h-[600px] bg-theme-bg', 'class="relative w-full aspect-square max-h-[350px] md:max-h-[450px] bg-theme-bg')
content = content.replace('style="height: 600px;"', '')

# 5. Form fields side-by-side (2x2)
content = content.replace('class="flex flex-col md:flex-row items-center gap-4 relative"', 'class="grid grid-cols-2 gap-4 relative"')
content = content.replace('class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-theme-border"', 'class="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-theme-border"')
content = content.replace('class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4"', 'class="grid grid-cols-2 gap-4 mt-4"')
content = content.replace('class="grid grid-cols-1 md:grid-cols-2 gap-4"', 'class="grid grid-cols-2 gap-4"')

with open('core/templates/core/booking_step1.html', 'w', encoding='utf-8') as f:
    f.write(content)
