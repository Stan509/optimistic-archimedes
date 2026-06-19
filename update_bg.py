import glob

hero_bg = '''<section data-aos="fade-up" id="hero-section" class="relative min-h-[85vh] flex items-center justify-center overflow-hidden py-16">
    <!-- Video / Static Image Background -->
    <div class="absolute inset-0 z-0 overflow-hidden hero-perspective">
        <div class="absolute inset-0 bg-black/60 z-10"></div>
        {% if current_site.slug == 'nyc' %}
            <img src="{% static 'core/images/nyc-hero.jpg' %}?v=3" alt="NYC Premium Car Service" id="hero-parallax-img" class="w-full h-full md:h-[130%] object-cover md:object-cover object-center absolute top-0 md:-top-[15%] left-0 will-change-transform">
        {% elif current_site.slug == 'dr' %}
            <img src="{% static 'core/images/dr-hero.jpg' %}?v=3" alt="Dominican Republic VIP Transfers" id="hero-parallax-img" class="w-full h-full md:h-[130%] object-cover md:object-cover object-center absolute top-0 md:-top-[15%] left-0 will-change-transform">
        {% endif %}
    </div>
    <div class="max-w-3xl w-full mx-auto px-4 sm:px-6 relative z-20">'''

for filename in glob.glob('core/templates/core/booking_*.html'):
    if filename.endswith('booking_step1.html'):
        continue
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('<section data-aos="fade-up"  class="py-16 bg-theme-bg min-h-[85vh]">\n    <div class="max-w-3xl mx-auto px-4 sm:px-6">', hero_bg)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

