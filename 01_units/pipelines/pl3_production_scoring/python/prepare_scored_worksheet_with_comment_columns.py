#!/usr/bin/env python3
"""Prepare a scored-worksheet CSV for manual feedback entry.

Copies a Layer 4 wide-stitched CSV to a staging location and appends two
columns at the end:
  - "."               — spacer / separator column
  - "Feedback comments" — pre-populated with a per-row summary string of the
                          form:
                          "Overall result for {section}: {grade} ({score} / {max_score}). {n} dimension(s)."
                          "{newline}  {dimension_1}: {value_1}"
                          "{newline}  {dimension_2}: {value_2}"
                          where:
                            {section}   — display label derived from the *_response_text column stem
                            {grade}     — submission_score value with underscores replaced by spaces
                            {score}     — submission_numeric_score for this row
                            {max_score} — maximum submission_numeric_score across all rows
                            {n}         — count of dimension columns (pattern: D followed by digits only,
                                          no underscore suffix)
                            {newline}   — actual line-feed character (ASCII 10 / CHAR(10))

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
import re
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


def _section_label(prefix: str) -> str:
    """Return a human-readable section label from the response-text prefix."""
    if not prefix:
        return ""
    if prefix.endswith("Response"):
        prefix = prefix[: -len("Response")]
    return f"Section {prefix}"


def _dimension_columns(header: list[str]) -> list[str]:
    """Return column names that are bare dimension identifiers (e.g. D01, D02)."""
    pattern = re.compile(r"^D\d+$")
    return [col for col in header if pattern.match(col)]


def _normalize_dimension_value(value: str) -> str:
    """Strip leading ordinal prefixes such as '1-' from dimension labels."""
    return re.sub(r"^\d+-", "", value)


def _build_feedback(
    section_label: str,
    grade: str,
    score_str: str,
    max_score_str: str,
    dim_count: int,
    dim_values: list[tuple[str, str]],
) -> str:
    grade_label = grade.replace("_", " ")
    dim_word = "dimension" if dim_count == 1 else "dimensions"
    lines = [
        f"Overall result for {section_label}: {grade_label} ({score_str} / {max_score_str}). {dim_count} {dim_word}."
    ]
    for dim_name, dim_value in dim_values:
        lines.append(f"  {dim_name}: {dim_value}")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    if not args.source_file.exists():
        print(f"Error: source file not found: {args.source_file}", file=sys.stderr)
        sys.exit(1)

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
        if max_val == int(max_val):
            max_score_str = f"{max_val:.2f}"
        else:
            max_score_str = f"{max_val:g}"

    prefix = _response_text_prefix(header)
    section_label = _section_label(prefix)
    dimension_columns = _dimension_columns(header)
    dim_count = len(dimension_columns)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)

    with args.output_file.open("w", newline="", encoding="utf-8") as dst_fh:
        writer = csv.DictWriter(dst_fh, fieldnames=header + [".", "Feedback comments"])
        writer.writeheader()

        for row in rows:
            score_raw = (row.get("submission_numeric_score") or "").strip()
            grade_raw = (row.get("submission_score") or "").strip()
            dim_values = [
                (dim_name, _normalize_dimension_value((row.get(dim_name) or "").strip()))
                for dim_name in dimension_columns
            ]

            if score_raw and grade_raw and section_label and max_score_str:
                feedback = _build_feedback(
                    section_label,
                    grade_raw,
                    score_raw,
                    max_score_str,
                    dim_count,
                    dim_values,
                )
            else:
                feedback = ""

            writer.writerow({**row, ".": "", "Feedback comments": feedback})

    print(f"Written: {args.output_file}")


if __name__ == "__main__":
    main()

