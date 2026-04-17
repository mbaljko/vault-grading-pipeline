#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


DEFAULT_INPUT_ROOT = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/input"
)
DEFAULT_OUTPUT_PATH = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/JSON_reports/json_analysis_report.md"
)
PRIMARY_DATASET_DIR_NAMES = (
    "student_data_all_MINUS_SAS",
    "student_data_SAS_SecM",
    "student_data_SAS_SecO",
)
DIMENSIONS = (
    "B-1",
    "B-2",
    "B-3",
    "C-1",
    "C-2",
    "C-3",
    "D-1",
    "D-2",
    "D-3",
)
DIMENSION_GROUPS = {
    "B": ("B-1", "B-2", "B-3"),
    "C": ("C-1", "C-2", "C-3"),
    "D": ("D-1", "D-2", "D-3"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate markdown analysis reports over promoted PPS2 JSON files.",
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=DEFAULT_INPUT_ROOT,
        help="Root directory containing the promoted JSON dataset directories.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Markdown report path to write.",
    )
    return parser.parse_args()


def load_promoted_json_records(input_root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for dir_name in PRIMARY_DATASET_DIR_NAMES:
        directory = input_root / dir_name
        if not directory.exists():
            continue
        for json_path in sorted(directory.glob("*.json")):
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            records.append(
                {
                    "path": json_path,
                    "student_pool": payload.get("STUDENT_POOL", ""),
                    "payload": payload,
                }
            )
    return records


def build_file_count_analysis(records: list[dict[str, object]]) -> list[str]:
    counts_by_pool: dict[str, int] = defaultdict(int)
    for record in records:
        student_pool = str(record.get("student_pool") or "")
        if student_pool:
            counts_by_pool[student_pool] += 1

    lines = [
        "## File Count",
        "",
        "### All data",
        "",
        f"- Number of files: {len(records)}",
    ]

    for student_pool in sorted(counts_by_pool):
        lines.extend(
            [
                "",
                f"### {student_pool}",
                "",
                f"- Number of files: {counts_by_pool[student_pool]}",
            ]
        )

    return lines


def split_records_by_student_pool(records: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped_records: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        student_pool = str(record.get("student_pool") or "")
        if student_pool:
            grouped_records[student_pool].append(record)
    return dict(grouped_records)


def build_e1_dimension_overview_table(records: list[dict[str, object]]) -> list[str]:
    counts_by_dimension: dict[str, dict[str, int]] = {}
    for dimension in DIMENSIONS:
        counts_by_dimension[dimension] = {"2": 0, "1": 0, "0": 0}
        for record in records:
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            health_value = str(payload.get(f"{dimension}_indicator_health_srcE1") or "")
            if health_value in counts_by_dimension[dimension]:
                counts_by_dimension[dimension][health_value] += 1

    header_row = "| Check Status | " + " | ".join(DIMENSIONS) + " |"
    divider_row = "| --- | " + " | ".join("---:" for _ in DIMENSIONS) + " |"

    passed_row = "| Passed (health=2) | " + " | ".join(
        str(counts_by_dimension[dimension]["2"]) for dimension in DIMENSIONS
    ) + " |"
    multiple_row = "| Multiple Selected (health=1) | " + " | ".join(
        str(counts_by_dimension[dimension]["1"]) for dimension in DIMENSIONS
    ) + " |"
    none_row = "| None Selected (health=0) | " + " | ".join(
        str(counts_by_dimension[dimension]["0"]) for dimension in DIMENSIONS
    ) + " |"
    total_row = "| Total | " + " | ".join(str(len(records)) for _ in DIMENSIONS) + " |"
    error_rate_row = "| % Error Rate | " + " | ".join(
        f"{(((counts_by_dimension[dimension]['1'] + counts_by_dimension[dimension]['0']) / len(records)) * 100) if records else 0.0:.1f}%"
        for dimension in DIMENSIONS
    ) + " |"

    return [header_row, divider_row, passed_row, multiple_row, none_row, total_row, error_rate_row]


def build_e1_dimension_overview_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## E1 Categorization of Dimension Devt : Type Uniqueness",
        "",
        "### All data",
        "",
        *build_e1_dimension_overview_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(["", f"### {student_pool}", "", *build_e1_dimension_overview_table(pool_records)])

    return lines


def build_tagset_health_by_dimension_table(records: list[dict[str, object]]) -> list[str]:
    counts_by_dimension: dict[str, dict[str, int]] = {}
    for dimension in DIMENSIONS:
        counts_by_dimension[dimension] = {"2": 0, "0": 0}
        for record in records:
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            health_value = str(payload.get(f"{dimension}_indicator_health_srcBCD2") or "")
            if health_value in counts_by_dimension[dimension]:
                counts_by_dimension[dimension][health_value] += 1

    header_row = "| Health Status | " + " | ".join(DIMENSIONS) + " |"
    divider_row = "| --- | " + " | ".join("---:" for _ in DIMENSIONS) + " |"
    health_2_row = "| Extracted (health=2) | " + " | ".join(
        str(counts_by_dimension[dimension]["2"]) for dimension in DIMENSIONS
    ) + " |"
    health_0_row = "| Not Extracted (health=0) | " + " | ".join(
        str(counts_by_dimension[dimension]["0"]) for dimension in DIMENSIONS
    ) + " |"
    total_row = "| Total | " + " | ".join(str(len(records)) for _ in DIMENSIONS) + " |"
    extracted_rate_row = "| % Extracted | " + " | ".join(
        f"{((counts_by_dimension[dimension]['2'] / len(records)) * 100) if records else 0.0:.1f}%"
        for dimension in DIMENSIONS
    ) + " |"
    not_extracted_rate_row = "| % Not Extracted | " + " | ".join(
        f"{((counts_by_dimension[dimension]['0'] / len(records)) * 100) if records else 0.0:.1f}%"
        for dimension in DIMENSIONS
    ) + " |"

    return [
        header_row,
        divider_row,
        health_2_row,
        health_0_row,
        total_row,
        extracted_rate_row,
        not_extracted_rate_row,
    ]


def build_tagset_health_by_dimension_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## indicator_health_srcBCD2",
        "",
        "### All data",
        "",
        *build_tagset_health_by_dimension_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(["", f"### {student_pool}", "", *build_tagset_health_by_dimension_table(pool_records)])

    return lines


def build_e2_status_table(records: list[dict[str, object]]) -> list[str]:
    counts_by_tension_dimensions = {count: 0 for count in range(len(DIMENSIONS) + 1)}

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        tension_count = sum(1 for dimension in DIMENSIONS if str(payload.get(f"{dimension}-status") or "") == "in tension")
        counts_by_tension_dimensions[tension_count] += 1

    lines = [
        "| Tension dimensions identified | Submission Count | % of Submissions |",
        "| ---: | ---: | ---: |",
    ]
    for tension_count in range(2, -1, -1):
        submission_count = counts_by_tension_dimensions[tension_count]
        percent = (submission_count / len(records)) * 100 if records else 0.0
        lines.append(f"| {tension_count} | {submission_count} | {percent:.1f}% |")
    lines.append(f"| Total | {len(records)} | 100.0% |")
    return lines


def build_e2_status_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## E2-based status",
        "",
        "### All data",
        "",
        *build_e2_status_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(["", f"### {student_pool}", "", *build_e2_status_table(pool_records)])

    return lines


def build_devt_tagset_tension_table(records: list[dict[str, object]]) -> list[str]:
    counts_by_tension_dimensions = {count: 0 for count in range(len(DIMENSIONS) + 1)}

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        tension_count = sum(1 for dimension in DIMENSIONS if str(payload.get(f"{dimension}-devt_tagset") or "") == "tension")
        counts_by_tension_dimensions[tension_count] += 1

    lines = [
        "| Tension dimensions identified | Submission Count | % of Submissions |",
        "| ---: | ---: | ---: |",
    ]
    for tension_count in range(len(DIMENSIONS), -1, -1):
        submission_count = counts_by_tension_dimensions[tension_count]
        percent = (submission_count / len(records)) * 100 if records else 0.0
        lines.append(f"| {tension_count} | {submission_count} | {percent:.1f}% |")
    lines.append(f"| Total | {len(records)} | 100.0% |")
    return lines


def build_devt_tagset_tension_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## devt_tagset Tension",
        "",
        "### All data",
        "",
        *build_devt_tagset_tension_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(["", f"### {student_pool}", "", *build_devt_tagset_tension_table(pool_records)])

    return lines


def build_tension_correlation_table(records: list[dict[str, object]]) -> list[str]:
    categories = (
        "No tension indicated",
        "Tension indicated from one source (E2 only)",
        "Tension reinforced (both sources)",
        "Tension conflict (tagset says tension but not E2)",
    )
    counts_by_dimension = {
        dimension: {category: 0 for category in categories}
        for dimension in DIMENSIONS
    }

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        for dimension in DIMENSIONS:
            e2_tension = str(payload.get(f"{dimension}-status") or "") == "in tension"
            tagset_tension = str(payload.get(f"{dimension}-devt_tagset") or "") == "tension"

            if e2_tension and tagset_tension:
                category = "Tension reinforced (both sources)"
            elif e2_tension:
                category = "Tension indicated from one source (E2 only)"
            elif tagset_tension:
                category = "Tension conflict (tagset says tension but not E2)"
            else:
                category = "No tension indicated"
            counts_by_dimension[dimension][category] += 1

    lines = [
        "| Category | " + " | ".join(DIMENSIONS) + " |",
        "| --- | " + " | ".join("---:" for _ in DIMENSIONS) + " |",
    ]
    for category in categories:
        lines.append(
            "| " + category + " | " + " | ".join(
                str(counts_by_dimension[dimension][category]) for dimension in DIMENSIONS
            ) + " |"
        )
    lines.append("| Total | " + " | ".join(str(len(records)) for _ in DIMENSIONS) + " |")
    return lines


def build_tension_correlation_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## Tension correlation - E2 vs tagset",
        "",
        "### All data",
        "",
        *build_tension_correlation_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(["", f"### {student_pool}", "", *build_tension_correlation_table(pool_records)])

    return lines


def count_group_indicator_population(payload: dict[str, object], group_dimensions: tuple[str, ...], suffix: str) -> int:
    return sum(1 for dimension in group_dimensions if str(payload.get(f"{dimension}{suffix}") or "").strip())


def build_group_indicator_population_table(records: list[dict[str, object]], suffix: str) -> list[str]:
    counts_by_group = {
        group_name: {count: 0 for count in range(4)}
        for group_name in DIMENSION_GROUPS
    }

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        for group_name, group_dimensions in DIMENSION_GROUPS.items():
            populated_count = count_group_indicator_population(payload, group_dimensions, suffix)
            counts_by_group[group_name][populated_count] += 1

    lines = [
        "| Populated indicators (n of 3) | B | C | D | B+C+D |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    aggregate_total = len(records) * len(DIMENSION_GROUPS)
    for populated_count in range(4):
        row_cells: list[str] = []
        for group_name in ("B", "C", "D"):
            count = counts_by_group[group_name][populated_count]
            percent = (count / len(records)) * 100 if records else 0.0
            row_cells.append(f"{count} ({percent:.1f}%)")
        aggregate_count = sum(counts_by_group[group_name][populated_count] for group_name in ("B", "C", "D"))
        aggregate_percent = (aggregate_count / aggregate_total) * 100 if aggregate_total else 0.0
        row_cells.append(f"{aggregate_count} ({aggregate_percent:.1f}%)")
        lines.append(f"| {populated_count} | " + " | ".join(row_cells) + " |")
    lines.append(
        "| Total | "
        + " | ".join([str(len(records)) for _ in range(3)] + [str(aggregate_total)])
        + " |"
    )
    return lines


def build_group_indicator_population_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## B/C/D indicator population",
        "",
        "### All data",
        "",
        "#### devt",
        "",
        *build_group_indicator_population_table(records, "-devt"),
        "",
        "#### devt_tagset",
        "",
        *build_group_indicator_population_table(records, "-devt_tagset"),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(
            [
                "",
                f"### {student_pool}",
                "",
                "#### devt",
                "",
                *build_group_indicator_population_table(pool_records, "-devt"),
                "",
                "#### devt_tagset",
                "",
                *build_group_indicator_population_table(pool_records, "-devt_tagset"),
            ]
        )

    return lines


def normalize_devt_value(value: object) -> str:
    raw_value = str(value or "").strip().lower()
    if raw_value == "shift":
        return "shift"
    if raw_value in {"cont/reinf", "cont-reinf", "continuity-reinforcement", "continuity/reinforcement"}:
        return "cont-reinf"
    return "other"


def build_shift_ratio_bin_labels() -> tuple[str, ...]:
    labels = []
    for bin_index in range(4):
        lower = bin_index / 4
        upper = (bin_index + 1) / 4
        labels.append(f"Q{bin_index + 1} ({lower:.2f}-{upper:.2f})")
    labels.append("No shift/cont-reinf")
    return tuple(labels)


def assign_shift_ratio_bin(shift_count: int, cont_reinf_count: int) -> str:
    total = shift_count + cont_reinf_count
    if total == 0:
        return "No shift/cont-reinf"

    shift_ratio = shift_count / total
    if shift_ratio >= 1.0:
        return "Q4 (0.75-1.00)"
    bin_index = int(shift_ratio * 4)
    lower = bin_index / 4
    upper = (bin_index + 1) / 4
    return f"Q{bin_index + 1} ({lower:.2f}-{upper:.2f})"


def build_shift_vs_cont_reinf_distribution_table(records: list[dict[str, object]]) -> list[str]:
    categories = build_shift_ratio_bin_labels()
    counts_by_category = {category: 0 for category in categories}

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        shift_count = 0
        cont_reinf_count = 0
        for group_dimensions in DIMENSION_GROUPS.values():
            for dimension in group_dimensions:
                normalized_value = normalize_devt_value(payload.get(f"{dimension}-devt"))
                if normalized_value == "shift":
                    shift_count += 1
                elif normalized_value == "cont-reinf":
                    cont_reinf_count += 1
        category = assign_shift_ratio_bin(shift_count, cont_reinf_count)
        counts_by_category[category] += 1

    lines = [
        "| Shift ratio quartile | B+C+D |",
        "| --- | ---: |",
    ]
    for category in categories:
        count = counts_by_category[category]
        percent = (count / len(records)) * 100 if records else 0.0
        lines.append(f"| {category} | {count} ({percent:.1f}%) |")
    lines.append(f"| Total | {len(records)} |")
    return lines


def build_shift_vs_cont_reinf_distribution_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## B/C/D shift vs cont-reinf distribution - Quartiles",
        "",
        "### All data",
        "",
        *build_shift_vs_cont_reinf_distribution_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(["", f"### {student_pool}", "", *build_shift_vs_cont_reinf_distribution_table(pool_records)])

    return lines


def build_report(records: list[dict[str, object]]) -> str:
    lines = [
        "# JSON Analysis Report",
        "",
        "Primary promoted JSON datasets only: sample-overlay and buffer directories are excluded.",
        "",
    ]
    lines.extend(build_file_count_analysis(records))
    lines.extend(["", *build_e1_dimension_overview_analysis(records)])
    lines.extend(["", *build_tagset_health_by_dimension_analysis(records)])
    lines.extend(["", *build_e2_status_analysis(records)])
    lines.extend(["", *build_devt_tagset_tension_analysis(records)])
    lines.extend(["", *build_tension_correlation_analysis(records)])
    lines.extend(["", *build_group_indicator_population_analysis(records)])
    lines.extend(["", *build_shift_vs_cont_reinf_distribution_analysis(records)])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    records = load_promoted_json_records(args.input_root)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(build_report(records), encoding="utf-8")
    print(f"Wrote JSON analysis report to {args.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())