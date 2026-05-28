# -*- coding: utf-8 -*-
"""
Handlers for MAGPK Schedule Telegram Bot.
Full redesign with calendar export and caching.
"""

from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from keyboards import (
    main_menu,
    group_prefix_keyboard,
    groups_by_prefix_keyboard,
    days_keyboard,
    calendar_keyboard,
    week_calendar_keyboard,
    about_keyboard,
    admin_panel_keyboard,
    settings_keyboard,
)
from parser import (
    fetch_schedule,
    fetch_schedule_data,
    fetch_week_schedule,
    cache_stats,
)
import asyncio
from calendar_export import generate_ics_for_day, generate_ics, get_google_calendar_lesson_links
from database import (
    get_user_group, 
    set_user_group, 
    update_user_activity, 
    get_user_interface, 
    set_user_interface
)

router = Router()

async def notify_admins_about_new_user(bot, user_id: int, username: str | None, first_name: str | None, last_name: str | None):
    from database import get_admin_settings
    settings = get_admin_settings()
    if not settings.get("notify_new_users", True):
        return
        
    from config import ADMIN_IDS
    username_str = f"@{username}" if username else "нет"
    name_str = f"{first_name or ''} {last_name or ''}".strip() or "Пользователь"
    text = (
        f"🔔 *Новый пользователь!*\n\n"
        f"👤 Имя: *{name_str}*\n"
        f"🆔 ID: `{user_id}`\n"
        f"🔗 Аккаунт: {username_str}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode="Markdown")
        except Exception:
            pass

def track_user(message: Message):
    uid = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    is_new = update_user_activity(uid, username, first_name, last_name)
    if is_new:
        asyncio.create_task(notify_admins_about_new_user(message.bot, uid, username, first_name, last_name))

def track_callback(call: CallbackQuery):
    uid = call.from_user.id
    username = call.from_user.username
    first_name = call.from_user.first_name
    last_name = call.from_user.last_name
    is_new = update_user_activity(uid, username, first_name, last_name)
    if is_new:
        asyncio.create_task(notify_admins_about_new_user(call.message.bot, uid, username, first_name, last_name))

# ===================================================================
#  TEXTS
# ===================================================================

WELCOME_NEW = (
    "👋 *Привет!*\n\n"
    "Я — бот расписания *МАГПК*.\n"
    "Покажу расписание занятий быстро и удобно! 🚀\n\n"
    "🤖 *Версия бота: 2.4*\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🎓 *Для начала выбери свою группу:*"
)

WELCOME_BACK = (
    "👋 *С возвращением!*\n\n"
    "👥 Группа: *{group}*\n"
    "🤖 *Версия бота: 2.4*\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Выбирай, что посмотреть 👇"
)

CHOOSE_PREFIX = (
    "\U0001f393 *\u0412\u044b\u0431\u043e\u0440 \u0433\u0440\u0443\u043f\u043f\u044b*\n\n"
    "\u041d\u0430\u0436\u043c\u0438 \u043d\u0430 *\u043f\u0435\u0440\u0432\u044b\u0435 \u0431\u0443\u043a\u0432\u044b* \u0441\u0432\u043e\u0435\u0439 \u0433\u0440\u0443\u043f\u043f\u044b \U0001f447"
)

CHOOSE_GROUP = (
    "🎓 *Группы на «{prefix}»:*\n\n"
    "Выберите свою группу 👇"
)

GROUP_SET = (
    "\u2705 *\u0413\u0440\u0443\u043f\u043f\u0430 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u0430!*\n\n"
    "\U0001f465 \u0422\u0432\u043e\u044f \u0433\u0440\u0443\u043f\u043f\u0430: *{group}*\n\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "\u0422\u0435\u043f\u0435\u0440\u044c \u043c\u043e\u0436\u0435\u0448\u044c \u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435! \U0001f447"
)

NO_GROUP = (
    "\u26a0\ufe0f *\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0432\u044b\u0431\u0435\u0440\u0438 \u0433\u0440\u0443\u043f\u043f\u0443!*\n\n"
    "\u041d\u0430\u0436\u043c\u0438 \U0001f393 *\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0433\u0440\u0443\u043f\u043f\u0443* \U0001f447"
)

LOADING = "\u23f3 \u0417\u0430\u0433\u0440\u0443\u0436\u0430\u044e \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435..."

ABOUT_TEXT = (
    "┌─────────────────────────────┐\n"
    "  ℹ️  *О боте МАГПК Расписание*\n"
    "└─────────────────────────────┘\n\n"
    "📱 Бот показывает расписание занятий\n"
    "Магнитогорского политехнического\n"
    "колледжа — быстро и удобно.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📊 *Возможности:*\n"
    "  • Расписание на сегодня / завтра\n"
    "  • Расписание на всю неделю\n"
    "  • 📲 Экспорт в календарь (iOS/Android)\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🎉 *Последнее обновление (v2.4):*\n"
    "  • Исправлены ошибки импорта календаря (.ics файл теперь полностью рабочий).\n"
    "  • Раздельные кнопки добавления каждой пары для Google Календаря.\n"
    "  • Возможность задать/сохранить группу, просто написав её имя в чат.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "👨‍💻 *Разработчик:* @Ishmametyev\n\n"
    "⚠️ *Дисклеймер:*\n"
    "Это _неофициальный_ бот. Данные берутся\n"
    "с сайта [magpk.ru](https://magpk.ru) в реальном времени.\n"
    "Автор не несёт ответственности за\n"
    "точность расписания.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Версия 2.4 • 2026"
)

HELP_TEXT = (
    "\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510\n"
    "  \U0001f4d6  *\u0421\u043f\u0440\u0430\u0432\u043a\u0430*\n"
    "\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518\n\n"
    "*\u041a\u043e\u043c\u0430\u043d\u0434\u044b:*\n"
    "/start \u2014 \u041d\u0430\u0447\u0430\u043b\u043e \u0440\u0430\u0431\u043e\u0442\u044b\n"
    "/today \u2014 \u0420\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043d\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f\n"
    "/tomorrow \u2014 \u0420\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430\n"
    "/week \u2014 \u0420\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043d\u0430 \u043d\u0435\u0434\u0435\u043b\u044e\n"
    "/group \u2014 \u0421\u043c\u0435\u043d\u0438\u0442\u044c \u0433\u0440\u0443\u043f\u043f\u0443\n"
    "/about \u2014 \u041e \u0431\u043e\u0442\u0435 \u0438 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430\n"
    "/help \u2014 \u042d\u0442\u0430 \u0441\u043f\u0440\u0430\u0432\u043a\u0430\n\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
    "\U0001f4f2 \u041f\u043e\u0441\u043b\u0435 \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u0438\u044f \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u044f \u043d\u0430\u0436\u043c\u0438\n"
    "*\u00ab\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0432 \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044c\u00bb* \u0447\u0442\u043e\u0431\u044b\n"
    "\u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043f\u0430\u0440\u044b \u0432 \u0441\u0432\u043e\u0439 \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044c!"
)


# ===================================================================
#  /start
# ===================================================================

@router.message(CommandStart())
async def cmd_start(message: Message):
    track_user(message)
    uid = message.from_user.id
    group = get_user_group(uid)
    interface = get_user_interface(uid)
    if group:
        await message.answer(
            WELCOME_BACK.format(group=group),
            parse_mode="Markdown",
            reply_markup=main_menu(has_group=True, user_id=uid, interface=interface),
        )
    else:
        await message.answer(
            WELCOME_NEW,
            parse_mode="Markdown",
            reply_markup=main_menu(has_group=False, user_id=uid, interface=interface),
        )


# ===================================================================
#  Settings
# ===================================================================

@router.message(F.text == "⚙️ Настройки")
@router.message(Command("settings"))
async def cmd_settings(message: Message):
    track_user(message)
    uid = message.from_user.id
    interface = get_user_interface(uid)
    await message.answer(
        "⚙️ *Настройки бота*\n\n"
        "Здесь вы можете изменить стиль интерфейса или сменить группу.",
        parse_mode="Markdown",
        reply_markup=settings_keyboard(interface)
    )

@router.callback_query(F.data == "toggle_interface")
async def on_toggle_interface(call: CallbackQuery):
    track_callback(call)
    uid = call.from_user.id
    current = get_user_interface(uid)
    new_interface = "compact" if current == "full" else "full"
    set_user_interface(uid, new_interface)
    
    await call.message.edit_reply_markup(reply_markup=settings_keyboard(new_interface))
    
    group = get_user_group(uid)
    await call.message.answer(
        f"✅ Интерфейс изменен на *{'Компактный' if new_interface == 'compact' else 'Полный'}*!",
        parse_mode="Markdown",
        reply_markup=main_menu(has_group=bool(group), user_id=uid, interface=new_interface)
    )
    await call.answer()

@router.callback_query(F.data == "change_group_inline")
async def on_change_group_inline(call: CallbackQuery):
    track_callback(call)
    await call.message.answer(
        CHOOSE_PREFIX,
        parse_mode="Markdown",
        reply_markup=group_prefix_keyboard(),
    )
    await call.answer()

@router.callback_query(F.data == "about_inline")
async def on_about_inline(call: CallbackQuery):
    track_callback(call)
    await call.message.answer(
        ABOUT_TEXT,
        parse_mode="Markdown",
        reply_markup=about_keyboard(),
        disable_web_page_preview=True,
    )
    await call.answer()

@router.callback_query(F.data == "choose_day_inline")
async def on_choose_day_inline(call: CallbackQuery):
    track_callback(call)
    await call.message.answer(
        "📅 *Выберите день:*",
        parse_mode="Markdown",
        reply_markup=days_keyboard(),
    )
    await call.answer()


# ===================================================================
#  /help
# ===================================================================

@router.message(Command("help"))
async def cmd_help(message: Message):
    track_user(message)
    await message.answer(HELP_TEXT, parse_mode="Markdown", disable_web_page_preview=True)


# ===================================================================
#  /about
# ===================================================================

@router.message(Command("about"))
@router.message(Command("support"))
@router.message(F.text == "\u2139\ufe0f \u041e \u0431\u043e\u0442\u0435")
async def cmd_about(message: Message):
    track_user(message)
    await message.answer(
        ABOUT_TEXT,
        parse_mode="Markdown",
        reply_markup=about_keyboard(),
        disable_web_page_preview=True,
    )


# ===================================================================
#  Group selection
# ===================================================================

@router.message(F.text.in_(["\U0001f393 \u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0433\u0440\u0443\u043f\u043f\u0443", "\U0001f504 \u0421\u043c\u0435\u043d\u0438\u0442\u044c \u0433\u0440\u0443\u043f\u043f\u0443"]))
@router.message(Command("group"))
async def choose_group(message: Message):
    track_user(message)
    await message.answer(
        CHOOSE_PREFIX,
        parse_mode="Markdown",
        reply_markup=group_prefix_keyboard(),
    )


@router.callback_query(F.data.startswith("prefix:"))
async def on_prefix(call: CallbackQuery):
    track_callback(call)
    prefix = call.data.split(":", 1)[1]
    await call.message.edit_text(
        CHOOSE_GROUP.format(prefix=prefix),
        parse_mode="Markdown",
        reply_markup=groups_by_prefix_keyboard(prefix),
    )


@router.callback_query(F.data == "back_prefix")
async def on_back_prefix(call: CallbackQuery):
    track_callback(call)
    await call.message.edit_text(
        CHOOSE_PREFIX,
        parse_mode="Markdown",
        reply_markup=group_prefix_keyboard(),
    )


@router.callback_query(F.data.startswith("setgroup:"))
async def on_set_group(call: CallbackQuery):
    track_callback(call)
    group = call.data.split(":", 1)[1]
    uid = call.from_user.id
    set_user_group(uid, group)
    interface = get_user_interface(uid)
    await call.message.delete()
    await call.message.answer(
        GROUP_SET.format(group=group),
        parse_mode="Markdown",
        reply_markup=main_menu(has_group=True, user_id=uid, interface=interface),
    )


# ===================================================================
#  Schedule today
# ===================================================================

@router.message(F.text == "\U0001f4c5 \u0421\u0435\u0433\u043e\u0434\u043d\u044f")
@router.message(Command("today"))
async def schedule_today(message: Message):
    track_user(message)
    uid = message.from_user.id
    group = get_user_group(uid)
    interface = get_user_interface(uid)
    if not group:
        await message.answer(NO_GROUP, parse_mode="Markdown",
                             reply_markup=main_menu(has_group=False, user_id=uid, interface=interface))
        return

    msg = await message.answer(LOADING)
    today = date.today()
    text = await fetch_schedule(group, today)
    lessons = await fetch_schedule_data(group, today)
    g_links = get_google_calendar_lesson_links(group, today, lessons)
    
    await msg.edit_text(text, parse_mode="Markdown",
                        disable_web_page_preview=True,
                        reply_markup=calendar_keyboard(today.isoformat(), g_links))


# ===================================================================
#  Schedule tomorrow
# ===================================================================

@router.message(F.text == "\U0001f4c6 \u0417\u0430\u0432\u0442\u0440\u0430")
@router.message(Command("tomorrow"))
async def schedule_tomorrow(message: Message):
    track_user(message)
    uid = message.from_user.id
    group = get_user_group(uid)
    interface = get_user_interface(uid)
    if not group:
        await message.answer(NO_GROUP, parse_mode="Markdown",
                             reply_markup=main_menu(has_group=False, user_id=uid, interface=interface))
        return

    msg = await message.answer(LOADING)
    tomorrow = date.today() + timedelta(days=1)
    text = await fetch_schedule(group, tomorrow)
    lessons = await fetch_schedule_data(group, tomorrow)
    g_links = get_google_calendar_lesson_links(group, tomorrow, lessons)
    
    await msg.edit_text(text, parse_mode="Markdown",
                        disable_web_page_preview=True,
                        reply_markup=calendar_keyboard(tomorrow.isoformat(), g_links))


# ===================================================================
#  Schedule week
# ===================================================================

@router.message(F.text == "\U0001f5d3 \u041d\u0435\u0434\u0435\u043b\u044f")
@router.message(Command("week"))
async def schedule_week(message: Message):
    track_user(message)
    uid = message.from_user.id
    group = get_user_group(uid)
    interface = get_user_interface(uid)
    if not group:
        await message.answer(NO_GROUP, parse_mode="Markdown",
                             reply_markup=main_menu(has_group=False, user_id=uid, interface=interface))
        return

    msg = await message.answer("\u23f3 \u0417\u0430\u0433\u0440\u0443\u0436\u0430\u044e \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043d\u0430 \u043d\u0435\u0434\u0435\u043b\u044e...\n\u042d\u0442\u043e \u0437\u0430\u0439\u043c\u0451\u0442 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0441\u0435\u043a\u0443\u043d\u0434 \u23f1")

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    days_texts = await fetch_week_schedule(group, monday)

    await msg.delete()
    for text in days_texts:
        await message.answer(text, parse_mode="Markdown",
                             disable_web_page_preview=True)

    # One button to add the ENTIRE week at once
    await message.answer(
        "\U0001f4c5 *\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0432 \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044c?*\n"
        "\u041d\u0430\u0436\u043c\u0438 \u043a\u043d\u043e\u043f\u043a\u0443 \u2014 \u0432\u0441\u0435 \u043f\u0430\u0440\u044b \u043d\u0435\u0434\u0435\u043b\u0438 \u0434\u043e\u0431\u0430\u0432\u044f\u0442\u0441\u044f \u0441\u0440\u0430\u0437\u0443!",
        parse_mode="Markdown",
        reply_markup=week_calendar_keyboard(monday.isoformat()),
    )



# ===================================================================
#  Choose specific day
# ===================================================================

@router.message(F.text == "\U0001f4cb \u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0434\u0435\u043d\u044c")
async def choose_day(message: Message):
    track_user(message)
    uid = message.from_user.id
    group = get_user_group(uid)
    interface = get_user_interface(uid)
    if not group:
        await message.answer(NO_GROUP, parse_mode="Markdown",
                             reply_markup=main_menu(has_group=False, user_id=uid, interface=interface))
        return

    await message.answer(
        "\U0001f4cb *\u0412\u044b\u0431\u0435\u0440\u0438 \u0434\u0435\u043d\u044c:*",
        parse_mode="Markdown",
        reply_markup=days_keyboard(),
    )


@router.callback_query(F.data.startswith("day:"))
async def on_day_select(call: CallbackQuery):
    track_callback(call)
    date_str = call.data.split(":", 1)[1]
    uid = call.from_user.id
    group = get_user_group(uid)
    if not group:
        await call.answer("\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0432\u044b\u0431\u0435\u0440\u0438 \u0433\u0440\u0443\u043f\u043f\u0443!", show_alert=True)
        return

    await call.message.edit_text(LOADING)
    target_date = date.fromisoformat(date_str)
    text = await fetch_schedule(group, target_date)
    lessons = await fetch_schedule_data(group, target_date)
    g_links = get_google_calendar_lesson_links(group, target_date, lessons)
    await call.message.edit_text(text, parse_mode="Markdown",
                                 disable_web_page_preview=True,
                                 reply_markup=calendar_keyboard(target_date.isoformat(), g_links))


# ===================================================================
#  Calendar export (.ics)
# ===================================================================

@router.callback_query(F.data.startswith("export_cal:"))
async def on_export_calendar(call: CallbackQuery):
    track_callback(call)
    date_str = call.data.split(":", 1)[1]
    uid = call.from_user.id
    group = get_user_group(uid)

    if not group:
        await call.answer("\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0432\u044b\u0431\u0435\u0440\u0438 \u0433\u0440\u0443\u043f\u043f\u0443!", show_alert=True)
        return

    target_date = date.fromisoformat(date_str)

    # Data from cache if already loaded!
    lessons = await fetch_schedule_data(group, target_date)

    if not lessons:
        await call.answer("\U0001f4ed \u041d\u0435\u0442 \u0437\u0430\u043d\u044f\u0442\u0438\u0439 \u0434\u043b\u044f \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430!", show_alert=True)
        return

    filepath = generate_ics_for_day(group, target_date, lessons)

    if not filepath:
        await call.answer("\u274c \u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u0444\u0430\u0439\u043b", show_alert=True)
        return

    await call.answer("\U0001f4f2 \u0421\u043e\u0437\u0434\u0430\u044e \u0444\u0430\u0439\u043b \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044f...")

    doc = FSInputFile(filepath, filename=f"\u0420\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435_{group}_{date_str}.ics")
    from config import WEEKDAYS_RU
    day_name = WEEKDAYS_RU[target_date.weekday()]
    date_fmt = target_date.strftime("%d.%m.%Y")
    count = len(lessons)
    word = "\u043f\u0430\u0440\u0430" if count == 1 else ("\u043f\u0430\u0440\u044b" if 2 <= count <= 4 else "\u043f\u0430\u0440")

    caption = (
        f"\U0001f4f2 *\u0420\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0434\u043b\u044f \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044f*\n\n"
        f"\U0001f465 {group}  \u2022  {day_name}, {date_fmt}\n"
        f"\U0001f4ca {count} {word}\n\n"
        f"_\u041e\u0442\u043a\u0440\u043e\u0439 \u0444\u0430\u0439\u043b \u2014 \u043e\u043d \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438\n"
        f"\u0434\u043e\u0431\u0430\u0432\u0438\u0442\u0441\u044f \u0432 \u0442\u0432\u043e\u0439 \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044c!_\n\n"
        f"\u2705 \u0420\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u043d\u0430 iOS, Android, Windows"
    )

    await call.message.answer_document(
        doc,
        caption=caption,
        parse_mode="Markdown",
    )

    import os
    try:
        os.remove(filepath)
    except OSError:
        pass


@router.callback_query(F.data.startswith("export_week:"))
async def on_export_week(call: CallbackQuery):
    track_callback(call)
    monday_str = call.data.split(":", 1)[1]
    uid = call.from_user.id
    group = get_user_group(uid)

    if not group:
        await call.answer("Сначала выбери группу!", show_alert=True)
        return

    monday = date.fromisoformat(monday_str)
    await call.answer("🗓 Формирую календарь на неделю...")

    week_data = []
    for i in range(6):  # Пн-Сб
        target_date = monday + timedelta(days=i)
        lessons = await fetch_schedule_data(group, target_date)
        if lessons:
            week_data.append((target_date, lessons))

    if not week_data:
        await call.answer("📭 Нет занятий на этой неделе!", show_alert=True)
        return

    filepath = generate_ics(group, week_data, "week")

    if not filepath:
        await call.answer("❌ Не удалось создать файл", show_alert=True)
        return

    doc = FSInputFile(filepath, filename=f"Расписание_{group}_неделя.ics")
    
    caption = (
        f"🗓 *Расписание на неделю для календаря*\n\n"
        f"👥 Группа: *{group}*\n"
        f"📅 С {monday.strftime('%d.%m')} по {(monday + timedelta(days=5)).strftime('%d.%m')}\n\n"
        f"_Открой файл — все пары недели добавятся в твой календарь сразу!_"
    )

    await call.message.answer_document(
        doc,
        caption=caption,
        parse_mode="Markdown",
    )

    import os
    try:
        os.remove(filepath)
    except OSError:
        pass


# ===================================================================
#  Admin panel / FSM Authentication
# ===================================================================

class AdminStates(StatesGroup):
    waiting_for_password = State()

@router.message(Command("cancel"))
@router.message(F.text.lower() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    track_user(message)
    current_state = await state.get_state()
    if current_state is None:
        return
        
    state_data = await state.get_data()
    prompt_msg_id = state_data.get("prompt_msg_id")
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception:
        pass
        
    # Удаляем сообщение с запросом пароля
    if prompt_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
        except Exception:
            pass
            
    await state.clear()
    uid = message.from_user.id
    group = get_user_group(uid)
    interface = get_user_interface(uid)
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=main_menu(has_group=bool(group), user_id=uid, interface=interface)
    )

@router.message(F.text == "⚙️ Панель администратора")
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    track_user(message)
    from config import ADMIN_IDS
    uid = message.from_user.id
    
    if uid not in ADMIN_IDS:
        await message.answer("❌ Доступ ограничен.")
        return

    # Удаляем команду администратора для чистоты чата
    try:
        await message.delete()
    except Exception:
        pass

    await state.set_state(AdminStates.waiting_for_password)
    from aiogram.types import ReplyKeyboardRemove
    sent_msg = await message.answer(
        "🔑 Введите секретный пароль доступа (или отправьте *Отмена* для отмены):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    # Сохраняем ID сообщения с приглашением
    await state.update_data(prompt_msg_id=sent_msg.message_id)

@router.message(AdminStates.waiting_for_password)
async def check_admin_password(message: Message, state: FSMContext):
    track_user(message)
    from config import ADMIN_PASSWORD
    
    # Сразу удаляем сообщение пользователя с паролем для конфиденциальности
    try:
        await message.delete()
    except Exception:
        pass
        
    password_entered = message.text.strip() if message.text else ""
    
    # Получаем ID предыдущего сообщения-приглашения
    state_data = await state.get_data()
    prompt_msg_id = state_data.get("prompt_msg_id")
    
    if password_entered == ADMIN_PASSWORD:
        await state.clear()
        
        # Удаляем сообщение с просьбой ввести пароль
        if prompt_msg_id:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
            except Exception:
                pass
                
        from database import get_admin_stats, generate_users_report, get_admin_settings
        
        stats_text = get_admin_stats()
        report_file = generate_users_report()
        
        uid = message.from_user.id
        group = get_user_group(uid)
        interface = get_user_interface(uid)
        
        settings = get_admin_settings()
        notify_status = settings.get("notify_new_users", True)
        
        await message.answer(
            stats_text, 
            parse_mode="Markdown", 
            reply_markup=admin_panel_keyboard(notify_status)
        )
        
        doc = FSInputFile(report_file, filename="users_report.xlsx")
        await message.answer_document(
            doc, 
            caption="📋 Полный отчет о пользователях бота",
            reply_markup=main_menu(has_group=bool(group), user_id=uid, interface=interface)
        )
        
        import os
        try:
            os.remove(report_file)
        except OSError:
            pass
    else:
        # Если пароль неверный, удаляем старое приглашение и присылаем новое
        if prompt_msg_id:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
            except Exception:
                pass
                
        sent_msg = await message.answer(
            "❌ Неверный пароль. Попробуйте еще раз или напишите *Отмена*:"
        )
        await state.update_data(prompt_msg_id=sent_msg.message_id)


@router.callback_query(F.data == "toggle_notify")
async def on_toggle_notify(call: CallbackQuery):
    track_callback(call)
    from database import get_admin_settings, set_admin_settings
    
    settings = get_admin_settings()
    current_status = settings.get("notify_new_users", True)
    new_status = not current_status
    settings["notify_new_users"] = new_status
    set_admin_settings(settings)
    
    from keyboards import admin_panel_keyboard
    await call.message.edit_reply_markup(reply_markup=admin_panel_keyboard(new_status))
    await call.answer(f"Уведомления {'включены' if new_status else 'выключены'}!", show_alert=False)

# ===================================================================
#  Unknown message
# ===================================================================

@router.message()
async def unknown(message: Message):
    track_user(message)
    if message.text:
        text = message.text.strip().upper()
        from config import ALL_GROUPS
        matched_group = None
        for g in ALL_GROUPS:
            if g.upper() == text:
                matched_group = g
                break
        
        if matched_group:
            uid = message.from_user.id
            set_user_group(uid, matched_group)
            interface = get_user_interface(uid)
            await message.answer(
                GROUP_SET.format(group=matched_group),
                parse_mode="Markdown",
                reply_markup=main_menu(has_group=True, user_id=uid, interface=interface),
            )
            return

    uid = message.from_user.id
    group = get_user_group(uid)
    interface = get_user_interface(uid)
    await message.answer(
        "🤔 Не понял. Если ты хотел выбрать группу, введи её название (например, *ТМ9-23-2*).\nИли используй кнопки меню /help.",
        parse_mode="Markdown",
        reply_markup=main_menu(has_group=bool(group), user_id=uid, interface=interface),
    )
