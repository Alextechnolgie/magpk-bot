import json
import os
import tempfile
import base64
import shutil
from datetime import datetime, timedelta, timezone
from config import get_mgn_now, get_mgn_today

# Если папка /data существует (например, в Docker или Railway Volume), используем её.
# Иначе используем текущую директорию.
DB_DIR = "/data" if os.path.isdir("/data") else "."
DB_FILE = os.path.join(DB_DIR, "users.json")
BACKUP_FILE = DB_FILE + ".bak"
ACTIVITY_LOG_FILE = os.path.join(DB_DIR, "activity.log")

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


def _load_from_file(path: str) -> dict | None:
    """Загружает и дешифрует данные из конкретного файла."""
    if not os.path.exists(path):
        return None
    
    from config import DB_ENCRYPTION_KEY
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return None
                
            if content.startswith("{"):
                return json.loads(content)
            else:
                decrypted = _xor_decipher(content, DB_ENCRYPTION_KEY)
                return json.loads(decrypted)
    except Exception as e:
        print(f"⚠️ Ошибка при чтении {path}: {e}")
        return None


def _load() -> dict:
    # 1. Пытаемся загрузить основной файл
    data = _load_from_file(DB_FILE)
    
    # 2. Если основной файл битый или пустой, пробуем бэкап
    if data is None and os.path.exists(BACKUP_FILE):
        print(f"🔄 Попытка восстановления из бэкапа: {BACKUP_FILE}")
        data = _load_from_file(BACKUP_FILE)
        if data:
            print("✅ Данные восстановлены из бэкапа!")
            _save(data) # Сохраняем восстановленное как основное
            
    if data is None:
        data = {}
                        
    # Если в базе нет ключевых старых пользователей, добавляем их (НЕ затирая новых)
    old_users = {
        "8510857913": {
            "group": "ТМ9-23-2",
            "joined_at": "2026-05-28 17:37:49",
            "last_seen": "2026-05-28 17:54:21",
            "username": "Ishmametyev",
            "first_name": "Алексей",
            "last_name": "Ишмаметьев"
        },
        "787372049": {
            "group": "ТМ9-23-2",
            "joined_at": "2026-05-28 17:40:04",
            "last_seen": "2026-05-28 17:40:31",
            "username": "tsukimanu",
            "first_name": "Костя",
            "last_name": ""
        },
        "1478043047": {
            "group": "ТМ9-23-2",
            "joined_at": "2026-05-28 17:41:14",
            "last_seen": "2026-05-28 17:41:36",
            "username": "kiprro",
            "first_name": "URAL",
            "last_name": ""
        },
        "1003834844": {
            "group": "ТМ9-23-2",
            "joined_at": "2026-05-28 17:47:48",
            "last_seen": "2026-05-28 17:48:52",
            "username": "Stranadozdei",
            "first_name": "Noize",
            "last_name": ""
        },
        "1054079756": {
            "group": "ТМ9-23-2",
            "joined_at": "2026-05-28 17:48:11",
            "last_seen": "2026-05-28 17:48:27",
            "username": "MrNoMor",
            "first_name": "Mr.NoMore",
            "last_name": ""
        },
        "5011839347": {
            "group": "ТМ9-23-2",
            "joined_at": "2026-05-28 17:53:02",
            "last_seen": "2026-05-28 17:53:24",
            "username": "Sudar73i",
            "first_name": "Sudar'",
            "last_name": ""
        },
        "5168364362": {
            "group": "МС-25",
            "joined_at": "2026-05-28 17:53:57",
            "last_seen": "2026-05-28 17:54:08",
            "username": "UwU_loveeeeee",
            "first_name": "Лерч",
            "last_name": ""
        },
        "6534886874": {
            "group": "ТМ9-23-2",
            "joined_at": "2026-05-29 00:38:08",
            "last_seen": "2026-05-29 00:38:47",
            "username": "Sm0k1ti",
            "first_name": "Sm0k1ti\"",
            "last_name": ""
        },
        "1527703119": {
            "group": None,
            "joined_at": "2026-05-29 00:57:09",
            "last_seen": "2026-05-29 00:57:15",
            "username": "kaynex",
            "first_name": "𝚔𝚊𝚢𝚗𝚎𝚡",
            "last_name": ""
        }
    }
    
    modified = False
    for uid, info in old_users.items():
        if uid not in data:
            data[uid] = info
            modified = True
            
    if modified:
        _save(data)
        
    return data


def _save(data: dict):
    """Атомарно сохраняет данные на диск с созданием бэкапа."""
    from config import DB_ENCRYPTION_KEY
    data_str = json.dumps(data, ensure_ascii=False, indent=2)
    encrypted = _xor_cipher(data_str, DB_ENCRYPTION_KEY)
    
    # 1. Создаем бэкап текущего рабочего файла перед обновлением
    if os.path.exists(DB_FILE):
        try:
            shutil.copy2(DB_FILE, BACKUP_FILE)
        except Exception:
            pass

    # 2. Атомарная запись через временный файл (предотвращает пустой файл при сбое)
    dir_name = os.path.dirname(DB_FILE)
    temp_fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix="db_tmp_")
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(encrypted)
        
        # В Windows os.rename не может перезаписывать существующий файл
        if os.name == 'nt' and os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            
        os.rename(temp_path, DB_FILE)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"❌ Критическая ошибка при сохранении базы: {e}")


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


def get_user_interface(user_id: int) -> str:
    """Возвращает тип интерфейса пользователя (по умолчанию 'full')."""
    cache = _get_cache()
    info = cache.get(str(user_id))
    if isinstance(info, dict):
        return info.get("interface", "full")
    return "full"


def set_user_interface(user_id: int, interface_type: str):
    """Устанавливает тип интерфейса пользователя."""
    cache = _get_cache()
    uid_str = str(user_id)
    info = cache.get(uid_str)
    
    if not isinstance(info, dict):
        info = {
            "group": info if isinstance(info, str) else None,
            "joined_at": get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
            "username": None,
            "first_name": None,
            "last_name": None
        }
    
    info["interface"] = interface_type
    cache[uid_str] = info
    _save(cache)


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


def set_user_group(user_id: int, group: str):
    """Сохраняет группу пользователя в кэш и записывает на диск."""
    cache = _get_cache()
    uid_str = str(user_id)
    info = cache.get(uid_str)
    
    now_str = get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    
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
    _sync_user_to_google(user_id, info)


def update_user_activity(user_id: int, username: str | None, first_name: str | None, last_name: str | None, referrer_id: int = None) -> bool:
    """Обновляет информацию об имени аккаунта и времени последней активности.
    Возвращает True, если пользователь абсолютно новый (ранее отсутствовал в базе)."""
    cache = _get_cache()
    uid_str = str(user_id)
    is_new = uid_str not in cache
    
    now_str = get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    
    info = cache.get(uid_str)
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
        
    if is_new and referrer_id and referrer_id != user_id:
        info["invited_by"] = referrer_id
        
    cache[uid_str] = info
    _save(cache)
    _sync_user_to_google(user_id, info)
    return is_new



def get_admin_settings() -> dict:
    """Возвращает настройки администратора."""
    cache = _get_cache()
    settings = cache.get("__settings__")
    if not isinstance(settings, dict):
        settings = {"notify_new_users": True}
    return settings


def set_admin_settings(settings: dict):
    """Сохраняет настройки администратора в базу."""
    cache = _get_cache()
    cache["__settings__"] = settings
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
    total_users = sum(1 for k in cache if k != "__settings__")
    
    now = get_mgn_now().replace(tzinfo=None)
    today_start = datetime(now.year, now.month, now.day)
    seven_days_ago = today_start - timedelta(days=7)
    thirty_days_ago = today_start - timedelta(days=30)
    
    today_count = 0
    week_count = 0
    month_count = 0
    
    # Реферальная статистика
    referral_counts = {}
    invited_total = 0
    
    for user_id, info in cache.items():
        if user_id == "__settings__":
            continue
        joined_str = None
        if isinstance(info, dict):
            joined_str = info.get("joined_at")
            ref_id = info.get("invited_by")
            if ref_id:
                invited_total += 1
                ref_id_str = str(ref_id)
                referral_counts[ref_id_str] = referral_counts.get(ref_id_str, 0) + 1
            
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
    
    top_referrers = sorted(referral_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    top_lines = []
    for idx, (ref_id_str, count) in enumerate(top_referrers, 1):
        ref_info = cache.get(ref_id_str)
        if isinstance(ref_info, dict):
            first = ref_info.get("first_name") or ""
            last = ref_info.get("last_name") or ""
            name = f"{first} {last}".strip() or "Пользователь"
            username = ref_info.get("username")
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


def generate_users_report() -> str:
    """Генерирует красивый Excel-отчет о пользователях и активности."""
    cache = _get_cache()
    total_users = sum(1 for k in cache if k != "__settings__")
    
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    
    wb = Workbook()
    
    # -------------------------------------------------------------
    # Стили
    # -------------------------------------------------------------
    font_title = Font(name="Calibri", size=16, bold=True, color="1F497D")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=11)
    font_bold = Font(name="Calibri", size=11, bold=True)
    
    fill_header = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid") # Темно-синий
    fill_zebra = PatternFill(start_color="F2F5F8", end_color="F2F5F8", fill_type="solid") # Светлый серо-синий
    
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
        
    row_num = 5
    for uid_str, info in cache.items():
        if uid_str == "__settings__":
            continue
        group = ""
        username = ""
        name = "Пользователь"
        joined = "-"
        last_seen = "-"
        invited_by = "-"
        referrals_count = get_referred_users_count(int(uid_str))
        
        if isinstance(info, dict):
            group = info.get("group") or ""
            username = f"@{info.get('username')}" if info.get("username") else "-"
            first = info.get("first_name") or ""
            last = info.get("last_name") or ""
            if first or last:
                name = f"{first} {last}".strip()
            joined = info.get("joined_at") or "-"
            last_seen = info.get("last_seen") or "-"
            invited_by = str(info.get("invited_by")) if info.get("invited_by") else "-"
        else:
            group = info or ""
            
        row_data = [uid_str, group, username, name, joined, last_seen, invited_by, referrals_count]
        
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
    
    # Считаем данные из логов
    dau = 0
    wau = 0
    total_today = 0
    total_week = 0
    hourly_distribution = [0] * 24
    command_counts = {}
    
    if os.path.exists(ACTIVITY_LOG_FILE):
        now = get_mgn_now().replace(tzinfo=None)
        today_start = datetime(now.year, now.month, now.day)
        seven_days_ago = today_start - timedelta(days=7)
        
        active_users_today = set()
        active_users_week = set()
        
        try:
            with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        dt = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")
                        uid = entry["user_id"]
                        action = entry["action"]
                        
                        if dt >= seven_days_ago:
                            total_week += 1
                            active_users_week.add(uid)
                            
                            cmd = action.split()[0] if action else "unknown"
                            if cmd.startswith("cb:"):
                                cmd = "кнопка: " + cmd.split(":")[1].split()[0]
                            command_counts[cmd] = command_counts.get(cmd, 0) + 1
                            hourly_distribution[dt.hour] += 1
                            
                        if dt >= today_start:
                            total_today += 1
                            active_users_today.add(uid)
                    except Exception:
                        continue
            dau = len(active_users_today)
            wau = len(active_users_week)
        except Exception:
            pass
            
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
        
    log_rows = []
    if os.path.exists(ACTIVITY_LOG_FILE):
        try:
            with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        log_rows.append(entry)
                    except Exception:
                        continue
            log_rows = log_rows[-1000:]
            log_rows.reverse()
        except Exception:
            pass
            
    for idx, entry in enumerate(log_rows, 4):
        uid = entry.get("user_id")
        t_str = entry.get("time")
        act = entry.get("action")
        
        u_info = cache.get(str(uid))
        u_desc = ""
        if isinstance(u_info, dict):
            first = u_info.get("first_name") or ""
            last = u_info.get("last_name") or ""
            grp = u_info.get("group") or ""
            name = f"{first} {last}".strip() or "Пользователь"
            u_desc = f"{name} ({grp})" if grp else name
        elif isinstance(u_info, str):
            u_desc = f"Группа: {u_info}"
        else:
            u_desc = "Новый/Неизвестный"
            
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


def log_activity(user_id: int, action: str):
    """Логирует действие пользователя в activity.log."""
    now_str = get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "user_id": user_id,
        "time": now_str,
        "action": action
    }
    try:
        with open(ACTIVITY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"❌ Ошибка при логировании активности: {e}")


def get_activity_stats() -> str:
    """Анализирует лог активности и формирует сводку с гистограммой по часам за последние 7 дней."""
    if not os.path.exists(ACTIVITY_LOG_FILE):
        return "📊 *Статистика активности:* Нет логов активности."

    now = get_mgn_now().replace(tzinfo=None)
    today_start = datetime(now.year, now.month, now.day)
    seven_days_ago = today_start - timedelta(days=7)

    total_today = 0
    total_week = 0
    active_users_today = set()
    active_users_week = set()

    hourly_distribution = [0] * 24
    command_counts = {}

    try:
        with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    dt = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")
                    uid = entry["user_id"]
                    action = entry["action"]

                    if dt >= seven_days_ago:
                        total_week += 1
                        active_users_week.add(uid)

                        # Группируем популярные действия
                        cmd = action.split()[0] if action else "unknown"
                        if cmd.startswith("cb:"):
                            cmd = "кнопка: " + cmd.split(":")[1].split()[0]
                        command_counts[cmd] = command_counts.get(cmd, 0) + 1

                    if dt >= today_start:
                        total_today += 1
                        active_users_today.add(uid)

                    if dt >= seven_days_ago:
                        hourly_distribution[dt.hour] += 1
                except Exception:
                    continue
    except Exception as e:
        return f"❌ Ошибка при чтении логов: {e}"

    dau = len(active_users_today)
    wau = len(active_users_week)

    # Топ команд
    top_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    commands_str = "\n".join(f"  • `{cmd}`: *{count}* раз" for cmd, count in top_commands)

    # Гистограмма активности
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


def get_referred_users_count(user_id: int) -> int:
    """Подсчитывает количество пользователей, приглашенных этим пользователем."""
    cache = _get_cache()
    count = 0
    for uid_str, info in cache.items():
        if uid_str == "__settings__":
            continue
        if isinstance(info, dict) and info.get("invited_by") == user_id:
            count += 1
    return count


def is_promo_dismissed(user_id: int, promo_id: str) -> bool:
    """Проверяет, скрыл ли пользователь промо навсегда."""
    cache = _get_cache()
    info = cache.get(str(user_id))
    if isinstance(info, dict):
        promos = info.get("promos", {})
        promo_info = promos.get(promo_id)
        if isinstance(promo_info, dict):
            return promo_info.get("dismissed", False)
        elif isinstance(promo_info, bool):
            return promo_info
    return False


def dismiss_promo(user_id: int, promo_id: str):
    """Скрывает промо-сообщение для пользователя навсегда."""
    cache = _get_cache()
    uid_str = str(user_id)
    info = cache.get(uid_str)

    if not isinstance(info, dict):
        info = {
            "group": info if isinstance(info, str) else None,
            "joined_at": get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
            "username": None,
            "first_name": None,
            "last_name": None
        }

    if "promos" not in info:
        info["promos"] = {}

    promo_info = info["promos"].get(promo_id)
    if not isinstance(promo_info, dict):
        promo_info = {"dismissed": True, "last_shown_at": None}
    else:
        promo_info["dismissed"] = True

    info["promos"][promo_id] = promo_info
    cache[uid_str] = info
    _save(cache)


def can_show_promo_today(user_id: int, promo_id: str) -> bool:
    """Проверяет, можно ли показать пользователю промо сегодня."""
    cache = _get_cache()
    info = cache.get(str(user_id))
    if not isinstance(info, dict):
        return True

    promos = info.get("promos", {})
    promo_info = promos.get(promo_id)
    if not promo_info:
        return True

    if isinstance(promo_info, bool):
        return not promo_info

    if promo_info.get("dismissed", False):
        return False

    last_shown = promo_info.get("last_shown_at")
    if not last_shown:
        return True

    today_str = get_mgn_today().isoformat()
    return last_shown != today_str


def record_promo_show(user_id: int, promo_id: str):
    """Сохраняет текущую дату как дату последнего показа промо."""
    cache = _get_cache()
    uid_str = str(user_id)
    info = cache.get(uid_str)

    if not isinstance(info, dict):
        info = {
            "group": info if isinstance(info, str) else None,
            "joined_at": get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": get_mgn_now().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
            "username": None,
            "first_name": None,
            "last_name": None
        }

    if "promos" not in info:
        info["promos"] = {}

    promo_info = info["promos"].get(promo_id)
    if not isinstance(promo_info, dict):
        dismissed = promo_info if isinstance(promo_info, bool) else False
        promo_info = {"dismissed": dismissed}

    promo_info["last_shown_at"] = get_mgn_today().isoformat()
    info["promos"][promo_id] = promo_info
    cache[uid_str] = info
    _save(cache)
