#!/usr/bin/env python3

"""
Inspection harness for LexicalResolver v1.

Database:

    datasets/output/strongs_v2_test.db

This script is intentionally read-only.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.lexical_resolver import (
    LexicalResolver,
    ResolutionKind,
    format_resolution,
)


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "datasets" / "output" / "strongs_v2_test.db"


def find_exact_single_id() -> str:
    """
    Find one actual eStrong in the disposable DB that has exactly one record.

    This avoids inventing an arbitrary fixture.
    """

    uri = DB_PATH.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(uri, uri=True) as con:
        row = con.execute(
            """
            SELECT estrong
            FROM strongs_senses
            GROUP BY estrong
            HAVING COUNT(*) = 1
            ORDER BY estrong
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        raise RuntimeError(
            "Could not find an exact-single eStrong fixture"
        )

    return row[0]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_exact_single(
    resolver: LexicalResolver,
    strongs_id: str,
) -> None:
    result = resolver.resolve(strongs_id)

    assert_true(
        result.kind is ResolutionKind.EXACT_SINGLE,
        f"{strongs_id}: expected EXACT_SINGLE, got {result.kind}",
    )

    assert_true(
        result.group_count == 1,
        f"{strongs_id}: expected 1 group",
    )

    assert_true(
        result.record_count == 1,
        f"{strongs_id}: expected 1 record",
    )

    assert_true(
        result.groups[0].estrong == strongs_id,
        f"{strongs_id}: wrong eStrong",
    )

    print(
        f"PASS exact_single: {strongs_id}"
    )


def test_g1_exact_multi(
    resolver: LexicalResolver,
) -> None:
    result = resolver.resolve("G1")

    assert_true(
        result.kind is ResolutionKind.EXACT_MULTI,
        f"G1: expected EXACT_MULTI, got {result.kind}",
    )

    assert_true(
        result.group_count == 1,
        "G1: expected one eStrong group",
    )

    assert_true(
        result.groups[0].estrong == "G1",
        "G1: expected eStrong group G1",
    )

    dstrongs = {
        record.dstrong
        for record in result.groups[0].records
    }

    assert_true(
        "G0001G =" in dstrongs,
        "G1: missing dStrong G0001G =",
    )

    assert_true(
        "G0001H =" in dstrongs,
        "G1: missing dStrong G0001H =",
    )

    transliterations = {
        record.transliteration
        for record in result.groups[0].records
    }

    assert_true(
        "Alpha" in transliterations,
        "G1: missing Alpha transliteration",
    )

    assert_true(
        "a" in transliterations,
        "G1: missing a transliteration",
    )

    print(
        "PASS exact_multi: G1"
    )


def test_h1004_suffix_family(
    resolver: LexicalResolver,
) -> None:
    result = resolver.resolve("H1004")

    assert_true(
        result.kind is ResolutionKind.SUFFIX_FAMILY,
        f"H1004: expected SUFFIX_FAMILY, got {result.kind}",
    )

    estrongs = {
        group.estrong
        for group in result.groups
    }

    assert_true(
        "H1004a" in estrongs,
        "H1004: missing H1004a",
    )

    assert_true(
        "H1004b" in estrongs,
        "H1004: missing H1004b",
    )

    assert_true(
        "H1004" not in estrongs,
        "H1004: bare ID must not be manufactured as a group",
    )

    print(
        "PASS suffix_family: H1004"
    )


def test_h122_numeric_prefix_exclusion(
    resolver: LexicalResolver,
) -> None:
    result = resolver.resolve("H122")

    assert_true(
        result.kind is ResolutionKind.SUFFIX_FAMILY,
        f"H122: expected SUFFIX_FAMILY, got {result.kind}",
    )

    estrongs = {
        group.estrong
        for group in result.groups
    }

    assert_true(
        estrongs == {"H122a", "H122b"},
        (
            "H122: expected exactly H122a and H122b; "
            f"got {sorted(estrongs)}"
        ),
    )

    assert_true(
        all(
            not estrong.startswith(
                (
                    "H1220",
                    "H1221",
                    "H1222",
                    "H1223",
                    "H1224",
                    "H1225",
                    "H1226",
                    "H1227",
                    "H1228",
                    "H1229",
                )
            )
            for estrong in estrongs
        ),
        "H122: numeric prefix collision leaked into suffix family",
    )

    print(
        "PASS strict suffix rule: H122"
    )


def test_unknown(
    resolver: LexicalResolver,
) -> None:
    result = resolver.resolve("H999999")

    assert_true(
        result.kind is ResolutionKind.UNRESOLVED,
        (
            "H999999: expected UNRESOLVED, "
            f"got {result.kind}"
        ),
    )

    assert_true(
        result.normalized_id == "H999999",
        "H999999: normalized ID not preserved",
    )

    assert_true(
        result.group_count == 0,
        "H999999: unresolved result must have zero groups",
    )

    assert_true(
        result.record_count == 0,
        "H999999: unresolved result must have zero records",
    )

    assert_true(
        result.reason == "no_lexical_relationship",
        (
            "H999999: unexpected reason "
            f"{result.reason!r}"
        ),
    )

    print(
        "PASS unresolved: H999999"
    )


def test_invalid_identifier(
    resolver: LexicalResolver,
) -> None:
    result = resolver.resolve("00430")

    assert_true(
        result.kind is ResolutionKind.UNRESOLVED,
        "00430: expected UNRESOLVED",
    )

    assert_true(
        result.normalized_id is None,
        "00430: raw TTESV number must not be silently normalized",
    )

    assert_true(
        result.reason == "invalid_strongs_identifier",
        (
            "00430: unexpected reason "
            f"{result.reason!r}"
        ),
    )

    print(
        "PASS conservative normalization: 00430"
    )


def test_lowercase_normalization(
    resolver: LexicalResolver,
) -> None:
    upper = resolver.resolve("G1")
    lower = resolver.resolve("  g1  ")

    assert_true(
        lower.normalized_id == "G1",
        "g1: expected normalization to G1",
    )

    assert_true(
        lower.kind == upper.kind,
        "g1: resolution kind differs from G1",
    )

    assert_true(
        lower.groups == upper.groups,
        "g1: resolution data differs from G1",
    )

    print(
        "PASS case/whitespace normalization: g1"
    )


def test_deterministic_order(
    resolver: LexicalResolver,
) -> None:
    first = resolver.resolve("G1")
    second = resolver.resolve("G1")

    assert_true(
        first == second,
        "G1: repeated resolution was not deterministic",
    )

    print(
        "PASS deterministic ordering: G1"
    )


def show_representative_results(
    resolver: LexicalResolver,
    exact_single_id: str,
) -> None:
    print()
    print()
    print("===== REPRESENTATIVE RESOLUTIONS =====")

    for strongs_id in (
        exact_single_id,
        "G1",
        "H430",
        "H1004",
        "H122",
        "H999999",
    ):
        print()
        print(
            format_resolution(
                resolver.resolve(strongs_id)
            )
        )


def main() -> None:
    print(
        f"Database: {DB_PATH}"
    )

    resolver = LexicalResolver(DB_PATH)

    exact_single_id = find_exact_single_id()

    print()
    print("===== CONTRACT TESTS =====")

    test_exact_single(
        resolver,
        exact_single_id,
    )

    test_g1_exact_multi(
        resolver,
    )

    test_h1004_suffix_family(
        resolver,
    )

    test_h122_numeric_prefix_exclusion(
        resolver,
    )

    test_unknown(
        resolver,
    )

    test_invalid_identifier(
        resolver,
    )

    test_lowercase_normalization(
        resolver,
    )

    test_deterministic_order(
        resolver,
    )

    print()
    print("ALL CONTRACT TESTS PASSED")

    show_representative_results(
        resolver,
        exact_single_id,
    )


if __name__ == "__main__":
    main()
