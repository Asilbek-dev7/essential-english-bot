import html
import logging
import random
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import ADMIN_IDS, QUESTION_OPTIONS_COUNT, UNIT_RANGE_SIZE
from bot.database import db
from bot.keyboards import (
    admin_menu_kb,
    book_list_reply_kb,
    count_kb,
    lang_kb,
    main_menu_reply_kb,
    next_question_kb,
    options_kb,
    ranges_kb,
    restart_kb,
    single_units_kb,
)

logger = logging.getLogger(__name__)

router = Router(name="user")

# telegram_id -> quiz session dict, kept in memory for the lifetime of the process
SESSIONS: dict[int, dict] = {}


async def get_session(user_id: int) -> dict | None:
    """Memory first; fall back to the DB copy (e.g. after a bot restart)."""
    session = SESSIONS.get(user_id)
    if session is None:
        session = await db.load_session(user_id)
        if session is not None:
            SESSIONS[user_id] = session
    return session


async def save_session(user_id: int):
    await db.save_session(user_id, SESSIONS[user_id])


async def drop_session(user_id: int):
    SESSIONS.pop(user_id, None)
    await db.delete_session(user_id)


async def send_books_list(message: Message):
    books = await db.list_books()
    if not books:
        await message.answer("📚 Hozircha bazada kitoblar yo'q. Admin so'zlarni qo'shishi kerak.")
        return
    await message.answer(
        "📚 Kitobni tanlang:", reply_markup=book_list_reply_kb(books)
    )


async def is_book_name(message: Message) -> bool:
    if not message.text:
        return False
    return await db.get_book_by_name(message.text) is not None


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    await drop_session(message.from_user.id)
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        "👋 Xush kelibsiz!\n\n"
        "📚 Essential English Words kitoblari asosida inglizcha so'zlarni "
        "random test tarzida mashq qiling.",
        reply_markup=main_menu_reply_kb(is_admin),
    )
    await send_books_list(message)


@router.message(F.text == "📚 Kitoblar")
async def menu_books(message: Message):
    await drop_session(message.from_user.id)
    await send_books_list(message)


@router.message(F.text == "📊 Natijalarim")
async def menu_stats(message: Message):
    stats = await db.get_user_stats(message.from_user.id)
    if not stats or stats["total"] == 0:
        await message.answer("Sizda hali natija yo'q. Test yechib ko'ring!")
        return
    total, correct, wrong = stats["total"], stats["correct"], stats["wrong"]
    percent = round(correct / total * 100) if total else 0

    last_total = stats["last_total"] or 0
    last_correct = stats["last_correct"] or 0
    last_played_at = stats["last_played_at"]
    last_played = last_played_at[:16] if last_played_at else "—"

    text = (
        "📊 Sizning umumiy natijangiz\n"
        "━━━━━━━━━━━━━━\n"
        f"📝 Jami savollar: {total}\n"
        f"✅ To'g'ri: {correct}\n"
        f"❌ Noto'g'ri: {wrong}\n"
        f"🎯 Aniqlik: {correct}/{total} ({percent}%)\n"
        "━━━━━━━━━━━━━━\n"
        f"🕓 Oxirgi natija: {last_correct}/{last_total}\n"
        f"📅 Sana: {last_played}"
    )
    await message.answer(text)


LANG_NAMES = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский"}


@router.message(F.text == "🌐 Til / Язык")
async def menu_lang(message: Message):
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    current = await db.get_user_lang(message.from_user.id)
    await message.answer(
        "🌐 So'zlar tarjimasi tilini tanlang / Выберите язык перевода слов:\n\n"
        f"Hozirgi / Текущий: {LANG_NAMES[current]}",
        reply_markup=lang_kb(current),
    )


@router.callback_query(F.data.startswith("lang:"))
async def choose_lang(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    if lang not in LANG_NAMES:
        await callback.answer()
        return
    await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
    await db.set_user_lang(callback.from_user.id, lang)
    await callback.message.edit_text(
        f"✅ Til o'zgartirildi / Язык изменён: {LANG_NAMES[lang]}", reply_markup=lang_kb(lang)
    )
    await callback.answer()


@router.message(F.text == "ℹ️ Yordam")
async def menu_help(message: Message):
    text = (
        "ℹ️ Yordam\n\n"
        "📚 Kitoblar — kitob, Unit diapazoni va savollar sonini tanlab, test yeching\n"
        "📊 Natijalarim — barcha vaqtdagi statistikangiz va oxirgi natijangiz\n"
        "🌐 Til / Язык — tarjima tilini tanlash (o'zbekcha yoki ruscha)\n"
        "/start — botni qayta ishga tushirish\n\n"
        "So'zlar va javob variantlari har safar random tartibda chiqadi. "
        "Test paytida 4 ta variantdan birini tanlang. Har javobdan keyin "
        "to'g'ri javob ko'rsatiladi va \"➡️ Keyingi savol\" tugmasi chiqadi. "
        "Tanlangan savollar tugagach, natijangiz chiqadi."
    )
    await message.answer(text)


@router.message(F.text == "🛠 Admin panel")
async def menu_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Sizda admin huquqi yo'q.")
        return
    await message.answer("🛠 Admin panel", reply_markup=admin_menu_kb())


@router.message(F.text == "⬅️ Orqaga")
async def menu_back(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer("Bosh menyu:", reply_markup=main_menu_reply_kb(is_admin))


@router.message(is_book_name)
async def book_selected(message: Message):
    await drop_session(message.from_user.id)
    book = await db.get_book_by_name(message.text)
    is_admin = message.from_user.id in ADMIN_IDS
    ranges = await db.get_unit_ranges(book["id"], UNIT_RANGE_SIZE)
    if not ranges:
        await message.answer(
            "Bu kitobda hali so'zlar yo'q.", reply_markup=main_menu_reply_kb(is_admin)
        )
        return
    await message.answer(f"📖 {book['name']}", reply_markup=main_menu_reply_kb(is_admin))
    await message.answer(
        "Unit diapazonini tanlang:", reply_markup=ranges_kb(book["id"], ranges)
    )


@router.callback_query(F.data == "back_to_books")
async def back_to_books(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await send_books_list(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("book:"))
async def choose_book(callback: CallbackQuery):
    book_id = int(callback.data.split(":")[1])
    ranges = await db.get_unit_ranges(book_id, UNIT_RANGE_SIZE)
    if not ranges:
        await callback.answer("Bu kitobda hali so'zlar yo'q.", show_alert=True)
        return
    await callback.message.edit_text(
        "Unit diapazonini tanlang:", reply_markup=ranges_kb(book_id, ranges)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("singleunits:"))
async def choose_single_unit_menu(callback: CallbackQuery):
    book_id = int(callback.data.split(":")[1])
    units = await db.list_units(book_id)
    if not units:
        await callback.answer("Bu kitobda hali unit yo'q.", show_alert=True)
        return
    unit_numbers = sorted(u["number"] for u in units)
    await callback.message.edit_text(
        "Bitta unitni tanlang:", reply_markup=single_units_kb(book_id, unit_numbers)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("range:"))
async def choose_range(callback: CallbackQuery):
    _, book_id, unit_from, unit_to = callback.data.split(":")
    book_id, unit_from, unit_to = int(book_id), int(unit_from), int(unit_to)
    words = await db.list_words_in_range(book_id, unit_from, unit_to)
    if not words:
        await callback.answer("Bu diapazonda so'zlar topilmadi.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Bu diapazonda {len(words)} ta so'z bor.\n\nNechta savol yechmoqchisiz?",
        reply_markup=count_kb(book_id, unit_from, unit_to, len(words)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("count:"))
async def choose_count(callback: CallbackQuery):
    _, book_id, unit_from, unit_to, count = callback.data.split(":")
    question_count = None if count == "all" else int(count)
    await start_quiz(
        callback, int(book_id), int(unit_from), int(unit_to), question_count
    )


async def start_quiz(
    callback: CallbackQuery, book_id: int, unit_from: int, unit_to: int, question_count: int | None
):
    words = await db.list_words_in_range(book_id, unit_from, unit_to)
    if not words:
        await callback.answer("Bu diapazonda so'zlar topilmadi.", show_alert=True)
        return
    remaining = [dict(w) for w in words]
    random.shuffle(remaining)
    if question_count is not None:
        remaining = remaining[:question_count]
    SESSIONS[callback.from_user.id] = {
        "book_id": book_id,
        "unit_from": unit_from,
        "unit_to": unit_to,
        "remaining": remaining,
        "current": None,
        "total_words": len(remaining),
        "asked": 0,
        "total": 0,
        "correct": 0,
        "wrong": 0,
        "user_name": callback.from_user.full_name,
        "username": callback.from_user.username,
        "lang": await db.get_user_lang(callback.from_user.id),
    }
    await save_session(callback.from_user.id)
    await callback.answer()
    await ask_next_question(callback.message, callback.from_user.id)


async def build_question(user_telegram_id: int) -> dict:
    session = SESSIONS[user_telegram_id]
    session["asked"] += 1
    word_row = session["remaining"].pop()
    lang = session["lang"]
    translation_ru = word_row["translation_ru"] or word_row["translation"]
    correct_text = translation_ru if lang == "ru" else word_row["translation"]
    wrong = await db.random_wrong_translations(
        session["book_id"],
        word_row["id"],
        QUESTION_OPTIONS_COUNT - 1,
        lang=lang,
        exclude_text=correct_text,
    )
    options = [correct_text] + wrong
    random.shuffle(options)
    correct_index = options.index(correct_text)
    question = {
        "word_id": word_row["id"],
        "word": word_row["word"],
        "translation": correct_text,
        "translation_uz": word_row["translation"],
        "translation_ru": translation_ru,
        "options": options,
        "correct_index": correct_index,
    }
    session["current"] = question
    await save_session(user_telegram_id)
    return question


async def ask_next_question(message: Message, user_telegram_id: int):
    session = await get_session(user_telegram_id)
    if session is None:
        return

    if not session["remaining"]:
        await finish_quiz(message, user_telegram_id)
        return

    question = await build_question(user_telegram_id)
    text = (
        f"📖 Savol {session['asked']}/{session['total_words']}   "
        f"✅ {session['correct']}  ❌ {session['wrong']}\n\n"
        f"So'z:\n<b>{question['word']}</b>"
    )
    await message.edit_text(text, reply_markup=options_kb(question["options"]), parse_mode="HTML")


async def notify_admins(bot, user_telegram_id: int, session: dict, total: int, correct: int, wrong: int, percent: int):
    book = await db.get_book(session["book_id"])
    book_name = book["name"] if book else "?"
    unit_from, unit_to = session["unit_from"], session["unit_to"]
    units = f"Unit {unit_from}" if unit_from == unit_to else f"Unit {unit_from}–{unit_to}"
    username = f"@{session['username']}" if session.get("username") else "—"
    text = (
        "📩 <b>Yangi natija</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"👤 {html.escape(session.get('user_name') or '—')} ({html.escape(username)})\n"
        f"🆔 <code>{user_telegram_id}</code>\n"
        f"📚 {html.escape(book_name)} — {units}\n"
        f"🎯 Natija: {correct}/{total} ({percent}%)\n"
        f"✅ {correct}   ❌ {wrong}\n"
        f"🕓 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logger.warning(f"Adminga ({admin_id}) hisobot yuborib bo'lmadi: {e}")


async def finish_quiz(message: Message, user_telegram_id: int):
    session = await get_session(user_telegram_id)
    if session is None:
        return
    total = session["total"]
    correct = session["correct"]
    wrong = session["wrong"]
    percent = round(correct / total * 100) if total else 0

    # drop first: a double tap on "next" must not record the result twice
    await drop_session(user_telegram_id)
    await db.add_user_result(user_telegram_id, correct, wrong)
    await notify_admins(message.bot, user_telegram_id, session, total, correct, wrong, percent)

    text = (
        "🎉 Tabriklaymiz! Siz tanlangan Unit(lar)ni yakunladingiz.\n\n"
        "📊 Natijangiz\n"
        "━━━━━━━━━━━━━━\n"
        f"📝 Jami savollar: {total}\n"
        f"✅ To'g'ri: {correct}\n"
        f"❌ Noto'g'ri: {wrong}\n"
        f"🎯 Natija: {correct}/{total} ({percent}%)\n"
        "━━━━━━━━━━━━━━\n\n"
        "Qayta boshlaysizmi?"
    )
    await message.edit_text(
        text,
        reply_markup=restart_kb(session["book_id"], session["unit_from"], session["unit_to"]),
    )


@router.callback_query(F.data.startswith("ans:"))
async def answer_question(callback: CallbackQuery):
    session = await get_session(callback.from_user.id)
    if session is None or session["current"] is None:
        await callback.answer("Sessiya topilmadi. /start ni bosing.", show_alert=True)
        return

    chosen_index = int(callback.data.split(":")[1])
    question = session["current"]
    session["total"] += 1

    both_langs = (
        f"🇺🇿 {html.escape(question['translation_uz'], quote=False)}\n"
        f"🇷🇺 {html.escape(question['translation_ru'], quote=False)}"
    )
    if chosen_index == question["correct_index"]:
        session["correct"] += 1
        text = f"✅ To'g'ri!\n\n<b>{question['word']}</b>\n{both_langs}"
    else:
        session["wrong"] += 1
        correct_letter = chr(65 + question["correct_index"])
        text = (
            f"❌ Noto'g'ri.\n\n<b>{question['word']}</b>\n\n"
            f"To'g'ri javob: {correct_letter})\n{both_langs}"
        )

    session["current"] = None
    await save_session(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=next_question_kb())
    await callback.answer()


@router.callback_query(F.data == "next")
async def next_question(callback: CallbackQuery):
    session = await get_session(callback.from_user.id)
    if session is None:
        await callback.answer("Sessiya topilmadi. /start ni bosing.", show_alert=True)
        return
    await callback.answer()
    await ask_next_question(callback.message, callback.from_user.id)


@router.message(Command("admin"))
async def cmd_admin_denied(message: Message):
    """Reached only when the admin router's ADMIN_IDS filter rejected the user."""
    await message.answer("⛔ Sizda admin huquqi yo'q.")
