from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from bot.database.db import Database

class IsAdminFilter(Filter):
    async def __call__(self, event: Message | CallbackQuery, db: Database) -> bool:
        user_id = event.from_user.id
        return await db.is_admin(user_id)
