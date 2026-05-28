#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Fix week handler to include Google Calendar URLs per day
import pathlib

p = pathlib.Path(r'C:\Users\alexi\.gemini\antigravity\scratch\magpk_bot\handlers.py')
text = p.read_text(encoding='utf-8')

# Fix: in the week loop, generate Google URL for each day
old = """        # \u041a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u043d\u0430\u044f \u043a\u043d\u043e\u043f\u043a\u0430 \u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0434\u043d\u044f
        markup = calendar_keyboard(day.isoformat())"""

new = """        # Google Calendar URL for each day
        day_lessons = await fetch_schedule_data(group, day)
        day_g_url = get_google_calendar_day_link(group, day, day_lessons)
        markup = calendar_keyboard(day.isoformat(), day_g_url)"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')
    print('Fixed week handler with Google URL per day')
else:
    # Try with garbled comment
    lines = text.split('\n')
    found = False
    for i, line in enumerate(lines):
        if 'markup = calendar_keyboard(day.isoformat())' in line:
            # Replace just this line and the comment above it
            comment_line = lines[i-1]
            lines[i-1] = '        # Google Calendar URL for each day'
            lines[i] = '        day_lessons = await fetch_schedule_data(group, day)\n        day_g_url = get_google_calendar_day_link(group, day, day_lessons)\n        markup = calendar_keyboard(day.isoformat(), day_g_url)'
            found = True
            break
    
    if found:
        text = '\n'.join(lines)
        p.write_text(text, encoding='utf-8')
        print('Fixed week handler (fallback method)')
    else:
        print('Pattern not found')
        for i, line in enumerate(lines):
            if 'calendar_keyboard(day' in line:
                print(f"  Line {i+1}: {repr(line)}")
