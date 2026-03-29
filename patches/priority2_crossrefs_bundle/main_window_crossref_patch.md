# main_window.py integration snippet

Add import near other engine imports:
```python
from app.engines.cross_reference_engine import CrossReferenceEngine
```

In `__init__`:
```python
self.crossref_engine = CrossReferenceEngine()
```

Replace `get_crossrefs_for_current` with:
```python
def get_crossrefs_for_current(self):
    rows = self.crossref_engine.get_cross_references(
        self.normalize_current_book(),
        int(self.chapter_var.get()),
        int(self.verse_var.get()),
        limit=50,
    )
    if rows:
        return [f"{r.target_book.title()} {r.target_chapter}:{r.target_verse}" for r in rows]

    current = self.current_ref()
    with self._connect() as conn:
        manual = conn.execute(
            "SELECT target_ref, note FROM user_crossrefs WHERE source_ref=? ORDER BY id",
            (current,),
        ).fetchall()
    if manual:
        return [row["target_ref"] for row in manual]
    return []
```
