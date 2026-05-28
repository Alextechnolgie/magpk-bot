import json
import os
import tempfile
import base64
from datetime import datetime, timedelta

DB_FILE = "users.json"

# Внутрипамятый кэш для исключения постоянного чтения с диска
_users_cache = None


def _xor_cipher(data_str: str, key: str) -> str:
    key_bytes = key.encode("utf-8")
    data_bytes = data_str.encode("utf-8")
    xor_bytes = bytearray(d ^ key_bytes[i % len(key_bytes)] for i, d in enumerate(data_bytes))
    return base64.b64encode(xor_bytes).decode("utf-8")


def _xor_decipher(encoded_str: str, key: str) -> str:
    key_bytes = key.encode("utf-8")
    xor_bytes = base64.b64decode(encoded_str.encode("utf-8"))
    data_bytes = bytearray(d ^ key_bytes[i % len(key_bytes)] for i, d in enumerate(xor_bytes))
    return data_bytes.decode("utf-8")


def _load() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    
    from config import DB_ENCRYPTION_KEY
    
    with open(DB_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return {}
            
        # Если начинается с '{', то это старый незашифрованный формат
        if content.startswith("{"):
            try:
                return json.loads(content)
            except Exception:
                return {}
        
        # Пытаемся расшифровать
        try:
            decrypted = _xor_decipher(content, DB_ENCRYPTION_KEY)
            return json.loads(decrypted)
        except Exception:
            return {}


def _save(data: dict):
    from config import DB_ENCRYPTION_KEY
    data_str = json.dumps(data, ensure_ascii=False, indent=2)
    encrypted = _xor_cipher(data_str, DB_ENCRYPTION_KEY)
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        f.write(encrypted)


def _get_cache() -> dict:
    global _users_cache
    if _users_cache is None:
        _users_cache = _load()
    return _users_cache


def get_user_group(user_id: int) -> str | None:
    """Возвращает сохранённую группу пользователя или None из кэша памяти."""
    cache = _get_cache()
    info = cache.get(str(user_id))
    if isinstance(info, dict):
        return info.get("group")
    return info  # string or None


def set_user_group(user_id: int, group: str):
    """Сохраняет группу пользователя в кэш и записывает на диск."""
    cache = _get_cache()
    uid_str = str(user_id)
    info = cache.get(uid_str)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if isinstance(info, dict):
        info["group"] = group
    else:
        info = {
            "group": group,
            "joined_at": now_str,
            "last_seen": now_str,
            "username": None,
            "first_name": None,
            "last_name": None
        }
    cache[uid_str] = info
    _save(cache)


def update_user_activity(user_id: int, username: str | None, first_name: str | None, last_name: str | None):
    """Обновляет информацию об имени аккаунта и времени последней активности."""
    cache = _get_cache()
    uid_str = str(user_id)
    info = cache.get(uid_str)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if isinstance(info, dict):
        if "joined_at" not in info:
            info["joined_at"] = now_str
        info["last_seen"] = now_str
        info["username"] = username
        info["first_name"] = first_name
        info["last_name"] = last_name
    elif isinstance(info, str):
        info = {
            "group": info,
            "joined_at": now_str,
            "last_seen": now_str,
            "username": username,
            "first_name": first_name,
            "last_name": last_name
        }
    else:
        info = {
            "group": None,
            "joined_at": now_str,
            "last_seen": now_str,
            "username": username,
            "first_name": first_name,
            "last_name": last_name
        }
        
    cache[uid_str] = info
    _save(cache)


def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return None


def get_admin_stats() -> str:
    """Генерирует сводную текстовую статистику с ASCII-графиками."""
    cache = _get_cache()
    total_users = len(cache)
    
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    seven_days_ago = today_start - timedelta(days=7)
    thirty_days_ago = today_start - timedelta(days=30)
    
    today_count = 0
    week_count = 0
    month_count = 0
    
    for user_id, info in cache.items():
        joined_str = None
        if isinstance(info, dict):
            joined_str = info.get("joined_at")
            
        dt = _parse_datetime(joined_str)
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
    
    lines = [
        "📊 *Статистика пользователей бота:*",
        f"👥 Всего пользователей: *{total_users}*",
        "",
        "📈 *Прирост новых пользователей:*",
        f"📅 За сегодня:  `[{bar_today}]` *{today_count}* чел.",
        f"📅 За 7 дней:   `[{bar_week}]` *{week_count}* чел.",
        f"📅 За 30 дней:  `[{bar_month}]` *{month_count}* чел.",
    ]
    return "\n".join(lines)


def generate_users_report() -> str:
    """Генерирует текстовую таблицу пользователей во временный файл."""
    cache = _get_cache()
    lines = [
        "ОТЧЕТ ПО ПОЛЬЗОВАТЕЛЯМ БОТА МАГПК РАСПИСАНИЕ",
        f"Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        f"Всего пользователей: {len(cache)}",
        "=" * 120,
        f"{'ID':<12} | {'Группа':<12} | {'Telegram Аккаунт':<20} | {'Имя Фамилия':<25} | {'Зарегистрирован':<19} | {'Активность':<19}",
        "=" * 120,
    ]
    
    for uid_str, info in cache.items():
        group = ""
        username = ""
        name = "Пользователь"
        joined = "-"
        last_seen = "-"
        
        if isinstance(info, dict):
            group = info.get("group") or ""
            username = f"@{info.get('username')}" if info.get("username") else "-"
            first = info.get("first_name") or ""
            last = info.get("last_name") or ""
            if first or last:
                name = f"{first} {last}".strip()
            joined = info.get("joined_at") or "-"
            last_seen = info.get("last_seen") or "-"
        else:
            group = info or ""
            
        lines.append(f"{uid_str:<12} | {group:<12} | {username:<20} | {name:<25} | {joined:<19} | {last_seen:<19}")
        
    filepath = os.path.join(tempfile.gettempdir(), "users_report.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filepath
