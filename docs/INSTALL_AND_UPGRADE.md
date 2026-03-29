# Install and Upgrade Guide for v8

## Recommended first step

Clone your working v7 project into a v8 folder:

```bash
cp -r ~/Bible/BibleStudyApp/ultimate_bible_app_v7 ~/Bible/BibleStudyApp/ultimate_bible_app_v8
```

## Copy v8 files into the project

```bash
cp app/engines/scholar_alignment.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8/app/engines/
cp app/engines/scholar_search.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8/app/engines/
cp app/engines/esv_strongs_tagger.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8/app/engines/
cp scripts/import_alignment_dataset.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8/scripts/
cp scripts/import_esv_strongs_alignment.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8/scripts/
cp scripts/load_demo_scholar_tokens.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8/scripts/
```

## Main window wiring

To render scholar tokens and add a scholar search pane, merge the scholar imports and methods into your live `app/ui/main_window.py`.

## Import real alignment data

```bash
cd ~/Bible/BibleStudyApp/ultimate_bible_app_v8
PYTHONPATH=. python scripts/import_alignment_dataset.py /path/to/alignment.csv --translation esv --replace
```

## Verify

```bash
sqlite3 ~/UltimateBibleApp/data/bible.db "SELECT COUNT(*) FROM scholar_alignment_tokens;"
```
