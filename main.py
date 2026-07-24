import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN
from bot.database.db import Database
from bot.middlewares.subscription import SubscriptionMiddleware
from bot.handlers import start, admin, inline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

async def main():
    if not BOT_TOKEN:
        print("⚠️ ILTIMOS: .env faylida bot tokeningizni (BOT_TOKEN) ko'rsating!")
        return

    db = Database()
    await db.init()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp["db"] = db

    sub_middleware = SubscriptionMiddleware()
    dp.message.outer_middleware(sub_middleware)
    dp.callback_query.outer_middleware(sub_middleware)
    dp.inline_query.outer_middleware(sub_middleware)

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(inline.router)

    print("🚀 Bot muvaffaqiyatli ishga tushirildi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
