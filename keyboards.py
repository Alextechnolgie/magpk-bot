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

def main_menu(has_group: bool = False, user_id: int = None, interface: str = "full") -> ReplyKeyboardMarkup:
    from config import ADMIN_IDS
    is_admin = user_id in ADMIN_IDS

    if not has_group:
        buttons = [
            [KeyboardButton(text="🎓 Выбрать группу")],
        ]
    elif interface == "compact":
        buttons = [
            [KeyboardButton(text="📅 Сегодня"),
             KeyboardButton(text="📆 Завтра")],
            [KeyboardButton(text="🗓 Неделя"),
             KeyboardButton(text="⚙️ Настройки")],
        ]
    else:
        # full interface
        buttons = [
            [KeyboardButton(text="📅 Сегодня"),
             KeyboardButton(text="📆 Завтра")],
            [KeyboardButton(text="🗓 Неделя"),
             KeyboardButton(text="📋 Выбрать день")],
            [KeyboardButton(text="🔄 Сменить группу"),
             KeyboardButton(text="ℹ️ О боте")],
            [KeyboardButton(text="⚙️ Настройки")],
        ]
        
    if is_admin:
        # Добавляем кнопку админки только для администраторов
        buttons.append([KeyboardButton(text="⚙️ Панель администратора")])
        
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def settings_keyboard(current_interface: str) -> InlineKeyboardMarkup:
    """Клавиатура настроек."""
    interface_label = "🖼 Интерфейс: Компактный" if current_interface == "compact" else "🖼 Интерфейс: Полный"
    
    buttons = [
        [InlineKeyboardButton(text=interface_label, callback_data="toggle_interface")],
        [InlineKeyboardButton(text="🔄 Сменить группу", callback_data="change_group_inline")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about_inline")],
        [InlineKeyboardButton(text="📋 Выбрать конкретный день", callback_data="choose_day_inline")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
    from datetime import timedelta
    from config import WEEKDAYS_RU, get_mgn_today
    today = get_mgn_today()
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

def calendar_keyboard(target_date_iso: str, google_links: list[tuple[str, str]] = None) -> InlineKeyboardMarkup:
    """Inline-кнопки для экспорта расписания на день."""
    buttons = [
        [InlineKeyboardButton(
            text="🍏 Добавить всё в календарь (.ics)",
            callback_data=f"export_cal:{target_date_iso}"
        )],
    ]
    if google_links:
        row = []
        for label, url in google_links:
            row.append(InlineKeyboardButton(
                text=f"🤖 Google: {label}",
                url=url
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
            
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def week_calendar_keyboard(monday_iso: str) -> InlineKeyboardMarkup:
    """Inline-кнопки для экспорта расписания на всю неделю."""
    buttons = [
        [InlineKeyboardButton(
            text="📲 Добавить ВСЮ НЕДЕЛЮ в календарь",
            callback_data=f"export_week:{monday_iso}"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Кнопка "О боте" / "Поддержать" ─────────────────────────────────────────

def about_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела 'О боте'."""
    from config import DONATE_LINK
    buttons = [
        [InlineKeyboardButton(
            text="☕️ Поддержать проект (СБП)",
            url=DONATE_LINK
        )],
        [InlineKeyboardButton(
            text="💬 Написать автору",
            url="https://t.me/Ishmametyev"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_panel_keyboard(notify_status: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления уведомлениями в панели администратора."""
    label = "🔔 Уведомления о новых: ВКЛ" if notify_status else "🔕 Уведомления о новых: ВЫКЛ"
    buttons = [
        [InlineKeyboardButton(text=label, callback_data="toggle_notify")],
        [InlineKeyboardButton(text="📢 Рассылка сообщения", callback_data="admin_broadcast")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def broadcast_target_keyboard() -> InlineKeyboardMarkup:
    """Выбор цели для рассылки."""
    buttons = [
        [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="broadcast_target:all")],
        [InlineKeyboardButton(text="🎓 Конкретной группе", callback_data="broadcast_target:group")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
