"""
Bazani tekshirish uchun namunaviy (demo) so'zlar bilan to'ldiradi.
Bu Essential English Words kitobining haqiqiy matni EMAS — faqat botni
sinab ko'rish uchun umumiy inglizcha so'zlar va tarjimalari.

Ishga tushirish: python seed_demo.py
"""

import asyncio

from bot.database import db

DEMO = {
    "1-kitob (demo)": {
        1: [
            ("abandon", "tark etmoq"),
            ("benefit", "foyda"),
            ("candidate", "nomzod"),
            ("delicate", "nozik"),
            ("efficient", "samarali"),
        ],
        2: [
            ("fragile", "mo'rt"),
            ("generous", "saxiy"),
            ("harvest", "hosil"),
            ("immense", "ulkan"),
            ("journey", "sayohat"),
        ],
        3: [
            ("knowledge", "bilim"),
            ("liberty", "erkinlik"),
            ("modest", "kamtar"),
            ("neutral", "betaraf"),
            ("obvious", "aniq"),
        ],
    },
}


async def main():
    await db.init()
    for book_name, units in DEMO.items():
        book_id = await db.add_book(book_name)
        for unit_number, words in units.items():
            unit_id = await db.add_unit(book_id, unit_number)
            for word, translation in words:
                await db.add_word(unit_id, word, translation)
    print("Demo ma'lumotlar qo'shildi.")


if __name__ == "__main__":
    asyncio.run(main())
