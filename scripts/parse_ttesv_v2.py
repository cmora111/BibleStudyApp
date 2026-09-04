#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BOOK_MAP = {
    "Gen": "genesis", "Exo": "exodus", "Lev": "leviticus",
    "Num": "numbers", "Deu": "deuteronomy", "Jos": "joshua",
    "Jdg": "judges", "Rut": "ruth", "1Sa": "1samuel",
    "2Sa": "2samuel", "1Ki": "1kings", "2Ki": "2kings",
    "1Ch": "1chronicles", "2Ch": "2chronicles",
    "Ezr": "ezra", "Neh": "nehemiah", "Est": "esther",
    "Job": "job", "Psa": "psalms", "Pro": "proverbs",
    "Ecc": "ecclesiastes", "Sng": "songofsolomon",
    "Song": "songofsolomon", "Isa": "isaiah",
    "Jer": "jeremiah", "Lam": "lamentations",
    "Eze": "ezekiel", "Ezek": "ezekiel", "Dan": "daniel",
    "Hos": "hosea", "Joe": "joel", "Joel": "joel",
    "Amo": "amos", "Oba": "obadiah", "Jon": "jonah",
    "Mic": "micah", "Nah": "nahum", "Hab": "habakkuk",
    "Zep": "zephaniah", "Hag": "haggai",
    "Zec": "zechariah", "Mal": "malachi",

    "Mat": "matthew", "Mrk": "mark", "Luk": "luke",
    "Jhn": "john", "Act": "acts", "Rom": "romans",
    "1Co": "1corinthians", "2Co": "2corinthians",
    "Gal": "galatians", "Eph": "ephesians",
    "Php": "philippians", "Col": "colossians",
    "1Th": "1thessalonians", "2Th": "2thessalonians",
    "1Ti": "1timothy", "2Ti": "2timothy",
    "Tit": "titus", "Phm": "philemon", "Heb": "hebrews",
    "Jas": "james", "1Pe": "1peter", "2Pe": "2peter",
    "1Jn": "1john", "2Jn": "2john", "3Jn": "3john",
    "Jud": "jude", "Rev": "revelation",
}


LINE_RE = re.compile(
    r"^\$([1-3]?[A-Za-z]+)\s+(\d+):(\d+)\t(.*)$"
)

NORMAL_STRONGS_RE = re.compile(
    r"<(\d+)>"
)

PACKED_STRONGS_RE = re.compile(
    r"<([0-9+]+)>"
)

LHS_RE = re.compile(
    r"^\d+(?:\+\d+)*$"
)


@dataclass(frozen=True)
class TTESVStrongs:
    raw: str
    normalized: str | None
    language: str | None
    status: str


@dataclass
class TTESVMapping:
    lhs_raw: str
    lhs_values: tuple[int, ...]
    strongs: tuple[TTESVStrongs, ...]
    raw_field: str

    # Classification of the LHS is intentionally deferred.
    # A value such as "16" may be an ESV position, while a value
    # such as "300" may be literal numeric text.
    lhs_kind: str = "unclassified"

    notes: list[str] = field(default_factory=list)


@dataclass
class TTESVUnresolvedField:
    raw_field: str
    reason: str


@dataclass
class TTESVVerse:
    source_book: str
    book: str
    chapter: int
    verse: int
    mappings: list[TTESVMapping]
    unresolved: list[TTESVUnresolvedField]
    raw_line: str


def normalize_strongs(raw: str) -> TTESVStrongs:
    """
    Normalize only forms explicitly understood from the TTESV header.

    Documented ordinary forms:
      Hebrew: five digits beginning with zero
      Greek:  four digits

    Anything else is preserved but not guessed.
    """

    if len(raw) == 5 and raw.startswith("0"):
        return TTESVStrongs(
            raw=raw,
            normalized=f"H{int(raw)}",
            language="hebrew",
            status="normal",
        )

    if len(raw) == 4:
        return TTESVStrongs(
            raw=raw,
            normalized=f"G{int(raw)}",
            language="greek",
            status="normal",
        )

    return TTESVStrongs(
        raw=raw,
        normalized=None,
        language=None,
        status="unresolved",
    )


def parse_strongs_rhs(
    rhs: str,
) -> tuple[tuple[TTESVStrongs, ...], list[str]]:
    """
    Parse the RHS without silently discarding source information.

    Accepted forms include:

        <00216>
        <00216>+<03588>
        <03068+05251>

    The packed form is observed in TTESV even though the header's
    primary example uses separate angle brackets.
    """

    notes: list[str] = []

    # Standard:
    #   <00216>
    #   <00216>+<03588>
    standard = re.fullmatch(
        r"<\d+>(?:\+<\d+>)*",
        rhs,
    )

    if standard:
        raw_ids = tuple(NORMAL_STRONGS_RE.findall(rhs))
        return (
            tuple(normalize_strongs(x) for x in raw_ids),
            notes,
        )

    # Observed alternate/packed form:
    #   <03068+05251>
    packed = re.fullmatch(
        r"<\d+(?:\+\d+)+>",
        rhs,
    )

    if packed:
        inside = rhs[1:-1]
        raw_ids = tuple(inside.split("+"))
        notes.append("packed_strongs_syntax")

        return (
            tuple(normalize_strongs(x) for x in raw_ids),
            notes,
        )

    return (), ["unrecognized_strongs_rhs"]


def parse_mapping_field(
    raw_field: str,
) -> TTESVMapping | TTESVUnresolvedField:

    if "=" not in raw_field:
        return TTESVUnresolvedField(
            raw_field=raw_field,
            reason="missing_equals_or_lhs",
        )

    lhs, rhs = raw_field.split("=", 1)

    lhs = lhs.strip()
    rhs = rhs.strip()

    if not LHS_RE.fullmatch(lhs):
        return TTESVUnresolvedField(
            raw_field=raw_field,
            reason="unrecognized_lhs",
        )

    lhs_values = tuple(
        int(value)
        for value in lhs.split("+")
    )

    strongs, notes = parse_strongs_rhs(rhs)

    if not strongs:
        return TTESVUnresolvedField(
            raw_field=raw_field,
            reason="unrecognized_rhs",
        )

    mapping = TTESVMapping(
        lhs_raw=lhs,
        lhs_values=lhs_values,
        strongs=strongs,
        raw_field=raw_field,
        notes=notes,
    )

    if any(s.status != "normal" for s in strongs):
        mapping.notes.append("unresolved_strongs_id")

    if len(lhs_values) > 1:
        mapping.notes.append("multiple_lhs_values")

    if len(strongs) > 1:
        mapping.notes.append("multiple_strongs_ids")

    return mapping


def parse_ttesv_line(
    line: str,
) -> TTESVVerse | None:

    raw_line = line.rstrip("\n")

    match = LINE_RE.match(raw_line)

    if not match:
        return None

    source_book, chapter_s, verse_s, blob = match.groups()

    book = BOOK_MAP.get(source_book)

    if book is None:
        return None

    mappings: list[TTESVMapping] = []
    unresolved: list[TTESVUnresolvedField] = []

    fields = [
        part.strip()
        for part in blob.split("\t")
        if part.strip()
    ]

    for raw_field in fields:
        result = parse_mapping_field(raw_field)

        if isinstance(result, TTESVMapping):
            mappings.append(result)
        else:
            unresolved.append(result)

    return TTESVVerse(
        source_book=source_book,
        book=book,
        chapter=int(chapter_s),
        verse=int(verse_s),
        mappings=mappings,
        unresolved=unresolved,
        raw_line=raw_line,
    )


def parse_ttesv_file(path: Path) -> list[TTESVVerse]:
    verses: list[TTESVVerse] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            verse = parse_ttesv_line(line)

            if verse is not None:
                verses.append(verse)

    return verses


def default_source() -> Path:
    tagged_dir = (
        ROOT
        / "datasets"
        / "source"
        / "STEPBible-Data"
        / "Tagged-Bibles"
    )

    matches = sorted(tagged_dir.glob("TTESV*"))

    if not matches:
        raise FileNotFoundError(
            f"No TTESV source found under {tagged_dir}"
        )

    return matches[0]


def print_mapping(mapping: TTESVMapping) -> None:
    ids = []

    for strongs in mapping.strongs:
        if strongs.normalized:
            ids.append(
                f"{strongs.raw}->{strongs.normalized}"
            )
        else:
            ids.append(
                f"{strongs.raw}->UNRESOLVED"
            )

    print(
        f"  {mapping.lhs_raw:8} "
        f"{', '.join(ids)}"
    )

    if mapping.notes:
        print(
            f"           notes: "
            f"{', '.join(mapping.notes)}"
        )


def main() -> int:
    if len(sys.argv) > 2:
        print(
            "Usage: PYTHONPATH=. "
            "python scripts/parse_ttesv_v2.py [TTESV_FILE]"
        )
        return 2

    source = (
        Path(sys.argv[1]).expanduser().resolve()
        if len(sys.argv) == 2
        else default_source()
    )

    if not source.exists():
        print(f"Missing TTESV source: {source}")
        return 1

    verses = parse_ttesv_file(source)

    counts = Counter()

    examples: dict[
        tuple[str, int, int],
        TTESVVerse
    ] = {}

    wanted = {
        ("genesis", 1, 1),
        ("genesis", 1, 4),
        ("genesis", 5, 28),
        ("genesis", 6, 15),
        ("exodus", 17, 15),
        ("2samuel", 15, 17),
        ("2samuel", 21, 20),
        ("songofsolomon", 4, 5),
        ("john", 1, 1),
    }

    for verse in verses:
        counts["verses"] += 1
        counts["mappings"] += len(verse.mappings)
        counts["unresolved_fields"] += len(verse.unresolved)

        key = (
            verse.book,
            verse.chapter,
            verse.verse,
        )

        if key in wanted:
            examples[key] = verse

        for mapping in verse.mappings:
            counts["strongs_links"] += len(mapping.strongs)

            if len(mapping.lhs_values) > 1:
                counts["multi_lhs"] += 1

            if len(mapping.strongs) > 1:
                counts["multi_strongs"] += 1

            if "packed_strongs_syntax" in mapping.notes:
                counts["packed_strongs"] += 1

            for strongs in mapping.strongs:
                if strongs.status == "normal":
                    if strongs.language == "hebrew":
                        counts["hebrew_links"] += 1
                    elif strongs.language == "greek":
                        counts["greek_links"] += 1
                else:
                    counts["unresolved_strongs"] += 1

    print(f"Source: {source}")
    print()

    print("=== PARSE COUNTS ===")

    for key in sorted(counts):
        print(f"{key:24} {counts[key]:,}")

    print()
    print("=== SELECTED VERSES ===")

    for key in sorted(wanted):
        verse = examples.get(key)

        if verse is None:
            print()
            print(f"{key}: NOT FOUND")
            continue

        print()
        print(
            f"{verse.book} "
            f"{verse.chapter}:{verse.verse}"
        )

        for mapping in verse.mappings:
            print_mapping(mapping)

        for unresolved in verse.unresolved:
            print(
                f"  UNRESOLVED: "
                f"{unresolved.raw_field!r} "
                f"({unresolved.reason})"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
