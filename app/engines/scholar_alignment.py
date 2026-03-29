from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

@dataclass(slots=True)
class AlignmentToken:
    translation: str
    book: str
    chapter: int
    verse: int
    token_index: int
    token_text: str
    strongs_id: str = ""
    lemma: str = ""
    morph: str = ""
    source_lang: str = ""
    source_surface: str = ""

class ScholarAlignmentEngine:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scholar_alignment_tokens (
                    translation TEXT NOT NULL,
                    book TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    verse INTEGER NOT NULL,
                    token_index INTEGER NOT NULL,
                    token_text TEXT NOT NULL,
                    strongs_id TEXT DEFAULT '',
                    lemma TEXT DEFAULT '',
                    morph TEXT DEFAULT '',
                    source_lang TEXT DEFAULT '',
                    source_surface TEXT DEFAULT '',
                    PRIMARY KEY (translation, book, chapter, verse, token_index)
                )
            ''')
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scholar_alignment_lookup ON scholar_alignment_tokens(translation, book, chapter, verse)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scholar_alignment_strongs ON scholar_alignment_tokens(strongs_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scholar_alignment_lemma ON scholar_alignment_tokens(lemma)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scholar_alignment_morph ON scholar_alignment_tokens(morph)")
            conn.commit()

    def import_rows(self, rows: list[dict], replace: bool = False) -> int:
        if not rows:
            return 0
        translation = str(rows[0].get("translation", "")).lower().strip()
        items = []
        for row in rows:
            items.append((
                str(row.get("translation", "")).lower().strip(),
                str(row.get("book", "")).lower().strip(),
                int(row.get("chapter")),
                int(row.get("verse")),
                int(row.get("token_index")),
                str(row.get("token_text", "")).strip(),
                str(row.get("strongs_id", "")).strip().upper(),
                str(row.get("lemma", "")).strip(),
                str(row.get("morph", "")).strip(),
                str(row.get("source_lang", "")).strip(),
                str(row.get("source_surface", "")).strip(),
            ))
        with self._connect() as conn:
            if replace and translation:
                conn.execute("DELETE FROM scholar_alignment_tokens WHERE translation=?", (translation,))
            conn.executemany('''
                INSERT INTO scholar_alignment_tokens
                (translation, book, chapter, verse, token_index, token_text, strongs_id, lemma, morph, source_lang, source_surface)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(translation, book, chapter, verse, token_index)
                DO UPDATE SET
                    token_text=excluded.token_text,
                    strongs_id=excluded.strongs_id,
                    lemma=excluded.lemma,
                    morph=excluded.morph,
                    source_lang=excluded.source_lang,
                    source_surface=excluded.source_surface
            ''', items)
            conn.commit()
        return len(items)
