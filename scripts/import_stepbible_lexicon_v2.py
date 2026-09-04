#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StepLexiconEntry:
    estrong: str
    dstrong: str
    ustrong: str
    lemma: str
    transliteration: str
    morph: str
    gloss: str
    definition: str


def normalize_estrong(value: str) -> str:
    value = value.strip()

    match = re.fullmatch(r"([GH])0*(\d+)([A-Za-z]*)", value, re.IGNORECASE)
    if not match:
        return value.upper()

    prefix, number, suffix = match.groups()

    return f"{prefix.upper()}{int(number)}{suffix.lower()}"


def parse_step_file(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")

        for row in reader:
            if len(row) < 8:
                continue

            raw_id = row[0].strip()

            if not re.fullmatch(r"[GH]\d+[A-Za-z]*", raw_id, re.IGNORECASE):
                continue

            yield StepLexiconEntry(
                estrong=normalize_estrong(raw_id),
                dstrong=row[1].strip(),
                ustrong=row[2].strip(),
                lemma=row[3].strip(),
                transliteration=row[4].strip(),
                morph=row[5].strip(),
                gloss=row[6].strip(),
                definition=row[7].strip(),
            )


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python scripts/import_stepbible_lexicon_v2.py "
            "<TBESG-file> <TBESH-file>"
        )
        return 1

    greek_path = Path(sys.argv[1])
    hebrew_path = Path(sys.argv[2])

    entries = list(parse_step_file(greek_path))
    entries.extend(parse_step_file(hebrew_path))

    print(f"Parsed {len(entries):,} STEP lexical records")
    print()

    wanted = {"G26", "G3056", "H430", "H2617", "H2617a", "H2617b"}

    for entry in entries:
        if entry.estrong not in wanted:
            continue

        print("=" * 72)
        print(f"eStrong:         {entry.estrong}")
        print(f"dStrong:         {entry.dstrong}")
        print(f"uStrong:         {entry.ustrong}")
        print(f"Lemma:           {entry.lemma}")
        print(f"Transliteration: {entry.transliteration}")
        print(f"Morphology:      {entry.morph}")
        print(f"Gloss:           {entry.gloss}")
        print(f"Definition:      {entry.definition[:300]}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
