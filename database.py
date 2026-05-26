import json
import os

DB_FILE = "users.json"


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


def get_user_group(user_id: int) -> str | None:
    """Возвращает сохранённую группу пользователя или None."""
    data = _load()
    return data.get(str(user_id))


def set_user_group(user_id: int, group: str):
    """Сохраняет группу пользователя."""
    data = _load()
    data[str(user_id)] = group
    _save(data)
