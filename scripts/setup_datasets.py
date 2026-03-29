#!/usr/bin/env python3
"""
Create a Bible dataset folder structure, optionally download public-domain/open datasets,
convert supported source files into import-ready formats, and optionally import them into
Ultimate Bible App v7.

Usage examples:
  python scripts/setup_datasets.py --root datasets
  python scripts/setup_datasets.py --root datasets --download-public
  python scripts/setup_datasets.py --root datasets --download-public --import-into-db
  python scripts/setup_datasets.py --root datasets --source ../../Bibles/web.txt --translation web

Notes:
- This script only downloads public/openly available resources.
- It does NOT download ESV or other commercially licensed datasets.
- For licensed texts you already own, place them under datasets/raw/ and then run with --source.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = Path.home() / "BibleStudy" / "bible.db"

PUBLIC_DOWNLOADS = {
    "web": {
        "url": "https://ebible.org/eng-web/webtxt.zip",
        "zip_member_candidates": ["webtxt.txt", "web_olb.txt"],
        "target_name": "webtxt.zip",
    },
    "scrollmapper": {
        "url": "https://github.com/scrollmapper/bible_databases/archive/refs/heads/master.zip",
        "target_name": "scrollmapper_bible_databases.zip",
    },
}

BOOK_ALIASES = {
    "gen": "genesis", "ge": "genesis", "gn": "genesis",
    "ex": "exodus", "exo": "exodus",
    "lev": "leviticus", "lv": "leviticus",
    "num": "numbers", "nm": "numbers",
    "deut": "deuteronomy", "dt": "deuteronomy",
    "jos": "joshua", "josh": "joshua",
    "jdg": "judges", "judg": "judges",
    "rut": "ruth",
    "1sam": "1samuel", "2sam": "2samuel",
    "1kgs": "1kings", "2kgs": "2kings",
    "1chr": "1chronicles", "2chr": "2chronicles",
    "neh": "nehemiah", "est": "esther",
    "ps": "psalms", "prov": "proverbs", "eccl": "ecclesiastes",
    "song": "songofsolomon", "sos": "songofsolomon",
    "isa": "isaiah", "jer": "jeremiah", "lam": "lamentations",
    "ezek": "ezekiel", "dan": "daniel",
    "hos": "hosea", "joel": "joel", "amos": "amos", "obad": "obadiah",
    "jon": "jonah", "mic": "micah", "nah": "nahum", "hab": "habakkuk",
    "zep": "zephaniah", "hag": "haggai", "zec": "zechariah", "mal": "malachi",
    "matt": "matthew", "mk": "mark", "mrk": "mark", "lk": "luke", "jn": "john",
    "rom": "romans", "1cor": "1corinthians", "2cor": "2corinthians",
    "gal": "galatians", "eph": "ephesians", "phil": "philippians",
    "col": "colossians", "1th": "1thessalonians", "2th": "2thessalonians",
    "1tim": "1timothy", "2tim": "2timothy", "phlm": "philemon",
    "heb": "hebrews", "jas": "james", "jam": "james",
    "1pet": "1peter", "2pet": "2peter",
    "1jn": "1john", "2jn": "2john", "3jn": "3john",
    "jud": "jude", "rev": "revelation",
}

VERSE_LINE_PATTERNS = [
    re.compile(r"^([1-3]?\s?[A-Za-z][A-Za-z\s]+?)\s+(\d+):(\d+)\s+(.+)$"),
    re.compile(r"^([1-3]?[A-Za-z]+)\s+(\d+):(\d+)\s+(.+)$"),
    re.compile(r"^([1-3]?\s?[A-Za-z][A-Za-z\s]+?)\.(\d+)\.(\d+)\s+(.+)$"),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def ensure_dirs(root: Path) -> dict[str, Path]:
    dirs = {
        "root": root,
        "raw": root / "raw",
        "bibles": root / "bibles",
        "greek": root / "greek",
        "hebrew": root / "hebrew",
        "lexicons": root / "lexicons",
        "crossrefs": root / "crossrefs",
        "converted": root / "converted",
        "downloads": root / "downloads",
        "tmp": root / "tmp",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        log(f"Already downloaded: {dest}")
        return dest
    log(f"Downloading {url}")
    urllib.request.urlretrieve(url, dest)
    log(f"Saved to {dest}")
    return dest


def extract_zip_member(zip_path: Path, out_dir: Path, candidates: list[str]) -> Optional[Path]:
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for candidate in candidates:
            for name in names:
                if name.endswith(candidate):
                    target = out_dir / Path(name).name
                    with zf.open(name) as src, open(target, "wb") as dst:
                        dst.write(src.read())
                    return target
    return None


def normalize_book(book: str) -> str:
    b = re.sub(r"[^A-Za-z0-9 ]+", "", book).strip().lower()
    b = re.sub(r"\s+", " ", b)
    compact = b.replace(" ", "")
    return BOOK_ALIASES.get(compact, compact)


def parse_human_bible_line(line: str) -> Optional[tuple[str, int, int, str]]:
    text = line.strip()
    if not text:
        return None
    for pat in VERSE_LINE_PATTERNS:
        m = pat.match(text)
        if m:
            book = normalize_book(m.group(1))
            try:
                ch = int(m.group(2))
                vs = int(m.group(3))
            except ValueError:
                return None
            verse_text = m.group(4).strip()
            if not verse_text:
                return None
            return book, ch, vs, verse_text
    return None


def convert_human_bible_to_pipe(source: Path, dest: Path, translation: str) -> int:
    count = 0
    with open(source, "r", encoding="utf-8", errors="ignore") as inp, open(dest, "w", encoding="utf-8") as out:
        for line in inp:
            parsed = parse_human_bible_line(line)
            if not parsed:
                continue
            book, ch, vs, verse_text = parsed
            out.write(f"{translation}|{book}|{ch}|{vs}|{verse_text}\n")
            count += 1
    return count


def convert_scrollmapper_csv(source: Path, dest: Path, translation: str) -> int:
    count = 0
    with open(source, "r", encoding="utf-8", errors="ignore", newline="") as inp, open(dest, "w", encoding="utf-8", newline="") as out:
        reader = csv.DictReader(inp)
        writer = csv.writer(out)
        writer.writerow(["translation", "book", "chapter", "verse", "text", "strongs"])
        for row in reader:
            book = normalize_book(row.get("book", ""))
            chapter = row.get("chapter")
            verse = row.get("verse")
            text = row.get("text", "").strip()
            if not book or not chapter or not verse or not text:
                continue
            writer.writerow([translation, book, chapter, verse, text, row.get("strongs", "")])
            count += 1
    return count


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS verses(
            translation TEXT,
            book TEXT,
            chapter INTEGER,
            verse INTEGER,
            text TEXT,
            strongs TEXT DEFAULT ''
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS strongs(
            strongs TEXT PRIMARY KEY,
            lemma TEXT,
            transliteration TEXT,
            definition TEXT
        )
        """
    )
    conn.commit()
    return conn


def import_pipe_into_db(pipe_file: Path, db_path: Path) -> int:
    conn = connect_db(db_path)
    cur = conn.cursor()
    count = 0
    with open(pipe_file, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("|", 5)
            if len(parts) < 5:
                continue
            translation, book, chapter, verse, text = parts[:5]
            strongs = parts[5] if len(parts) > 5 else ""
            try:
                cur.execute(
                    "INSERT INTO verses (translation, book, chapter, verse, text, strongs) VALUES (?, ?, ?, ?, ?, ?)",
                    (translation, book, int(chapter), int(verse), text, strongs),
                )
                count += 1
            except ValueError:
                continue
    conn.commit()
    conn.close()
    return count


def maybe_prepare_public_downloads(dirs: dict[str, Path]) -> list[Path]:
    prepared: list[Path] = []

    web_cfg = PUBLIC_DOWNLOADS["web"]
    web_zip = download(web_cfg["url"], dirs["downloads"] / web_cfg["target_name"])
    extracted = extract_zip_member(web_zip, dirs["raw"], web_cfg["zip_member_candidates"])
    if extracted:
        prepared.append(extracted)
        log(f"Prepared WEB source: {extracted}")
    else:
        log("Could not locate a WEB source file inside the ZIP.")

    sm_cfg = PUBLIC_DOWNLOADS["scrollmapper"]
    sm_zip = download(sm_cfg["url"], dirs["downloads"] / sm_cfg["target_name"])
    with zipfile.ZipFile(sm_zip) as zf:
        csv_candidates = [n for n in zf.namelist() if n.lower().endswith(".csv") and "/csv/" in n.lower()]
        for name in csv_candidates[:10]:
            target = dirs["raw"] / Path(name).name
            with zf.open(name) as src, open(target, "wb") as dst:
                dst.write(src.read())
            prepared.append(target)
    log(f"Prepared {len(prepared)} raw source files.")
    return prepared


def infer_translation_from_name(path: Path, default: str = "web") -> str:
    name = path.stem.lower()
    for token in ["kjv", "web", "asv", "bbe", "oeb", "esv", "niv", "nasb"]:
        if token in name:
            return token
    return default


def convert_source(source: Path, converted_dir: Path, explicit_translation: Optional[str]) -> Optional[Path]:
    translation = explicit_translation or infer_translation_from_name(source)
    out_path = converted_dir / f"{source.stem}_{translation}_import.csv"

    suffix = source.suffix.lower()
    if suffix == ".csv":
        count = convert_scrollmapper_csv(source, out_path, translation)
        log(f"Converted CSV source: {source.name} -> {out_path.name} ({count} verses)")
        return out_path if count else None

    out_path = converted_dir / f"{source.stem}_{translation}_import.pipe"
    count = convert_human_bible_to_pipe(source, out_path, translation)
    log(f"Converted text source: {source.name} -> {out_path.name} ({count} verses)")
    return out_path if count else None


def import_converted_file(path: Path, db_path: Path) -> int:
    if path.suffix.lower() == ".pipe":
        return import_pipe_into_db(path, db_path)

    conn = connect_db(db_path)
    cur = conn.cursor()
    count = 0
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                cur.execute(
                    "INSERT INTO verses (translation, book, chapter, verse, text, strongs) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        row["translation"],
                        row["book"],
                        int(row["chapter"]),
                        int(row["verse"]),
                        row["text"],
                        row.get("strongs", ""),
                    ),
                )
                count += 1
            except Exception:
                continue
    conn.commit()
    conn.close()
    return count


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Prepare dataset folders, convert Bible sources, and optionally import them into the app database.")
    p.add_argument("--root", default="datasets", help="Dataset root folder to create/manage.")
    p.add_argument("--download-public", action="store_true", help="Download public/open datasets such as WEB and Scrollmapper.")
    p.add_argument("--source", action="append", default=[], help="Path to a Bible source file you already have.")
    p.add_argument("--translation", default=None, help="Explicit translation code for --source when it cannot be inferred.")
    p.add_argument("--import-into-db", action="store_true", help="Import converted sources into the SQLite database.")
    p.add_argument("--db", default=str(DEFAULT_DB), help="Database path for import step.")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    dirs = ensure_dirs(root)
    log(f"Dataset structure ready at: {root}")

    sources: list[Path] = []
    if args.download_public:
        sources.extend(maybe_prepare_public_downloads(dirs))

    for src in args.source:
        source_path = Path(src).expanduser().resolve()
        if not source_path.exists():
            log(f"Missing source file: {source_path}")
            continue
        sources.append(source_path)

    converted: list[Path] = []
    seen = set()
    for source in sources:
        if source in seen:
            continue
        seen.add(source)
        converted_path = convert_source(source, dirs["converted"], args.translation)
        if converted_path and converted_path.exists():
            converted.append(converted_path)

    if args.import_into_db:
        total = 0
        db_path = Path(args.db).expanduser().resolve()
        for item in converted:
            inserted = import_converted_file(item, db_path)
            total += inserted
            log(f"Imported {inserted} verses from {item.name} into {db_path}")
        log(f"Total imported verses: {total}")

    if not sources:
        log("No sources were converted yet. Place licensed files in datasets/raw/ or pass --source to convert them.")

    log("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
