#!/usr/bin/env python3
"""Generate a Layer 1 rubric payload and scoring manifest from an indicator registry.

This script reads a markdown indicator registry, extracts the Layer 1
indicator rows, and writes two markdown outputs in the same directory by
default. Registry sections can continue to use the existing wide markdown
tables, and the Base Table section may also be expressed as repeated two-column
`field | value` record tables for indicators with longer prose fields:

- RUBRIC_<ASSESSMENT>_CAL_payload_<VERSION>.md
- <ASSESSMENT>_Layer1_ScoringManifest_<VERSION>.md

The generated documents follow the same structural conventions as the existing
pl1C_rubric_devt rubric payload and scoring manifest examples.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_REGISTRY_COLUMNS = {
    "indicator_id",
    "assessment_id",
    "component_id",
    "sbo_short_description",
    "indicator_definition",
    "assessment_guidance",
    "evaluation_notes",
}
BASE_TABLE_REQUIRED_COLUMNS = {
    "template_id",
    "local_slot",
    "sbo_short_description",
    "indicator_definition",
    "assessment_guidance",
    "evaluation_notes",
}
VERSION_TOKEN_RE = re.compile(r"_(v(?:_i)?\d+)\.md$", re.IGNORECASE)
SHORTID_NUMBER_RE = re.compile(r"(\d+)")
HEADING_RE = re.compile(r"^\s*(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")
FIELD_VALUE_TABLE_HEADERS = ["field", "value"]
SKIPPED_REUSE_RULE_STATUSES = {"inactive", "draft"}


@dataclass(frozen=True)
class IndicatorRow:
    indicator_id: str
    sbo_identifier: str
    sbo_identifier_shortid: str
    assessment_id: str
    component_id: str
    sbo_short_description: str
    indicator_definition: str
    assessment_guidance: str
    evaluation_notes: str
    decision_procedure: str
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate rubric and scoring manifest markdown from an indicator registry."
    )
    parser.add_argument(
        "--indicator-registry",
        type=Path,
        required=True,
        help="Path to the markdown indicator registry file.",
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
            row_label = row.get("template_id", "").strip() or row.get("indicator_id", "").strip() or str(row_index)
            raise ValueError(f"{table_name} row {row_label!r} is missing required column(s): {missing_columns}")


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


def build_indicator_rows_from_explicit_table(
    table_rows: list[dict[str, str]],
    include_inactive: bool,
) -> list[IndicatorRow]:
    rows: list[IndicatorRow] = []
    for record in table_rows:
        status = record.get("status", "").strip().lower()
        if not include_inactive and status and status != "active":
            continue
        rows.append(
            IndicatorRow(
                indicator_id=record["indicator_id"],
                assessment_id=record["assessment_id"],
                component_id=record["component_id"],
                sbo_identifier=resolve_sbo_identifier(record),
                sbo_identifier_shortid=resolve_sbo_identifier_shortid(record),
                sbo_short_description=record["sbo_short_description"],
                indicator_definition=record["indicator_definition"],
                assessment_guidance=record["assessment_guidance"],
                evaluation_notes=record["evaluation_notes"],
                decision_procedure=resolve_decision_procedure(record),
                status=record.get("status", ""),
            )
        )
    return rows


def resolve_decision_procedure(record: dict[str, str]) -> str:
    return record.get("decision_procedure", "").strip()


def should_skip_reuse_rule_row(reuse_row: dict[str, str], include_inactive: bool) -> bool:
    if include_inactive:
        return False
    return reuse_row.get("status", "").strip().lower() in SKIPPED_REUSE_RULE_STATUSES


def build_indicator_rows_from_base_and_reuse_tables(
    base_rows: list[dict[str, str]],
    reuse_rows: list[dict[str, str]],
    registry_metadata: dict[str, str],
    include_inactive: bool,
) -> list[IndicatorRow]:
    base_by_template_id = {
        row.get("template_id", "").strip(): row for row in base_rows if row.get("template_id", "").strip()
    }
    base_by_local_slot = {
        row.get("local_slot", "").strip(): row for row in base_rows if row.get("local_slot", "").strip()
    }

    rows: list[IndicatorRow] = []
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
            IndicatorRow(
                indicator_id=merged_record["indicator_id"],
                assessment_id=assessment_id,
                component_id=merged_record["component_id"],
                sbo_identifier=resolve_sbo_identifier(merged_record),
                sbo_identifier_shortid=resolve_sbo_identifier_shortid(merged_record),
                sbo_short_description=merged_record["sbo_short_description"],
                indicator_definition=merged_record["indicator_definition"],
                assessment_guidance=merged_record["assessment_guidance"],
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

    return {
        "local_slot": local_slot,
        "local_slot_int": str(int(local_slot)),
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


def build_indicator_rows_from_rule_based_reuse_table(
    base_rows: list[dict[str, str]],
    reuse_rows: list[dict[str, str]],
    registry_metadata: dict[str, str],
    include_inactive: bool,
) -> list[IndicatorRow]:
    rows: list[IndicatorRow] = []
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

        indicator_id_template = extract_rule_template(reuse_row.get("indicator_id_rule", "").strip())
        if not indicator_id_template:
            raise ValueError("Reuse Rule Table must include indicator_id_rule for rule-based expansion.")

        reuse_status = reuse_row.get("status", "").strip()
        for component_id, template_values in expand_component_pattern(component_pattern):
            for base_row in matching_base_rows:
                effective_status = reuse_status or base_row.get("status", "").strip()
                if not include_inactive and effective_status and effective_status.lower() != "active":
                    continue

                local_slot = base_row.get("local_slot", "").strip()
                indicator_id = apply_token_template(
                    indicator_id_template,
                    {
                        **template_values,
                        "local_slot": local_slot,
                    },
                )

                merged_record = dict(base_row)
                merged_record.update(reuse_row)
                merged_record["assessment_id"] = assessment_id
                merged_record["component_id"] = component_id
                merged_record["indicator_id"] = indicator_id

                rows.append(
                    IndicatorRow(
                        indicator_id=indicator_id,
                        assessment_id=assessment_id,
                        component_id=component_id,
                        sbo_identifier=resolve_sbo_identifier(merged_record),
                        sbo_identifier_shortid=resolve_sbo_identifier_shortid(merged_record),
                        sbo_short_description=base_row["sbo_short_description"],
                        indicator_definition=base_row["indicator_definition"],
                        assessment_guidance=base_row["assessment_guidance"],
                        evaluation_notes=base_row["evaluation_notes"],
                        decision_procedure=resolve_decision_procedure(base_row),
                        status=effective_status,
                    )
                )

    return rows


def build_indicator_rows_from_component_block_reuse_table(
    base_rows: list[dict[str, str]],
    reuse_rows: list[dict[str, str]],
    component_block_rows: list[dict[str, str]],
    registry_metadata: dict[str, str],
    include_inactive: bool,
) -> list[IndicatorRow]:
    rows: list[IndicatorRow] = []
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

        indicator_id_format = reuse_row.get("indicator_id_format", "").strip()
        if not indicator_id_format:
            raise ValueError("Reuse Rule Table must include indicator_id_format for component-block expansion.")

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
                indicator_id = apply_expression_template(indicator_id_format, expression_values)

                merged_record = dict(base_row)
                merged_record.update(reuse_row)
                merged_record["assessment_id"] = assessment_id
                merged_record["component_id"] = component_id
                merged_record["indicator_id"] = indicator_id

                rows.append(
                    IndicatorRow(
                        indicator_id=indicator_id,
                        assessment_id=assessment_id,
                        component_id=component_id,
                        sbo_identifier=resolve_sbo_identifier(merged_record),
                        sbo_identifier_shortid=resolve_sbo_identifier_shortid(merged_record),
                        sbo_short_description=base_row["sbo_short_description"],
                        indicator_definition=base_row["indicator_definition"],
                        assessment_guidance=base_row["assessment_guidance"],
                        evaluation_notes=base_row["evaluation_notes"],
                        decision_procedure=resolve_decision_procedure(base_row),
                        status=effective_status,
                    )
                )

    return rows


def load_indicator_rows(registry_path: Path, include_inactive: bool) -> list[IndicatorRow]:
    tables = collect_markdown_tables(registry_path)
    registry_metadata = extract_registry_metadata(tables)

    explicit_table: dict[str, object] | None = None
    base_rows = collect_section_rows(
        tables,
        "base table",
        required_columns=BASE_TABLE_REQUIRED_COLUMNS,
        allow_field_value_records=True,
    )
    reuse_table = find_table_by_heading(tables, "reuse rule table")
    component_block_rule_table = find_table_by_heading(tables, "component block rule table")

    for table in tables:
        headers = set(table["headers"])
        if REQUIRED_REGISTRY_COLUMNS.issubset(headers):
            explicit_table = table
            break

    rows: list[IndicatorRow] = []
    if base_rows and reuse_table is not None:
        reuse_headers = set(reuse_table["headers"])
        validate_required_columns("Base Table", base_rows, BASE_TABLE_REQUIRED_COLUMNS)
        if {"indicator_id", "component_id"}.issubset(reuse_headers):
            if "template_id" not in reuse_headers and "local_slot" not in reuse_headers:
                raise ValueError("Reuse Rule Table must include template_id or local_slot for Base Table joins.")
            rows = build_indicator_rows_from_base_and_reuse_tables(
                base_rows=base_rows,
                reuse_rows=list(reuse_table["rows"]),
                registry_metadata=registry_metadata,
                include_inactive=include_inactive,
            )
        elif {
            "template_group",
            "applies_to_component_pattern",
            "component_block_rule",
            "local_slot_source",
            "indicator_id_format",
        }.issubset(reuse_headers):
            if component_block_rule_table is None:
                raise ValueError(
                    "Component block rule table is required when Reuse Rule Table uses component_block_rule, "
                    "local_slot_source, and indicator_id_format columns."
                )
            rows = build_indicator_rows_from_component_block_reuse_table(
                base_rows=base_rows,
                reuse_rows=list(reuse_table["rows"]),
                component_block_rows=list(component_block_rule_table["rows"]),
                registry_metadata=registry_metadata,
                include_inactive=include_inactive,
            )
        elif {"template_group", "applies_to_component_pattern", "indicator_id_rule"}.issubset(reuse_headers):
            rows = build_indicator_rows_from_rule_based_reuse_table(
                base_rows=base_rows,
                reuse_rows=list(reuse_table["rows"]),
                registry_metadata=registry_metadata,
                include_inactive=include_inactive,
            )
        else:
            raise ValueError(
                "Reuse Rule Table must either provide indicator_id/component_id rows or rule-based columns "
                "template_group, applies_to_component_pattern, and indicator_id_rule, or the component-block rule set."
            )
    elif explicit_table is not None:
        rows = build_indicator_rows_from_explicit_table(
            table_rows=list(explicit_table["rows"]),
            include_inactive=include_inactive,
        )
    else:
        raise ValueError(
            "Could not locate a usable indicator source in the registry. Expected either a flat indicator table "
            "or a Base Table plus Reuse Rule Table."
        )

    if not rows:
        raise ValueError(f"No indicator rows were loaded from registry: {registry_path}")

    assessment_ids = {row.assessment_id for row in rows}
    if len(assessment_ids) != 1:
        raise ValueError(f"Expected one assessment_id in registry, found: {sorted(assessment_ids)}")

    return sorted(rows, key=indicator_sort_key)


def resolve_sbo_identifier(record: dict[str, str]) -> str:
    explicit_value = record.get("sbo_identifier", "").strip()
    if explicit_value:
        return explicit_value

    assessment_id = record["assessment_id"].strip()
    component_id = record["component_id"].strip()
    indicator_id = record["indicator_id"].strip()
    component_shortid = derive_component_shortid(component_id)
    return f"I_{assessment_id}_{component_shortid}_{indicator_id}"


def resolve_sbo_identifier_shortid(record: dict[str, str]) -> str:
    explicit_value = record.get("sbo_identifier_shortid", "").strip()
    if explicit_value:
        return explicit_value
    return record["indicator_id"].strip()


def derive_component_shortid(component_id: str) -> str:
    shortid = component_id.strip()
    shortid = shortid.replace("Section", "Sec")
    shortid = shortid.replace("Response", "")
    return shortid


def indicator_sort_key(row: IndicatorRow) -> tuple[str, int, str]:
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
    output_dir: Path | None,
    rubric_output: Path | None,
    manifest_output: Path | None,
) -> tuple[Path, Path]:
    resolved_output_dir = output_dir.resolve() if output_dir else registry_path.parent.resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    rubric_path = (
        with_registry_version_suffix(rubric_output.resolve(), version_token)
        if rubric_output
        else resolved_output_dir / f"RUBRIC_{assessment_id}_CAL_payload_{version_token}.md"
    )
    manifest_path = (
        with_registry_version_suffix(manifest_output.resolve(), version_token)
        if manifest_output
        else resolved_output_dir / f"{assessment_id}_Layer1_ScoringManifest_{version_token}.md"
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


def group_rows_by_component(rows: list[IndicatorRow]) -> dict[str, list[IndicatorRow]]:
    grouped: dict[str, list[IndicatorRow]] = defaultdict(list)
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


def render_rubric_document(title_stem: str, assessment_id: str, rows: list[IndicatorRow]) -> str:
    component_rows = group_rows_by_component(rows)

    layer_1_instance_rows = [
        [
            row.sbo_identifier,
            row.sbo_identifier_shortid,
            row.assessment_id,
            row.component_id,
            row.indicator_id,
            row.sbo_short_description,
        ]
        for row in rows
    ]

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
        render_markdown_table(
            [
                "sbo_identifier",
                "sbo_identifier_shortid",
                "assessment_id",
                "component_id",
                "indicator_id",
                "sbo_short_description",
            ],
            layer_1_instance_rows,
        ),
        "",
        "#### 5.3 Layer 2 SBO Instances",
        "Registry of **dimension SBO instances**.",
        "Required fields typically include:",
        "",
        render_markdown_table(
            ["field"],
            [
                ["`sbo_identifier`"],
                ["`sbo_identifier_shortid`"],
                ["`assessment_id`"],
                ["`component_id`"],
                ["`dimension_id`"],
                ["`sbo_short_description`"],
            ],
        ),
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

    for component_id, component_indicator_rows in component_rows.items():
        parts.extend(
            [
                f"##### Component: `{component_id}`",
                "",
                render_markdown_table(
                    [
                        "sbo_identifier",
                        "sbo_short_description",
                        "indicator_definition",
                        "assessment_guidance",
                        "evaluation_notes",
                        "decision_procedure",
                    ],
                    [
                        [
                            row.sbo_identifier,
                            row.sbo_short_description,
                            row.indicator_definition,
                            row.assessment_guidance,
                            row.evaluation_notes,
                            row.decision_procedure,
                        ]
                        for row in component_indicator_rows
                    ],
                ),
                "",
            ]
        )

    parts.extend(
        [
            "#### 6.2 Layer 2 Value Derivation",
            "Derives `dimension_score` from indicator evidence.",
            "Typical contents:",
            "- indicator → dimension mapping tables",
            "- optional fallback rules",
            "- interpretation notes",
            "#### 6.3 Layer 3 Value Derivation",
            "Derives `component_score` from dimension evidence.",
            "Typical contents:",
            "- dimension → component mapping tables",
            "- optional boundary rules",
            "- interpretation notes",
            "#### 6.4 Layer 4 Value Derivation",
            "Derives `submission_score` from component scores.",
            "Typical contents:",
            "- component aggregation rules",
            "- optional fallback rules",
            "- interpretation notes",
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


def render_manifest_document(title_stem: str, assessment_id: str, rows: list[IndicatorRow]) -> str:
    component_rows = group_rows_by_component(rows)
    manifest_rows = [
        [
            row.component_id,
            f"`{row.sbo_identifier}`",
            f"`{row.indicator_id}`",
            f"`{row.sbo_short_description}`",
            row.indicator_definition,
            row.assessment_guidance,
            row.evaluation_notes,
            row.decision_procedure,
        ]
        for row in rows
    ]

    parts = [
        f"## {title_stem}",
        "",
        "### 1. Manifest metadata",
        "",
        render_markdown_table(
            ["field", "value"],
            [
                ["assessment_id", assessment_id],
                ["scoring_layer", "Layer1"],
                ["scoring_scope", "participant_id × component_id"],
                ["ontology_reference", "Rubric_SpecificationGuide_v*"],
                ["expected_input_identifier", "participant_id"],
                ["runtime_output_identifier", "submission_id"],
                ["component_registry_count", str(len(component_rows))],
                ["total_indicator_count", str(len(rows))],
            ],
        ),
        "",
        "### 2. Identifier context",
        "",
        "Scoring unit:",
        "",
        "```text",
        "participant_id × component_id",
        "```",
        "",
        "Identifier relationship:",
        "",
        "```text",
        "submission_id ↔ participant_id",
        "```",
        "",
        "### 3. Layer 1 Indicator Scoring Manifest",
        "",
        render_markdown_table(
            [
                "component_id",
                "sbo_identifier",
                "indicator_id",
                "sbo_short_description",
                "indicator_definition",
                "assessment_guidance",
                "evaluation_notes",
                "decision_procedure",
            ],
            manifest_rows,
        ),
        "",
    ]
    return "\n".join(parts)


def write_text_if_stale(output_path: Path, content: str, source_path: Path) -> str:
    """Write output_path only when it is missing or older than source_path."""
    if output_path.exists():
        output_stat = output_path.stat()
        source_stat = source_path.stat()
        if output_stat.st_mtime_ns >= source_stat.st_mtime_ns:
            return "skipped"

    output_path.write_text(content, encoding="utf-8")
    return "written"


def prepend_derived_file_header(content: str, source_path: Path) -> str:
    return f"{render_derived_file_header(source_path)}\n\n{content}"


def main() -> int:
    args = parse_args()

    registry_path = args.indicator_registry.resolve()
    if not registry_path.exists():
        raise FileNotFoundError(f"Indicator registry not found: {registry_path}")

    rows = load_indicator_rows(registry_path, include_inactive=args.include_inactive)
    assessment_id = rows[0].assessment_id
    version_token = extract_version_token(registry_path)

    rubric_path, manifest_path = resolve_output_paths(
        registry_path=registry_path,
        assessment_id=assessment_id,
        version_token=version_token,
        output_dir=args.output_dir,
        rubric_output=args.rubric_output,
        manifest_output=args.manifest_output,
    )

    rubric_text = prepend_derived_file_header(
        render_rubric_document(rubric_path.stem, assessment_id, rows),
        registry_path,
    )
    manifest_text = prepend_derived_file_header(
        render_manifest_document(manifest_path.stem, assessment_id, rows),
        registry_path,
    )

    rubric_status = write_text_if_stale(rubric_path, rubric_text, registry_path)
    manifest_status = write_text_if_stale(manifest_path, manifest_text, registry_path)

    print(f"Indicator registry: {registry_path}")
    print(f"Rubric output: {rubric_path} ({rubric_status})")
    print(f"Manifest output: {manifest_path} ({manifest_status})")
    print(f"Assessment: {assessment_id}")
    print(f"Indicators written: {len(rows)}")
    print(f"Components written: {len(group_rows_by_component(rows))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())