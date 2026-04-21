#!/usr/bin/env python3
"""Generate a markdown report with descriptive statistics for Layer 2 dimension results."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from generate_rubric_and_manifest_from_indicator_registry import collect_markdown_tables


ITERATION_RE = re.compile(r"\b(iter\d+)\b", re.IGNORECASE)
RUN_RE = re.compile(r"\b(run\d+)\b", re.IGNORECASE)
DIMENSION_ID_RE = re.compile(r"^D\d+(\d)$")
INDICATOR_ID_RE = re.compile(r"^I(\d+)$")
WILDCARD_INDICATOR_ID_RE = re.compile(r"^I\*(\d)$")
MAX_HISTOGRAM_BAR_WIDTH = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a markdown report with descriptive statistics for Layer 2 dimension results."
    )
    parser.add_argument("--dimension-registry", dest="dimension_registry", type=Path)
    parser.add_argument("--indicator-registry", dest="dimension_registry", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--sbo-manifest-file", type=Path, required=True)
    parser.add_argument("--file-with-scored-texts", type=Path, required=True, action="append")
    parser.add_argument("--component-id", action="append", help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=Path, required=False)
    parser.add_argument("--iteration-label", type=str, required=False)
    parser.add_argument("--run-label", type=str, required=False)
    args = parser.parse_args()
    if args.dimension_registry is None:
        parser.error("one of --dimension-registry or --indicator-registry is required")
    return args


def derive_assignment_id(path: Path) -> str:
    match = re.match(r"^([A-Za-z0-9]+)_Layer2_", path.name)
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
        f"I_{assignment_id}_Layer2_grade_award_report_"
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
        raw_scale = str(row.get("dimension_evidence_scale", "")).strip()
        if raw_scale:
            return [item.strip() for item in raw_scale.split(",") if item.strip()]
    return []


def parse_json_object(raw_value: str) -> dict[str, str]:
    stripped = str(raw_value).strip()
    if not stripped:
        return {}
    decoded = json.loads(stripped)
    if not isinstance(decoded, dict):
        raise ValueError("Expected JSON object.")
    return {str(key): str(value) for key, value in decoded.items()}


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


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


def wildcard_dimension_id(dimension_id: str) -> str:
    match = DIMENSION_ID_RE.match(dimension_id)
    if match:
        return f"D*{match.group(1)}"
    return dimension_id


def wildcard_dimension_sort_key(dimension_id: str) -> tuple[int, str]:
    match = re.match(r"^D\*(\d)$", dimension_id)
    if match:
        return int(match.group(1)), dimension_id
    return 10**9, dimension_id


def indicator_sort_key(indicator_id: str) -> tuple[int, str]:
    match = INDICATOR_ID_RE.match(indicator_id)
    if match:
        return int(match.group(1)), indicator_id
    return 10**9, indicator_id


def wildcard_indicator_id(indicator_id: str) -> str:
    match = re.match(r"^I\d*(\d)$", indicator_id)
    if match:
        return f"I*{match.group(1)}"
    return indicator_id


def wildcard_indicator_sort_key(indicator_id: str) -> tuple[int, str]:
    match = WILDCARD_INDICATOR_ID_RE.match(indicator_id)
    if match:
        return int(match.group(1)), indicator_id
    return indicator_sort_key(indicator_id)


def aggregate_dimension_counts(rows: list[dict[str, str]]) -> dict[str, Counter[str]]:
    aggregate_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        dimension_id = str(row.get("dimension_id", "")).strip()
        result_value = str(row.get("evidence_status", "")).strip()
        if not dimension_id or not result_value:
            continue
        aggregate_counts[wildcard_dimension_id(dimension_id)][result_value] += 1
    return {
        dimension_id: counts
        for dimension_id, counts in sorted(aggregate_counts.items(), key=lambda item: wildcard_dimension_sort_key(item[0]))
    }


def aggregate_indicator_counts(rows: list[dict[str, str]]) -> dict[str, dict[str, Counter[str]]]:
    aggregate_counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for row in rows:
        dimension_id = str(row.get("dimension_id", "")).strip()
        if not dimension_id:
            continue
        aggregate_dimension_id = wildcard_dimension_id(dimension_id)
        indicator_values = parse_json_object(row.get("source_indicator_values_json", ""))
        for indicator_id, indicator_value in indicator_values.items():
            aggregate_counts[aggregate_dimension_id][indicator_id][indicator_value] += 1
    return {
        aggregate_dimension_id: {
            indicator_id: counts
            for indicator_id, counts in sorted(indicator_counts.items(), key=lambda item: indicator_sort_key(item[0]))
        }
        for aggregate_dimension_id, indicator_counts in sorted(aggregate_counts.items(), key=lambda item: wildcard_dimension_sort_key(item[0]))
    }


def build_dimension_result_sections(
    aggregate_counts: dict[str, Counter[str]],
    grade_scale: list[str],
) -> list[str]:
    all_counts: Counter[str] = Counter()
    for counts in aggregate_counts.values():
        all_counts.update(counts)

    groups: list[tuple[str, Counter[str]]] = []
    if all_counts:
        groups.append(("All Dimensions", all_counts))
    groups.extend((dimension_id, aggregate_counts[dimension_id]) for dimension_id in aggregate_counts)

    sections: list[str] = []
    for heading, counts in groups:
        total = sum(counts.values())
        ordered_scores = [score for score in grade_scale if score in counts]
        ordered_scores.extend(score for score in sorted(counts) if score not in ordered_scores)
        resolution = compute_histogram_resolution(max((counts[score] for score in ordered_scores), default=0))
        table_rows = [
            [
                score,
                str(counts[score]),
                f"{(counts[score] / total * 100) if total else 0:.1f}%",
                render_histogram_bar(counts[score], resolution),
            ]
            for score in ordered_scores
        ]
        table_rows.append(["Total", str(total), "100.0%", ""])
        sections.extend(
            [
                f"#### {heading}" if heading == "All Dimensions" else f"#### `{heading}`",
                render_markdown_table(["evidence_status", "count", "%", "bar"], table_rows),
                build_histogram_resolution_note(resolution),
                "",
            ]
        )
    return sections


def build_layer1_indicator_histogram_rows(
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

    return {
        aggregate_dimension_id: descriptions
        for aggregate_dimension_id, descriptions in descriptions_by_dimension.items()
    }


def render_bullet_description_block(label: str, items: list[str]) -> list[str]:
    if not items:
        return []
    if label:
        return [f"{label}:", *items]
    return items


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
    aggregated_dimension_counts = aggregate_dimension_counts(rows)
    aggregated_indicator_counts = aggregate_indicator_counts(rows)
    dimension_result_sections = build_dimension_result_sections(aggregated_dimension_counts, grade_scale)
    snapshot_dir = args.dimension_registry.resolve().parent
    indicator_description_groups = load_indicator_description_groups(snapshot_dir)

    metadata_rows = [
        ["assignment_id", assignment_id],
        ["iteration_label", iteration_label],
        ["run_label", run_label],
        ["generated_at_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")],
        ["dimension_registry", str(args.dimension_registry.resolve())],
        ["manifest_file", str(args.sbo_manifest_file.resolve())],
        ["scored_csv_count", str(len(scored_paths))],
        ["scored_csvs", "<br>".join(str(path) for path in scored_paths)],
        ["output_file", str(output_path)],
        ["rows_read", str(total_rows)],
        ["distinct_row_units", str(len(row_identifiers))],
        ["component_ids", ", ".join(component_ids)],
    ]

    sections = [
        f"## Layer 2 Grade Award Report: {assignment_id}",
        "",
        "### Metadata",
        render_markdown_table(["field", "value"], metadata_rows),
        "",
    ]

    if dimension_result_sections:
        sections.extend([
            "### Dimension Results",
            "",
        ])
        sections.extend(dimension_result_sections)

    if aggregated_indicator_counts:
        sections.extend([
            "## Layer 1 Details",
            "",
        ])
        for dimension_id in sorted(aggregated_indicator_counts, key=wildcard_dimension_sort_key):
            indicator_ids, histogram_rows, histogram_note = build_layer1_indicator_histogram_rows(
                aggregated_indicator_counts.get(dimension_id, {})
            )
            if not indicator_ids:
                continue
            sections.extend([
                f"### `{dimension_id}`",
                "Indicator order: " + ", ".join(f"`{indicator_id}`" for indicator_id in indicator_ids),
            ])
            sections.extend(render_indicator_description_block(indicator_description_groups.get(dimension_id, [])))
            sections.extend([
                "",
                render_markdown_table(["Bin", "Indicator", "Count", "%", "Bar"], histogram_rows),
                histogram_note,
                "",
            ])

    output_path.write_text("\n".join(sections), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    output_path = generate_report(args)
    print(output_path)


if __name__ == "__main__":
    main()