#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re

from pps1_slot_populator import select_section_dimensions


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
CONVERGED_VALUE_ORDER = (
    "shift",
    "cont-reinf",
    "intro",
    "tension",
    "conflicting",
)
CONFLICTED_VALUE_LABELS = (
    "cont-reinf+intro",
    "cont-reinf+shift",
    "intro+cont-reinf",
    "intro+shift",
    "shift+cont-reinf",
    "shift+intro",
)
CONVERGED_HEALTH_ORDER = (
    "asserted",
    "asserted-alongside-intro",
    "reinforced",
    "conflict",
)
SECTION1_SLOT_FIELDS = ("Sec1_TS1_dim", "Sec1_TS2_dim", "Sec1_TS3_dim")
SECTION2_SLOT_FIELDS = ("Sec2_V1_dim", "Sec2_V2_dim")
SECTION3_SLOT_FIELDS = ("Sec4_Slot1_dim", "Sec4_Slot2_dim", "Sec4_Slot3_dim")
ALL_SLOT_FIELDS = SECTION1_SLOT_FIELDS + SECTION2_SLOT_FIELDS + SECTION3_SLOT_FIELDS
SLOT_WORD_COUNT_FIELDS = {
    "TS1": ("Sec1_TS1_PPP", "Sec1_TS1_PPS1"),
    "TS2": ("Sec1_TS2_PPP", "Sec1_TS2_PPS1"),
    "TS3": ("Sec1_TS3_PPP", "Sec1_TS3_PPS1"),
    "V1": ("Sec2_V1_PPP", "Sec2_V1_PPS1"),
    "V2": ("Sec2_V2_PPP", "Sec2_V2_PPS1"),
    "Slot1": ("Sec4_Slot1_PPS1",),
    "Slot2": ("Sec4_Slot2_PPS1",),
    "Slot3": ("Sec4_Slot3_PPS1",),
}
SLOT_WORD_COUNT_ORDER = tuple(SLOT_WORD_COUNT_FIELDS)
HUMAN_FRIENDLY_TO_SHORT_DIMENSION = {
    "Institutional structures and organisational arrangements": "B-1",
    "Responsibility and accountability distribution": "B-2",
    "Institutional influence, constraint, and authority": "B-3",
    "Justice, accessibility, and harm": "C-1",
    "Assumptions about neutrality, efficiency, fairness, or objectivity": "C-2",
    "Criteria for identifying harm, exclusion, or accessibility barriers": "C-3",
    "Human responsibility vs AI-mediated delegation of responsibility": "D-1",
    "AI-mediated oversight, uncertainty, and verification practices": "D-2",
    "Role of tools or AI systems in shaping professional judgement": "D-3",
}


@dataclass(frozen=True)
class SlotAnalysisSchema:
    dimensions: list[str]
    short_to_dotted_dimension: dict[str, str]
    section1_slots: list[str]
    section2_slots: list[str]
    section3_slots: list[str]


SLOT_ANALYSIS_SCHEMA = SlotAnalysisSchema(
    dimensions=list(DIMENSIONS),
    short_to_dotted_dimension={},
    section1_slots=list(SECTION1_SLOT_FIELDS),
    section2_slots=list(SECTION2_SLOT_FIELDS),
    section3_slots=list(SECTION3_SLOT_FIELDS),
)


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


def ordered_labels(values: list[str], preferred_order: tuple[str, ...]) -> list[str]:
    preferred = [label for label in preferred_order if label in values]
    remaining = sorted(label for label in values if label not in preferred_order)
    return preferred + remaining


def normalize_report_label(value: object) -> str:
    return str(value or "").strip()


def normalize_converged_value_for_report(value: object) -> str:
    normalized = normalize_report_label(value)
    conflicted_labels = set(CONFLICTED_VALUE_LABELS) | {"conflicted", "conflicting"}
    if normalized in conflicted_labels:
        return "conflicting"
    return normalized


def normalize_converged_health_for_report(value: object) -> str:
    normalized = normalize_report_label(value)
    if normalized.startswith("conflict:"):
        return "conflict"
    return normalized


def extract_conflict_detail_from_payload(payload: dict[str, object], dimension: str) -> str:
    value_label = normalize_report_label(payload.get(f"{dimension}-devt_converged"))
    if value_label in CONFLICTED_VALUE_LABELS:
        return value_label

    health_label = normalize_report_label(payload.get(f"{dimension}-devt_converged_health"))
    if health_label.startswith("conflict:"):
        return health_label.removeprefix("conflict:").strip()

    return ""


def build_converged_value_table(records: list[dict[str, object]]) -> list[str]:
    counts_by_dimension: dict[str, dict[str, int]] = {
        dimension: defaultdict(int) for dimension in DIMENSIONS
    }
    observed_labels: set[str] = set()

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        for dimension in DIMENSIONS:
            label = normalize_converged_value_for_report(payload.get(f"{dimension}-devt_converged"))
            counts_by_dimension[dimension][label] += 1
            observed_labels.add(label)

    ordered = ordered_labels(list(observed_labels), CONVERGED_VALUE_ORDER)

    lines = [
        "| Converged value | " + " | ".join(DIMENSIONS) + " |",
        "| --- | " + " | ".join("---:" for _ in DIMENSIONS) + " |",
    ]
    for label in ordered:
        lines.append(
            f"| {label} | "
            + " | ".join(str(counts_by_dimension[dimension][label]) for dimension in DIMENSIONS)
            + " |"
        )
    lines.append("| Total | " + " | ".join(str(len(records)) for _ in DIMENSIONS) + " |")
    return lines


def build_converged_conflict_breakdown_table(records: list[dict[str, object]]) -> list[str]:
    counts_by_dimension: dict[str, dict[str, int]] = {
        dimension: defaultdict(int) for dimension in DIMENSIONS
    }
    observed_labels: set[str] = set()

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        for dimension in DIMENSIONS:
            label = extract_conflict_detail_from_payload(payload, dimension)
            if label:
                counts_by_dimension[dimension][label] += 1
                observed_labels.add(label)

    lines = [
        "| Conflicted value | " + " | ".join(DIMENSIONS) + " |",
        "| --- | " + " | ".join("---:" for _ in DIMENSIONS) + " |",
    ]
    ordered_labels_to_render = [
        label for label in CONFLICTED_VALUE_LABELS if label in observed_labels
    ]
    ordered_labels_to_render.extend(
        sorted(label for label in observed_labels if label not in CONFLICTED_VALUE_LABELS)
    )

    for label in ordered_labels_to_render:
        lines.append(
            f"| {label} | "
            + " | ".join(str(counts_by_dimension[dimension][label]) for dimension in DIMENSIONS)
            + " |"
        )
    lines.append(
        "| Total conflicted | "
        + " | ".join(
            str(sum(counts_by_dimension[dimension].values()))
            for dimension in DIMENSIONS
        )
        + " |"
    )
    return lines


def build_converged_health_table(records: list[dict[str, object]]) -> list[str]:
    counts_by_dimension: dict[str, dict[str, int]] = {
        dimension: defaultdict(int) for dimension in DIMENSIONS
    }
    observed_labels: set[str] = set()

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        for dimension in DIMENSIONS:
            label = normalize_converged_health_for_report(payload.get(f"{dimension}-devt_converged_health"))
            counts_by_dimension[dimension][label] += 1
            observed_labels.add(label)

    ordered = ordered_labels(list(observed_labels), CONVERGED_HEALTH_ORDER)

    lines = [
        "| Converged health | " + " | ".join(DIMENSIONS) + " |",
        "| --- | " + " | ".join("---:" for _ in DIMENSIONS) + " |",
    ]
    for label in ordered:
        lines.append(
            f"| {label} | "
            + " | ".join(str(counts_by_dimension[dimension][label]) for dimension in DIMENSIONS)
            + " |"
        )
    lines.append("| Total | " + " | ".join(str(len(records)) for _ in DIMENSIONS) + " |")
    return lines


def build_converged_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## Converged development fields",
        "",
        "### All data",
        "",
        "#### Converged values",
        "",
        *build_converged_value_table(records),
        "",
        "##### Conflicted value breakdown",
        "",
        *build_converged_conflict_breakdown_table(records),
        "",
        "#### Converged health",
        "",
        *build_converged_health_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(
            [
                "",
                f"### {student_pool}",
                "",
                "#### Converged values",
                "",
                *build_converged_value_table(pool_records),
                "",
                "##### Conflicted value breakdown",
                "",
                *build_converged_conflict_breakdown_table(pool_records),
                "",
                "#### Converged health",
                "",
                *build_converged_health_table(pool_records),
            ]
        )

    return lines


def normalize_devt_value(value: object) -> str:
    raw_value = str(value or "").strip().lower()
    if raw_value == "shift":
        return "shift"
    if raw_value in {
        "cont/reinf",
        "cont-reinf",
        "continuity-reinforcement",
        "continuity/reinforcement",
        "intro",
        "introduction",
    }:
        return "cont-reinf"
    return "other"


def build_shift_ratio_bin_labels(bin_count: int) -> tuple[str, ...]:
    labels = []
    for bin_index in range(bin_count):
        lower = bin_index / bin_count
        upper = (bin_index + 1) / bin_count
        if bin_count == 4:
            labels.append(f"Q{bin_index + 1} ({lower:.2f}-{upper:.2f})")
        else:
            labels.append(f"{lower:.1f}-{upper:.1f}")
    return tuple(labels)


def build_shift_count_labels(total_dimensions: int) -> tuple[str, ...]:
    return tuple(f"{shift_count} of {total_dimensions} shifted" for shift_count in range(total_dimensions + 1))


def assign_shift_ratio_bin(shift_count: int, cont_reinf_count: int, bin_count: int) -> str:
    total = shift_count + cont_reinf_count
    shift_ratio = shift_count / total
    if shift_ratio >= 1.0:
        if bin_count == 4:
            return "Q4 (0.75-1.00)"
        return "0.9-1.0"
    bin_index = int(shift_ratio * bin_count)
    lower = bin_index / bin_count
    upper = (bin_index + 1) / bin_count
    if bin_count == 4:
        return f"Q{bin_index + 1} ({lower:.2f}-{upper:.2f})"
    return f"{lower:.1f}-{upper:.1f}"


def get_shift_vs_cont_reinf_counts(payload: dict[str, object]) -> tuple[int, int] | None:
    shift_count = 0
    cont_reinf_count = 0

    for dimension in DIMENSIONS:
        normalized_value = normalize_devt_value(payload.get(f"{dimension}-devt"))
        if normalized_value == "shift":
            shift_count += 1
        elif normalized_value == "cont-reinf":
            cont_reinf_count += 1
        else:
            return None

    return shift_count, cont_reinf_count


def build_shift_count_distribution_table(records: list[dict[str, object]]) -> list[str]:
    total_dimensions = len(DIMENSIONS)
    categories = build_shift_count_labels(total_dimensions)
    counts_by_category = {category: 0 for category in categories}
    eligible_records = 0

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        shift_counts = get_shift_vs_cont_reinf_counts(payload)
        if shift_counts is None:
            continue
        shift_count, _ = shift_counts
        eligible_records += 1
        counts_by_category[f"{shift_count} of {total_dimensions} shifted"] += 1

    excluded_records = len(records) - eligible_records

    lines = [
        "| Shift count bin | Submission Count | % of Included |",
        "| --- | ---: | ---: |",
    ]
    for category in categories:
        count = counts_by_category[category]
        percent = (count / eligible_records) * 100 if eligible_records else 0.0
        lines.append(f"| {category} | {count} | {percent:.1f}% |")
    lines.append(f"| Included submissions | {eligible_records} | {100.0 if eligible_records else 0.0:.1f}% |")
    lines.append(
        f"| Excluded submissions | {excluded_records} | {((excluded_records / len(records)) * 100) if records else 0.0:.1f}% |"
    )
    lines.append(f"| Total submissions | {len(records)} | {100.0 if records else 0.0:.1f}% |")
    return lines


def build_shift_vs_cont_reinf_distribution_table(records: list[dict[str, object]], bin_count: int) -> list[str]:
    categories = build_shift_ratio_bin_labels(bin_count)
    counts_by_category = {category: 0 for category in categories}
    eligible_records = 0

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        shift_counts = get_shift_vs_cont_reinf_counts(payload)
        if shift_counts is None:
            continue
        shift_count, cont_reinf_count = shift_counts
        eligible_records += 1
        category = assign_shift_ratio_bin(shift_count, cont_reinf_count, bin_count)
        counts_by_category[category] += 1

    excluded_records = len(records) - eligible_records

    lines = [
        f"| Shift ratio {'quartile' if bin_count == 4 else 'decile'} | Submission Count | % of Included |",
        "| --- | ---: | ---: |",
    ]
    for category in categories:
        count = counts_by_category[category]
        percent = (count / eligible_records) * 100 if eligible_records else 0.0
        lines.append(f"| {category} | {count} | {percent:.1f}% |")
    lines.append(f"| Included submissions | {eligible_records} | {100.0 if eligible_records else 0.0:.1f}% |")
    lines.append(
        f"| Excluded submissions | {excluded_records} | {((excluded_records / len(records)) * 100) if records else 0.0:.1f}% |"
    )
    lines.append(f"| Total submissions | {len(records)} | {100.0 if records else 0.0:.1f}% |")
    return lines


def build_shift_vs_cont_reinf_distribution_analysis(records: list[dict[str, object]], *, bin_count: int, heading: str) -> list[str]:
    lines = [
        heading,
        "",
        "### All data",
        "",
        *build_shift_vs_cont_reinf_distribution_table(records, bin_count),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(["", f"### {student_pool}", "", *build_shift_vs_cont_reinf_distribution_table(pool_records, bin_count)])

    return lines


def get_group_shift_vs_cont_reinf_counts(payload: dict[str, object], group_dimensions: tuple[str, ...]) -> tuple[int, int] | None:
    shift_count = 0
    cont_reinf_count = 0

    for dimension in group_dimensions:
        normalized_value = normalize_devt_value(payload.get(f"{dimension}-devt"))
        if normalized_value == "shift":
            shift_count += 1
        elif normalized_value == "cont-reinf":
            cont_reinf_count += 1
        else:
            return None

    return shift_count, cont_reinf_count


def build_group_shift_count_table(records: list[dict[str, object]]) -> list[str]:
    categories = tuple(f"{shift_count} of 3 shifted" for shift_count in range(4))
    counts_by_group = {
        group_name: {category: 0 for category in categories}
        for group_name in DIMENSION_GROUPS
    }
    included_by_group = {group_name: 0 for group_name in DIMENSION_GROUPS}

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        for group_name, group_dimensions in DIMENSION_GROUPS.items():
            shift_counts = get_group_shift_vs_cont_reinf_counts(payload, group_dimensions)
            if shift_counts is None:
                continue
            shift_count, _ = shift_counts
            included_by_group[group_name] += 1
            counts_by_group[group_name][f"{shift_count} of 3 shifted"] += 1

    lines = [
        "| Shift count bin | B Count | B % Included | C Count | C % Included | D Count | D % Included |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category in categories:
        row_cells: list[str] = []
        for group_name in ("B", "C", "D"):
            count = counts_by_group[group_name][category]
            included = included_by_group[group_name]
            percent = (count / included) * 100 if included else 0.0
            row_cells.extend([str(count), f"{percent:.1f}%"])
        lines.append(f"| {category} | " + " | ".join(row_cells) + " |")

    included_cells: list[str] = []
    excluded_cells: list[str] = []
    total_cells: list[str] = []
    for group_name in ("B", "C", "D"):
        included = included_by_group[group_name]
        excluded = len(records) - included
        included_cells.extend([str(included), f"{100.0 if included else 0.0:.1f}%"])
        excluded_cells.extend([str(excluded), f"{((excluded / len(records)) * 100) if records else 0.0:.1f}%"])
        total_cells.extend([str(len(records)), f"{100.0 if records else 0.0:.1f}%"])

    lines.append("| Included submissions | " + " | ".join(included_cells) + " |")
    lines.append("| Excluded submissions | " + " | ".join(excluded_cells) + " |")
    lines.append("| Total submissions | " + " | ".join(total_cells) + " |")
    return lines


def build_group_shift_count_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## B/C/D shift vs cont-reinf distribution - Quartiles",
        "",
        "### All data",
        "",
        *build_group_shift_count_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(["", f"### {student_pool}", "", *build_group_shift_count_table(pool_records)])

    return lines


def build_shift_count_distribution_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## B/C/D shift vs cont-reinf distribution - Deciles",
        "",
        "### All data",
        "",
        *build_shift_count_distribution_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend(["", f"### {student_pool}", "", *build_shift_count_distribution_table(pool_records)])

    return lines


def normalize_slot_dimension(value: object) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    if normalized in HUMAN_FRIENDLY_TO_SHORT_DIMENSION:
        return HUMAN_FRIENDLY_TO_SHORT_DIMENSION[normalized]
    short_match = re.match(r"^([BCD]-\d)\b", normalized)
    if short_match:
        return short_match.group(1)
    dotted_match = re.match(r"^([BCD])\.2\.(\d)\b", normalized)
    if dotted_match:
        return f"{dotted_match.group(1)}-{dotted_match.group(2)}"
    return normalized


def normalize_payload_for_slot_analysis(payload: dict[str, object]) -> dict[str, str]:
    return {str(key): "" if value is None else str(value) for key, value in payload.items()}


def get_actual_slot_dimensions(payload: dict[str, object]) -> dict[str, str]:
    return {field: normalize_slot_dimension(payload.get(field)) for field in ALL_SLOT_FIELDS}


def get_record_json_filename(record: dict[str, object]) -> str:
    path_value = str(record.get("path") or "")
    if path_value:
        return Path(path_value).name
    payload = record.get("payload")
    if isinstance(payload, dict):
        participant_id = str(payload.get("participant_id") or "").strip()
        if participant_id:
            return f"{participant_id}.json"
    return ""


def get_expected_slot_selection(payload: dict[str, object]):
    normalized_payload = normalize_payload_for_slot_analysis(payload)
    return select_section_dimensions(SLOT_ANALYSIS_SCHEMA, normalized_payload)


def get_expected_slot_dimensions(payload: dict[str, object]) -> dict[str, str]:
    selection = get_expected_slot_selection(payload)
    return {
        **dict(zip(SECTION1_SLOT_FIELDS, selection.section1_dims, strict=False)),
        **dict(zip(SECTION2_SLOT_FIELDS, selection.section2_dims, strict=False)),
        **dict(zip(SECTION3_SLOT_FIELDS, selection.section3_dims, strict=False)),
    }


def describe_slot_policy_issues(payload: dict[str, object]) -> list[str]:
    selection = get_expected_slot_selection(payload)
    actual = get_actual_slot_dimensions(payload)
    issues: list[str] = []

    if len(selection.section2_dims) < len(SECTION2_SLOT_FIELDS):
        blocked_dims = ", ".join(selection.section2_blocked_unknown_dims) or "none"
        issues.append(
            f"Section2 underfilled {len(selection.section2_dims)}/{len(SECTION2_SLOT_FIELDS)}; "
            f"unknown-devt blocked={blocked_dims}"
        )

    for field in SECTION2_SLOT_FIELDS:
        dimension = actual.get(field, "")
        if dimension and not str(payload.get(f"{dimension}-devt_converged") or "").strip():
            issues.append(f"{field} uses {dimension} with unknown devt")

    expected_section2 = [
        selection.section2_dims[index] if index < len(selection.section2_dims) else ""
        for index in range(len(SECTION2_SLOT_FIELDS))
    ]
    actual_section2 = [actual.get(field, "") for field in SECTION2_SLOT_FIELDS]
    if actual_section2 != expected_section2:
        issues.append(
            "actual V slots differ from policy-expected fill: "
            + ", ".join(expected_section2)
            + " vs "
            + ", ".join(actual_section2)
        )

    return issues


def format_slot_value(value: str) -> str:
    return value or ""


def count_words(value: object) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    return len(re.findall(r"\b\w+\b", text))


def get_slot_word_counts(payload: dict[str, object]) -> dict[str, int]:
    return {
        slot_label: sum(count_words(payload.get(field, "")) for field in source_fields)
        for slot_label, source_fields in SLOT_WORD_COUNT_FIELDS.items()
    }


def percentile_nearest_rank(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def get_slot_word_count_thresholds(records: list[dict[str, object]]) -> dict[str, tuple[int | None, int | None]]:
    thresholds: dict[str, tuple[int | None, int | None]] = {}
    for slot_label in SLOT_WORD_COUNT_ORDER:
        counts: list[int] = []
        for record in records:
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            counts.append(get_slot_word_counts(payload)[slot_label])
        low = percentile_nearest_rank(counts, 0.05)
        high = percentile_nearest_rank(counts, 0.95)
        if low is not None and high is not None and low >= high:
            thresholds[slot_label] = (None, None)
        else:
            thresholds[slot_label] = (low, high)
    return thresholds


def classify_slot_word_count(word_count: int, low: int | None, high: int | None) -> str:
    if low is not None and word_count <= low:
        return "very short"
    if high is not None and word_count >= high:
        return "very long"
    return ""


def format_slot_word_count_cell(word_count: int, flag: str) -> str:
    if not flag:
        return str(word_count)
    return f"{word_count} ({flag})"


def duplicate_slot_dimensions(actual_dimensions: dict[str, str]) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for field in SECTION1_SLOT_FIELDS + SECTION2_SLOT_FIELDS:
        dimension = actual_dimensions.get(field, "")
        if dimension:
            counts[dimension] += 1
    return [dimension for dimension, count in sorted(counts.items()) if count > 1]


def same_family_non_tension_exists(payload: dict[str, object], dimension: str) -> bool:
    family = dimension.split("-", 1)[0]
    for candidate in DIMENSIONS:
        if not candidate.startswith(f"{family}-") or candidate == dimension:
            continue
        if str(payload.get(f"{candidate}-status") or "") != "in tension":
            return True
    return False


def expected_ts_family(slot_field: str) -> str:
    if slot_field == "Sec1_TS1_dim":
        return "B"
    if slot_field == "Sec1_TS2_dim":
        return "C"
    return "D"


def describe_slot_selection_issues(payload: dict[str, object]) -> list[str]:
    actual = get_actual_slot_dimensions(payload)
    expected = get_expected_slot_dimensions(payload)
    issues: list[str] = []

    duplicates = duplicate_slot_dimensions(actual)
    if duplicates:
        issues.append("duplicate dimensions: " + ", ".join(duplicates))

    for field in SECTION1_SLOT_FIELDS:
        dimension = actual.get(field, "")
        if dimension and not dimension.startswith(f"{expected_ts_family(field)}-"):
            issues.append(f"{field} chose {dimension} outside its expected family")

    actual_section2 = [actual.get(field, "") for field in SECTION2_SLOT_FIELDS]
    expected_section2 = [expected.get(field, "") for field in SECTION2_SLOT_FIELDS]
    if actual_section2 != expected_section2:
        issues.append("V expected " + ", ".join(expected_section2) + " but got " + ", ".join(actual_section2))

    actual_section3 = [actual.get(field, "") for field in SECTION3_SLOT_FIELDS]
    expected_section3 = [expected.get(field, "") for field in SECTION3_SLOT_FIELDS]
    if actual_section3 != expected_section3:
        issues.append("Sec4 expected " + ", ".join(expected_section3) + " but got " + ", ".join(actual_section3))

    for field in SECTION1_SLOT_FIELDS:
        dimension = actual.get(field, "")
        if not dimension:
            continue
        if str(payload.get(f"{dimension}-status") or "") == "in tension" and same_family_non_tension_exists(payload, dimension):
            issues.append(f"{field} chose in-tension {dimension} despite a same-family non-tension option")

    if any(dimension.startswith("D-") for dimension in actual_section2 if dimension):
        issues.append("V includes D dimension")

    return issues


def describe_slot_selection_issues_by_group(payload: dict[str, object]) -> dict[str, list[str]]:
    actual = get_actual_slot_dimensions(payload)
    expected = get_expected_slot_dimensions(payload)
    grouped_issues = {"ts": [], "v": [], "slot": []}

    duplicates = duplicate_slot_dimensions(actual)
    if duplicates:
        grouped_issues["v"].append("duplicate dimensions across TS/V: " + ", ".join(duplicates))

    for field in SECTION1_SLOT_FIELDS:
        dimension = actual.get(field, "")
        if dimension and not dimension.startswith(f"{expected_ts_family(field)}-"):
            grouped_issues["ts"].append(f"{field} chose {dimension} outside its expected family")

    actual_section2 = [actual.get(field, "") for field in SECTION2_SLOT_FIELDS]
    expected_section2 = [expected.get(field, "") for field in SECTION2_SLOT_FIELDS]
    if actual_section2 != expected_section2:
        grouped_issues["v"].append(
            "expected " + ", ".join(expected_section2) + " but got " + ", ".join(actual_section2)
        )

    actual_section3 = [actual.get(field, "") for field in SECTION3_SLOT_FIELDS]
    expected_section3 = [expected.get(field, "") for field in SECTION3_SLOT_FIELDS]
    if actual_section3 != expected_section3:
        grouped_issues["slot"].append(
            "expected " + ", ".join(expected_section3) + " but got " + ", ".join(actual_section3)
        )

    for field in SECTION1_SLOT_FIELDS:
        dimension = actual.get(field, "")
        if not dimension:
            continue
        if str(payload.get(f"{dimension}-status") or "") == "in tension" and same_family_non_tension_exists(payload, dimension):
            grouped_issues["ts"].append(
                f"{field} chose in-tension {dimension} despite a same-family non-tension option"
            )

    if any(dimension.startswith("D-") for dimension in actual_section2 if dimension):
        grouped_issues["v"].append("includes D dimension")

    return grouped_issues


def slot_analysis_row(record: dict[str, object], *, include_issues: bool) -> str:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    actual = get_actual_slot_dimensions(payload)
    json_filename = get_record_json_filename(record)
    student_pool = str(record.get("student_pool") or "")
    cells = [
        json_filename,
        student_pool,
        format_slot_value(actual.get("Sec1_TS1_dim", "")),
        format_slot_value(actual.get("Sec1_TS2_dim", "")),
        format_slot_value(actual.get("Sec1_TS3_dim", "")),
        format_slot_value(actual.get("Sec2_V1_dim", "")),
        format_slot_value(actual.get("Sec2_V2_dim", "")),
        format_slot_value(actual.get("Sec4_Slot1_dim", "")),
        format_slot_value(actual.get("Sec4_Slot2_dim", "")),
        format_slot_value(actual.get("Sec4_Slot3_dim", "")),
    ]
    if include_issues:
        issues = "; ".join(describe_slot_selection_issues(payload))
        cells.append(issues)
    return "| " + " | ".join(cell.replace("|", "/") for cell in cells) + " |"


def build_slot_selection_table(records: list[dict[str, object]], *, problematic: bool) -> list[str]:
    filtered_records: list[dict[str, object]] = []
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        issues = describe_slot_selection_issues(payload)
        if problematic and issues:
            filtered_records.append(record)
        if not problematic and not issues:
            filtered_records.append(record)

    filtered_records.sort(
        key=lambda record: (
            str(record.get("student_pool") or ""),
            get_record_json_filename(record),
            str(record.get("path") or ""),
        )
    )

    header = "| JSON file | Pool | TS1 | TS2 | TS3 | V1 | V2 | Slot1 | Slot2 | Slot3 |"
    divider = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    if problematic:
        header = "| JSON file | Pool | TS1 | TS2 | TS3 | V1 | V2 | Slot1 | Slot2 | Slot3 | Issues |"
        divider = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"

    lines = [header, divider]
    if not filtered_records:
        empty_cells = ["(none)"] + [""] * 9
        if problematic:
            empty_cells.append("")
        lines.append("| " + " | ".join(empty_cells) + " |")
        return lines

    for record in filtered_records:
        lines.append(slot_analysis_row(record, include_issues=problematic))
    return lines


def build_problematic_slot_selection_table(records: list[dict[str, object]], group: str) -> list[str]:
    field_map = {
        "ts": SECTION1_SLOT_FIELDS,
        "v": SECTION2_SLOT_FIELDS,
        "slot": SECTION3_SLOT_FIELDS,
    }
    label_map = {
        "ts": ("TS1", "TS2", "TS3"),
        "v": ("V1", "V2"),
        "slot": ("Slot1", "Slot2", "Slot3"),
    }
    fields = field_map[group]
    labels = label_map[group]

    filtered_records: list[dict[str, object]] = []
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if describe_slot_selection_issues_by_group(payload)[group]:
            filtered_records.append(record)

    filtered_records.sort(
        key=lambda record: (
            str(record.get("student_pool") or ""),
            get_record_json_filename(record),
            str(record.get("path") or ""),
        )
    )

    header = "| JSON file | Pool | " + " | ".join(labels) + " | Issues |"
    divider = "| --- | --- | " + " | ".join("---" for _ in labels) + " | --- |"
    lines = [header, divider]
    if not filtered_records:
        lines.append("| (none) |  | " + " | ".join("" for _ in labels) + " |  |")
        return lines

    for record in filtered_records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        actual = get_actual_slot_dimensions(payload)
        json_filename = get_record_json_filename(record)
        student_pool = str(record.get("student_pool") or "")
        issues = "; ".join(describe_slot_selection_issues_by_group(payload)[group])
        cells = [json_filename, student_pool] + [format_slot_value(actual.get(field, "")) for field in fields] + [issues]
        lines.append("| " + " | ".join(cell.replace("|", "/") for cell in cells) + " |")
    return lines


def build_slot_policy_problem_table(records: list[dict[str, object]]) -> list[str]:
    filtered_records: list[dict[str, object]] = []
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if describe_slot_policy_issues(payload):
            filtered_records.append(record)

    filtered_records.sort(
        key=lambda record: (
            str(record.get("student_pool") or ""),
            get_record_json_filename(record),
            str(record.get("path") or ""),
        )
    )

    lines = [
        "| JSON file | Pool | V1 | V2 | Policy Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not filtered_records:
        lines.append("| (none) |  |  |  |  |")
        return lines

    for record in filtered_records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        actual = get_actual_slot_dimensions(payload)
        json_filename = get_record_json_filename(record)
        student_pool = str(record.get("student_pool") or "")
        notes = "; ".join(describe_slot_policy_issues(payload))
        cells = [
            json_filename,
            student_pool,
            format_slot_value(actual.get("Sec2_V1_dim", "")),
            format_slot_value(actual.get("Sec2_V2_dim", "")),
            notes,
        ]
        lines.append("| " + " | ".join(cell.replace("|", "/") for cell in cells) + " |")

    return lines


def build_slot_selection_analysis_block(records: list[dict[str, object]]) -> list[str]:
    straightforward_count = 0
    problematic_count = 0
    policy_problem_count = 0
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if describe_slot_policy_issues(payload):
            policy_problem_count += 1
        if describe_slot_selection_issues(payload):
            problematic_count += 1
        else:
            straightforward_count += 1

    return [
        "#### Slot Filling Policy",
        "",
        "- Section 1 and Section 4 may fall back to dimensions whose converged development type is unknown.",
        "- Section 2 may only use dimensions whose `-devt_converged` value is known.",
        f"- Policy-compliant cases: {straightforward_count + problematic_count - policy_problem_count}",
        f"- Policy-problem cases: {policy_problem_count}",
        "",
        "#### Policy-problem cases",
        "",
        *build_slot_policy_problem_table(records),
        "",
        f"- Straightforward cases: {straightforward_count}",
        f"- Problematic cases: {problematic_count}",
        "",
        "#### Straightforward cases",
        "",
        *build_slot_selection_table(records, problematic=False),
        "",
        "#### Problematic cases",
        "",
        "##### TS slots",
        "",
        *build_problematic_slot_selection_table(records, "ts"),
        "",
        "##### V slots",
        "",
        *build_problematic_slot_selection_table(records, "v"),
        "",
        "##### Section 4 slots",
        "",
        *build_problematic_slot_selection_table(records, "slot"),
    ]


def build_slot_selection_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## Slot Selection Analysis",
        "",
        "### All data",
        "",
        *build_slot_selection_analysis_block(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend([
            "",
            f"### {student_pool}",
            "",
            *build_slot_selection_analysis_block(pool_records),
        ])

    return lines


def build_slot_word_count_overview_table(records: list[dict[str, object]]) -> list[str]:
    thresholds = get_slot_word_count_thresholds(records)
    sorted_records = sorted(
        (
            record
            for record in records
            if isinstance(record.get("payload"), dict)
        ),
        key=lambda record: (
            str(record.get("student_pool") or ""),
            get_record_json_filename(record),
            str(record.get("path") or ""),
        ),
    )

    lines = [
        "| JSON file | Pool | TS1 | TS2 | TS3 | V1 | V2 | Slot1 | Slot2 | Slot3 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not sorted_records:
        lines.append("| (none) |  |  |  |  |  |  |  |  |  |")
        return lines

    for record in sorted_records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        word_counts = get_slot_word_counts(payload)
        cells = [get_record_json_filename(record), str(record.get("student_pool") or "")]
        for slot_label in SLOT_WORD_COUNT_ORDER:
            low, high = thresholds[slot_label]
            flag = classify_slot_word_count(word_counts[slot_label], low, high)
            cells.append(format_slot_word_count_cell(word_counts[slot_label], flag))
        lines.append("| " + " | ".join(cell.replace("|", "/") for cell in cells) + " |")

    return lines


def build_slot_word_count_extreme_cases_table(records: list[dict[str, object]]) -> list[str]:
    thresholds = get_slot_word_count_thresholds(records)
    rows: list[list[str]] = []

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        word_counts = get_slot_word_counts(payload)
        for slot_label in SLOT_WORD_COUNT_ORDER:
            low, high = thresholds[slot_label]
            flag = classify_slot_word_count(word_counts[slot_label], low, high)
            if not flag:
                continue
            rows.append(
                [
                    get_record_json_filename(record),
                    str(record.get("student_pool") or ""),
                    slot_label,
                    str(word_counts[slot_label]),
                    flag,
                    f"p05={low if low is not None else ''}; p95={high if high is not None else ''}",
                ]
            )

    rows.sort(key=lambda row: (row[1], row[0], row[2], row[4], row[3]))
    lines = [
        "| JSON file | Pool | Slot | Word count | Flag | Thresholds |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    if not rows:
        lines.append("| (none) |  |  |  |  |  |")
        return lines

    for row in rows:
        lines.append("| " + " | ".join(cell.replace("|", "/") for cell in row) + " |")
    return lines


def build_slot_word_count_summary(records: list[dict[str, object]]) -> list[str]:
    thresholds = get_slot_word_count_thresholds(records)
    lines = [
        "| Slot | p05 | p95 | Min | Max |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for slot_label in SLOT_WORD_COUNT_ORDER:
        counts: list[int] = []
        for record in records:
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            counts.append(get_slot_word_counts(payload)[slot_label])
        if not counts:
            lines.append(f"| {slot_label} |  |  |  |  |")
            continue
        low, high = thresholds[slot_label]
        lines.append(f"| {slot_label} | {'' if low is None else low} | {'' if high is None else high} | {min(counts)} | {max(counts)} |")
    return lines


def build_slot_word_count_analysis(records: list[dict[str, object]]) -> list[str]:
    lines = [
        "## Slot Word Count Overview",
        "",
        "Counts below are total words drawn from the populated text fields for each slot.",
        "Extreme flags are relative to the current dataset slice using the 5th and 95th percentile cutoffs for each slot.",
        "",
        "### All data",
        "",
        "#### Threshold summary",
        "",
        *build_slot_word_count_summary(records),
        "",
        "#### Per-student overview",
        "",
        *build_slot_word_count_overview_table(records),
        "",
        "#### Extreme cases",
        "",
        *build_slot_word_count_extreme_cases_table(records),
    ]

    for student_pool, pool_records in sorted(split_records_by_student_pool(records).items()):
        lines.extend([
            "",
            f"### {student_pool}",
            "",
            "#### Threshold summary",
            "",
            *build_slot_word_count_summary(pool_records),
            "",
            "#### Per-student overview",
            "",
            *build_slot_word_count_overview_table(pool_records),
            "",
            "#### Extreme cases",
            "",
            *build_slot_word_count_extreme_cases_table(pool_records),
        ])

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
    lines.extend(["", *build_shift_count_distribution_analysis(records)])
    lines.extend(["", *build_group_shift_count_analysis(records)])
    lines.extend(["", *build_converged_analysis(records)])
    lines.extend(["", *build_slot_selection_analysis(records)])
    lines.extend(["", *build_slot_word_count_analysis(records)])
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