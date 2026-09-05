"""
Lexical resolution for STEP Strong's data.

Purpose
=======

This module resolves a canonical Strong's identifier such as:

    H1004
    H430
    G1
    G3056

against the lossless STEP lexical table:

    strongs_senses

The resolver preserves the lexical relationships present in the source data.
It does NOT choose a more-specific lexical identity when the requested
identifier does not establish that specificity.

Resolution kinds
================

EXACT_SINGLE
    The requested identifier exactly matches one eStrong identity and that
    eStrong has exactly one STEP lexical record.

EXACT_MULTI
    The requested identifier exactly matches one eStrong identity, but that
    eStrong has multiple STEP lexical records.

SUFFIX_FAMILY
    No exact eStrong exists for the requested identifier, but one or more
    alphabetically suffixed eStrong identities exist.

    Example:

        H1004
            -> H1004a
            -> H1004b

UNRESOLVED
    No supported lexical relationship can be established.

Important invariants
====================

1. Every LexicalRecord corresponds to one source row in strongs_senses.

2. The resolver never silently selects one record from a plural result.

3. Exact eStrong matches take precedence over suffix-family relationships.

4. A suffix-family relationship requires an alphabetic suffix only.

       H122 -> H122a       valid
       H122 -> H122b       valid

       H122 -> H1220       NOT a suffix-family relationship

5. eStrong grouping is preserved. Multiple records beneath one eStrong are
   distinct from multiple eStrong identities.

6. Empty STEP fields remain empty.

7. Resolution order is deterministic but does not imply preference.

8. The resolver does not:
       - infer token-level lexical sense
       - choose a preferred dStrong
       - choose a preferred eStrong child
       - synthesize lemma/transliteration/gloss/definition
       - infer pronunciation
       - rewrite Bible tags
       - modify the database
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
import sqlite3
from typing import Iterable


_CANONICAL_STRONGS_RE = re.compile(r"^[HG][1-9][0-9]*$")
_ALPHA_SUFFIX_RE_TEMPLATE = r"^{base}[A-Za-z]+$"


class ResolutionKind(str, Enum):
    EXACT_SINGLE = "exact_single"
    EXACT_MULTI = "exact_multi"
    SUFFIX_FAMILY = "suffix_family"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class LexicalRecord:
    """
    One lossless row from strongs_senses.
    """

    estrong: str
    dstrong: str
    ustrong: str
    lemma: str
    transliteration: str
    morph: str
    gloss: str
    definition: str
    language: str
    source: str
    source_ordinal: int


@dataclass(frozen=True, slots=True)
class EStrongGroup:
    """
    One eStrong identity and every STEP lexical record belonging to it.
    """

    estrong: str
    records: tuple[LexicalRecord, ...]

    @property
    def record_count(self) -> int:
        return len(self.records)


@dataclass(frozen=True, slots=True)
class LexicalResolution:
    """
    Complete result of resolving one requested Strong's identifier.
    """

    requested_id: str
    normalized_id: str | None
    kind: ResolutionKind
    groups: tuple[EStrongGroup, ...]
    reason: str | None = None

    @property
    def group_count(self) -> int:
        return len(self.groups)

    @property
    def record_count(self) -> int:
        return sum(len(group.records) for group in self.groups)

    @property
    def is_resolved(self) -> bool:
        return self.kind is not ResolutionKind.UNRESOLVED

    @property
    def is_singular(self) -> bool:
        return (
            self.kind is ResolutionKind.EXACT_SINGLE
            and self.group_count == 1
            and self.record_count == 1
        )

    def iter_records(self) -> Iterable[LexicalRecord]:
        for group in self.groups:
            yield from group.records


class LexicalResolver:
    """
    Read-only resolver for STEP strongs_senses data.

    The resolver owns no database connection between calls. Each resolution
    opens a short-lived read-only SQLite connection.

    This makes the initial implementation simple and safe for isolated testing.
    Connection management can be optimized later if profiling demonstrates a
    need.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser().resolve()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, strongs_id: str) -> LexicalResolution:
        """
        Resolve one canonical Strong's identifier.

        Resolution order:

            1. normalize/validate identifier
            2. exact eStrong lookup
            3. strict alphabetic suffix-family lookup
            4. unresolved

        Exact identity always takes precedence over suffix-family discovery.
        """

        requested = "" if strongs_id is None else str(strongs_id)
        normalized = self.normalize_id(requested)

        if normalized is None:
            return LexicalResolution(
                requested_id=requested,
                normalized_id=None,
                kind=ResolutionKind.UNRESOLVED,
                groups=(),
                reason="invalid_strongs_identifier",
            )

        self._validate_database()

        with self._connect_read_only() as con:
            exact_records = self._load_records_for_estrong(
                con,
                normalized,
            )

            if exact_records:
                group = EStrongGroup(
                    estrong=normalized,
                    records=exact_records,
                )

                if len(exact_records) == 1:
                    kind = ResolutionKind.EXACT_SINGLE
                else:
                    kind = ResolutionKind.EXACT_MULTI

                return LexicalResolution(
                    requested_id=requested,
                    normalized_id=normalized,
                    kind=kind,
                    groups=(group,),
                    reason=None,
                )

            suffix_ids = self._find_suffix_estrongs(
                con,
                normalized,
            )

            if suffix_ids:
                groups = tuple(
                    EStrongGroup(
                        estrong=estrong,
                        records=self._load_records_for_estrong(
                            con,
                            estrong,
                        ),
                    )
                    for estrong in suffix_ids
                )

                return LexicalResolution(
                    requested_id=requested,
                    normalized_id=normalized,
                    kind=ResolutionKind.SUFFIX_FAMILY,
                    groups=groups,
                    reason=None,
                )

        return LexicalResolution(
            requested_id=requested,
            normalized_id=normalized,
            kind=ResolutionKind.UNRESOLVED,
            groups=(),
            reason="no_lexical_relationship",
        )

    @staticmethod
    def normalize_id(value: str) -> str | None:
        """
        Perform deliberately conservative normalization.

        Accepted:

            H1004
            h1004
            G1
            g3056

        Leading/trailing whitespace is ignored.

        Not accepted:

            00430
            3056
            H01004
            H1004a
            G0001G

        The resolver accepts the application's compatibility Strong's identity,
        not raw TTESV numbers, eStrong suffix identities, or dStrong identities.

        Additional normalization rules must be introduced deliberately rather
        than inferred here.
        """

        if value is None:
            return None

        normalized = str(value).strip().upper()

        if not _CANONICAL_STRONGS_RE.fullmatch(normalized):
            return None

        return normalized

    # ------------------------------------------------------------------
    # Database access
    # ------------------------------------------------------------------

    def _connect_read_only(self) -> sqlite3.Connection:
        """
        Open SQLite in read-only URI mode.

        No resolver operation should be capable of altering the database.
        """

        uri = self.db_path.as_uri() + "?mode=ro"

        con = sqlite3.connect(
            uri,
            uri=True,
        )

        con.row_factory = sqlite3.Row
        return con

    def _validate_database(self) -> None:
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Strong's database does not exist: {self.db_path}"
            )

        if not self.db_path.is_file():
            raise ValueError(
                f"Strong's database path is not a file: {self.db_path}"
            )

        with self._connect_read_only() as con:
            row = con.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'strongs_senses'
                """
            ).fetchone()

            if row is None:
                raise RuntimeError(
                    "Database does not contain required table "
                    "'strongs_senses'"
                )

    @staticmethod
    def _load_records_for_estrong(
        con: sqlite3.Connection,
        estrong: str,
    ) -> tuple[LexicalRecord, ...]:
        """
        Return every lossless STEP record for one exact eStrong identity.

        Ordering is deterministic source order.

        Ordering does NOT represent preference.
        """

        rows = con.execute(
            """
            SELECT
                estrong,
                dstrong,
                ustrong,
                lemma,
                transliteration,
                morph,
                gloss,
                definition,
                language,
                source,
                source_ordinal
            FROM strongs_senses
            WHERE estrong = ?
            ORDER BY
                source_ordinal,
                dstrong
            """,
            (estrong,),
        ).fetchall()

        return tuple(
            LexicalRecord(
                estrong=row["estrong"],
                dstrong=row["dstrong"],
                ustrong=row["ustrong"],
                lemma=row["lemma"],
                transliteration=row["transliteration"],
                morph=row["morph"],
                gloss=row["gloss"],
                definition=row["definition"],
                language=row["language"],
                source=row["source"],
                source_ordinal=row["source_ordinal"],
            )
            for row in rows
        )

    @staticmethod
    def _find_suffix_estrongs(
        con: sqlite3.Connection,
        base_id: str,
    ) -> tuple[str, ...]:
        """
        Find alphabetically suffixed eStrong identities belonging to base_id.

        Example:

            H1004 -> H1004a, H1004b

        Numeric prefix collisions are explicitly excluded:

            H122 -> H1220     excluded
            H122 -> H1221     excluded
        """

        # LIKE reduces the candidate set. Python performs the authoritative
        # strict suffix check.
        rows = con.execute(
            """
            SELECT DISTINCT estrong
            FROM strongs_senses
            WHERE estrong LIKE ?
            ORDER BY estrong
            """,
            (base_id + "%",),
        ).fetchall()

        suffix_re = re.compile(
            _ALPHA_SUFFIX_RE_TEMPLATE.format(
                base=re.escape(base_id)
            ),
            re.IGNORECASE,
        )

        matches = [
            row["estrong"]
            for row in rows
            if suffix_re.fullmatch(row["estrong"])
        ]

        return tuple(sorted(matches))


def format_resolution(
    resolution: LexicalResolution,
) -> str:
    """
    Human-readable diagnostic representation.

    This formatter is for development/testing. It does not define future UI
    presentation policy.
    """

    lines: list[str] = []

    lines.append("=" * 72)
    lines.append(f"requested_id : {resolution.requested_id!r}")
    lines.append(f"normalized   : {resolution.normalized_id!r}")
    lines.append(f"kind         : {resolution.kind.value}")
    lines.append(f"group_count  : {resolution.group_count}")
    lines.append(f"record_count : {resolution.record_count}")

    if resolution.reason:
        lines.append(f"reason       : {resolution.reason}")

    for group_index, group in enumerate(
        resolution.groups,
        start=1,
    ):
        lines.append("")
        lines.append(
            f"[eStrong group {group_index}] "
            f"{group.estrong} "
            f"({group.record_count} record(s))"
        )

        for record_index, record in enumerate(
            group.records,
            start=1,
        ):
            lines.append(
                f"  record {record_index}"
            )
            lines.append(
                f"    eStrong         : {record.estrong}"
            )
            lines.append(
                f"    dStrong         : {record.dstrong}"
            )
            lines.append(
                f"    uStrong         : {record.ustrong}"
            )
            lines.append(
                f"    lemma           : {record.lemma}"
            )
            lines.append(
                f"    transliteration : {record.transliteration}"
            )
            lines.append(
                f"    morph           : {record.morph}"
            )
            lines.append(
                f"    gloss           : {record.gloss}"
            )
            lines.append(
                f"    definition      : {record.definition}"
            )
            lines.append(
                f"    language        : {record.language}"
            )
            lines.append(
                f"    source          : {record.source}"
            )
            lines.append(
                f"    source_ordinal  : {record.source_ordinal}"
            )

    return "\n".join(lines)
