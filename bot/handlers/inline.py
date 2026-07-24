from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultCachedVoice, InlineQueryResultArticle, InputTextMessageContent
from bot.database.db import Database
import uuid

router = Router()

@router.inline_query()
async def inline_search_handler(inline_query: InlineQuery, db: Database):
    query = inline_query.query.strip()
    voices = await db.search_voices(query=query, limit=50)

    if not voices:
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="🔍 Ovoz topilmadi",
                description=f"'{query}' bo'yicha hech qanday ovoz topilmadi." if query else "Hozircha ovozlar mavjud emas.",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔍 <b>'{query}'</b> bo'yicha ovoz topilmadi.",
                    parse_mode="HTML"
                )
            )
        ]
        await inline_query.answer(results, cache_time=1, is_personal=True)
        return

    results = []
    for v in voices:
        results.append(
            InlineQueryResultCachedVoice(
                id=str(v["id"]),
                voice_file_id=v["file_id"],
                title=v["title"]
            )
        )

    await inline_query.answer(results, cache_time=1, is_personal=True)

@router.chosen_inline_result()
async def chosen_inline_handler(chosen_result, db: Database):
    try:
        voice_id = int(chosen_result.result_id)
        await db.increment_voice_usage(voice_id)
    except Exception:
        pass
