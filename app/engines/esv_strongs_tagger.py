from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TaggedToken:
    token: str
    strongs: str | None = None


class ESVStrongsTagger:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS verse_token_tags (
                    translation TEXT NOT NULL,
                    book TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    verse INTEGER NOT NULL,
                    token_index INTEGER NOT NULL,
                    token_text TEXT NOT NULL,
                    strongs_id TEXT,
                    lemma TEXT DEFAULT '',
                    gloss TEXT DEFAULT '',
                    PRIMARY KEY (translation, book, chapter, verse, token_index)
                )
                '''
            )
            conn.commit()

    def import_alignment_rows(self, rows, translation: str = "esv", replace: bool = False) -> int:
        tr = translation.lower().strip()
        items = []
        for row in rows:
            items.append(
                (
                    tr,
                    str(row["book"]).strip().lower(),
                    int(row["chapter"]),
                    int(row["verse"]),
                    int(row["token_index"]),
                    str(row["token_text"]).strip(),
                    (str(row.get("strongs_id", "")).strip().upper() or None),
                    str(row.get("lemma", "")).strip(),
                    str(row.get("gloss", "")).strip(),
                )
            )
        with self._connect() as conn:
            if replace:
                conn.execute("DELETE FROM verse_token_tags WHERE translation=?", (tr,))
            conn.executemany(
                '''
                INSERT INTO verse_token_tags
                (translation, book, chapter, verse, token_index, token_text, strongs_id, lemma, gloss)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(translation, book, chapter, verse, token_index)
                DO UPDATE SET
                    token_text=excluded.token_text,
                    strongs_id=excluded.strongs_id,
                    lemma=excluded.lemma,
                    gloss=excluded.gloss
                ''',
                items,
            )
            conn.commit()
        return len(items)
