# SlaydBot

Groq AI yordamida Telegram ichida mavzu bo'yicha `.pptx` prezentatsiya yaratadigan bot.

## Ishlash tartibi

1. Foydalanuvchi botga mavzu yuboradi.
2. Bot slaydlar sonini so'raydi.
3. Faqat `5` dan `15` gacha bo'lgan son qabul qilinadi.
4. Bot Groq API orqali shu songa mos o'zbekcha slayd matnlarini yaratadi.
5. Bot `.pptx` fayl generatsiya qiladi.
6. Tayyor prezentatsiya foydalanuvchiga Telegram orqali yuboriladi.
7. Admin panel orqali user statistikasi va broadcast ishlaydi.

## O'rnatish

```bash
npm install
```

`.env` fayl yarating:

```env
BOT_TOKEN=telegram_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
MONGODB_URI=your_mongodb_connection_string_here
MONGODB_DB_NAME=slaydbot
ADMIN_IDS=123456789
```

## Ishga tushirish

```bash
npm start
```

## Admin buyruqlar

- `/admin` - admin panel menyusi
- `/stats` - jami userlar va bloklaganlar soni
- `/broadcast` - barcha userlarga xabar yuborish
