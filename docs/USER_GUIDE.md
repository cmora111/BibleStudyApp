# Ultimate Bible App v8 User Guide

## What v8 adds

Version 8 adds a scholar layer on top of the Bible reader:
- semantic search
- AI Bible study assistant
- Strong's word study
- scholar search
- clickable scholar tokens when alignment data exists

## Normal use

### Read a verse
1. Choose a translation.
2. Enter book, chapter, and verse.
3. Click **Go**.

### Read a whole chapter
1. Choose a translation.
2. Enter book and chapter.
3. Click **Read Chapter**.

### Semantic search
Use the search box with theme-based queries:
- `grace through faith`
- `hope in suffering`

### AI study assistant
Ask questions like:
- `What does the Bible teach about salvation?`
- `How does Romans 8 connect suffering and hope?`

### Strong's lookup
Enter codes like:
- `G25`
- `H7225`

### Scholar search
Use structured queries:
- `strongs:G25`
- `lemma:agapao`
- `morph:V-PAI-3S`

## Scholar alignment data

To unlock clickable scholar tokens you need alignment data.

Expected alignment columns:
- `book`
- `chapter`
- `verse`
- `token_index`
- `token_text`
- `strongs_id`

Optional:
- `lemma`
- `morph`
- `source_lang`
- `source_surface`

## Demo mode

To test the scholar layer without a full dataset:

```bash
cd ~/Bible/BibleStudyApp/ultimate_bible_app_v8
PYTHONPATH=. python scripts/load_demo_scholar_tokens.py
```

Then open Romans 8:28 in ESV.

## ESV note

Exact ESV Strong's tagging requires licensed reverse-interlinear or alignment data.
This bundle supports importing that data cleanly, but it does not fabricate it.
