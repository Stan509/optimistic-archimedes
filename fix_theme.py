import os
import re

directory = r"c:\Users\Réginald\Documents\antigravity\optimistic-archimedes\core\templates"

replacements = [
    # Backgrounds
    (r'bg-luxe-dark-grey', 'bg-theme-card'),
    (r'bg-luxe-black', 'bg-theme-bg'),
    (r'bg-luxe-grey', 'bg-theme-card'),
    
    # Text colors
    (r'\btext-white\b', 'text-theme-text'),
    (r'\btext-gray-400\b', 'text-theme-text/70'),
    (r'\btext-gray-300\b', 'text-theme-text/80'),
    (r'\btext-gray-500\b', 'text-theme-text/60'),
    
    # Borders
    (r'\bborder-gray-800\b', 'border-theme-border'),
    (r'\bborder-gray-900\b', 'border-theme-border'),
    
    # Gradients and Overlays
    (r'\bfrom-luxe-black\b', 'from-theme-bg'),
    (r'\bfrom-black\b', 'from-theme-bg'),
    (r'\bvia-black\b', 'via-theme-bg'),
    (r'\bto-black\b', 'to-theme-bg'),
]

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, new_content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".html"):
            process_file(os.path.join(root, file))

print("Done.")
