import os
import re

directory = r"c:\Users\Réginald\Documents\antigravity\optimistic-archimedes\core\templates\core"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = re.sub(r'\bfont-light\b', 'font-medium', content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".html"):
            process_file(os.path.join(root, file))

print("Done.")
