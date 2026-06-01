import asyncio
import sys
import os
import argparse
import psycopg2
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramAPIError

# Load environment
load_dotenv()

# We can also add parent directory to path to import config if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Message text
MESSAGE = (
    "📢 *Важное обновление бота МАГПК Расписание!* 🚀\n\n"
    "Привет! Мы рады сообщить, что бот снова работает стабильно и быстро! Мы провели крупное техническое обновление:\n\n"
    "🤝 *Реферальная система:* Теперь вы можете помочь боту развиваться! В меню «ℹ️ О боте» появилась ваша персональная ссылка для приглашения друзей из политеха, а также счетчик приглашенных вами студентов. Делитесь ботом с одногруппниками в один клик!\n\n"
    "🤫 *Умные уведомления:* Мы добавили полезные напоминания о развитии проекта, но сделали их ненавязчивыми — они будут показываться не чаще 1 раза в сутки и только при просмотре расписания, а кнопка «Больше не показывать» скроет их навсегда.\n\n"
    "⚡ *Повышена стабильность:* Исправлен баг со сбросом выбранных групп, решены проблемы с выгрузкой календарей и оптимизирована скорость загрузки расписания.\n\n"
    "Спасибо, что вы с нами! Желаем успешной учёбы! 🎓✨"
)

def safe_print(msg, end="\n", flush=True):
    """Prints message safely to stdout, handling UnicodeEncodeErrors in Windows terminal."""
    try:
        sys.stdout.write(msg + end)
        if flush:
            sys.stdout.flush()
    except UnicodeEncodeError:
        try:
            encoding = sys.stdout.encoding or 'utf-8'
            encoded = (msg + end).encode(encoding, errors='replace').decode(encoding)
            sys.stdout.write(encoded)
            if flush:
                sys.stdout.flush()
        except Exception:
            ascii_msg = ''.join(c if ord(c) < 128 else '?' for c in (msg + end))
            sys.stdout.write(ascii_msg)
            if flush:
                sys.stdout.flush()

async def main():
    parser = argparse.ArgumentParser(description="Бродкаст обновлений пользователям бота.")
    parser.add_argument("--db", type=str, help="DATABASE_URL для PostgreSQL. Если не задан, берется из окружения.")
    parser.add_argument("--test-id", type=int, help="ID пользователя для тестовой отправки (сухой запуск).")
    parser.add_argument("--skip-file", type=str, help="Путь к логу предыдущего запуска для пропуска уже обработанных ID.")
    args = parser.parse_args()

    # Get DB URL
    db_url = args.db or os.getenv("DATABASE_URL")
    if not db_url:
        safe_print("DATABASE_URL not set!")
        sys.exit(1)

    # Get Bot Token
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        safe_print("BOT_TOKEN not found in environment!")
        sys.exit(1)

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

    # Fetch users from Postgres
    safe_print("Connecting to PostgreSQL database...")
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, first_name FROM users;")
        users = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        safe_print(f"Error fetching users: {e}")
        await bot.session.close()
        sys.exit(1)

    safe_print(f"Total users in DB: {len(users)}")

    # Parse skip file if provided
    processed_ids = set()
    if args.skip_file and os.path.exists(args.skip_file):
        safe_print(f"Reading skip file: {args.skip_file}...")
        try:
            with open(args.skip_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "Sending to" in line and ("SUCCESS" in line or "API ERROR" in line or "BLOCKED" in line):
                        # Extract the ID: it's between "Sending to " and the next space
                        parts = line.split("Sending to ")
                        if len(parts) > 1:
                            uid_part = parts[1].split()[0]
                            if uid_part.isdigit():
                                processed_ids.add(int(uid_part))
            safe_print(f"Skipping {len(processed_ids)} already processed user IDs.")
        except Exception as e:
            safe_print(f"Failed to parse skip file: {e}")

    if args.test_id:
        safe_print(f"Test mode. Sending only to user: {args.test_id}")
        target_users = [u for u in users if u[0] == args.test_id]
        if not target_users:
            safe_print(f"User {args.test_id} not found in DB, sending blindly.")
            target_users = [(args.test_id, None, "Test")]
    else:
        target_users = [u for u in users if u[0] not in processed_ids]

    safe_print(f"Starting broadcast for {len(target_users)} recipients...")
    success = 0
    blocked = 0
    failed = 0

    for idx, user in enumerate(target_users):
        user_id, username, first_name = user
        name_str = f"@{username}" if username else (first_name or str(user_id))
        safe_print(f"[{idx+1}/{len(target_users)}] Sending to {user_id} ({name_str})...", end="", flush=True)

        sent = False
        retries = 3
        while not sent and retries > 0:
            try:
                await bot.send_message(chat_id=user_id, text=MESSAGE)
                safe_print(" SUCCESS")
                success += 1
                sent = True
            except TelegramForbiddenError:
                safe_print(" BLOCKED")
                blocked += 1
                sent = True
            except TelegramRetryAfter as e:
                safe_print(f" RATE LIMIT. Waiting {e.retry_after}s...")
                await asyncio.sleep(e.retry_after + 1)
                retries -= 1
            except TelegramAPIError as e:
                safe_print(f" API ERROR: {e}")
                failed += 1
                sent = True
            except Exception as e:
                safe_print(f" ERROR: {e}")
                failed += 1
                sent = True

        # Небольшая пауза для соблюдения лимитов Telegram (30 сообщений/сек)
        await asyncio.sleep(0.05)

    safe_print("\nBroadcast results:")
    safe_print(f"   Success: {success}")
    safe_print(f"   Blocked: {blocked}")
    safe_print(f"   Failed: {failed}")

    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
