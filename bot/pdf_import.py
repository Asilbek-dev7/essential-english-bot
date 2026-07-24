import io
import re

import pdfplumber

_UNIT_RE = re.compile(r"unit\s*(\d+)", re.IGNORECASE)

# allows short multi-word terms like "vice versa"
_WORD = r"[A-Za-z][A-Za-z'\-]*(?:\s[A-Za-z][A-Za-z'\-]*){0,2}"

_LINE_PATTERNS = [
    # "1. abandon - tark etmoq" (numbered list)
    re.compile(rf"^\s*\d+[.\)]\s*({_WORD})\s*[-–—:]\s*(.+?)\s*$"),
    # "abandon - tark etmoq" / "abandon: tark etmoq"
    re.compile(rf"^\s*({_WORD})\s*[-–—:]\s*(.+?)\s*$"),
    # "abandon\ttark etmoq" (tab separated, common in copy-pasted tables)
    re.compile(rf"^\s*({_WORD})\t+(.+?)\s*$"),
    # "abandon    tark etmoq" (2+ spaces, PDF table extraction)
    re.compile(rf"^\s*({_WORD})\s{{2,}}(.+?)\s*$"),
]

_STOP_WORDS = {
    "unit", "page", "word", "words", "contents", "index",
    "essential", "english", "book", "chapter", "exercise", "exercises",
}


def parse_pdf_text(text: str) -> tuple[list[tuple[int, str, str]], int]:
    """Returns (entries, skipped_line_count). entries = [(unit_number, word, translation), ...]"""
    entries: list[tuple[int, str, str]] = []
    skipped = 0
    current_unit = 1

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading = _UNIT_RE.search(line)
        if heading and len(line) < 40:
            current_unit = int(heading.group(1))
            continue

        matched = False
        for pattern_index, pattern in enumerate(_LINE_PATTERNS):
            m = pattern.match(line)
            if not m:
                continue
            word, translation = m.group(1).strip(), m.group(2).strip()
            if len(word) < 2 or not translation:
                continue
            # Only the weak (space-separated) pattern is prone to matching
            # title/heading lines, so only it gets filtered against stop words.
            is_weak_pattern = pattern_index == len(_LINE_PATTERNS) - 1
            if is_weak_pattern and (
                word.lower() in _STOP_WORDS or translation.lower() in _STOP_WORDS
            ):
                continue
            entries.append((current_unit, word, translation))
            matched = True
            break

        if not matched:
            skipped += 1

    return entries, skipped


def extract_pdf_text(data: bytes) -> str:
    chunks = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            chunks.append(page_text)
    return "\n".join(chunks)


def parse_pdf_bytes(data: bytes) -> tuple[list[tuple[int, str, str]], int]:
    text = extract_pdf_text(data)
    return parse_pdf_text(text)
