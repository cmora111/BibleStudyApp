#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from app.core.bible_db import BibleDB
from app.core.lexical_resolver import LexicalResolver, ResolutionKind
from app.engines.strongs_engine import StrongsWordStudyEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BIBLE_DB = PROJECT_ROOT / "data" / "bible.db"
LEXICAL_DB = (
    PROJECT_ROOT
    / "datasets"
    / "output"
    / "strongs_v2_test.db"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    require(BIBLE_DB.exists(), f"Bible database not found: {BIBLE_DB}")
    require(LEXICAL_DB.exists(), f"Lexical database not found: {LEXICAL_DB}")

    db = BibleDB(BIBLE_DB)
    resolver = LexicalResolver(LEXICAL_DB)

    engine = StrongsWordStudyEngine(
        db,
        translation="esv",
        lexical_resolver=resolver,
    )

    print("=== STRONG'S ENGINE / RESOLVER CONTRACT ===")
    print()

    # --------------------------------------------------------------
    # EXACT_SINGLE
    # --------------------------------------------------------------

    result = engine.study_code("G10")

    require(result.resolution is not None, "G10 missing resolution")
    require(
        result.resolution.kind is ResolutionKind.EXACT_SINGLE,
        f"G10 wrong kind: {result.resolution.kind}",
    )
    require(result.entry is not None, "G10 should expose legacy entry")
    require(result.entry.strongs_id == "G10", "G10 wrong legacy ID")

    record = next(result.resolution.iter_records())

    require(
        result.entry.strongs_id == record.estrong,
        "G10 legacy strongs_id does not match source record",
    )
    require(
        result.entry.lemma == record.lemma,
        "G10 legacy lemma does not match source record",
    )
    require(
        result.entry.transliteration == record.transliteration,
        "G10 legacy transliteration does not match source record",
    )
    require(
        result.entry.definition == record.definition,
        "G10 legacy definition does not match source record",
    )
    require(
        result.entry.language == record.language,
        "G10 legacy language does not match source record",
    )
    require(
        result.entry.gloss == record.gloss,
        "G10 legacy gloss does not match source record",
    )

    print("PASS EXACT_SINGLE: G10")
    print(f"  lemma:           {result.entry.lemma}")
    print(f"  transliteration: {result.entry.transliteration}")
    print()

    # --------------------------------------------------------------
    # EXACT_MULTI
    # --------------------------------------------------------------

    result = engine.study_code("G1")

    require(result.resolution is not None, "G1 missing resolution")
    require(
        result.resolution.kind is ResolutionKind.EXACT_MULTI,
        f"G1 wrong kind: {result.resolution.kind}",
    )
    require(result.resolution.record_count == 2, "G1 should have 2 records")
    require(
        result.entry is None,
        "G1 must not collapse plural resolution to legacy entry",
    )

    print("PASS EXACT_MULTI: G1")
    print(f"  records: {result.resolution.record_count}")
    print("  legacy entry: None")
    print()

    # --------------------------------------------------------------
    # SECOND EXACT_MULTI CASE
    # --------------------------------------------------------------

    result = engine.study_code("H430")

    require(result.resolution is not None, "H430 missing resolution")
    require(
        result.resolution.kind is ResolutionKind.EXACT_MULTI,
        f"H430 wrong kind: {result.resolution.kind}",
    )
    require(result.resolution.record_count == 3, "H430 should have 3 records")
    require(
        result.entry is None,
        "H430 must not collapse plural resolution to legacy entry",
    )

    print("PASS EXACT_MULTI: H430")
    print(f"  records: {result.resolution.record_count}")
    print("  legacy entry: None")
    print()

    # --------------------------------------------------------------
    # SUFFIX_FAMILY
    # --------------------------------------------------------------

    result = engine.study_code("H1004")

    require(result.resolution is not None, "H1004 missing resolution")
    require(
        result.resolution.kind is ResolutionKind.SUFFIX_FAMILY,
        f"H1004 wrong kind: {result.resolution.kind}",
    )
    require(result.resolution.group_count == 2, "H1004 should have 2 groups")
    require(
        tuple(group.estrong for group in result.resolution.groups)
        == ("H1004a", "H1004b"),
        "H1004 wrong suffix-family groups",
    )
    require(
        result.entry is None,
        "H1004 must not collapse suffix family to legacy entry",
    )

    print("PASS SUFFIX_FAMILY: H1004")
    print(
        "  groups:",
        ", ".join(group.estrong for group in result.resolution.groups),
    )
    print("  legacy entry: None")
    print()

    # --------------------------------------------------------------
    # UNRESOLVED
    # --------------------------------------------------------------

    result = engine.study_code("H999999")

    require(result.resolution is not None, "H999999 missing resolution")
    require(
        result.resolution.kind is ResolutionKind.UNRESOLVED,
        f"H999999 wrong kind: {result.resolution.kind}",
    )
    require(result.entry is None, "unresolved result should have no entry")

    print("PASS UNRESOLVED: H999999")
    print("  legacy entry: None")
    print()

    # --------------------------------------------------------------
    # LEGACY PATH
    # --------------------------------------------------------------

    legacy_engine = StrongsWordStudyEngine(
        db,
        translation="esv",
    )

    legacy_result = legacy_engine.study_code("G1")

    require(
        legacy_result.resolution is None,
        "legacy path should not manufacture a lexical resolution",
    )

    print("PASS LEGACY PATH")
    print("  resolution: None")
    print()

    print("ALL ENGINE CONTRACT TESTS PASSED")


if __name__ == "__main__":
    main()
