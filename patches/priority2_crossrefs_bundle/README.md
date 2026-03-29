# Priority 2: Real Cross-Reference Dataset Integration

Files included:
- cross_reference_engine.py
- import_cross_references.py
- crossrefs_sample.csv
- main_window_crossref_patch.md

## Install
```bash
cp cross_reference_engine.py ~/Bible/BibleStudyApp/ultimate_bible_app_latest/app/engines/
cp import_cross_references.py ~/Bible/BibleStudyApp/ultimate_bible_app_latest/scripts/
cp crossrefs_sample.csv ~/Bible/BibleStudyApp/ultimate_bible_app_latest/
```

## Test with sample data
```bash
cd ~/Bible/BibleStudyApp/ultimate_bible_app_latest
PYTHONPATH=. python scripts/import_cross_references.py crossrefs_sample.csv --replace-dataset sample
```

## Verify
```bash
sqlite3 ~/UltimateBibleApp/data/bible.db "
SELECT source_book, source_chapter, source_verse, target_book, target_chapter, target_verse, votes, dataset
FROM cross_references
ORDER BY votes DESC
LIMIT 10;"
```
