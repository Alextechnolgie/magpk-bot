#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Simplify week handler - remove per-day calendar buttons, keep only one "add whole week" button
import pathlib

p = pathlib.Path(r'C:\Users\alexi\.gemini\antigravity\scratch\magpk_bot\handlers.py')
text = p.read_text(encoding='utf-8')

# Find the week handler body and replace the loop that sends per-day messages
# Current code sends each day with calendar_keyboard per day, then last day with week button
# New code: send each day WITHOUT calendar buttons, then send week button separately

lines = text.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Find the week schedule sending loop
    if '    await msg.delete()' in line and i > 260 and i < 310:
        # This is inside schedule_week handler
        # Replace everything from here to the end of the for loop
        new_lines.append(line)  # await msg.delete()
        i += 1
        
        # Skip old loop code until we find the next section or blank lines after loop
        # Collect until we find a line that's not indented with 8 spaces (i.e. end of loop)
        # or a new section
        while i < len(lines):
            curr = lines[i]
            # We're looking for the end of the for loop block
            if curr.strip() == '' and i + 1 < len(lines) and not lines[i+1].startswith('        '):
                break
            if curr.startswith('# ===') or curr.startswith('@router'):
                break
            i += 1
        
        # Insert our simplified code
        new_lines.append('    for text in days_texts:')
        new_lines.append('        await message.answer(text, parse_mode="Markdown",')
        new_lines.append('                             disable_web_page_preview=True)')
        new_lines.append('')
        new_lines.append('    # One button to add the ENTIRE week at once')
        new_lines.append('    await message.answer(')
        new_lines.append('        "\\U0001f4c5 *\\u0414\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u044c \\u0432 \\u043a\\u0430\\u043b\\u0435\\u043d\\u0434\\u0430\\u0440\\u044c?*\\n"')
        new_lines.append('        "\\u041d\\u0430\\u0436\\u043c\\u0438 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u2014 \\u0432\\u0441\\u0435 \\u043f\\u0430\\u0440\\u044b \\u043d\\u0435\\u0434\\u0435\\u043b\\u0438 \\u0434\\u043e\\u0431\\u0430\\u0432\\u044f\\u0442\\u0441\\u044f \\u0441\\u0440\\u0430\\u0437\\u0443!",')
        new_lines.append('        parse_mode="Markdown",')
        new_lines.append('        reply_markup=week_calendar_keyboard(monday.isoformat()),')
        new_lines.append('    )')
        new_lines.append('')
        continue
    
    new_lines.append(line)
    i += 1

text = '\n'.join(new_lines)
p.write_text(text, encoding='utf-8')
print('Week handler simplified - single "add whole week" button')
