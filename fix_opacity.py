import os
import re

directory = r"c:\Users\Réginald\Documents\antigravity\optimistic-archimedes\core\templates\core"

replacements = [
    (r'text-theme-text/60', 'text-theme-text/80'),
    (r'text-theme-text/70', 'text-theme-text/90'),
    (r'text-theme-text/80', 'text-theme-text/95'),
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
