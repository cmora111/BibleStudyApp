# Licensed dataset import guide

This app does not ship with commercial Bible text or proprietary lexicons. It can import files that you are licensed to use.

## Supported Bible formats

### Pipe-delimited text

```text
john|3|16|For God so loved the world...|G1063 G2316 G25 G3588 G2889
```

Fields:
1. `book`
2. `chapter`
3. `verse`
4. `text`
5. optional `strongs`

### CSV

Required columns:
- `book`
- `chapter`
- `verse`
- `text`

Optional columns:
- `translation`
- `strongs`

### JSONL

One JSON object per line:

```json
{"translation":"esv","book":"john","chapter":3,"verse":16,"text":"For God so loved the world...","strongs":"G1063 G2316 G25 G3588 G2889"}
```

## Supported Strong's lexicon formats

### CSV

Required columns:
- `strongs_id`
- `lemma`
- `definition`

Optional columns:
- `transliteration`
- `language`
- `gloss`

### JSONL

```json
{"strongs_id":"G26","lemma":"agape","transliteration":"agapē","definition":"love, benevolence","language":"Greek","gloss":"love"}
```

## GUI import

Use the **Licensed Dataset Import** panel or the **File** menu.

## CLI import

```bash
PYTHONPATH=. python scripts/import_bible_dataset.py /path/to/esv.csv --format csv
PYTHONPATH=. python scripts/import_strongs_lexicon.py /path/to/strongs.jsonl --format jsonl
```
