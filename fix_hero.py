import os
import re

directory = r"c:\Users\Réginald\Documents\antigravity\optimistic-archimedes\core\templates\core"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    # Revert gradients
    new_content = re.sub(r'\bfrom-theme-bg\b', 'from-black', new_content)
    new_content = re.sub(r'\bvia-theme-bg\b', 'via-black', new_content)
    new_content = re.sub(r'\bto-theme-bg\b', 'to-black', new_content)
    
    # We also need to fix text-theme-text inside the hero sections.
    # Since hero sections usually have these gradients, let's just find sections with `from-black` and change their text back to white.
    # Actually, a simpler way is to just find specific files with hero sections and fix them manually, or use regex.
    # Let's write out the new content for now.
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".html"):
            process_file(os.path.join(root, file))

print("Done.")
