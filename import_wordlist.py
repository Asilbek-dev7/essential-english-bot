"""
Matn ko'rinishidagi so'z ro'yxatini ("Unit N" sarlavhalari va
"so'z - tarjima" qatorlari bilan) bazaga import qiladi.

Ishlatish:
    python import_wordlist.py "<fayl_yoli.txt>" "<Kitob nomi>"
"""

import asyncio
import sys
from pathlib import Path

from bot.database import db
from bot.pdf_import import parse_pdf_text


async def import_file(path: str, book_name: str):
    text = Path(path).read_text(encoding="utf-8")
    entries, skipped = parse_pdf_text(text)

    await db.init()
    existing = await db.get_book_by_name(book_name)
    book_id = existing["id"] if existing else await db.add_book(book_name)

    added = 0
    for unit_number, word, translation in entries:
        unit_id = await db.get_or_create_unit(book_id, unit_number)
        await db.add_word(unit_id, word, translation)
        added += 1

    print(f"Kitob: {book_name} (id={book_id})")
    print(f"Qo'shildi: {added} ta so'z")
    print(f"Aniqlanmagan qatorlar: {skipped}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('Ishlatish: python import_wordlist.py "<fayl.txt>" "<Kitob nomi>"')
        sys.exit(1)
    asyncio.run(import_file(sys.argv[1], sys.argv[2]))
