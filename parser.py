import urllib.request
import urllib.parse
import http.cookiejar
import ssl
import re
from bs4 import BeautifulSoup
from datetime import date, timedelta
from config import SCHEDULE_URL, WEEKDAYS_RU

# Отключаем проверку SSL (частая проблема учебных сайтов)
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


async def fetch_schedule(group: str, target_date: date) -> str:
    """
    Получает расписание для группы на указанную дату с сайта magpk.ru.
    Возвращает отформатированную строку с расписанием.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    day_name = WEEKDAYS_RU[target_date.weekday()]
    date_formatted = target_date.strftime("%d.%m.%Y")

    # Для работы сайта колледжа обязательно нужно получить Cookie сессии через GET
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=ssl_ctx)
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": SCHEDULE_URL,
    }

    def make_request():
        # 1. GET запрос для создания сессии и куки
        req_get = urllib.request.Request(SCHEDULE_URL, headers=headers)
        opener.open(req_get)

        # Ищем CSRF-токен Joomla, если он есть
        # (Обычно форма работает и без него, но для надежности добавим)
        csrf_token = None

        # 2. POST запрос
        payload = {
            "uch_gr_html": group,
            "date_sch_html": date_str,
            "btn_schedule_html": "Расписание",
        }
        
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req_post = urllib.request.Request(SCHEDULE_URL, data=data, headers=headers, method="POST")
        with opener.open(req_post, timeout=15) as response:
            return response.read().decode("utf-8", errors="replace")

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        html = await loop.run_in_executor(None, make_request)
    except Exception as e:
        return f"❌ Ошибка соединения с сайтом: {e}"

    return parse_schedule(html, group, day_name, date_formatted)


def parse_schedule(html: str, group: str, day_name: str, date_formatted: str) -> str:
    """
    Парсит HTML-страницу с расписанием и возвращает текст.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Ищем блок с расписанием
    timetable_div = soup.find("div", class_="timetable")
    
    if not timetable_div:
        # Проверяем, выходной ли это день
        body_text = soup.get_text(" ", strip=True).lower()
        if "занятий нет" in body_text or "нет занятий" in body_text or "выходной" in body_text:
            return (
                f"📅 *{group}* — {day_name}, {date_formatted}\n\n"
                f"🎉 *Занятий нет!* Выходной день."
            )
        return (
            f"📅 *{group}* — {day_name}, {date_formatted}\n\n"
            f"ℹ️ Расписание на этот день не найдено.\n"
            f"Возможно, это выходной или данные ещё не добавлены."
        )

    # Внутри timetable_div ищем все блоки пар <ul class="timetable__period">
    periods = timetable_div.find_all("ul", class_="timetable__period")
    
    if not periods:
        return (
            f"📅 *{group}* — {day_name}, {date_formatted}\n\n"
            f"🎉 *Занятий нет!* Выходной день."
        )

    lines = [f"📅 *{group}* — {day_name}, {date_formatted}\n"]
    
    for period in periods:
        # Номер пары (например, "1 пара")
        num_tag = period.find("li", class_="timetable__item--period-num")
        num_str = num_tag.get_text(strip=True) if num_tag else "Пара"

        # Данные внутри period
        period_details = period.find("div", class_="period")
        if not period_details:
            continue

        time_tag = period_details.find("span", class_="period__time")
        disciple_tag = period_details.find("span", class_="period__disciple")
        teacher_tag = period_details.find("span", class_="period__teacher")
        hall_tag = period_details.find("span", class_="period__lecturehall")

        time_str = time_tag.get_text(strip=True) if time_tag else ""
        disciple_str = disciple_tag.get_text(strip=True) if disciple_tag else ""
        teacher_str = teacher_tag.get_text(strip=True) if teacher_tag else ""
        hall_str = hall_tag.get_text(strip=True) if hall_tag else ""

        if disciple_str:
            # Красиво форматируем вывод
            num_display = f"*{num_str}*"
            if time_str:
                num_display += f" ({time_str})"
            
            line = f"\n{num_display}\n📖 {disciple_str}"
            if teacher_str:
                line += f"\n👤 {teacher_str}"
            if hall_str:
                # Очищаем кабинет от лишних длинных названий отделений для компактности
                clean_hall = hall_str.replace("Машиностроительное отделение /", "").strip()
                clean_hall = clean_hall.replace("технологическое отделения /", "").strip()
                clean_hall = clean_hall.replace("общеобразовательное отделение /", "").strip()
                line += f"\n🚪 {clean_hall}"
            
            lines.append(line)

    if len(lines) == 1:
        lines.append("\n🎉 *Занятий нет!* Выходной день.")

    lines.append(f"\n\n🔗 [Открыть на сайте]({SCHEDULE_URL})")
    return "\n".join(lines)


async def fetch_week_schedule(group: str, start_date: date) -> list[str]:
    """
    Получает расписание на неделю (6 дней, пн-сб).
    Возвращает список сообщений.
    """
    results = []
    for i in range(6):
        day = start_date + timedelta(days=i)
        if day.weekday() == 6:  # Пропускаем воскресенье
            continue
        text = await fetch_schedule(group, day)
        results.append(text)
    return results
