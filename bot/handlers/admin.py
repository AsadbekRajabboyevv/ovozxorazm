import os
import re
import uuid
import asyncio
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.exceptions import TelegramBadRequest

from bot.database.db import Database
from bot.filters.admin import IsAdminFilter
from bot.services.audio import AudioService
from bot.keyboards.admin_kb import (
    admin_main_keyboard, admin_sub_keyboard, channels_list_keyboard,
    voices_pagination_keyboard, voice_detail_keyboard, back_to_admin_keyboard
)

router = Router()
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

class AddVoiceFSM(StatesGroup):
    waiting_audio = State()
    waiting_title = State()
    waiting_tags = State()

class EditVoiceFSM(StatesGroup):
    waiting_new_title = State()
    waiting_new_tags = State()

class AddChannelFSM(StatesGroup):
    waiting_channel_id = State()

class SetStorageChannelFSM(StatesGroup):
    waiting_storage_channel = State()

class ImportVoicesFSM(StatesGroup):
    waiting_range = State()

class BroadcastFSM(StatesGroup):
    waiting_message = State()

async def safe_edit_text(call: CallbackQuery, text: str, reply_markup=None, parse_mode="HTML"):
    try:
        await call.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest:
        pass
    except Exception:
        try:
            await call.message.delete()
            await call.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            pass

@router.callback_query(F.data == "ignore")
async def cb_ignore(call: CallbackQuery):
    await call.answer()

# Navigation & Dashboard
@router.callback_query(F.data == "admin_main_menu")
async def cb_admin_main(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await safe_edit_text(call, "👑 <b>Admin Paneli:</b>", reply_markup=admin_main_keyboard())

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer()
    await state.clear()
    stats = await db.get_user_stats()
    force_sub = await db.get_setting("force_sub", "off")
    storage_ch = await db.get_setting("storage_channel", "Belgilanmagan")
    sub_status = "🟢 Yoqilgan" if force_sub == "on" else "🔴 O'chirilgan"

    text = (
        "📊 <b>Bot Statistikasi va Ma'lumotlar:</b>\n\n"
        f"👥 <b>Foydalanuvchilar soni:</b> {stats['users']} ta\n"
        f"🎙 <b>Jami ovozlar soni:</b> {stats['voices']} ta\n"
        f"⚡ <b>Ovozlardan foydalanishlar:</b> {stats['uses']} marotaba\n"
        f"📦 <b>Baza (Storage) Kanali:</b> {storage_ch}\n"
        f"📢 <b>Obuna kanallari:</b> {stats['channels']} ta\n"
        f"🔒 <b>Majburiy obuna holati:</b> {sub_status}\n"
    )
    await safe_edit_text(call, text, reply_markup=admin_main_keyboard())

# Storage Channel Setup
@router.callback_query(F.data == "admin_storage_channel")
async def cb_storage_channel_info(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer()
    await state.clear()
    storage_ch = await db.get_setting("storage_channel", "Belgilanmagan")
    await state.set_state(SetStorageChannelFSM.waiting_storage_channel)
    text = (
        f"📦 <b>Baza (Storage) Kanali Sozlamalari:</b>\n\n"
        f"Hozirgi saqlash kanali: <b>{storage_ch}</b>\n\n"
        "Ovozlarni Telegram xotirasida (baza kanalida) saqlash uchun yangi kanal linki yoki ID'sini yuboring:\n"
        "<i>(Masalan: <code>@ovozlar_baza</code> yoki <code>-100123456789</code>)</i>\n"
        "⚠️ <i>Eslatma: Bot ushbu kanalda administrator bo'lishi kerak!</i>"
    )
    await safe_edit_text(call, text, reply_markup=back_to_admin_keyboard())

@router.message(SetStorageChannelFSM.waiting_storage_channel, F.text)
async def process_set_storage_channel(message: Message, state: FSMContext, db: Database, bot: Bot):
    ch_input = message.text.strip()
    try:
        chat = await bot.get_chat(ch_input)
        ch_val = str(chat.id) if chat.username is None else f"@{chat.username}"
        await db.set_setting("storage_channel", ch_val)
        await message.answer(
            f"✅ <b>Baza kanali o'rnatildi:</b> {chat.title} ({ch_val})\n\n"
            "Endi yangi qo'shilgan ovozlar ushbu kanalga yuboriladi va message ID orqali saqlanadi.",
            reply_markup=admin_main_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
    except Exception as e:
        await message.answer(
            f"❌ Kanal o'rnatishda xatolik: {str(e)}\n\n"
            "Bot ushbu kanalda admin ekanligini tekshiring va qaytadan kiriting.",
            reply_markup=back_to_admin_keyboard(),
            parse_mode="HTML"
        )

# Import / Sync Voices from Channel
@router.callback_query(F.data == "admin_import_voices")
async def cb_import_voices_start(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer()
    await state.clear()
    storage_ch = await db.get_setting("storage_channel", "")
    if not storage_ch:
        await safe_edit_text(
            call,
            "⚠️ <b>Avval Baza (Storage) Kanalini sozlang!</b>\n\n"
            "Kanal ovozlarini qayta tiklash uchun avval admin paneldan <b>'📦 Baza Kanal'</b> menyusi orqali saqlash kanalini biriktiring.",
            reply_markup=admin_main_keyboard()
        )
        return

    await state.set_state(ImportVoicesFSM.waiting_range)
    text = (
        "🔄 <b>Kanal Ovozlarini Qayta Tiklash (Import):</b>\n\n"
        "Baza kanaldagi xabarlar ID oralig'ini kiriting.\n"
        "<i>(Masalan: <code>1-300</code> yoki <code>1-1000</code>)</i>\n\n"
        "Bot kanaldagi barcha ovozli xabarlarni skan qiladi va nom hamda teglari bilan bazaga qayta tiklaydi."
    )
    await safe_edit_text(call, text, reply_markup=back_to_admin_keyboard())

@router.message(ImportVoicesFSM.waiting_range, F.text)
async def process_import_voices_range(message: Message, state: FSMContext, db: Database, bot: Bot):
    storage_ch = await db.get_setting("storage_channel", "")
    val = message.text.strip()
    
    start_id = 1
    end_id = 500

    if "-" in val:
        parts = val.split("-")
        if parts[0].isdigit() and parts[1].isdigit():
            start_id = int(parts[0])
            end_id = int(parts[1])
    elif val.isdigit():
        end_id = int(val)

    await state.clear()
    status_msg = await message.answer(f"⏳ Kanal skan qilinmoqda (Message ID: {start_id} - {end_id})...")

    imported = 0
    skipped = 0

    for msg_id in range(start_id, end_id + 1):
        try:
            copied_msg = await bot.copy_message(
                chat_id=message.from_user.id,
                from_chat_id=storage_ch,
                message_id=msg_id
            )
            
            if copied_msg.voice:
                caption = copied_msg.caption or ""
                
                custom_id = None
                title = f"Ovoz #{msg_id}"
                tags = "ovoz"

                id_match = re.search(r"Id:\s*(\d+)", caption, re.IGNORECASE)
                if id_match:
                    custom_id = int(id_match.group(1))

                title_match = re.search(r"Ovoz nomi:\s*(.+)", caption, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()

                tags_match = re.search(r"Ovoz teglari:\s*(.+)", caption, re.IGNORECASE)
                if tags_match:
                    tags = tags_match.group(1).strip()

                success = await db.import_voice_if_not_exists(
                    title=title,
                    tags=tags,
                    file_id=copied_msg.voice.file_id,
                    file_unique_id=copied_msg.voice.file_unique_id or "",
                    duration=copied_msg.voice.duration or 0,
                    storage_message_id=msg_id,
                    custom_id=custom_id
                )

                if success:
                    imported += 1
                else:
                    skipped += 1

            try:
                await bot.delete_message(chat_id=message.from_user.id, message_id=copied_msg.message_id)
            except Exception:
                pass

        except Exception:
            pass

        await asyncio.sleep(0.03)

    await status_msg.edit_text(
        f"✅ <b>Kanal sinxronlash yakunlandi!</b>\n\n"
        f"🎙 <b>Yangi tiklangan ovozlar:</b> {imported} ta\n"
        f"⏩ <b>Mavjud/O'tkazib yuborilgan:</b> {skipped} ta",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )

# Voice Management & Pagination
@router.callback_query(F.data.startswith("admin_voices_page_"))
async def cb_admin_voices(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer()
    await state.clear()
    page = int(call.data.split("_")[-1])
    limit = 8
    offset = page * limit

    voices = await db.get_all_voices(offset=offset, limit=limit)
    total_count = (await db.get_user_stats())["voices"]
    total_pages = max(1, (total_count + limit - 1) // limit)

    if not voices:
        text = "🔊 <b>Bazada hozircha hech qanday ovoz mavjud emas.</b>\n\nYangisini qo'shishingiz mumkin."
    else:
        text = f"🔊 <b>Ovozlar ro'yxati (Sahifa {page + 1}/{total_pages}):</b>"

    await safe_edit_text(call, text, reply_markup=voices_pagination_keyboard(voices, page, total_pages))

@router.callback_query(F.data.startswith("voice_detail_"))
async def cb_voice_detail(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer()
    await state.clear()
    voice_id = int(call.data.split("_")[-1])
    voice = await db.get_voice(voice_id)
    if not voice:
        await call.answer("❌ Ovoz topilmadi!", show_alert=True)
        return

    msg_id_info = f"<code>{voice['storage_message_id']}</code>" if voice.get('storage_message_id') else "Mavjud emas"

    text = (
        f"🎙 <b>Ovoz ma'lumotlari:</b>\n\n"
        f"📌 <b>Nomi:</b> {voice['title']}\n"
        f"🏷 <b>Teglar:</b> <code>{voice['tags']}</code>\n"
        f"📦 <b>Baza Message ID:</b> {msg_id_info}\n"
        f"⚡ <b>Foydalanilgan:</b> {voice['use_count']} marta\n"
        f"🆔 <b>ID:</b> {voice['id']}"
    )
    
    try:
        await call.message.delete()
    except Exception:
        pass

    await call.message.answer_voice(
        voice=voice["file_id"],
        caption=text,
        reply_markup=voice_detail_keyboard(voice_id),
        parse_mode="HTML"
    )

# Add Voice Process (MP3 -> pydub conversion -> DB Save -> Channel Upload with Formatted Caption)
@router.callback_query(F.data == "admin_add_voice")
async def cb_add_voice_start(call: CallbackQuery, state: FSMContext, db: Database):
    await call.answer()
    await state.clear()
    storage_ch = await db.get_setting("storage_channel", "")
    if not storage_ch:
        await safe_edit_text(
            call,
            "⚠️ <b>Avval Baza (Storage) Kanalini sozlang!</b>\n\n"
            "Ovozlarni Telegram kanalida saqlash uchun avval admin paneldan <b>'📦 Baza Kanal'</b> menyusi orqali saqlash kanalini biriktiring.",
            reply_markup=admin_main_keyboard()
        )
        return

    await state.set_state(AddVoiceFSM.waiting_audio)
    await safe_edit_text(
        call,
        "🎙 <b>Yangi ovoz qo'shish:</b>\n\n"
        "Iltimos, MP3 audio fayl yoki Ovozli xabar yuboring.\n"
        "<i>(Fayl pydub orqali Telegram voice formatiga o'girilib, Baza kanalga yuklanadi hamda message ID saqlanadi)</i>",
        reply_markup=back_to_admin_keyboard()
    )

@router.message(AddVoiceFSM.waiting_audio, F.audio | F.voice | F.document)
async def process_voice_audio(message: Message, state: FSMContext, bot: Bot, db: Database):
    storage_ch = await db.get_setting("storage_channel", "")
    if not storage_ch:
        await message.answer("⚠️ Baza kanali o'rnatilmagan!", reply_markup=admin_main_keyboard())
        await state.clear()
        return

    temp_in = f"data/temp_{uuid.uuid4().hex}"
    status_msg = await message.answer("⏳ Audio pydub orqali convert qilinmoqda...")
    
    try:
        file_id = None
        duration = 0
        file_unique_id = ""

        if message.voice:
            file_id = message.voice.file_id
            duration = message.voice.duration or 0
            file_unique_id = message.voice.file_unique_id
        else:
            audio_obj = message.audio or message.document
            if not audio_obj:
                await status_msg.edit_text("❌ Yaroqli audio fayl yuboring!")
                return
                
            file = await bot.get_file(audio_obj.file_id)
            download_path = f"{temp_in}_in"
            await bot.download_file(file.file_path, download_path)
            
            output_name = uuid.uuid4().hex
            converted_ogg = await AudioService.convert_mp3_to_voice_ogg(download_path, output_name)
            
            sent_temp = await message.answer_voice(voice=FSInputFile(converted_ogg))
            file_id = sent_temp.voice.file_id
            duration = sent_temp.voice.duration or 0
            file_unique_id = sent_temp.voice.file_unique_id
            
            AudioService.cleanup_file(download_path)
            AudioService.cleanup_file(converted_ogg)

        await state.update_data(
            file_id=file_id,
            duration=duration,
            file_unique_id=file_unique_id
        )
        await state.set_state(AddVoiceFSM.waiting_title)
        
        await status_msg.delete()
        await message.answer(
            "✏️ <b>Endi ushbu ovoz uchun nom kiriting:</b>",
            reply_markup=back_to_admin_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")
        if os.path.exists(temp_in + "_in"):
            AudioService.cleanup_file(temp_in + "_in")

@router.message(AddVoiceFSM.waiting_title, F.text)
async def process_voice_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(AddVoiceFSM.waiting_tags)
    
    await message.answer(
        f"🏷 <b>Nomi:</b> {title}\n\n"
        "<b>Endi qidiruv uchun teglar kiriting (vergul bilan ajratib):</b>\n"
        "<i>Masalan: xorazm, hazil, prikol, kulgu</i>",
        reply_markup=back_to_admin_keyboard(),
        parse_mode="HTML"
    )

@router.message(AddVoiceFSM.waiting_tags, F.text)
async def process_voice_tags(message: Message, state: FSMContext, db: Database, bot: Bot):
    tags = message.text.strip()
    data = await state.get_data()
    storage_ch = await db.get_setting("storage_channel", "")

    # 1. Add voice to DB to get generated ID
    voice_id = await db.add_voice(
        title=data["title"],
        tags=tags,
        file_id=data["file_id"],
        file_unique_id=data.get("file_unique_id", ""),
        duration=data.get("duration", 0)
    )

    created_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. Format channel caption
    channel_caption = (
        f"Id: {voice_id}\n"
        f"Ovoz nomi: {data['title']}\n"
        f"Ovoz teglari: {tags}\n"
        f"Yuklangan vaqti: {created_at_str}"
    )

    storage_msg_id = None
    final_file_id = data["file_id"]

    # 3. Send voice to Storage Channel with required caption format
    if storage_ch:
        try:
            storage_msg = await bot.send_voice(
                chat_id=storage_ch,
                voice=data["file_id"],
                caption=channel_caption
            )
            storage_msg_id = storage_msg.message_id
            final_file_id = storage_msg.voice.file_id
            await db.update_voice_storage_info(voice_id, final_file_id, storage_msg_id)
        except Exception as e:
            await message.answer(f"⚠️ Baza kanaliga yuborishda xatolik: {str(e)}")

    await state.clear()
    
    await message.answer(
        f"✅ <b>Ovoz muvaffaqiyatli saqlandi!</b> (ID: {voice_id})\n\n"
        f"📌 <b>Nomi:</b> {data['title']}\n"
        f"🏷 <b>Teglar:</b> {tags}\n"
        f"📦 <b>Baza Msg ID:</b> #{storage_msg_id}",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )

# Voice Editing
@router.callback_query(F.data.startswith("edit_voice_title_"))
async def cb_edit_title_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    voice_id = int(call.data.split("_")[-1])
    await state.update_data(edit_voice_id=voice_id)
    await state.set_state(EditVoiceFSM.waiting_new_title)
    await call.message.reply("✏️ <b>Yangi nomni kiriting:</b>", parse_mode="HTML")

@router.message(EditVoiceFSM.waiting_new_title, F.text)
async def process_edit_title(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    voice_id = data.get("edit_voice_id")
    if voice_id:
        voice = await db.get_voice(voice_id)
        if voice:
            await db.update_voice(voice_id, message.text.strip(), voice["tags"])
            await message.answer(f"✅ Ovoz nomi <b>'{message.text.strip()}'</b> ga o'zgartirildi!", reply_markup=admin_main_keyboard(), parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("edit_voice_tags_"))
async def cb_edit_tags_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    voice_id = int(call.data.split("_")[-1])
    await state.update_data(edit_voice_id=voice_id)
    await state.set_state(EditVoiceFSM.waiting_new_tags)
    await call.message.reply("🏷 <b>Yangi teglarni kiriting (vergul bilan):</b>", parse_mode="HTML")

@router.message(EditVoiceFSM.waiting_new_tags, F.text)
async def process_edit_tags(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    voice_id = data.get("edit_voice_id")
    if voice_id:
        voice = await db.get_voice(voice_id)
        if voice:
            await db.update_voice(voice_id, voice["title"], message.text.strip())
            await message.answer("✅ Teglar muvaffaqiyatli yangilandi!", reply_markup=admin_main_keyboard(), parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("confirm_del_voice_"))
async def cb_del_voice(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer()
    await state.clear()
    voice_id = int(call.data.split("_")[-1])
    await db.delete_voice(voice_id)
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer("🗑 <b>Ovoz bazadan o'chirildi!</b>", reply_markup=admin_main_keyboard(), parse_mode="HTML")

# Mandatory Subscription Management
@router.callback_query(F.data == "admin_sub_menu")
async def cb_sub_menu(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer()
    await state.clear()
    is_enabled = (await db.get_setting("force_sub", "off")) == "on"
    channels = await db.get_channels()
    text = (
        "📢 <b>Majburiy Obuna Sozlamalari:</b>\n\n"
        f"Hozirgi holat: <b>{'Yoqilgan' if is_enabled else 'O`chirilgan'}</b>\n"
        f"Ulangan kanallar: <b>{len(channels)} ta</b>"
    )
    await safe_edit_text(call, text, reply_markup=admin_sub_keyboard(is_enabled, channels))

@router.callback_query(F.data == "admin_toggle_sub")
async def cb_toggle_sub(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer()
    current = await db.get_setting("force_sub", "off")
    new_status = "off" if current == "on" else "on"
    await db.set_setting("force_sub", new_status)
    await cb_sub_menu(call, db, state)

@router.callback_query(F.data == "admin_add_channel")
async def cb_add_ch_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await state.set_state(AddChannelFSM.waiting_channel_id)
    text = (
        "➕ <b>Yangi obuna kanali qo'shish:</b>\n\n"
        "Kanal username'ini kiriting (Masalan: <code>@kanallink</code> yoki ID <code>-100123456789</code>):\n"
        "<i>Eslatma: Bot ushbu kanalda administrator bo'lishi shart!</i>"
    )
    await safe_edit_text(call, text, reply_markup=back_to_admin_keyboard())

@router.message(AddChannelFSM.waiting_channel_id, F.text)
async def process_add_channel(message: Message, state: FSMContext, db: Database, bot: Bot):
    ch_input = message.text.strip()
    try:
        chat = await bot.get_chat(ch_input)
        invite_link = chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else "")
        
        success = await db.add_channel(
            channel_id=str(chat.id) if chat.username is None else f"@{chat.username}",
            title=chat.title or ch_input,
            invite_link=invite_link
        )
        
        if success:
            await message.answer(f"✅ <b>Obuna kanali qo'shildi:</b> {chat.title}", reply_markup=admin_main_keyboard(), parse_mode="HTML")
        else:
            await message.answer("⚠️ Ushbu kanal allaqachon qo'shilgan!", reply_markup=admin_main_keyboard())
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Kanalni tekshirishda xatolik: {str(e)}\nBot ushbu kanalda admin ekanligini tekshiring.", reply_markup=back_to_admin_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "admin_list_channels")
async def cb_list_channels(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer()
    await state.clear()
    channels = await db.get_channels()
    if not channels:
        await safe_edit_text(call, "📋 Hozircha hech qanday obuna kanali qo'shilmagan.", reply_markup=back_to_admin_keyboard())
        return
    await safe_edit_text(call, "📋 <b>Biriktirilgan obuna kanallari:</b>", reply_markup=channels_list_keyboard(channels))

@router.callback_query(F.data.startswith("admin_del_ch_"))
async def cb_del_channel(call: CallbackQuery, db: Database, state: FSMContext):
    await call.answer("🗑 Kanal o'chirildi!", show_alert=True)
    ch_db_id = call.data.split("_")[-1]
    await db.remove_channel(ch_db_id)
    await cb_list_channels(call, db, state)

# Broadcast System
@router.callback_query(F.data == "admin_broadcast")
async def cb_broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await state.set_state(BroadcastFSM.waiting_message)
    text = (
        "✉️ <b>Barcha foydalanuvchilarga xabar yuborish:</b>\n\n"
        "Yubormoqchi bo'lgan xabaringizni yuboring (Matn, Rasm, Video, Ovozli xabar)."
    )
    await safe_edit_text(call, text, reply_markup=back_to_admin_keyboard())

@router.message(BroadcastFSM.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext, db: Database):
    await state.clear()
    user_ids = await db.get_all_user_ids()
    
    status_msg = await message.answer(f"⏳ Broadcast boshlandi... Jami: {len(user_ids)} foydalanuvchi")
    
    success = 0
    failed = 0
    
    for uid in user_ids:
        try:
            await message.copy_to(chat_id=uid)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            
    await status_msg.edit_text(
        f"✅ <b>Broadcast yakunlandi!</b>\n\n"
        f"🟢 Yuborildi: {success} ta\n"
        f"🔴 Yuborilmadi (bloklagan): {failed} ta",
        parse_mode="HTML"
    )
