from __future__ import annotations

import re

BOOK_TITLES = {
    "genesis": "Genesis",
    "exodus": "Exodus",
    "isaiah": "Isaiah",
    "psalms": "Psalms",
    "matthew": "Matthew",
    "john": "John",
    "acts": "Acts",
    "romans": "Romans",
    "1corinthians": "1 Corinthians",
    "ephesians": "Ephesians",
    "hebrews": "Hebrews",
    "james": "James",
    "1peter": "1 Peter",
    "1john": "1 John",
}

WORD_RE = re.compile(r"[A-Za-z']+")
STRONGS_RE = re.compile(r"\b[GH]\d{1,5}\b", re.IGNORECASE)


def pretty_ref(book: str, chapter: int, verse: int) -> str:
    return f"{BOOK_TITLES.get(book.lower(), book.title())} {chapter}:{verse}"


def tokenize_words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def parse_strongs_codes(strongs: str) -> list[str]:
    return [code.upper() for code in STRONGS_RE.findall(strongs or "")]
