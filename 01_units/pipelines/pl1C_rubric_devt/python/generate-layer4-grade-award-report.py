#!/usr/bin/env python3
"""Generate a markdown report with descriptive statistics for Layer 4 grade awards."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ITERATION_RE = re.compile(r"\b(iter\d+)\b", re.IGNORECASE)
RUN_RE = re.compile(r"\b(run\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class NumericSummary:
    count: int
    minimum: float
    q1: float
    median: float
    mean: float
    q3: float
    maximum: float
    stdev: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a markdown report with descriptive statistics for Layer 4 grade awards."
    )
    parser.add_argument("--submission-registry", type=Path, required=True)
    parser.add_argument("--sbo-manifest-file", type=Path, required=True)
    parser.add_argument("--file-with-scored-texts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=False)
    parser.add_argument("--iteration-label", type=str, required=False)
    parser.add_argument("--run-label", type=str, required=False)
    return parser.parse_args()


def derive_assignment_id(path: Path) -> str:
    match = re.match(r"^([A-Za-z0-9]+)_Layer4_", path.name)
    if match:
        return match.group(1)
    match = re.match(r"^([A-Za-z0-9]+)_Registry_", path.name)
    if match:
        return match.group(1)
    return "assignment"


def derive_iteration_label(path: Path, explicit_label: str | None) -> str:
    if explicit_label:
        return explicit_label.strip()
    for part in path.parts:
        match = ITERATION_RE.search(part)
        if match:
            return match.group(1).lower()
    match = ITERATION_RE.search(str(path))
    if match:
        return match.group(1).lower()
    return "iteration"


def derive_run_label(path: Path, explicit_label: str | None) -> str:
    if explicit_label:
        return explicit_label.strip()
    for part in path.parts:
        match = RUN_RE.search(part)
        if match:
            return match.group(1).lower()
    match = RUN_RE.search(str(path))
    if match:
        return match.group(1).lower()
    return "run"


def sanitize_label(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", label.strip()).strip("-") or "report"


def derive_output_filename(assignment_id: str, iteration_label: str, run_label: str) -> str:
    return (
        f"I_{assignment_id}_Layer4_grade_award_report_"
        f"{sanitize_label(iteration_label)}_{sanitize_label(run_label)}.md"
    )


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def parse_grade_scale(rows: list[dict[str, str]]) -> list[str]:
    for row in rows:
        raw_scale = str(row.get("submission_performance_scale", "")).strip()
        if raw_scale:
            return [item.strip() for item in raw_scale.split(",") if item.strip()]
    return []


def parse_float(value: str) -> float | None:
    stripped = str(value).strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def percentile_inclusive(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * fraction
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = position - lower_index
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    return lower_value + (upper_value - lower_value) * weight


def summarize_numeric(values: list[float]) -> NumericSummary:
    sorted_values = sorted(values)
    return NumericSummary(
        count=len(sorted_values),
        minimum=sorted_values[0],
        q1=percentile_inclusive(sorted_values, 0.25),
        median=statistics.median(sorted_values),
        mean=statistics.fmean(sorted_values),
        q3=percentile_inclusive(sorted_values, 0.75),
        maximum=sorted_values[-1],
        stdev=statistics.stdev(sorted_values) if len(sorted_values) > 1 else None,
    )


def format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def build_distribution_rows(categories: list[str], counts: Counter[str], total: int) -> list[list[str]]:
    rows: list[list[str]] = []
    seen: set[str] = set()
    for category in categories:
        count = counts.get(category, 0)
        rows.append([category, str(count), f"{(count / total * 100) if total else 0:.1f}%"])
        seen.add(category)
    for category in sorted(counts):
        if category in seen:
            continue
        count = counts[category]
        rows.append([category, str(count), f"{(count / total * 100) if total else 0:.1f}%"])
    return rows


def parse_json_object(raw_value: str) -> dict[str, str]:
    stripped = str(raw_value).strip()
    if not stripped:
        return {}
    decoded = json.loads(stripped)
    if not isinstance(decoded, dict):
        raise ValueError("Expected JSON object.")
    return {str(key): str(value) for key, value in decoded.items()}


def build_component_grade_rows(rows: list[dict[str, str]]) -> tuple[list[str], list[list[str]]]:
    component_grade_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        component_scores = parse_json_object(row.get("source_component_scores_json", ""))
        for component_id, grade in component_scores.items():
            component_grade_counts[component_id][grade] += 1
    if not component_grade_counts:
        return [], []

    grade_labels = sorted({grade for counts in component_grade_counts.values() for grade in counts})
    headers = ["component_id", *grade_labels]
    table_rows: list[list[str]] = []
    for component_id in sorted(component_grade_counts):
        counts = component_grade_counts[component_id]
        table_rows.append([component_id, *[str(counts.get(grade, 0)) for grade in grade_labels]])
    return headers, table_rows


def build_component_numeric_rows(rows: list[dict[str, str]]) -> list[list[str]]:
    component_numeric_values: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        numeric_values = parse_json_object(row.get("source_component_numeric_values_json", ""))
        for component_id, raw_value in numeric_values.items():
            parsed_value = parse_float(raw_value)
            if parsed_value is not None:
                component_numeric_values[component_id].append(parsed_value)

    table_rows: list[list[str]] = []
    for component_id in sorted(component_numeric_values):
        values = component_numeric_values[component_id]
        if not values:
            continue
        summary = summarize_numeric(values)
        table_rows.append(
            [
                component_id,
                str(summary.count),
                format_float(summary.minimum),
                format_float(summary.mean),
                format_float(summary.median),
                format_float(summary.maximum),
            ]
        )
    return table_rows


def generate_report(args: argparse.Namespace) -> Path:
    rows = load_rows(args.file_with_scored_texts)
    if not rows:
        raise ValueError(f"No scored rows found in {args.file_with_scored_texts}")

    assignment_id = derive_assignment_id(args.sbo_manifest_file)
    iteration_label = derive_iteration_label(args.file_with_scored_texts, args.iteration_label)
    run_label = derive_run_label(args.file_with_scored_texts, args.run_label)
    output_dir = args.output_dir.resolve() if args.output_dir else args.file_with_scored_texts.parent.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / derive_output_filename(assignment_id, iteration_label, run_label)

    total_rows = len(rows)
    submission_ids = {str(row.get("submission_id", "")).strip() for row in rows if str(row.get("submission_id", "")).strip()}
    grade_scale = parse_grade_scale(rows)
    grade_counts = Counter(str(row.get("submission_score", "")).strip() for row in rows if str(row.get("submission_score", "")).strip())
    confidence_counts = Counter(str(row.get("min_confidence_component", "")).strip() for row in rows if str(row.get("min_confidence_component", "")).strip())
    flags_counts = Counter(str(row.get("flags_any_component", "")).strip() for row in rows if str(row.get("flags_any_component", "")).strip())
    numeric_scores = [
        parsed_value
        for parsed_value in (parse_float(row.get("submission_numeric_score", "")) for row in rows)
        if parsed_value is not None
    ]
    numeric_summary = summarize_numeric(numeric_scores) if numeric_scores else None
    component_grade_headers, component_grade_rows = build_component_grade_rows(rows)
    component_numeric_rows = build_component_numeric_rows(rows)

    metadata_rows = [
        ["assignment_id", assignment_id],
        ["iteration_label", iteration_label],
        ["run_label", run_label],
        ["generated_at_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")],
        ["submission_registry", str(args.submission_registry.resolve())],
        ["manifest_file", str(args.sbo_manifest_file.resolve())],
        ["scored_csv", str(args.file_with_scored_texts.resolve())],
        ["output_file", str(output_path)],
        ["rows_read", str(total_rows)],
        ["distinct_submissions", str(len(submission_ids))],
    ]

    sections = [
        f"# Layer 4 Grade Award Report: {assignment_id}",
        "",
        "## Metadata",
        render_markdown_table(["field", "value"], metadata_rows),
        "",
        "## Final Grade Award Distribution",
        render_markdown_table(
            ["submission_score", "count", "percent"],
            build_distribution_rows(grade_scale, grade_counts, total_rows),
        ),
        "",
    ]

    if numeric_summary is not None:
        sections.extend(
            [
                "## Submission Numeric Score Summary",
                render_markdown_table(
                    ["count", "min", "q1", "median", "mean", "q3", "max", "stdev"],
                    [[
                        str(numeric_summary.count),
                        format_float(numeric_summary.minimum),
                        format_float(numeric_summary.q1),
                        format_float(numeric_summary.median),
                        format_float(numeric_summary.mean),
                        format_float(numeric_summary.q3),
                        format_float(numeric_summary.maximum),
                        format_float(numeric_summary.stdev),
                    ]],
                ),
                "",
            ]
        )

    if confidence_counts:
        sections.extend(
            [
                "## Minimum Component Confidence Distribution",
                render_markdown_table(
                    ["min_confidence_component", "count", "percent"],
                    build_distribution_rows([], confidence_counts, total_rows),
                ),
                "",
            ]
        )

    if flags_counts:
        sections.extend(
            [
                "## Flags Distribution",
                render_markdown_table(
                    ["flags_any_component", "count", "percent"],
                    build_distribution_rows([], flags_counts, total_rows),
                ),
                "",
            ]
        )

    if component_grade_headers and component_grade_rows:
        sections.extend(
            [
                "## Component Grade Award Counts",
                render_markdown_table(component_grade_headers, component_grade_rows),
                "",
            ]
        )

    if component_numeric_rows:
        sections.extend(
            [
                "## Component Numeric Score Summary",
                render_markdown_table(
                    ["component_id", "count", "min", "mean", "median", "max"],
                    component_numeric_rows,
                ),
                "",
            ]
        )

    output_path.write_text("\n".join(sections), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    output_path = generate_report(args)
    print(output_path)


if __name__ == "__main__":
    main()