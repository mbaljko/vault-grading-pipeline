#!/usr/bin/env python3

"""Estimate how many submission rows are easy to segment structurally.

This companion script reads the same pre-componentised canonical-population CSV used by
``post-hoc-componentisation.py`` and classifies each ``response_text`` row using the
same structural cues described in the segmentation prompt.

The goal is not to invoke the LLM. It applies the same deterministic parsing heuristics
as the production script and tallies rows that can be segmented safely because their
structure clearly exposes three claim boundaries, for example via:

1. Explicit ``Claim 1`` / ``Claim 2`` / ``Claim 3`` markers.
2. Numbered ``1.`` / ``2.`` / ``3.`` style markers.
3. Three or more occurrences of ``In this system`` or ``In thissystem``.

The script prints a concise summary to stdout. It can optionally write a row-level CSV
audit describing which heuristic matched each row.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from post_hoc_componentisation_common import (
    extract_response_payload,
    extract_submission_id,
    load_csv_rows,
    try_easy_parse_claims,
    build_reconstruction_check_output,
)


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

def write_row_audit(output_path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "submission_id",
        "parse_strategy",
        "easily_parsable",
        "reconstruction_check_output",
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
    parse_counter: Counter[str] = Counter()
    easy_count = 0
    skipped_empty_rows = 0

    for row in raw_rows:
        response_text = row.get(response_text_key, "")
        header_info, cleaned_text = extract_response_payload(response_text)
        if not cleaned_text.strip():
            skipped_empty_rows += 1
            continue
        submission_id = extract_submission_id(row, header_info)
        claims, parse_strategy = try_easy_parse_claims(cleaned_text)
        reconstruction_check_output = ""
        if claims is not None:
            reconstruction_check_output = build_reconstruction_check_output(cleaned_text, *claims)
        parse_counter[parse_strategy] += 1
        is_easy = claims is not None
        if is_easy:
            easy_count += 1
        audit_rows.append(
            {
                "submission_id": submission_id,
                "parse_strategy": parse_strategy,
                "easily_parsable": "true" if is_easy else "false",
                "reconstruction_check_output": reconstruction_check_output,
                "cleaned_response_text": cleaned_text,
            }
        )

    total_rows = len(audit_rows)
    easy_share = (easy_count / total_rows * 100.0) if total_rows else 0.0

    print(f"[summary] input_path={input_path}")
    print(f"[summary] total_rows={total_rows}")
    print(f"[summary] skipped_empty_rows={skipped_empty_rows}")
    print(f"[summary] easily_parsable_rows={easy_count}")
    print(f"[summary] easily_parsable_pct={easy_share:.2f}")
    for parse_strategy, count in sorted(parse_counter.items()):
        print(f"[summary] parse_strategy[{parse_strategy}]={count}")

    if args.output_path is not None:
        output_path = args.output_path.resolve()
        write_row_audit(output_path, audit_rows)
        print(f"[summary] audit_csv={output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())