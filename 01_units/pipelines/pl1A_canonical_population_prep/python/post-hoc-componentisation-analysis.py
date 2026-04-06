#!/usr/bin/env python3

"""Estimate how many submission rows are easy to segment structurally.

This companion script reads the same pre-componentised canonical-population CSV used by
``post-hoc-componentisation.py`` and classifies each ``response_text`` row using the
same structural cues described in the segmentation prompt.

The goal is not to segment text. It only tallies rows that appear easy to parse because
their structure clearly exposes three claim boundaries, for example via:

1. Explicit ``Claim 1`` / ``Claim 2`` / ``Claim 3`` markers.
2. Numbered ``1.`` / ``2.`` / ``3.`` style markers.
3. Three or more occurrences of ``In this system`` or ``In thissystem``.

The script prints a concise summary to stdout. It can optionally write a row-level CSV
audit describing which heuristic matched each row.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path


RESPONSE_TEXT_COLUMN = "response_text"
SUBMISSION_ID_COLUMN = "submission_id"
LEADING_TICKED_HEADER_RE = re.compile(r"\A`+\s*(?=\+\+\+)", re.DOTALL)
HEADER_BLOCK_RE = re.compile(r"\A\+\+\+(?P<header>[^\n]+)\n\+\+\+\n?", re.DOTALL)
FOOTER_BLOCK_RE = re.compile(r"\n?\+\+\+\s*\Z", re.DOTALL)
CLAIM_LABEL_RE = re.compile(
    r"(?im)(?:^|[\n\r])\s*claim(?:\s+statement)?\s*([123])\s*[:.)-]?"
)
NUMBERED_LABEL_RE = re.compile(r"(?im)(?:^|[\n\r])\s*([123])\s*[.)]\s+")
IN_THIS_SYSTEM_RE = re.compile(r"in\s+this\s*system", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read the post-hoc componentisation input CSV and tally rows that are easy "
            "to segment because of their visible structure."
        )
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        required=True,
        help="Source CSV file containing response_text values.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional row-level CSV audit output.",
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
    return header_info, stripped_text


def extract_submission_id(row: dict[str, str], header_info: str) -> str:
    submission_id = row.get(SUBMISSION_ID_COLUMN, "").strip()
    if submission_id:
        return submission_id

    prefix = "submission_id="
    if header_info.startswith(prefix):
        return header_info[len(prefix):].strip()
    return ""


def has_ordered_triplet(matches: list[int]) -> bool:
    ordered_unique: list[int] = []
    for value in matches:
        if not ordered_unique or ordered_unique[-1] != value:
            ordered_unique.append(value)
    return ordered_unique[:3] == [1, 2, 3]


def classify_structure(cleaned_response_text: str) -> tuple[bool, str, dict[str, int]]:
    claim_matches = [int(match.group(1)) for match in CLAIM_LABEL_RE.finditer(cleaned_response_text)]
    numbered_matches = [int(match.group(1)) for match in NUMBERED_LABEL_RE.finditer(cleaned_response_text)]
    in_this_system_count = len(IN_THIS_SYSTEM_RE.findall(cleaned_response_text))

    metrics = {
        "claim_label_count": len(claim_matches),
        "numbered_label_count": len(numbered_matches),
        "in_this_system_count": in_this_system_count,
    }

    if has_ordered_triplet(claim_matches):
        return True, "claim_markers", metrics
    if has_ordered_triplet(numbered_matches):
        return True, "numbered_markers", metrics
    if in_this_system_count >= 3:
        return True, "in_this_system_triplet", metrics
    return False, "no_clear_triplet_structure", metrics


def write_row_audit(output_path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "submission_id",
        "structure_classification",
        "easily_parsable",
        "claim_label_count",
        "numbered_label_count",
        "in_this_system_count",
        "cleaned_response_text",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    input_path = args.input_path.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    raw_rows, response_text_key = load_csv_rows(input_path)
    audit_rows: list[dict[str, str]] = []
    classification_counter: Counter[str] = Counter()
    easy_count = 0

    for row in raw_rows:
        response_text = row.get(response_text_key, "")
        header_info, cleaned_text = extract_response_payload(response_text)
        submission_id = extract_submission_id(row, header_info)
        is_easy, classification, metrics = classify_structure(cleaned_text)
        classification_counter[classification] += 1
        if is_easy:
            easy_count += 1
        audit_rows.append(
            {
                "submission_id": submission_id,
                "structure_classification": classification,
                "easily_parsable": "true" if is_easy else "false",
                "claim_label_count": str(metrics["claim_label_count"]),
                "numbered_label_count": str(metrics["numbered_label_count"]),
                "in_this_system_count": str(metrics["in_this_system_count"]),
                "cleaned_response_text": cleaned_text,
            }
        )

    total_rows = len(audit_rows)
    easy_share = (easy_count / total_rows * 100.0) if total_rows else 0.0

    print(f"[summary] input_path={input_path}")
    print(f"[summary] total_rows={total_rows}")
    print(f"[summary] easily_parsable_rows={easy_count}")
    print(f"[summary] easily_parsable_pct={easy_share:.2f}")
    for classification, count in sorted(classification_counter.items()):
        print(f"[summary] classification[{classification}]={count}")

    if args.output_path is not None:
        output_path = args.output_path.resolve()
        write_row_audit(output_path, audit_rows)
        print(f"[summary] audit_csv={output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())