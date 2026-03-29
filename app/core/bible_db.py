from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from typing import Iterable, List

from app.core.config import DB_FILE


@dataclass(slots=True)
class VerseRecord:
    translation: str
    book: str
    chapter: int
    verse: int
    text: str
    strongs: str = ""


@dataclass(slots=True)
class StrongsEntry:
    strongs_id: str
    lemma: str
    transliteration: str
    definition: str
    language: str = "unknown"
    gloss: str = ""


class BibleDB:
    """
    SQLite access layer for the Bible app.

    Best-practice locking fix:
    - one long-lived write-capable connection
    - short-lived read connections for lookup-heavy UI actions
    - WAL mode + busy timeout
    - thread lock around writes
    """

    def __init__(self, db_path=DB_FILE):
        self.db_file = str(db_path)
        self._write_lock = threading.RLock()
        self.conn = self._open_connection(write=True)
        self.create()

    def _open_connection(self, write: bool = False) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_file,
            timeout=30,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=30000;")
        if write:
            conn.execute("PRAGMA temp_store=MEMORY;")
        return conn

    def _read_one(self, sql: str, params=()):
        with self._open_connection(write=False) as conn:
            return conn.execute(sql, params).fetchone()

    def _read_all(self, sql: str, params=()):
        with self._open_connection(write=False) as conn:
            return conn.execute(sql, params).fetchall()

    def create(self) -> None:
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS verses (
                    translation TEXT NOT NULL,
                    book TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    verse INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    strongs TEXT DEFAULT '',
                    PRIMARY KEY (translation, book, chapter, verse)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS strongs_lexicon (
                    strongs_id TEXT PRIMARY KEY,
                    lemma TEXT NOT NULL,
                    transliteration TEXT DEFAULT '',
                    definition TEXT NOT NULL,
                    language TEXT DEFAULT 'unknown',
                    gloss TEXT DEFAULT ''
                )
                """
            )
            self.conn.commit()

    def close(self) -> None:
        try:
            with self._write_lock:
                self.conn.commit()
        finally:
            self.conn.close()

    def upsert_verse(self, record: VerseRecord) -> None:
        with self._write_lock:
            self.conn.execute(
                """
                INSERT INTO verses (translation, book, chapter, verse, text, strongs)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(translation, book, chapter, verse)
                DO UPDATE SET text=excluded.text, strongs=excluded.strongs
                """,
                (
                    record.translation.lower(),
                    record.book.lower(),
                    record.chapter,
                    record.verse,
                    record.text,
                    record.strongs,
                ),
            )
            self.conn.commit()

    def bulk_import(self, records: Iterable[VerseRecord]) -> int:
        items = [
            (
                record.translation.lower(),
                record.book.lower(),
                record.chapter,
                record.verse,
                record.text,
                record.strongs,
            )
            for record in records
        ]
        if not items:
            return 0

        with self._write_lock:
            self.conn.executemany(
                """
                INSERT INTO verses (translation, book, chapter, verse, text, strongs)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(translation, book, chapter, verse)
                DO UPDATE SET text=excluded.text, strongs=excluded.strongs
                """,
                items,
            )
            self.conn.commit()
        return len(items)

    def upsert_strongs_entry(self, entry: StrongsEntry) -> None:
        with self._write_lock:
            self.conn.execute(
                """
                INSERT INTO strongs_lexicon (strongs_id, lemma, transliteration, definition, language, gloss)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(strongs_id)
                DO UPDATE SET
                    lemma=excluded.lemma,
                    transliteration=excluded.transliteration,
                    definition=excluded.definition,
                    language=excluded.language,
                    gloss=excluded.gloss
                """,
                (
                    entry.strongs_id.upper(),
                    entry.lemma,
                    entry.transliteration,
                    entry.definition,
                    entry.language,
                    entry.gloss,
                ),
            )
            self.conn.commit()

    def bulk_import_strongs(self, entries):
        rows = [
            (
                entry.strongs_id.upper(),
                entry.lemma,
                entry.transliteration,
                entry.language,
                entry.gloss,
                entry.definition,
            )
            for entry in entries
        ]

        self.conn.executemany(
            """
            INSERT OR REPLACE INTO strongs
            (strongs_id, lemma, transliteration, language, gloss, definition)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()
        return len(rows)

        self.conn.executemany(
            """
            INSERT OR REPLACE INTO strongs
            (strongs_id, lemma, transliteration, language, gloss, definition)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()
        return len(rows)

    def get_strongs_entry(self, strongs_id: str) -> StrongsEntry | None:
        row = self._read_one(
            """
            SELECT strongs_id, lemma, transliteration, definition, language, gloss
            FROM strongs_lexicon
            WHERE strongs_id = ?
            """,
            (strongs_id.upper().strip(),),
        )
        return StrongsEntry(**dict(row)) if row else None

    def search_strongs_entries(self, query: str, limit: int = 25) -> list[StrongsEntry]:
        wildcard = f"%{query}%"
        rows = self._read_all(
            """
            SELECT strongs_id, lemma, transliteration, definition, language, gloss
            FROM strongs_lexicon
            WHERE strongs_id LIKE ? OR lemma LIKE ? OR transliteration LIKE ? OR definition LIKE ? OR gloss LIKE ?
            ORDER BY strongs_id
            LIMIT ?
            """,
            (wildcard, wildcard, wildcard, wildcard, wildcard, limit),
        )
        return [StrongsEntry(**dict(r)) for r in rows]

    def get_verse(self, translation: str, book: str, chapter: int, verse: int) -> VerseRecord | None:
        row = self._read_one(
            """
            SELECT translation, book, chapter, verse, text, strongs
            FROM verses
            WHERE translation=? AND book=? AND chapter=? AND verse=?
            """,
            (translation.lower(), book.lower(), chapter, verse),
        )
        return VerseRecord(**dict(row)) if row else None

    def get_context(self, translation: str, book: str, chapter: int, verse: int) -> List[VerseRecord]:
        verses = []
        for candidate in (verse - 1, verse, verse + 1):
            if candidate < 1:
                continue
            row = self.get_verse(translation, book, chapter, candidate)
            if row:
                verses.append(row)
        return verses

    def search_contains(self, query: str, translation: str | None = None, limit: int = 100) -> list[VerseRecord]:
        query = query.strip()
        if not query:
            return []
        wildcard = f"%{query}%"
        if translation:
            rows = self._read_all(
                """
                SELECT translation, book, chapter, verse, text, strongs
                FROM verses
                WHERE translation=? AND text LIKE ?
                ORDER BY book, chapter, verse
                LIMIT ?
                """,
                (translation.lower(), wildcard, limit),
            )
        else:
            rows = self._read_all(
                """
                SELECT translation, book, chapter, verse, text, strongs
                FROM verses
                WHERE text LIKE ?
                ORDER BY translation, book, chapter, verse
                LIMIT ?
                """,
                (wildcard, limit),
            )
        return [VerseRecord(**dict(r)) for r in rows]

    def all_verses(self, translation: str | None = None) -> list[VerseRecord]:
        if translation:
            rows = self._read_all(
                """
                SELECT translation, book, chapter, verse, text, strongs
                FROM verses
                WHERE translation=?
                ORDER BY book, chapter, verse
                """,
                (translation.lower(),),
            )
        else:
            rows = self._read_all(
                """
                SELECT translation, book, chapter, verse, text, strongs
                FROM verses
                ORDER BY translation, book, chapter, verse
                """
            )
        return [VerseRecord(**dict(r)) for r in rows]

    def find_verses_by_strongs(self, strongs_id: str, translation: str | None = None, limit: int = 50) -> list[VerseRecord]:
        wildcard = f"%{strongs_id.upper()}%"
        if translation:
            rows = self._read_all(
                """
                SELECT translation, book, chapter, verse, text, strongs
                FROM verses
                WHERE translation=? AND strongs LIKE ?
                ORDER BY book, chapter, verse
                LIMIT ?
                """,
                (translation.lower(), wildcard, limit),
            )
        else:
            rows = self._read_all(
                """
                SELECT translation, book, chapter, verse, text, strongs
                FROM verses
                WHERE strongs LIKE ?
                ORDER BY translation, book, chapter, verse
                LIMIT ?
                """,
                (wildcard, limit),
            )
        return [VerseRecord(**dict(r)) for r in rows]

    def translations(self) -> list[str]:
        rows = self._read_all("SELECT DISTINCT translation FROM verses ORDER BY translation")
        return [row[0] for row in rows]

    def get_chapter(self, translation: str, book: str, chapter: int) -> list[VerseRecord]:
        rows = self._read_all(
            """
            SELECT translation, book, chapter, verse, text, strongs
            FROM verses
            WHERE translation=? AND book=? AND chapter=?
            ORDER BY verse
            """,
            (translation.lower(), book.lower(), chapter),
        )
        return [VerseRecord(**dict(r)) for r in rows]
