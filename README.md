# 🎙 Ovoz Telegram Boti (@ovozxorazmbot)

Ushbu bot Telegram'da MP3 va Ovozli xabarlarni saqlash, pydub orqali Telegram Voice formatiga avtomatik konvertatsiya qilish, teg va nomlar bo'yicha tezkor inline qidiruv hamda majburiy obuna va admin panelini o'z ichiga olgan zamonaviy botdir.

## 🚀 Texnologiyalar
- **Python 3.10+**
- **aiogram 3.x**
- **aiosqlite** (SQLite ma'lumotlar bazasi)
- **pydub & imageio-ffmpeg** (Audio convertation)

## 📋 Ishga tushirish yo'riqnomasi

1. **Kutubxonalarni o'rnatish:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Sozlamalarni kiritish:**
   `.env.example` faylidan nusxa olib `.env` nomli fayl yarating va Telegram bot sozlamalarini kiriting:
   ```env
   BOT_TOKEN=YOUR_BOT_TOKEN_HERE
   ADMIN_PHONE=+998XXXXXXXXX
   ADMIN_IDS=123456789
   STORAGE_CHANNEL_ID=@your_storage_channel
   ```

3. **Botni ishga tushirish:**
   ```bash
   python main.py
   ```

## ⚙️ Asosiy Imkoniyatlar
- 👑 **Admin Panel:** `/admin` buyrug'i yoki telefon raqamini yuborish orqali kirish.
- 🎙 **MP3 Convertation:** Admin yuborgan har qanday MP3 faylni `pydub` orqali `.ogg` telegram voice formatiga avtomatik convert qiladi.
- 🔍 **Inline Qidiruv:** `@ovozxorazmbot <nomi yoki tegi>` orqali har qanday chatga ovozli xabarlarni lahzalik tezlikda yuborish.
- 📦 **Telegram Storage Channel:** Ovozli xabarlar Telegram kanalida saqlanadi hamda Message ID bo'yicha tezkor chaqiriladi.
- 🔒 **Majburiy Obuna:** Kanallarga va botga obuna bo'lishni tekshirish (Admin panelda ON/OFF qilish imkoniyati).
- 📊 **Statistika:** Jami foydalanuvchilar, ovozlar va foydalanishlar statistikasi.
- ✉️ **Broadcast:** Barcha foydalanuvchilarga xabar yuborish.
