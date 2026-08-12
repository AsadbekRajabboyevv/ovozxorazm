import logging
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultCachedVoice
from bot.database.db import Database

router = Router()

PAGE_LIMIT = 20

@router.inline_query()
async def inline_search_handler(inline_query: InlineQuery, db: Database):
    query = inline_query.query.strip()

    offset = 0
    if inline_query.offset:
        try:
            offset = int(inline_query.offset)
        except ValueError:
            offset = 0

    try:
        voices = await db.search_voices(query=query, limit=PAGE_LIMIT, offset=offset)
        logging.info(f"Inline Query: '{query}' | Offset: {offset} | Voices found: {len(voices)}")

        if not voices:
            # Return empty results list so nothing can be clicked or sent to the chat (read-only)
            await inline_query.answer([], cache_time=1, is_personal=True)
            return

        results = []
        for v in voices:
            results.append(
                InlineQueryResultCachedVoice(
                    id=f"v_{v['id']}",
                    voice_file_id=v["file_id"],
                    title=v["title"]
                )
            )

        next_offset = str(offset + len(voices)) if len(voices) >= PAGE_LIMIT else ""

        await inline_query.answer(
            results,
            next_offset=next_offset,
            cache_time=1,
            is_personal=True
        )
    except Exception as e:
        logging.error(f"Inline search error: {e}", exc_info=True)
        await inline_query.answer([], cache_time=1, is_personal=True)

@router.chosen_inline_result()
async def chosen_inline_handler(chosen_result, db: Database):
    try:
        res_id = chosen_result.result_id
        if res_id.startswith("v_"):
            voice_id = int(res_id.split("_")[1])
            await db.increment_voice_usage(voice_id)
    except Exception:
        pass
