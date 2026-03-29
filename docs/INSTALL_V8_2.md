# Ultimate Bible App v8.2 Install Guide

v8.2 adds a starter Strong's dataset bundle on top of the v8 scholar layer and v8.1 UI lookup reliability.

## What is included
- v8.1 book normalizer
- scholar alignment engine
- scholar search engine
- starter Strong's lexicon demo CSV
- starter alignment demo CSV
- script to build a local starter Strong's bundle

## Recommended upgrade path

1. Copy your working project to a v8.2 folder:
```bash
cp -r ~/Bible/BibleStudyApp/ultimate_bible_app_v8 ~/Bible/BibleStudyApp/ultimate_bible_app_v8_2
```

2. Copy the bundle files into the project:
```bash
cp app/core/book_normalizer.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8_2/app/core/
cp app/engines/scholar_alignment.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8_2/app/engines/
cp app/engines/scholar_search.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8_2/app/engines/
cp scripts/load_demo_scholar_tokens.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8_2/scripts/
cp scripts/import_alignment_dataset.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8_2/scripts/
cp scripts/build_strongs_dataset_bundle.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8_2/scripts/
cp -r datasets ~/Bible/BibleStudyApp/ultimate_bible_app_v8_2/
```

3. Load demo scholar tokens:
```bash
cd ~/Bible/BibleStudyApp/ultimate_bible_app_v8_2
PYTHONPATH=. python scripts/load_demo_scholar_tokens.py
```

4. Build the local starter Strong's bundle:
```bash
PYTHONPATH=. python scripts/build_strongs_dataset_bundle.py --out datasets/output
```

5. Merge the v8 scholar UI wiring and the v8.1 book normalization into your live `app/ui/main_window.py`.
