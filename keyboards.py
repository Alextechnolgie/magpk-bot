# -*- coding: utf-8 -*-
"""
Клавиатуры Telegram бота МАГПК Расписание.
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from config import ALL_GROUPS


# ─── Главное меню ────────────────────────────────────────────────────────────

def main_menu(has_group: bool = False) -> ReplyKeyboardMarkup:
    if not has_group:
        buttons = [
            [KeyboardButton(text="🎓 Выбрать группу")],
        ]
    else:
        buttons = [
            [KeyboardButton(text="📅 Сегодня"),
             KeyboardButton(text="📆 Завтра")],
            [KeyboardButton(text="🗓 Неделя"),
             KeyboardButton(text="📋 Выбрать день")],
            [KeyboardButton(text="🔄 Сменить группу"),
             KeyboardButton(text="ℹ️ О боте")],
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


# ─── Выбор группы (inline по префиксам) ─────────────────────────────────────

def group_prefix_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с первыми буквами групп для быстрого поиска."""
    prefixes = sorted(set(g[:2] for g in ALL_GROUPS))
    buttons = []
    row = []
    for i, prefix in enumerate(prefixes):
        row.append(InlineKeyboardButton(
            text=f"📁 {prefix}", callback_data=f"prefix:{prefix}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def groups_by_prefix_keyboard(prefix: str) -> InlineKeyboardMarkup:
    """Список групп, начинающихся с prefix."""
    groups = [g for g in ALL_GROUPS if g.startswith(prefix)]
    buttons = []
    row = []
    for i, g in enumerate(groups):
        row.append(InlineKeyboardButton(
            text=g, callback_data=f"setgroup:{g}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    # Кнопка назад
    buttons.append([InlineKeyboardButton(text="◀️ Назад к буквам", callback_data="back_prefix")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Выбор дня для расписания ────────────────────────────────────────────────

def days_keyboard() -> InlineKeyboardMarkup:
    from datetime import date, timedelta
    from config import WEEKDAYS_RU
    today = date.today()
    buttons = []
    for i in range(7):
        d = today + timedelta(days=i)
        if d.weekday() == 6:  # Воскресенье
            continue
        label = WEEKDAYS_RU[d.weekday()] + "  •  " + d.strftime("%d.%m")
        if i == 0:
            label = "📌 Сегодня  •  " + d.strftime("%d.%m")
        elif i == 1:
            label = "📎 Завтра  •  " + d.strftime("%d.%m")
        buttons.append([InlineKeyboardButton(
            text=label, callback_data=f"day:{d.isoformat()}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Кнопки календаря ────────────────────────────────────────────────────────

def calendar_keyboard(target_date_iso: str, google_url: str = "") -> InlineKeyboardMarkup:
    """Inline-кнопки для экспорта расписания на день."""
    buttons = [
        [InlineKeyboardButton(
            text="🍏 iPhone / iOS (файл)",
            callback_data=f"export_cal:{target_date_iso}"
        )],
    ]
    if google_url:
        buttons.append([InlineKeyboardButton(
            text="🤖 Google Календарь (ссылка)",
            url=google_url
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def week_calendar_keyboard(monday_iso: str) -> InlineKeyboardMarkup:
    """Inline-кнопки для экспорта расписания на всю неделю."""
    buttons = [
        [InlineKeyboardButton(
            text="🗓 Добавить ВСЮ НЕДЕЛЮ (iPhone)",
            callback_data=f"export_week:{monday_iso}"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Кнопка "О боте" / "Поддержать" ─────────────────────────────────────────

def about_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела 'О боте'."""
    buttons = [
        [InlineKeyboardButton(
            text="💬 Написать автору",
            url="https://t.me/Ishmametyev"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
