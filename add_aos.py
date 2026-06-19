import os
import re

directory = r"c:\Users\Réginald\Documents\antigravity\optimistic-archimedes\core\templates\core"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    
    # Add data-aos="fade-up" to sections if not already present
    new_content = re.sub(
        r'<section(?![^>]*data-aos)([^>]*)class="([^"]*)"',
        r'<section data-aos="fade-up" \1class="\2"',
        new_content
    )
    
    # Add data-aos="fade-up" to glass-cards if not already present
    new_content = re.sub(
        r'<div(?![^>]*data-aos)([^>]*)class="([^"]*glass-card[^"]*)"',
        r'<div data-aos="fade-up" data-aos-delay="100" \1class="\2"',
        new_content
    )

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".html"):
            process_file(os.path.join(root, file))

print("Done.")
