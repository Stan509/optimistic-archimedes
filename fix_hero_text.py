import os
import re

directory = r"c:\Users\Réginald\Documents\antigravity\optimistic-archimedes\core\templates\core"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find sections with from-black
    def replacer(match):
        section_content = match.group(0)
        # Replace text-theme-text with text-white
        section_content = section_content.replace('text-theme-text', 'text-white')
        # Also replace text-theme-text/80 with text-white/80 etc.
        section_content = re.sub(r'text-theme-text/(\d+)', r'text-white/\1', section_content)
        return section_content

    new_content = re.sub(r'<section class="relative[^>]*>.*?</section>', replacer, content, flags=re.DOTALL)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".html"):
            process_file(os.path.join(root, file))

print("Done.")
