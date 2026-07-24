from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ---------- persistent bottom menu ----------

def main_menu_reply_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="📚 Kitoblar")],
        [KeyboardButton(text="📊 Natijalarim"), KeyboardButton(text="ℹ️ Yordam")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="🛠 Admin panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def book_list_reply_kb(books) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=book["name"])] for book in books]
    rows.append([KeyboardButton(text="⬅️ Orqaga")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


# ---------- user flow ----------


def ranges_kb(book_id: int, ranges: list[tuple[int, int]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for start, end in ranges:
        b.button(text=f"{start}–{end}", callback_data=f"range:{book_id}:{start}:{end}")
    b.button(text="⬅️ Orqaga", callback_data="back_to_books")
    b.adjust(2)
    return b.as_markup()


def count_kb(book_id: int, unit_from: int, unit_to: int, available: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for n in (5, 10, 15, 20, 30):
        if n < available:
            b.button(text=str(n), callback_data=f"count:{book_id}:{unit_from}:{unit_to}:{n}")
    b.button(
        text=f"Barchasi ({available})",
        callback_data=f"count:{book_id}:{unit_from}:{unit_to}:all",
    )
    b.button(text="⬅️ Orqaga", callback_data=f"book:{book_id}")
    b.adjust(3)
    return b.as_markup()


def options_kb(options: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for idx, opt in enumerate(options):
        b.button(text=f"{chr(65 + idx)}) {opt}", callback_data=f"ans:{idx}")
    b.adjust(1)
    return b.as_markup()


def next_question_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➡️ Keyingi savol", callback_data="next")
    return b.as_markup()


def restart_kb(book_id: int, unit_from: int, unit_to: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔁 Qayta boshlash", callback_data=f"range:{book_id}:{unit_from}:{unit_to}")
    b.button(text="📚 Kitoblar", callback_data="back_to_books")
    b.adjust(1)
    return b.as_markup()


# ---------- admin flow ----------

def admin_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📚 Kitob qo'shish", callback_data="adm:add_book")
    b.button(text="📖 Unit qo'shish", callback_data="adm:add_unit")
    b.button(text="➕ So'z qo'shish", callback_data="adm:add_word")
    b.button(text="📂 So'zlarni ko'rish/tahrirlash", callback_data="adm:browse")
    b.button(text="📥 Ko'p so'zni birdan yuklash", callback_data="adm:bulk_import")
    b.adjust(1)
    return b.as_markup()


def admin_books_kb(books, purpose: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for book in books:
        b.button(text=book["name"], callback_data=f"adm_book:{purpose}:{book['id']}")
    b.button(text="⬅️ Orqaga", callback_data="adm:menu")
    b.adjust(1)
    return b.as_markup()


def admin_units_kb(units, purpose: str, book_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for unit in units:
        b.button(text=f"Unit {unit['number']}", callback_data=f"adm_unit:{purpose}:{unit['id']}")
    b.button(text="⬅️ Orqaga", callback_data=f"adm_book_back:{purpose}:{book_id}")
    b.adjust(2)
    return b.as_markup()


def admin_words_kb(words, unit_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for w in words:
        b.button(text=w["word"], callback_data=f"adm_word:{w['id']}")
    b.button(text="⬅️ Orqaga", callback_data="adm:browse")
    b.adjust(2)
    return b.as_markup()


def admin_word_detail_kb(word_id: int, unit_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Tahrirlash", callback_data=f"adm_word_edit:{word_id}")
    b.button(text="🗑 O'chirish", callback_data=f"adm_word_del:{word_id}")
    b.button(text="⬅️ Orqaga", callback_data=f"adm_unit:browse:{unit_id}")
    b.adjust(1)
    return b.as_markup()


def admin_confirm_delete_kb(word_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ha, o'chirish", callback_data=f"adm_word_del_confirm:{word_id}")
    b.button(text="❌ Bekor qilish", callback_data=f"adm_word:{word_id}")
    b.adjust(1)
    return b.as_markup()


def admin_pdf_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ha, bazaga qo'shish", callback_data="adm_pdf_confirm")
    b.button(text="❌ Bekor qilish", callback_data="adm:menu")
    b.adjust(1)
    return b.as_markup()


def admin_cancel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="❌ Bekor qilish", callback_data="adm:menu")
    return b.as_markup()
