# -*- coding: utf-8 -*-
"""
Модуль генерации .ics файлов для экспорта расписания в календарь.
Поддерживает iOS Calendar, Google Calendar, Samsung Calendar и другие.
"""

import os
import re
import tempfile
import urllib.parse
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


def generate_ics(
    group: str,
    data: list[tuple[date, list[dict]]],
    filename_prefix: str = "schedule",
) -> Optional[str]:
    """
    Генерирует .ics файл для одного или нескольких дней.
    
    data — список кортежей (target_date, lessons)
    """
    if not data:
        return None

    all_events = []
    
    for target_date, lessons in data:
        if not lessons:
            continue
            
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

            description_parts = [f"📚 {pair_num}"]
            if teacher:
                description_parts.append(f"👤 {teacher}")
            if room:
                description_parts.append(f"🚪 {room}")
            description_parts.append(f"Группа: {group}")
            description_parts.append("Создано ботом МАГПК Расписание")
            description = "\\n".join(description_parts)

            # Место
            location = room if room else "МАГПК"

            # Формируем событие
            now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            
            # Проверяем длительность пары для разделения на две части по 45 минут с 5-минутной переменой
            duration_mins = int((dtend - dtstart).total_seconds() / 60)
            if duration_mins >= 50:
                # Первая половина (45 минут)
                dtstart_1 = dtstart
                dtend_1 = dtstart + timedelta(minutes=45)
                uid_1 = _make_uid(group, target_date, f"{i}-part1")
                
                event_1 = f"""BEGIN:VEVENT
UID:{uid_1}
DTSTAMP:{now}
DTSTART;TZID=Asia/Yekaterinburg:{dtstart_1.strftime("%Y%m%dT%H%M%S")}
DTEND;TZID=Asia/Yekaterinburg:{dtend_1.strftime("%Y%m%dT%H%M%S")}
SUMMARY:{_escape_ics(subject)} (1/2)
DESCRIPTION:{description}\\nЧасть 1 из 2
LOCATION:{_escape_ics(location)}
BEGIN:VALARM
TRIGGER:-PT60M
ACTION:DISPLAY
DESCRIPTION:Через 1 час: {_escape_ics(subject)} (1/2)
END:VALARM
END:VEVENT"""
                all_events.append(event_1)

                # Внутрипарная перемена (5 минут)
                dtstart_break = dtstart + timedelta(minutes=45)
                dtend_break = dtstart + timedelta(minutes=50)
                uid_break = _make_uid(group, target_date, f"{i}-break5")
                
                break_event = f"""BEGIN:VEVENT
UID:{uid_break}
DTSTAMP:{now}
DTSTART;TZID=Asia/Yekaterinburg:{dtstart_break.strftime("%Y%m%dT%H%M%S")}
DTEND;TZID=Asia/Yekaterinburg:{dtend_break.strftime("%Y%m%dT%H%M%S")}
SUMMARY:☕️ Перемена (5 мин)
DESCRIPTION:Перерыв внутри пары
LOCATION:{_escape_ics(location)}
END:VEVENT"""
                all_events.append(break_event)

                # Вторая половина
                dtstart_2 = dtstart + timedelta(minutes=50)
                dtend_2 = dtend
                uid_2 = _make_uid(group, target_date, f"{i}-part2")
                
                event_2 = f"""BEGIN:VEVENT
UID:{uid_2}
DTSTAMP:{now}
DTSTART;TZID=Asia/Yekaterinburg:{dtstart_2.strftime("%Y%m%dT%H%M%S")}
DTEND;TZID=Asia/Yekaterinburg:{dtend_2.strftime("%Y%m%dT%H%M%S")}
SUMMARY:{_escape_ics(subject)} (2/2)
DESCRIPTION:{description}\\nЧасть 2 из 2
LOCATION:{_escape_ics(location)}
END:VEVENT"""
                all_events.append(event_2)
            else:
                # Обычное событие, если пара короткая
                uid = _make_uid(group, target_date, i)
                event = f"""BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now}
DTSTART;TZID=Asia/Yekaterinburg:{dtstart.strftime("%Y%m%dT%H%M%S")}
DTEND;TZID=Asia/Yekaterinburg:{dtend.strftime("%Y%m%dT%H%M%S")}
SUMMARY:{_escape_ics(subject)}
DESCRIPTION:{description}
LOCATION:{_escape_ics(location)}
BEGIN:VALARM
TRIGGER:-PT60M
ACTION:DISPLAY
DESCRIPTION:Через 1 час: {_escape_ics(subject)}
END:VALARM
END:VEVENT"""
                all_events.append(event)

            # Добавляем перемену перед следующей парой
            if i < len(lessons):
                next_lesson = lessons[i] # i - это уже индекс следующего (так как i в enumerate от 1)
                next_time_str = next_lesson.get("time", "")
                next_parsed = _parse_time_range(next_time_str)
                
                if parsed and next_parsed:
                    _, curr_end = parsed
                    next_start, _ = next_parsed
                    
                    # Считаем разницу
                    fmt = "%H:%M"
                    try:
                        t1 = datetime.strptime(curr_end, fmt)
                        t2 = datetime.strptime(next_start, fmt)
                        diff = int((t2 - t1).total_seconds() / 60)
                        
                        if 0 < diff <= 20:
                            label = "☕️ Перемена"
                            
                            b_start_h, b_start_m = map(int, curr_end.split(":"))
                            b_end_h, b_end_m = map(int, next_start.split(":"))
                            
                            b_dtstart = datetime(target_date.year, target_date.month, target_date.day, b_start_h, b_start_m)
                            b_dtend = datetime(target_date.year, target_date.month, target_date.day, b_end_h, b_end_m)
                            
                            b_uid = _make_uid(group, target_date, f"{i}-interbreak")
                            break_event = f"""BEGIN:VEVENT
UID:{b_uid}
DTSTAMP:{now}
DTSTART;TZID=Asia/Yekaterinburg:{b_dtstart.strftime("%Y%m%dT%H%M%S")}
DTEND;TZID=Asia/Yekaterinburg:{b_dtend.strftime("%Y%m%dT%H%M%S")}
SUMMARY:{label} ({diff} мин)
DESCRIPTION:Перерыв между парами
END:VEVENT"""
                            all_events.append(break_event)
                    except:
                        pass

    if not all_events:
        return None

    # Собираем .ics файл
    label = f"Расписание {group}"
    events_str = "\n".join(all_events)
    cal = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//MAGPK Bot//Schedule//RU
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:{label}
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
{events_str}
END:VCALENDAR"""

    # Записываем во временный файл
    filename = f"{filename_prefix}_{group}_{datetime.now().strftime('%H%M%S')}.ics"
    filepath = os.path.join(tempfile.gettempdir(), filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(cal)
    
    return filepath


def generate_ics_for_day(group: str, target_date: date, lessons: list[dict]) -> Optional[str]:
    """Обертка для обратной совместимости."""
    return generate_ics(group, [(target_date, lessons)], "day")


def get_google_calendar_lesson_links(group: str, target_date: date, lessons: list[dict]) -> list[tuple[str, str]]:
    """Генерирует ссылки для добавления каждой пары в Google Calendar отдельными событиями."""
    links = []
    if not lessons:
        return links
        
    for i, lesson in enumerate(lessons, 1):
        subject = lesson.get("subject", "Занятие")
        pair_num = lesson.get("pair_num", f"{i} пара")
        
        # Определяем время
        time_str = lesson.get("time", "")
        parsed = _parse_time_range(time_str)
        if parsed:
            start_time_str, end_time_str = parsed
        else:
            times = PAIR_TIMES.get(pair_num, PAIR_TIMES.get(f"{i} пара", ("08:00", "09:35")))
            start_time_str, end_time_str = times

        s_h, s_m = map(int, start_time_str.split(":"))
        e_h, e_m = map(int, end_time_str.split(":"))
        
        dt_start = datetime(target_date.year, target_date.month, target_date.day, s_h, s_m)
        dt_end = datetime(target_date.year, target_date.month, target_date.day, e_h, e_m)
        
        # Разница часового пояса (+5 к UTC)
        utc_start = (dt_start - timedelta(hours=5)).strftime("%Y%m%dT%H%M%SZ")
        utc_end = (dt_end - timedelta(hours=5)).strftime("%Y%m%dT%H%M%SZ")
        
        teacher = lesson.get("teacher", "")
        room = lesson.get("room", "")
        
        # Описание события
        description_parts = [f"📚 {pair_num}"]
        if teacher:
            description_parts.append(f"👤 {teacher}")
        if room:
            description_parts.append(f"🚪 {room}")
        description_parts.append(f"Группа: {group}")
        description_parts.append("Создано ботом МАГПК Расписание")
        description = "\\n".join(description_parts)
        
        params = {
            "action": "TEMPLATE",
            "text": f"{subject} ({pair_num})",
            "dates": f"{utc_start}/{utc_end}",
            "details": description,
            "location": room if room else "МАГПК",
        }
        
        url = "https://www.google.com/calendar/render?" + urllib.parse.urlencode(params)
        links.append((pair_num, url))
        
    return links
