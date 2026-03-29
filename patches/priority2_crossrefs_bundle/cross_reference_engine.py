from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import DB_FILE


@dataclass
class CrossReference:
    source_book: str
    source_chapter: int
    source_verse: int
    target_book: str
    target_chapter: int
    target_verse: int
    votes: int = 0
    source_label: str = ""
    target_label: str = ""
    note: str = ""


class CrossReferenceEngine:
    def __init__(self, db_file: Optional[str] = None):
        self.db_file = db_file or DB_FILE
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cross_references (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_book TEXT NOT NULL,
                    source_chapter INTEGER NOT NULL,
                    source_verse INTEGER NOT NULL,
                    target_book TEXT NOT NULL,
                    target_chapter INTEGER NOT NULL,
                    target_verse INTEGER NOT NULL,
                    votes INTEGER DEFAULT 0,
                    source_label TEXT DEFAULT '',
                    target_label TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    dataset TEXT DEFAULT 'custom',
                    UNIQUE (
                        source_book, source_chapter, source_verse,
                        target_book, target_chapter, target_verse, dataset
                    )
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cross_refs_source
                ON cross_references(source_book, source_chapter, source_verse, votes DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cross_refs_target
                ON cross_references(target_book, target_chapter, target_verse)
            """)
            conn.commit()

    def get_cross_references(self, book: str, chapter: int, verse: int, limit: int = 50, min_votes: int = 0) -> List[CrossReference]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT source_book, source_chapter, source_verse,
                       target_book, target_chapter, target_verse,
                       votes, source_label, target_label, note
                FROM cross_references
                WHERE source_book=? AND source_chapter=? AND source_verse=? AND votes>=?
                ORDER BY votes DESC, target_book, target_chapter, target_verse
                LIMIT ?
                """,
                (book, chapter, verse, min_votes, limit),
            ).fetchall()

        return [
            CrossReference(
                source_book=row["source_book"],
                source_chapter=row["source_chapter"],
                source_verse=row["source_verse"],
                target_book=row["target_book"],
                target_chapter=row["target_chapter"],
                target_verse=row["target_verse"],
                votes=row["votes"],
                source_label=row["source_label"],
                target_label=row["target_label"],
                note=row["note"],
            )
            for row in rows
        ]

    def has_data(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM cross_references").fetchone()
        return bool(row and row[0] > 0)
