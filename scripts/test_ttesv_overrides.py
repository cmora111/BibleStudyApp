#!/usr/bin/env python
from __future__ import annotations

import csv
import re
import sqlite3
import sys
from pathlib import Path

# allow project imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import DB_FILE

TTESV_RE = re.compile(r'^\$([1-3]?[A-Za-z]+)\s+(\d+):(\d+)\t(.*)$')
MAP_RE = re.compile(r'(\d+(?:\+\d+)*)=<(\d+)>')

BOOK_MAP = {
    "Gen": "genesis", "Exo": "exodus", "Lev": "leviticus", "Num": "numbers",
    "Deu": "deuteronomy", "Jos": "joshua", "Jdg": "judges", "Rut": "ruth",
    "1Sa": "1samuel", "2Sa": "2samuel", "1Ki": "1kings", "2Ki": "2kings",
    "1Ch": "1chronicles", "2Ch": "2chronicles", "Ezr": "ezra", "Neh": "nehemiah",
    "Est": "esther", "Job": "job", "Psa": "psalms", "Pro": "proverbs",
    "Ecc": "ecclesiastes", "Sng": "songofsolomon", "Song": "songofsolomon",
    "Isa": "isaiah", "Jer": "jeremiah", "Lam": "lamentations", "Eze": "ezekiel",
    "Ezek": "ezekiel", "Dan": "daniel", "Hos": "hosea", "Joe": "joel", "Joel": "joel",
    "Amo": "amos", "Oba": "obadiah", "Jon": "jonah", "Mic": "micah", "Nah": "nahum",
    "Hab": "habakkuk", "Zep": "zephaniah", "Hag": "haggai", "Zec": "zechariah",
    "Mal": "malachi", "Mat": "matthew", "Mrk": "mark", "Luk": "luke", "Jhn": "john",
    "Act": "acts", "Rom": "romans", "1Co": "1corinthians", "2Co": "2corinthians",
    "Gal": "galatians", "Eph": "ephesians", "Php": "philippians", "Col": "colossians",
    "1Th": "1thessalonians", "2Th": "2thessalonians", "1Ti": "1timothy", "2Ti": "2timothy",
    "Tit": "titus", "Phm": "philemon", "Heb": "hebrews", "Jas": "james",
    "1Pe": "1peter", "2Pe": "2peter", "1Jn": "1john", "2Jn": "2john",
    "3Jn": "3john", "Jud": "jude", "Rev": "revelation",
}

POSITION_BUFFER = 3

EXPECTED_OMISSIONS = {
    ("matthew", 12, 47), ("matthew", 17, 21), ("matthew", 18, 11), ("matthew", 23, 14),
    ("mark", 7, 16), ("mark", 9, 44), ("mark", 9, 46), ("mark", 11, 26), ("mark", 15, 28),
    ("luke", 17, 36), ("luke", 23, 17), ("john", 5, 4), ("acts", 8, 37), ("acts", 15, 34),
    ("acts", 24, 7), ("acts", 28, 29), ("romans", 16, 24),
}


# ---------------- TOKENIZER ----------------

def tokenize(text: str):
    text = text.replace("’", "'")
    return re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|[.,:;!?()\"]", text)


# ---------------- PARSERS ----------------

def parse_mapping_blob(blob: str, token_count=None):
    mapping = {}
    ignored = 0

    for m in MAP_RE.finditer(blob):
        positions = m.group(1).split("+")
        strongs = f"G{int(m.group(2))}"

        for pos in positions:
            p = int(pos)

            if token_count is not None and p > token_count + POSITION_BUFFER:
                ignored += 1
                continue

            mapping[p] = strongs

    return mapping, ignored


def fetch_esv_verse(conn, book, chapter, verse):
    row = conn.execute(
        "SELECT text FROM verses WHERE translation='esv' AND book=? AND chapter=? AND verse=?",
        (book, chapter, verse),
    ).fetchone()
    return row[0] if row else None


def parse_replacement_tokens(text: str):
    if not text:
        return []
    return [part.strip() for part in text.split("|") if part.strip()]


def parse_position_override(text: str):
    mapping = {}

    if not text:
        return mapping

    for chunk in text.split("|"):
        chunk = chunk.strip()

        if not chunk or "=" not in chunk:
            continue

        left, right = chunk.split("=", 1)

        try:
            pos = int(left.strip())
        except ValueError:
            continue

        sid = right.strip().upper()

        if sid and sid[0] not in {"G", "H"} and sid.isdigit():
            sid = f"G{int(sid)}"

        mapping[pos] = sid

    return mapping


# ---------------- LOADERS ----------------

def load_ttesv(path: Path):
    verses = {}

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.startswith("$"):
                continue

            m = TTESV_RE.match(line.rstrip("\n"))
            if not m:
                continue

            short_book, ch_s, vs_s, blob = m.groups()

            book = BOOK_MAP.get(short_book)
            if not book:
                continue

            chapter = int(ch_s)
            verse = int(vs_s)

            if book == "psalms" and verse == 0:
                continue

            if (book, chapter, verse) in EXPECTED_OMISSIONS:
                continue

            verses[(book, chapter, verse)] = blob

    return verses


def load_overrides(path: Path):
    rows = []

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                key = (
                    row["book"].strip().lower(),
                    int(row["chapter"]),
                    int(row["verse"]),
                )
            except Exception:
                continue

            action = (row.get("action") or "").strip().lower()

            if not action:
                continue

            rows.append({
                "key": key,
                "book": key[0],
                "chapter": key[1],
                "verse": key[2],
                "action": action,
                "replacement_tokens": (row.get("replacement_tokens") or "").strip(),
                "position_override": (row.get("position_override") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
            })

    return rows


# ---------------- CORE LOGIC ----------------

def mismatch_count(conn, ttesv_map, overrides_by_key):
    mismatches = 0

    for key, blob in ttesv_map.items():
        book, chapter, verse = key

        verse_text = fetch_esv_verse(conn, book, chapter, verse)
        if not verse_text:
            continue

        ov = overrides_by_key.get(key, {})
        action = ov.get("action", "")

        if action == "skip":
            continue

        tokens = tokenize(verse_text)
        strongs_map, _ = parse_mapping_blob(blob, token_count=len(tokens))

        if action == "retokenize":
            replacement_tokens = parse_replacement_tokens(ov.get("replacement_tokens", ""))
            if replacement_tokens:
                tokens = replacement_tokens
                strongs_map, _ = parse_mapping_blob(blob, token_count=len(tokens))

        if action == "manual_map":
            strongs_map.update(parse_position_override(ov.get("position_override", "")))

        if strongs_map and max(strongs_map) > len(tokens):
            mismatches += 1

    return mismatches


# ---------------- MAIN ----------------

def main():
    if len(sys.argv) < 3:
        print("Usage: PYTHONPATH=. python scripts/test_ttesv_overrides.py TTESV.txt overrides.csv")
        return 1

    ttesv_path = Path(sys.argv[1]).expanduser().resolve()
    overrides_path = Path(sys.argv[2]).expanduser().resolve()

    conn = sqlite3.connect(DB_FILE)

    ttesv_map = load_ttesv(ttesv_path)
    override_rows = load_overrides(overrides_path)

    baseline = mismatch_count(conn, ttesv_map, {})
    print(f"Baseline mismatches (no overrides): {baseline}")

    results = []

    for row in override_rows:
        score = mismatch_count(conn, ttesv_map, {row["key"]: row})
        delta = score - baseline

        outcome = (
            "improved" if delta < 0 else
            "unchanged" if delta == 0 else
            "worse"
        )

        results.append({
            "book": row["book"],
            "chapter": row["chapter"],
            "verse": row["verse"],
            "action": row["action"],
            "delta": delta,
            "mismatches": score,
            "outcome": outcome,
            "notes": row["notes"],
        })

    conn.close()

    results.sort(key=lambda r: (r["delta"], r["book"], r["chapter"], r["verse"]))

    out_csv = Path.cwd() / "ttesv_override_test_results.csv"

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "book", "chapter", "verse",
                "action", "delta", "mismatches", "outcome", "notes"
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults written to: {out_csv}")

    print("\nTop helpful overrides:")
    for r in [x for x in results if x["outcome"] == "improved"][:10]:
        print(f"  {r['book']} {r['chapter']}:{r['verse']} [{r['action']}] delta={r['delta']}")

    print("\nNeutral overrides:")
    for r in [x for x in results if x["outcome"] == "unchanged"][:10]:
        print(f"  {r['book']} {r['chapter']}:{r['verse']} [{r['action']}]")

    print("\nHarmful overrides:")
    for r in [x for x in results if x["outcome"] == "worse"][:10]:
        print(f"  {r['book']} {r['chapter']}:{r['verse']} delta=+{r['delta']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
