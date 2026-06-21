import re

with open('core/templates/core/booking_step1.html', 'r', encoding='utf-8') as f:
    b_html = f.read()

match = re.search(r'<script>\s*document\.addEventListener\(\'DOMContentLoaded\', \(\) => \{(.*?)</script>', b_html, re.DOTALL)
if match:
    b_js = match.group(1)
    
    with open('core/templates/core/index.html', 'r', encoding='utf-8') as f_idx:
        idx_html = f_idx.read()
        
    new_idx_html = re.sub(r'<script>\s*document\.addEventListener\(\'DOMContentLoaded\', \(\) => \{.*?</script>', '<script>\n      document.addEventListener(\'DOMContentLoaded\', () => {' + b_js + '</script>', idx_html, flags=re.DOTALL)
    
    with open('core/templates/core/index.html', 'w', encoding='utf-8') as f_idx:
        f_idx.write(new_idx_html)
    print('Replaced script block perfectly.')
else:
    print('Failed to extract script block')
