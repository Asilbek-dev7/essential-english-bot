# Essential English Words — Telegram Bot

Kitob → Unit diapazoni → random so'z testlari (4 variant) tarzida ishlaydigan
Telegram bot. Python 3.11+, aiogram 3, SQLite.

## O'rnatish

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

`.env` faylida:

```
BOT_TOKEN=...                # @BotFather'dan olingan token
ADMIN_IDS=123456789          # @userinfobot orqali olingan Telegram ID, vergul bilan bir nechta
DB_PATH=data/bot.db
```

`ADMIN_IDS` bo'sh bo'lsa, `/admin` paneliga hech kim kira olmaydi.

## Ishga tushirish

```bash
python -m bot.main
```

Sinov uchun namunaviy so'zlar bilan bazani to'ldirish (ixtiyoriy):

```bash
python seed_demo.py
```

## Foydalanuvchi oqimi

1. `/start` — kitob tanlash
2. Unit diapazonini tanlash (1–5, 6–10, ...)
3. Bot random so'z va 4 ta variantni (tugmalar) chiqaradi
4. Javob tanlanganda ✅/❌ va to'g'ri javob ko'rsatiladi
5. "➡️ Keyingi savol" — keyingi random so'z (bir xil so'z sessiyada qayta chiqmaydi)
6. Barcha so'zlar tugagach — natija (jami/to'g'ri/noto'g'ri/foiz) va qayta boshlash tugmasi

## Admin panel

`ADMIN_IDS` ro'yxatidagi foydalanuvchilar `/admin` buyrug'i bilan kiradi:

- 📚 Kitob qo'shish
- 📖 Unit qo'shish
- ➕ So'z qo'shish (so'z + tarjima)
- 📂 So'zlarni ko'rish / tahrirlash / o'chirish
- 📥 Ko'p so'zni birdan yuklash — `.txt` fayl yoki matn xabar, har qatorda:

  ```
  unit|so'z|tarjima
  4|abandon|tark etmoq
  4|benefit|foyda
  ```

  Mavjud bo'lmagan unit avtomatik yaratiladi.

## Loyiha tuzilishi

```
bot/
  config.py        # .env dan sozlamalar
  database.py       # SQLite (aiosqlite) — books/units/words/users
  keyboards.py       # inline klaviaturalar
  states.py          # admin FSM holatlari
  main.py            # kirish nuqtasi (polling)
  handlers/
    user.py           # /start, test oqimi
    admin.py           # /admin, CRUD
seed_demo.py         # sinov uchun namunaviy so'zlar
data/bot.db          # SQLite fayli (avtomatik yaratiladi)
```

## Eslatma

`seed_demo.py` ichidagi so'zlar Essential English Words kitobining haqiqiy
matni emas — botni tezda sinab ko'rish uchun umumiy inglizcha so'zlar.
Haqiqiy kitob lug'atini admin panel orqali (yoki bulk import bilan) o'zingiz
kiritishingiz kerak.
