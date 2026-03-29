#!/usr/bin/env python3
"""
Strict ESV converter for mutool-extracted text.

Goals:
- convert `esv_raw.txt` -> `esv.csv`
- aggressively skip footnotes / textual notes
- reject malformed verse rows
- validate basic verse continuity within each chapter
- write a reject log for suspicious lines

Outputs:
- esv.csv
- esv_rejects.log
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

INPUT = Path("esv_raw.txt")
OUTPUT = Path("esv.csv")
REJECTS = Path("esv_rejects.log")

BOOKS = {
    "GENESIS": "genesis",
    "EXODUS": "exodus",
    "LEVITICUS": "leviticus",
    "NUMBERS": "numbers",
    "DEUTERONOMY": "deuteronomy",
    "JOSHUA": "joshua",
    "JUDGES": "judges",
    "RUTH": "ruth",
    "1 SAMUEL": "1samuel",
    "2 SAMUEL": "2samuel",
    "1 KINGS": "1kings",
    "2 KINGS": "2kings",
    "1 CHRONICLES": "1chronicles",
    "2 CHRONICLES": "2chronicles",
    "EZRA": "ezra",
    "NEHEMIAH": "nehemiah",
    "ESTHER": "esther",
    "JOB": "job",
    "PSALMS": "psalms",
    "PROVERBS": "proverbs",
    "ECCLESIASTES": "ecclesiastes",
    "SONG OF SOLOMON": "songofsolomon",
    "ISAIAH": "isaiah",
    "JEREMIAH": "jeremiah",
    "LAMENTATIONS": "lamentations",
    "EZEKIEL": "ezekiel",
    "DANIEL": "daniel",
    "HOSEA": "hosea",
    "JOEL": "joel",
    "AMOS": "amos",
    "OBADIAH": "obadiah",
    "JONAH": "jonah",
    "MICAH": "micah",
    "NAHUM": "nahum",
    "HABAKKUK": "habakkuk",
    "ZEPHANIAH": "zephaniah",
    "HAGGAI": "haggai",
    "ZECHARIAH": "zechariah",
    "MALACHI": "malachi",
    "MATTHEW": "matthew",
    "MARK": "mark",
    "LUKE": "luke",
    "JOHN": "john",
    "ACTS": "acts",
    "ROMANS": "romans",
    "1 CORINTHIANS": "1corinthians",
    "2 CORINTHIANS": "2corinthians",
    "GALATIANS": "galatians",
    "EPHESIANS": "ephesians",
    "PHILIPPIANS": "philippians",
    "COLOSSIANS": "colossians",
    "1 THESSALONIANS": "1thessalonians",
    "2 THESSALONIANS": "2thessalonians",
    "1 TIMOTHY": "1timothy",
    "2 TIMOTHY": "2timothy",
    "TITUS": "titus",
    "PHILEMON": "philemon",
    "HEBREWS": "hebrews",
    "JAMES": "james",
    "1 PETER": "1peter",
    "2 PETER": "2peter",
    "1 JOHN": "1john",
    "2 JOHN": "2john",
    "3 JOHN": "3john",
    "JUDE": "jude",
    "REVELATION": "revelation",
}

CHAPTER_VERSE_START = re.compile(r'^(\d+):(\d+)\s+(.*)$')
INLINE_VERSE = re.compile(r'(?<!\d)(\d+)(?=[A-Z“"\'(\[])')

FOOTNOTE_PATTERNS = [
    re.compile(r'^\[\d+\]'),
    re.compile(r'^\d+\.\d+\s'),
    re.compile(r'^\d+:\d+\s+Or\s', re.I),
    re.compile(r'^\d+:\d+\s+Some manuscripts\s', re.I),
    re.compile(r'^Or\s', re.I),
    re.compile(r'^Some manuscripts\s', re.I),
    re.compile(r'^Hebrew\s', re.I),
    re.compile(r'^Greek\s', re.I),
    re.compile(r'^Syriac\s', re.I),
    re.compile(r'^Septuagint\s', re.I),
    re.compile(r'^Compare\s', re.I),
    re.compile(r'^The meaning of the Hebrew', re.I),
    re.compile(r'^Probable reading', re.I),
]

BAD_TEXT_PATTERNS = [
    re.compile(r'\bSome manuscripts\b', re.I),
    re.compile(r'\bHebrew\b'),
    re.compile(r'\bGreek\b'),
    re.compile(r'\bSeptuagint\b'),
    re.compile(r'\bSyriac\b'),
    re.compile(r'\bCompare\b'),
]

MIN_VERSE_TEXT_LEN = 8
MAX_SECTION_HEADING_WORDS = 10

def clean_text(s: str) -> str:
    s = s.replace("\x0c", " ")
    s = s.replace("￾", "")
    s = re.sub(r'\[\d+\]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def is_probable_footnote_line(line: str) -> bool:
    raw = line.strip()
    if not raw:
        return False
    return any(pat.match(raw) for pat in FOOTNOTE_PATTERNS)

def is_probable_bad_verse_text(text: str) -> bool:
    t = text.strip()
    if len(t) < MIN_VERSE_TEXT_LEN:
        return True
    if any(p.search(t) for p in BAD_TEXT_PATTERNS):
        return True
    letters = [c for c in t if c.isalpha()]
    if letters:
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio < 0.02 and t[:1].islower():
            return True
    return False

def split_inline_verses(text: str):
    starts = list(INLINE_VERSE.finditer(text))
    if not starts:
        return []
    parts = []
    for i, m in enumerate(starts):
        start = m.start()
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        segment = text[start:end].strip()
        seg_match = re.match(r'^(\d+)(.*)$', segment, re.S)
        if not seg_match:
            continue
        verse_num = int(seg_match.group(1))
        body = clean_text(seg_match.group(2))
        if body:
            parts.append((verse_num, body))
    return parts

def validate_and_filter(rows, rejects):
    by_chapter = defaultdict(list)
    for row in rows:
        _, book, chapter, verse, text = row
        by_chapter[(book, chapter)].append((verse, text))

    kept = []
    for (book, chapter), items in by_chapter.items():
        items.sort(key=lambda x: x[0])
        last_verse = 0
        seen = set()
        for verse, text in items:
            if verse in seen:
                rejects.append(f"DUPLICATE\t{book} {chapter}:{verse}\t{text}")
                continue
            seen.add(verse)
            if verse < 1:
                rejects.append(f"BADVERSE\t{book} {chapter}:{verse}\t{text}")
                continue
            if is_probable_bad_verse_text(text):
                rejects.append(f"BADTEXT\t{book} {chapter}:{verse}\t{text}")
                continue
            if last_verse and verse - last_verse > 3:
                rejects.append(f"GAP\t{book} {chapter}:{verse}\tprev={last_verse}\t{text}")
            last_verse = verse
            kept.append(["esv", book, chapter, verse, text])
    kept.sort(key=lambda r: (r[1], r[2], r[3]))
    return kept

def main():
    text = INPUT.read_text(encoding='utf-8', errors='ignore')
    lines = [line.rstrip() for line in text.splitlines()]

    raw_rows = []
    rejects = []
    current_book = None
    current_chapter = None
    started = False
    buffer = ''

    def flush_buffer():
        nonlocal buffer
        if not buffer or current_book is None or current_chapter is None:
            buffer = ''
            return
        for verse_num, verse_text in split_inline_verses(buffer):
            if is_probable_footnote_line(verse_text):
                rejects.append(f"FOOTNOTE_AS_VERSE\t{current_book} {current_chapter}:{verse_num}\t{verse_text}")
                continue
            raw_rows.append(["esv", current_book, current_chapter, verse_num, verse_text])
        buffer = ''

    for raw in lines:
        line = clean_text(raw)
        if not line:
            continue
        if line in BOOKS:
            flush_buffer()
            current_book = BOOKS[line]
            current_chapter = None
            if line == "GENESIS":
                started = True
            continue
        if not started:
            continue
        if re.fullmatch(r'Chapter \d+', line):
            continue
        if current_book and not re.match(r'^\d', line) and ':' not in line and len(line.split()) <= MAX_SECTION_HEADING_WORDS:
            continue
        if is_probable_footnote_line(line):
            rejects.append(f"SKIP_FOOTNOTE_LINE\t{line}")
            continue
        m = CHAPTER_VERSE_START.match(line)
        if m:
            flush_buffer()
            current_chapter = int(m.group(1))
            verse = int(m.group(2))
            verse_text = clean_text(m.group(3))
            if is_probable_footnote_line(verse_text):
                rejects.append(f"SKIP_VERSE_START_FOOTNOTE\t{current_book} {current_chapter}:{verse}\t{verse_text}")
                buffer = ''
            else:
                buffer = f"{verse}{verse_text}"
            continue
        if current_book and current_chapter is not None:
            if is_probable_footnote_line(line):
                rejects.append(f"SKIP_CONTINUATION_FOOTNOTE\t{line}")
                continue
            buffer += ' ' + line

    flush_buffer()
    final_rows = validate_and_filter(raw_rows, rejects)

    with OUTPUT.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["translation", "book", "chapter", "verse", "text"])
        writer.writerows(final_rows)

    REJECTS.write_text("\n".join(rejects) + ("\n" if rejects else ""), encoding="utf-8")
    print(f"Wrote {len(final_rows)} verses to {OUTPUT}")
    print(f"Wrote {len(rejects)} rejected/suspicious lines to {REJECTS}")

if __name__ == "__main__":
    main()