#!/usr/bin/env python3

"""Shared text cleaning helpers for LMS-exported LMS text fields."""

from __future__ import annotations

import html
import re
from typing import Any


NON_BREAKING_SPACE = chr(160)
SUSPICIOUS_MOJIBAKE_MARKERS = ("Ã", "Â", "â", "‚", "¬")
COMMON_MOJIBAKE_REPLACEMENTS = (
    ("¬†", " "),
    ("‚Äî", "—"),
    ("‚Äú", "“"),
    ("‚Äù", "”"),
    ("‚Äò", "‘"),
    ("‚Äô", "’"),
    ("â€”", "—"),
    ("â€“", "–"),
    ("â€œ", "“"),
    ("â€", "”"),
    ("â€˜", "‘"),
    ("â€™", "’"),
    ("â€¦", "…"),
    ("â€¢", "•"),
    ("Â\u00a0", " "),
    (NON_BREAKING_SPACE, " "),
)
HTML_BREAK_TOKENS = ("<br />", "<br/>", "<br>", "</p>", "</li>")
TAG_RE = re.compile(r"<[^>]*>")
LIST_ITEM_OPEN_RE = re.compile(r"<li\b[^>]*>", re.IGNORECASE)
LMS_RICH_TEXT_COLUMNS = frozenset(
    {
        "GenAIAttestation",
        "B3Interpretation",
        "C3Interpretation",
        "D3Interpretation",
        "B3Use",
        "C3Use",
        "D3Use",
    }
)


def _count_mojibake_markers(value: str) -> int:
    return sum(value.count(marker) for marker in SUSPICIOUS_MOJIBAKE_MARKERS)


def _repair_common_utf8_mojibake(value: str) -> str:
    repaired = value
    for _ in range(2):
        if _count_mojibake_markers(repaired) == 0:
            break
        try:
            candidate = repaired.encode("cp1252").decode("utf-8")
        except UnicodeError:
            break
        if _count_mojibake_markers(candidate) >= _count_mojibake_markers(repaired):
            break
        repaired = candidate
    return repaired


def normalise_html_quotes(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value
    if len(normalized) >= 2 and normalized.startswith('"') and normalized.endswith('"'):
        normalized = normalized[1:-1]
    return normalized.replace('""', '"')


def sanitise_mojibake(value: str | None) -> str | None:
    if value is None:
        return None

    result = value
    for source, target in COMMON_MOJIBAKE_REPLACEMENTS:
        result = result.replace(source, target)

    result = _repair_common_utf8_mojibake(result)

    for source, target in COMMON_MOJIBAKE_REPLACEMENTS:
        result = result.replace(source, target)

    return result.strip()


def strip_tags(value: str | None) -> str | None:
    if value is None:
        return None
    return TAG_RE.sub("", value).strip()


def strip_html_fast_plain(raw: Any) -> str | None:
    if raw is None:
        return None

    text = normalise_html_quotes(str(raw))
    if text is not None:
        text = html.unescape(text)
    text = sanitise_mojibake(text)
    if text is None:
        return None

    text = LIST_ITEM_OPEN_RE.sub("- ", text)
    for token in HTML_BREAK_TOKENS:
        text = text.replace(token, "\n")
    text = strip_tags(text)
    if text is None:
        return None
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return sanitise_mojibake(text)


def remove_whitespace_and_zero_width(value: str | None) -> str | None:
    if value is None:
        return None
    characters_to_remove = {
        " ",
        "\t",
        "\n",
        "\r",
        NON_BREAKING_SPACE,
        chr(65279),
        chr(8203),
        chr(8204),
        chr(8205),
    }
    return "".join(character for character in value if character not in characters_to_remove)


def is_effectively_blank(value: str | None) -> bool:
    if value is None:
        return True
    return len(remove_whitespace_and_zero_width(value) or "") == 0


def is_lms_response_column(column_name: str | None) -> bool:
    if not column_name:
        return False
    return column_name.casefold().endswith("response")


def should_clean_lms_text_column(column_name: str | None) -> bool:
    if not column_name:
        return False
    return is_lms_response_column(column_name) or column_name in LMS_RICH_TEXT_COLUMNS


def clean_lms_text(raw: Any) -> str:
    return strip_html_fast_plain(raw) or ""


def clean_lms_response_text(raw: Any) -> str:
    return clean_lms_text(raw)