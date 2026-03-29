from __future__ import annotations

import difflib
from typing import Iterable

BOOK_ALIASES = {
    "gen": "genesis", "ge": "genesis", "gn": "genesis", "genesis": "genesis",
    "exo": "exodus", "exod": "exodus", "ex": "exodus", "exodus": "exodus",
    "lev": "leviticus", "leviticus": "leviticus",
    "num": "numbers", "numbers": "numbers",
    "deu": "deuteronomy", "deut": "deuteronomy", "deuteronomy": "deuteronomy",
    "jos": "joshua", "josh": "joshua", "joshua": "joshua",
    "jdg": "judges", "judg": "judges", "judges": "judges",
    "rut": "ruth", "ruth": "ruth",
    "1sa": "1samuel", "1 sam": "1samuel", "1 samuel": "1samuel", "1samuel": "1samuel",
    "2sa": "2samuel", "2 sam": "2samuel", "2 samuel": "2samuel", "2samuel": "2samuel",
    "1ki": "1kings", "1 kgs": "1kings", "1 kings": "1kings", "1kings": "1kings",
    "2ki": "2kings", "2 kgs": "2kings", "2 kings": "2kings", "2kings": "2kings",
    "1ch": "1chronicles", "1 chr": "1chronicles", "1 chronicles": "1chronicles", "1chronicles": "1chronicles",
    "2ch": "2chronicles", "2 chr": "2chronicles", "2 chronicles": "2chronicles", "2chronicles": "2chronicles",
    "ezr": "ezra", "ezra": "ezra", "neh": "nehemiah", "nehemiah": "nehemiah",
    "est": "esther", "esth": "esther", "esther": "esther", "job": "job",
    "ps": "psalms", "psa": "psalms", "psalm": "psalms", "psalms": "psalms",
    "prov": "proverbs", "pro": "proverbs", "proverbs": "proverbs",
    "ecc": "ecclesiastes", "eccl": "ecclesiastes", "ecclesiastes": "ecclesiastes",
    "song": "songofsolomon", "song of solomon": "songofsolomon", "songofsolomon": "songofsolomon", "sol": "songofsolomon",
    "isa": "isaiah", "isaiah": "isaiah", "jer": "jeremiah", "jeremiah": "jeremiah",
    "lam": "lamentations", "lamentations": "lamentations", "eze": "ezekiel", "ezek": "ezekiel", "ezekiel": "ezekiel",
    "dan": "daniel", "daniel": "daniel", "hos": "hosea", "hosea": "hosea",
    "joe": "joel", "joel": "joel", "amo": "amos", "amos": "amos",
    "oba": "obadiah", "obad": "obadiah", "obadiah": "obadiah", "jon": "jonah", "jonah": "jonah",
    "mic": "micah", "micah": "micah", "nah": "nahum", "nahum": "nahum",
    "hab": "habakkuk", "habakkuk": "habakkuk", "zep": "zephaniah", "zeph": "zephaniah", "zephaniah": "zephaniah",
    "hag": "haggai", "haggai": "haggai", "zec": "zechariah", "zech": "zechariah", "zechariah": "zechariah",
    "mal": "malachi", "malachi": "malachi", "mat": "matthew", "matt": "matthew", "matthew": "matthew",
    "mar": "mark", "mark": "mark", "luk": "luke", "luke": "luke", "joh": "john", "john": "john",
    "act": "acts", "acts": "acts", "rom": "romans", "roman": "romans", "romans": "romans",
    "1co": "1corinthians", "1 cor": "1corinthians", "1 corinthians": "1corinthians", "1corinthians": "1corinthians",
    "2co": "2corinthians", "2 cor": "2corinthians", "2 corinthians": "2corinthians", "2corinthians": "2corinthians",
    "gal": "galatians", "galation": "galatians", "galations": "galatians", "galatians": "galatians",
    "eph": "ephesians", "ephesians": "ephesians", "phi": "philippians", "phil": "philippians", "philippians": "philippians",
    "col": "colossians", "colossians": "colossians",
    "1th": "1thessalonians", "1 thess": "1thessalonians", "1 thessalonians": "1thessalonians", "1thessalonians": "1thessalonians",
    "2th": "2thessalonians", "2 thess": "2thessalonians", "2 thessalonians": "2thessalonians", "2thessalonians": "2thessalonians",
    "1ti": "1timothy", "1 tim": "1timothy", "1 timothy": "1timothy", "1timothy": "1timothy",
    "2ti": "2timothy", "2 tim": "2timothy", "2 timothy": "2timothy", "2timothy": "2timothy",
    "tit": "titus", "titus": "titus", "phm": "philemon", "phlm": "philemon", "philemon": "philemon",
    "heb": "hebrews", "hebrews": "hebrews", "jam": "james", "jas": "james", "james": "james",
    "1pe": "1peter", "1 pet": "1peter", "1 peter": "1peter", "1peter": "1peter",
    "2pe": "2peter", "2 pet": "2peter", "2 peter": "2peter", "2peter": "2peter",
    "1jo": "1john", "1 john": "1john", "1john": "1john",
    "2jo": "2john", "2 john": "2john", "2john": "2john",
    "3jo": "3john", "3 john": "3john", "3john": "3john",
    "jud": "jude", "jude": "jude", "rev": "revelation", "revelation": "revelation",
}
CANONICAL_BOOKS = sorted(set(BOOK_ALIASES.values()))

def normalize_book_name(user_text: str, known_books: Iterable[str] | None = None) -> str:
    text = " ".join((user_text or "").strip().lower().split())
    if not text:
        return text
    if text in BOOK_ALIASES:
        return BOOK_ALIASES[text]
    compact = text.replace(".", "").replace(" ", "")
    if compact in BOOK_ALIASES:
        return BOOK_ALIASES[compact]
    candidates = list(known_books or CANONICAL_BOOKS) or CANONICAL_BOOKS
    alias_keys = list(BOOK_ALIASES.keys())
    alias_match = difflib.get_close_matches(text, alias_keys, n=1, cutoff=0.72)
    if alias_match:
        return BOOK_ALIASES[alias_match[0]]
    compact_match = difflib.get_close_matches(compact, alias_keys, n=1, cutoff=0.72)
    if compact_match:
        return BOOK_ALIASES[compact_match[0]]
    book_match = difflib.get_close_matches(compact, candidates, n=1, cutoff=0.72)
    if book_match:
        return book_match[0]
    return compact
