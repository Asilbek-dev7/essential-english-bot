import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from bot.config import ADMIN_IDS, BOT_TOKEN
from bot.database import db
from bot.handlers import admin, user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start_keepalive_server():
    """Tiny HTTP server so uptime pingers (e.g. Replit + UptimeRobot) can keep the process awake."""
    async def health(request):
        return web.Response(text="Bot ishlayapti ✅")

    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Keep-alive server {port}-portda ishga tushdi")


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
    await start_keepalive_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")
