import json
import os

DB_FILE = "users.json"

# Внутрипамятый кэш для исключения постоянного чтения с диска
_users_cache = None


def _load() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def _save(data: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_cache() -> dict:
    global _users_cache
    if _users_cache is None:
        _users_cache = _load()
    return _users_cache


def get_user_group(user_id: int) -> str | None:
    """Возвращает сохранённую группу пользователя или None из кэша памяти."""
    cache = _get_cache()
    return cache.get(str(user_id))


def set_user_group(user_id: int, group: str):
    """Сохраняет группу пользователя в кэш и записывает на диск."""
    cache = _get_cache()
    cache[str(user_id)] = group
    _save(cache)
