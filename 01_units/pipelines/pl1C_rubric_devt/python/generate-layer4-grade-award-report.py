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

from generate_rubric_and_manifest_from_indicator_registry import collect_markdown_tables


ITERATION_RE = re.compile(r"\b(iter\d+)\b", re.IGNORECASE)
RUN_RE = re.compile(r"\b(run\d+)\b", re.IGNORECASE)
DIMENSION_ID_RE = re.compile(r"^D\d+(\d)$")
MAX_HISTOGRAM_BAR_WIDTH = 20


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


@dataclass(frozen=True)
class Layer4ScaleInfo:
    maximum_numeric_score: float
    maximum_component_numeric_score: float
    cutpoints: list[dict[str, object]]
    bound_component_ids: list[str]


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


def parse_layer4_scale_info(manifest_path: Path) -> Layer4ScaleInfo | None:
    tables = collect_markdown_tables(manifest_path)
    manifest_table = next(
        (
            table
            for table in tables
            if "submission_scoring_payload_json" in table.get("headers", [])
        ),
        None,
    )
    if manifest_table is None:
        return None

    rows = manifest_table.get("rows", [])
    if not rows:
        return None

    payload_raw = str(rows[0].get("submission_scoring_payload_json", "")).strip()
    if not payload_raw:
        return None

    payload = json.loads(payload_raw)
    if not isinstance(payload, dict):
        return None

    raw_cutpoints = payload.get("numeric_cutpoints", [])
    if not isinstance(raw_cutpoints, list) or not raw_cutpoints:
        return None

    maximum_numeric_score = max(float(cutpoint["numeric_maximum"]) for cutpoint in raw_cutpoints)
    raw_component_value_map = payload.get("component_value_map", {})
    maximum_component_numeric_score = 0.0
    if isinstance(raw_component_value_map, dict) and raw_component_value_map:
        maximum_component_numeric_score = max(float(value) for value in raw_component_value_map.values())
    raw_bound_component_ids = payload.get("bound_component_ids", [])
    bound_component_ids = [str(component_id) for component_id in raw_bound_component_ids if str(component_id).strip()]
    return Layer4ScaleInfo(
        maximum_numeric_score=maximum_numeric_score,
        maximum_component_numeric_score=maximum_component_numeric_score,
        cutpoints=raw_cutpoints,
        bound_component_ids=bound_component_ids,
    )


def discover_layer3_component_output_paths(layer4_scored_csv: Path) -> list[Path]:
    layer4_dir = layer4_scored_csv.resolve().parent
    layer3_dir = layer4_dir.parent / "layer3"
    if not layer3_dir.is_dir():
        return []
    return sorted(layer3_dir.glob("*_Layer3_component_scoring_*_output.csv"))


def discover_layer2_dimension_output_paths(layer4_scored_csv: Path) -> list[Path]:
    layer4_dir = layer4_scored_csv.resolve().parent
    layer2_dir = layer4_dir.parent / "layer2"
    if not layer2_dir.is_dir():
        return []
    return sorted(layer2_dir.glob("*_Layer2_dimension_scoring_*_output.csv"))


def indicator_sort_key(indicator_id: str) -> tuple[int, str]:
    match = re.match(r"^I(\d+)$", indicator_id)
    if match:
        return int(match.group(1)), indicator_id
    return 10**9, indicator_id


def aggregate_layer2_indicator_counts(layer4_scored_csv: Path) -> dict[str, dict[str, Counter[str]]]:
    aggregate_counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for csv_path in discover_layer2_dimension_output_paths(layer4_scored_csv):
        for row in load_rows(csv_path):
            dimension_id = str(row.get("dimension_id", "")).strip()
            match = DIMENSION_ID_RE.match(dimension_id)
            if not match:
                continue
            aggregate_dimension_id = f"D*{match.group(1)}"
            indicator_values = parse_json_object(row.get("source_indicator_values_json", ""))
            for indicator_id, indicator_value in indicator_values.items():
                aggregate_counts[aggregate_dimension_id][indicator_id][indicator_value] += 1
    return {
        aggregate_dimension_id: {
            indicator_id: counts
            for indicator_id, counts in sorted(indicator_counts.items(), key=lambda item: indicator_sort_key(item[0]))
        }
        for aggregate_dimension_id, indicator_counts in sorted(aggregate_counts.items())
    }


def aggregate_layer3_dimension_counts(layer4_scored_csv: Path) -> dict[str, Counter[str]]:
    aggregate_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for csv_path in discover_layer3_component_output_paths(layer4_scored_csv):
        for row in load_rows(csv_path):
            dimension_values = parse_json_object(row.get("source_dimension_values_json", ""))
            for dimension_id, dimension_value in dimension_values.items():
                match = DIMENSION_ID_RE.match(dimension_id)
                if not match:
                    continue
                aggregate_dimension_id = f"D*{match.group(1)}"
                aggregate_counts[aggregate_dimension_id][dimension_value] += 1
    return aggregate_counts


def build_layer3_dimension_rows(aggregate_counts: dict[str, Counter[str]]) -> list[list[str]]:
    dimension_ids = [dimension_id for dimension_id in ("D*1", "D*2", "D*3") if dimension_id in aggregate_counts]
    if not dimension_ids:
        return []

    ordered_bins = [
        ("0-little_to_no_demonstration", "little_to_no_demonstration"),
        ("1-partially_demonstrated", "partially_demonstrated"),
        ("2-demonstrated", "demonstrated"),
    ]
    table_rows: list[list[str]] = []
    for display_label, raw_label in ordered_bins:
        table_rows.append(
            [display_label, *[str(aggregate_counts[dimension_id].get(raw_label, 0)) for dimension_id in dimension_ids]]
        )
    table_rows.append(
        ["Total", *[str(sum(aggregate_counts[dimension_id].values())) for dimension_id in dimension_ids]]
    )
    return table_rows


def build_layer3_dimension_histogram_rows(
    aggregate_counts: dict[str, Counter[str]],
) -> tuple[list[list[str]], str]:
    dimension_ids = [dimension_id for dimension_id in ("D*1", "D*2", "D*3") if dimension_id in aggregate_counts]
    if not dimension_ids:
        return [], build_histogram_resolution_note(1)

    ordered_bins = [
        ("0-little_to_no_demonstration", "little_to_no_demonstration"),
        ("1-partially_demonstrated", "partially_demonstrated"),
        ("2-demonstrated", "demonstrated"),
    ]
    max_count = max(
        (
            aggregate_counts[dimension_id].get(raw_label, 0)
            for dimension_id in dimension_ids
            for _, raw_label in ordered_bins
        ),
        default=0,
    )
    resolution = compute_histogram_resolution(max_count)
    table_rows: list[list[str]] = []
    for display_label, raw_label in ordered_bins:
        count_lines: list[str] = []
        bar_lines: list[str] = []
        for dimension_id in dimension_ids:
            bin_count = aggregate_counts[dimension_id].get(raw_label, 0)
            count_lines.append(str(bin_count))
            bar_lines.append(render_histogram_bar(bin_count, resolution))
        table_rows.append([
            display_label,
            "<br>".join(count_lines),
            "<br>".join(bar_lines),
        ])
    table_rows.append([
        "Total",
        "<br>".join(str(sum(aggregate_counts[dimension_id].values())) for dimension_id in dimension_ids),
        "",
    ])
    return table_rows, build_histogram_resolution_note(resolution)


def build_single_layer3_dimension_histogram_rows(
    aggregate_counts: dict[str, Counter[str]],
    dimension_id: str,
) -> tuple[list[list[str]], str]:
    if dimension_id not in aggregate_counts:
        return [], build_histogram_resolution_note(1)

    ordered_bins = [
        ("0-little_to_no_demonstration", "little_to_no_demonstration"),
        ("1-partially_demonstrated", "partially_demonstrated"),
        ("2-demonstrated", "demonstrated"),
    ]
    counts = aggregate_counts[dimension_id]
    max_count = max((counts.get(raw_label, 0) for _, raw_label in ordered_bins), default=0)
    resolution = compute_histogram_resolution(max_count)
    table_rows: list[list[str]] = []
    for display_label, raw_label in ordered_bins:
        bin_count = counts.get(raw_label, 0)
        table_rows.append([
            display_label,
            str(bin_count),
            render_histogram_bar(bin_count, resolution),
        ])
    table_rows.append(["Total", str(sum(counts.values())), ""])
    return table_rows, build_histogram_resolution_note(resolution)


def build_layer2_indicator_histogram_rows(
    indicator_counts: dict[str, Counter[str]],
) -> tuple[list[str], list[list[str]], str]:
    indicator_ids = sorted(indicator_counts, key=indicator_sort_key)
    if not indicator_ids:
        return [], [], build_histogram_resolution_note(1)

    preferred_bins = ["not_present", "present"]
    observed_bins = {
        indicator_value
        for counts in indicator_counts.values()
        for indicator_value in counts
    }
    ordered_bins = preferred_bins + sorted(observed_bins - set(preferred_bins))
    max_count = max(
        (
            indicator_counts[indicator_id].get(indicator_value, 0)
            for indicator_id in indicator_ids
            for indicator_value in ordered_bins
        ),
        default=0,
    )
    resolution = compute_histogram_resolution(max_count)
    table_rows: list[list[str]] = []
    for indicator_value in ordered_bins:
        count_lines: list[str] = []
        bar_lines: list[str] = []
        for indicator_id in indicator_ids:
            bin_count = indicator_counts[indicator_id].get(indicator_value, 0)
            count_lines.append(str(bin_count))
            bar_lines.append(render_histogram_bar(bin_count, resolution))
        table_rows.append([
            indicator_value,
            "<br>".join(count_lines),
            "<br>".join(bar_lines),
        ])
    table_rows.append([
        "Total",
        "<br>".join(str(sum(indicator_counts[indicator_id].values())) for indicator_id in indicator_ids),
        "",
    ])
    return indicator_ids, table_rows, build_histogram_resolution_note(resolution)


def normalize_to_percent(value: float, maximum_numeric_score: float) -> float:
    if maximum_numeric_score <= 0:
        return 0.0
    return value / maximum_numeric_score * 100.0


def build_band_edges() -> list[tuple[float, float]]:
    edges: list[tuple[float, float]] = [(0.0, 50.0)]
    start = 50.0
    while start < 100.0:
        end = min(start + 5.0, 100.0)
        edges.append((start, end))
        start = end
    return edges


def intervals_overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> bool:
    return start_a < end_b and start_b < end_a


def format_band_value(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}"


def format_band_label(band_min: float, band_max: float) -> str:
    return f"{format_band_value(band_min)}-{format_band_value(band_max)}"


def compute_histogram_resolution(max_count: int, max_width: int = MAX_HISTOGRAM_BAR_WIDTH) -> int:
    if max_count <= 0:
        return 1
    return max(1, (max_count + max_width - 1) // max_width)


def render_histogram_bar(count: int, resolution: int) -> str:
    if count <= 0:
        return ""
    bar_width = max(1, (count + resolution - 1) // resolution)
    return "█" * bar_width


def build_histogram_resolution_note(resolution: int, max_width: int = MAX_HISTOGRAM_BAR_WIDTH) -> str:
    if resolution == 1:
        return f"Resolution: 1 block = 1 count; max width = {max_width} blocks."
    return f"Resolution: 1 block ~= {resolution} counts; max width = {max_width} blocks."


def score_in_band(score: float, band_min: float, band_max: float) -> bool:
    if band_max >= 100.0:
        return band_min <= score <= band_max
    return band_min <= score < band_max


def collect_cutpoint_percentage_series(
    scale_info: Layer4ScaleInfo,
    input_rows: list[dict[str, str]],
) -> tuple[list[float], dict[str, list[float]]]:
    component_ids = scale_info.bound_component_ids
    submission_percentages: list[float] = []
    component_percentages: dict[str, list[float]] = defaultdict(list)
    for row in input_rows:
        submission_numeric_score = parse_float(row.get("submission_numeric_score", ""))
        if submission_numeric_score is not None:
            submission_percentages.append(
                normalize_to_percent(submission_numeric_score, scale_info.maximum_numeric_score)
            )

        component_numeric_values = parse_json_object(row.get("source_component_numeric_values_json", ""))
        for component_id in component_ids:
            component_numeric_value = parse_float(component_numeric_values.get(component_id, ""))
            if component_numeric_value is None:
                continue
            component_percentages[component_id].append(
                normalize_to_percent(component_numeric_value, scale_info.maximum_component_numeric_score)
            )

    return submission_percentages, component_percentages


def build_histogram_rows(percentages: list[float]) -> tuple[list[list[str]], str]:
    band_edges = build_band_edges()
    band_counts = [
        sum(
            1 for normalized_percentage in percentages
            if score_in_band(normalized_percentage, band_min, band_max)
        )
        for band_min, band_max in band_edges
    ]
    resolution = compute_histogram_resolution(max(band_counts, default=0))
    table_rows: list[list[str]] = []
    for (band_min, band_max), band_count in zip(band_edges, band_counts):
        table_rows.append([
            format_band_label(band_min, band_max),
            str(band_count),
            render_histogram_bar(band_count, resolution),
        ])
    table_rows.append(["Total", str(len(percentages)), ""])
    return table_rows, build_histogram_resolution_note(resolution)


def build_multi_histogram_rows(
    series_by_label: list[tuple[str, list[float]]],
) -> tuple[list[list[str]], str]:
    band_edges = build_band_edges()
    band_counts_by_series: list[list[int]] = []
    max_count = 0
    for _, percentages in series_by_label:
        series_counts = [
            sum(
                1 for normalized_percentage in percentages
                if score_in_band(normalized_percentage, band_min, band_max)
            )
            for band_min, band_max in band_edges
        ]
        band_counts_by_series.append(series_counts)
        max_count = max(max_count, max(series_counts, default=0))
    resolution = compute_histogram_resolution(max_count)
    table_rows: list[list[str]] = []
    for band_index, (band_min, band_max) in enumerate(band_edges):
        count_lines: list[str] = []
        bar_lines: list[str] = []
        for series_counts in band_counts_by_series:
            band_count = series_counts[band_index]
            count_lines.append(str(band_count))
            bar_lines.append(render_histogram_bar(band_count, resolution))
        table_rows.append([
            format_band_label(band_min, band_max),
            "<br>".join(count_lines),
            "<br>".join(bar_lines),
        ])
    table_rows.append([
        "Total",
        "<br>".join(str(len(percentages)) for _, percentages in series_by_label),
        "",
    ])
    return table_rows, build_histogram_resolution_note(resolution)


def build_percentage_distribution_rows(percentages: list[float]) -> list[list[str]]:
    percentage_counts = Counter(f"{value:.1f}%" for value in percentages)
    total = len(percentages)
    ordered_values = sorted(percentage_counts, key=lambda value: float(value.rstrip("%")))
    return [
        [percentage_value, str(percentage_counts[percentage_value]), f"{(percentage_counts[percentage_value] / total * 100) if total else 0:.1f}%"]
        for percentage_value in ordered_values
    ]


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
    scale_info = parse_layer4_scale_info(args.sbo_manifest_file)
    normalized_percentages = [
        normalize_to_percent(value, scale_info.maximum_numeric_score)
        for value in numeric_scores
    ] if scale_info is not None else []
    numeric_summary = summarize_numeric(numeric_scores) if numeric_scores else None
    normalized_percentage_summary = summarize_numeric(normalized_percentages) if normalized_percentages else None
    component_grade_headers, component_grade_rows = build_component_grade_rows(rows)
    component_numeric_rows = build_component_numeric_rows(rows)
    layer2_indicator_counts = aggregate_layer2_indicator_counts(args.file_with_scored_texts)
    layer3_dimension_counts = aggregate_layer3_dimension_counts(args.file_with_scored_texts)
    layer3_dimension_ids = [dimension_id for dimension_id in ("D*1", "D*2", "D*3") if dimension_id in layer3_dimension_counts]
    layer3_dimension_display_ids = [f"`{dimension_id}`" for dimension_id in layer3_dimension_ids]
    layer3_dimension_rows = build_layer3_dimension_rows(layer3_dimension_counts)
    layer3_dimension_histogram_rows, layer3_dimension_histogram_note = build_layer3_dimension_histogram_rows(layer3_dimension_counts)

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
    if scale_info is not None:
        metadata_rows.append(["maximum_numeric_score", format_float(scale_info.maximum_numeric_score)])

    sections = [
        f"## Layer 4 Grade Award Report: {assignment_id}",
        "",
        "### Metadata",
        render_markdown_table(["field", "value"], metadata_rows),
        "",
        "### Final Grade Award Distribution",
        render_markdown_table(
            ["submission_score", "count", "percent"],
            build_distribution_rows(grade_scale, grade_counts, total_rows),
        ),
        "",
    ]

    if scale_info is not None:
        submission_percentages, component_percentages = collect_cutpoint_percentage_series(scale_info, rows)
        submission_histogram_rows, submission_histogram_note = build_histogram_rows(submission_percentages)
        sections.extend(
            [
                "### Grade Band Mapping to 0-100%",
                "#### Submission",
                render_markdown_table(
                    ["Bin", "Count", "Bar"],
                    submission_histogram_rows,
                ),
                submission_histogram_note,
                "",
                "",
            ]
        )
        component_series = [
            (component_id, component_percentages.get(component_id, []))
            for component_id in scale_info.bound_component_ids
        ]
        if component_series:
            component_histogram_rows, component_histogram_note = build_multi_histogram_rows(component_series)
            sections.extend(
                [
                    "#### Components",
                    "Component order: " + ", ".join(component_id for component_id, _ in component_series),
                    "",
                    render_markdown_table(
                        ["Bin", "Count", "Bar"],
                        component_histogram_rows,
                    ),
                    component_histogram_note,
                    "",
                ]
            )

    if numeric_summary is not None:
        sections.extend(
            [
                "### Submission Numeric Score Summary",
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

    if normalized_percentage_summary is not None:
        sections.extend(
            [
                "### Submission Percentage Score Summary",
                render_markdown_table(
                    ["count", "min", "q1", "median", "mean", "q3", "max", "stdev"],
                    [[
                        str(normalized_percentage_summary.count),
                        f"{normalized_percentage_summary.minimum:.1f}%",
                        f"{normalized_percentage_summary.q1:.1f}%",
                        f"{normalized_percentage_summary.median:.1f}%",
                        f"{normalized_percentage_summary.mean:.1f}%",
                        f"{normalized_percentage_summary.q3:.1f}%",
                        f"{normalized_percentage_summary.maximum:.1f}%",
                        f"{normalized_percentage_summary.stdev:.1f}%" if normalized_percentage_summary.stdev is not None else "",
                    ]],
                ),
                "",
                "### Exact Percentage Distribution",
                render_markdown_table(
                    ["normalized_grade_value", "count", "percent"],
                    build_percentage_distribution_rows(normalized_percentages),
                ),
                "",
            ]
        )

    if confidence_counts:
        sections.extend(
            [
                "### Minimum Component Confidence Distribution",
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
                "### Flags Distribution",
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
                "### Component Grade Award Counts",
                render_markdown_table(component_grade_headers, component_grade_rows),
                "",
            ]
        )

    if component_numeric_rows:
        sections.extend(
            [
                "### Component Numeric Score Summary",
                render_markdown_table(
                    ["component_id", "count", "min", "mean", "median", "max"],
                    component_numeric_rows,
                ),
                "",
            ]
        )

    if layer3_dimension_rows:
        sections.extend(
            [
                f"## Layer 3 Grade Award Report: {assignment_id}",
                "",
                "### Aggregate Dimension Distribution",
                render_markdown_table(["Bin", *layer3_dimension_display_ids], layer3_dimension_rows),
                "",
            ]
        )
        if layer3_dimension_histogram_rows:
            sections.extend(
                [
                    "### Aggregate Dimension Histogram",
                    "Dimension order: " + ", ".join(layer3_dimension_display_ids),
                    "",
                    render_markdown_table(["Bin", "Count", "Bar"], layer3_dimension_histogram_rows),
                    layer3_dimension_histogram_note,
                    "",
                ]
            )
            for dimension_id in layer3_dimension_ids:
                single_dimension_rows, single_dimension_note = build_single_layer3_dimension_histogram_rows(
                    layer3_dimension_counts,
                    dimension_id,
                )
                if not single_dimension_rows:
                    continue
                sections.extend(
                    [
                        f"#### `{dimension_id}`",
                        render_markdown_table(["Bin", "Count", "Bar"], single_dimension_rows),
                        single_dimension_note,
                        "",
                    ]
                )

    layer2_dimension_ids = [dimension_id for dimension_id in ("D*1", "D*2", "D*3") if dimension_id in layer2_indicator_counts]
    if layer2_dimension_ids:
        sections.extend(
            [
                f"## Layer 2 Grade Award Report: {assignment_id}",
                "",
            ]
        )
        for aggregate_dimension_id in layer2_dimension_ids:
            indicator_ids, layer2_histogram_rows, layer2_histogram_note = build_layer2_indicator_histogram_rows(
                layer2_indicator_counts[aggregate_dimension_id]
            )
            if not indicator_ids:
                continue
            sections.extend(
                [
                    f"### `{aggregate_dimension_id}` Indicator Histogram",
                    "Indicator order: " + ", ".join(f"`{indicator_id}`" for indicator_id in indicator_ids),
                    "",
                    render_markdown_table(["Bin", "Count", "Bar"], layer2_histogram_rows),
                    layer2_histogram_note,
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