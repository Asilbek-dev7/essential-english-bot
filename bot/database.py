import json
import random
import re
from pathlib import Path
from typing import Optional

import aiosqlite

from bot.config import DB_PATH, RU_TRANSLATIONS_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS units (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    number  INTEGER NOT NULL,
    UNIQUE(book_id, number)
);

CREATE TABLE IF NOT EXISTS words (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id     INTEGER NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    word        TEXT NOT NULL,
    translation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username    TEXT,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_stats (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total   INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    wrong   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    telegram_id INTEGER PRIMARY KEY,
    data        TEXT NOT NULL,
    updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# columns added after the initial release; applied to existing DBs via ALTER TABLE
_USER_STATS_EXTRA_COLUMNS = {
    "last_total": "INTEGER NOT NULL DEFAULT 0",
    "last_correct": "INTEGER NOT NULL DEFAULT 0",
    "last_wrong": "INTEGER NOT NULL DEFAULT 0",
    "last_played_at": "TEXT",
}

_BOOKS_EXTRA_COLUMNS = {
    "position": "INTEGER",
}

_WORDS_EXTRA_COLUMNS = {
    "translation_ru": "TEXT",
}

_USERS_EXTRA_COLUMNS = {
    "lang": "TEXT NOT NULL DEFAULT 'uz'",
}

LANGS = ("uz", "ru")


class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.executescript(SCHEMA)
            for table, extra in (
                ("user_stats", _USER_STATS_EXTRA_COLUMNS),
                ("books", _BOOKS_EXTRA_COLUMNS),
                ("words", _WORDS_EXTRA_COLUMNS),
                ("users", _USERS_EXTRA_COLUMNS),
            ):
                cur = await db.execute(f"PRAGMA table_info({table})")
                existing_columns = {row[1] for row in await cur.fetchall()}
                for name, col_type in extra.items():
                    if name not in existing_columns:
                        await db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")
            await db.execute(
                "DELETE FROM quiz_sessions WHERE updated_at < datetime('now', '-7 days')"
            )
            await db.commit()
        await self.apply_ru_translations()

    async def apply_ru_translations(self):
        """Fill translation_ru from data/ru_translations.txt (book|unit|word|ru) where still empty."""
        if not RU_TRANSLATIONS_PATH.exists():
            return
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM words WHERE translation_ru IS NULL")
            if (await cur.fetchone())[0] == 0:
                return
            cur = await db.execute("SELECT id, name FROM books")
            book_ids = {}
            for book_id, name in await cur.fetchall():
                m = re.search(r"(\d+)\s*$", name)
                if m:
                    book_ids[int(m.group(1))] = book_id
            rows = []
            for line in RU_TRANSLATIONS_PATH.read_text(encoding="utf-8").splitlines():
                parts = line.split("|", 3)
                if len(parts) != 4 or not parts[0].isdigit() or not parts[1].isdigit():
                    continue
                book_id = book_ids.get(int(parts[0]))
                if book_id is not None:
                    rows.append((parts[3].strip(), parts[2].strip(), book_id, int(parts[1])))
            await db.executemany(
                """UPDATE words SET translation_ru = ?
                   WHERE translation_ru IS NULL AND word = ?
                     AND unit_id = (SELECT id FROM units WHERE book_id = ? AND number = ?)""",
                rows,
            )
            await db.commit()

    # ---------- quiz sessions (survive bot restarts) ----------

    async def save_session(self, telegram_id: int, session: dict):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO quiz_sessions (telegram_id, data, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(telegram_id) DO UPDATE SET
                       data = excluded.data, updated_at = CURRENT_TIMESTAMP""",
                (telegram_id, json.dumps(session, ensure_ascii=False)),
            )
            await db.commit()

    async def load_session(self, telegram_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT data FROM quiz_sessions WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cur.fetchone()
        return json.loads(row[0]) if row else None

    async def delete_session(self, telegram_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM quiz_sessions WHERE telegram_id = ?", (telegram_id,))
            await db.commit()

    # ---------- user language ----------

    async def get_user_lang(self, telegram_id: int) -> str:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT lang FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cur.fetchone()
            return row[0] if row and row[0] in LANGS else "uz"

    async def set_user_lang(self, telegram_id: int, lang: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET lang = ? WHERE telegram_id = ?", (lang, telegram_id))
            await db.commit()

    # ---------- users ----------

    async def get_or_create_user(self, telegram_id: int, username: Optional[str]) -> int:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            cur = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cur.fetchone()
            if row:
                await db.execute(
                    "UPDATE users SET username = ? WHERE id = ?", (username, row[0])
                )
                await db.commit()
                return row[0]
            cur = await db.execute(
                "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
                (telegram_id, username),
            )
            await db.execute(
                "INSERT INTO user_stats (user_id) VALUES (?)", (cur.lastrowid,)
            )
            await db.commit()
            return cur.lastrowid

    async def get_user_stats(self, telegram_id: int) -> Optional[aiosqlite.Row]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """SELECT s.* FROM user_stats s
                   JOIN users u ON u.id = s.user_id
                   WHERE u.telegram_id = ?""",
                (telegram_id,),
            )
            return await cur.fetchone()

    async def add_user_result(self, telegram_id: int, correct: int, wrong: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            cur = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cur.fetchone()
            if not row:
                return
            user_id = row[0]
            await db.execute(
                """UPDATE user_stats
                   SET total = total + ?, correct = correct + ?, wrong = wrong + ?,
                       last_total = ?, last_correct = ?, last_wrong = ?,
                       last_played_at = CURRENT_TIMESTAMP
                   WHERE user_id = ?""",
                (correct + wrong, correct, wrong, correct + wrong, correct, wrong, user_id),
            )
            await db.commit()

    # ---------- books ----------

    async def add_book(self, name: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("INSERT INTO books (name) VALUES (?)", (name,))
            await db.commit()
            return cur.lastrowid

    async def list_books(self) -> list[aiosqlite.Row]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM books ORDER BY COALESCE(position, id), id")
            return list(await cur.fetchall())

    async def set_book_position(self, book_id: int, position: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE books SET position = ? WHERE id = ?", (position, book_id))
            await db.commit()

    async def get_book(self, book_id: int) -> Optional[aiosqlite.Row]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            return await cur.fetchone()

    async def get_book_by_name(self, name: str) -> Optional[aiosqlite.Row]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM books WHERE name = ?", (name,))
            return await cur.fetchone()

    async def delete_book(self, book_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
            await db.commit()

    # ---------- units ----------

    async def add_unit(self, book_id: int, number: int) -> Optional[int]:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            try:
                cur = await db.execute(
                    "INSERT INTO units (book_id, number) VALUES (?, ?)", (book_id, number)
                )
                await db.commit()
                return cur.lastrowid
            except aiosqlite.IntegrityError:
                return None

    async def get_or_create_unit(self, book_id: int, number: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            cur = await db.execute(
                "SELECT id FROM units WHERE book_id = ? AND number = ?", (book_id, number)
            )
            row = await cur.fetchone()
            if row:
                return row[0]
            cur = await db.execute(
                "INSERT INTO units (book_id, number) VALUES (?, ?)", (book_id, number)
            )
            await db.commit()
            return cur.lastrowid

    async def list_units(self, book_id: int) -> list[aiosqlite.Row]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM units WHERE book_id = ? ORDER BY number", (book_id,)
            )
            return list(await cur.fetchall())

    async def get_unit_ranges(self, book_id: int, range_size: int) -> list[tuple[int, int]]:
        units = await self.list_units(book_id)
        if not units:
            return []
        numbers = sorted(u["number"] for u in units)
        max_unit = numbers[-1]
        ranges = []
        start = 1
        while start <= max_unit:
            end = start + range_size - 1
            if any(start <= n <= end for n in numbers):
                ranges.append((start, end))
            start = end + 1
        return ranges

    # ---------- words ----------

    async def add_word(
        self, unit_id: int, word: str, translation: str, translation_ru: Optional[str] = None
    ) -> int:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            cur = await db.execute(
                "INSERT INTO words (unit_id, word, translation, translation_ru) VALUES (?, ?, ?, ?)",
                (unit_id, word, translation, translation_ru),
            )
            await db.commit()
            return cur.lastrowid

    async def get_word(self, word_id: int) -> Optional[aiosqlite.Row]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM words WHERE id = ?", (word_id,))
            return await cur.fetchone()

    async def update_word(
        self, word_id: int, word: str, translation: str, translation_ru: Optional[str] = None
    ):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE words SET word = ?, translation = ?, translation_ru = ? WHERE id = ?",
                (word, translation, translation_ru, word_id),
            )
            await db.commit()

    async def delete_word(self, word_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM words WHERE id = ?", (word_id,))
            await db.commit()

    async def list_words_in_unit(self, unit_id: int) -> list[aiosqlite.Row]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM words WHERE unit_id = ? ORDER BY id", (unit_id,)
            )
            return list(await cur.fetchall())

    async def list_words_in_range(
        self, book_id: int, unit_from: int, unit_to: int
    ) -> list[aiosqlite.Row]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """SELECT w.* FROM words w
                   JOIN units u ON u.id = w.unit_id
                   WHERE u.book_id = ? AND u.number BETWEEN ? AND ?
                   ORDER BY w.id""",
                (book_id, unit_from, unit_to),
            )
            return list(await cur.fetchall())

    async def random_wrong_translations(
        self,
        book_id: int,
        exclude_word_id: int,
        count: int,
        lang: str = "uz",
        exclude_text: Optional[str] = None,
    ) -> list[str]:
        column = (
            "COALESCE(NULLIF(w.translation_ru, ''), w.translation)"
            if lang == "ru"
            else "w.translation"
        )
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                f"""SELECT DISTINCT {column} AS tr FROM words w
                    JOIN units u ON u.id = w.unit_id
                    WHERE u.book_id = ? AND w.id != ?""",
                (book_id, exclude_word_id),
            )
            rows = [r["tr"] for r in await cur.fetchall() if r["tr"] != exclude_text]
        random.shuffle(rows)
        if len(rows) >= count:
            return rows[:count]
        # not enough distractors in this book -> pull from any book
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                f"SELECT DISTINCT {column} AS tr FROM words w WHERE w.id != ?",
                (exclude_word_id,),
            )
            all_rows = [
                r["tr"] for r in await cur.fetchall() if r["tr"] not in rows and r["tr"] != exclude_text
            ]
        random.shuffle(all_rows)
        return (rows + all_rows)[:count]


db = Database()
