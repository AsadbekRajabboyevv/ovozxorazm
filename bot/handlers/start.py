from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.database.db import Database
from bot.keyboards.user_kb import user_main_keyboard, phone_request_keyboard
from bot.keyboards.admin_kb import admin_main_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, bot: Bot, state: FSMContext):
    await state.clear()
    user = message.from_user
    await db.add_or_update_user(
        user_id=user.id,
        full_name=user.full_name,
        username=user.username
    )

    is_admin = await db.is_admin(user.id)
    bot_info = await bot.get_me()

    text = (
        f"<b>Assalomu alaykum, {user.full_name}!</b> 👋\n\n"
        f"🤖 <b>@{bot_info.username}</b> rasmiy ovozli xabarlar botiga xush kelibsiz!\n\n"
        f"⚡ <i>Ushbu bot orqali har qanday chatda <b>@{bot_info.username}</b> deb yozib, eng zo'r ovozlarni zudlik bilan yuborishingiz mumkin!</i>"
    )

    if is_admin:
        text += "\n\n👑 <b>Siz adminsiz! Admin paneldan foydalanishingiz mumkin.</b>"

    await message.answer(text, reply_markup=user_main_keyboard(is_admin, bot_info.username), parse_mode="HTML")

@router.message(Command("admin"))
async def cmd_admin(message: Message, db: Database, state: FSMContext):
    await state.clear()
    if await db.is_admin(message.from_user.id):
        await message.answer("👑 <b>Admin panelga xush kelibsiz:</b>", reply_markup=admin_main_keyboard(), parse_mode="HTML")
    else:
        await message.answer(
            "⚠️ <b>Siz admin emassiz!</b>\n\n"
            "Agar siz ma'mur bo'lsangiz, tasdiqlash uchun telefon raqamingizni yuboring:",
            reply_markup=phone_request_keyboard(),
            parse_mode="HTML"
        )

@router.message(F.contact)
async def process_contact(message: Message, db: Database, bot: Bot, state: FSMContext):
    await state.clear()
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer("⚠️ Iltimos, o'zingizning telefon raqamingizni yuboring.")
        return

    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    await db.add_or_update_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        phone_number=phone
    )

    is_admin = await db.is_admin(message.from_user.id)
    bot_info = await bot.get_me()

    if is_admin:
        await message.answer(
            "✅ <b>Telefon raqamingiz tasdiqlandi! Siz admin huquqiga egasiz.</b>",
            reply_markup=admin_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"✅ Telefon raqamingiz qabul qilindi: {phone}",
            reply_markup=user_main_keyboard(False, bot_info.username)
        )

@router.callback_query(F.data == "check_subscription")
async def cb_check_sub(call: CallbackQuery, db: Database, bot: Bot, state: FSMContext):
    await call.answer()
    await state.clear()
    bot_info = await bot.get_me()
    is_admin = await db.is_admin(call.from_user.id)
    await call.message.edit_text(
        "✅ <b>Barcha kanallarga muvaffaqiyatli a'zo bo me'yorlar bajarildi!</b>\n\nEndi ovozlardan foydalanishingiz mumkin.",
        reply_markup=user_main_keyboard(is_admin, bot_info.username),
        parse_mode="HTML"
    )
