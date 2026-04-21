#!/usr/bin/env python3
"""Generate a markdown report with descriptive statistics for Layer 1 indicator grade awards."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from generate_rubric_and_manifest_from_indicator_registry import collect_markdown_tables


ITERATION_RE = re.compile(r"\b(iter\d+)\b", re.IGNORECASE)
RUN_RE = re.compile(r"\b(run\d+)\b", re.IGNORECASE)
INDICATOR_ID_RE = re.compile(r"^I(\d+)$")
WILDCARD_INDICATOR_ID_RE = re.compile(r"^I\*(\d)$")
MAX_HISTOGRAM_BAR_WIDTH = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a markdown report with descriptive statistics for Layer 1 indicator grade awards."
    )
    parser.add_argument("--indicator-registry", type=Path, required=True)
    parser.add_argument("--sbo-manifest-file", type=Path, required=True)
    parser.add_argument("--file-with-scored-texts", type=Path, required=True, action="append")
    parser.add_argument("--component-id", action="append")
    parser.add_argument("--output-dir", type=Path, required=False)
    parser.add_argument("--iteration-label", type=str, required=False)
    parser.add_argument("--run-label", type=str, required=False)
    parser.add_argument("--comparison-scope", type=str, required=False, help=argparse.SUPPRESS)
    parser.add_argument("--baseline-iteration-label", type=str, required=False, help=argparse.SUPPRESS)
    parser.add_argument("--baseline-run-label", type=str, required=False, help=argparse.SUPPRESS)
    return parser.parse_args()


def derive_assignment_id(path: Path) -> str:
    match = re.match(r"^([A-Za-z0-9]+)_Layer1_", path.name)
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
        f"I_{assignment_id}_Layer1_grade_award_report_"
        f"{sanitize_label(iteration_label)}_{sanitize_label(run_label)}.md"
    )


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


def resolve_scored_csv_paths(path_inputs: list[Path]) -> list[Path]:
    csv_paths: list[Path] = []
    seen_paths: set[Path] = set()
    for path_input in path_inputs:
        resolved = path_input.resolve()
        candidates: list[Path]
        if resolved.is_dir():
            candidates = sorted(resolved.glob("*_Layer1_indicator_scoring_*_output.csv"))
        elif resolved.is_file():
            candidates = [resolved]
        else:
            raise FileNotFoundError(f"Scored-text path not found: {resolved}")
        for candidate in candidates:
            if candidate.name.endswith("-wide.csv"):
                continue
            if candidate in seen_paths:
                continue
            seen_paths.add(candidate)
            csv_paths.append(candidate)
    return csv_paths


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_rows_from_paths(csv_paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for csv_path in csv_paths:
        rows.extend(load_rows(csv_path))
    return rows


def filter_component_rows(rows: list[dict[str, str]], component_ids: list[str]) -> list[dict[str, str]]:
    normalized = {component_id.strip() for component_id in component_ids if component_id and component_id.strip()}
    if not normalized:
        return rows
    return [row for row in rows if str(row.get("component_id", "")).strip() in normalized]


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


def parse_registry_field_value_table(table: dict[str, object]) -> dict[str, str]:
    headers = table.get("headers", [])
    if headers != ["field", "value"]:
        return {}
    return {
        str(row.get("field", "")).strip(): str(row.get("value", "")).strip()
        for row in table.get("rows", [])
    }


def load_indicator_descriptions(registry_path: Path) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for table in collect_markdown_tables(registry_path):
        row_map = parse_registry_field_value_table(table)
        indicator_id = row_map.get("indicator_id", "").strip()
        local_slot = row_map.get("local_slot", "").strip()
        short_description = row_map.get("sbo_short_description", "").strip()
        wildcard_id = ""
        if indicator_id:
            wildcard_id = wildcard_indicator_id(indicator_id)
        elif local_slot:
            wildcard_id = wildcard_indicator_id(f"I{local_slot}")
        if wildcard_id and short_description and wildcard_id not in descriptions:
            descriptions[wildcard_id] = short_description
    return descriptions


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


def aggregate_evidence_counts(rows: list[dict[str, str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        evidence_status = str(row.get("evidence_status", "")).strip()
        if evidence_status:
            counts[evidence_status] += 1
    return counts


def aggregate_wildcard_indicator_counts(rows: list[dict[str, str]]) -> dict[str, Counter[str]]:
    aggregate_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        indicator_id = str(row.get("indicator_id", "")).strip()
        evidence_status = str(row.get("evidence_status", "")).strip()
        if not indicator_id or not evidence_status:
            continue
        aggregate_counts[wildcard_indicator_id(indicator_id)][evidence_status] += 1
    return {
        indicator_id: counts
        for indicator_id, counts in sorted(aggregate_counts.items(), key=lambda item: wildcard_indicator_sort_key(item[0]))
    }


def aggregate_component_indicator_counts(rows: list[dict[str, str]]) -> dict[str, dict[str, Counter[str]]]:
    aggregate_counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for row in rows:
        component_id = str(row.get("component_id", "")).strip()
        indicator_id = str(row.get("indicator_id", "")).strip()
        evidence_status = str(row.get("evidence_status", "")).strip()
        if not component_id or not indicator_id or not evidence_status:
            continue
        aggregate_counts[component_id][indicator_id][evidence_status] += 1
    return {
        component_id: {
            indicator_id: counts
            for indicator_id, counts in sorted(indicator_counts.items(), key=lambda item: indicator_sort_key(item[0]))
        }
        for component_id, indicator_counts in sorted(aggregate_counts.items())
    }


def build_histogram_rows(counts: Counter[str]) -> tuple[list[list[str]], str]:
    total = sum(counts.values())
    preferred_bins = ["not_present", "present"]
    ordered_bins = [item for item in preferred_bins if item in counts]
    ordered_bins.extend(item for item in sorted(counts) if item not in ordered_bins)
    resolution = compute_histogram_resolution(max((counts[item] for item in ordered_bins), default=0))
    rows = [
        [
            item,
            str(counts[item]),
            f"{(counts[item] / total * 100) if total else 0:.1f}%",
            render_histogram_bar(counts[item], resolution),
        ]
        for item in ordered_bins
    ]
    rows.append(["Total", str(total), "100.0%", ""])
    return rows, build_histogram_resolution_note(resolution)


def build_component_indicator_sections(
    indicator_counts: dict[str, Counter[str]],
    indicator_descriptions: dict[str, str],
) -> list[str]:
    sections: list[str] = []
    for indicator_id, counts in indicator_counts.items():
        histogram_rows, histogram_note = build_histogram_rows(counts)
        description = indicator_descriptions.get(wildcard_indicator_id(indicator_id), "")
        sections.extend([
            f"#### `{indicator_id}`",
        ])
        if description:
            sections.append(f"- {description}")
        sections.extend([
            "",
            render_markdown_table(["evidence_status", "count", "%", "bar"], histogram_rows),
            histogram_note,
            "",
        ])
    return sections


def generate_report(args: argparse.Namespace) -> Path:
    scored_paths = resolve_scored_csv_paths(args.file_with_scored_texts)
    if not scored_paths:
        raise ValueError("No Layer 1 combined scored CSVs were found.")

    rows = load_rows_from_paths(scored_paths)
    rows = filter_component_rows(rows, args.component_id or [])
    if not rows:
        raise ValueError("No Layer 1 scored rows matched the requested component scope.")

    assignment_id = derive_assignment_id(args.sbo_manifest_file)
    iteration_label = derive_iteration_label(scored_paths[0], args.iteration_label)
    run_label = derive_run_label(scored_paths[0], args.run_label)
    output_dir = args.output_dir.resolve() if args.output_dir else scored_paths[0].parent.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / derive_output_filename(assignment_id, iteration_label, run_label)

    row_identifiers = collect_row_identifier_set(rows)
    component_ids = sorted({str(row.get("component_id", "")).strip() for row in rows if str(row.get("component_id", "")).strip()})
    evidence_counts = aggregate_evidence_counts(rows)
    wildcard_indicator_counts = aggregate_wildcard_indicator_counts(rows)
    component_indicator_counts = aggregate_component_indicator_counts(rows)
    indicator_descriptions = load_indicator_descriptions(args.indicator_registry.resolve())

    metadata_rows = [
        ["assignment_id", assignment_id],
        ["iteration_label", iteration_label],
        ["run_label", run_label],
        ["generated_at_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")],
        ["indicator_registry", str(args.indicator_registry.resolve())],
        ["manifest_file", str(args.sbo_manifest_file.resolve())],
        ["scored_csv_count", str(len(scored_paths))],
        ["scored_csvs", "<br>".join(str(path) for path in scored_paths)],
        ["output_file", str(output_path)],
        ["rows_read", str(len(rows))],
        ["distinct_row_units", str(len(row_identifiers))],
        ["component_ids", ", ".join(component_ids)],
    ]

    overall_rows, overall_note = build_histogram_rows(evidence_counts)
    sections = [
        f"## Layer 1 Grade Award Report: {assignment_id}",
        "",
        "### Metadata",
        "",
        render_markdown_table(["field", "value"], metadata_rows),
        "",
        "### Indicator Results",
        "",
        "#### All Indicators",
        "",
        render_markdown_table(["evidence_status", "count", "%", "bar"], overall_rows),
        overall_note,
        "",
    ]

    for wildcard_indicator, counts in wildcard_indicator_counts.items():
        histogram_rows, histogram_note = build_histogram_rows(counts)
        sections.append(f"#### `{wildcard_indicator}`")
        description = indicator_descriptions.get(wildcard_indicator, "")
        if description:
            sections.append(f"- {description}")
        sections.extend([
            "",
            render_markdown_table(["evidence_status", "count", "%", "bar"], histogram_rows),
            histogram_note,
            "",
        ])

    if component_indicator_counts:
        sections.extend([
            "## Component Details",
            "",
        ])
        for component_id, indicator_counts in component_indicator_counts.items():
            sections.extend([
                f"### `{component_id}`",
                "",
            ])
            sections.extend(build_component_indicator_sections(indicator_counts, indicator_descriptions))

    output_path.write_text("\n".join(sections), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    output_path = generate_report(args)
    print(output_path)


if __name__ == "__main__":
    main()