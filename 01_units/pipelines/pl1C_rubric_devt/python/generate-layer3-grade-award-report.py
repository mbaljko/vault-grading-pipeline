#!/usr/bin/env python3
"""Generate a markdown report with descriptive statistics for Layer 3 component grade awards."""

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a markdown report with descriptive statistics for Layer 3 component grade awards."
    )
    parser.add_argument("--component-registry", type=Path, required=True)
    parser.add_argument("--sbo-manifest-file", type=Path, required=True)
    parser.add_argument("--file-with-scored-texts", type=Path, required=True, action="append")
    parser.add_argument("--output-dir", type=Path, required=False)
    parser.add_argument("--iteration-label", type=str, required=False)
    parser.add_argument("--run-label", type=str, required=False)
    return parser.parse_args()


def derive_assignment_id(path: Path) -> str:
    match = re.match(r"^([A-Za-z0-9]+)_Layer3_", path.name)
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
        f"I_{assignment_id}_Layer3_grade_award_report_"
        f"{sanitize_label(iteration_label)}_{sanitize_label(run_label)}.md"
    )


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_rows_from_paths(csv_paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for csv_path in csv_paths:
        rows.extend(load_rows(csv_path))
    return rows


def parse_grade_scale(rows: list[dict[str, str]]) -> list[str]:
    for row in rows:
        raw_scale = str(row.get("component_performance_scale", "")).strip()
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


def discover_layer2_dimension_output_paths(layer3_scored_csv: Path) -> list[Path]:
    layer3_dir = layer3_scored_csv.resolve().parent
    layer2_dir = layer3_dir.parent / "layer2"
    if not layer2_dir.is_dir():
        return []
    return sorted(layer2_dir.glob("*_Layer2_dimension_scoring_*_output.csv"))


def indicator_sort_key(indicator_id: str) -> tuple[int, str]:
    match = re.match(r"^I(\d+)$", indicator_id)
    if match:
        return int(match.group(1)), indicator_id
    return 10**9, indicator_id


def wildcard_indicator_id(indicator_id: str) -> str:
    match = re.match(r"^I\d*(\d)$", indicator_id)
    if match:
        return f"I*{match.group(1)}"
    return indicator_id


def wildcard_indicator_sort_key(indicator_id: str) -> tuple[int, str]:
    match = re.match(r"^I\*(\d)$", indicator_id)
    if match:
        return int(match.group(1)), indicator_id
    return indicator_sort_key(indicator_id)


def aggregate_layer2_indicator_counts(layer3_scored_csv: Path) -> dict[str, dict[str, Counter[str]]]:
    aggregate_counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for csv_path in discover_layer2_dimension_output_paths(layer3_scored_csv):
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


def aggregate_layer3_dimension_counts(rows: list[dict[str, str]]) -> dict[str, Counter[str]]:
    aggregate_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
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
    table_rows.append(["Total", *[str(sum(aggregate_counts[dimension_id].values())) for dimension_id in dimension_ids]])
    return table_rows


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
        table_rows.append([display_label, "<br>".join(count_lines), "<br>".join(bar_lines)])
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
    total_count = sum(counts.values())
    max_count = max((counts.get(raw_label, 0) for _, raw_label in ordered_bins), default=0)
    resolution = compute_histogram_resolution(max_count)
    table_rows: list[list[str]] = []
    for display_label, raw_label in ordered_bins:
        bin_count = counts.get(raw_label, 0)
        table_rows.append([
            display_label,
            str(bin_count),
            f"{(bin_count / total_count * 100) if total_count else 0:.1f}%",
            render_histogram_bar(bin_count, resolution),
        ])
    table_rows.append(["Total", str(total_count), "100.0%", ""])
    return table_rows, build_histogram_resolution_note(resolution)


def build_layer2_indicator_histogram_rows(
    indicator_counts: dict[str, Counter[str]],
) -> tuple[list[str], list[list[str]], str]:
    wildcard_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for indicator_id, counts in indicator_counts.items():
        wildcard_id = wildcard_indicator_id(indicator_id)
        wildcard_counts[wildcard_id].update(counts)

    indicator_ids = sorted(wildcard_counts, key=wildcard_indicator_sort_key)
    if not indicator_ids:
        return [], [], build_histogram_resolution_note(1)

    preferred_bins = ["not_present", "present"]
    observed_bins = {indicator_value for counts in wildcard_counts.values() for indicator_value in counts}
    ordered_bins = preferred_bins + sorted(observed_bins - set(preferred_bins))
    max_count = max(
        (
            wildcard_counts[indicator_id].get(indicator_value, 0)
            for indicator_id in indicator_ids
            for indicator_value in ordered_bins
        ),
        default=0,
    )
    resolution = compute_histogram_resolution(max_count)
    table_rows: list[list[str]] = []
    indicator_lines = "<br>".join(f"`{indicator_id}`" for indicator_id in indicator_ids)
    totals_by_indicator = {indicator_id: sum(wildcard_counts[indicator_id].values()) for indicator_id in indicator_ids}
    for indicator_value in ordered_bins:
        count_lines: list[str] = []
        percent_lines: list[str] = []
        bar_lines: list[str] = []
        for indicator_id in indicator_ids:
            bin_count = wildcard_counts[indicator_id].get(indicator_value, 0)
            total_count = totals_by_indicator[indicator_id]
            count_lines.append(str(bin_count))
            percent_lines.append(f"{(bin_count / total_count * 100) if total_count else 0:.1f}%")
            bar_lines.append(render_histogram_bar(bin_count, resolution))
        table_rows.append([
            indicator_value,
            indicator_lines,
            "<br>".join(count_lines),
            "<br>".join(percent_lines),
            "<br>".join(bar_lines),
        ])
    table_rows.append([
        "Total",
        indicator_lines,
        "<br>".join(str(totals_by_indicator[indicator_id]) for indicator_id in indicator_ids),
        "<br>".join("100.0%" for _ in indicator_ids),
        "",
    ])
    return indicator_ids, table_rows, build_histogram_resolution_note(resolution)


def parse_registry_field_value_table(table: dict[str, object]) -> dict[str, str]:
    headers = table.get("headers", [])
    if headers != ["field", "value"]:
        return {}
    return {
        str(row.get("field", "")).strip(): str(row.get("value", "")).strip()
        for row in table.get("rows", [])
    }


def parse_registry_list_value(raw_value: str) -> list[str]:
    return [item.strip().strip("`") for item in str(raw_value).split(",") if item.strip()]


def discover_registry_snapshot_file(snapshot_dir: Path, pattern: str) -> Path | None:
    matches = sorted(snapshot_dir.glob(pattern))
    if not matches:
        return None
    return matches[0]


def load_layer3_description_groups(snapshot_dir: Path) -> dict[str, list[tuple[str, str, str]]]:
    registry_path = discover_registry_snapshot_file(snapshot_dir, "*_Registry_Layer3_Component_*.md")
    if registry_path is None:
        return {}

    tables = collect_markdown_tables(registry_path)
    component_rows = next(
        (
            table.get("rows", [])
            for table in tables
            if {"component_id", "sbo_short_description"}.issubset(set(table.get("headers", [])))
        ),
        [],
    )
    binding_rows = next(
        (
            table.get("rows", [])
            for table in tables
            if {"component_id", "d*1", "d*2", "d*3"}.issubset(set(table.get("headers", [])))
        ),
        [],
    )

    component_display_by_id: dict[str, tuple[str, str]] = {}
    for row in component_rows:
        component_id = str(row.get("component_id", "")).strip()
        display_id = str(row.get("sbo_identifier_shortid", "")).strip() or component_id
        short_description = str(row.get("sbo_short_description", "")).strip()
        if component_id and short_description:
            component_display_by_id[component_id] = (display_id, short_description)

    descriptions_by_dimension: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for row in binding_rows:
        component_id = str(row.get("component_id", "")).strip()
        display_item = component_display_by_id.get(component_id)
        if display_item is None:
            continue
        for aggregate_dimension_id in ("D*1", "D*2", "D*3"):
            concrete_dimension_id = str(row.get(aggregate_dimension_id.lower(), "")).strip()
            if concrete_dimension_id:
                descriptions_by_dimension[aggregate_dimension_id].append(
                    (concrete_dimension_id, display_item[0], display_item[1])
                )

    return {aggregate_dimension_id: descriptions for aggregate_dimension_id, descriptions in descriptions_by_dimension.items()}


def load_indicator_description_groups(snapshot_dir: Path) -> dict[str, list[tuple[str, str]]]:
    layer1_registry_path = discover_registry_snapshot_file(snapshot_dir, "*_Registry_Layer1_Indicator_*.md")
    layer2_registry_path = discover_registry_snapshot_file(snapshot_dir, "*_Registry_Layer2_Dimension_*.md")
    if layer1_registry_path is None or layer2_registry_path is None:
        return {}

    layer1_short_descriptions_by_slot: dict[str, str] = {}
    for table in collect_markdown_tables(layer1_registry_path):
        row_map = parse_registry_field_value_table(table)
        local_slot = row_map.get("local_slot", "").strip()
        short_description = row_map.get("sbo_short_description", "").strip()
        if local_slot and short_description:
            layer1_short_descriptions_by_slot[local_slot] = short_description

    descriptions_by_dimension: dict[str, list[tuple[str, str]]] = defaultdict(list)
    seen_by_dimension: dict[str, set[str]] = defaultdict(set)
    for table in collect_markdown_tables(layer2_registry_path):
        row_map = parse_registry_field_value_table(table)
        dimension_local_id = row_map.get("dimension_local_id", "").strip()
        input_indicators = parse_registry_list_value(row_map.get("input_indicators", ""))
        if not dimension_local_id or not input_indicators:
            continue
        aggregate_dimension_id = f"D*{dimension_local_id[-1]}"
        for indicator_id in input_indicators:
            local_slot = indicator_id.removeprefix("I*").strip()
            wildcard_id = f"I*{local_slot[-1]}" if local_slot else indicator_id
            short_description = layer1_short_descriptions_by_slot.get(local_slot, "")
            if not short_description or wildcard_id in seen_by_dimension[aggregate_dimension_id]:
                continue
            descriptions_by_dimension[aggregate_dimension_id].append((wildcard_id, short_description))
            seen_by_dimension[aggregate_dimension_id].add(wildcard_id)

    return {aggregate_dimension_id: descriptions for aggregate_dimension_id, descriptions in descriptions_by_dimension.items()}


def render_bullet_description_block(label: str, items: list[str]) -> list[str]:
    if not items:
        return []
    if label:
        return [f"{label}:", *items]
    return items


def render_layer3_description_block(items: list[tuple[str, str, str]]) -> list[str]:
    return render_bullet_description_block(
        "Layer 3 SBOs",
        [f"- `{dimension_id}` - `{component_shortid}` {description}" for dimension_id, component_shortid, description in items],
    )


def render_indicator_description_block(items: list[tuple[str, str]]) -> list[str]:
    return render_bullet_description_block("", [f"- `{indicator_id}` {description}" for indicator_id, description in items])


def first_present_value(row: dict[str, str], field_names: list[str]) -> str:
    for field_name in field_names:
        value = str(row.get(field_name, "")).strip()
        if value:
            return value
    return ""


def collect_row_identifier_set(rows: list[dict[str, str]]) -> set[str]:
    identifiers: set[str] = set()
    for row in rows:
        identifier = first_present_value(row, ["submission_id", "participant_id", "response_id"])
        if identifier:
            identifiers.add(identifier)
    return identifiers


def build_component_grade_rows(rows: list[dict[str, str]]) -> list[list[str]]:
    component_grade_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        component_id = str(row.get("component_id", "")).strip() or "(unknown)"
        component_score = str(row.get("component_score", "")).strip()
        if component_score:
            component_grade_counts[component_id][component_score] += 1

    table_rows: list[list[str]] = []
    for component_id in sorted(component_grade_counts):
        counts = component_grade_counts[component_id]
        total = sum(counts.values())
        distribution = ", ".join(f"{grade}={counts[grade]}" for grade in sorted(counts))
        table_rows.append([component_id, str(total), distribution])
    return table_rows


def build_numeric_distribution_rows(values: list[float]) -> list[list[str]]:
    value_counts = Counter(f"{value:.3f}" for value in values)
    total = len(values)
    return [
        [value_label, str(value_counts[value_label]), f"{(value_counts[value_label] / total * 100) if total else 0:.1f}%"]
        for value_label in sorted(value_counts, key=float)
    ]


def generate_report(args: argparse.Namespace) -> Path:
    scored_paths = [path.resolve() for path in args.file_with_scored_texts]
    rows = load_rows_from_paths(scored_paths)
    if not rows:
        raise ValueError(f"No scored rows found in {', '.join(str(path) for path in scored_paths)}")

    assignment_id = derive_assignment_id(args.sbo_manifest_file)
    iteration_label = derive_iteration_label(scored_paths[0], args.iteration_label)
    run_label = derive_run_label(scored_paths[0], args.run_label)
    output_dir = args.output_dir.resolve() if args.output_dir else scored_paths[0].parent.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / derive_output_filename(assignment_id, iteration_label, run_label)

    total_rows = len(rows)
    row_identifiers = collect_row_identifier_set(rows)
    component_ids = sorted({str(row.get("component_id", "")).strip() for row in rows if str(row.get("component_id", "")).strip()})
    grade_scale = parse_grade_scale(rows)
    numeric_scores = [
        parsed_value
        for parsed_value in (parse_float(row.get("component_numeric_score", "")) for row in rows)
        if parsed_value is not None
    ]
    numeric_summary = summarize_numeric(numeric_scores) if numeric_scores else None
    component_grade_rows = build_component_grade_rows(rows)
    layer2_indicator_counts = aggregate_layer2_indicator_counts(scored_paths[0])
    layer3_dimension_counts = aggregate_layer3_dimension_counts(rows)
    snapshot_dir = args.component_registry.resolve().parent
    layer3_description_groups = load_layer3_description_groups(snapshot_dir)
    indicator_description_groups = load_indicator_description_groups(snapshot_dir)
    layer3_dimension_ids = [dimension_id for dimension_id in ("D*1", "D*2", "D*3") if dimension_id in layer3_dimension_counts]
    layer3_dimension_display_ids = [f"`{dimension_id}`" for dimension_id in layer3_dimension_ids]
    layer3_dimension_rows = build_layer3_dimension_rows(layer3_dimension_counts)
    layer3_dimension_histogram_rows, layer3_dimension_histogram_note = build_layer3_dimension_histogram_rows(layer3_dimension_counts)

    metadata_rows = [
        ["assignment_id", assignment_id],
        ["iteration_label", iteration_label],
        ["run_label", run_label],
        ["generated_at_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")],
        ["component_registry", str(args.component_registry.resolve())],
        ["manifest_file", str(args.sbo_manifest_file.resolve())],
        ["scored_csv_count", str(len(scored_paths))],
        ["scored_csvs", "<br>".join(str(path) for path in scored_paths)],
        ["output_file", str(output_path)],
        ["rows_read", str(total_rows)],
        ["distinct_row_units", str(len(row_identifiers))],
        ["component_ids", ", ".join(component_ids)],
    ]

    sections = [
        f"## Layer 3 Grade Award Report: {assignment_id}",
        "",
        "### Metadata",
        render_markdown_table(["field", "value"], metadata_rows),
        "",
    ]

    if numeric_summary is not None:
        sections.extend(
            [
                "### Component Numeric Score Summary",
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
                "### Exact Numeric Distribution",
                render_markdown_table(
                    ["component_numeric_score", "count", "percent"],
                    build_numeric_distribution_rows(numeric_scores),
                ),
                "",
            ]
        )

    if component_grade_rows:
        sections.extend(
            [
                "### Component Totals",
                render_markdown_table(["component_id", "rows", "grade_distribution"], component_grade_rows),
                "",
            ]
        )

    if layer3_dimension_rows or layer3_dimension_histogram_rows:
        sections.extend([
            "## Layer 2/3 Report, Aggregate",
            "",
        ])
        if layer3_dimension_rows:
            sections.extend(
                [
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

    disaggregate_dimension_ids = [
        dimension_id
        for dimension_id in ("D*1", "D*2", "D*3")
        if dimension_id in layer3_dimension_counts or dimension_id in layer2_indicator_counts
    ]
    if disaggregate_dimension_ids:
        sections.extend([
            "## Layer 2/3 Report, Disaggregate",
            "",
        ])
        for dimension_id in disaggregate_dimension_ids:
            sections.extend([f"### `{dimension_id}`"])
            sections.extend(render_layer3_description_block(layer3_description_groups.get(dimension_id, [])))
            sections.append("")
            single_dimension_rows, single_dimension_note = build_single_layer3_dimension_histogram_rows(
                layer3_dimension_counts,
                dimension_id,
            )
            if single_dimension_rows:
                sections.extend(
                    [
                        "#### Aggregate Dimension Histogram",
                        render_markdown_table(["Bin", "Count", "%", "Bar"], single_dimension_rows),
                        single_dimension_note,
                        "",
                    ]
                )

            indicator_ids, layer2_histogram_rows, layer2_histogram_note = build_layer2_indicator_histogram_rows(
                layer2_indicator_counts.get(dimension_id, {})
            )
            if indicator_ids:
                sections.extend(
                    [
                        f"#### `{dimension_id}` Indicator Histogram",
                        "Indicator order: " + ", ".join(f"`{indicator_id}`" for indicator_id in indicator_ids),
                    ]
                )
                sections.extend(render_indicator_description_block(indicator_description_groups.get(dimension_id, [])))
                sections.extend(
                    [
                        "",
                        render_markdown_table(["Bin", "Indicator", "Count", "%", "Bar"], layer2_histogram_rows),
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