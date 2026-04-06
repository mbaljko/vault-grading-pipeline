from __future__ import annotations

import csv
import re
from pathlib import Path


RESPONSE_TEXT_COLUMN = "response_text"
SUBMISSION_ID_COLUMN = "submission_id"
LEADING_TICKED_HEADER_RE = re.compile(r"\A`+\s*(?=\+\+\+)", re.DOTALL)
HEADER_BLOCK_RE = re.compile(r"\A\+\+\+(?P<header>[^\n]+)\n\+\+\+\n?", re.DOTALL)
FOOTER_BLOCK_RE = re.compile(r"\n?\+\+\+\s*\Z", re.DOTALL)
LEADING_SECTION_HEADING_RE = re.compile(
    r"\A\s*Section\s*(?:[\n\r]+\s*)?(?P<section>[A-Z])\s*(?:[:\-\u2013\u2014]|‚Äì|‚Äî)\s*Constraint\s+Interaction\s+Claims\s*",
    re.IGNORECASE,
)
EMPTY_RESPONSE_PLACEHOLDERS = {"<<EMPTY>>"}
CLAIM_MARKER_SEGMENT_RE = re.compile(
    r"(?im)(?<![a-z])(?P<segment>(?:analytic\s+)?claim(?:\s+statement)?\s*#?\s*(?P<number>[123])\s*[:.)-]?)"
)
PLAIN_CLAIM_STATEMENT_SEGMENT_RE = re.compile(
    r"(?im)(?:^|[\n\r])\s*(?P<segment>claim\s+statement\s*[:.)-]?)"
)
PLAIN_CLAIM_SEGMENT_RE = re.compile(
    r"(?im)(?:^|[\n\r])\s*(?P<segment>claim\s*[:.)-])"
)
NUMBERED_MARKER_SEGMENT_RE = re.compile(
    r"(?im)(?:^|[\n\r])\s*(?P<segment>(?P<number>[123])\s*[.)]\s+)"
)
IN_THIS_SYSTEM_SEGMENT_RE = re.compile(r"(?i)(?P<segment>(?:-\s*)?in\s+(?:this|the)\s*system)")


def load_csv_rows(input_path: Path) -> tuple[list[dict[str, str]], str]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header row: {input_path}")

        normalized_fieldnames = {field.strip().lower(): field for field in reader.fieldnames if field}
        response_text_key = normalized_fieldnames.get(RESPONSE_TEXT_COLUMN)
        if response_text_key is None:
            raise ValueError(f"CSV is missing required '{RESPONSE_TEXT_COLUMN}' column: {input_path}")

        rows: list[dict[str, str]] = []
        for raw_row in reader:
            normalized_row: dict[str, str] = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                normalized_row[key.strip()] = (value or "")
            if not any(value.strip() for value in normalized_row.values()):
                continue
            rows.append(normalized_row)

    return rows, response_text_key


def extract_response_payload(response_text: str) -> tuple[str, str]:
    stripped_text = response_text.strip()
    header_info = ""
    stripped_text = LEADING_TICKED_HEADER_RE.sub("", stripped_text)

    header_match = HEADER_BLOCK_RE.match(stripped_text)
    if header_match:
        header_info = header_match.group("header").strip()
        stripped_text = stripped_text[header_match.end():]

    stripped_text = FOOTER_BLOCK_RE.sub("", stripped_text).strip()
    stripped_text = LEADING_SECTION_HEADING_RE.sub("", stripped_text, count=1).lstrip()
    if stripped_text.strip().upper() in EMPTY_RESPONSE_PLACEHOLDERS:
        stripped_text = ""
    return header_info, stripped_text


def extract_submission_id(row: dict[str, str], header_info: str) -> str:
    submission_id = row.get(SUBMISSION_ID_COLUMN, "").strip()
    if submission_id:
        return submission_id

    prefix = "submission_id="
    if header_info.startswith(prefix):
        return header_info[len(prefix):].strip()
    return ""


def strip_outer_wrapping_quotes(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    return text


def build_reconstruction_check_output(
    cleaned_response_text: str,
    claim_1: str,
    claim_2: str,
    claim_3: str,
) -> str:
    reconstructed_text = f"{claim_1}{claim_2}{claim_3}"
    if reconstructed_text == cleaned_response_text:
        return "ok"

    normalized_cleaned = strip_outer_wrapping_quotes(cleaned_response_text)
    normalized_reconstructed = strip_outer_wrapping_quotes(reconstructed_text)
    if normalized_reconstructed == normalized_cleaned:
        return "ok_after_outer_quote_normalization"

    mismatch_index = 0
    max_prefix = min(len(normalized_cleaned), len(normalized_reconstructed))
    while (
        mismatch_index < max_prefix
        and normalized_cleaned[mismatch_index] == normalized_reconstructed[mismatch_index]
    ):
        mismatch_index += 1

    expected_char = (
        repr(normalized_cleaned[mismatch_index])
        if mismatch_index < len(normalized_cleaned)
        else "<end>"
    )
    actual_char = (
        repr(normalized_reconstructed[mismatch_index])
        if mismatch_index < len(normalized_reconstructed)
        else "<end>"
    )
    return (
        "mismatch"
        f"; first_difference_index={mismatch_index}"
        f"; expected_char={expected_char}"
        f"; actual_char={actual_char}"
        f"; expected_length={len(normalized_cleaned)}"
        f"; actual_length={len(normalized_reconstructed)}"
    )


def select_ordered_triplet_starts(matches: list[tuple[int, int]]) -> list[int]:
    expected_number = 1
    starts: list[int] = []
    for number, start in matches:
        if number != expected_number:
            continue
        starts.append(start)
        expected_number += 1
        if expected_number == 4:
            return starts
    return []


def split_claims_from_starts(cleaned_response_text: str, starts: list[int]) -> tuple[str, str, str] | None:
    if len(starts) != 3:
        return None
    if sorted(starts) != starts or len(set(starts)) != 3:
        return None
    if (
        starts[0] == 1
        and len(cleaned_response_text) >= 2
        and cleaned_response_text[0] == cleaned_response_text[-1]
        and cleaned_response_text[0] in {'"', "'"}
    ):
        starts = [0, starts[1], starts[2]]
    return (
        cleaned_response_text[starts[0]:starts[1]],
        cleaned_response_text[starts[1]:starts[2]],
        cleaned_response_text[starts[2]:],
    )


def parse_segment_starts_with_numbered_pattern(
    cleaned_response_text: str,
    pattern: re.Pattern[str],
) -> list[int]:
    matches = [
        (int(match.group("number")), match.start("segment"))
        for match in pattern.finditer(cleaned_response_text)
    ]
    return select_ordered_triplet_starts(matches)


def try_easy_parse_claims(
    cleaned_response_text: str,
) -> tuple[tuple[str, str, str] | None, str]:
    if not cleaned_response_text.strip():
        return ("", "", ""), "empty_response"

    claim_marker_starts = parse_segment_starts_with_numbered_pattern(
        cleaned_response_text,
        CLAIM_MARKER_SEGMENT_RE,
    )
    if claim_marker_starts:
        claims = split_claims_from_starts(cleaned_response_text, claim_marker_starts)
        if claims is not None:
            reconstruction_status = build_reconstruction_check_output(cleaned_response_text, *claims)
            if reconstruction_status in {"ok", "ok_after_outer_quote_normalization"}:
                return claims, "claim_markers"

    numbered_marker_starts = parse_segment_starts_with_numbered_pattern(
        cleaned_response_text,
        NUMBERED_MARKER_SEGMENT_RE,
    )
    if numbered_marker_starts:
        claims = split_claims_from_starts(cleaned_response_text, numbered_marker_starts)
        if claims is not None:
            reconstruction_status = build_reconstruction_check_output(cleaned_response_text, *claims)
            if reconstruction_status in {"ok", "ok_after_outer_quote_normalization"}:
                return claims, "numbered_markers"

    plain_claim_statement_starts = [
        match.start("segment")
        for match in PLAIN_CLAIM_STATEMENT_SEGMENT_RE.finditer(cleaned_response_text)
    ]
    if len(plain_claim_statement_starts) >= 3:
        claims = split_claims_from_starts(cleaned_response_text, plain_claim_statement_starts[:3])
        if claims is not None:
            reconstruction_status = build_reconstruction_check_output(cleaned_response_text, *claims)
            if reconstruction_status in {"ok", "ok_after_outer_quote_normalization"}:
                return claims, "plain_claim_statement_markers"

    plain_claim_starts = [
        match.start("segment")
        for match in PLAIN_CLAIM_SEGMENT_RE.finditer(cleaned_response_text)
    ]
    if len(plain_claim_starts) >= 3:
        claims = split_claims_from_starts(cleaned_response_text, plain_claim_starts[:3])
        if claims is not None:
            reconstruction_status = build_reconstruction_check_output(cleaned_response_text, *claims)
            if reconstruction_status in {"ok", "ok_after_outer_quote_normalization"}:
                return claims, "plain_claim_markers"

    in_this_system_starts = [
        match.start("segment")
        for match in IN_THIS_SYSTEM_SEGMENT_RE.finditer(cleaned_response_text)
    ]
    if len(in_this_system_starts) >= 3:
        claims = split_claims_from_starts(cleaned_response_text, in_this_system_starts[:3])
        if claims is not None:
            reconstruction_status = build_reconstruction_check_output(cleaned_response_text, *claims)
            if reconstruction_status in {"ok", "ok_after_outer_quote_normalization"}:
                return claims, "in_this_system_triplet"

    return None, "llm"