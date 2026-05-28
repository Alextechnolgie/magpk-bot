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


async def daily_stats_scheduler(bot: Bot):
    import datetime
    from database import get_admin_stats
    from config import ADMIN_IDS
    
    logger.info("📅 Планировщик ежедневной статистики запущен!")
    while True:
        try:
            # Текущее время в Магнитогорске (GMT+5)
            tz = datetime.timezone(datetime.timedelta(hours=5))
            now = datetime.datetime.now(tz)
            # Отправка каждый день в 22:00 по Магнитогорску
            target_time = now.replace(hour=22, minute=0, second=0, microsecond=0)
            if now >= target_time:
                target_time += datetime.timedelta(days=1)
                
            sleep_seconds = (target_time - now).total_seconds()
            logger.info(f"⏳ Следующий автоматический отчет через {sleep_seconds:.1f} сек. (в {target_time})")
            await asyncio.sleep(sleep_seconds)
            
            # Генерация и рассылка статистики
            stats_text = get_admin_stats()
            report_text = f"📢 *Ежедневный автоматический отчет:*\n\n{stats_text}"
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(chat_id=admin_id, text=report_text, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Не удалось отправить отчет админу {admin_id}: {e}")
                    
        except asyncio.CancelledError:
            logger.info("📅 Планировщик ежедневной статистики остановлен.")
            break
        except Exception as e:
            logger.error(f"Ошибка в планировщике статистики: {e}")
            await asyncio.sleep(60)


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

    # Запускаем планировщик ежедневной статистики в фоне
    stats_task = asyncio.create_task(daily_stats_scheduler(bot))

    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        stats_task.cancel()
        await bot.session.close()
        logger.info("🛑 Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
