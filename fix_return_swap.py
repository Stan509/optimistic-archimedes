import re

with open('core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

search_pattern = r"booking_return\.linked_booking = booking_outbound\s*booking_return\.save\(\)"
replace_pattern = r"""
                # Swap airport and destination for return leg
                if airport_id:
                    booking_return.destination_id = int(airport_id)
                if dest_id:
                    booking_return.airport_id = int(dest_id)

                booking_return.linked_booking = booking_outbound
                booking_return.save()
"""

new_content = re.sub(search_pattern, replace_pattern.strip(), content)

with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Updated return_booking address logic')
