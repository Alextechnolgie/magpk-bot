import asyncio
import sys
import os
from datetime import date

# Добавляем родительскую директорию в sys.path, так как скрипт перемещен в utils/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser import fetch_schedule

# Настраиваем вывод в UTF-8 для консоли Windows
sys.stdout.reconfigure(encoding="utf-8")

async def main():
    print("Запускаем тест нового парсера...")
    res = await fetch_schedule("ТМ9-23-2", date(2026, 5, 25))
    print("\n--- Отформатированный вывод для бота ---")
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
