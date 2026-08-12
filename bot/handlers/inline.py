from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultCachedVoice, InlineQueryResultArticle, InputTextMessageContent
from bot.database.db import Database
import uuid

router = Router()

PAGE_LIMIT = 20

@router.inline_query()
async def inline_search_handler(inline_query: InlineQuery, db: Database):
    query = inline_query.query.strip()

    offset = 0
    if inline_query.offset and inline_query.offset.isdigit():
        offset = int(inline_query.offset)

    voices = await db.search_voices(query=query, limit=PAGE_LIMIT, offset=offset)

    if not voices and offset == 0:
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

    next_offset = str(offset + len(voices)) if len(voices) == PAGE_LIMIT else ""

    await inline_query.answer(
        results,
        next_offset=next_offset,
        cache_time=1,
        is_personal=True
    )

@router.chosen_inline_result()
async def chosen_inline_handler(chosen_result, db: Database):
    try:
        voice_id = int(chosen_result.result_id)
        await db.increment_voice_usage(voice_id)
    except Exception:
        pass
