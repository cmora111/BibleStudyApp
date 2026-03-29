from __future__ import annotations

from dataclasses import dataclass

from app.core.bible_db import BibleDB, StrongsEntry, VerseRecord
from app.core.utils import parse_strongs_codes, pretty_ref, tokenize_words


@dataclass(slots=True)
class WordStudyResult:
    entry: StrongsEntry | None
    occurrences: list[str]
    verse_hits: list[VerseRecord]
    linked_codes: list[str]


class StrongsWordStudyEngine:
    def __init__(self, db: BibleDB, translation: str = "kjv"):
        self.db = db
        self.translation = translation

    def set_translation(self, translation: str) -> None:
        self.translation = translation

    def extract_word_links(self, verse: VerseRecord) -> list[tuple[str, str | None]]:
        words = tokenize_words(verse.text)
        codes = parse_strongs_codes(verse.strongs)
        linked: list[tuple[str, str | None]] = []
        for idx, word in enumerate(words):
            code = codes[idx] if idx < len(codes) else None
            linked.append((word, code))
        return linked

    def study_code(self, strongs_id: str, limit: int = 10) -> WordStudyResult:
        code = strongs_id.upper()
        entry = self.db.get_strongs_entry(code)
        verse_hits = self.db.find_verses_by_strongs(code, translation=self.translation, limit=limit)
        occurrences = [f"{pretty_ref(v.book, v.chapter, v.verse)} — {v.text}" for v in verse_hits]
        linked_codes = []
        if verse_hits:
            linked_codes = parse_strongs_codes(verse_hits[0].strongs)
        return WordStudyResult(entry=entry, occurrences=occurrences, verse_hits=verse_hits, linked_codes=linked_codes)

    def search(self, query: str, limit: int = 25) -> list[StrongsEntry]:
        return self.db.search_strongs_entries(query, limit=limit)
