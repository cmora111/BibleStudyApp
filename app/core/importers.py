from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from app.core.bible_db import StrongsEntry, VerseRecord


def _clean_translation(path: Path, translation: str | None = None) -> str:
    return (translation or path.stem).strip().lower()


def parse_pipe_file(path: str | Path, translation: str | None = None) -> Iterable[VerseRecord]:
    path = Path(path)
    tr = _clean_translation(path, translation)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 4)
            if len(parts) < 4:
                continue
            book, chapter, verse, text = parts[:4]
            strongs = parts[4].strip() if len(parts) >= 5 else ""
            yield VerseRecord(
                translation=tr,
                book=book.lower().strip(),
                chapter=int(chapter),
                verse=int(verse),
                text=text.strip(),
                strongs=strongs,
            )


def parse_bible_csv(path: str | Path, translation: str | None = None) -> Iterable[VerseRecord]:
    path = Path(path)
    tr = _clean_translation(path, translation)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            book = (row.get("book") or row.get("Book") or "").strip().lower()
            chapter = row.get("chapter") or row.get("Chapter")
            verse = row.get("verse") or row.get("Verse")
            text = (row.get("text") or row.get("Text") or row.get("verse_text") or "").strip()
            strongs = (row.get("strongs") or row.get("Strongs") or row.get("strongs_codes") or "").strip()
            tr_row = (row.get("translation") or row.get("Translation") or tr).strip().lower()
            if not (book and chapter and verse and text):
                continue
            yield VerseRecord(
                translation=tr_row,
                book=book,
                chapter=int(chapter),
                verse=int(verse),
                text=text,
                strongs=strongs,
            )


def parse_bible_jsonl(path: str | Path, translation: str | None = None) -> Iterable[VerseRecord]:
    path = Path(path)
    tr = _clean_translation(path, translation)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            book = str(obj.get("book", "")).strip().lower()
            chapter = obj.get("chapter")
            verse = obj.get("verse")
            text = str(obj.get("text", "")).strip()
            strongs = str(obj.get("strongs", "")).strip()
            tr_row = str(obj.get("translation", tr)).strip().lower()
            if not (book and chapter and verse and text):
                continue
            yield VerseRecord(
                translation=tr_row,
                book=book,
                chapter=int(chapter),
                verse=int(verse),
                text=text,
                strongs=strongs,
            )


def detect_bible_format(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".pipe"}:
        return "pipe"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".csv":
        return "csv"
    raise ValueError(f"Unsupported Bible format: {path.suffix}")


def parse_bible_file(path: str | Path, translation: str | None = None, fmt: str | None = None) -> Iterable[VerseRecord]:
    path = Path(path)
    kind = (fmt or detect_bible_format(path)).lower()
    if kind == "pipe":
        yield from parse_pipe_file(path, translation=translation)
        return
    if kind == "csv":
        yield from parse_bible_csv(path, translation=translation)
        return
    if kind == "jsonl":
        yield from parse_bible_jsonl(path, translation=translation)
        return
    raise ValueError(f"Unsupported Bible parser format: {kind}")


def parse_strongs_csv(path: str | Path) -> Iterable[StrongsEntry]:
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            strongs_id = (row.get("strongs_id") or row.get("id") or "").strip().upper()
            definition = (row.get("definition") or "").strip()
            lemma = (row.get("lemma") or "").strip()
            if not strongs_id or not definition or not lemma:
                continue
            yield StrongsEntry(
                strongs_id=strongs_id,
                lemma=lemma,
                transliteration=(row.get("transliteration") or "").strip(),
                definition=definition,
                language=(row.get("language") or "unknown").strip(),
                gloss=(row.get("gloss") or "").strip(),
            )


def parse_strongs_jsonl(path: str | Path) -> Iterable[StrongsEntry]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            strongs_id = str(row.get("strongs_id") or row.get("id") or "").strip().upper()
            definition = str(row.get("definition") or "").strip()
            lemma = str(row.get("lemma") or "").strip()
            if not strongs_id or not definition or not lemma:
                continue
            yield StrongsEntry(
                strongs_id=strongs_id,
                lemma=lemma,
                transliteration=str(row.get("transliteration") or "").strip(),
                definition=definition,
                language=str(row.get("language") or "unknown").strip(),
                gloss=str(row.get("gloss") or "").strip(),
            )


def detect_strongs_format(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".jsonl":
        return "jsonl"
    raise ValueError(f"Unsupported Strong's format: {path.suffix}")


def parse_strongs_file(path: str | Path, fmt: str | None = None) -> Iterable[StrongsEntry]:
    path = Path(path)
    kind = (fmt or detect_strongs_format(path)).lower()
    if kind == "csv":
        yield from parse_strongs_csv(path)
        return
    if kind == "jsonl":
        yield from parse_strongs_jsonl(path)
        return
    raise ValueError(f"Unsupported Strong's parser format: {kind}")


def parse_bible_folder(folder: str | Path) -> Iterable[VerseRecord]:
    folder = Path(folder)
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".pipe", ".csv", ".jsonl"}:
            continue
        yield from parse_bible_file(path)
