#!/usr/bin/env python3
"""Prepare a scored-worksheet CSV for manual feedback entry.

Copies a scored CSV to a staging location and appends or populates output
columns according to a JSON scheme selected with --scheme. Schemes can either
describe a single score column plus generated feedback, or a set of score and
feedback columns matched by regex and aggregated into output columns.

Inputs:
    --source-file   Path to the source scored CSV.
    --output-file   Destination path for the annotated copy.
    --scheme        Scheme name or explicit JSON path. Defaults to the current
                                    Layer 4 wide-stitched scheme.

Example:
        python prepare_scored_worksheet_with_comment_columns.py \
                --source-file path/to/RUN_...-wide-stitched.csv \
                --output-file path/to/RUN_...-wide-stitched-with-comments.csv \
                --scheme current-layer4-wide-stitched
"""

from __future__ import annotations

import argparse
import csv
import json
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
    parser.add_argument(
        "--scheme",
        default="current-layer4-wide-stitched",
        help=(
            "Scheme name from worksheet_feedback_schemes/ or an explicit JSON path. "
            "Defaults to 'current-layer4-wide-stitched'."
        ),
    )
    return parser.parse_args()


def _load_scheme(scheme_value: str) -> dict[str, object]:
    candidate = Path(scheme_value)
    if candidate.is_file():
        scheme_path = candidate
    else:
        scheme_dir = Path(__file__).resolve().parent / "worksheet_feedback_schemes"
        filename = scheme_value if scheme_value.endswith(".json") else f"{scheme_value}.json"
        scheme_path = scheme_dir / filename

    if not scheme_path.is_file():
        print(f"Error: scheme file not found: {scheme_path}", file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(scheme_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid scheme JSON in {scheme_path}: {exc}", file=sys.stderr)
        sys.exit(1)


def _require_scheme_value(container: dict[str, object], key: str) -> object:
    value = container.get(key)
    if value in (None, ""):
        print(f"Error: scheme is missing required key '{key}'.", file=sys.stderr)
        sys.exit(1)
    return value


def _matching_columns(header: list[str], match_regex: str) -> list[str]:
    pattern = re.compile(match_regex)
    return [col for col in header if pattern.match(col)]


def _parse_float_or_none(raw_value: str) -> float | None:
    text = (raw_value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_numeric(value: float) -> str:
    if value == int(value):
        return f"{value:.2f}"
    return f"{value:g}"


def _response_text_prefix(header: list[str], match_regex: str) -> str:
    """Return the prefix of the first response-text column matched by scheme regex."""
    pattern = re.compile(match_regex)
    for col in header:
        match = pattern.match(col)
        if match:
            return match.group(1) if match.groups() else col
    return ""


def _section_label(prefix: str, section_prefix: str, strip_suffix: str) -> str:
    """Return a human-readable section label from the response-text prefix."""
    if not prefix:
        return ""
    if strip_suffix and prefix.endswith(strip_suffix):
        prefix = prefix[: -len(strip_suffix)]
    return f"{section_prefix}{prefix}"


def _dimension_columns(header: list[str], match_regex: str) -> list[str]:
    """Return column names matched by the scheme's dimension regex."""
    pattern = re.compile(match_regex)
    return [col for col in header if pattern.match(col)]


def _normalize_dimension_value(value: str, strip_leading_regex: str) -> str:
    """Normalize a dimension value according to scheme rules."""
    if not strip_leading_regex:
        return value
    return re.sub(strip_leading_regex, "", value)


def _aggregate_score_values(row: dict[str, str], score_columns: list[str], aggregate: str) -> str:
    values = [
        parsed
        for parsed in (_parse_float_or_none(row.get(column, "")) for column in score_columns)
        if parsed is not None
    ]
    if not values:
        return ""
    if aggregate == "sum":
        return _format_numeric(sum(values))
    if aggregate == "max":
        return _format_numeric(max(values))
    print(f"Error: unsupported score aggregate '{aggregate}'.", file=sys.stderr)
    sys.exit(1)


def _concatenate_feedback_values(
    row: dict[str, str],
    feedback_columns: list[str],
    separator: str,
) -> str:
    values = [(row.get(column) or "").strip() for column in feedback_columns]
    return separator.join(value for value in values if value)


def _build_feedback(
    summary_template: str,
    dimension_template: str,
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
        summary_template.format(
            section_label=section_label,
            grade=grade_label,
            score=score_str,
            max_score=max_score_str,
            dimension_count=dim_count,
            dimension_word=dim_word,
        )
    ]
    for dim_name, dim_value in dim_values:
        lines.append(
            dimension_template.format(
                dimension=dim_name,
                value=dim_value,
            )
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    scheme = _load_scheme(args.scheme)

    separator_output_column = str(_require_scheme_value(scheme, "separator_output_column"))
    feedback_output_column = str(_require_scheme_value(scheme, "feedback_output_column"))
    score_column = str(scheme.get("score_column", ""))
    score_output_column = str(scheme.get("score_output_column", ""))

    score_columns_cfg = scheme.get("score_columns")
    if score_column and score_columns_cfg:
        print("Error: scheme must define either 'score_column' or 'score_columns', not both.", file=sys.stderr)
        sys.exit(1)
    if not score_column and not score_columns_cfg:
        print("Error: scheme must define one of 'score_column' or 'score_columns'.", file=sys.stderr)
        sys.exit(1)

    score_match_regex = ""
    score_aggregate = "max"
    if score_columns_cfg:
        if not isinstance(score_columns_cfg, dict):
            print("Error: scheme key 'score_columns' must be an object.", file=sys.stderr)
            sys.exit(1)
        score_match_regex = str(_require_scheme_value(score_columns_cfg, "match_regex"))
        score_aggregate = str(score_columns_cfg.get("aggregate", "sum"))

    grade_label_column = str(scheme.get("grade_label_column", ""))

    feedback_columns_cfg = scheme.get("feedback_columns")
    feedback_match_regex = ""
    feedback_separator = "\n\n"
    if feedback_columns_cfg:
        if not isinstance(feedback_columns_cfg, dict):
            print("Error: scheme key 'feedback_columns' must be an object.", file=sys.stderr)
            sys.exit(1)
        feedback_match_regex = str(_require_scheme_value(feedback_columns_cfg, "match_regex"))
        feedback_separator = str(feedback_columns_cfg.get("separator", "\n\n"))

    response_text_regex = ""
    response_text_prefix = ""
    response_text_strip_suffix = ""
    dimension_match_regex = ""
    strip_leading_regex = ""
    summary_template = ""
    dimension_template = ""

    if not feedback_columns_cfg:
        response_text = _require_scheme_value(scheme, "response_text")
        if not isinstance(response_text, dict):
            print("Error: scheme key 'response_text' must be an object.", file=sys.stderr)
            sys.exit(1)
        response_text_regex = str(_require_scheme_value(response_text, "match_regex"))
        response_text_prefix = str(_require_scheme_value(response_text, "section_prefix"))
        response_text_strip_suffix = str(response_text.get("strip_suffix", ""))

        dimension_columns_cfg = _require_scheme_value(scheme, "dimension_columns")
        if not isinstance(dimension_columns_cfg, dict):
            print("Error: scheme key 'dimension_columns' must be an object.", file=sys.stderr)
            sys.exit(1)
        dimension_match_regex = str(_require_scheme_value(dimension_columns_cfg, "match_regex"))

        dimension_normalization = scheme.get("dimension_value_normalization", {})
        if not isinstance(dimension_normalization, dict):
            print("Error: scheme key 'dimension_value_normalization' must be an object.", file=sys.stderr)
            sys.exit(1)
        strip_leading_regex = str(dimension_normalization.get("strip_leading_regex", ""))

        feedback_format = _require_scheme_value(scheme, "feedback_format")
        if not isinstance(feedback_format, dict):
            print("Error: scheme key 'feedback_format' must be an object.", file=sys.stderr)
            sys.exit(1)
        summary_template = str(_require_scheme_value(feedback_format, "summary_template"))
        dimension_template = str(_require_scheme_value(feedback_format, "dimension_template"))

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

    score_source_columns: list[str]
    if score_column:
        if score_column not in header:
            print(
                f"Error: column '{score_column}' not found in source file.",
                file=sys.stderr,
            )
            sys.exit(1)
        score_source_columns = [score_column]
    else:
        score_source_columns = _matching_columns(header, score_match_regex)
        if not score_source_columns:
            print(
                f"Error: no columns matched score regex '{score_match_regex}' in source file.",
                file=sys.stderr,
            )
            sys.exit(1)

    if grade_label_column and grade_label_column not in header:
        print(
            f"Error: column '{grade_label_column}' not found in source file.",
            file=sys.stderr,
        )
        sys.exit(1)

    feedback_source_columns: list[str] = []
    if feedback_columns_cfg:
        feedback_source_columns = _matching_columns(header, feedback_match_regex)
        if not feedback_source_columns:
            print(
                f"Error: no columns matched feedback regex '{feedback_match_regex}' in source file.",
                file=sys.stderr,
            )
            sys.exit(1)

    numeric_values: list[float] = []
    for row in rows:
        if score_column:
            raw = (row.get(score_column) or "").strip()
        else:
            raw = _aggregate_score_values(row, score_source_columns, score_aggregate)
        try:
            numeric_values.append(float(raw))
        except ValueError:
            pass

    if not numeric_values:
        print(
            f"Warning: no numeric values found in '{score_column}'; "
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

    prefix = _response_text_prefix(header, response_text_regex) if response_text_regex else ""
    section_label = _section_label(prefix, response_text_prefix, response_text_strip_suffix) if response_text_regex else ""
    dimension_columns = _dimension_columns(header, dimension_match_regex) if dimension_match_regex else []
    dim_count = len(dimension_columns)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(header)
    if score_output_column and score_output_column not in fieldnames:
        fieldnames.append(score_output_column)
    if separator_output_column not in fieldnames:
        fieldnames.append(separator_output_column)
    if feedback_output_column not in fieldnames:
        fieldnames.append(feedback_output_column)

    with args.output_file.open("w", newline="", encoding="utf-8") as dst_fh:
        writer = csv.DictWriter(
            dst_fh,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for row in rows:
            if score_column:
                score_raw = (row.get(score_column) or "").strip()
            else:
                score_raw = _aggregate_score_values(row, score_source_columns, score_aggregate)
            grade_raw = (row.get(grade_label_column) or "").strip()
            dim_values = [
                (
                    dim_name,
                    _normalize_dimension_value(
                        (row.get(dim_name) or "").strip(),
                        strip_leading_regex,
                    ),
                )
                for dim_name in dimension_columns
            ]

            if feedback_columns_cfg:
                feedback = _concatenate_feedback_values(
                    row,
                    feedback_source_columns,
                    feedback_separator,
                )
            elif score_raw and grade_raw and section_label and max_score_str:
                feedback = _build_feedback(
                    summary_template,
                    dimension_template,
                    section_label,
                    grade_raw,
                    score_raw,
                    max_score_str,
                    dim_count,
                    dim_values,
                )
            else:
                feedback = ""

            writer.writerow(
                {
                    **row,
                    **({score_output_column: score_raw} if score_output_column else {}),
                    separator_output_column: "",
                    feedback_output_column: feedback,
                }
            )

    print(f"Written: {args.output_file}")


if __name__ == "__main__":
    main()

