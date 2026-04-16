#!/usr/bin/env python3
"""Import PPS1 LMS CSV data into per-student JSON files.

The output schema, field ordering, and CSV-to-JSON mappings live in an external
JSON config file so they can be updated without changing Python code.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
import random
import re
import shutil
from pathlib import Path
import sys
from typing import Any


APPS_DIR = Path(__file__).resolve().parents[3] / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from lms_text_cleaning import clean_lms_text, should_clean_lms_text_column


DEFAULT_SCHEMA_PATH = Path(
    "/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/pps1_import_schema.json"
)


@dataclass(frozen=True)
class SectionSlot:
    dim_field: str
    ppp_field: str | None = None
    pps1_field: str | None = None


@dataclass(frozen=True)
class ClaimFields:
    dimension_field: str
    text_fields: list[str]


@dataclass(frozen=True)
class IdentityFields:
    participant_id: str
    family_name: str
    given_name: str


@dataclass(frozen=True)
class ParticipantIdentity:
    given_name: str
    family_name: str


@dataclass(frozen=True)
class GeneratedRecord:
    path: Path
    given_name: str
    family_name: str


@dataclass(frozen=True)
class AuditRow:
    source_csv_path: str
    row_index: int
    user: str
    username: str
    email_address: str
    participant_id: str
    given_name: str
    family_name: str
    output_json_path: str
    dimension_check_fields: dict[str, str]
    position_state_matrix_fields: dict[str, str]


@dataclass(frozen=True)
class ImportSchema:
    import_defaults: "ImportDefaults"
    record_defaults: dict[str, str]
    dimensions: list[str]
    short_to_dotted_dimension: dict[str, str]
    direct_field_map: dict[str, str]
    grid_status_map: dict[str, str]
    section1_slots: list[SectionSlot]
    section2_slots: list[SectionSlot]
    section3_slots: list[SectionSlot]
    claim_fields: ClaimFields
    identity_fields: IdentityFields


@dataclass(frozen=True)
class ImportDefaults:
    csv_path: Path
    participants_csv_path: Path
    all_output_dir: Path
    sample_output_dir: Path
    audit_path: Path
    sample_size: int


def parse_section_slots(raw_slots: list[dict[str, str]]) -> list[SectionSlot]:
    return [
        SectionSlot(
            dim_field=slot["dim"],
            ppp_field=slot.get("ppp"),
            pps1_field=slot.get("pps1"),
        )
        for slot in raw_slots
    ]


def load_schema(schema_path: Path) -> ImportSchema:
    raw_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    import_defaults = ImportDefaults(
        csv_path=Path(raw_schema["importDefaults"]["csvPath"]),
        participants_csv_path=Path(raw_schema["importDefaults"]["participantsCsvPath"]),
        all_output_dir=Path(raw_schema["importDefaults"]["allOutputDir"]),
        sample_output_dir=Path(raw_schema["importDefaults"]["sampleOutputDir"]),
        audit_path=Path(raw_schema["importDefaults"]["auditPath"]),
        sample_size=int(raw_schema["importDefaults"]["sampleSize"]),
    )

    identity_fields = IdentityFields(
        participant_id=raw_schema["identityFields"]["participantId"],
        family_name=raw_schema["identityFields"]["familyName"],
        given_name=raw_schema["identityFields"]["givenName"],
    )
    claim_fields = ClaimFields(
        dimension_field=raw_schema["claimFields"]["dimension"],
        text_fields=list(raw_schema["claimFields"]["texts"]),
    )

    return ImportSchema(
        import_defaults=import_defaults,
        record_defaults=dict(raw_schema["recordDefaults"]),
        dimensions=list(raw_schema["dimensions"]),
        short_to_dotted_dimension=dict(raw_schema["shortToDottedDimension"]),
        direct_field_map=dict(raw_schema["directFieldMap"]),
        grid_status_map=dict(raw_schema["gridStatusMap"]),
        section1_slots=parse_section_slots(raw_schema["section1Slots"]),
        section2_slots=parse_section_slots(raw_schema["section2Slots"]),
        section3_slots=parse_section_slots(raw_schema["section3Slots"]),
        claim_fields=claim_fields,
        identity_fields=identity_fields,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PPS1 LMS CSV rows into per-student JSON files.")
    parser.add_argument("--csv-path", type=Path)
    parser.add_argument("--participants-csv-path", type=Path)
    parser.add_argument("--schema-path", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--all-output-dir", type=Path)
    parser.add_argument("--sample-output-dir", type=Path)
    parser.add_argument("--audit-path", type=Path)
    parser.add_argument("--sample-size", type=int)
    parser.add_argument("--sample-seed", type=int)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def resolve_runtime_value[T](override: T | None, default: T) -> T:
    return default if override is None else override


def normalize_value(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def sanitize_filename(raw_value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_value.strip())
    cleaned = cleaned.strip("._")
    return cleaned or fallback


def split_user_name(user_value: str, username_value: str) -> tuple[str, str]:
    parts = [part for part in user_value.split() if part]
    if not parts:
        fallback = username_value.strip() or "Unknown"
        return "", fallback
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def normalize_participant_name(value: str | None) -> str:
    return normalize_value(value)


def load_participant_lookup(participants_csv_path: Path) -> dict[str, ParticipantIdentity]:
    lookup: dict[str, ParticipantIdentity] = {}
    with participants_csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError(f"Participants CSV has no header row: {participants_csv_path}")

        for row in reader:
            email = normalize_value(row.get("Email address")).casefold()
            if not email:
                continue

            identity = ParticipantIdentity(
                given_name=normalize_participant_name(row.get("First name")),
                family_name=normalize_participant_name(row.get("Last name")),
            )
            lookup[email] = identity
            local_part = email.split("@", 1)[0]
            if local_part:
                lookup.setdefault(local_part.casefold(), identity)

    return lookup


def resolve_names(
    row: dict[str, str],
    participant_lookup: dict[str, ParticipantIdentity],
) -> tuple[str, str]:
    user_value = normalize_value(row.get("User"))
    username_value = normalize_value(row.get("Username"))
    email_value = normalize_value(row.get("Email address")).casefold()

    fallback_given_name, fallback_family_name = split_user_name(user_value, username_value)

    participant = participant_lookup.get(email_value) or participant_lookup.get(username_value.casefold())
    if participant is None:
        return fallback_given_name, fallback_family_name

    given_name = participant.given_name or fallback_given_name
    family_name = participant.family_name or fallback_family_name
    return given_name, family_name


def build_empty_record(schema: ImportSchema) -> dict[str, str]:
    return dict(schema.record_defaults)


def checked(value: str) -> bool:
    normalized = value.strip().casefold()
    return normalized in {"✓", "true", "yes", "1"}


def derive_development_value(row: dict[str, str], prefix: str) -> str:
    if checked(normalize_value(row.get(f"{prefix}_shift"))):
        return "Shift"
    if checked(normalize_value(row.get(f"{prefix}_cont"))):
        return "Cont/Reinf"
    if checked(normalize_value(row.get(f"{prefix}_intro"))):
        return "Intro"
    return ""


def build_dimension_development_audit_fields(
    schema: ImportSchema,
    row: dict[str, str],
) -> dict[str, str]:
    audit_fields: dict[str, str] = {}

    for dimension in schema.dimensions:
        prefix = schema.short_to_dotted_dimension[dimension].replace(".", "")
        shift_selected = checked(normalize_value(row.get(f"{prefix}_shift")))
        cont_reinf_selected = checked(normalize_value(row.get(f"{prefix}_cont")))
        intro_selected = checked(normalize_value(row.get(f"{prefix}_intro")))
        selected_count = sum((shift_selected, cont_reinf_selected, intro_selected))
        check_passed = selected_count == 1

        if check_passed:
            error_value = ""
        elif selected_count == 0:
            error_value = "none selected"
        else:
            error_value = "multiple selected"

        audit_fields[f"{dimension}-shift"] = str(shift_selected).lower()
        audit_fields[f"{dimension}-cont-reinf"] = str(cont_reinf_selected).lower()
        audit_fields[f"{dimension}-intro"] = str(intro_selected).lower()
        audit_fields[f"{dimension}-check"] = str(check_passed).lower()
        audit_fields[f"{dimension}-err"] = error_value

    return audit_fields


def build_position_state_matrix_audit_fields(row: dict[str, str]) -> dict[str, str]:
    matrix_columns = [
        "E2_00_GridResponse",
        "E2_10_GridResponse",
        "E2_01_GridResponse",
        "E2_11_GridResponse",
    ]
    audit_fields: dict[str, str] = {}
    specified_count = 0

    for column_name in matrix_columns:
        value = normalize_value(row.get(column_name))
        audit_fields[column_name] = value
        if value:
            specified_count += 1

    saturation_rate = (specified_count / len(matrix_columns)) * 100
    audit_fields["Position-State Matrix Saturation Rate"] = f"{saturation_rate:.1f}%"
    return audit_fields


def populate_status_values(schema: ImportSchema, record: dict[str, str], row: dict[str, str]) -> None:
    dotted_to_short_dimension = {
        value: key for key, value in schema.short_to_dotted_dimension.items()
    }

    for grid_key, status_value in schema.grid_status_map.items():
        dimension_value = normalize_value(row.get(grid_key))
        short_dimension = dotted_to_short_dimension.get(dimension_value)
        if not short_dimension:
            continue
        record[f"{short_dimension}-status"] = status_value


def populate_development_values(schema: ImportSchema, record: dict[str, str], row: dict[str, str]) -> None:
    for dimension in schema.dimensions:
        prefix = schema.short_to_dotted_dimension[dimension].replace(".", "")
        record[f"{dimension}-devt"] = derive_development_value(row, prefix)


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def select_section_dimensions(schema: ImportSchema, record: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    priority = ordered_unique(
        [dimension for dimension in schema.dimensions if record.get(f"{dimension}-status")]
        + [dimension for dimension in schema.dimensions if record.get(f"{dimension}-devt")]
        + schema.dimensions
    )
    section1 = priority[:3]
    remaining = [dimension for dimension in priority if dimension not in section1]
    section2 = remaining[:3]
    tension_dims = [
        dimension for dimension in schema.dimensions if record.get(f"{dimension}-status") == "in tension"
    ]
    tension_priority = ordered_unique(tension_dims + section2 + remaining)
    section3 = tension_priority[:2]
    return section1, section2, section3


def populate_section_fields(schema: ImportSchema, record: dict[str, str]) -> None:
    section1_dims, section2_dims, section3_dims = select_section_dimensions(schema, record)

    for dimension, slot in zip(section1_dims, schema.section1_slots, strict=False):
        record[slot.dim_field] = schema.short_to_dotted_dimension[dimension]
        if slot.ppp_field:
            record[slot.ppp_field] = record.get(f"{dimension}-PPP", "")
        if slot.pps1_field:
            record[slot.pps1_field] = record.get(f"{dimension}-PPS1", "")

    for dimension, slot in zip(section2_dims, schema.section2_slots, strict=False):
        record[slot.dim_field] = schema.short_to_dotted_dimension[dimension]
        if slot.ppp_field:
            record[slot.ppp_field] = record.get(f"{dimension}-PPP", "")
        if slot.pps1_field:
            record[slot.pps1_field] = record.get(f"{dimension}-PPS1", "")

    for dimension, slot in zip(section3_dims, schema.section3_slots, strict=False):
        record[slot.dim_field] = schema.short_to_dotted_dimension[dimension]
        if slot.pps1_field:
            record[slot.pps1_field] = record.get(f"{dimension}-PPS1", "")

    if section2_dims:
        record[schema.claim_fields.dimension_field] = schema.short_to_dotted_dimension[section2_dims[0]]

    for dimension, claim_field in zip(section2_dims, schema.claim_fields.text_fields, strict=False):
        record[claim_field] = record.get(f"{dimension}-PPS1", "")


def build_record(
    schema: ImportSchema,
    row: dict[str, str],
    participant_lookup: dict[str, ParticipantIdentity],
) -> dict[str, str]:
    record = build_empty_record(schema)

    user_value = normalize_value(row.get("User"))
    username_value = normalize_value(row.get("Username"))
    given_name, family_name = resolve_names(row, participant_lookup)

    record[schema.identity_fields.participant_id] = username_value or sanitize_filename(user_value, "unknown")
    record[schema.identity_fields.given_name] = given_name
    record[schema.identity_fields.family_name] = family_name

    for csv_key, json_key in schema.direct_field_map.items():
        if json_key in record:
            raw_value = row.get(csv_key)
            if should_clean_lms_text_column(csv_key):
                record[json_key] = clean_lms_text(raw_value)
            else:
                record[json_key] = normalize_value(raw_value)

    populate_development_values(schema, record, row)
    populate_status_values(schema, record, row)
    populate_section_fields(schema, record)

    return record


def build_filename_base(given_name: str, family_name: str, fallback: str) -> str:
    given_component = sanitize_filename(given_name, "")
    normalized_family_name = normalize_value(family_name)

    if normalized_family_name == ".":
        family_component = "_DOT"
    else:
        family_component = sanitize_filename(normalized_family_name, "").upper()

    if given_component and family_component:
        if family_component.startswith("_"):
            return f"{family_component}_{given_component}"
        return f"{family_component}_{given_component}"
    if given_component:
        return given_component
    if family_component:
        return family_component.lstrip("_") or fallback
    return fallback


def make_output_filename(
    schema: ImportSchema,
    record: dict[str, str],
    row: dict[str, str],
    used_names: set[str],
    row_index: int,
) -> str:
    username_value = normalize_value(row.get("Username"))
    fallback_base_name = sanitize_filename(username_value, f"row_{row_index:04d}")
    base_name = build_filename_base(
        record.get(schema.identity_fields.given_name, ""),
        record.get(schema.identity_fields.family_name, ""),
        fallback_base_name,
    )

    if base_name not in used_names:
        used_names.add(base_name)
        return f"{base_name}.json"

    fallback_name = sanitize_filename(username_value, f"row_{row_index:04d}")
    candidate = f"{base_name}__{fallback_name}" if fallback_name else f"{base_name}__{row_index:04d}"
    counter = 2
    unique_candidate = candidate
    while unique_candidate in used_names:
        unique_candidate = f"{candidate}_{counter}"
        counter += 1
    used_names.add(unique_candidate)
    return f"{unique_candidate}.json"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def build_audit_fieldnames(schema: ImportSchema) -> list[str]:
    fieldnames = [
        "source_csv_path",
        "row_index",
        "user",
        "username",
        "email_address",
        "participant_id",
        "given_name",
        "family_name",
        "output_json_path",
        ".",
    ]
    for dimension in schema.dimensions:
        fieldnames.extend(
            [
                f"{dimension}-shift",
                f"{dimension}-cont-reinf",
                f"{dimension}-intro",
                f"{dimension}-check",
                f"{dimension}-err",
            ]
        )
    fieldnames.append(".")
    fieldnames.extend(
        [
            ".",
            "E2_00_GridResponse",
            "E2_10_GridResponse",
            "E2_01_GridResponse",
            "E2_11_GridResponse",
            "Position-State Matrix Saturation Rate",
            ".",
        ]
    )
    return fieldnames


def write_audit_csv(path: Path, schema: ImportSchema, rows: list[AuditRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = build_audit_fieldnames(schema)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row_values = {
                "source_csv_path": row.source_csv_path,
                "row_index": row.row_index,
                "user": row.user,
                "username": row.username,
                "email_address": row.email_address,
                "participant_id": row.participant_id,
                "given_name": row.given_name,
                "family_name": row.family_name,
                "output_json_path": row.output_json_path,
                ".": "",
            }
            row_values.update(row.dimension_check_fields)
            row_values.update(row.position_state_matrix_fields)
            writer.writerow(row_values)


def build_audit_summary_report(schema: ImportSchema, rows: list[AuditRow]) -> str:
    position_state_matrix_labels = {
        "E2_00_GridResponse": {
            "position_state": "stable",
            "development_type": "shift",
        },
        "E2_10_GridResponse": {
            "position_state": "stable",
            "development_type": "continuity/reinforcement",
        },
        "E2_01_GridResponse": {
            "position_state": "in_tension",
            "development_type": "shift",
        },
        "E2_11_GridResponse": {
            "position_state": "in_tension",
            "development_type": "continuity/reinforcement",
        },
    }

    counts_by_dimension: dict[str, dict[str, int]] = {}
    for dimension in schema.dimensions:
        passed = 0
        none_selected = 0
        multiple_selected = 0

        for row in rows:
            check_value = row.dimension_check_fields[f"{dimension}-check"]
            error_value = row.dimension_check_fields[f"{dimension}-err"]
            if check_value == "true":
                passed += 1
            elif error_value == "none selected":
                none_selected += 1
            elif error_value == "multiple selected":
                multiple_selected += 1

        counts_by_dimension[dimension] = {
            "Passed": passed,
            "None Selected": none_selected,
            "Multiple Selected": multiple_selected,
        }

    header_cells = ["Check Status", *schema.dimensions]
    divider_cells = ["---", *("---:" for _ in schema.dimensions)]

    lines = [
        "# PPS1 Import Audit Summary",
        "",
        f"- Total imported rows: {len(rows)}",
        "",
        "## Dimensions : Devt Type Uniqueness",
        "",
        f"| {' | '.join(header_cells)} |",
        f"| {' | '.join(divider_cells)} |",
    ]

    for status_label in ("Passed", "None Selected", "Multiple Selected"):
        row_cells = [status_label]
        row_cells.extend(str(counts_by_dimension[dimension][status_label]) for dimension in schema.dimensions)
        lines.append(f"| {' | '.join(row_cells)} |")

    total_row_cells = ["Total"]
    total_row_cells.extend(
        str(
            counts_by_dimension[dimension]["Passed"]
            + counts_by_dimension[dimension]["None Selected"]
            + counts_by_dimension[dimension]["Multiple Selected"]
        )
        for dimension in schema.dimensions
    )
    lines.append(f"| {' | '.join(total_row_cells)} |")

    error_rate_row_cells = ["% Error Rate"]
    for dimension in schema.dimensions:
        total_count = (
            counts_by_dimension[dimension]["Passed"]
            + counts_by_dimension[dimension]["None Selected"]
            + counts_by_dimension[dimension]["Multiple Selected"]
        )
        error_count = (
            counts_by_dimension[dimension]["None Selected"]
            + counts_by_dimension[dimension]["Multiple Selected"]
        )
        error_rate = 0.0 if total_count == 0 else (error_count / total_count) * 100
        error_rate_row_cells.append(f"{error_rate:.1f}%")
    lines.append(f"| {' | '.join(error_rate_row_cells)} |")

    matrix_columns = [
        "E2_00_GridResponse",
        "E2_10_GridResponse",
        "E2_01_GridResponse",
        "E2_11_GridResponse",
    ]
    specified_counts = {column_name: 0 for column_name in matrix_columns}
    saturation_total = 0.0
    saturation_distribution = {4: 0, 3: 0, 2: 0, 1: 0, 0: 0}
    coverage_group_counts: dict[tuple[str, str], int] = {}

    for row in rows:
        specified_in_row = 0
        for column_name in matrix_columns:
            if row.position_state_matrix_fields[column_name]:
                specified_counts[column_name] += 1
                specified_in_row += 1
        saturation_value = row.position_state_matrix_fields["Position-State Matrix Saturation Rate"]
        saturation_total += float(saturation_value.rstrip("%"))
        saturation_distribution[specified_in_row] += 1

    for column_name in matrix_columns:
        position_state = position_state_matrix_labels[column_name]["position_state"]
        development_type = position_state_matrix_labels[column_name]["development_type"]
        coverage_group_counts[(position_state, development_type)] = specified_counts[column_name]

    average_saturation_rate = 0.0 if not rows else saturation_total / len(rows)

    lines.extend(
        [
            "",
            "## Position-State Matrix",
            "",
            "### Coverage",
            "",
            "| Metric | position_state | development_type | Count | % of Students |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for column_name in matrix_columns:
        specified_percent = 0.0 if not rows else (specified_counts[column_name] / len(rows)) * 100
        lines.append(
            f"| {column_name} specified | {position_state_matrix_labels[column_name]['position_state']} | {position_state_matrix_labels[column_name]['development_type']} | {specified_counts[column_name]} | {specified_percent:.1f}% |"
        )
    lines.append(f"| Average Saturation Rate |  |  |  | {average_saturation_rate:.1f}% |")
    lines.extend(
        [
            "",
            "| position_state | development_type | Count | % of Students |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    aggregate_rows = [
        ("stable", "shift", coverage_group_counts[("stable", "shift")], len(rows)),
        (
            "stable",
            "continuity/reinforcement",
            coverage_group_counts[("stable", "continuity/reinforcement")],
            len(rows),
        ),
        ("in_tension", "shift", coverage_group_counts[("in_tension", "shift")], len(rows)),
        (
            "in_tension",
            "continuity/reinforcement",
            coverage_group_counts[("in_tension", "continuity/reinforcement")],
            len(rows),
        ),
        (
            "stable",
            "*",
            coverage_group_counts[("stable", "shift")]
            + coverage_group_counts[("stable", "continuity/reinforcement")],
            len(rows) * 2,
        ),
        (
            "in_tension",
            "*",
            coverage_group_counts[("in_tension", "shift")]
            + coverage_group_counts[("in_tension", "continuity/reinforcement")],
            len(rows) * 2,
        ),
        (
            "*",
            "shift",
            coverage_group_counts[("stable", "shift")]
            + coverage_group_counts[("in_tension", "shift")],
            len(rows) * 2,
        ),
        (
            "*",
            "continuity/reinforcement",
            coverage_group_counts[("stable", "continuity/reinforcement")]
            + coverage_group_counts[("in_tension", "continuity/reinforcement")],
            len(rows) * 2,
        ),
        (
            "*",
            "*",
            sum(coverage_group_counts.values()),
            len(rows) * 4,
        ),
    ]
    for position_state, development_type, group_count, denominator in aggregate_rows:
        group_percent = 0.0 if denominator == 0 else (group_count / denominator) * 100
        lines.append(
            f"| {position_state} | {development_type} | {group_count} | {group_percent:.1f}% |"
        )
    lines.extend(
        [
            "",
            "### Saturation Distribution",
            "",
            "| Metric | All 4 | Only 3 | Only 2 | Only 1 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.append(
        "| Count | "
        f"{saturation_distribution[4]} | {saturation_distribution[3]} | {saturation_distribution[2]} | {saturation_distribution[1]} |"
    )
    lines.append(
        "| % of Students | "
        f"{((saturation_distribution[4] / len(rows)) * 100) if rows else 0.0:.1f}% | "
        f"{((saturation_distribution[3] / len(rows)) * 100) if rows else 0.0:.1f}% | "
        f"{((saturation_distribution[2] / len(rows)) * 100) if rows else 0.0:.1f}% | "
        f"{((saturation_distribution[1] / len(rows)) * 100) if rows else 0.0:.1f}% |"
    )

    lines.append("")
    return "\n".join(lines)


def write_audit_summary_report(path: Path, schema: ImportSchema, rows: list[AuditRow]) -> None:
    path.write_text(build_audit_summary_report(schema, rows), encoding="utf-8")


def clear_existing_json_files(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for json_path in directory.glob("*.json"):
        json_path.unlink()


def _select_augmented_sample(
    generated_records: list[GeneratedRecord],
    sample_size: int,
    chooser: random.Random | random.SystemRandom,
) -> list[GeneratedRecord]:
    if not generated_records:
        return []

    count = min(sample_size, len(generated_records))
    selected_records = list(chooser.sample(generated_records, count))
    selected_paths = {record.path for record in selected_records}

    dot_records = [record for record in generated_records if normalize_value(record.family_name) == "."]
    if dot_records:
        dot_record = chooser.choice(dot_records)
        if dot_record.path not in selected_paths:
            selected_records.append(dot_record)
            selected_paths.add(dot_record.path)

    longest_family_record = max(
        generated_records,
        key=lambda record: (len(normalize_value(record.family_name)), record.path.name),
    )
    if longest_family_record.path not in selected_paths:
        selected_records.append(longest_family_record)
        selected_paths.add(longest_family_record.path)

    longest_given_record = max(
        generated_records,
        key=lambda record: (len(normalize_value(record.given_name)), record.path.name),
    )
    if longest_given_record.path not in selected_paths:
        selected_records.append(longest_given_record)

    return selected_records


def duplicate_sample(
    generated_records: list[GeneratedRecord],
    sample_output_dir: Path,
    sample_size: int,
    sample_seed: int | None,
) -> list[Path]:
    sample_output_dir.mkdir(parents=True, exist_ok=True)
    if not generated_records or sample_size <= 0:
        return []
    chooser = random.Random(sample_seed) if sample_seed is not None else random.SystemRandom()
    selected_records = _select_augmented_sample(generated_records, sample_size, chooser)
    copied_paths: list[Path] = []
    for record in selected_records:
        target_path = sample_output_dir / record.path.name
        shutil.copy2(record.path, target_path)
        copied_paths.append(target_path)
    return copied_paths


def main() -> int:
    args = parse_args()
    schema = load_schema(args.schema_path)
    csv_path = resolve_runtime_value(args.csv_path, schema.import_defaults.csv_path)
    participants_csv_path = resolve_runtime_value(
        args.participants_csv_path,
        schema.import_defaults.participants_csv_path,
    )
    all_output_dir = resolve_runtime_value(args.all_output_dir, schema.import_defaults.all_output_dir)
    sample_output_dir = resolve_runtime_value(
        args.sample_output_dir,
        schema.import_defaults.sample_output_dir,
    )
    audit_path = resolve_runtime_value(args.audit_path, schema.import_defaults.audit_path)
    audit_summary_path = audit_path.with_suffix(".md")
    sample_size = resolve_runtime_value(args.sample_size, schema.import_defaults.sample_size)

    participant_lookup = load_participant_lookup(participants_csv_path)
    clear_existing_json_files(all_output_dir)
    clear_existing_json_files(sample_output_dir)

    generated_records: list[GeneratedRecord] = []
    audit_rows: list[AuditRow] = []
    used_names: set[str] = set()

    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header row: {csv_path}")

        for row_index, row in enumerate(reader, start=1):
            record = build_record(schema, row, participant_lookup)
            file_name = make_output_filename(schema, record, row, used_names, row_index)
            output_path = all_output_dir / file_name
            write_json(output_path, record)
            generated_records.append(
                GeneratedRecord(
                    path=output_path,
                    given_name=record.get(schema.identity_fields.given_name, ""),
                    family_name=record.get(schema.identity_fields.family_name, ""),
                )
            )
            audit_rows.append(
                AuditRow(
                    source_csv_path=str(csv_path),
                    row_index=row_index,
                    user=normalize_value(row.get("User")),
                    username=normalize_value(row.get("Username")),
                    email_address=normalize_value(row.get("Email address")),
                    participant_id=record.get(schema.identity_fields.participant_id, ""),
                    given_name=record.get(schema.identity_fields.given_name, ""),
                    family_name=record.get(schema.identity_fields.family_name, ""),
                    output_json_path=str(output_path),
                    dimension_check_fields=build_dimension_development_audit_fields(schema, row),
                    position_state_matrix_fields=build_position_state_matrix_audit_fields(row),
                )
            )
            if args.verbose:
                print(f"Wrote {output_path}")

    write_audit_csv(audit_path, schema, audit_rows)
    write_audit_summary_report(audit_summary_path, schema, audit_rows)

    copied_paths = duplicate_sample(
        generated_records=generated_records,
        sample_output_dir=sample_output_dir,
        sample_size=sample_size,
        sample_seed=args.sample_seed,
    )

    print(f"Wrote {len(generated_records)} JSON files to {all_output_dir}")
    print(f"Wrote import audit CSV to {audit_path}")
    print(f"Wrote import audit summary report to {audit_summary_path}")
    print(f"Copied {len(copied_paths)} sampled JSON files to {sample_output_dir}")
    if args.verbose and copied_paths:
        for copied_path in copied_paths:
            print(f"Sampled {copied_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())