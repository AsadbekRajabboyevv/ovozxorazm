from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def admin_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="🔊 Ovozlar", callback_data="admin_voices_page_0")
        ],
        [
            InlineKeyboardButton(text="➕ Ovoz Qo'shish", callback_data="admin_add_voice"),
            InlineKeyboardButton(text="🔄 Kanal Ovozlarini Tiklash", callback_data="admin_import_voices")
        ],
        [
            InlineKeyboardButton(text="📦 Baza Kanal (Storage)", callback_data="admin_storage_channel"),
            InlineKeyboardButton(text="📢 Majburiy Obuna", callback_data="admin_sub_menu")
        ],
        [
            InlineKeyboardButton(text="✉️ Ommaviy Xabar", callback_data="admin_broadcast")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_sub_keyboard(is_enabled: bool, channels: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    status_text = "🟢 Yoqilgan (ON)" if is_enabled else "🔴 O'chirilgan (OFF)"
    buttons = [
        [InlineKeyboardButton(text=f"Obuna holati: {status_text}", callback_data="admin_toggle_sub")],
        [
            InlineKeyboardButton(text="➕ Kanal Qo'shish", callback_data="admin_add_channel"),
            InlineKeyboardButton(text="📋 Kanallar Ro'yxati", callback_data="admin_list_channels")
        ],
        [InlineKeyboardButton(text="⬅️ Bosh Menyu", callback_data="admin_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def channels_list_keyboard(channels: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        title = ch.get("title") or ch.get("channel_id")
        buttons.append([
            InlineKeyboardButton(text=f"📢 {title}", callback_data=f"ch_info_{ch['id']}"),
            InlineKeyboardButton(text="❌ O'chirish", callback_data=f"admin_del_ch_{ch['id']}")
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_sub_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def voices_pagination_keyboard(voices: List[Dict[str, Any]], page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    for v in voices:
        msg_info = f" | Msg #{v['storage_message_id']}" if v.get('storage_message_id') else ""
        buttons.append([InlineKeyboardButton(text=f"🎙 {v['title']} (🔍 {v['use_count']}{msg_info})", callback_data=f"voice_detail_{v['id']}")])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Avvalgi", callback_data=f"admin_voices_page_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{max(1, total_pages)}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_voices_page_{page + 1}"))
    
    if nav_row:
        buttons.append(nav_row)
    
    buttons.append([
        InlineKeyboardButton(text="➕ Yangi Ovoz", callback_data="admin_add_voice"),
        InlineKeyboardButton(text="⬅️ Bosh Menyu", callback_data="admin_main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def voice_detail_keyboard(voice_id: int, page: int = 0) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✏️ Nomini Tahrirlash", callback_data=f"edit_voice_title_{voice_id}"),
            InlineKeyboardButton(text="🏷 Teglarni Tahrirlash", callback_data=f"edit_voice_tags_{voice_id}")
        ],
        [
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"confirm_del_voice_{voice_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data=f"admin_voices_page_{page}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Bekor qilish / Orqaga", callback_data="admin_main_menu")]])
