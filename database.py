# -*- coding: utf-8 -*-
"""
Database module for MAGPK Bot.
Migrated from users.json file to PostgreSQL (on Railway) with SQLite local fallback.
Supports automatic table initialization and migration of existing users.json data.
"""

import json
import os
import tempfile
import base64
import sqlite3
from datetime import datetime, timedelta, date
from config import get_mgn_now, get_mgn_today

# Попробуем импортировать psycopg2 для Postgres
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Считываем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Если URL задан и библиотека psycopg2 установлена, используем PostgreSQL
USE_POSTGRES = bool(DATABASE_URL) and HAS_PSYCOPG2

if not HAS_PSYCOPG2 and DATABASE_URL:
    print("⚠️ DATABASE_URL задана, но библиотека psycopg2-binary не установлена. Используем локальный SQLite.")

# -----------------------------------------------------------------------------
# Подключение и управление соединениями
# -----------------------------------------------------------------------------

def get_connection():
    """Создает новое соединение с базой данных (Postgres или SQLite)."""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        # SQLite
        db_dir = "/data" if os.path.isdir("/data") else "."
        db_path = os.path.join(db_dir, "users.db")
        conn = sqlite3.connect(db_path)
        # Включаем поддержку внешних ключей в SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn


def execute_query(query, params=None, fetch=None):
    """Выполняет SQL-запрос, безопасно управляя соединением и курсором."""
    # Если SQLite, конвертируем плейсхолдеры %s в ?
    if not USE_POSTGRES:
        query = query.replace("%s", "?")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        if fetch == "one":
            result = cur.fetchone()
        elif fetch == "all":
            result = cur.fetchall()
        else:
            result = None
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка SQL ({query}): {e}")
        raise e
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# Шифрование XOR (для миграции старого users.json)
# -----------------------------------------------------------------------------

def _xor_decipher(encoded_str: str, key: str) -> str:
    key_bytes = key.encode("utf-8")
    xor_bytes = base64.b64decode(encoded_str.encode("utf-8"))
    data_bytes = bytearray(d ^ key_bytes[i % len(key_bytes)] for i, d in enumerate(xor_bytes))
    return data_bytes.decode("utf-8")

# -----------------------------------------------------------------------------
# Инициализация схемы и Миграция
# -----------------------------------------------------------------------------

def init_db():
    """Создает таблицы базы данных при первом запуске."""
    if USE_POSTGRES:
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                group_name VARCHAR(50),
                username VARCHAR(100),
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                interface VARCHAR(20) DEFAULT 'full',
                joined_at TIMESTAMP,
                last_seen TIMESTAMP,
                invited_by BIGINT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS promos (
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                promo_id VARCHAR(100),
                dismissed BOOLEAN DEFAULT FALSE,
                last_shown_at DATE,
                PRIMARY KEY (user_id, promo_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                time TIMESTAMP,
                action VARCHAR(255)
            );
            """
        ]
    else:
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                group_name TEXT,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                interface TEXT DEFAULT 'full',
                joined_at TIMESTAMP,
                last_seen TIMESTAMP,
                invited_by INTEGER
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS promos (
                user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
                promo_id TEXT,
                dismissed INTEGER DEFAULT 0,
                last_shown_at TEXT,
                PRIMARY KEY (user_id, promo_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                time TIMESTAMP,
                action TEXT
            );
            """
        ]

    try:
        conn = get_connection()
    except Exception as e:
        print(f"❌ Не удалось подключиться к базе данных при инициализации: {e}")
        return

    try:
        cur = conn.cursor()
        for q in queries:
            cur.execute(q)
        conn.commit()
        print(f"✅ База данных успешно инициализирована (Postgres: {USE_POSTGRES})")
    except Exception as e:
        print(f"❌ Ошибка инициализации таблиц: {e}")
    finally:
        conn.close()


def migrate_json_to_db():
    """Переносит данные из старого users.json в SQL базу данных при первом запуске."""
    try:
        # Проверяем, пуста ли таблица users
        res = execute_query("SELECT COUNT(*) FROM users;", fetch="one")
        if res and res[0] > 0:
            return

        db_dir = "/data" if os.path.isdir("/data") else "."
        old_db_file = os.path.join(db_dir, "users.json")
        if not os.path.exists(old_db_file):
            old_db_file = "users.json"

        if not os.path.exists(old_db_file):
            return

        print(f"📦 Найдена старая база {old_db_file}. Запуск миграции...")
        from config import DB_ENCRYPTION_KEY

        with open(old_db_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return

            if content.startswith("{"):
                data = json.loads(content)
            else:
                data = json.loads(_xor_decipher(content, DB_ENCRYPTION_KEY))

        try:
            conn = get_connection()
        except Exception as e:
            print(f"❌ Не удалось подключиться к базе данных при миграции: {e}")
            return
        try:
            cur = conn.cursor()
            
            # Для SQLite / Postgres
            placeholder = "?" if not USE_POSTGRES else "%s"

            for uid_str, info in data.items():
                if uid_str == "__settings__":
                    # Перенос настроек админа
                    val_str = json.dumps(info)
                    cur.execute(f"""
                        INSERT INTO settings (key, value) VALUES ('admin_settings', {placeholder})
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
                    """, (val_str,))
                    continue

                uid = int(uid_str)
                group = None
                joined_at = None
                last_seen = None
                username = None
                first_name = None
                last_name = None
                interface = "full"
                invited_by = None
                promos = {}

                if isinstance(info, dict):
                    group = info.get("group")
                    joined_at = info.get("joined_at")
                    last_seen = info.get("last_seen")
                    username = info.get("username")
                    first_name = info.get("first_name")
                    last_name = info.get("last_name")
                    interface = info.get("interface", "full")
                    invited_by = info.get("invited_by")
                    promos = info.get("promos", {})
                else:
                    group = info

                # Вставка пользователя
                cur.execute(f"""
                    INSERT INTO users (user_id, group_name, username, first_name, last_name, interface, joined_at, last_seen, invited_by)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                    ON CONFLICT (user_id) DO NOTHING;
                """, (uid, group, username, first_name, last_name, interface, joined_at, last_seen, invited_by))

                # Вставка промо для пользователя
                for promo_id, p_info in promos.items():
                    dismissed = False
                    last_shown = None
                    if isinstance(p_info, dict):
                        dismissed = p_info.get("dismissed", False)
                        last_shown = p_info.get("last_shown_at")
                    elif isinstance(p_info, bool):
                        dismissed = p_info

                    cur.execute(f"""
                        INSERT INTO promos (user_id, promo_id, dismissed, last_shown_at)
                        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                        ON CONFLICT (user_id, promo_id) DO NOTHING;
                    """, (uid, promo_id, dismissed, last_shown))

            conn.commit()
            print("✅ Все данные успешно перенесены из JSON в SQL базу!")
            
            # Переименовываем users.json, чтобы больше не запускать миграцию
            try:
                os.rename(old_db_file, old_db_file + ".migrated")
            except Exception:
                pass
        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка миграции SQL: {e}")
        finally:
            conn.close()
    except Exception as e:
        print(f"❌ Ошибка чтения файла миграции: {e}")


# Запускаем инициализацию и миграцию при импорте модуля
try:
    init_db()
    migrate_json_to_db()
except Exception as e:
    print(f"⚠️ Предупреждение: не удалось инициализировать БД при старте: {e}")

# -----------------------------------------------------------------------------
# Google Sheet Sync
# -----------------------------------------------------------------------------

def _sync_user_to_google(user_id: int, info: dict):
    """Отправляет данные пользователя в Google Таблицу в фоновом режиме."""
    from config import GOOGLE_SHEET_URL
    if not GOOGLE_SHEET_URL:
        return
        
    import asyncio
    import aiohttp
    
    async def task():
        payload = {
            "user_id": str(user_id),
            "group": info.get("group"),
            "username": info.get("username"),
            "first_name": info.get("first_name"),
            "last_name": info.get("last_name"),
            "joined_at": info.get("joined_at"),
            "last_seen": info.get("last_seen")
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(GOOGLE_SHEET_URL, json=payload, timeout=10) as resp:
                    await resp.read()
        except Exception:
            pass
            
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(task())
    except RuntimeError:
        pass

# -----------------------------------------------------------------------------
# Методы получения и обновления данных (Пользователи)
# -----------------------------------------------------------------------------

def get_user_group(user_id: int) -> str | None:
    """Возвращает сохранённую группу пользователя."""
    res = execute_query("SELECT group_name FROM users WHERE user_id = %s;", (user_id,), fetch="one")
    return res[0] if res else None


def get_user_interface(user_id: int) -> str:
    """Возвращает тип интерфейса пользователя (по умолчанию 'full')."""
    res = execute_query("SELECT interface FROM users WHERE user_id = %s;", (user_id,), fetch="one")
    return res[0] if res else "full"


def set_user_interface(user_id: int, interface_type: str):
    """Устанавливает тип интерфейса пользователя."""
    now_str = get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    execute_query("""
        INSERT INTO users (user_id, interface, joined_at, last_seen)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET interface = EXCLUDED.interface, last_seen = EXCLUDED.last_seen;
    """, (user_id, interface_type, now_str, now_str))


def set_user_group(user_id: int, group: str):
    """Сохраняет группу пользователя."""
    now_str = get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    execute_query("""
        INSERT INTO users (user_id, group_name, joined_at, last_seen)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET group_name = EXCLUDED.group_name, last_seen = EXCLUDED.last_seen;
    """, (user_id, group, now_str, now_str))
    
    # Получаем полные данные для синхронизации с Google Sheets
    res = execute_query("SELECT username, first_name, last_name, joined_at, last_seen FROM users WHERE user_id = %s;", (user_id,), fetch="one")
    if res:
        username, first_name, last_name, j_at, l_seen = res
        
        def format_dt(dt):
            if isinstance(dt, datetime):
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return str(dt) if dt else None

        info = {
            "group": group,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "joined_at": format_dt(j_at),
            "last_seen": format_dt(l_seen)
        }
        _sync_user_to_google(user_id, info)


def update_user_activity(user_id: int, username: str | None, first_name: str | None, last_name: str | None, referrer_id: int = None) -> bool:
    """Обновляет имя аккаунта и время активности. Возвращает True, если пользователь новый."""
    res = execute_query("SELECT user_id FROM users WHERE user_id = %s;", (user_id,), fetch="one")
    is_new = res is None
    
    now_str = get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    
    if is_new:
        invited_by = referrer_id if (referrer_id and referrer_id != user_id) else None
        execute_query("""
            INSERT INTO users (user_id, username, first_name, last_name, joined_at, last_seen, invited_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (user_id, username, first_name, last_name, now_str, now_str, invited_by))
    else:
        execute_query("""
            UPDATE users SET username = %s, first_name = %s, last_name = %s, last_seen = %s WHERE user_id = %s;
        """, (username, first_name, last_name, now_str, user_id))
        
    # Синхронизация Google Sheets
    res = execute_query("SELECT group_name, joined_at, last_seen, invited_by FROM users WHERE user_id = %s;", (user_id,), fetch="one")
    if res:
        group_name, j_at, l_seen, inv_by = res
        
        def format_dt(dt):
            if isinstance(dt, datetime):
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return str(dt) if dt else None

        info = {
            "group": group_name,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "joined_at": format_dt(j_at),
            "last_seen": format_dt(l_seen)
        }
        _sync_user_to_google(user_id, info)
        
    return is_new

# -----------------------------------------------------------------------------
# Настройки Администратора
# -----------------------------------------------------------------------------

def get_admin_settings() -> dict:
    """Возвращает настройки администратора."""
    res = execute_query("SELECT value FROM settings WHERE key = 'admin_settings';", fetch="one")
    if res:
        try:
            return json.loads(res[0])
        except Exception:
            pass
    return {"notify_new_users": True}


def set_admin_settings(settings: dict):
    """Сохраняет настройки администратора."""
    val_str = json.dumps(settings)
    execute_query("""
        INSERT INTO settings (key, value) VALUES ('admin_settings', %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
    """, (val_str,))

# -----------------------------------------------------------------------------
# Вспомогательные функции дат
# -----------------------------------------------------------------------------

def _parse_datetime(dt_val) -> datetime | None:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    dt_str = str(dt_val)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return None

# -----------------------------------------------------------------------------
# Реферальная система и Промо-акции
# -----------------------------------------------------------------------------

def get_referred_users_count(user_id: int) -> int:
    """Возвращает число приглашенных этим пользователем человек."""
    res = execute_query("SELECT COUNT(*) FROM users WHERE invited_by = %s;", (user_id,), fetch="one")
    return res[0] if res else 0


def is_promo_dismissed(user_id: int, promo_id: str) -> bool:
    """Проверяет, отключил ли пользователь промо навсегда."""
    res = execute_query("SELECT dismissed FROM promos WHERE user_id = %s AND promo_id = %s;", (user_id, promo_id), fetch="one")
    if res:
        return bool(res[0])
    return False


def dismiss_promo(user_id: int, promo_id: str):
    """Скрывает промо навсегда для пользователя."""
    execute_query("""
        INSERT INTO promos (user_id, promo_id, dismissed)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, promo_id) DO UPDATE SET dismissed = EXCLUDED.dismissed;
    """, (user_id, promo_id, True))


def can_show_promo_today(user_id: int, promo_id: str) -> bool:
    """Проверяет, можно ли показать пользователю промо сегодня."""
    res = execute_query("SELECT dismissed, last_shown_at FROM promos WHERE user_id = %s AND promo_id = %s;", (user_id, promo_id), fetch="one")
    if not res:
        return True
        
    dismissed, last_shown = res
    if dismissed:
        return False
        
    if not last_shown:
        return True
        
    today = get_mgn_today()
    if isinstance(last_shown, str):
        return last_shown != today.isoformat()
    else:
        return last_shown != today


def record_promo_show(user_id: int, promo_id: str):
    """Записывает сегодняшнюю дату как дату последнего показа промо."""
    today_str = get_mgn_today().isoformat()
    execute_query("""
        INSERT INTO promos (user_id, promo_id, dismissed, last_shown_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, promo_id) DO UPDATE SET last_shown_at = EXCLUDED.last_shown_at;
    """, (user_id, promo_id, False, today_str))

# -----------------------------------------------------------------------------
# Логирование и Метрики Активности
# -----------------------------------------------------------------------------

def log_activity(user_id: int, action: str):
    """Логирует действие пользователя."""
    now_str = get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    execute_query("INSERT INTO activity_log (user_id, time, action) VALUES (%s, %s, %s);", (user_id, now_str, action))


def get_activity_stats() -> str:
    """Генерирует красивый текстовый отчет активности пользователей."""
    now = get_mgn_now().replace(tzinfo=None)
    today_start = datetime(now.year, now.month, now.day)
    seven_days_ago = today_start - timedelta(days=7)
    
    # Считываем логи за последние 7 дней
    if USE_POSTGRES:
        logs = execute_query("SELECT user_id, time, action FROM activity_log WHERE time >= %s;", (seven_days_ago,), fetch="all")
        total_today_res = execute_query("SELECT COUNT(*), COUNT(DISTINCT user_id) FROM activity_log WHERE time >= %s;", (today_start,), fetch="one")
        total_today, dau = total_today_res if total_today_res else (0, 0)
    else:
        logs = execute_query("SELECT user_id, time, action FROM activity_log WHERE time >= %s;", (seven_days_ago.strftime("%Y-%m-%d %H:%M:%S"),), fetch="all")
        total_today_res = execute_query("SELECT COUNT(*), COUNT(DISTINCT user_id) FROM activity_log WHERE time >= %s;", (today_start.strftime("%Y-%m-%d %H:%M:%S"),), fetch="one")
        total_today, dau = total_today_res if total_today_res else (0, 0)
        
    if not logs:
        return "📊 *Статистика активности:* Нет логов за последние 7 дней."
        
    total_week = len(logs)
    active_users_week = set()
    
    hourly_distribution = [0] * 24
    command_counts = {}
    
    for row in logs:
        uid, time_val, action = row
        active_users_week.add(uid)
        
        dt = time_val
        if isinstance(dt, str):
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            
        hourly_distribution[dt.hour] += 1
        
        cmd = action.split()[0] if action else "unknown"
        if cmd.startswith("cb:"):
            cmd = "кнопка: " + cmd.split(":")[1].split()[0]
        command_counts[cmd] = command_counts.get(cmd, 0) + 1
        
    wau = len(active_users_week)
    
    top_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    commands_str = "\n".join(f"  • `{cmd}`: *{count}* раз" for cmd, count in top_commands)
    
    max_hour_val = max(hourly_distribution) if max(hourly_distribution) > 0 else 1
    chart_lines = []
    for h in range(24):
        val = hourly_distribution[h]
        if val > 0 or (7 <= h <= 22):
            filled = int((val / max_hour_val) * 10)
            bar = "█" * filled + "░" * (10 - filled)
            chart_lines.append(f"`{h:02d}:00` `[{bar}]` *{val}* запр.")
            
    peak_hours = sorted(range(24), key=lambda h: hourly_distribution[h], reverse=True)[:5]
    peak_hours_str = ", ".join(f"{h:02d}:00" for h in peak_hours if hourly_distribution[h] > 0)
    
    lines = [
        "📊 *Анализ активности пользователей:*",
        f"👥 Активно сегодня (DAU): *{dau}* чел. ({total_today} запр.)",
        f"👥 Активно за 7 дней (WAU): *{wau}* чел. ({total_week} запр.)",
        f"🔥 Пиковое время: *{peak_hours_str or 'нет данных'}*",
        "",
        "🔝 *Популярные функции (за 7 дней):*",
        commands_str or "  • Нет данных",
        "",
        "🕒 *Активность по часам (за 7 дней):*",
        *chart_lines
    ]
    return "\n".join(lines)

# -----------------------------------------------------------------------------
# Общая статистика панели администратора
# -----------------------------------------------------------------------------

def get_admin_stats() -> str:
    """Генерирует сводную статистику пользователей с ASCII-графиками."""
    cache = execute_query("SELECT user_id, joined_at, username, first_name, last_name, invited_by FROM users;", fetch="all")
    total_users = len(cache)
    
    now = get_mgn_now().replace(tzinfo=None)
    today_start = datetime(now.year, now.month, now.day)
    seven_days_ago = today_start - timedelta(days=7)
    thirty_days_ago = today_start - timedelta(days=30)
    
    today_count = 0
    week_count = 0
    month_count = 0
    
    referral_counts = {}
    invited_total = 0
    
    for row in cache:
        uid, joined_at, username, first_name, last_name, invited_by = row
        
        if invited_by:
            invited_total += 1
            ref_id_str = str(invited_by)
            referral_counts[ref_id_str] = referral_counts.get(ref_id_str, 0) + 1
            
        dt = joined_at
        if isinstance(dt, str):
            dt = _parse_datetime(dt)
        if dt:
            if dt >= today_start:
                today_count += 1
            if dt >= seven_days_ago:
                week_count += 1
            if dt >= thirty_days_ago:
                month_count += 1
                
    def make_bar(val, max_val):
        if max_val == 0 or val == 0:
            return "░░░░░░░░░░"
        filled = min(10, int(val / max_val * 10))
        return "█" * filled + "░" * (10 - filled)
        
    max_val = max(today_count, week_count, month_count, 1)
    bar_today = make_bar(today_count, max_val)
    bar_week = make_bar(week_count, max_val)
    bar_month = make_bar(month_count, max_val)
    
    top_referrers = sorted(referral_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    top_lines = []
    for idx, (ref_id_str, count) in enumerate(top_referrers, 1):
        ref_info = execute_query("SELECT first_name, last_name, username FROM users WHERE user_id = %s;", (int(ref_id_str),), fetch="one")
        if ref_info:
            first, last, username = ref_info
            name = f"{first or ''} {last or ''}".strip() or "Пользователь"
            user_str = f"{name} (@{username})" if username else name
        else:
            user_str = f"ID {ref_id_str}"
        top_lines.append(f"  {idx}. {user_str} — *{count}* чел.")
        
    lines = [
        "📊 *Статистика пользователей бота:*",
        f"👥 Всего пользователей: *{total_users}*",
        "",
        "📈 *Прирост новых пользователей:*",
        f"📅 За сегодня:  `[{bar_today}]` *{today_count}* чел.",
        f"📅 За 7 дней:   `[{bar_week}]` *{week_count}* чел.",
        f"📅 За 30 дней:  `[{bar_month}]` *{month_count}* чел.",
        "",
        "🤝 *Реферальная статистика:*",
        f"🔗 Приглашено через рефералов: *{invited_total}* чел.",
    ]
    if top_lines:
        lines.append("🏆 *Топ-3 пригласивших:*")
        lines.extend(top_lines)
        
    return "\n".join(lines)

# -----------------------------------------------------------------------------
# Генерация Excel Отчета
# -----------------------------------------------------------------------------

def generate_users_report() -> str:
    """Генерирует многостраничный Excel-отчет о пользователях и активности."""
    cache = execute_query("SELECT user_id, group_name, username, first_name, last_name, interface, joined_at, last_seen, invited_by FROM users;", fetch="all")
    total_users = len(cache)
    
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    
    wb = Workbook()
    
    # Стили
    font_title = Font(name="Calibri", size=16, bold=True, color="1F497D")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=11)
    font_bold = Font(name="Calibri", size=11, bold=True)
    
    fill_header = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    fill_zebra = PatternFill(start_color="F2F5F8", end_color="F2F5F8", fill_type="solid")
    
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    
    border_thin = Side(border_style="thin", color="D9D9D9")
    border_double = Side(border_style="double", color="1F497D")
    
    cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
    header_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_double)

    # -------------------------------------------------------------
    # Лист 1: Пользователи
    # -------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "Пользователи"
    ws1.views.sheetView[0].showGridLines = True
    
    headers1 = [
        "Telegram ID", 
        "Группа", 
        "Telegram Username", 
        "Имя и Фамилия", 
        "Зарегистрирован", 
        "Последняя активность",
        "ID Пригласившего",
        "Пригласил рефералов"
    ]
    
    ws1.merge_cells("A1:H1")
    title_cell = ws1["A1"]
    title_cell.value = "Отчет по пользователям бота МАГПК Расписание"
    title_cell.font = font_title
    title_cell.alignment = align_left
    ws1.row_dimensions[1].height = 40
    
    ws1.merge_cells("A2:H2")
    info_cell = ws1["A2"]
    info_cell.value = f"Всего пользователей: {total_users}  |  Дата генерации: {get_mgn_now().replace(tzinfo=None).strftime('%d.%m.%Y %H:%M:%S')}"
    info_cell.font = Font(name="Calibri", size=11, italic=True)
    info_cell.alignment = align_left
    ws1.row_dimensions[2].height = 20
    
    ws1.row_dimensions[4].height = 28
    for col_num, header in enumerate(headers1, 1):
        cell = ws1.cell(row=4, column=col_num)
        cell.value = header
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = header_border
        
    def format_dt(dt):
        if not dt:
            return "-"
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return str(dt)

    row_num = 5
    for row in cache:
        uid, group, username, first_name, last_name, interface, j_at, l_seen, invited_by = row
        
        name = f"{first_name or ''} {last_name or ''}".strip() or "Пользователь"
        username_str = f"@{username}" if username else "-"
        invited_str = str(invited_by) if invited_by else "-"
        referrals_count = get_referred_users_count(uid)
        
        row_data = [
            str(uid), 
            group or "", 
            username_str, 
            name, 
            format_dt(j_at), 
            format_dt(l_seen), 
            invited_str, 
            referrals_count
        ]
        
        ws1.row_dimensions[row_num].height = 20
        is_even = (row_num % 2 == 0)
        
        for col_num, val in enumerate(row_data, 1):
            cell = ws1.cell(row=row_num, column=col_num)
            cell.value = val
            cell.font = font_data
            cell.border = cell_border
            if is_even:
                cell.fill = fill_zebra
            if col_num in [1, 2, 5, 6, 7, 8]:
                cell.alignment = align_center
            else:
                cell.alignment = align_left
        row_num += 1
        
    for col in ws1.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row in [1, 2]:
                continue
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws1.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # -------------------------------------------------------------
    # Лист 2: Анализ активности
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Анализ активности")
    ws2.views.sheetView[0].showGridLines = True
    
    ws2.merge_cells("A1:D1")
    title_cell2 = ws2["A1"]
    title_cell2.value = "Анализ активности пользователей (за последние 7 дней)"
    title_cell2.font = font_title
    title_cell2.alignment = align_left
    ws2.row_dimensions[1].height = 40
    
    now = get_mgn_now().replace(tzinfo=None)
    today_start = datetime(now.year, now.month, now.day)
    seven_days_ago = today_start - timedelta(days=7)
    
    if USE_POSTGRES:
        logs = execute_query("SELECT user_id, time, action FROM activity_log WHERE time >= %s;", (seven_days_ago,), fetch="all")
        total_today_res = execute_query("SELECT COUNT(*), COUNT(DISTINCT user_id) FROM activity_log WHERE time >= %s;", (today_start,), fetch="one")
        total_today, dau = total_today_res if total_today_res else (0, 0)
    else:
        logs = execute_query("SELECT user_id, time, action FROM activity_log WHERE time >= %s;", (seven_days_ago.strftime("%Y-%m-%d %H:%M:%S"),), fetch="all")
        total_today_res = execute_query("SELECT COUNT(*), COUNT(DISTINCT user_id) FROM activity_log WHERE time >= %s;", (today_start.strftime("%Y-%m-%d %H:%M:%S"),), fetch="one")
        total_today, dau = total_today_res if total_today_res else (0, 0)
        
    total_week = len(logs) if logs else 0
    active_users_week = set()
    hourly_distribution = [0] * 24
    command_counts = {}
    
    if logs:
        for row in logs:
            uid, time_val, action = row
            active_users_week.add(uid)
            
            dt = time_val
            if isinstance(dt, str):
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
                
            hourly_distribution[dt.hour] += 1
            
            cmd = action.split()[0] if action else "unknown"
            if cmd.startswith("cb:"):
                cmd = "кнопка: " + cmd.split(":")[1].split()[0]
            command_counts[cmd] = command_counts.get(cmd, 0) + 1
            
    wau = len(active_users_week)
    
    # Записываем общие метрики
    ws2.cell(row=3, column=1, value="Метрика").font = font_bold
    ws2.cell(row=3, column=2, value="Значение").font = font_bold
    ws2.cell(row=3, column=1).border = header_border
    ws2.cell(row=3, column=2).border = header_border
    
    metrics = [
        ("Активно сегодня (DAU)", dau),
        ("Активно за 7 дней (WAU)", wau),
        ("Всего запросов за сегодня", total_today),
        ("Всего запросов за 7 дней", total_week)
    ]
    
    for idx, (m_name, m_val) in enumerate(metrics, 4):
        ws2.cell(row=idx, column=1, value=m_name).font = font_data
        ws2.cell(row=idx, column=2, value=m_val).font = font_data
        ws2.cell(row=idx, column=1).border = cell_border
        ws2.cell(row=idx, column=2).border = cell_border
        
    # Таблица почасовой активности
    ws2.cell(row=10, column=1, value="Час").font = font_bold
    ws2.cell(row=10, column=2, value="Кол-во запросов").font = font_bold
    ws2.cell(row=10, column=1).border = header_border
    ws2.cell(row=10, column=2).border = header_border
    
    for h in range(24):
        r = 11 + h
        ws2.cell(row=r, column=1, value=f"{h:02d}:00").font = font_data
        ws2.cell(row=r, column=2, value=hourly_distribution[h]).font = font_data
        ws2.cell(row=r, column=1).alignment = align_center
        ws2.cell(row=r, column=2).alignment = align_center
        ws2.cell(row=r, column=1).border = cell_border
        ws2.cell(row=r, column=2).border = cell_border
        
    # Таблица популярных команд
    ws2.cell(row=10, column=4, value="Команда / Кнопка").font = font_bold
    ws2.cell(row=10, column=5, value="Кол-во использований").font = font_bold
    ws2.cell(row=10, column=4).border = header_border
    ws2.cell(row=10, column=5).border = header_border
    
    top_cmds = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    for idx, (cmd_name, cmd_cnt) in enumerate(top_cmds, 11):
        ws2.cell(row=idx, column=4, value=cmd_name).font = font_data
        ws2.cell(row=idx, column=5, value=cmd_cnt).font = font_data
        ws2.cell(row=idx, column=4).border = cell_border
        ws2.cell(row=idx, column=5).border = cell_border
        ws2.cell(row=idx, column=5).alignment = align_center
        
    ws2.column_dimensions["A"].width = 28
    ws2.column_dimensions["B"].width = 18
    ws2.column_dimensions["D"].width = 25
    ws2.column_dimensions["E"].width = 22

    # -------------------------------------------------------------
    # Лист 3: Лог действий (последние 1000)
    # -------------------------------------------------------------
    ws3 = wb.create_sheet(title="Лог действий")
    ws3.views.sheetView[0].showGridLines = True
    
    ws3.merge_cells("A1:D1")
    title_cell3 = ws3["A1"]
    title_cell3.value = "Лог последних действий пользователей (до 1000 записей)"
    title_cell3.font = font_title
    title_cell3.alignment = align_left
    ws3.row_dimensions[1].height = 40
    
    headers3 = ["Время", "Telegram ID", "Пользователь (Имя / Группа)", "Действие"]
    ws3.row_dimensions[3].height = 24
    for col_num, header in enumerate(headers3, 1):
        cell = ws3.cell(row=3, column=col_num)
        cell.value = header
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = header_border
        
    # Достаем последние 1000 записей из activity_log
    log_rows = execute_query("SELECT user_id, time, action FROM activity_log ORDER BY id DESC LIMIT 1000;", fetch="all")
    
    if log_rows:
        for idx, entry in enumerate(log_rows, 4):
            uid, time_val, act = entry
            t_str = format_dt(time_val)
            
            # Получаем информацию о пользователе из кэша / бд
            u_info = execute_query("SELECT first_name, last_name, group_name FROM users WHERE user_id = %s;", (uid,), fetch="one")
            u_desc = ""
            if u_info:
                first, last, grp = u_info
                name = f"{first or ''} {last or ''}".strip() or "Пользователь"
                u_desc = f"{name} ({grp})" if grp else name
            else:
                u_desc = f"ID: {uid}"
                
            row_data = [t_str, str(uid), u_desc, act]
            ws3.row_dimensions[idx].height = 18
            is_even = (idx % 2 == 0)
            
            for col_num, val in enumerate(row_data, 1):
                cell = ws3.cell(row=idx, column=col_num)
                cell.value = val
                cell.font = font_data
                cell.border = cell_border
                if is_even:
                    cell.fill = fill_zebra
                if col_num in [1, 2]:
                    cell.alignment = align_center
                
    ws3.column_dimensions["A"].width = 20
    ws3.column_dimensions["B"].width = 16
    ws3.column_dimensions["C"].width = 32
    ws3.column_dimensions["D"].width = 40

    filepath = os.path.join(tempfile.gettempdir(), "users_report.xlsx")
    wb.save(filepath)
    return filepath
