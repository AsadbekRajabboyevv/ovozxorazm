from typing import Callable, Dict, Any, Awaitable, List
from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from bot.database.db import Database

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        db: Database = data.get("db")
        bot: Bot = data.get("bot")

        if not db or not bot:
            return await handler(event, data)

        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        if await db.is_admin(user.id):
            return await handler(event, data)

        force_sub = await db.get_setting("force_sub", "off")
        if force_sub.lower() != "on":
            return await handler(event, data)

        channels = await db.get_channels()
        if not channels:
            return await handler(event, data)

        unsubscribed_channels = []
        for ch in channels:
            try:
                member = await bot.get_chat_member(chat_id=ch["channel_id"], user_id=user.id)
                if member.status not in ["creator", "administrator", "member"]:
                    unsubscribed_channels.append(ch)
            except Exception:
                unsubscribed_channels.append(ch)

        if not unsubscribed_channels:
            return await handler(event, data)

        if isinstance(event, InlineQuery):
            buttons = []
            for ch in unsubscribed_channels:
                ch_title = ch.get("title") or "Kanalga a'zo bo'lish"
                link = ch["invite_link"] or (f"https://t.me/{ch['channel_id'].replace('@', '')}" if ch["channel_id"].startswith("@") else None)
                if link:
                    buttons.append([InlineKeyboardButton(text=f"📢 {ch_title}", url=link)])
            
            bot_info = await bot.get_me()
            buttons.append([InlineKeyboardButton(text="🤖 Botga o'tib tekshirish", url=f"https://t.me/{bot_info.username}?start=sub_check")])
            
            result = InlineQueryResultArticle(
                id="sub_required",
                title="⚠️ Obuna bo'ling!",
                description="Ovozlardan foydalanish uchun kanallarga a'zo bo'lishingiz va botga start bosishingiz kerak.",
                input_message_content=InputTextMessageContent(
                    message_text="⚠️ Botdan va inline ovozlardan foydalanish uchun avval kanallarga a'zo bo'ling!"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
            return await bot.answer_inline_query(event.id, results=[result], cache_time=1, is_personal=True)

        if isinstance(event, CallbackQuery) and event.data == "check_subscription":
            await event.answer("❌ Hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
            return

        keyboard = self.build_subscription_keyboard(unsubscribed_channels)
        text = (
            "<b>⚠️ Diqqat! Botdan va ovozlardan foydalanish uchun quyidagi kanallarga a'zo bo'ling:</b>\n\n"
            "Kanallarga a'zo bo'lgach <b>'✅ Tekshirish'</b> tugmasini bosing."
        )

        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
            return
        elif isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            return

    @staticmethod
    def build_subscription_keyboard(channels: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        buttons = []
        for ch in channels:
            link = ch["invite_link"] or (f"https://t.me/{ch['channel_id'].replace('@', '')}" if ch["channel_id"].startswith("@") else None)
            if link:
                buttons.append([InlineKeyboardButton(text=f"📢 {ch['title'] or ch['channel_id']}", url=link)])
        
        buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
