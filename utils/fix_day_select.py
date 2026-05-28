#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Fix on_day_select to include Google Calendar URL
import pathlib

p = pathlib.Path(r'C:\Users\alexi\.gemini\antigravity\scratch\magpk_bot\handlers.py')
text = p.read_text(encoding='utf-8')

old = """    await call.message.edit_text(LOADING)
    target_date = date.fromisoformat(date_str)
    text = await fetch_schedule(group, target_date)
    await call.message.edit_text(text, parse_mode="Markdown",
                                 disable_web_page_preview=True,
                                 reply_markup=calendar_keyboard(target_date.isoformat()))"""

new = """    await call.message.edit_text(LOADING)
    target_date = date.fromisoformat(date_str)
    text = await fetch_schedule(group, target_date)
    lessons = await fetch_schedule_data(group, target_date)
    g_url = get_google_calendar_day_link(group, target_date, lessons)
    await call.message.edit_text(text, parse_mode="Markdown",
                                 disable_web_page_preview=True,
                                 reply_markup=calendar_keyboard(target_date.isoformat(), g_url))"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')
    print('Fixed on_day_select with Google Calendar URL')
else:
    print('Pattern not found - checking...')
    # Maybe whitespace difference
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'on_day_select' in line or 'calendar_keyboard(target_date' in line:
            print(f"  Line {i+1}: {repr(line)}")
