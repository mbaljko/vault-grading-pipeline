#!/usr/bin/env python3
"""Prepare a scored-worksheet CSV for manual feedback entry.

Copies a Layer 4 wide-stitched CSV to a staging location and appends two
columns at the end:
  - "."               — spacer / separator column
  - "Feedback comments" — pre-populated with a per-row summary string of the
                          form:
                          "Overall result for {prefix}: {grade} ( {score} / {max_score}). {n} dimension(s)."
                          where:
                            {prefix}    — stem of the *_response_text column (e.g. E21Response)
                            {grade}     — submission_score value with underscores replaced by spaces
                            {score}     — submission_numeric_score for this row
                            {max_score} — maximum submission_numeric_score across all rows
                                          (pattern: D followed by digits only, no underscore suffix)
                                          "dimension" vs "dimensions" used appropriately

Inputs:
  --source-file   Path to the source *-wide-stitched.csv file.
  --output-file   Destination path for the annotated copy.

Example:
    python prepare_scored_worksheet_with_comment_columns.py \\
        --source-file path/to/RUN_...-wide-stitched.csv \\
        --output-file path/to/RUN_...-wide-stitched-with-comments.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a Layer 4 wide-stitched CSV and append '.' and "
            "'Feedback comments' columns."
        )
    )
    parser.add_argument(
        "--source-file",
        type=Path,
        required=True,
        help="Path to the source *-wide-stitched.csv.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        required=True,
        help="Destination path for the annotated copy.",
    )
    return parser.parse_args()


def _response_text_prefix(header: list[str]) -> str:
    """Return the prefix of the first column matching *_response_text."""
    for col in header:
        if col.endswith("_response_text"):
            return col[: -len("_response_text")]
    return ""


def _dimension_columns(header: list[str]) -> list[str]:
    """Return column names that are bare dimension identifiers (e.g. D01, D02).

    Matches headers of the form D followed by one or more digits, with no
    underscore suffix (to exclude indicator columns such as D01_IE211).
    """
    import re
    pattern = re.compile(r'^D\d+$')
    return [col for col in header if pattern.match(col)]


def _build_feedback(
    prefix: str,
    grade: str,
    score_str: str,
    max_score_str: str,
    dim_count: int,
) -> str:
    grade_label = grade.replace("_", " ")
    dim_word = "dimension" if dim_count == 1 else "dimensions"
    return (
        f"Overall result for {prefix}: {grade_label} ( {score_str} / {max_score_str}). "
        f"{dim_count} {dim_word}."
    )


def main() -> None:
    args = parse_args()

    if not args.source_file.exists():
        print(f"Error: source file not found: {args.source_file}", file=sys.stderr)
        sys.exit(1)

    # --- first pass: collect all rows and compute max numeric score ---
    with args.source_file.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            print("Error: source file is empty.", file=sys.stderr)
            sys.exit(1)
        header = list(reader.fieldnames)
        rows = list(reader)

    if "submission_numeric_score" not in header:
        print(
            "Error: column 'submission_numeric_score' not found in source file.",
            file=sys.stderr,
        )
        sys.exit(1)
    if "submission_score" not in header:
        print(
            "Error: column 'submission_score' not found in source file.",
            file=sys.stderr,
        )
        sys.exit(1)

    numeric_values: list[float] = []
    for row in rows:
        raw = (row.get("submission_numeric_score") or "").strip()
        try:
            numeric_values.append(float(raw))
        except ValueError:
            pass

    if not numeric_values:
        print(
            "Warning: no numeric values found in 'submission_numeric_score'; "
            "Feedback comments column will be empty.",
            file=sys.stderr,
        )
        max_score_str = ""
    else:
        max_val = max(numeric_values)
        # Preserve one decimal place if the value is a whole number, else use
        # the natural float representation stripped of trailing zeros.
        if max_val == int(max_val):
            max_score_str = f"{max_val:.2f}"
        else:
            max_score_str = f"{max_val:g}"

    prefix = _response_text_prefix(header)
    dim_count = len(_dimension_columns(header))

    # --- second pass: write output ---
    args.output_file.parent.mkdir(parents=True, exist_ok=True)

    with args.output_file.open("w", newline="", encoding="utf-8") as dst_fh:
        writer = csv.DictWriter(dst_fh, fieldnames=header + [".", "Feedback comments"])
        writer.writeheader()

        for row in rows:
            score_raw = (row.get("submission_numeric_score") or "").strip()
            grade_raw = (row.get("submission_score") or "").strip()

            if score_raw and grade_raw and prefix and max_score_str:
                feedback = _build_feedback(prefix, grade_raw, score_raw, max_score_str, dim_count)
            else:
                feedback = ""

            writer.writerow({**row, ".": "", "Feedback comments": feedback})

    print(f"Written: {args.output_file}")


if __name__ == "__main__":
    main()

