import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import ADMIN_IDS, BOT_TOKEN
from bot.database import db
from bot.handlers import admin, user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    await db.init()

    if not ADMIN_IDS:
        logger.warning(
            "ADMIN_IDS bo'sh — .env faylida ADMIN_IDS ni to'ldirmaguningizcha "
            "hech kim /admin buyrug'idan foydalana olmaydi."
        )

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(admin.router)
    dp.include_router(user.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")
