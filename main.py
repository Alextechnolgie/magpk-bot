import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from handlers import router

load_dotenv()
# Сначала пробуем взять из окружения (для Railway), если нет — из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main():
    token = os.environ.get("BOT_TOKEN") or BOT_TOKEN
    if not token or token == "ВСТАВЬ_ТОКЕН_СЮДА":
        raise ValueError("BOT_TOKEN не найден! Добавь его в переменные на Railway или в файл .env")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("🤖 Бот Магнитогорского Политеха запущен!")
    logger.info("📡 Режим: polling (long polling)")

    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()
        logger.info("🛑 Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
