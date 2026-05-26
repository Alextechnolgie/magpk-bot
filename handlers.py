from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from datetime import date, timedelta

from database import get_user_group, set_user_group
from keyboards import (
    main_menu,
    group_prefix_keyboard,
    groups_by_prefix_keyboard,
    days_keyboard,
)
from parser import fetch_schedule, fetch_week_schedule

router = Router()

# ════════════════════════════════════════════════════════════════════════════
#  Тексты с дизайном
# ════════════════════════════════════════════════════════════════════════════

WELCOME_NEW = """
🏫 *Привет! Я бот Магнитогорского Политеха* 

Я помогу тебе быстро узнать расписание занятий прямо в Telegram — без входа на сайт.

━━━━━━━━━━━━━━━━━━━━━
📌 *Для начала выбери свою группу:*
"""

WELCOME_BACK = """
🏫 *Привет, снова ты!*

Твоя группа: *{group}*

━━━━━━━━━━━━━━━━━━━━━
Что смотрим? 👇
"""

CHOOSE_PREFIX = """
🔍 *Выбор группы*

Нажми на *первые буквы* названия своей группы 👇
"""

CHOOSE_GROUP = """
📋 *Группы начинающиеся на «{prefix}»:*

Выбери свою группу 👇
"""

GROUP_SET = """
✅ *Группа сохранена!*

Твоя группа: *{group}*

━━━━━━━━━━━━━━━━━━━━━
Теперь выбери что хочешь посмотреть 👇
"""

NO_GROUP = """
⚠️ *Сначала выбери группу!*

Нажми кнопку ниже 👇
"""

LOADING = "⏳ Загружаю расписание..."


# ════════════════════════════════════════════════════════════════════════════
#  /start
# ════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    group = get_user_group(uid)
    if group:
        await message.answer(
            WELCOME_BACK.format(group=group),
            parse_mode="Markdown",
            reply_markup=main_menu(has_group=True),
        )
    else:
        await message.answer(
            WELCOME_NEW,
            parse_mode="Markdown",
            reply_markup=main_menu(has_group=False),
        )


# ════════════════════════════════════════════════════════════════════════════
#  /help
# ════════════════════════════════════════════════════════════════════════════

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = """
ℹ️ *Справка по боту*

*Доступные команды:*
/start — Главное меню
/today — Расписание на сегодня
/tomorrow — Расписание на завтра
/week — Расписание на неделю
/group — Сменить группу
/help — Эта справка

━━━━━━━━━━━━━━━━━━━━━
*Данные берутся с официального сайта:*
[magpk.ru](https://magpk.ru/studentu/raspisanie-zanyatij)

Расписание обновляется в реальном времени 🔄
"""
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)


# ════════════════════════════════════════════════════════════════════════════
#  Выбор группы
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text.in_(["🔍 Выбрать группу", "🔍 Сменить группу"]))
@router.message(Command("group"))
async def choose_group(message: Message):
    await message.answer(
        CHOOSE_PREFIX,
        parse_mode="Markdown",
        reply_markup=group_prefix_keyboard(),
    )


@router.callback_query(F.data.startswith("prefix:"))
async def on_prefix(call: CallbackQuery):
    prefix = call.data.split(":", 1)[1]
    await call.message.edit_text(
        CHOOSE_GROUP.format(prefix=prefix),
        parse_mode="Markdown",
        reply_markup=groups_by_prefix_keyboard(prefix),
    )


@router.callback_query(F.data == "back_prefix")
async def on_back_prefix(call: CallbackQuery):
    await call.message.edit_text(
        CHOOSE_PREFIX,
        parse_mode="Markdown",
        reply_markup=group_prefix_keyboard(),
    )


@router.callback_query(F.data.startswith("setgroup:"))
async def on_set_group(call: CallbackQuery):
    group = call.data.split(":", 1)[1]
    uid = call.from_user.id
    set_user_group(uid, group)
    await call.message.delete()
    await call.message.answer(
        GROUP_SET.format(group=group),
        parse_mode="Markdown",
        reply_markup=main_menu(has_group=True),
    )


# ════════════════════════════════════════════════════════════════════════════
#  Расписание на сегодня
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "📅 Расписание на сегодня")
@router.message(Command("today"))
async def schedule_today(message: Message):
    uid = message.from_user.id
    group = get_user_group(uid)
    if not group:
        await message.answer(NO_GROUP, parse_mode="Markdown",
                             reply_markup=main_menu(has_group=False))
        return

    msg = await message.answer(LOADING)
    text = await fetch_schedule(group, date.today())
    await msg.edit_text(text, parse_mode="Markdown",
                        disable_web_page_preview=True)


# ════════════════════════════════════════════════════════════════════════════
#  Расписание на завтра
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "📆 Расписание на завтра")
@router.message(Command("tomorrow"))
async def schedule_tomorrow(message: Message):
    uid = message.from_user.id
    group = get_user_group(uid)
    if not group:
        await message.answer(NO_GROUP, parse_mode="Markdown",
                             reply_markup=main_menu(has_group=False))
        return

    msg = await message.answer(LOADING)
    tomorrow = date.today() + timedelta(days=1)
    text = await fetch_schedule(group, tomorrow)
    await msg.edit_text(text, parse_mode="Markdown",
                        disable_web_page_preview=True)


# ════════════════════════════════════════════════════════════════════════════
#  Расписание на неделю
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "🗓 Расписание на неделю")
@router.message(Command("week"))
async def schedule_week(message: Message):
    uid = message.from_user.id
    group = get_user_group(uid)
    if not group:
        await message.answer(NO_GROUP, parse_mode="Markdown",
                             reply_markup=main_menu(has_group=False))
        return

    msg = await message.answer("⏳ Загружаю расписание на неделю...\nЭто займёт несколько секунд 🕐")

    today = date.today()
    # Начало текущей недели (понедельник)
    monday = today - timedelta(days=today.weekday())
    days_texts = await fetch_week_schedule(group, monday)

    await msg.delete()
    for text in days_texts:
        await message.answer(text, parse_mode="Markdown",
                             disable_web_page_preview=True)


# ════════════════════════════════════════════════════════════════════════════
#  Выбор конкретного дня
# ════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("day:"))
async def on_day_select(call: CallbackQuery):
    date_str = call.data.split(":", 1)[1]
    uid = call.from_user.id
    group = get_user_group(uid)
    if not group:
        await call.answer("Сначала выбери группу!", show_alert=True)
        return

    await call.message.edit_text("⏳ Загружаю расписание...")
    target_date = date.fromisoformat(date_str)
    text = await fetch_schedule(group, target_date)
    await call.message.edit_text(text, parse_mode="Markdown",
                                 disable_web_page_preview=True)


# ════════════════════════════════════════════════════════════════════════════
#  Неизвестные сообщения
# ════════════════════════════════════════════════════════════════════════════

@router.message()
async def unknown(message: Message):
    uid = message.from_user.id
    group = get_user_group(uid)
    await message.answer(
        "🤔 Не понял команду. Используй кнопки меню или напиши /help",
        reply_markup=main_menu(has_group=bool(group)),
    )
