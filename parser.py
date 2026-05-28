# -*- coding: utf-8 -*-
"""
Парсер расписания с сайта magpk.ru
С кэшированием — парсим сайт один раз, потом отдаём из кэша.
"""

import urllib.request
import urllib.parse
import http.cookiejar
import ssl
import re
import time
import logging
from bs4 import BeautifulSoup
from datetime import date, timedelta
from config import SCHEDULE_URL, WEEKDAYS_RU

logger = logging.getLogger(__name__)

# Отключаем проверку SSL
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ═══════════════════════════════════════════════════════════════════════════════
#  КЭШ
#  Ключ: (group, date_iso) → {"lessons": [...], "timestamp": float}
#  TTL: 30 минут (1800 секунд)
# ═══════════════════════════════════════════════════════════════════════════════

_cache: dict[tuple[str, str], dict] = {}
CACHE_TTL = 1800  # 30 минут


def _cache_key(group: str, target_date: date) -> tuple[str, str]:
    return (group, target_date.isoformat())


def _cache_get(group: str, target_date: date) -> list[dict] | None:
    """Возвращает закэшированные уроки или None если кэш устарел/пуст."""
    key = _cache_key(group, target_date)
    entry = _cache.get(key)
    if entry is None:
        return None
    if time.time() - entry["timestamp"] > CACHE_TTL:
        del _cache[key]
        logger.info(f"♻️ Кэш устарел: {key}")
        return None
    logger.info(f"✅ Кэш-хит: {key}")
    return entry["lessons"]


def _cache_set(group: str, target_date: date, lessons: list[dict] | None):
    """Сохраняет уроки в кэш."""
    key = _cache_key(group, target_date)
    # lessons=None значит «расписание не найдено» — тоже кэшируем
    _cache[key] = {
        "lessons": lessons,
        "timestamp": time.time(),
    }
    logger.info(f"💾 Кэш сохранён: {key} ({len(lessons) if lessons else 0} пар)")

    # Чистим старые записи (больше 200 — удаляем самые старые)
    if len(_cache) > 200:
        oldest = sorted(_cache.items(), key=lambda x: x[1]["timestamp"])
        for k, _ in oldest[:50]:
            del _cache[k]


def clear_cache():
    """Полная очистка кэша (можно вызвать через админ-команду)."""
    _cache.clear()
    logger.info("🗑 Кэш полностью очищен")


def cache_stats() -> dict:
    """Статистика кэша."""
    now = time.time()
    active = sum(1 for v in _cache.values() if now - v["timestamp"] <= CACHE_TTL)
    return {
        "total": len(_cache),
        "active": active,
        "expired": len(_cache) - active,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ПАРСИНГ HTML
# ═══════════════════════════════════════════════════════════════════════════════

def _clean_hall(hall_str: str) -> str:
    """Убирает длинные названия отделений из строки кабинета."""
    for prefix in [
        "Машиностроительное отделение /",
        "технологическое отделения /",
        "общеобразовательное отделение /",
        "Технологическое отделение /",
        "Общеобразовательное отделение /",
    ]:
        hall_str = hall_str.replace(prefix, "").strip()
    return hall_str


def _parse_html(html: str) -> list[dict] | None:
    """
    Парсит HTML и возвращает список уроков или None если блок не найден.
    Пустой список = занятий нет.
    """
    soup = BeautifulSoup(html, "html.parser")
    timetable_div = soup.find("div", class_="timetable")

    if not timetable_div:
        # Проверяем, выходной ли это
        body_text = soup.get_text(" ", strip=True).lower()
        if "занятий нет" in body_text or "нет занятий" in body_text or "выходной" in body_text:
            return []  # Пустой = выходной
        return None  # None = данных нет вообще

    periods = timetable_div.find_all("ul", class_="timetable__period")
    if not periods:
        return []

    lessons = []
    for period in periods:
        num_tag = period.find("li", class_="timetable__item--period-num")
        num_str = num_tag.get_text(strip=True) if num_tag else "Пара"

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
            lessons.append({
                "pair_num": num_str,
                "time": time_str,
                "subject": disciple_str,
                "teacher": teacher_str,
                "room": _clean_hall(hall_str),
            })

    return lessons


# ═══════════════════════════════════════════════════════════════════════════════
#  HTTP ЗАПРОСЫ
# ═══════════════════════════════════════════════════════════════════════════════

async def _fetch_html(group: str, target_date: date) -> str:
    """Получает HTML со страницы расписания (сетевой запрос)."""
    date_str = target_date.strftime("%Y-%m-%d")

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
        req_get = urllib.request.Request(SCHEDULE_URL, headers=headers)
        opener.open(req_get)

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
        return await loop.run_in_executor(None, make_request)
    except Exception as e:
        return f"❌ Ошибка соединения с сайтом: {e}"


async def _get_lessons(group: str, target_date: date) -> list[dict] | None | str:
    """
    Главная функция получения данных.
    1. Проверяет кэш
    2. Если кэша нет — загружает с сайта, парсит, кэширует
    Возвращает:
      list[dict] — уроки (может быть пустым = выходной)
      None — данные не найдены
      str — ошибка
    """
    # 1. Проверяем кэш
    cached = _cache_get(group, target_date)
    if cached is not None:
        return cached

    # Кэш может хранить None (данные не найдены), поэтому проверяем ключ
    key = _cache_key(group, target_date)
    if key in _cache and _cache[key]["lessons"] is None:
        if time.time() - _cache[key]["timestamp"] <= CACHE_TTL:
            logger.info(f"✅ Кэш-хит (None): {key}")
            return None

    # 2. Загружаем с сайта
    logger.info(f"🌐 Загрузка с сайта: {group} / {target_date}")
    html = await _fetch_html(group, target_date)
    if isinstance(html, str) and html.startswith("❌"):
        return html  # Ошибка сети — не кэшируем

    # 3. Парсим
    lessons = _parse_html(html)

    # 4. Кэшируем
    _cache_set(group, target_date, lessons)

    return lessons


# ═══════════════════════════════════════════════════════════════════════════════
#  ПУБЛИЧНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

async def fetch_schedule(group: str, target_date: date) -> str:
    """
    Получает расписание для группы на указанную дату.
    Возвращает отформатированную строку для Telegram.
    Данные берутся из кэша или загружаются с сайта (и кэшируются).
    """
    day_name = WEEKDAYS_RU[target_date.weekday()]
    date_formatted = target_date.strftime("%d.%m.%Y")

    result = await _get_lessons(group, target_date)

    # Ошибка сети
    if isinstance(result, str):
        return result

    # Данные не найдены
    if result is None:
        return (
            f"┌─────────────────────────────┐\n"
            f"  📅  *{group}*  •  {day_name}\n"
            f"  🗓  {date_formatted}\n"
            f"└─────────────────────────────┘\n\n"
            f"ℹ️ Расписание не найдено.\n"
            f"Возможно, данные ещё не добавлены."
        )

    # Пустой список = выходной
    if not result:
        return (
            f"┌─────────────────────────────┐\n"
            f"  📅  *{group}*  •  {day_name}\n"
            f"  🗓  {date_formatted}\n"
            f"└─────────────────────────────┘\n\n"
            f"🎉 *Занятий нет!* Отдыхай!"
        )

    return _format_schedule(group, day_name, date_formatted, result)


async def fetch_schedule_data(group: str, target_date: date) -> list[dict]:
    """
    Получает структурированные данные расписания для .ics.
    Данные берутся из кэша или загружаются с сайта.
    """
    result = await _get_lessons(group, target_date)
    if isinstance(result, (str, type(None))):
        return []
    return result


async def fetch_week_schedule(group: str, start_date: date) -> list[str]:
    """Расписание на неделю (пн-сб). Все дни кэшируются отдельно."""
    results = []
    for i in range(6):
        day = start_date + timedelta(days=i)
        if day.weekday() == 6:
            continue
        text = await fetch_schedule(group, day)
        results.append(text)
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  ФОРМАТИРОВАНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

def _format_schedule(group: str, day_name: str, date_formatted: str, lessons: list[dict]) -> str:
    """Форматирует расписание в красивый текст для Telegram."""
    lines = [
        f"┌─────────────────────────────┐",
        f"  📅  *{group}*  •  {day_name}",
        f"  🗓  {date_formatted}",
        f"└─────────────────────────────┘",
        "",
    ]

    pair_emojis = {
        "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣",
        "5": "5️⃣", "6": "6️⃣", "7": "7️⃣",
    }

    for lesson in lessons:
        pair_num = lesson["pair_num"]
        digit = re.search(r'\d', pair_num)
        emoji = pair_emojis.get(digit.group() if digit else "", "📗")

        time_str = lesson["time"]
        subject = lesson["subject"]
        teacher = lesson["teacher"]
        room = lesson["room"]

        lines.append(f"{emoji}  *{pair_num}*")
        if time_str:
            lines.append(f"    🕐  {time_str}")
        lines.append(f"    📖  {subject}")
        if teacher:
            lines.append(f"    👤  {teacher}")
        if room:
            lines.append(f"    🚪  {room}")
        lines.append("")

    count = len(lessons)
    word = "пара" if count == 1 else ("пары" if 2 <= count <= 4 else "пар")
    lines.append(f"📊  Всего: *{count} {word}*")
    lines.append(f"\n🔗 [Открыть на сайте]({SCHEDULE_URL})")

    return "\n".join(lines)
