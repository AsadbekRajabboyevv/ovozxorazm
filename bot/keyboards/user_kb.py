from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def user_main_keyboard(is_admin: bool = False, bot_username: str = "ovozxorazmbot") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🎙 Ovozlardan foydalanish (Inline)", switch_inline_query_current_chat="")
        ]
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="admin_main_menu")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def phone_request_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)
