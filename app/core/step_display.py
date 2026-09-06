"""
Plain-text presentation helpers for lossless STEP lexical content.

These functions transform known STEP presentation markup for display only.
They do not modify, normalize, or reinterpret the authoritative source data.
"""

from __future__ import annotations

import re


_BREAK_TAG_RE = re.compile(
    r"<\s*(?:br|lb)\s*/?\s*>",
    re.IGNORECASE,
)

_KNOWN_TAG_RE = re.compile(
    r"</?\s*(?:"
    r"b|i|ref|re|author|date|a|greek|note|def|corr"
    r")\b[^>]*>",
    re.IGNORECASE,
)


def step_plain_text(text: str) -> str:
    """
    Project known STEP presentation markup to readable plain text.

    Only observed, explicitly recognized STEP tags are transformed.
    Unknown angle-bracket content is preserved.
    """
    if not text:
        return ""

    rendered = _BREAK_TAG_RE.sub("\n", text)
    rendered = _KNOWN_TAG_RE.sub("", rendered)

    # Remove presentation whitespace surrounding line breaks while
    # preserving the source's textual content and paragraph structure.
    lines = [line.strip() for line in rendered.splitlines()]

    # Collapse runs of blank lines introduced by adjacent break tags.
    output: list[str] = []
    previous_blank = False

    for line in lines:
        blank = not line

        if blank and previous_blank:
            continue

        output.append(line)
        previous_blank = blank

    return "\n".join(output).strip()
