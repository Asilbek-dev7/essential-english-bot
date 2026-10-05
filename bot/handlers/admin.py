import io

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import ADMIN_IDS
from bot.database import db
from bot.keyboards import (
    admin_books_kb,
    admin_cancel_kb,
    admin_confirm_delete_kb,
    admin_menu_kb,
    admin_pdf_confirm_kb,
    admin_units_kb,
    admin_word_detail_kb,
    admin_words_kb,
)
from bot.pdf_import import parse_pdf_bytes
from bot.states import AdminStates

router = Router(name="admin")
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


async def show_books_for_purpose(target, purpose: str, edit: bool = True):
    books = await db.list_books()
    if not books:
        text = "Kitoblar yo'q. Avval \"📚 Kitob qo'shish\" orqali kitob qo'shing."
        if isinstance(target, CallbackQuery):
            await target.answer(text, show_alert=True)
        else:
            await target.answer(text)
        return
    text = "Kitobni tanlang:"
    markup = admin_books_kb(books, purpose)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


async def show_units_for_purpose(callback: CallbackQuery, purpose: str, book_id: int):
    units = await db.list_units(book_id)
    if not units:
        await callback.answer(
            "Bu kitobda hali unit yo'q. Avval \"📖 Unit qo'shish\" orqali unit qo'shing.",
            show_alert=True,
        )
        return
    await callback.message.edit_text(
        "Unitni tanlang:", reply_markup=admin_units_kb(units, purpose, book_id)
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🛠 Admin panel", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "adm:menu")
async def adm_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛠 Admin panel", reply_markup=admin_menu_kb())
    await callback.answer()


# ---------- add book ----------

@router.callback_query(F.data == "adm:add_book")
async def adm_add_book(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_book_name)
    await callback.message.edit_text(
        "Kitob nomini kiriting (masalan: 1-kitob):", reply_markup=admin_cancel_kb()
    )
    await callback.answer()


@router.message(AdminStates.add_book_name)
async def adm_add_book_save(message: Message, state: FSMContext):
    name = message.text.strip()
    try:
        await db.add_book(name)
        await message.answer(f"✅ Kitob qo'shildi: {name}", reply_markup=admin_menu_kb())
    except Exception:
        await message.answer(
            "⚠️ Bu nomdagi kitob allaqachon mavjud yoki xatolik yuz berdi.",
            reply_markup=admin_menu_kb(),
        )
    await state.clear()


# ---------- add unit ----------

@router.callback_query(F.data == "adm:add_unit")
async def adm_add_unit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_unit_choose_book)
    await show_books_for_purpose(callback, "unit")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_book:unit:"))
async def adm_add_unit_book_chosen(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[2])
    await state.update_data(book_id=book_id)
    await state.set_state(AdminStates.add_unit_number)
    await callback.message.edit_text(
        "Unit raqamini kiriting (masalan: 4):", reply_markup=admin_cancel_kb()
    )
    await callback.answer()


@router.message(AdminStates.add_unit_number)
async def adm_add_unit_save(message: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data["book_id"]
    if not message.text.strip().isdigit():
        await message.answer("Raqam kiriting, masalan: 4")
        return
    number = int(message.text.strip())
    unit_id = await db.add_unit(book_id, number)
    if unit_id is None:
        await message.answer(f"⚠️ Unit {number} allaqachon mavjud.", reply_markup=admin_menu_kb())
    else:
        await message.answer(f"✅ Unit {number} qo'shildi.", reply_markup=admin_menu_kb())
    await state.clear()


# ---------- add word ----------

@router.callback_query(F.data == "adm:add_word")
async def adm_add_word(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_word_choose_book)
    await show_books_for_purpose(callback, "word")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_book:word:"))
async def adm_add_word_book_chosen(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[2])
    await state.update_data(book_id=book_id)
    await state.set_state(AdminStates.add_word_choose_unit)
    await show_units_for_purpose(callback, "word", book_id)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_book_back:word:"))
async def adm_add_word_book_back(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_word_choose_book)
    await show_books_for_purpose(callback, "word")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_unit:word:"))
async def adm_add_word_unit_chosen(callback: CallbackQuery, state: FSMContext):
    unit_id = int(callback.data.split(":")[2])
    await state.update_data(unit_id=unit_id)
    await state.set_state(AdminStates.add_word_text)
    await callback.message.edit_text(
        "So'zni kiriting (inglizcha):", reply_markup=admin_cancel_kb()
    )
    await callback.answer()


@router.message(AdminStates.add_word_text)
async def adm_add_word_text(message: Message, state: FSMContext):
    await state.update_data(word=message.text.strip())
    await state.set_state(AdminStates.add_word_translation)
    await message.answer("Tarjimasini kiriting:", reply_markup=admin_cancel_kb())


@router.message(AdminStates.add_word_translation)
async def adm_add_word_translation(message: Message, state: FSMContext):
    await state.update_data(translation=message.text.strip())
    await state.set_state(AdminStates.add_word_translation_ru)
    await message.answer(
        "Ruscha tarjimasini kiriting (o'tkazib yuborish uchun - yuboring):",
        reply_markup=admin_cancel_kb(),
    )


@router.message(AdminStates.add_word_translation_ru)
async def adm_add_word_translation_ru(message: Message, state: FSMContext):
    data = await state.get_data()
    translation_ru = None if message.text.strip() == "-" else message.text.strip()
    await db.add_word(data["unit_id"], data["word"], data["translation"], translation_ru)
    await message.answer(
        f"✅ So'z qo'shildi:\n\n{data['word']} — {data['translation']}\n🇷🇺 {translation_ru or '—'}",
        reply_markup=admin_menu_kb(),
    )
    await state.clear()


# ---------- browse / edit / delete ----------

@router.callback_query(F.data == "adm:browse")
async def adm_browse(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.browse_choose_book)
    await show_books_for_purpose(callback, "browse")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_book:browse:"))
async def adm_browse_book_chosen(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[2])
    await state.update_data(book_id=book_id)
    await state.set_state(AdminStates.browse_choose_unit)
    await show_units_for_purpose(callback, "browse", book_id)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_book_back:browse:"))
async def adm_browse_book_back(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.browse_choose_book)
    await show_books_for_purpose(callback, "browse")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_unit:browse:"))
async def adm_browse_unit_chosen(callback: CallbackQuery):
    unit_id = int(callback.data.split(":")[2])
    words = await db.list_words_in_unit(unit_id)
    if not words:
        await callback.answer("Bu unitda so'z yo'q.", show_alert=True)
        return
    await callback.message.edit_text(
        "So'zni tanlang:", reply_markup=admin_words_kb(words, unit_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_word:"))
async def adm_word_detail(callback: CallbackQuery):
    word_id = int(callback.data.split(":")[1])
    word = await db.get_word(word_id)
    if word is None:
        await callback.answer("So'z topilmadi.", show_alert=True)
        return
    text = (
        f"Word:\n{word['word']}\n\nTranslation:\n{word['translation']}\n\n"
        f"Перевод:\n{word['translation_ru'] or '—'}"
    )
    await callback.message.edit_text(
        text, reply_markup=admin_word_detail_kb(word_id, word["unit_id"])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_word_edit:"))
async def adm_word_edit_start(callback: CallbackQuery, state: FSMContext):
    word_id = int(callback.data.split(":")[1])
    word = await db.get_word(word_id)
    if word is None:
        await callback.answer("So'z topilmadi.", show_alert=True)
        return
    await state.update_data(word_id=word_id)
    await state.set_state(AdminStates.edit_word_text)
    await callback.message.edit_text(
        f"Joriy so'z: {word['word']}\n\nYangi so'zni kiriting:", reply_markup=admin_cancel_kb()
    )
    await callback.answer()


@router.message(AdminStates.edit_word_text)
async def adm_word_edit_text(message: Message, state: FSMContext):
    await state.update_data(word=message.text.strip())
    await state.set_state(AdminStates.edit_word_translation)
    await message.answer("Yangi tarjimani kiriting:", reply_markup=admin_cancel_kb())


@router.message(AdminStates.edit_word_translation)
async def adm_word_edit_translation(message: Message, state: FSMContext):
    await state.update_data(translation=message.text.strip())
    await state.set_state(AdminStates.edit_word_translation_ru)
    await message.answer(
        "Yangi ruscha tarjimani kiriting (o'zgartirmaslik uchun - yuboring):",
        reply_markup=admin_cancel_kb(),
    )


@router.message(AdminStates.edit_word_translation_ru)
async def adm_word_edit_translation_ru(message: Message, state: FSMContext):
    data = await state.get_data()
    current = await db.get_word(data["word_id"])
    keep = message.text.strip() == "-"
    translation_ru = (current["translation_ru"] if current else None) if keep else message.text.strip()
    await db.update_word(data["word_id"], data["word"], data["translation"], translation_ru)
    await message.answer(
        f"✅ So'z yangilandi:\n\n{data['word']} — {data['translation']}\n🇷🇺 {translation_ru or '—'}",
        reply_markup=admin_menu_kb(),
    )
    await state.clear()


@router.callback_query(F.data.startswith("adm_word_del:"))
async def adm_word_delete_confirm(callback: CallbackQuery):
    word_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "So'zni o'chirishni tasdiqlaysizmi?", reply_markup=admin_confirm_delete_kb(word_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_word_del_confirm:"))
async def adm_word_delete(callback: CallbackQuery):
    word_id = int(callback.data.split(":")[1])
    await db.delete_word(word_id)
    await callback.message.edit_text("🗑 So'z o'chirildi.", reply_markup=admin_menu_kb())
    await callback.answer()


# ---------- bulk import ----------

@router.callback_query(F.data == "adm:bulk_import")
async def adm_bulk_import_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.bulk_import_choose_book)
    await show_books_for_purpose(callback, "bulk")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_book:bulk:"))
async def adm_bulk_import_book_chosen(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[2])
    await state.update_data(book_id=book_id)
    await state.set_state(AdminStates.bulk_import_wait_file)
    await callback.message.edit_text(
        "So'zlarni qo'shishning ikki yo'li bor:\n\n"
        "1️⃣ <b>Matn / .txt fayl</b> — har bir qatorda:\n"
        "<code>unit|so'z|tarjima|ruscha (ixtiyoriy)</code>\n"
        "Masalan:\n<code>4|abandon|tark etmoq|покидать\n4|benefit|foyda</code>\n\n"
        "2️⃣ <b>Kitobning PDF fayli</b> — shunchaki PDF faylni shu yerga yuboring, "
        "bot o'zi matnni o'qib, so'z va tarjimalarni aniqlashga harakat qiladi "
        "(qo'shishdan oldin natijani ko'rsatib, tasdiqlashingizni so'raydi).",
        reply_markup=admin_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.bulk_import_wait_file)
async def adm_bulk_import_process(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    book_id = data["book_id"]

    is_pdf = message.document and (
        (message.document.mime_type or "") == "application/pdf"
        or (message.document.file_name or "").lower().endswith(".pdf")
    )

    if is_pdf:
        await handle_pdf_upload(message, state, bot, book_id)
        return

    if message.document:
        buf = io.BytesIO()
        await bot.download(message.document, destination=buf)
        content = buf.getvalue().decode("utf-8", errors="ignore")
    elif message.text:
        content = message.text
    else:
        await message.answer("Matn, .txt yoki PDF fayl yuboring.")
        return

    added = 0
    errors = []
    for i, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) not in (3, 4) or not parts[0].isdigit() or not parts[1] or not parts[2]:
            errors.append(i)
            continue
        unit_number, word, translation = int(parts[0]), parts[1], parts[2]
        translation_ru = parts[3] or None if len(parts) == 4 else None
        unit_id = await db.get_or_create_unit(book_id, unit_number)
        await db.add_word(unit_id, word, translation, translation_ru)
        added += 1

    summary = f"✅ {added} ta so'z qo'shildi."
    if errors:
        shown = ", ".join(str(x) for x in errors[:10])
        summary += f"\n⚠️ Xato qatorlar: {shown}" + (" ..." if len(errors) > 10 else "")
    await message.answer(summary, reply_markup=admin_menu_kb())
    await state.clear()


async def handle_pdf_upload(message: Message, state: FSMContext, bot: Bot, book_id: int):
    status = await message.answer("📄 PDF o'qilmoqda, biroz kuting...")
    buf = io.BytesIO()
    await bot.download(message.document, destination=buf)

    try:
        entries, skipped = parse_pdf_bytes(buf.getvalue())
    except Exception:
        await status.edit_text(
            "⚠️ PDF faylni o'qib bo'lmadi. Fayl buzilgan yoki himoyalangan bo'lishi mumkin.",
            reply_markup=admin_menu_kb(),
        )
        await state.clear()
        return

    if not entries:
        await status.edit_text(
            "⚠️ PDF ichidan so'z/tarjima juftliklari topilmadi.\n\n"
            "Sabab: PDF skanerlangan rasm bo'lishi mumkin (matn qatlami yo'q) yoki "
            "format kutilganidan farq qiladi. Matn (.txt) yoki \"unit|so'z|tarjima\" "
            "formatida yuborib ko'ring.",
            reply_markup=admin_menu_kb(),
        )
        await state.clear()
        return

    await state.update_data(pdf_entries=entries)
    await state.set_state(AdminStates.bulk_import_pdf_confirm)

    sample = "\n".join(f"Unit {u}: {w} — {t}" for u, w, t in entries[:8])
    text = (
        "📄 PDF tahlil qilindi.\n\n"
        f"✅ Aniqlangan so'zlar: {len(entries)}\n"
        f"⚠️ Aniqlanmagan qatorlar: {skipped}\n\n"
        f"Namuna:\n{sample}\n\n"
        "Diqqat: bu avtomatik tahlil, ba'zi qatorlar noto'g'ri aniqlangan bo'lishi mumkin. "
        "Bazaga qo'shishni tasdiqlaysizmi?"
    )
    await status.edit_text(text, reply_markup=admin_pdf_confirm_kb())


@router.callback_query(F.data == "adm_pdf_confirm")
async def adm_pdf_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    entries = data.get("pdf_entries") or []
    book_id = data.get("book_id")

    added = 0
    for unit_number, word, translation in entries:
        unit_id = await db.get_or_create_unit(book_id, unit_number)
        await db.add_word(unit_id, word, translation)
        added += 1

    await callback.message.edit_text(
        f"✅ {added} ta so'z bazaga qo'shildi.", reply_markup=admin_menu_kb()
    )
    await state.clear()
    await callback.answer()
