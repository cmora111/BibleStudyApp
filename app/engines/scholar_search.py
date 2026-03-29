from __future__ import annotations

from dataclasses import dataclass
from app.engines.scholar_alignment import ScholarAlignmentEngine

@dataclass(slots=True)
class ScholarSearchHit:
    translation: str
    reference: str
    token_text: str
    strongs_id: str
    lemma: str
    morph: str
    source_lang: str
    source_surface: str

class ScholarSearchEngine:
    def __init__(self, db_path: str):
        self.alignments = ScholarAlignmentEngine(db_path)

    def search(self, query: str, translation: str | None = None, limit: int = 100) -> list[ScholarSearchHit]:
        query = query.strip()
        if ":" not in query:
            return []
        prefix, value = query.split(":", 1)
        prefix = prefix.strip().lower()
        value = value.strip()
        field = {"strongs": "strongs_id", "lemma": "lemma", "morph": "morph"}.get(prefix)
        if not field:
            return []
        sql = f"SELECT * FROM scholar_alignment_tokens WHERE {field}=?"
        params = [value.upper() if field == "strongs_id" else value]
        if translation:
            sql += " AND translation=?"
            params.append(translation.lower())
        sql += " ORDER BY translation, book, chapter, verse, token_index LIMIT ?"
        params.append(limit)
        with self.alignments._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [ScholarSearchHit(
            translation=r["translation"],
            reference=f'{r["book"].title()} {r["chapter"]}:{r["verse"]}',
            token_text=r["token_text"],
            strongs_id=r["strongs_id"],
            lemma=r["lemma"],
            morph=r["morph"],
            source_lang=r["source_lang"],
            source_surface=r["source_surface"],
        ) for r in rows]
