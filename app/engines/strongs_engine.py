from __future__ import annotations

from dataclasses import dataclass

from app.core.bible_db import BibleDB, StrongsEntry, VerseRecord
from app.core.lexical_resolver import (
    LexicalRecord,
    LexicalResolution,
    LexicalResolver,
)
from app.core.utils import parse_strongs_codes, pretty_ref, tokenize_words


@dataclass(slots=True)
class WordStudyResult:
    resolution: LexicalResolution | None
    entry: StrongsEntry | None
    occurrences: list[str]
    verse_hits: list[VerseRecord]
    linked_codes: list[str]


class StrongsWordStudyEngine:
    def __init__(
        self,
        db: BibleDB,
        translation: str = "kjv",
        lexical_resolver: LexicalResolver | None = None,
    ):
        self.db = db
        self.translation = translation
        self.lexical_resolver = lexical_resolver

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

    @staticmethod
    def _legacy_entry_from_record(record: LexicalRecord) -> StrongsEntry:
        return StrongsEntry(
            strongs_id=record.estrong,
            lemma=record.lemma,
            transliteration=record.transliteration,
            definition=record.definition,
            language=record.language,
            gloss=record.gloss,
        )

    def study_code(self, strongs_id: str, limit: int = 10) -> WordStudyResult:
        code = strongs_id.upper()

        resolution = None

        if self.lexical_resolver is None:
            entry = self.db.get_strongs_entry(code)
        else:
            resolution = self.lexical_resolver.resolve(code)

            if resolution.is_singular:
                record = next(resolution.iter_records())
                entry = self._legacy_entry_from_record(record)
            else:
                entry = None

        verse_hits = self.db.find_verses_by_strongs(
            code,
            translation=self.translation,
            limit=limit,
        )

        occurrences = [
            f"{pretty_ref(v.book, v.chapter, v.verse)} — {v.text}"
            for v in verse_hits
        ]

        linked_codes = []
        if verse_hits:
            linked_codes = parse_strongs_codes(verse_hits[0].strongs)

        return WordStudyResult(
            resolution=resolution,
            entry=entry,
            occurrences=occurrences,
            verse_hits=verse_hits,
            linked_codes=linked_codes,
        )

    def search(self, query: str, limit: int = 25) -> list[StrongsEntry]:
        return self.db.search_strongs_entries(query, limit=limit)
