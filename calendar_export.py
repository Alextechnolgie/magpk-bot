# -*- coding: utf-8 -*-
"""
Модуль генерации .ics файлов для экспорта расписания в календарь.
Поддерживает iOS Calendar, Google Calendar, Samsung Calendar и другие.
"""

import os
import re
import tempfile
from datetime import date, datetime, timedelta
from typing import Optional

# Стандартные времена пар (начало - конец)
PAIR_TIMES = {
    "1 пара": ("08:15", "09:50"),
    "2 пара": ("10:10", "11:45"),
    "3 пара": ("12:05", "13:40"),
    "4 пара": ("13:50", "15:25"),
    "5 пара": ("15:35", "17:10"),
    "6 пара": ("17:20", "18:55"),
    "7 пара": ("19:00", "20:35"),
}


def _parse_time_range(time_str: str) -> tuple[str, str] | None:
    """Парсит строку времени вида '08:15-09:50' или '08:15 - 09:50'."""
    match = re.match(r'(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})', time_str)
    if match:
        return match.group(1), match.group(2)
    return None


def _make_uid(group: str, target_date: date, pair_num: int) -> str:
    """Генерирует уникальный UID для события."""
    return f"magpk-{group}-{target_date.isoformat()}-pair{pair_num}@magpk-bot"


def _escape_ics(text: str) -> str:
    """Экранирует специальные символы для .ics формата."""
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\n", "\\n")
    return text


def generate_ics_for_day(
    group: str,
    target_date: date,
    lessons: list[dict],
) -> Optional[str]:
    """
    Генерирует .ics файл для одного дня.
    
    lessons — список словарей:
    {
        "pair_num": "1 пара",
        "time": "08:15-09:50",
        "subject": "Математика",
        "teacher": "Иванов И.И.",
        "room": "Кабинет №31",
    }
    
    Возвращает путь к временному .ics файлу или None если нет занятий.
    """
    if not lessons:
        return None

    events = []
    for i, lesson in enumerate(lessons, 1):
        # Определяем время начала и конца
        time_str = lesson.get("time", "")
        parsed = _parse_time_range(time_str)
        if parsed:
            start_time_str, end_time_str = parsed
        else:
            # Берём из стандартного расписания
            pair_key = lesson.get("pair_num", f"{i} пара")
            times = PAIR_TIMES.get(pair_key, PAIR_TIMES.get(f"{i} пара", ("08:00", "09:35")))
            start_time_str, end_time_str = times

        # Создаём datetime
        start_h, start_m = map(int, start_time_str.split(":"))
        end_h, end_m = map(int, end_time_str.split(":"))
        
        dtstart = datetime(target_date.year, target_date.month, target_date.day, start_h, start_m)
        dtend = datetime(target_date.year, target_date.month, target_date.day, end_h, end_m)

        subject = lesson.get("subject", "Занятие")
        teacher = lesson.get("teacher", "")
        room = lesson.get("room", "")
        pair_num = lesson.get("pair_num", f"{i} пара")

        # Описание события
        description_parts = [f"📚 {pair_num}"]
        if teacher:
            description_parts.append(f"👤 {teacher}")
        if room:
            description_parts.append(f"🚪 {room}")
        description_parts.append(f"\nГруппа: {group}")
        description_parts.append("Создано ботом МАГПК Расписание")
        description = "\\n".join(description_parts)

        # Место
        location = room if room else "МАГПК"

        # Формируем событие
        uid = _make_uid(group, target_date, i)
        now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        
        event = f"""BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now}
DTSTART;TZID=Asia/Yekaterinburg:{dtstart.strftime("%Y%m%dT%H%M%S")}
DTEND;TZID=Asia/Yekaterinburg:{dtend.strftime("%Y%m%dT%H%M%S")}
SUMMARY:{_escape_ics(subject)}
DESCRIPTION:{description}
LOCATION:{_escape_ics(location)}
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Через 15 минут: {_escape_ics(subject)}
END:VALARM
END:VEVENT"""
        events.append(event)

    if not events:
        return None

    # Собираем .ics файл
    date_label = target_date.strftime("%d.%m.%Y")
    cal = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//MAGPK Bot//Schedule//RU
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:МАГПК {group} — {date_label}
X-WR-TIMEZONE:Asia/Yekaterinburg
BEGIN:VTIMEZONE
TZID:Asia/Yekaterinburg
BEGIN:STANDARD
DTSTART:19700101T000000
TZOFFSETFROM:+0500
TZOFFSETTO:+0500
TZNAME:+05
END:STANDARD
END:VTIMEZONE
{"".join(events)}
END:VCALENDAR"""

    # Записываем во временный файл
    filename = f"schedule_{group}_{target_date.isoformat()}.ics"
    filepath = os.path.join(tempfile.gettempdir(), filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(cal)
    
    return filepath
