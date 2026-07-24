import random

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import ADMIN_IDS, QUESTION_OPTIONS_COUNT, UNIT_RANGE_SIZE
from bot.database import db
from bot.keyboards import (
    admin_menu_kb,
    book_list_reply_kb,
    count_kb,
    main_menu_reply_kb,
    next_question_kb,
    options_kb,
    ranges_kb,
    restart_kb,
)

router = Router(name="user")

# telegram_id -> quiz session dict, kept in memory for the lifetime of the process
SESSIONS: dict[int, dict] = {}


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
    SESSIONS.pop(message.from_user.id, None)
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
    SESSIONS.pop(message.from_user.id, None)
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


@router.message(F.text == "ℹ️ Yordam")
async def menu_help(message: Message):
    text = (
        "ℹ️ Yordam\n\n"
        "📚 Kitoblar — kitob, Unit diapazoni va savollar sonini tanlab, test yeching\n"
        "📊 Natijalarim — barcha vaqtdagi statistikangiz va oxirgi natijangiz\n"
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
    SESSIONS.pop(message.from_user.id, None)
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
    remaining = list(words)
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
    }
    await callback.answer()
    await ask_next_question(callback.message, callback.from_user.id)


async def build_question(user_telegram_id: int) -> dict:
    session = SESSIONS[user_telegram_id]
    session["asked"] += 1
    word_row = session["remaining"].pop()
    wrong = await db.random_wrong_translations(
        session["book_id"], word_row["id"], QUESTION_OPTIONS_COUNT - 1
    )
    options = [word_row["translation"]] + wrong
    random.shuffle(options)
    correct_index = options.index(word_row["translation"])
    question = {
        "word_id": word_row["id"],
        "word": word_row["word"],
        "translation": word_row["translation"],
        "options": options,
        "correct_index": correct_index,
    }
    session["current"] = question
    return question


async def ask_next_question(message: Message, user_telegram_id: int):
    session = SESSIONS.get(user_telegram_id)
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


async def finish_quiz(message: Message, user_telegram_id: int):
    session = SESSIONS.get(user_telegram_id)
    if session is None:
        return
    total = session["total"]
    correct = session["correct"]
    wrong = session["wrong"]
    percent = round(correct / total * 100) if total else 0

    await db.add_user_result(user_telegram_id, correct, wrong)

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
    session = SESSIONS.get(callback.from_user.id)
    if session is None or session["current"] is None:
        await callback.answer("Sessiya topilmadi. /start ni bosing.", show_alert=True)
        return

    chosen_index = int(callback.data.split(":")[1])
    question = session["current"]
    session["total"] += 1

    if chosen_index == question["correct_index"]:
        session["correct"] += 1
        text = f"✅ To'g'ri!\n\n<b>{question['word']}</b> — {question['translation']}"
    else:
        session["wrong"] += 1
        correct_letter = chr(65 + question["correct_index"])
        text = (
            f"❌ Noto'g'ri.\n\n<b>{question['word']}</b>\n\n"
            f"To'g'ri javob:\n{correct_letter}) {question['translation']}"
        )

    session["current"] = None
    await callback.message.edit_text(text, reply_markup=next_question_kb())
    await callback.answer()


@router.callback_query(F.data == "next")
async def next_question(callback: CallbackQuery):
    session = SESSIONS.get(callback.from_user.id)
    if session is None:
        await callback.answer("Sessiya topilmadi. /start ni bosing.", show_alert=True)
        return
    await callback.answer()
    await ask_next_question(callback.message, callback.from_user.id)


@router.message(Command("admin"))
async def cmd_admin_denied(message: Message):
    """Reached only when the admin router's ADMIN_IDS filter rejected the user."""
    await message.answer("⛔ Sizda admin huquqi yo'q.")
