#!/usr/bin/env python3
"""Generate rubric payload and scoring manifest markdown from Layer 1-4 registries.

This script reads a markdown registry, extracts Layer 1 indicator rows, Layer 2
dimension rows, Layer 3 component rows, or Layer 4 submission rows, and writes
two markdown outputs in the same directory by default. Layer 1 registries may
continue to use the existing wide markdown tables or the Base Table plus Reuse
Rule Table expansion model. Layers 2-4 are expected to provide explicit tables.

Default outputs:

- RUBRIC_<ASSESSMENT>_CAL_payload_<VERSION>.md for Layer 1
- RUBRIC_<ASSESSMENT>_CAL_payload_Layer2_<VERSION>.md for Layer 2
- RUBRIC_<ASSESSMENT>_CAL_payload_Layer3_<VERSION>.md for Layer 3
- RUBRIC_<ASSESSMENT>_CAL_payload_Layer4_<VERSION>.md for Layer 4
- <ASSESSMENT>_Layer1_ScoringManifest_<VERSION>.md
- <ASSESSMENT>_Layer2_ScoringManifest_<VERSION>.md
- <ASSESSMENT>_Layer3_ScoringManifest_<VERSION>.md
- <ASSESSMENT>_Layer4_ScoringManifest_<VERSION>.md

The generated documents follow the same structural conventions as the existing
pl1C_rubric_devt rubric payload and scoring manifest examples.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


COMMON_EXPLICIT_REQUIRED_COLUMNS = {
    "assessment_id",
    "component_id",
    "sbo_short_description",
}
LAYER1_REQUIRED_REGISTRY_COLUMNS = {
    "indicator_id",
    *COMMON_EXPLICIT_REQUIRED_COLUMNS,
    "indicator_definition",
    "assessment_guidance",
    "evaluation_notes",
}
LAYER1_BASE_TABLE_REQUIRED_COLUMNS = {
    "template_id",
    "local_slot",
    "sbo_short_description",
    "indicator_definition",
    "assessment_guidance",
    "evaluation_notes",
}
LAYER2_REQUIRED_REGISTRY_COLUMNS = {
    "dimension_id",
    *COMMON_EXPLICIT_REQUIRED_COLUMNS,
}
LAYER3_REQUIRED_REGISTRY_COLUMNS = {
    *COMMON_EXPLICIT_REQUIRED_COLUMNS,
}
LAYER4_REQUIRED_REGISTRY_COLUMNS = {
    "assessment_id",
    "sbo_short_description",
}
LAYER2_BASE_TABLE_REQUIRED_COLUMNS = {
    "dimension_template_id",
    "dimension_local_id",
    "sbo_short_description",
    "dimension_definition",
}
VERSION_TOKEN_RE = re.compile(r"_(v(?:_i)?\d+)\.md$", re.IGNORECASE)
SHORTID_NUMBER_RE = re.compile(r"(\d+)")
HEADING_RE = re.compile(r"^\s*(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")
LAYER2_RULE_HEADING_RE = re.compile(r"^\s*#{4,6}\s+(D\d+)\b")
BINDING_LINE_RE = re.compile(r"^\s*-\s+`([^`]+)`:\s*(.*?)\s*$")
FIELD_VALUE_TABLE_HEADERS = ["field", "value"]
SKIPPED_REUSE_RULE_STATUSES = {"inactive", "draft"}
KNOWN_COMPONENT_PERFORMANCE_ORDER = {
    "not_demonstrated": 0,
    "below_expectations": 1,
    "approaching_expectations": 2,
    "meets_expectations": 3,
    "exceeds_expectations": 4,
}
KNOWN_SUBMISSION_PERFORMANCE_ORDER = {
    "not_demonstrated": 0,
    "below_expectations": 1,
    "approaching_expectations": 2,
    "meets_expectations": 3,
    "exceeds_expectations": 4,
}


@dataclass(frozen=True)
class RegistryLayerConfig:
    name: str
    manifest_layer_label: str
    section_layer_label: str
    item_label: str
    item_id_field: str
    manifest_item_id_field: str
    explicit_required_columns: set[str]
    definition_field_candidates: tuple[str, ...]
    guidance_field_candidates: tuple[str, ...]
    output_definition_header: str
    output_guidance_header: str
    supports_base_table_reuse: bool
    rubric_filename_suffix: str
    manifest_includes_component_id: bool = True


@dataclass(frozen=True)
class RegistryRow:
    item_id: str
    sbo_identifier: str
    sbo_identifier_shortid: str
    assessment_id: str
    component_id: str
    sbo_short_description: str
    definition_text: str
    guidance_text: str
    evaluation_notes: str
    decision_procedure: str
    status: str
    template_id: str = ""
    evidence_scale: str = ""
    scoring_payload_json: str = ""


LAYER_CONFIGS = {
    "layer1": RegistryLayerConfig(
        name="layer1",
        manifest_layer_label="Layer1",
        section_layer_label="Layer 1",
        item_label="Indicator",
        item_id_field="indicator_id",
        manifest_item_id_field="indicator_id",
        explicit_required_columns=LAYER1_REQUIRED_REGISTRY_COLUMNS,
        definition_field_candidates=("indicator_definition",),
        guidance_field_candidates=("assessment_guidance",),
        output_definition_header="indicator_definition",
        output_guidance_header="assessment_guidance",
        supports_base_table_reuse=True,
        rubric_filename_suffix="",
    ),
    "layer2": RegistryLayerConfig(
        name="layer2",
        manifest_layer_label="Layer2",
        section_layer_label="Layer 2",
        item_label="Dimension",
        item_id_field="dimension_id",
        manifest_item_id_field="dimension_id",
        explicit_required_columns=LAYER2_REQUIRED_REGISTRY_COLUMNS,
        definition_field_candidates=("dimension_definition", "scoring_claim", "dimension_claim"),
        guidance_field_candidates=("dimension_guidance", "assessment_guidance", "dimension_notes"),
        output_definition_header="dimension_definition",
        output_guidance_header="dimension_guidance",
        supports_base_table_reuse=False,
        rubric_filename_suffix="_Layer2",
    ),
    "layer3": RegistryLayerConfig(
        name="layer3",
        manifest_layer_label="Layer3",
        section_layer_label="Layer 3",
        item_label="Component",
        item_id_field="component_id",
        manifest_item_id_field="",
        explicit_required_columns=LAYER3_REQUIRED_REGISTRY_COLUMNS,
        definition_field_candidates=("component_definition", "scoring_claim", "component_claim"),
        guidance_field_candidates=("component_guidance", "assessment_guidance", "component_notes"),
        output_definition_header="component_definition",
        output_guidance_header="component_guidance",
        supports_base_table_reuse=False,
        rubric_filename_suffix="_Layer3",
    ),
    "layer4": RegistryLayerConfig(
        name="layer4",
        manifest_layer_label="Layer4",
        section_layer_label="Layer 4",
        item_label="Submission",
        item_id_field="",
        manifest_item_id_field="",
        explicit_required_columns=LAYER4_REQUIRED_REGISTRY_COLUMNS,
        definition_field_candidates=("submission_definition", "scoring_claim", "submission_claim"),
        guidance_field_candidates=("submission_guidance", "assessment_guidance", "submission_notes"),
        output_definition_header="submission_definition",
        output_guidance_header="submission_guidance",
        supports_base_table_reuse=False,
        rubric_filename_suffix="_Layer4",
        manifest_includes_component_id=False,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate rubric and scoring manifest markdown from a Layer 1, 2, 3, or 4 registry."
    )
    parser.add_argument(
        "--registry",
        "--indicator-registry",
        dest="registry_path",
        type=Path,
        required=True,
        help="Path to the markdown registry file.",
    )
    parser.add_argument(
        "--registry-layer",
        choices=["auto", "layer1", "layer2", "layer3", "layer4"],
        default="auto",
        help="Registry layer to load. Defaults to auto-detection.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for generated outputs. Defaults to the registry file directory.",
    )
    parser.add_argument(
        "--rubric-output",
        type=Path,
        help="Explicit rubric output file path. Overrides --output-dir naming.",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        help="Explicit manifest output file path. Overrides --output-dir naming.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include rows whose status is not 'active'.",
    )
    return parser.parse_args()


def resolve_first_present(record: dict[str, str], field_names: tuple[str, ...]) -> str:
    for field_name in field_names:
        value = record.get(field_name, "").strip()
        if value:
            return value
    return ""


def infer_registry_layer(
    tables: list[dict[str, object]],
    requested_layer: str,
    registry_path: Path,
) -> RegistryLayerConfig:
    if requested_layer != "auto":
        return LAYER_CONFIGS[requested_layer]

    for table in tables:
        headers = {str(header).strip().lower() for header in table.get("headers", [])}
        if "dimension_id" in headers:
            return LAYER_CONFIGS["layer2"]
        if "indicator_id" in headers:
            return LAYER_CONFIGS["layer1"]
        if {"assessment_id", "component_id", "sbo_short_description"}.issubset(headers):
            if headers & {"component_definition", "component_guidance", "component_notes", "component_claim"}:
                return LAYER_CONFIGS["layer3"]
        if {"assessment_id", "sbo_short_description"}.issubset(headers) and "component_id" not in headers:
            if headers & {"submission_definition", "submission_guidance", "submission_notes", "submission_claim"}:
                return LAYER_CONFIGS["layer4"]

    base_table = find_table_by_heading(tables, "base table")
    reuse_table = find_table_by_heading(tables, "reuse rule table")
    if base_table is not None and reuse_table is not None:
        return LAYER_CONFIGS["layer1"]

    registry_name = registry_path.name.lower()
    if "layer3" in registry_name:
        return LAYER_CONFIGS["layer3"]
    if "layer4" in registry_name:
        return LAYER_CONFIGS["layer4"]

    raise ValueError(
        "Could not infer registry layer. Pass --registry-layer layer1, layer2, layer3, or layer4 explicitly."
    )


def normalize_markdown_cell(value: str) -> str:
    stripped = value.strip()
    if re.fullmatch(r"`[^`]*`", stripped):
        return stripped[1:-1].strip()
    return stripped


def parse_markdown_row(line: str) -> list[str]:
    parts = [part.strip() for part in line.strip().split("|")]
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [normalize_markdown_cell(part) for part in parts]


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    compact = [cell.replace(" ", "") for cell in cells]
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in compact)


def collect_markdown_tables(registry_path: Path) -> list[dict[str, object]]:
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    tables: list[dict[str, object]] = []
    current_heading = ""
    heading_path: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        heading_match = HEADING_RE.match(line)
        if heading_match:
            current_heading = heading_match.group("title").strip().lower()
            heading_level = len(heading_match.group("level"))
            heading_path = heading_path[: heading_level - 1]
            heading_path.append(current_heading)
            index += 1
            continue

        if "|" not in line:
            index += 1
            continue

        header_cells = parse_markdown_row(line)
        if not header_cells or index + 1 >= len(lines) or "|" not in lines[index + 1]:
            index += 1
            continue

        separator_cells = parse_markdown_row(lines[index + 1])
        if len(separator_cells) != len(header_cells) or not is_separator_row(separator_cells):
            index += 1
            continue

        headers = [cell.strip().lower() for cell in header_cells]
        row_records: list[dict[str, str]] = []
        index += 2
        while index < len(lines) and "|" in lines[index]:
            cells = parse_markdown_row(lines[index])
            if len(cells) != len(headers):
                break
            row_records.append(dict(zip(headers, cells, strict=True)))
            index += 1

        tables.append(
            {
                "heading": current_heading,
                "heading_path": list(heading_path),
                "headers": headers,
                "rows": row_records,
            }
        )

    return tables


def collect_markdown_sections(registry_path: Path) -> list[dict[str, object]]:
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    headings: list[dict[str, object]] = []
    heading_path: list[str] = []

    for index, line in enumerate(lines):
        heading_match = HEADING_RE.match(line)
        if heading_match is None:
            continue
        title = heading_match.group("title").strip()
        normalized_title = title.lower()
        heading_level = len(heading_match.group("level"))
        heading_path = heading_path[: heading_level - 1]
        heading_path.append(normalized_title)
        headings.append(
            {
                "index": index,
                "level": heading_level,
                "title": normalized_title,
                "raw_title": title,
                "heading_path": list(heading_path),
            }
        )

    sections: list[dict[str, object]] = []
    for heading_index, heading in enumerate(headings):
        end_index = len(lines)
        for next_heading in headings[heading_index + 1 :]:
            if int(next_heading["level"]) <= int(heading["level"]):
                end_index = int(next_heading["index"])
                break
        sections.append(
            {
                "title": heading["title"],
                "raw_title": heading["raw_title"],
                "level": heading["level"],
                "heading_path": heading["heading_path"],
                "content_lines": lines[int(heading["index"]) + 1 : end_index],
            }
        )
    return sections


def find_table_by_heading(tables: list[dict[str, object]], heading_text: str) -> dict[str, object] | None:
    normalized_heading = heading_text.strip().lower()
    for table in tables:
        if str(table["heading"]).strip().lower() == normalized_heading:
            return table
    return None


def find_tables_by_heading(
    tables: list[dict[str, object]],
    heading_text: str,
    include_descendants: bool = False,
) -> list[dict[str, object]]:
    normalized_heading = heading_text.strip().lower()
    matches: list[dict[str, object]] = []
    for table in tables:
        heading = str(table.get("heading", "")).strip().lower()
        heading_path = [str(item).strip().lower() for item in table.get("heading_path", [])]
        if heading == normalized_heading:
            matches.append(table)
            continue
        if include_descendants and normalized_heading in heading_path:
            matches.append(table)
    return matches


def find_section_by_title(sections: list[dict[str, object]], section_title: str) -> dict[str, object] | None:
    normalized_title = section_title.strip().lower()
    for section in sections:
        if str(section.get("title", "")).strip().lower() == normalized_title:
            return section
    return None


def extract_section_text(section: dict[str, object] | None) -> str:
    if section is None:
        return ""
    prose_lines: list[str] = []
    bullet_lines: list[str] = []
    for raw_line in section.get("content_lines", []):
        stripped_line = str(raw_line).strip()
        if not stripped_line or stripped_line == "---" or stripped_line.startswith("|"):
            continue
        if stripped_line.startswith("- "):
            bullet_lines.append(stripped_line[2:].strip())
            continue
        prose_lines.append(stripped_line)
    parts: list[str] = []
    if prose_lines:
        parts.append(" ".join(prose_lines))
    if bullet_lines:
        parts.append("; ".join(bullet_lines))
    return " ".join(part for part in parts if part).strip()


def format_rule_summary(table: dict[str, object] | None) -> str:
    if table is None:
        return ""
    headers = [str(header).strip() for header in table.get("headers", [])]
    if len(headers) < 2:
        return ""
    outcome_field = headers[0]
    condition_fields = headers[1:]
    grouped_conditions: dict[str, list[str]] = {}
    for row in table.get("rows", []):
        outcome_value = str(row.get(outcome_field, "")).strip()
        if not outcome_value:
            continue
        condition_text = ", ".join(
            f"{field}={str(row.get(field, '')).strip()}"
            for field in condition_fields
            if str(row.get(field, "")).strip()
        )
        if not condition_text:
            continue
        grouped_conditions.setdefault(outcome_value, []).append(condition_text)
    if not grouped_conditions:
        return ""
    return "; ".join(
        f"{outcome_value} when " + " or ".join(conditions)
        for outcome_value, conditions in grouped_conditions.items()
    )


def format_binding_summary(row: dict[str, str] | None, key_field: str) -> str:
    if row is None:
        return ""
    binding_items = [
        f"{field}={value.strip()}"
        for field, value in row.items()
        if field != key_field and value.strip()
    ]
    return ", ".join(binding_items)


def build_layer3_registry_enrichment(
    tables: list[dict[str, object]],
    sections: list[dict[str, object]],
) -> dict[str, dict[str, str]]:
    summary_intro = extract_section_text(find_section_by_title(sections, "registry summary"))
    execution_note = extract_section_text(find_section_by_title(sections, "execution note"))
    target_sbo_class = extract_section_text(find_section_by_title(sections, "target sbo class"))
    input_sbo_class = extract_section_text(find_section_by_title(sections, "input sbo class"))
    summary_table = find_table_by_heading(tables, "registry summary")
    bindings_table = find_table_by_heading(tables, "dimension bindings")
    rule_table = find_table_by_heading(tables, "component scoring rule")
    rule_summary = format_rule_summary(rule_table)

    summary_rows_by_component = {
        row.get("component_id", "").strip(): row
        for row in (summary_table or {}).get("rows", [])
        if row.get("component_id", "").strip()
    }
    binding_rows_by_component = {
        row.get("component_id", "").strip(): row
        for row in (bindings_table or {}).get("rows", [])
        if row.get("component_id", "").strip()
    }

    enrichment: dict[str, dict[str, str]] = {}
    for component_id, summary_row in summary_rows_by_component.items():
        dimensions_text = summary_row.get("dimensions", "").strip()
        binding_summary = format_binding_summary(binding_rows_by_component.get(component_id), "component_id")
        definition_parts = [
            f"Derives {target_sbo_class} from {input_sbo_class}." if target_sbo_class and input_sbo_class else "",
            summary_intro,
            f"Input dimensions for {component_id}: {dimensions_text}." if dimensions_text else "",
        ]
        evaluation_notes_parts = [
            f"Dimension bindings: {binding_summary}." if binding_summary else "",
            execution_note,
        ]
        decision_parts = [
            "Apply the component scoring rule defined in the registry.",
            rule_summary,
            f"Use bindings {binding_summary}." if binding_summary else "",
        ]
        enrichment[component_id] = {
            "component_definition": " ".join(part for part in definition_parts if part).strip(),
            "component_guidance": execution_note,
            "evaluation_notes": " ".join(part for part in evaluation_notes_parts if part).strip(),
            "decision_procedure": " ".join(part for part in decision_parts if part).strip(),
        }
    return enrichment


def build_layer4_registry_enrichment(
    tables: list[dict[str, object]],
    sections: list[dict[str, object]],
) -> dict[str, dict[str, str]]:
    summary_intro = extract_section_text(find_section_by_title(sections, "registry summary"))
    execution_note = extract_section_text(find_section_by_title(sections, "execution note"))
    target_sbo_class = extract_section_text(find_section_by_title(sections, "target sbo class"))
    input_sbo_class = extract_section_text(find_section_by_title(sections, "input sbo class"))
    summary_table = find_table_by_heading(tables, "registry summary")
    bindings_table = find_table_by_heading(tables, "component bindings")
    rule_table = find_table_by_heading(tables, "submission scoring rule")
    rule_summary = format_rule_summary(rule_table)

    summary_rows_by_assessment = {
        row.get("assessment_id", "").strip(): row
        for row in (summary_table or {}).get("rows", [])
        if row.get("assessment_id", "").strip()
    }
    binding_rows_by_assessment = {
        row.get("assessment_id", "").strip(): row
        for row in (bindings_table or {}).get("rows", [])
        if row.get("assessment_id", "").strip()
    }

    enrichment: dict[str, dict[str, str]] = {}
    for assessment_id, summary_row in summary_rows_by_assessment.items():
        input_components_text = summary_row.get("input components", "").strip()
        binding_summary = format_binding_summary(binding_rows_by_assessment.get(assessment_id), "assessment_id")
        definition_parts = [
            f"Derives {target_sbo_class} from {input_sbo_class}." if target_sbo_class and input_sbo_class else "",
            summary_intro,
            f"Input components for {assessment_id}: {input_components_text}." if input_components_text else "",
        ]
        evaluation_notes_parts = [
            f"Component bindings: {binding_summary}." if binding_summary else "",
            execution_note,
        ]
        decision_parts = [
            "Apply the submission scoring rule defined in the registry.",
            rule_summary,
            f"Use bindings {binding_summary}." if binding_summary else "",
        ]
        enrichment[assessment_id] = {
            "submission_definition": " ".join(part for part in definition_parts if part).strip(),
            "submission_guidance": execution_note,
            "evaluation_notes": " ".join(part for part in evaluation_notes_parts if part).strip(),
            "decision_procedure": " ".join(part for part in decision_parts if part).strip(),
        }
    return enrichment


def build_registry_enrichment_lookup(
    registry_path: Path,
    tables: list[dict[str, object]],
    layer_config: RegistryLayerConfig,
) -> dict[str, dict[str, str]]:
    if layer_config.name not in {"layer3", "layer4"}:
        return {}
    sections = collect_markdown_sections(registry_path)
    if layer_config.name == "layer3":
        return build_layer3_registry_enrichment(tables, sections)
    return build_layer4_registry_enrichment(tables, sections)


def is_field_value_table(table: dict[str, object]) -> bool:
    headers = [str(header).strip().lower() for header in table.get("headers", [])]
    return headers == FIELD_VALUE_TABLE_HEADERS


def convert_field_value_table_to_record(table: dict[str, object]) -> dict[str, str]:
    if not is_field_value_table(table):
        raise ValueError("Table is not a field/value record table.")

    record: dict[str, str] = {}
    for row in table.get("rows", []):
        field_name = str(row.get("field", "")).strip().lower()
        if not field_name:
            continue
        if field_name in record:
            raise ValueError(f"Duplicate field {field_name!r} in field/value record table.")
        record[field_name] = str(row.get("value", "")).strip()
    return record


def collect_section_rows(
    tables: list[dict[str, object]],
    heading_text: str,
    *,
    required_columns: set[str],
    allow_field_value_records: bool = False,
    include_descendants: bool = True,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table in find_tables_by_heading(tables, heading_text, include_descendants=include_descendants):
        headers = {str(header).strip().lower() for header in table.get("headers", [])}
        if required_columns.issubset(headers):
            rows.extend(list(table.get("rows", [])))
            continue
        if allow_field_value_records and is_field_value_table(table):
            record = convert_field_value_table_to_record(table)
            if record:
                rows.append(record)
    return rows


def validate_required_columns(
    table_name: str,
    rows: list[dict[str, str]],
    required_columns: set[str],
) -> None:
    for row_index, row in enumerate(rows, start=1):
        missing_columns = sorted(column for column in required_columns if column not in row)
        if missing_columns:
            row_label = (
                row.get("template_id", "").strip()
                or row.get("indicator_id", "").strip()
                or row.get("dimension_id", "").strip()
                or str(row_index)
            )
            raise ValueError(f"{table_name} row {row_label!r} is missing required column(s): {missing_columns}")


def resolve_definition_text(record: dict[str, str], layer_config: RegistryLayerConfig) -> str:
    return resolve_first_present(record, layer_config.definition_field_candidates)


def resolve_guidance_text(record: dict[str, str], layer_config: RegistryLayerConfig) -> str:
    return resolve_first_present(record, layer_config.guidance_field_candidates)


def resolve_scale_text(record: dict[str, str], layer_config: RegistryLayerConfig) -> str:
    if layer_config.name == "layer2":
        return record.get("dimension_evidence_scale", "").strip()
    if layer_config.name == "layer3":
        return record.get("component_performance_scale", "").strip()
    if layer_config.name == "layer4":
        return record.get("submission_performance_scale", "").strip()
    return ""


def resolve_scoring_payload_json(record: dict[str, str], layer_config: RegistryLayerConfig) -> str:
    if layer_config.name == "layer2":
        return record.get("dimension_scoring_payload_json", "").strip()
    if layer_config.name == "layer3":
        return record.get("component_scoring_payload_json", "").strip()
    if layer_config.name == "layer4":
        return record.get("submission_scoring_payload_json", "").strip()
    return ""


def extract_registry_metadata(tables: list[dict[str, object]]) -> dict[str, str]:
    metadata_table = find_table_by_heading(tables, "registry metadata")
    if metadata_table is None:
        return {}

    headers = list(metadata_table["headers"])
    if headers != ["field", "value"]:
        return {}

    metadata: dict[str, str] = {}
    for row in metadata_table["rows"]:
        field_name = row.get("field", "").strip()
        if field_name:
            metadata[field_name] = row.get("value", "").strip()
    return metadata


def serialize_scoring_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def derive_ordered_scale_values(values: list[str], known_order: dict[str, int]) -> list[str]:
    normalized_values = [value.strip() for value in values if value.strip()]
    deduplicated_values = list(dict.fromkeys(normalized_values))
    if deduplicated_values and all(value in known_order for value in deduplicated_values):
        return sorted(deduplicated_values, key=lambda value: known_order[value])
    return deduplicated_values


def normalize_scale_token(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def parse_layer2_scoring_payloads(registry_path: Path) -> dict[tuple[str, str], str]:
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    in_layer2_value_derivation = False
    payloads: dict[tuple[str, str], str] = {}
    index = 0

    while index < len(lines):
        line = lines[index]
        heading_match = HEADING_RE.match(line)
        if heading_match:
            heading_title = heading_match.group("title").strip().lower()
            if heading_title == "layer 2 value derivation":
                in_layer2_value_derivation = True
                index += 1
                continue

        if not in_layer2_value_derivation:
            index += 1
            continue

        template_heading_match = LAYER2_RULE_HEADING_RE.match(line)
        if template_heading_match is None:
            index += 1
            continue

        dimension_template_id = template_heading_match.group(1)
        index += 1

        while index + 1 < len(lines):
            if HEADING_RE.match(lines[index]) and LAYER2_RULE_HEADING_RE.match(lines[index]):
                break
            if "|" not in lines[index] or "|" not in lines[index + 1]:
                index += 1
                continue
            header_cells = parse_markdown_row(lines[index])
            separator_cells = parse_markdown_row(lines[index + 1])
            if not header_cells or len(header_cells) != len(separator_cells) or not is_separator_row(separator_cells):
                index += 1
                continue

            headers = [cell.strip() for cell in header_cells]
            rule_rows: list[dict[str, str]] = []
            cursor = index + 2
            while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
                cells = parse_markdown_row(lines[cursor])
                if len(cells) != len(headers):
                    break
                rule_rows.append({headers[cell_index]: cells[cell_index].strip() for cell_index in range(len(headers))})
                cursor += 1

            bindings_by_component: dict[str, list[str]] = {}
            while cursor < len(lines):
                stripped_line = lines[cursor].strip()
                if not stripped_line:
                    cursor += 1
                    continue
                if stripped_line == "---":
                    cursor += 1
                    break
                if HEADING_RE.match(lines[cursor]):
                    break
                if stripped_line.lower() == "bindings:":
                    cursor += 1
                    continue
                binding_match = BINDING_LINE_RE.match(lines[cursor])
                if binding_match is not None:
                    component_id = binding_match.group(1).strip()
                    bound_indicator_ids = re.findall(r"`([^`]+)`", binding_match.group(2))
                    bindings_by_component[component_id] = [indicator_id.strip() for indicator_id in bound_indicator_ids]
                    cursor += 1
                    continue
                cursor += 1

            input_indicator_tokens = headers[1:]
            normalized_rule_rows = [
                {
                    "resultant_scale_value": row[headers[0]],
                    "conditions": {token: row.get(token, "").strip() for token in input_indicator_tokens},
                }
                for row in rule_rows
            ]
            for component_id, bound_indicator_ids in bindings_by_component.items():
                payload = {
                    "dimension_template_id": dimension_template_id,
                    "input_indicator_tokens": input_indicator_tokens,
                    "bound_indicator_ids": bound_indicator_ids,
                    "derivation_rules": normalized_rule_rows,
                }
                payloads[(component_id, dimension_template_id)] = serialize_scoring_payload(payload)

            index = cursor
            break

    return payloads


def parse_layer3_scoring_payloads(registry_path: Path) -> dict[str, dict[str, str]]:
    tables = collect_markdown_tables(registry_path)
    rule_table = find_table_by_heading(tables, "component scoring rule")
    bindings_table = find_table_by_heading(tables, "dimension bindings")
    if rule_table is None or bindings_table is None:
        return {}

    rule_headers = [str(header).strip() for header in rule_table.get("headers", [])]
    if len(rule_headers) < 2:
        return {}

    token_headers = rule_headers[1:]
    derivation_rules = [
        {
            "resultant_scale_value": str(row.get(rule_headers[0], "")).strip(),
            "conditions": {
                token: str(row.get(token, "")).strip()
                for token in token_headers
            },
        }
        for row in rule_table.get("rows", [])
        if str(row.get(rule_headers[0], "")).strip()
    ]
    performance_scale = derive_ordered_scale_values(
        [rule["resultant_scale_value"] for rule in derivation_rules],
        KNOWN_COMPONENT_PERFORMANCE_ORDER,
    )

    payloads: dict[str, dict[str, str]] = {}
    for row in bindings_table.get("rows", []):
        component_id = str(row.get("component_id", "")).strip()
        if not component_id:
            continue
        bound_dimension_ids = [str(row.get(token, "")).strip() for token in token_headers]
        payload = {
            "component_id": component_id,
            "input_dimension_tokens": token_headers,
            "bound_dimension_ids": bound_dimension_ids,
            "derivation_rules": derivation_rules,
        }
        payloads[component_id] = {
            "component_scoring_payload_json": serialize_scoring_payload(payload),
            "component_performance_scale": ", ".join(performance_scale),
        }
    return payloads


def parse_layer4_scoring_payloads(registry_path: Path) -> dict[str, dict[str, str]]:
    tables = collect_markdown_tables(registry_path)
    bindings_table = find_table_by_heading(tables, "component bindings")
    component_value_table = find_table_by_heading(tables, "component value mapping")
    cutpoint_table = find_table_by_heading(tables, "numeric cutpoint table")
    if bindings_table is None or component_value_table is None or cutpoint_table is None:
        return {}

    component_value_map: dict[str, float] = {}
    for row in component_value_table.get("rows", []):
        raw_level = str(row.get("component level", "")).strip()
        raw_numeric_value = str(row.get("numeric value", "")).strip()
        if not raw_level or not raw_numeric_value:
            continue
        component_value_map[normalize_scale_token(raw_level)] = float(raw_numeric_value)
    if not component_value_map:
        return {}

    numeric_cutpoints: list[dict[str, object]] = []
    for row in cutpoint_table.get("rows", []):
        raw_scale_value = str(row.get("resultant scale value", "")).strip()
        raw_minimum = str(row.get("numeric minimum", "")).strip()
        raw_maximum = str(row.get("numeric maximum", "")).strip()
        if not raw_scale_value or not raw_minimum or not raw_maximum:
            continue
        numeric_cutpoints.append(
            {
                "resultant_scale_value": normalize_scale_token(raw_scale_value),
                "numeric_minimum": float(raw_minimum),
                "numeric_maximum": float(raw_maximum),
            }
        )
    if not numeric_cutpoints:
        return {}

    performance_scale = derive_ordered_scale_values(
        [str(cutpoint["resultant_scale_value"]) for cutpoint in numeric_cutpoints],
        KNOWN_SUBMISSION_PERFORMANCE_ORDER,
    )

    payloads: dict[str, dict[str, str]] = {}
    for row in bindings_table.get("rows", []):
        assessment_id = str(row.get("assessment_id", "")).strip()
        if not assessment_id:
            continue
        component_tokens = [str(header).strip() for header in bindings_table.get("headers", []) if str(header).strip() and str(header).strip() != "assessment_id"]
        component_bindings = {
            token: str(row.get(token, "")).strip()
            for token in component_tokens
            if str(row.get(token, "")).strip()
        }
        payload = {
            "assessment_id": assessment_id,
            "input_component_tokens": component_tokens,
            "component_bindings": component_bindings,
            "bound_component_ids": list(component_bindings.values()),
            "component_value_map": component_value_map,
            "numeric_cutpoints": numeric_cutpoints,
        }
        payloads[assessment_id] = {
            "submission_scoring_payload_json": serialize_scoring_payload(payload),
            "submission_performance_scale": ", ".join(performance_scale),
        }
    return payloads


def build_registry_rows_from_explicit_table(
    table_rows: list[dict[str, str]],
    include_inactive: bool,
    layer_config: RegistryLayerConfig,
    enrichment_lookup: dict[str, dict[str, str]] | None = None,
) -> list[RegistryRow]:
    rows: list[RegistryRow] = []
    for record in table_rows:
        status = record.get("status", "").strip().lower()
        if not include_inactive and status and status != "active":
            continue
        item_id = record.get(layer_config.item_id_field, "").strip() if layer_config.item_id_field else ""
        enrichment_key = (
            record.get("component_id", "").strip()
            if layer_config.name == "layer3"
            else record.get("assessment_id", "").strip()
            if layer_config.name == "layer4"
            else item_id
        )
        merged_record = dict((enrichment_lookup or {}).get(enrichment_key, {}))
        merged_record.update(record)
        rows.append(
            RegistryRow(
                item_id=item_id,
                assessment_id=merged_record["assessment_id"].strip(),
                component_id=merged_record.get("component_id", "").strip(),
                sbo_identifier=resolve_sbo_identifier(merged_record),
                sbo_identifier_shortid=resolve_sbo_identifier_shortid(merged_record),
                sbo_short_description=merged_record["sbo_short_description"].strip(),
                definition_text=resolve_definition_text(merged_record, layer_config),
                guidance_text=resolve_guidance_text(merged_record, layer_config),
                evaluation_notes=merged_record.get("evaluation_notes", "").strip(),
                decision_procedure=resolve_decision_procedure(merged_record),
                status=merged_record.get("status", ""),
                evidence_scale=resolve_scale_text(merged_record, layer_config),
                scoring_payload_json=resolve_scoring_payload_json(merged_record, layer_config),
            )
        )
    return rows


def build_layer2_rows_from_instance_and_base_tables(
    instance_rows: list[dict[str, str]],
    base_rows: list[dict[str, str]],
    scoring_payloads_by_component_template: dict[tuple[str, str], str],
    include_inactive: bool,
    layer_config: RegistryLayerConfig,
) -> list[RegistryRow]:
    base_by_template_id = {
        row.get("dimension_template_id", "").strip(): row
        for row in base_rows
        if row.get("dimension_template_id", "").strip()
    }

    rows: list[RegistryRow] = []
    for instance_row in instance_rows:
        status = instance_row.get("status", "").strip().lower()
        if not include_inactive and status and status != "active":
            continue

        dimension_template_id = instance_row.get("dimension_template_id", "").strip()
        merged_record = dict(base_by_template_id.get(dimension_template_id, {}))
        merged_record.update(instance_row)
        scoring_payload_json = scoring_payloads_by_component_template.get(
            (merged_record["component_id"].strip(), dimension_template_id),
            "",
        )

        rows.append(
            RegistryRow(
                item_id=merged_record[layer_config.item_id_field].strip(),
                assessment_id=merged_record["assessment_id"].strip(),
                component_id=merged_record["component_id"].strip(),
                sbo_identifier=resolve_sbo_identifier(merged_record),
                sbo_identifier_shortid=resolve_sbo_identifier_shortid(merged_record),
                sbo_short_description=merged_record["sbo_short_description"].strip(),
                definition_text=resolve_definition_text(merged_record, layer_config),
                guidance_text=resolve_guidance_text(merged_record, layer_config),
                evaluation_notes=merged_record.get("evaluation_notes", "").strip(),
                decision_procedure=resolve_decision_procedure(merged_record),
                status=merged_record.get("status", ""),
                template_id=dimension_template_id,
                evidence_scale=merged_record.get("dimension_evidence_scale", "").strip(),
                scoring_payload_json=scoring_payload_json,
            )
        )

    return rows


def resolve_decision_procedure(record: dict[str, str]) -> str:
    return record.get("decision_procedure", "").strip()


def should_skip_reuse_rule_row(reuse_row: dict[str, str], include_inactive: bool) -> bool:
    if include_inactive:
        return False
    return reuse_row.get("status", "").strip().lower() in SKIPPED_REUSE_RULE_STATUSES


def build_registry_rows_from_base_and_reuse_tables(
    base_rows: list[dict[str, str]],
    reuse_rows: list[dict[str, str]],
    registry_metadata: dict[str, str],
    include_inactive: bool,
    layer_config: RegistryLayerConfig,
) -> list[RegistryRow]:
    base_by_template_id = {
        row.get("template_id", "").strip(): row for row in base_rows if row.get("template_id", "").strip()
    }
    base_by_local_slot = {
        row.get("local_slot", "").strip(): row for row in base_rows if row.get("local_slot", "").strip()
    }

    rows: list[RegistryRow] = []
    for reuse_row in reuse_rows:
        if should_skip_reuse_rule_row(reuse_row, include_inactive):
            continue

        template_id = reuse_row.get("template_id", "").strip()
        local_slot = reuse_row.get("local_slot", "").strip()
        base_row = None
        if template_id:
            base_row = base_by_template_id.get(template_id)
        if base_row is None and local_slot:
            base_row = base_by_local_slot.get(local_slot)
        if base_row is None:
            raise ValueError(
                "Reuse Rule Table row could not be joined to Base Table. "
                f"template_id={template_id or '<empty>'} local_slot={local_slot or '<empty>'}"
            )

        assessment_id = (
            reuse_row.get("assessment_id", "").strip()
            or registry_metadata.get("assessment_id", "").strip()
        )
        if not assessment_id:
            raise ValueError("Assessment ID is required in either registry metadata or the Reuse Rule Table.")

        merged_record = dict(base_row)
        merged_record.update(reuse_row)
        merged_record["assessment_id"] = assessment_id

        effective_status = (
            reuse_row.get("status", "").strip()
            or base_row.get("status", "").strip()
        )
        if not include_inactive and effective_status and effective_status.lower() != "active":
            continue

        rows.append(
            RegistryRow(
                item_id=merged_record[layer_config.item_id_field],
                assessment_id=assessment_id,
                component_id=merged_record["component_id"],
                sbo_identifier=resolve_sbo_identifier(merged_record),
                sbo_identifier_shortid=resolve_sbo_identifier_shortid(merged_record),
                sbo_short_description=merged_record["sbo_short_description"],
                definition_text=resolve_definition_text(merged_record, layer_config),
                guidance_text=resolve_guidance_text(merged_record, layer_config),
                evaluation_notes=merged_record["evaluation_notes"],
                decision_procedure=resolve_decision_procedure(merged_record),
                status=effective_status,
            )
        )

    return rows


def extract_rule_template(rule_text: str) -> str:
    match = re.search(r"`([^`]+)`", rule_text)
    if match:
        return match.group(1).strip()
    return rule_text.split(" where ", 1)[0].strip()


def expand_component_pattern(pattern: str) -> list[tuple[str, dict[str, str]]]:
    match = re.search(r"\{(\d+)\.\.(\d+)\}", pattern)
    if not match:
        return [(pattern.strip(), {})]

    start = int(match.group(1))
    end = int(match.group(2))
    prefix = pattern[: match.start()]
    suffix = pattern[match.end() :]

    expanded: list[tuple[str, dict[str, str]]] = []
    for number in range(start, end + 1):
        expanded.append((f"{prefix}{number}{suffix}", {"claim_index": str(number)}))
    return expanded


def apply_token_template(template: str, values: dict[str, str]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def resolve_component_block_lookup(component_block_rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    for row in component_block_rows:
        block_rule_id = row.get("block_rule_id", "").strip()
        component_id = row.get("component_id", "").strip()
        component_block = row.get("component_block", "").strip()
        if block_rule_id and component_id and component_block:
            lookup[(block_rule_id, component_id)] = component_block
    return lookup


def resolve_local_slot_values(base_row: dict[str, str], local_slot_source: str) -> dict[str, str]:
    local_slot = base_row.get("local_slot", "").strip()
    if not local_slot:
        raise ValueError("Base Table row is missing local_slot.")

    if local_slot_source and local_slot_source != "template.local_slot":
        raise ValueError(f"Unsupported local_slot_source: {local_slot_source}")

    if re.fullmatch(r"\d+", local_slot):
        local_slot_numeric = str(int(local_slot))
    elif re.fullmatch(r"0[A-Za-z0-9]+", local_slot):
        local_slot_numeric = local_slot[1:]
    else:
        local_slot_numeric = local_slot

    return {
        "local_slot": local_slot,
        "local_slot_int": local_slot_numeric,
    }


def evaluate_placeholder_expression(expression: str, values: dict[str, str]) -> str:
    tokens = [token.strip() for token in expression.split("+")]
    if not tokens:
        return ""

    resolved_terms: list[str] = []
    all_numeric = True
    for token in tokens:
        if not token:
            continue
        value = values.get(token, token)
        resolved_terms.append(value)
        if not re.fullmatch(r"-?\d+", value):
            all_numeric = False

    if all_numeric and resolved_terms:
        return str(sum(int(term) for term in resolved_terms))
    return "".join(resolved_terms)


def apply_expression_template(template: str, values: dict[str, str]) -> str:
    return re.sub(
        r"\{([^{}]+)\}",
        lambda match: evaluate_placeholder_expression(match.group(1).strip(), values),
        template,
    )


def build_registry_rows_from_rule_based_reuse_table(
    base_rows: list[dict[str, str]],
    reuse_rows: list[dict[str, str]],
    registry_metadata: dict[str, str],
    include_inactive: bool,
    layer_config: RegistryLayerConfig,
) -> list[RegistryRow]:
    rows: list[RegistryRow] = []
    available_template_groups = sorted(
        {
            template_id.rsplit("_", 1)[0]
            for template_id in (
                row.get("template_id", "").strip()
                for row in base_rows
            )
            if template_id and "_" in template_id
        }
    )

    for reuse_row in reuse_rows:
        if should_skip_reuse_rule_row(reuse_row, include_inactive):
            continue

        template_group = reuse_row.get("template_group", "").strip()
        if not template_group:
            raise ValueError("Reuse Rule Table must include template_group for rule-based expansion.")

        matching_base_rows = [
            row for row in base_rows if row.get("template_id", "").strip().startswith(f"{template_group}_")
        ]
        if not matching_base_rows:
            raise ValueError(
                "No Base Table rows matched Reuse Rule Table template_group="
                f"{template_group!r}. Available Base Table groups: {available_template_groups}"
            )

        assessment_id = reuse_row.get("assessment_id", "").strip() or registry_metadata.get("assessment_id", "").strip()
        if not assessment_id:
            raise ValueError("Assessment ID is required in either registry metadata or the Reuse Rule Table.")

        component_pattern = reuse_row.get("applies_to_component_pattern", "").strip()
        if not component_pattern:
            raise ValueError("Reuse Rule Table must include applies_to_component_pattern for rule-based expansion.")

        item_id_rule_field = f"{layer_config.item_id_field}_rule"
        item_id_template = extract_rule_template(reuse_row.get(item_id_rule_field, "").strip())
        if not item_id_template:
            raise ValueError(f"Reuse Rule Table must include {item_id_rule_field} for rule-based expansion.")

        reuse_status = reuse_row.get("status", "").strip()
        for component_id, template_values in expand_component_pattern(component_pattern):
            for base_row in matching_base_rows:
                effective_status = reuse_status or base_row.get("status", "").strip()
                if not include_inactive and effective_status and effective_status.lower() != "active":
                    continue

                local_slot = base_row.get("local_slot", "").strip()
                item_id = apply_token_template(
                    item_id_template,
                    {
                        **template_values,
                        "local_slot": local_slot,
                    },
                )

                merged_record = dict(base_row)
                merged_record.update(reuse_row)
                merged_record["assessment_id"] = assessment_id
                merged_record["component_id"] = component_id
                merged_record[layer_config.item_id_field] = item_id

                rows.append(
                    RegistryRow(
                        item_id=item_id,
                        assessment_id=assessment_id,
                        component_id=component_id,
                        sbo_identifier=resolve_sbo_identifier(merged_record),
                        sbo_identifier_shortid=resolve_sbo_identifier_shortid(merged_record),
                        sbo_short_description=base_row["sbo_short_description"],
                        definition_text=resolve_definition_text(base_row, layer_config),
                        guidance_text=resolve_guidance_text(base_row, layer_config),
                        evaluation_notes=base_row["evaluation_notes"],
                        decision_procedure=resolve_decision_procedure(base_row),
                        status=effective_status,
                    )
                )

    return rows


def build_registry_rows_from_component_block_reuse_table(
    base_rows: list[dict[str, str]],
    reuse_rows: list[dict[str, str]],
    component_block_rows: list[dict[str, str]],
    registry_metadata: dict[str, str],
    include_inactive: bool,
    layer_config: RegistryLayerConfig,
) -> list[RegistryRow]:
    rows: list[RegistryRow] = []
    component_block_lookup = resolve_component_block_lookup(component_block_rows)
    available_template_groups = sorted(
        {
            template_id.rsplit("_", 1)[0]
            for template_id in (
                row.get("template_id", "").strip()
                for row in base_rows
            )
            if template_id and "_" in template_id
        }
    )

    for reuse_row in reuse_rows:
        if should_skip_reuse_rule_row(reuse_row, include_inactive):
            continue

        template_group = reuse_row.get("template_group", "").strip()
        if not template_group:
            raise ValueError("Reuse Rule Table must include template_group for rule-based expansion.")

        matching_base_rows = [
            row for row in base_rows if row.get("template_id", "").strip().startswith(f"{template_group}_")
        ]
        if not matching_base_rows:
            raise ValueError(
                "No Base Table rows matched Reuse Rule Table template_group="
                f"{template_group!r}. Available Base Table groups: {available_template_groups}"
            )

        assessment_id = reuse_row.get("assessment_id", "").strip() or registry_metadata.get("assessment_id", "").strip()
        if not assessment_id:
            raise ValueError("Assessment ID is required in either registry metadata or the Reuse Rule Table.")

        component_pattern = reuse_row.get("applies_to_component_pattern", "").strip()
        if not component_pattern:
            raise ValueError("Reuse Rule Table must include applies_to_component_pattern for rule-based expansion.")

        component_block_rule = reuse_row.get("component_block_rule", "").strip()
        if not component_block_rule:
            raise ValueError("Reuse Rule Table must include component_block_rule for component-block expansion.")

        item_id_format_field = f"{layer_config.item_id_field}_format"
        item_id_format = reuse_row.get(item_id_format_field, "").strip()
        if not item_id_format:
            raise ValueError(f"Reuse Rule Table must include {item_id_format_field} for component-block expansion.")

        local_slot_source = reuse_row.get("local_slot_source", "").strip()
        reuse_status = reuse_row.get("status", "").strip()

        for component_id, template_values in expand_component_pattern(component_pattern):
            component_block = component_block_lookup.get((component_block_rule, component_id))
            if component_block is None:
                raise ValueError(
                    "Component block rule table could not resolve component_block for "
                    f"block_rule_id={component_block_rule!r}, component_id={component_id!r}"
                )

            for base_row in matching_base_rows:
                effective_status = reuse_status or base_row.get("status", "").strip()
                if not include_inactive and effective_status and effective_status.lower() != "active":
                    continue

                expression_values = {
                    **template_values,
                    **resolve_local_slot_values(base_row, local_slot_source),
                    "component_block": component_block,
                }
                item_id = apply_expression_template(item_id_format, expression_values)

                merged_record = dict(base_row)
                merged_record.update(reuse_row)
                merged_record["assessment_id"] = assessment_id
                merged_record["component_id"] = component_id
                merged_record[layer_config.item_id_field] = item_id

                rows.append(
                    RegistryRow(
                        item_id=item_id,
                        assessment_id=assessment_id,
                        component_id=component_id,
                        sbo_identifier=resolve_sbo_identifier(merged_record),
                        sbo_identifier_shortid=resolve_sbo_identifier_shortid(merged_record),
                        sbo_short_description=base_row["sbo_short_description"],
                        definition_text=resolve_definition_text(base_row, layer_config),
                        guidance_text=resolve_guidance_text(base_row, layer_config),
                        evaluation_notes=base_row["evaluation_notes"],
                        decision_procedure=resolve_decision_procedure(base_row),
                        status=effective_status,
                    )
                )

    return rows


def load_registry_rows(
    registry_path: Path,
    include_inactive: bool,
    layer_config: RegistryLayerConfig,
) -> list[RegistryRow]:
    tables = collect_markdown_tables(registry_path)
    registry_metadata = extract_registry_metadata(tables)
    layer2_scoring_payloads = parse_layer2_scoring_payloads(registry_path) if layer_config.name == "layer2" else {}
    layer3_scoring_payloads = parse_layer3_scoring_payloads(registry_path) if layer_config.name == "layer3" else {}
    layer4_scoring_payloads = parse_layer4_scoring_payloads(registry_path) if layer_config.name == "layer4" else {}
    enrichment_lookup = build_registry_enrichment_lookup(registry_path, tables, layer_config)
    if layer3_scoring_payloads:
        for component_id, payload_fields in layer3_scoring_payloads.items():
            enrichment_lookup.setdefault(component_id, {}).update(payload_fields)
    if layer4_scoring_payloads:
        for assessment_id, payload_fields in layer4_scoring_payloads.items():
            enrichment_lookup.setdefault(assessment_id, {}).update(payload_fields)

    explicit_table: dict[str, object] | None = None
    layer2_base_rows = collect_section_rows(
        tables,
        "dimension base table",
        required_columns=LAYER2_BASE_TABLE_REQUIRED_COLUMNS,
        allow_field_value_records=True,
    )
    base_rows = collect_section_rows(
        tables,
        "base table",
        required_columns=LAYER1_BASE_TABLE_REQUIRED_COLUMNS,
        allow_field_value_records=True,
    )
    reuse_table = find_table_by_heading(tables, "reuse rule table")
    component_block_rule_table = find_table_by_heading(tables, "component block rule table")

    for table in tables:
        headers = set(table["headers"])
        if layer_config.explicit_required_columns.issubset(headers):
            explicit_table = table
            break

    rows: list[RegistryRow] = []
    if layer_config.supports_base_table_reuse and base_rows and reuse_table is not None:
        reuse_headers = set(reuse_table["headers"])
        validate_required_columns("Base Table", base_rows, LAYER1_BASE_TABLE_REQUIRED_COLUMNS)
        if {layer_config.item_id_field, "component_id"}.issubset(reuse_headers):
            if "template_id" not in reuse_headers and "local_slot" not in reuse_headers:
                raise ValueError("Reuse Rule Table must include template_id or local_slot for Base Table joins.")
            rows = build_registry_rows_from_base_and_reuse_tables(
                base_rows=base_rows,
                reuse_rows=list(reuse_table["rows"]),
                registry_metadata=registry_metadata,
                include_inactive=include_inactive,
                layer_config=layer_config,
            )
        elif {
            "template_group",
            "applies_to_component_pattern",
            "component_block_rule",
            "local_slot_source",
            f"{layer_config.item_id_field}_format",
        }.issubset(reuse_headers):
            if component_block_rule_table is None:
                raise ValueError(
                    "Component block rule table is required when Reuse Rule Table uses component_block_rule, "
                    f"local_slot_source, and {layer_config.item_id_field}_format columns."
                )
            rows = build_registry_rows_from_component_block_reuse_table(
                base_rows=base_rows,
                reuse_rows=list(reuse_table["rows"]),
                component_block_rows=list(component_block_rule_table["rows"]),
                registry_metadata=registry_metadata,
                include_inactive=include_inactive,
                layer_config=layer_config,
            )
        elif {"template_group", "applies_to_component_pattern", f"{layer_config.item_id_field}_rule"}.issubset(reuse_headers):
            rows = build_registry_rows_from_rule_based_reuse_table(
                base_rows=base_rows,
                reuse_rows=list(reuse_table["rows"]),
                registry_metadata=registry_metadata,
                include_inactive=include_inactive,
                layer_config=layer_config,
            )
        else:
            raise ValueError(
                f"Reuse Rule Table must either provide {layer_config.item_id_field}/component_id rows or rule-based columns "
                f"template_group, applies_to_component_pattern, and {layer_config.item_id_field}_rule, or the component-block rule set."
            )
    elif explicit_table is not None:
        explicit_rows = list(explicit_table["rows"])
        if layer_config.name == "layer2" and layer2_base_rows:
            validate_required_columns("Dimension base table", layer2_base_rows, LAYER2_BASE_TABLE_REQUIRED_COLUMNS)
            rows = build_layer2_rows_from_instance_and_base_tables(
                instance_rows=explicit_rows,
                base_rows=layer2_base_rows,
                scoring_payloads_by_component_template=layer2_scoring_payloads,
                include_inactive=include_inactive,
                layer_config=layer_config,
            )
        else:
            rows = build_registry_rows_from_explicit_table(
                table_rows=explicit_rows,
                include_inactive=include_inactive,
                layer_config=layer_config,
                enrichment_lookup=enrichment_lookup,
            )
    else:
        raise ValueError(
            f"Could not locate a usable {layer_config.item_label.lower()} source in the registry. Expected either a flat {layer_config.item_label.lower()} table "
            "or a Base Table plus Reuse Rule Table."
        )

    if not rows:
        raise ValueError(f"No {layer_config.item_label.lower()} rows were loaded from registry: {registry_path}")

    assessment_ids = {row.assessment_id for row in rows}
    if len(assessment_ids) != 1:
        raise ValueError(f"Expected one assessment_id in registry, found: {sorted(assessment_ids)}")

    return sorted(rows, key=indicator_sort_key)


def resolve_sbo_identifier(record: dict[str, str]) -> str:
    explicit_value = record.get("sbo_identifier", "").strip()
    if explicit_value:
        return explicit_value

    assessment_id = record["assessment_id"].strip()
    component_id = record.get("component_id", "").strip()
    item_id = (
        record.get("indicator_id", "").strip()
        or record.get("dimension_id", "").strip()
    )
    if "indicator_id" in record and record.get("indicator_id", "").strip():
        component_shortid = derive_component_shortid(component_id)
        return f"I_{assessment_id}_{component_shortid}_{item_id}"
    if "dimension_id" in record and record.get("dimension_id", "").strip():
        component_shortid = derive_component_shortid(component_id)
        return f"D_{assessment_id}_{component_shortid}_{item_id}"
    if component_id:
        component_shortid = derive_component_shortid(component_id)
        return f"C_{assessment_id}_{component_shortid}"
    return f"S_{assessment_id}"


def resolve_sbo_identifier_shortid(record: dict[str, str]) -> str:
    explicit_value = record.get("sbo_identifier_shortid", "").strip()
    if explicit_value:
        return explicit_value
    return (
        record.get("indicator_id", "").strip()
        or record.get("dimension_id", "").strip()
        or derive_component_shortid(record.get("component_id", "").strip())
        or "submission"
    )


def derive_component_shortid(component_id: str) -> str:
    shortid = component_id.strip()
    shortid = shortid.replace("Section", "Sec")
    shortid = shortid.replace("Response", "")
    return shortid


def indicator_sort_key(row: RegistryRow) -> tuple[str, int, str]:
    match = SHORTID_NUMBER_RE.search(row.sbo_identifier_shortid)
    shortid_number = int(match.group(1)) if match else 0
    return row.component_id, shortid_number, row.sbo_identifier


def extract_version_token(registry_path: Path) -> str:
    match = VERSION_TOKEN_RE.search(registry_path.name)
    if match:
        return match.group(1)
    return "v01"


def resolve_output_paths(
    registry_path: Path,
    assessment_id: str,
    version_token: str,
    layer_config: RegistryLayerConfig,
    output_dir: Path | None,
    rubric_output: Path | None,
    manifest_output: Path | None,
) -> tuple[Path, Path]:
    resolved_output_dir = output_dir.resolve() if output_dir else registry_path.parent.resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    rubric_path = (
        rubric_output.resolve()
        if rubric_output
        else resolved_output_dir / f"RUBRIC_{assessment_id}_CAL_payload{layer_config.rubric_filename_suffix}_{version_token}.md"
    )
    manifest_path = (
        manifest_output.resolve()
        if manifest_output
        else resolved_output_dir / f"{assessment_id}_{layer_config.manifest_layer_label}_ScoringManifest_{version_token}.md"
    )
    rubric_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    return rubric_path, manifest_path


def with_registry_version_suffix(output_path: Path, version_token: str) -> Path:
    match = VERSION_TOKEN_RE.search(output_path.name)
    if match:
        updated_name = VERSION_TOKEN_RE.sub(f"_{version_token}.md", output_path.name)
        return output_path.with_name(updated_name)
    return output_path


def group_rows_by_component(rows: list[RegistryRow]) -> dict[str, list[RegistryRow]]:
    grouped: dict[str, list[RegistryRow]] = defaultdict(list)
    for row in rows:
        grouped[row.component_id].append(row)
    return dict(sorted(grouped.items()))


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    body_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator_line, *body_lines])


def format_timestamp(timestamp_seconds: float) -> str:
    return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc).isoformat(timespec="seconds")


def render_derived_file_header(source_path: Path) -> str:
    source_stat = source_path.stat()
    source_timestamp = format_timestamp(source_stat.st_mtime)
    generated_timestamp = format_timestamp(datetime.now(tz=timezone.utc).timestamp())
    return (
        "<!-- DO NOT EDIT DIRECTLY. THIS IS A DERIVED FILE. "
        f"SOURCE: {source_path} | SOURCE_TIMESTAMP_UTC: {source_timestamp} | GENERATED_AT_UTC: {generated_timestamp} -->"
    )


def render_rubric_document(
    title_stem: str,
    assessment_id: str,
    rows: list[RegistryRow],
    layer_config: RegistryLayerConfig,
) -> str:
    component_rows = group_rows_by_component(rows)

    instance_rows = [
        [
            row.sbo_identifier,
            row.sbo_identifier_shortid,
            row.assessment_id,
            row.component_id,
            row.item_id,
            row.sbo_short_description,
        ]
        for row in rows
    ]

    layer1_instances_content = render_markdown_table(
        [
            "sbo_identifier",
            "sbo_identifier_shortid",
            "assessment_id",
            "component_id",
            "indicator_id",
            "sbo_short_description",
        ],
        instance_rows,
    ) if layer_config.name == "layer1" else render_markdown_table(["field"], [["`sbo_identifier`"], ["`sbo_identifier_shortid`"], ["`assessment_id`"], ["`component_id`"], ["`indicator_id`"], ["`sbo_short_description`"]])

    layer2_instances_content = render_markdown_table(
        [
            "sbo_identifier",
            "sbo_identifier_shortid",
            "assessment_id",
            "component_id",
            "dimension_id",
            "sbo_short_description",
        ],
        instance_rows,
    ) if layer_config.name == "layer2" else render_markdown_table(
        ["field"],
        [
            ["`sbo_identifier`"],
            ["`sbo_identifier_shortid`"],
            ["`assessment_id`"],
            ["`component_id`"],
            ["`dimension_id`"],
            ["`sbo_short_description`"],
        ],
    )

    parts: list[str] = [
        f"## {title_stem}",
        "### 0A. Purpose",
        "Defines the **structural schema of a rubric payload** used to evaluate **participant assignment artefacts**.",
        "",
        "The rubric operates under the **four-layer scoring ontology**.",
        "Authoring conventions, identifier rules, and mapping semantics are defined in `Rubric_SpecificationGuide_v02`.",
        "",
        render_markdown_table(
            ["layer", "SBO class"],
            [
                ["Layer 1", "indicator"],
                ["Layer 2", "dimension"],
                ["Layer 3", "component"],
                ["Layer 4", "submission-level aggregate"],
            ],
        ),
        "### 0B. Identifier Registry",
        "",
        render_markdown_table(
            ["identifier", "level", "meaning", "used in"],
            [
                ["`assessment_id`", "rubric specification", "identifies the assessment for which the rubric payload is authored", "rubric payload, SBO instance registries"],
                ["`participant_id`", "dataset / scoring input", "identifies one participant artefact in the canonical dataset and scoring inputs", "canonical datasets, runtime assessment artefacts"],
                ["`submission_id`", "scoring output schema", "standardised output field name used when participant identifiers are emitted by scoring pipelines", "runtime scoring outputs, scoring prompt output schemas"],
                ["`component_id`", "component", "identifies a component or response surface within the assessment", "datasets, rubric payload, scoring pipelines"],
                ["`dimension_id`", "rubric dimension", "identifies a dimension SBO within a component", "rubric payload"],
                ["`indicator_id`", "rubric indicator", "identifies an indicator SBO within a component", "rubric payload"],
            ],
        ),
        "",
        "### 1. Layer 4 SBO Registry",
        "",
        render_markdown_table(["field"], [["`submission_score`"]]),
        "### 2. Layer 3 SBO Registry",
        "",
        render_markdown_table(["field"], [["`component_score`"]]),
        "### 3. Layer 2 SBO Registry",
        "",
        render_markdown_table(["field"], [["`dimension_score`"]]),
        "### 4. Layer 1 SBO Registry",
        "",
        render_markdown_table(["field"], [["`indicator_score`"]]),
        "",
        "### 4A. Score Registry Summary",
        "",
        render_markdown_table(
            ["layer", "SBO class", "score field", "score meaning"],
            [
                ["Layer 1", "indicator", "`indicator_score`", "evidence status assigned to an indicator SBO"],
                ["Layer 2", "dimension", "`dimension_score`", "dimension-level evidence judgement derived from indicator evidence"],
                ["Layer 3", "component", "`component_score`", "component-level performance judgement derived from dimension evidence"],
                ["Layer 4", "submission-level aggregate", "`submission_score`", "assignment-level performance judgement derived from component scores"],
            ],
        ),
        "### 5. SBO Instance Registries",
        "Instance registries define the specific **Score-Bearing Object (SBO) instances** used by the rubric.",
        "Each instance must include:",
        "- `sbo_identifier`",
        "- `sbo_identifier_shortid`",
        "- any layer-specific identifier fields (for example `component_id`, `dimension_id`, or `indicator_id`)",
        "- `sbo_short_description`",
        "`sbo_identifier_shortid` is a compact token used in mapping tables and rule definitions.",
        "",
        "",
        "#### 5.4 Layer 1 SBO Instances (Draft)",
        "",
        layer1_instances_content,
        "",
        "#### 5.3 Layer 2 SBO Instances",
        "",
        layer2_instances_content,
        "#### 5.2 Layer 3 SBO Instances",
        "Registry of **component SBO instances**.",
        "Required fields typically include:",
        "",
        render_markdown_table(
            ["field"],
            [
                ["`sbo_identifier`"],
                ["`sbo_identifier_shortid`"],
                ["`assessment_id`"],
                ["`component_id`"],
                ["`sbo_short_description`"],
            ],
        ),
        "#### 5.1 Layer 4 SBO Instances",
        "Registry of **submission SBO instances**.",
        "Required fields typically include:",
        "",
        render_markdown_table(
            ["field"],
            [
                ["`sbo_identifier`"],
                ["`sbo_identifier_shortid`"],
                ["`assessment_id`"],
                ["`sbo_short_description`"],
            ],
        ),
        "### 6. SBO Value Derivation Registries",
        "Value-derivation sections define how scores for each SBO layer are computed.",
        "These sections may contain:",
        "- registry summaries",
        "- evaluation guidance",
        "- mapping tables",
        "- fallback rules",
        "- interpretation notes",
        "",
        "",
        "#### 6.1 Layer 1 SBO Value Derivation (Draft)",
        "",
    ]

    if layer_config.name == "layer1":
        for component_id, component_registry_rows in component_rows.items():
            parts.extend(
                [
                    f"##### Component: `{component_id}`",
                    "",
                    render_markdown_table(
                        [
                            "sbo_identifier",
                            "sbo_short_description",
                            layer_config.output_definition_header,
                            layer_config.output_guidance_header,
                            "evaluation_notes",
                            "decision_procedure",
                        ],
                        [
                            [
                                row.sbo_identifier,
                                row.sbo_short_description,
                                row.definition_text,
                                row.guidance_text,
                                row.evaluation_notes,
                                row.decision_procedure,
                            ]
                            for row in component_registry_rows
                        ],
                    ),
                    "",
                ]
            )
    else:
        parts.extend(
            [
                "This payload was generated from a Layer 2 registry. Layer 1 value derivation content is not populated by this source document.",
                "",
            ]
        )

    parts.extend(
        [
            "#### 6.2 Layer 2 Value Derivation",
        ]
    )

    if layer_config.name == "layer2":
        parts.extend(
            [
                "Derived from the Layer 2 dimension registry.",
                "",
            ]
        )
        for component_id, component_registry_rows in component_rows.items():
            parts.extend(
                [
                    f"##### Component: `{component_id}`",
                    "",
                    render_markdown_table(
                        [
                            "sbo_identifier",
                            "sbo_short_description",
                            layer_config.output_definition_header,
                            layer_config.output_guidance_header,
                            "evaluation_notes",
                            "decision_procedure",
                        ],
                        [
                            [
                                row.sbo_identifier,
                                row.sbo_short_description,
                                row.definition_text,
                                row.guidance_text,
                                row.evaluation_notes,
                                row.decision_procedure,
                            ]
                            for row in component_registry_rows
                        ],
                    ),
                    "",
                ]
            )
    else:
        parts.extend(
            [
                "Derives `dimension_score` from indicator evidence.",
                "Typical contents:",
                "- indicator → dimension mapping tables",
                "- optional fallback rules",
                "- interpretation notes",
            ]
        )

    parts.extend(
        [
            "#### 6.3 Layer 3 Value Derivation",
        ]
    )

    if layer_config.name == "layer3":
        parts.extend(
            [
                "Derived from the Layer 3 component registry.",
                "",
            ]
        )
        for component_id, component_registry_rows in component_rows.items():
            parts.extend(
                [
                    f"##### Component: `{component_id}`",
                    "",
                    render_markdown_table(
                        [
                            "sbo_identifier",
                            "sbo_short_description",
                            layer_config.output_definition_header,
                            layer_config.output_guidance_header,
                            "evaluation_notes",
                            "decision_procedure",
                        ],
                        [
                            [
                                row.sbo_identifier,
                                row.sbo_short_description,
                                row.definition_text,
                                row.guidance_text,
                                row.evaluation_notes,
                                row.decision_procedure,
                            ]
                            for row in component_registry_rows
                        ],
                    ),
                    "",
                ]
            )
    else:
        parts.extend(
            [
                "Derives `component_score` from dimension evidence.",
                "Typical contents:",
                "- dimension → component mapping tables",
                "- optional boundary rules",
                "- interpretation notes",
            ]
        )

    parts.extend(
        [
            "#### 6.4 Layer 4 Value Derivation",
        ]
    )

    if layer_config.name == "layer4":
        parts.extend(
            [
                "Derived from the Layer 4 submission registry.",
                "",
                render_markdown_table(
                    [
                        "sbo_identifier",
                        "sbo_short_description",
                        layer_config.output_definition_header,
                        layer_config.output_guidance_header,
                        "evaluation_notes",
                        "decision_procedure",
                    ],
                    [
                        [
                            row.sbo_identifier,
                            row.sbo_short_description,
                            row.definition_text,
                            row.guidance_text,
                            row.evaluation_notes,
                            row.decision_procedure,
                        ]
                        for row in rows
                    ],
                ),
                "",
            ]
        )
    else:
        parts.extend(
            [
                "Derives `submission_score` from component scores.",
                "Typical contents:",
                "- component aggregation rules",
                "- optional fallback rules",
                "- interpretation notes",
            ]
        )

    parts.extend(
        [
            "### 7. Scoring Ontology and Identifier Context",
            "Evaluation hierarchy.",
            "",
            render_markdown_table(
                ["SBO class"],
                [
                    ["submission-level aggregate"],
                    ["component"],
                    ["dimension"],
                    ["indicator"],
                ],
            ),
            "",
            "Assessment artefact for Layers 1–3: `participant_id × component_id`.",
            "Assessment artefact for Layer 4: `participant_id`.",
            "",
            "The rubric payload itself is authored at the **assessment level**, using the identifier:",
            "",
            "`assessment_id`",
            "",
            "During scoring, participant artefacts identified by `participant_id` are evaluated using this rubric specification.",
            "### 8. Rubric Stability States",
            "",
            render_markdown_table(
                ["state"],
                [["Draft"], ["Under Evaluation"], ["Stabilised"], ["Frozen"]],
            ),
            "### 9. Scale Registry",
            "Defines the scoring scales used by the rubric.",
            "",
            render_markdown_table(
                ["scale_name", "scale_type"],
                [
                    ["`indicator_evidence_scale`", "evidence"],
                    ["`dimension_evidence_scale`", "evidence"],
                    ["`component_performance_scale`", "performance"],
                    ["`submission_performance_scale`", "performance"],
                ],
            ),
            "",
        ]
    )

    return "\n".join(parts)
def render_manifest_document(
    title_stem: str,
    assessment_id: str,
    rows: list[RegistryRow],
    layer_config: RegistryLayerConfig,
) -> str:
    component_rows = group_rows_by_component(rows)
    manifest_headers: list[str] = []
    if layer_config.manifest_includes_component_id:
        manifest_headers.append("component_id")
    manifest_headers.extend([
        "sbo_identifier",
    ])
    if layer_config.manifest_item_id_field:
        manifest_headers.append(layer_config.manifest_item_id_field)
    manifest_headers.extend([
        "sbo_short_description",
        layer_config.output_definition_header,
        layer_config.output_guidance_header,
        "evaluation_notes",
        "decision_procedure",
    ])
    manifest_rows: list[list[str]] = []
    for row in rows:
        manifest_row: list[str] = []
        if layer_config.manifest_includes_component_id:
            manifest_row.append(row.component_id)
        manifest_row.append(f"`{row.sbo_identifier}`")
        if layer_config.manifest_item_id_field:
            manifest_row.append(f"`{row.item_id}`")
        manifest_row.extend([
            f"`{row.sbo_short_description}`",
            row.definition_text,
            row.guidance_text,
            row.evaluation_notes,
            row.decision_procedure,
        ])
        if layer_config.name == "layer2":
            if "dimension_template_id" not in manifest_headers:
                manifest_headers.extend([
                    "dimension_template_id",
                    "dimension_evidence_scale",
                    "dimension_scoring_payload_json",
                ])
            manifest_row.extend([
                row.template_id,
                row.evidence_scale,
                row.scoring_payload_json,
            ])
        if layer_config.name == "layer3":
            if "component_performance_scale" not in manifest_headers:
                manifest_headers.extend([
                    "component_performance_scale",
                    "component_scoring_payload_json",
                ])
            manifest_row.extend([
                row.evidence_scale,
                row.scoring_payload_json,
            ])
        if layer_config.name == "layer4":
            if "submission_performance_scale" not in manifest_headers:
                manifest_headers.extend([
                    "submission_performance_scale",
                    "submission_scoring_payload_json",
                ])
            manifest_row.extend([
                row.evidence_scale,
                row.scoring_payload_json,
            ])
        manifest_rows.append(manifest_row)

    metadata_rows = [
        ["assessment_id", assessment_id],
        ["scoring_layer", layer_config.manifest_layer_label],
        ["scoring_scope", "participant_id × component_id" if layer_config.name != "layer4" else "participant_id"],
        ["ontology_reference", "Rubric_SpecificationGuide_v*"],
        ["expected_input_identifier", "participant_id"],
        ["runtime_output_identifier", "submission_id"],
    ]
    if layer_config.manifest_includes_component_id:
        metadata_rows.append(["component_registry_count", str(len(component_rows))])
    metadata_rows.append([f"total_{layer_config.item_label.lower()}_count", str(len(rows))])

    parts = [
        f"## {title_stem}",
        "",
        "### 1. Manifest metadata",
        "",
        render_markdown_table(
            ["field", "value"],
            metadata_rows,
        ),
        "",
        "### 2. Identifier context",
        "",
        "Scoring unit:",
        "",
        "```text",
        "participant_id" if layer_config.name == "layer4" else "participant_id × component_id",
        "```",
        "",
        "Identifier relationship:",
        "",
        "```text",
        "submission_id ↔ participant_id",
        "```",
        "",
        f"### 3. {layer_config.section_layer_label} {layer_config.item_label} Scoring Manifest",
        "",
        render_markdown_table(
            manifest_headers,
            manifest_rows,
        ),
        "",
    ]
    return "\n".join(parts)


def write_text_if_stale(output_path: Path, content: str, source_paths: list[Path]) -> str:
    """Write output_path only when it is missing or older than any dependency path."""
    if output_path.exists():
        output_stat = output_path.stat()
        newest_source_mtime_ns = max(source_path.stat().st_mtime_ns for source_path in source_paths)
        if output_stat.st_mtime_ns >= newest_source_mtime_ns:
            return "skipped"

    output_path.write_text(content, encoding="utf-8")
    return "written"


def prepend_derived_file_header(content: str, source_path: Path) -> str:
    return f"{render_derived_file_header(source_path)}\n\n{content}"


def main() -> int:
    args = parse_args()

    registry_path = args.registry_path.resolve()
    if not registry_path.exists():
        raise FileNotFoundError(f"Registry not found: {registry_path}")

    tables = collect_markdown_tables(registry_path)
    layer_config = infer_registry_layer(tables, args.registry_layer, registry_path)

    rows = load_registry_rows(
        registry_path,
        include_inactive=args.include_inactive,
        layer_config=layer_config,
    )
    assessment_id = rows[0].assessment_id
    version_token = extract_version_token(registry_path)

    rubric_path, manifest_path = resolve_output_paths(
        registry_path=registry_path,
        assessment_id=assessment_id,
        version_token=version_token,
        layer_config=layer_config,
        output_dir=args.output_dir,
        rubric_output=args.rubric_output,
        manifest_output=args.manifest_output,
    )

    rubric_text = prepend_derived_file_header(
        render_rubric_document(rubric_path.stem, assessment_id, rows, layer_config),
        registry_path,
    )
    manifest_text = prepend_derived_file_header(
        render_manifest_document(manifest_path.stem, assessment_id, rows, layer_config),
        registry_path,
    )

    dependency_paths = [registry_path, Path(__file__).resolve()]
    rubric_status = write_text_if_stale(rubric_path, rubric_text, dependency_paths)
    manifest_status = write_text_if_stale(manifest_path, manifest_text, dependency_paths)

    print(f"Registry: {registry_path}")
    print(f"Registry layer: {layer_config.manifest_layer_label}")
    print(f"Rubric output: {rubric_path} ({rubric_status})")
    print(f"Manifest output: {manifest_path} ({manifest_status})")
    print(f"Assessment: {assessment_id}")
    print(f"{layer_config.item_label}s written: {len(rows)}")
    print(f"Components written: {len(group_rows_by_component(rows))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())