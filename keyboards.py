from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from config import ALL_GROUPS

# ─── Главное меню ────────────────────────────────────────────────────────────

def main_menu(has_group: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📅 Расписание на сегодня"),
         KeyboardButton(text="📆 Расписание на завтра")],
        [KeyboardButton(text="🗓 Расписание на неделю")],
        [KeyboardButton(text="🔍 Сменить группу")],
    ]
    if not has_group:
        buttons = [[KeyboardButton(text="🔍 Выбрать группу")]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


# ─── Выбор группы (inline по префиксам) ─────────────────────────────────────

def group_prefix_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с первыми буквами групп для быстрого поиска."""
    prefixes = sorted(set(g[:2] for g in ALL_GROUPS))
    buttons = []
    row = []
    for i, prefix in enumerate(prefixes):
        row.append(InlineKeyboardButton(
            text=prefix, callback_data=f"prefix:{prefix}"
        ))
        if len(row) == 4:
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
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_prefix")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Выбор дня для расписания ────────────────────────────────────────────────

def days_keyboard() -> InlineKeyboardMarkup:
    from datetime import date, timedelta
    from config import WEEKDAYS_RU
    today = date.today()
    buttons = []
    for i in range(6):
        d = today + timedelta(days=i)
        if d.weekday() == 6:
            continue
        label = WEEKDAYS_RU[d.weekday()] + " " + d.strftime("%d.%m")
        if i == 0:
            label = "Сегодня — " + d.strftime("%d.%m")
        elif i == 1:
            label = "Завтра — " + d.strftime("%d.%m")
        buttons.append([InlineKeyboardButton(
            text=label, callback_data=f"day:{d.isoformat()}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
