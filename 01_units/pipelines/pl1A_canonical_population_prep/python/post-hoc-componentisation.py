#!/usr/bin/env python3

"""Segment submission response text into three claim-level rows via the shared LLM runner.

This script is the Layer 0 segmentation step for canonical population prep. It reads a
submission-level CSV, strips wrapper markup from each response, sends cleaned submissions
to the shared prompt runner in batches, and writes two outputs:

1. A claim-expanded CSV with one row per claim/component.
2. An audit CSV that preserves the cleaned submission text, raw LLM output, parsed claim
     columns, reconstruction checks, and any batch-level errors.

The script is intentionally batch-oriented. Each batch stores its prompt input, parsed
output, audit CSV, and status metadata under ``--batch-cache-dir`` so runs can be resumed,
rerun selectively, or rebuilt entirely from cached artifacts.

Expected inputs
----------------
- ``--input-path`` must point to a CSV with a header row.
- The CSV must include a ``response_text`` column.  
- all rows of the CSV contain response_text values to be segmented.
- A ``submission_id`` column is optional. If it is missing, the script will try to recover
    the submission ID from the leading ``+++submission_id=...`` wrapper inside the response text.
- Source response text may be wrapped in the house format:

    ``+++submission_id=...``
    ``+++``
    response body
    ``+++``

    The script removes that wrapper before calling the LLM runner.
- The output filename is also significant: its basename must contain either an ``AP<digits><section>_``
    prefix such as ``AP3B_...`` or a component marker such as ``SectionBResponse``. That section
    letter is used to derive the claim columns written to the audit CSV, for example
    ``claim_B1``, ``claim_B2``, and ``claim_B3``.

Outputs
-------
- ``--output-path`` receives the claim-expanded CSV with columns:
    ``submission_id``, ``component_id``, ``response_text``.
- ``--output-audit-path`` receives the full audit CSV with cleaned submission text, parse
    strategy, raw LLM output, three parsed claim columns, reconstruction diagnostics, and any
    LLM error message.
- ``--batch-cache-dir`` stores per-batch intermediate files and status JSON used for reruns.

LLM output contract
-------------------
For each submitted response, the prompt runner is expected to return one fenced Markdown block
containing explicit ``<row index="N">`` wrappers. Each row wrapper must contain exactly one
``<claim1>...</claim1>``, ``<claim2>...</claim2>``, and ``<claim3>...</claim3>`` block. This
format supports multiline verbatim claims. The parser retains backward compatibility with the
older single-line ``∞``-delimited format as a fallback.

Deterministic-only mode
-----------------------
When ``--deterministic-only`` is set, the script performs only the structural first pass,
writes claim-expanded rows for submissions segmented deterministically, and writes an audit
CSV for all rows. Rows that still require the LLM are marked as pending in the audit and are
not sent to the prompt runner.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any


RESPONSE_TEXT_COLUMN = "response_text"
SUBMISSION_ID_COLUMN = "submission_id"
DEFAULT_BATCH_SIZE = 20
LEADING_TICKED_HEADER_RE = re.compile(r"\A`+\s*(?=\+\+\+)", re.DOTALL)
HEADER_BLOCK_RE = re.compile(r"\A\+\+\+(?P<header>[^\n]+)\n\+\+\+\n?", re.DOTALL)
FOOTER_BLOCK_RE = re.compile(r"\n?\+\+\+\s*\Z", re.DOTALL)
FENCED_BLOCK_RE = re.compile(r"(?ms)^\s*`{3,4}[^\n`]*\n(?P<body>.*?)\n\s*`{3,4}\s*$")
LEADING_SECTION_HEADING_RE = re.compile(
    r"\A\s*Section\s*(?:[\n\r]+\s*)?(?P<section>[A-Z])\s*(?:[:\-\u2013\u2014]|‚Äì|‚Äî)\s*Constraint\s+Interaction\s+Claims\s*",
    re.IGNORECASE,
)
EMPTY_RESPONSE_PLACEHOLDERS = {"<<EMPTY>>"}
STANDALONE_LEADING_LABEL_RE = re.compile(
    r"(?is)(?P<label>(?:analytic\s+)?(?:claim|constraint|case)(?:\s+statement)?\s*)\Z"
)
ASSIGNMENT_SECTION_RE = re.compile(r"^(AP\d+)([A-Z])_", re.IGNORECASE)
SECTION_COMPONENT_RE = re.compile(r"Section([A-Z])\d*Response", re.IGNORECASE)
SUBMISSION_TAG_RE = re.compile(r'(?m)^<submission index="')
CLAIM_MARKER_SEGMENT_RE = re.compile(
    r"(?im)(?<![a-z])(?P<segment>(?:analytic\s+)?(?:claim|constraint|case)(?:\s+statement)?\s*#?\s*(?P<number>[123])\s*[:.)-]?)"
)
PLAIN_CLAIM_STATEMENT_SEGMENT_RE = re.compile(
    r"(?im)(?:^|[\n\r])\s*(?P<segment>claim\s+statement\s*[:.)-]?)"
)
PLAIN_CLAIM_SEGMENT_RE = re.compile(
    r"(?im)(?:^|[\n\r])\s*(?P<segment>claim\s*[:.)-])"
)
ORDINAL_LABEL_SEGMENT_RE = re.compile(
    r"(?im)(?:^|[\n\r])\s*(?P<segment>(?:the\s+)?(?P<ordinal>first|second|third|final)\s+(?:analytic\s+)?(?:claim|constraint|case)(?:\s+is(?:\s+that)?)?\s*[:.)-]?)"
)
COLON_NUMBERED_MARKER_SEGMENT_RE = re.compile(
    r"(?im)(?:^|[\n\r])\s*(?P<segment>(?P<number>[123])\s*:\s*)"
)
NUMBERED_MARKER_SEGMENT_RE = re.compile(
    r"(?im)(?:^|[\n\r])\s*(?P<segment>(?P<number>[123])\s*[.)]\s+)"
)
IN_THIS_SYSTEM_SEGMENT_RE = re.compile(r"(?i)(?P<segment>(?:-\s*)?in\s+(?:this|the)\s*system)")
BULLET_O_SEGMENT_RE = re.compile(r"(?im)(?:^|[\n\r])\s*(?P<segment>o)\s*(?=$|[\n\r])")
STRUCTURED_ROW_BLOCK_RE = re.compile(
    r"(?s)<row\b[^>]*\bindex=[\"'](?P<index>\d+)[\"'][^>]*>\s*"
    r"<claim1>(?P<claim_1>.*?)</claim1>\s*"
    r"<claim2>(?P<claim_2>.*?)</claim2>\s*"
    r"<claim3>(?P<claim_3>.*?)</claim3>\s*"
    r"</row>"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read a submission-level CSV, clean and batch response_text values, invoke the shared "
            "LLM runner, and write both claim-expanded and audit CSV outputs."
        ),
        epilog=(
            "Input requirements:\n"
            "  - --input-path must be a CSV containing a response_text column.\n"
            "  - submission_id is optional if it is embedded in the +++submission_id=... wrapper.\n"
            "  - The output filename must include either an AP<digits><section> prefix or a SectionXResponse token\n"
            "    so the script can derive claim column names such as claim_B1, claim_B2, claim_B3.\n\n"
            "Batch cache behavior:\n"
            "  - Each batch writes input, output, audit, and status files under --batch-cache-dir.\n"
            "  - Use --rerun-batch / --rerun-batches to rerun selected batches.\n"
            "  - Use --rerun-failed-batches to rerun only failed batches.\n"
            "  - Use --rebuild-from-batch-cache to skip API calls and rebuild final outputs only from successful cache artifacts.\n\n"
            "Examples:\n"
            "  python post-hoc-componentisation.py --input-path AP3B_source.csv --output-path AP3B_segmented.csv \\\n"
            "    --output-audit-path AP3B_segmented_audit.csv --runner-prompt-path segmentation_prompt.md \\\n"
            "    --batch-cache-dir batch_cache\n"
            "  python post-hoc-componentisation.py ... --rerun-batches 3,5\n"
            "  python post-hoc-componentisation.py ... --rebuild-from-batch-cache"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input-path", type=Path, required=True, help="Source file for segmentation input.")
    parser.add_argument("--output-path", type=Path, required=True, help="Destination CSV file for cleaned segmentation rows.")
    parser.add_argument(
        "--output-audit-path",
        type=Path,
        required=True,
        help="Destination CSV file for the audit copy of the cleaned segmentation rows.",
    )
    parser.add_argument(
        "--runner-prompt-path",
        type=Path,
        required=True,
        help="Prompt instructions file passed through to the shared LLM runner.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature passed to the shared LLM runner.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="Top-p value passed to the shared LLM runner.",
    )
    parser.add_argument(
        "--runner-dry-run",
        action="store_true",
        help="Pass --dry-run through to the shared LLM runner instead of calling the API.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of cleaned submissions to send in each LLM runner call (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--batch-cache-dir",
        type=Path,
        required=True,
        help="Directory used to store per-batch cache artifacts for reruns and rebuilds.",
    )
    parser.add_argument(
        "--rerun-batch",
        type=int,
        action="append",
        default=[],
        help="Rerun only the specified batch number. Repeatable.",
    )
    parser.add_argument(
        "--rerun-batches",
        type=str,
        default="",
        help="Comma-separated list of batch numbers to rerun, for example 3,5,8.",
    )
    parser.add_argument(
        "--rerun-failed-batches",
        action="store_true",
        help="Rerun only batches currently marked failed in the batch cache.",
    )
    parser.add_argument(
        "--rebuild-from-batch-cache",
        action="store_true",
        help="Do not invoke the LLM runner; rebuild final outputs only from existing batch cache artifacts.",
    )
    parser.add_argument(
        "--deterministic-only",
        action="store_true",
        help=(
            "Run only the deterministic structural parser, write claim-expanded rows for resolved submissions, "
            "and mark unresolved submissions as pending LLM segmentation in the audit CSV."
        ),
    )
    return parser.parse_args()


def load_csv_rows(input_path: Path) -> tuple[list[dict[str, str]], str]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header row: {input_path}")

        normalized_fieldnames = {field.strip().lower(): field for field in reader.fieldnames if field}
        response_text_key = normalized_fieldnames.get(RESPONSE_TEXT_COLUMN)
        if response_text_key is None:
            raise ValueError(
                f"CSV is missing required '{RESPONSE_TEXT_COLUMN}' column: {input_path}"
            )

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

    # Some source rows carry a stray leading backtick before the submission header.
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


def is_metadata_only_output_line(line: str) -> bool:
    stripped_line = line.strip()
    if not stripped_line:
        return True
    return (
        stripped_line == "+++"
        or stripped_line.startswith("+++submission_id=")
        or stripped_line.startswith("<submission ")
        or stripped_line == "</submission>"
    )


def extract_submission_id(row: dict[str, str], header_info: str) -> str:
    submission_id = row.get(SUBMISSION_ID_COLUMN, "").strip()
    if submission_id:
        return submission_id

    prefix = "submission_id="
    if header_info.startswith(prefix):
        return header_info[len(prefix):].strip()

    return ""


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError(f"Could not locate repository root from: {start}")


def resolve_runner_script_path() -> Path:
    repo_root = find_repo_root(Path(__file__).resolve().parent)
    runner_script_path = repo_root / "01_units/apps/prompt_runners/invoke_chatgpt_API.py"
    if not runner_script_path.exists():
        raise FileNotFoundError(f"Runner script not found: {runner_script_path}")
    return runner_script_path


def build_batch_prompt_input(batch_rows: list[dict[str, str]]) -> str:
    blocks: list[str] = []
    for batch_offset, row in enumerate(batch_rows, start=1):
        submission_id = row.get("submission_id", "").strip() or f"batch_item_{batch_offset:02d}"
        cleaned_response_text = row.get("cleaned_response_text", "")
        blocks.append(
            "\n".join(
                [
                    f"<submission index=\"{batch_offset}\" submission_id=\"{submission_id}\">",
                    cleaned_response_text,
                    "</submission>",
                ]
            )
        )
    return "\n\n".join(blocks)


def extract_fenced_markdown_body(text: str) -> str:
    stripped_text = text.strip()
    match = FENCED_BLOCK_RE.match(stripped_text)
    if match:
        return match.group("body").strip()
    return stripped_text


def strip_outer_wrapping_quotes(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    return text


def resolve_claim_column_names(input_path: Path) -> list[str]:
    match = ASSIGNMENT_SECTION_RE.match(input_path.name)
    if match:
        section_letter = match.group(2).upper()
    else:
        component_match = SECTION_COMPONENT_RE.search(input_path.name)
        if not component_match:
            raise ValueError(
                "Input filename must include either an APXY_ prefix or SectionYResponse component, "
                f"for example AP2B_... or ...SectionBResponse...: {input_path.name}"
            )
        section_letter = component_match.group(1).upper()

    return [
        f"claim_{section_letter}1",
        f"claim_{section_letter}2",
        f"claim_{section_letter}3",
    ]


def wrap_claim_response_text(submission_header: str, claim_text: str) -> str:
    header_line = submission_header.strip() or "submission_id="
    claim_body = claim_text.strip()
    return f"+++{header_line}\n+++\n{claim_body}\n+++\n"


def build_component_id_from_claim_column(claim_column_name: str) -> str:
    suffix = claim_column_name.removeprefix("claim_")
    return f"Section{suffix}Response"


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
    leading_label_match = STANDALONE_LEADING_LABEL_RE.search(cleaned_response_text[:starts[0]])
    if leading_label_match is not None:
        starts = [leading_label_match.start("label"), starts[1], starts[2]]
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


def parse_segment_starts_with_ordinal_pattern(
    cleaned_response_text: str,
    pattern: re.Pattern[str],
) -> list[int]:
    ordinal_to_number = {
        "first": 1,
        "second": 2,
        "third": 3,
        "final": 3,
    }
    matches = [
        (ordinal_to_number[match.group("ordinal").lower()], match.start("segment"))
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

    colon_numbered_marker_starts = parse_segment_starts_with_numbered_pattern(
        cleaned_response_text,
        COLON_NUMBERED_MARKER_SEGMENT_RE,
    )
    if colon_numbered_marker_starts:
        claims = split_claims_from_starts(cleaned_response_text, colon_numbered_marker_starts)
        if claims is not None:
            reconstruction_status = build_reconstruction_check_output(cleaned_response_text, *claims)
            if reconstruction_status in {"ok", "ok_after_outer_quote_normalization"}:
                return claims, "colon_numbered_markers"

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

    ordinal_label_starts = parse_segment_starts_with_ordinal_pattern(
        cleaned_response_text,
        ORDINAL_LABEL_SEGMENT_RE,
    )
    if ordinal_label_starts:
        claims = split_claims_from_starts(cleaned_response_text, ordinal_label_starts)
        if claims is not None:
            reconstruction_status = build_reconstruction_check_output(cleaned_response_text, *claims)
            if reconstruction_status in {"ok", "ok_after_outer_quote_normalization"}:
                return claims, "ordinal_label_markers"

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

    bullet_o_starts = [
        match.start("segment")
        for match in BULLET_O_SEGMENT_RE.finditer(cleaned_response_text)
    ]
    if len(bullet_o_starts) >= 3:
        claims = split_claims_from_starts(cleaned_response_text, bullet_o_starts[:3])
        if claims is not None:
            reconstruction_status = build_reconstruction_check_output(cleaned_response_text, *claims)
            if reconstruction_status in {"ok", "ok_after_outer_quote_normalization"}:
                return claims, "bullet_o_markers"

    return None, "llm"


def apply_claim_segmentation(
    row: dict[str, str],
    claims: tuple[str, str, str],
    parse_strategy: str,
) -> None:
    row["llm_output_text"] = " ∞ ".join(claims)
    row["claim_1"] = claims[0]
    row["claim_2"] = claims[1]
    row["claim_3"] = claims[2]
    row["reconstruction_check_output"] = build_reconstruction_check_output(
        cleaned_response_text=row["cleaned_response_text"],
        claim_1=row["claim_1"],
        claim_2=row["claim_2"],
        claim_3=row["claim_3"],
    )
    row["parse_strategy"] = parse_strategy


def rows_requiring_llm(prepared_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in prepared_rows if row.get("parse_strategy", "llm") == "llm"]


def mark_rows_pending_llm(prepared_rows: list[dict[str, str]]) -> None:
    for row in prepared_rows:
        if row.get("parse_strategy", "llm") != "llm":
            continue
        if row.get("llm_error", "").strip():
            continue
        row["llm_error"] = "pending_llm_segmentation"


def apply_easy_parse_first_pass(prepared_rows: list[dict[str, str]]) -> Counter[str]:
    parse_counter: Counter[str] = Counter()
    for row in prepared_rows:
        claims, parse_strategy = try_easy_parse_claims(row["cleaned_response_text"])
        if claims is None:
            row["parse_strategy"] = "llm"
            parse_counter["llm"] += 1
            continue
        apply_claim_segmentation(row, claims, parse_strategy=parse_strategy)
        parse_counter[parse_strategy] += 1
    return parse_counter


def copy_segmentation_fields(target_row: dict[str, str], source_row: dict[str, str]) -> None:
    for field_name in [
        "llm_output_text",
        "claim_1",
        "claim_2",
        "claim_3",
        "reconstruction_check_output",
        "llm_error",
    ]:
        target_row[field_name] = source_row.get(field_name, "")
    target_row["parse_strategy"] = source_row.get("parse_strategy", target_row.get("parse_strategy", "llm"))


def is_manual_override_note(text: str) -> bool:
    return "OVERRIDE" in (text or "").upper()


def recover_claims_from_llm_output_text(llm_output_text: str) -> dict[str, str] | None:
    if not (llm_output_text or "").strip():
        return None
    try:
        parsed_rows = parse_batch_llm_output(llm_output_text, expected_rows=1)
    except ValueError:
        return None
    return parsed_rows[0]


def normalize_loaded_audit_row(
    normalized_row: dict[str, str],
    claim_column_names: list[str],
) -> dict[str, str]:
    llm_error = normalized_row.get("llm_error", "")
    extra_note = normalized_row.get("", "")
    if not llm_error.strip() and extra_note.strip():
        llm_error = extra_note.strip()

    claim_1 = normalized_row.get(claim_column_names[0], "")
    claim_2 = normalized_row.get(claim_column_names[1], "")
    claim_3 = normalized_row.get(claim_column_names[2], "")
    llm_output_text = normalized_row.get("llm_output_text", "")
    if (not claim_1.strip() or not claim_2.strip() or not claim_3.strip()) and llm_output_text.strip():
        recovered = recover_claims_from_llm_output_text(llm_output_text)
        if recovered is not None:
            claim_1 = recovered["claim_1"]
            claim_2 = recovered["claim_2"]
            claim_3 = recovered["claim_3"]

    reconstruction_check_output = normalized_row.get("reconstruction_check_output", "")
    cleaned_response_text = normalized_row.get("cleaned_response_text", "")
    if claim_1 or claim_2 or claim_3:
        recomputed = build_reconstruction_check_output(cleaned_response_text, claim_1, claim_2, claim_3)
        if not reconstruction_check_output.strip() or is_manual_override_note(llm_error):
            reconstruction_check_output = recomputed
    if is_manual_override_note(llm_error):
        reconstruction_check_output = "ok_manual_override"

    return {
        "submission_id": normalized_row.get("submission_id", ""),
        "submission_header": normalized_row.get("submission_header", ""),
        "cleaned_response_text": cleaned_response_text,
        "llm_output_text": llm_output_text,
        "claim_1": claim_1,
        "claim_2": claim_2,
        "claim_3": claim_3,
        "reconstruction_check_output": reconstruction_check_output,
        "llm_error": llm_error,
        "parse_strategy": normalized_row.get("parse_strategy", "llm"),
    }


def parse_batch_llm_output(extracted_output_text: str, expected_rows: int) -> list[dict[str, str]]:
    body = extract_fenced_markdown_body(extracted_output_text)
    structured_matches = list(STRUCTURED_ROW_BLOCK_RE.finditer(body))
    if structured_matches:
        if len(structured_matches) != expected_rows:
            raise ValueError(
                f"Expected {expected_rows} structured row block(s) from batch, received {len(structured_matches)}."
            )

        parsed_rows: list[dict[str, str]] = []
        for expected_index, match in enumerate(structured_matches, start=1):
            actual_index = int(match.group("index"))
            if actual_index != expected_index:
                raise ValueError(
                    f"Structured batch output row index mismatch: expected {expected_index}, received {actual_index}."
                )
            claim_1 = match.group("claim_1")
            claim_2 = match.group("claim_2")
            claim_3 = match.group("claim_3")
            parsed_rows.append(
                {
                    "llm_output_text": match.group(0).strip(),
                    "claim_1": claim_1,
                    "claim_2": claim_2,
                    "claim_3": claim_3,
                }
            )
        return parsed_rows

    lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not is_metadata_only_output_line(line)
    ]
    if len(lines) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} output row(s) from batch, received {len(lines)} line(s)."
        )

    parsed_rows: list[dict[str, str]] = []
    for row_number, line in enumerate(lines, start=1):
        parts = [part.strip() for part in line.split("∞")]
        if len(parts) != 3:
            raise ValueError(
                f"Batch output row {row_number} does not contain exactly 3 claim columns: {line}"
            )
        parsed_rows.append(
            {
                "llm_output_text": line,
                "claim_1": parts[0],
                "claim_2": parts[1],
                "claim_3": parts[2],
            }
        )

    return parsed_rows


def compute_text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_submission_blocks(batch_input_text: str) -> int:
    return len(SUBMISSION_TAG_RE.findall(batch_input_text))


def parse_rerun_batch_numbers(rerun_batch: list[int], rerun_batches: str) -> set[int]:
    batch_numbers: set[int] = set()
    for batch_number in rerun_batch:
        if batch_number <= 0:
            raise ValueError(f"--rerun-batch values must be positive integers, received: {batch_number}")
        batch_numbers.add(batch_number)

    if rerun_batches.strip():
        for raw_value in rerun_batches.split(","):
            value = raw_value.strip()
            if not value:
                continue
            batch_number = int(value)
            if batch_number <= 0:
                raise ValueError(
                    f"--rerun-batches values must be positive integers, received: {batch_number}"
                )
            batch_numbers.add(batch_number)

    return batch_numbers


def build_batch_specs(rows: list[dict[str, str]], batch_size: int) -> list[dict[str, Any]]:
    batch_specs: list[dict[str, Any]] = []
    for batch_number, start_index in enumerate(range(0, len(rows), batch_size), start=1):
        end_index = min(start_index + batch_size, len(rows))
        batch_specs.append(
            {
                "batch_number": batch_number,
                "start_index": start_index,
                "end_index": end_index,
                "start_row": start_index + 1,
                "end_row": end_index,
                "rows": rows[start_index:end_index],
                "stem": f"batch_{batch_number:04d}_rows_{start_index + 1}_{end_index}",
            }
        )
    return batch_specs


def build_batch_cache_paths(batch_cache_dir: Path, batch_spec: dict[str, Any]) -> dict[str, Path]:
    stem = str(batch_spec["stem"])
    return {
        "input": batch_cache_dir / f"{stem}_input.txt",
        "input_meta_json": batch_cache_dir / f"{stem}_input_meta.json",
        "output_json": batch_cache_dir / f"{stem}_output.json",
        "audit_csv": batch_cache_dir / f"{stem}_audit.csv",
        "status_json": batch_cache_dir / f"{stem}_status.json",
    }


def load_batch_status(status_path: Path) -> dict[str, Any] | None:
    if not status_path.exists():
        return None
    return json.loads(status_path.read_text(encoding="utf-8"))


def load_batch_input_metadata(input_meta_path: Path) -> dict[str, Any] | None:
    if not input_meta_path.exists():
        return None
    return json.loads(input_meta_path.read_text(encoding="utf-8"))


def write_batch_input_metadata(
    input_meta_path: Path,
    batch_spec: dict[str, Any],
    source_input_sha256: str,
) -> None:
    payload = {
        "batch_number": batch_spec["batch_number"],
        "start_row": batch_spec["start_row"],
        "end_row": batch_spec["end_row"],
        "submission_ids": [row.get("submission_id", "") for row in batch_spec["rows"]],
        "source_input_sha256": source_input_sha256,
    }
    input_meta_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_batch_status(
    status_path: Path,
    batch_spec: dict[str, Any],
    claim_column_names: list[str],
    status: str,
    elapsed_seconds: float,
    error_message: str = "",
    input_sha256: str = "",
    source_input_sha256: str = "",
) -> None:
    payload = {
        "batch_number": batch_spec["batch_number"],
        "start_row": batch_spec["start_row"],
        "end_row": batch_spec["end_row"],
        "submission_ids": [row.get("submission_id", "") for row in batch_spec["rows"]],
        "claim_columns": claim_column_names,
        "status": status,
        "elapsed_seconds": round(elapsed_seconds, 4),
        "error_message": error_message,
        "input_sha256": input_sha256,
        "source_input_sha256": source_input_sha256,
    }
    status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def has_successful_current_cache(
    batch_paths: dict[str, Path],
    status_payload: dict[str, Any] | None,
    current_input_sha256: str,
) -> bool:
    return (
        status_payload is not None
        and status_payload.get("status") == "success"
        and batch_paths["audit_csv"].exists()
        and status_payload.get("input_sha256", "") == current_input_sha256
    )


def synchronize_batch_input_files(
    batch_specs: list[dict[str, Any]],
    batch_cache_dir: Path,
    claim_column_names: list[str],
) -> dict[int, dict[str, Any]]:
    batch_input_states: dict[int, dict[str, Any]] = {}

    for batch_spec in batch_specs:
        batch_paths = build_batch_cache_paths(batch_cache_dir, batch_spec)
        canonical_input_text = build_batch_prompt_input(list(batch_spec["rows"]))
        canonical_input_sha256 = compute_text_sha256(canonical_input_text)
        input_metadata = load_batch_input_metadata(batch_paths["input_meta_json"])
        status_payload = load_batch_status(batch_paths["status_json"])
        change_reasons: list[str] = []

        if not batch_paths["input"].exists():
            batch_paths["input"].write_text(canonical_input_text, encoding="utf-8")
            change_reasons.append("created_from_source")
        elif input_metadata is None or input_metadata.get("source_input_sha256") != canonical_input_sha256:
            existing_input_text = batch_paths["input"].read_text(encoding="utf-8")
            if existing_input_text != canonical_input_text:
                batch_paths["input"].write_text(canonical_input_text, encoding="utf-8")
                change_reasons.append("refreshed_from_source")
            else:
                change_reasons.append("refreshed_source_metadata")

        current_input_text = batch_paths["input"].read_text(encoding="utf-8")
        current_input_sha256 = compute_text_sha256(current_input_text)
        write_batch_input_metadata(
            batch_paths["input_meta_json"],
            batch_spec=batch_spec,
            source_input_sha256=canonical_input_sha256,
        )

        if status_payload is not None and (
            not status_payload.get("input_sha256") or not status_payload.get("source_input_sha256")
        ):
            write_batch_status(
                batch_paths["status_json"],
                batch_spec=batch_spec,
                claim_column_names=claim_column_names,
                status=status_payload.get("status", "missing"),
                elapsed_seconds=float(status_payload.get("elapsed_seconds", 0.0) or 0.0),
                error_message=status_payload.get("error_message", ""),
                input_sha256=current_input_sha256,
                source_input_sha256=canonical_input_sha256,
            )
            status_payload = load_batch_status(batch_paths["status_json"])

        if (
            status_payload is not None
            and status_payload.get("input_sha256")
            and status_payload.get("input_sha256") != current_input_sha256
            and not any(reason.startswith("refreshed_from_source") or reason == "created_from_source" for reason in change_reasons)
        ):
            change_reasons.append("edited_batch_input")

        if change_reasons:
            print(
                f"[batch-input {batch_spec['batch_number']}/{len(batch_specs)}] "
                f"{', '.join(change_reasons)}: {batch_paths['input']}",
                flush=True,
            )

        batch_input_states[int(batch_spec["batch_number"])] = {
            "source_input_sha256": canonical_input_sha256,
            "current_input_sha256": current_input_sha256,
            "changed": any(reason != "refreshed_source_metadata" for reason in change_reasons),
            "change_reasons": list(change_reasons),
        }

    return batch_input_states


def summarize_batch_rows(batch_rows: list[dict[str, str]]) -> tuple[int, Counter[str]]:
    reconstruction_counter = Counter(
        row.get("reconstruction_check_output", "") or "<empty>" for row in batch_rows
    )
    llm_error_count = sum(
        1
        for row in batch_rows
        if (row.get("llm_error", "") or "").strip() and not is_manual_override_note(row.get("llm_error", ""))
    )
    return llm_error_count, reconstruction_counter


def invoke_runner_for_batch(
    runner_script_path: Path,
    runner_prompt_path: Path,
    batch_rows: list[dict[str, str]],
    batch_number: int,
    total_batches: int,
    temperature: float,
    top_p: float,
    runner_dry_run: bool,
) -> tuple[list[dict[str, str]], str]:
    file_stem = f"segmentation_batch_{batch_number:04d}"
    prompt_input_text = build_batch_prompt_input(batch_rows)

    with tempfile.TemporaryDirectory(prefix=f"segment_runner_{file_stem}_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        prompt_input_path = temp_dir / f"{file_stem}_input.txt"
        prompt_input_path.write_text(prompt_input_text, encoding="utf-8")

        command = [
            sys.executable,
            str(runner_script_path),
            "--prompt-instructions-file",
            str(runner_prompt_path),
            "--prompt-input-file",
            str(prompt_input_path),
            "--temperature",
            str(temperature),
            "--top-p",
            str(top_p),
            "--output-dir",
            str(temp_dir),
            "--output-file-stem",
            file_stem,
            "--output-format",
            "json",
        ]
        if runner_dry_run:
            command.append("--dry-run")

        print(
            f"[batch {batch_number}/{total_batches}] invoking LLM runner for {len(batch_rows)} cleaned submission(s)",
            flush=True,
        )
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            stderr_text = completed.stderr.strip() or completed.stdout.strip()
            return [], stderr_text or f"Runner failed for batch {batch_number}."

        if runner_dry_run:
            print(
                f"[batch {batch_number}/{total_batches}] dry-run enabled; skipping API call",
                flush=True,
            )
            return [
                {
                    "llm_output_text": "",
                    "claim_1": "",
                    "claim_2": "",
                    "claim_3": "",
                }
                for _ in batch_rows
            ], ""

        extracted_json_path = temp_dir / f"{file_stem}_output.json"
        if not extracted_json_path.exists():
            return [], f"Runner output file was not created: {extracted_json_path}"

        payload = json.loads(extracted_json_path.read_text(encoding="utf-8"))
        extracted_output_text = payload.get("extracted_output_text", "")
        if not isinstance(extracted_output_text, str):
            return [], (
                f"Runner output payload is missing string extracted_output_text for batch {batch_number}."
            )

        try:
            parsed_rows = parse_batch_llm_output(extracted_output_text, expected_rows=len(batch_rows))
        except ValueError as exc:
            return [], str(exc)

        print(
            f"[batch {batch_number}/{total_batches}] received {len(parsed_rows)} segmented row(s)",
            flush=True,
        )
        return parsed_rows, ""


def prepare_cleaned_rows(input_path: Path) -> list[dict[str, str]]:
    rows, response_text_key = load_csv_rows(input_path)
    prepared_rows: list[dict[str, str]] = []

    for row in rows:
        response_text = row.get(response_text_key, "")
        header_info, cleaned_text = extract_response_payload(response_text)
        submission_id = extract_submission_id(row, header_info)
        prepared_rows.append(
            {
                "submission_id": submission_id,
                "submission_header": header_info,
                "cleaned_response_text": cleaned_text,
                "llm_output_text": "",
                "claim_1": "",
                "claim_2": "",
                "claim_3": "",
                "reconstruction_check_output": "",
                "llm_error": "",
                "parse_strategy": "llm",
            }
        )

    return prepared_rows


def load_audit_rows(output_audit_path: Path, claim_column_names: list[str]) -> list[dict[str, str]]:
    if len(claim_column_names) != 3:
        raise ValueError(f"Expected exactly 3 claim column names, received: {claim_column_names}")

    with output_audit_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"Audit CSV has no header row: {output_audit_path}")

        required_fieldnames = {
            "submission_id",
            "submission_header",
            "cleaned_response_text",
            "llm_output_text",
            "reconstruction_check_output",
            "llm_error",
            *claim_column_names,
        }
        missing_fieldnames = required_fieldnames.difference(reader.fieldnames)
        if missing_fieldnames:
            missing_fields = ", ".join(sorted(missing_fieldnames))
            raise ValueError(
                f"Audit CSV is missing required field(s) [{missing_fields}]: {output_audit_path}"
            )

        rows: list[dict[str, str]] = []
        for raw_row in reader:
            normalized_row = {key.strip(): (value or "") for key, value in raw_row.items() if key is not None}
            if not any(value.strip() for value in normalized_row.values()):
                continue
            rows.append(normalize_loaded_audit_row(normalized_row, claim_column_names))

    return rows


def load_batch_audit_rows(batch_audit_path: Path, claim_column_names: list[str]) -> list[dict[str, str]]:
    return load_audit_rows(batch_audit_path, claim_column_names)


def count_physical_lines(input_path: Path) -> int:
    with input_path.open("r", encoding="utf-8-sig") as handle:
        return sum(1 for _ in handle)


def print_summary(
    rows: list[dict[str, str]],
    prefix: str,
    label: str,
    claim_column_names: list[str],
    elapsed_seconds: float | None = None,
) -> None:
    reconstruction_counter = Counter(
        row.get("reconstruction_check_output", "") or "<empty>" for row in rows
    )
    parse_strategy_counter = Counter(row.get("parse_strategy", "llm") or "<empty>" for row in rows)
    llm_error_count = sum(
        1
        for row in rows
        if (row.get("llm_error", "") or "").strip() and not is_manual_override_note(row.get("llm_error", ""))
    )
    manual_override_count = sum(1 for row in rows if is_manual_override_note(row.get("llm_error", "")))

    print(f"[{prefix}] {label}", flush=True)
    print(f"[{prefix}] total_rows={len(rows)}", flush=True)
    print(f"[{prefix}] llm_error_rows={llm_error_count}", flush=True)
    print(f"[{prefix}] manual_override_rows={manual_override_count}", flush=True)
    print(f"[{prefix}] claim_columns={', '.join(claim_column_names)}", flush=True)
    if elapsed_seconds is not None:
        print(f"[{prefix}] elapsed_seconds={elapsed_seconds:.2f}", flush=True)

    for status, count in sorted(reconstruction_counter.items()):
        print(f"[{prefix}] reconstruction[{status}]={count}", flush=True)
    for parse_strategy, count in sorted(parse_strategy_counter.items()):
        print(f"[{prefix}] parse_strategy[{parse_strategy}]={count}", flush=True)


def print_cached_batch_summary(
    batch_spec: dict[str, Any],
    batch_rows: list[dict[str, str]],
    claim_column_names: list[str],
    status_payload: dict[str, Any] | None,
    total_batches: int,
) -> None:
    elapsed_seconds = None
    if status_payload is not None:
        raw_elapsed = status_payload.get("elapsed_seconds")
        if isinstance(raw_elapsed, int | float):
            elapsed_seconds = float(raw_elapsed)

    print(
        f"[batch {batch_spec['batch_number']}/{total_batches}] using cached successful batch artifacts",
        flush=True,
    )
    print_summary(
        batch_rows,
        prefix=f"batch-summary {batch_spec['batch_number']}/{total_batches}",
        label=f"rows {batch_spec['start_row']}-{batch_spec['end_row']}",
        claim_column_names=claim_column_names,
        elapsed_seconds=elapsed_seconds,
    )


def should_run_batch(
    batch_spec: dict[str, Any],
    batch_paths: dict[str, Path],
    batch_input_state: dict[str, Any],
    selected_batches: set[int],
    rerun_failed_batches: bool,
    rebuild_from_batch_cache: bool,
) -> bool:
    if rebuild_from_batch_cache:
        return False

    batch_status = load_batch_status(batch_paths["status_json"])
    batch_number = int(batch_spec["batch_number"])
    status_value = batch_status.get("status") if batch_status else ""
    has_success_cache = has_successful_current_cache(
        batch_paths,
        batch_status,
        current_input_sha256=batch_input_state["current_input_sha256"],
    )

    if batch_input_state["changed"]:
        return True

    if selected_batches:
        return batch_number in selected_batches

    if rerun_failed_batches:
        return status_value == "failed"

    return not has_success_cache


def run_one_batch(
    batch_spec: dict[str, Any],
    batch_paths: dict[str, Path],
    total_batches: int,
    claim_column_names: list[str],
    runner_script_path: Path,
    runner_prompt_path: Path,
    temperature: float,
    top_p: float,
    runner_dry_run: bool,
) -> tuple[list[dict[str, str]], str, float, str]:
    batch_rows = list(batch_spec["rows"])
    batch_start_time = time.perf_counter()
    batch_input_text = batch_paths["input"].read_text(encoding="utf-8")
    batch_input_sha256 = compute_text_sha256(batch_input_text)
    submission_block_count = count_submission_blocks(batch_input_text)
    if submission_block_count != len(batch_rows):
        elapsed_seconds = time.perf_counter() - batch_start_time
        return (
            [],
            (
                f"Batch input contains {submission_block_count} submission block(s); expected {len(batch_rows)}. "
                f"Edit {batch_paths['input']} so it preserves one <submission ...> block per source row."
            ),
            elapsed_seconds,
            batch_input_sha256,
        )

    command = [
        sys.executable,
        str(runner_script_path),
        "--prompt-instructions-file",
        str(runner_prompt_path),
        "--prompt-input-file",
        str(batch_paths["input"]),
        "--temperature",
        str(temperature),
        "--top-p",
        str(top_p),
        "--output-dir",
        str(batch_paths["input"].parent),
        "--output-file-stem",
        str(batch_spec["stem"]),
        "--output-format",
        "json",
    ]
    if runner_dry_run:
        command.append("--dry-run")

    print(
        f"[batch {batch_spec['batch_number']}/{total_batches}] invoking LLM runner for {len(batch_rows)} cleaned submission(s)",
        flush=True,
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    elapsed_seconds = time.perf_counter() - batch_start_time
    if completed.returncode != 0:
        stderr_text = completed.stderr.strip() or completed.stdout.strip()
        return [], stderr_text or f"Runner failed for batch {batch_spec['batch_number']}.", elapsed_seconds, batch_input_sha256

    if runner_dry_run:
        print(
            f"[batch {batch_spec['batch_number']}/{total_batches}] dry-run enabled; skipping API call",
            flush=True,
        )
        return [
            {
                "submission_id": row.get("submission_id", ""),
                "submission_header": row.get("submission_header", ""),
                "cleaned_response_text": row.get("cleaned_response_text", ""),
                "llm_output_text": "",
                "claim_1": "",
                "claim_2": "",
                "claim_3": "",
                "reconstruction_check_output": "",
                "llm_error": "",
                "parse_strategy": "llm",
            }
            for row in batch_rows
        ], "", elapsed_seconds, batch_input_sha256

    if not batch_paths["output_json"].exists():
        return [], f"Runner output file was not created: {batch_paths['output_json']}", elapsed_seconds, batch_input_sha256

    payload = json.loads(batch_paths["output_json"].read_text(encoding="utf-8"))
    extracted_output_text = payload.get("extracted_output_text", "")
    if not isinstance(extracted_output_text, str):
        return [], (
            f"Runner output payload is missing string extracted_output_text for batch {batch_spec['batch_number']}."
        ), elapsed_seconds, batch_input_sha256

    try:
        parsed_rows = parse_batch_llm_output(extracted_output_text, expected_rows=len(batch_rows))
    except ValueError as exc:
        return [], str(exc), elapsed_seconds, batch_input_sha256

    for row, parsed in zip(batch_rows, parsed_rows, strict=True):
        row["llm_output_text"] = parsed["llm_output_text"]
        row["claim_1"] = parsed["claim_1"]
        row["claim_2"] = parsed["claim_2"]
        row["claim_3"] = parsed["claim_3"]
        row["reconstruction_check_output"] = build_reconstruction_check_output(
            cleaned_response_text=row["cleaned_response_text"],
            claim_1=row["claim_1"],
            claim_2=row["claim_2"],
            claim_3=row["claim_3"],
        )
        row["parse_strategy"] = "llm"

    print(
        f"[batch {batch_spec['batch_number']}/{total_batches}] received {len(batch_rows)} segmented row(s)",
        flush=True,
    )
    write_segmentation_rows(batch_paths["audit_csv"], batch_rows, claim_column_names)
    return batch_rows, "", elapsed_seconds, batch_input_sha256


def merge_batch_audit_rows(
    batch_specs: list[dict[str, Any]],
    batch_cache_dir: Path,
    claim_column_names: list[str],
) -> list[dict[str, str]]:
    merged_rows: list[dict[str, str]] = []
    for batch_spec in batch_specs:
        batch_paths = build_batch_cache_paths(batch_cache_dir, batch_spec)
        status_payload = load_batch_status(batch_paths["status_json"])
        if status_payload is None or status_payload.get("status") != "success":
            raise RuntimeError(
                f"Batch {batch_spec['batch_number']} is not available as a successful cache artifact."
            )
        if not batch_paths["audit_csv"].exists():
            raise RuntimeError(
                f"Batch {batch_spec['batch_number']} is missing its audit CSV: {batch_paths['audit_csv']}"
            )
        merged_rows.extend(load_batch_audit_rows(batch_paths["audit_csv"], claim_column_names))
    return merged_rows


def collect_unavailable_batches(
    batch_specs: list[dict[str, Any]],
    batch_cache_dir: Path,
    batch_input_states: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    unavailable_batches: list[dict[str, Any]] = []
    for batch_spec in batch_specs:
        batch_paths = build_batch_cache_paths(batch_cache_dir, batch_spec)
        status_payload = load_batch_status(batch_paths["status_json"])
        batch_input_state = batch_input_states[int(batch_spec["batch_number"])]
        status_value = status_payload.get("status") if status_payload else "missing"
        error_message = status_payload.get("error_message", "") if status_payload else ""
        has_audit_csv = batch_paths["audit_csv"].exists()
        if has_successful_current_cache(
            batch_paths,
            status_payload,
            current_input_sha256=batch_input_state["current_input_sha256"],
        ):
            continue
        unavailable_batches.append(
            {
                "batch_number": batch_spec["batch_number"],
                "start_row": batch_spec["start_row"],
                "end_row": batch_spec["end_row"],
                "status": status_value,
                "has_audit_csv": has_audit_csv,
                "error_message": error_message,
                "input_changed": batch_input_state["changed"],
                "change_reasons": batch_input_state["change_reasons"],
            }
        )
    return unavailable_batches


def format_unavailable_batches_error(unavailable_batches: list[dict[str, Any]]) -> str:
    batch_numbers = ",".join(str(item["batch_number"]) for item in unavailable_batches)
    summary_lines = [
        "One or more batches are not available as successful cache artifacts.",
        f"Rerun suggestion: just RERUN_BATCHES=\"{batch_numbers}\" l0-post-hoc-componentisation <ASSIGNMENT>",
        "Unavailable batches:",
    ]
    for item in unavailable_batches:
        line = (
            f"- batch {item['batch_number']} rows {item['start_row']}-{item['end_row']} "
            f"status={item['status']} audit_csv={'present' if item['has_audit_csv'] else 'missing'}"
        )
        if item["input_changed"]:
            line += f" input_changed={'|'.join(item['change_reasons'])}"
        if item["error_message"]:
            line += f" error={item['error_message']}"
        summary_lines.append(line)
    return "\n".join(summary_lines)


def seed_batch_cache_from_whole_audit(
    whole_audit_rows: list[dict[str, str]],
    batch_specs: list[dict[str, Any]],
    batch_cache_dir: Path,
    claim_column_names: list[str],
) -> None:
    if len(whole_audit_rows) != sum(len(batch_spec["rows"]) for batch_spec in batch_specs):
        raise ValueError(
            "Whole-audit cache row count does not match the current batch plan; cannot seed batch cache."
        )

    cursor = 0
    for batch_spec in batch_specs:
        batch_length = len(batch_spec["rows"])
        batch_rows = whole_audit_rows[cursor:cursor + batch_length]
        cursor += batch_length
        batch_paths = build_batch_cache_paths(batch_cache_dir, batch_spec)
        prompt_input_text = build_batch_prompt_input(list(batch_spec["rows"]))
        batch_paths["input"].write_text(prompt_input_text, encoding="utf-8")
        source_input_sha256 = compute_text_sha256(prompt_input_text)
        write_batch_input_metadata(
            batch_paths["input_meta_json"],
            batch_spec=batch_spec,
            source_input_sha256=source_input_sha256,
        )
        write_segmentation_rows(batch_paths["audit_csv"], batch_rows, claim_column_names)
        write_batch_status(
            batch_paths["status_json"],
            batch_spec=batch_spec,
            claim_column_names=claim_column_names,
            status="success",
            elapsed_seconds=0.0,
            error_message="Seeded from whole-audit cache.",
            input_sha256=source_input_sha256,
            source_input_sha256=source_input_sha256,
        )


def execute_batch_cache_workflow(
    prepared_rows: list[dict[str, str]],
    batch_cache_dir: Path,
    claim_column_names: list[str],
    runner_script_path: Path,
    runner_prompt_path: Path,
    temperature: float,
    top_p: float,
    runner_dry_run: bool,
    batch_size: int,
    selected_batches: set[int],
    rerun_failed_batches: bool,
    rebuild_from_batch_cache: bool,
) -> list[dict[str, str]]:
    if batch_size <= 0:
        raise ValueError(f"--batch-size must be a positive integer, received: {batch_size}")

    llm_candidate_rows = rows_requiring_llm(prepared_rows)
    if not llm_candidate_rows:
        print("[progress] deterministic structural parsing covered all rows; no LLM batches required", flush=True)
        return prepared_rows

    batch_cache_dir.mkdir(parents=True, exist_ok=True)
    batch_specs = build_batch_specs(llm_candidate_rows, batch_size)
    total_batches = len(batch_specs)
    print(
        f"[progress] batch cache directory: {batch_cache_dir}",
        flush=True,
    )
    print(
        f"[progress] planned {total_batches} batch(es) from {len(llm_candidate_rows)} LLM submission(s)",
        flush=True,
    )

    batch_input_states = synchronize_batch_input_files(
        batch_specs=batch_specs,
        batch_cache_dir=batch_cache_dir,
        claim_column_names=claim_column_names,
    )

    for batch_spec in batch_specs:
        batch_paths = build_batch_cache_paths(batch_cache_dir, batch_spec)
        batch_number = int(batch_spec["batch_number"])
        batch_input_state = batch_input_states[batch_number]
        if should_run_batch(
            batch_spec=batch_spec,
            batch_paths=batch_paths,
            batch_input_state=batch_input_state,
            selected_batches=selected_batches,
            rerun_failed_batches=rerun_failed_batches,
            rebuild_from_batch_cache=rebuild_from_batch_cache,
        ):
            batch_rows, batch_error, elapsed_seconds, batch_input_sha256 = run_one_batch(
                batch_spec=batch_spec,
                batch_paths=batch_paths,
                total_batches=total_batches,
                claim_column_names=claim_column_names,
                runner_script_path=runner_script_path,
                runner_prompt_path=runner_prompt_path,
                temperature=temperature,
                top_p=top_p,
                runner_dry_run=runner_dry_run,
            )
            if batch_error:
                write_batch_status(
                    batch_paths["status_json"],
                    batch_spec=batch_spec,
                    claim_column_names=claim_column_names,
                    status="failed",
                    elapsed_seconds=elapsed_seconds,
                    error_message=batch_error,
                    input_sha256=batch_input_sha256,
                    source_input_sha256=batch_input_state["source_input_sha256"],
                )
                for row in batch_spec["rows"]:
                    row["llm_error"] = batch_error
                print(
                    f"[batch {batch_number}/{total_batches}] failed: {batch_error}",
                    flush=True,
                )
                print_summary(
                    list(batch_spec["rows"]),
                    prefix=f"batch-summary {batch_number}/{total_batches}",
                    label=f"rows {batch_spec['start_row']}-{batch_spec['end_row']}",
                    claim_column_names=claim_column_names,
                    elapsed_seconds=elapsed_seconds,
                )
                continue

            write_segmentation_rows(batch_paths["audit_csv"], batch_rows, claim_column_names)
            write_batch_status(
                batch_paths["status_json"],
                batch_spec=batch_spec,
                claim_column_names=claim_column_names,
                status="success",
                elapsed_seconds=elapsed_seconds,
                input_sha256=batch_input_sha256,
                source_input_sha256=batch_input_state["source_input_sha256"],
            )
            print_summary(
                batch_rows,
                prefix=f"batch-summary {batch_number}/{total_batches}",
                label=f"rows {batch_spec['start_row']}-{batch_spec['end_row']}",
                claim_column_names=claim_column_names,
                elapsed_seconds=elapsed_seconds,
            )
            continue

        status_payload = load_batch_status(batch_paths["status_json"])
        if not has_successful_current_cache(
            batch_paths,
            status_payload,
            current_input_sha256=batch_input_state["current_input_sha256"],
        ):
            print(
                f"[batch {batch_number}/{total_batches}] no successful cache available for rows {batch_spec['start_row']}-{batch_spec['end_row']}",
                flush=True,
            )
            continue
        batch_rows = load_batch_audit_rows(batch_paths["audit_csv"], claim_column_names)
        print_cached_batch_summary(
            batch_spec=batch_spec,
            batch_rows=batch_rows,
            claim_column_names=claim_column_names,
            status_payload=status_payload,
            total_batches=total_batches,
        )

    unavailable_batches = collect_unavailable_batches(batch_specs, batch_cache_dir, batch_input_states)
    if unavailable_batches:
        raise RuntimeError(format_unavailable_batches_error(unavailable_batches))

    merged_llm_rows = merge_batch_audit_rows(batch_specs, batch_cache_dir, claim_column_names)
    for target_row, merged_row in zip(llm_candidate_rows, merged_llm_rows, strict=True):
        copy_segmentation_fields(target_row, merged_row)
        target_row["parse_strategy"] = "llm"

    return prepared_rows


def apply_llm_segmentation(
    prepared_rows: list[dict[str, str]],
    runner_script_path: Path,
    runner_prompt_path: Path,
    temperature: float,
    top_p: float,
    runner_dry_run: bool,
    batch_size: int,
    claim_column_names: list[str],
) -> list[dict[str, str]]:
    if batch_size <= 0:
        raise ValueError(f"--batch-size must be a positive integer, received: {batch_size}")

    total_rows = len(prepared_rows)
    total_batches = math.ceil(total_rows / batch_size) if total_rows else 0

    print(
        f"[progress] submitting {total_rows} cleaned submission(s) in {total_batches} batch(es) of up to {batch_size}",
        flush=True,
    )

    for batch_index, start_index in enumerate(range(0, total_rows, batch_size), start=1):
        end_index = min(start_index + batch_size, total_rows)
        batch_rows = prepared_rows[start_index:end_index]
        batch_start_time = time.perf_counter()
        print(
            f"[progress] processing rows {start_index + 1}-{end_index} of {total_rows}",
            flush=True,
        )
        parsed_rows, batch_error = invoke_runner_for_batch(
            runner_script_path=runner_script_path,
            runner_prompt_path=runner_prompt_path,
            batch_rows=batch_rows,
            batch_number=batch_index,
            total_batches=total_batches,
            temperature=temperature,
            top_p=top_p,
            runner_dry_run=runner_dry_run,
        )
        if batch_error:
            for row in batch_rows:
                row["llm_error"] = batch_error
            print(
                f"[batch {batch_index}/{total_batches}] failed: {batch_error}",
                flush=True,
            )
            print_summary(
                batch_rows,
                prefix=f"batch-summary {batch_index}/{total_batches}",
                label=f"rows {start_index + 1}-{end_index}",
                claim_column_names=claim_column_names,
                elapsed_seconds=time.perf_counter() - batch_start_time,
            )
            continue

        for row, parsed in zip(batch_rows, parsed_rows, strict=True):
            row["llm_output_text"] = parsed["llm_output_text"]
            row["claim_1"] = parsed["claim_1"]
            row["claim_2"] = parsed["claim_2"]
            row["claim_3"] = parsed["claim_3"]
            row["reconstruction_check_output"] = build_reconstruction_check_output(
                cleaned_response_text=row["cleaned_response_text"],
                claim_1=row["claim_1"],
                claim_2=row["claim_2"],
                claim_3=row["claim_3"],
            )

        print_summary(
            batch_rows,
            prefix=f"batch-summary {batch_index}/{total_batches}",
            label=f"rows {start_index + 1}-{end_index}",
            claim_column_names=claim_column_names,
            elapsed_seconds=time.perf_counter() - batch_start_time,
        )

    return prepared_rows


def write_segmentation_rows(
    output_path: Path,
    rows: list[dict[str, str]],
    claim_column_names: list[str],
) -> None:
    if len(claim_column_names) != 3:
        raise ValueError(f"Expected exactly 3 claim column names, received: {claim_column_names}")

    fieldnames = [
        "submission_id",
        "submission_header",
        "cleaned_response_text",
        "parse_strategy",
        "llm_output_text",
        *claim_column_names,
        "reconstruction_check_output",
        "llm_error",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "submission_id": row.get("submission_id", ""),
                    "submission_header": row.get("submission_header", ""),
                    "cleaned_response_text": row.get("cleaned_response_text", ""),
                    "parse_strategy": row.get("parse_strategy", "llm"),
                    "llm_output_text": row.get("llm_output_text", ""),
                    claim_column_names[0]: row.get("claim_1", ""),
                    claim_column_names[1]: row.get("claim_2", ""),
                    claim_column_names[2]: row.get("claim_3", ""),
                    "reconstruction_check_output": row.get("reconstruction_check_output", ""),
                    "llm_error": row.get("llm_error", ""),
                }
            )


def write_claim_expanded_rows(
    output_path: Path,
    rows: list[dict[str, str]],
    claim_column_names: list[str],
) -> None:
    if len(claim_column_names) != 3:
        raise ValueError(f"Expected exactly 3 claim column names, received: {claim_column_names}")

    claim_keys = ["claim_1", "claim_2", "claim_3"]
    fieldnames = ["submission_id", "component_id", "response_text"]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            submission_id = row.get("submission_id", "")
            submission_header = row.get("submission_header", "")
            for claim_key, claim_column_name in zip(claim_keys, claim_column_names, strict=True):
                writer.writerow(
                    {
                        "submission_id": submission_id,
                        "component_id": build_component_id_from_claim_column(claim_column_name),
                        "response_text": wrap_claim_response_text(
                            submission_header=submission_header,
                            claim_text=row.get(claim_key, ""),
                        ),
                    }
                )


def print_run_incomplete_summary(error_message: str) -> None:
    print("[summary] run incomplete", flush=True)
    print(
        "[summary] final outputs were not written because one or more required batch artifacts are unavailable.",
        flush=True,
    )
    for line in error_message.splitlines():
        print(f"[summary] {line}", flush=True)


def main() -> int:
    args = parse_args()

    input_path = args.input_path.resolve()
    output_path = args.output_path.resolve()
    output_audit_path = args.output_audit_path.resolve()
    batch_cache_dir = args.batch_cache_dir.resolve()
    runner_prompt_path = args.runner_prompt_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not runner_prompt_path.exists():
        raise FileNotFoundError(f"Runner prompt file not found: {runner_prompt_path}")

    claim_column_names = resolve_claim_column_names(output_path)
    runner_script_path = resolve_runner_script_path()
    selected_batches = parse_rerun_batch_numbers(args.rerun_batch, args.rerun_batches)
    print(f"[progress] resolved claim output columns: {', '.join(claim_column_names)}", flush=True)

    if args.rebuild_from_batch_cache and selected_batches:
        raise ValueError("--rebuild-from-batch-cache cannot be combined with --rerun-batch/--rerun-batches")
    if args.deterministic_only and (
        selected_batches or args.rerun_failed_batches or args.rebuild_from_batch_cache
    ):
        raise ValueError(
            "--deterministic-only cannot be combined with rerun or batch-cache rebuild options"
        )

    print(f"[progress] loading source CSV: {input_path}", flush=True)
    physical_line_count = count_physical_lines(input_path)
    raw_rows, _ = load_csv_rows(input_path)
    prepared_rows = prepare_cleaned_rows(input_path)
    skipped_empty_rows = max(0, len(raw_rows) - len(prepared_rows))
    parse_counter = apply_easy_parse_first_pass(prepared_rows)
    llm_candidate_rows = rows_requiring_llm(prepared_rows)
    print(
        f"[progress] source file has {physical_line_count} physical line(s); prepared {len(prepared_rows)} non-empty submission row(s)",
        flush=True,
    )
    print(f"[progress] skipped_empty_rows={skipped_empty_rows}", flush=True)
    print(
        f"[progress] deterministic structural parsing handled {len(prepared_rows) - len(llm_candidate_rows)} row(s); "
        f"{len(llm_candidate_rows)} row(s) remain for LLM segmentation",
        flush=True,
    )
    for parse_strategy, count in sorted(parse_counter.items()):
        print(f"[progress] parse_strategy[{parse_strategy}]={count}", flush=True)

    if args.deterministic_only:
        mark_rows_pending_llm(prepared_rows)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_audit_path.parent.mkdir(parents=True, exist_ok=True)
        print("[progress] deterministic-only mode enabled; skipping LLM batching", flush=True)
        print(f"[progress] writing output CSV: {output_path}", flush=True)
        write_claim_expanded_rows(output_path, prepared_rows, claim_column_names)
        print(f"[progress] writing audit CSV: {output_audit_path}", flush=True)
        write_segmentation_rows(output_audit_path, prepared_rows, claim_column_names)
        print_summary(
            prepared_rows,
            prefix="summary",
            label="deterministic-only run complete",
            claim_column_names=claim_column_names,
        )
        print("[progress] deterministic-only segmentation run complete", flush=True)
        return 0

    batch_specs = build_batch_specs(llm_candidate_rows, args.batch_size)
    has_existing_batch_cache = batch_cache_dir.exists() and any(batch_cache_dir.iterdir())
    if not has_existing_batch_cache and output_audit_path.exists() and not selected_batches and not args.rerun_failed_batches and not args.rebuild_from_batch_cache:
        print(f"[progress] seeding batch cache from existing whole-audit CSV: {output_audit_path}", flush=True)
        whole_audit_rows = load_audit_rows(output_audit_path, claim_column_names)
        if len(whole_audit_rows) != len(prepared_rows):
            raise ValueError(
                "Whole-audit cache row count does not match the current prepared row count; cannot seed batch cache."
            )
        whole_audit_llm_rows = [
            audit_row
            for audit_row, prepared_row in zip(whole_audit_rows, prepared_rows, strict=True)
            if prepared_row.get("parse_strategy", "llm") == "llm"
        ]
        batch_cache_dir.mkdir(parents=True, exist_ok=True)
        seed_batch_cache_from_whole_audit(
            whole_audit_rows=whole_audit_llm_rows,
            batch_specs=batch_specs,
            batch_cache_dir=batch_cache_dir,
            claim_column_names=claim_column_names,
        )

    try:
        segmentation_rows = execute_batch_cache_workflow(
            prepared_rows=prepared_rows,
            batch_cache_dir=batch_cache_dir,
            claim_column_names=claim_column_names,
            runner_script_path=runner_script_path,
            runner_prompt_path=runner_prompt_path,
            temperature=args.temperature,
            top_p=args.top_p,
            runner_dry_run=args.runner_dry_run,
            batch_size=args.batch_size,
            selected_batches=selected_batches,
            rerun_failed_batches=args.rerun_failed_batches,
            rebuild_from_batch_cache=args.rebuild_from_batch_cache,
        )
    except RuntimeError as exc:
        print_run_incomplete_summary(str(exc))
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_audit_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[progress] writing output CSV: {output_path}", flush=True)
    write_claim_expanded_rows(output_path, segmentation_rows, claim_column_names)
    print(f"[progress] writing audit CSV: {output_audit_path}", flush=True)
    write_segmentation_rows(output_audit_path, segmentation_rows, claim_column_names)
    print_summary(
        segmentation_rows,
        prefix="summary",
        label="run complete",
        claim_column_names=claim_column_names,
    )
    print("[progress] segmentation run complete", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())