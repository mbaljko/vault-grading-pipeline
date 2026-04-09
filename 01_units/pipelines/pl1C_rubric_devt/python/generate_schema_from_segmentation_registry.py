#!/usr/bin/env python3
"""Parse a Layer 0 segmentation registry markdown file into raw and normalized registry artifacts.

This script currently implements Step 1 of the schema-generation workflow:

- read registry Markdown contents
- detect section boundaries
- parse Markdown tables into normalized row dictionaries
- preserve multiline field/value records
- validate required columns for known Layer 0 table types
- emit a raw registry plus a normalized registry that is ready for compilation

The command-line contract mostly mirrors
generate_rubric_and_manifest_from_indicator_registry.py, but this step writes
raw and normalized registry JSON artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


HEADING_RE = re.compile(r"^\s*(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")
FIELD_VALUE_HEADERS = ["field", "value"]
LAYER0_ALLOWED_LAYERS = {"auto", "layer0"}
REGISTRY_METADATA_REQUIRED_FIELDS = {"assessment_id", "registry_version"}
IDENTIFIER_RULE_REQUIRED_HEADERS = {"field", "rule"}
REUSE_RULE_REQUIRED_COLUMNS = {
	"rule_id",
	"template_group",
	"applies_to_component_pattern",
	"expansion_mode",
	"component_block_rule",
	"local_slot_source",
	"operator_id_format",
	"assessment_id",
	"status",
}
COMPONENT_BLOCK_RULE_REQUIRED_COLUMNS = {
	"block_rule_id",
	"component_id",
	"component_block",
}
OPERATOR_REQUIRED_FIELDS = {
	"template_id",
	"local_slot",
	"operator_short_description",
	"operator_definition",
	"operator_guidance",
	"failure_mode_guidance",
	"decision_procedure",
	"output_mode",
	"segment_id",
	"status",
}
IDENTIFIER_RULE_SOURCE_TEXT_FIELDS = {"rule"}
COMPONENT_BLOCK_SOURCE_TEXT_FIELDS = {"component_block"}
OPERATOR_SOURCE_TEXT_FIELDS = {
	"operator_short_description",
	"operator_definition",
	"operator_guidance",
	"failure_mode_guidance",
	"decision_procedure",
}
PROVENANCE_ONLY_FIELDS = {"operator_block_heading", "heading_path"}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate raw schema JSON from a Layer 0 segmentation registry."
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
		choices=["auto", "layer0", "layer1", "layer2", "layer3", "layer4"],
		default="auto",
		help="Registry layer to load. Only layer0 is implemented currently.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		help="Directory for generated outputs. Defaults to the registry file directory.",
	)
	parser.add_argument(
		"--raw-output",
		"--rubric-output",
		dest="raw_output",
		type=Path,
		help="Explicit raw registry JSON output file path.",
	)
	parser.add_argument(
		"--normalized-output",
		"--manifest-output",
		dest="normalized_output",
		type=Path,
		help="Explicit normalized registry JSON output file path.",
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


def normalize_header_name(value: str) -> str:
	normalized = normalize_markdown_cell(value).strip().lower()
	normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
	return normalized.strip("_")


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


def collect_markdown_sections(lines: list[str]) -> list[dict[str, object]]:
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


def classify_section(section: dict[str, object]) -> str:
	title = str(section.get("title", "")).strip().lower()
	heading_path = [str(item).strip().lower() for item in section.get("heading_path", [])]
	if title == "registry metadata":
		return "metadata"
	if title in {"identifier construction rules", "reuse rule table", "component block rule table", "design rules"}:
		return "rules"
	if "base table" in heading_path and title != "base table":
		return "base_table_operator_block"
	if title == "base table":
		return "base_table"
	return "other"


def collect_markdown_tables(lines: list[str]) -> list[dict[str, object]]:
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

		headers = [normalize_header_name(cell) for cell in header_cells]
		row_records: list[dict[str, str]] = []
		index += 2
		while index < len(lines):
			candidate_line = lines[index]
			if HEADING_RE.match(candidate_line):
				break
			if "|" in candidate_line and index + 1 < len(lines):
				candidate_header_cells = parse_markdown_row(candidate_line)
				next_line = lines[index + 1]
				if (
					candidate_header_cells == header_cells
					and "|" in next_line
					and len(parse_markdown_row(next_line)) == len(candidate_header_cells)
					and is_separator_row(parse_markdown_row(next_line))
				):
					break
			if "|" in candidate_line:
				cells = parse_markdown_row(candidate_line)
				if len(cells) == len(headers):
					row_records.append(dict(zip(headers, cells, strict=True)))
					index += 1
					continue
				break
			if row_records:
				continuation = candidate_line.rstrip()
				if continuation.strip():
					last_header = headers[-1]
					current_value = row_records[-1].get(last_header, "")
					row_records[-1][last_header] = (
						f"{current_value}\n{continuation.strip()}" if current_value else continuation.strip()
					)
				index += 1
				continue
			break

		table_record = {
			"heading": current_heading,
			"heading_path": list(heading_path),
			"headers": headers,
			"rows": row_records,
		}
		if [str(header).strip().lower() for header in headers] == FIELD_VALUE_HEADERS:
			tables.extend(split_field_value_table_records(table_record))
		else:
			tables.append(table_record)

	return tables


def find_first_table_by_heading(tables: list[dict[str, object]], heading_text: str) -> dict[str, object] | None:
	normalized_heading = heading_text.strip().lower()
	for table in tables:
		if str(table.get("heading", "")).strip().lower() == normalized_heading:
			return table
	return None


def is_field_value_table(table: dict[str, object]) -> bool:
	headers = [str(header).strip().lower() for header in table.get("headers", [])]
	return headers == FIELD_VALUE_HEADERS


def split_field_value_table_records(table: dict[str, object]) -> list[dict[str, object]]:
	if not is_field_value_table(table):
		return [table]

	split_tables: list[dict[str, object]] = []
	current_rows: list[dict[str, str]] = []
	seen_fields: set[str] = set()
	for row in table.get("rows", []):
		field_name = normalize_header_name(str(row.get("field", "")))
		if field_name and field_name in seen_fields and current_rows:
			split_tables.append(
				{
					"heading": table.get("heading", ""),
					"heading_path": list(table.get("heading_path", [])),
					"headers": list(table.get("headers", [])),
					"rows": current_rows,
				}
			)
			current_rows = []
			seen_fields = set()
		current_rows.append(row)
		if field_name:
			seen_fields.add(field_name)

	if current_rows:
		split_tables.append(
			{
				"heading": table.get("heading", ""),
				"heading_path": list(table.get("heading_path", [])),
				"headers": list(table.get("headers", [])),
				"rows": current_rows,
			}
		)
	return split_tables


def convert_field_value_table_to_record(table: dict[str, object]) -> dict[str, str]:
	if not is_field_value_table(table):
		raise ValueError("Table is not a field/value record table.")
	record: dict[str, str] = {}
	for row in table.get("rows", []):
		field_name = normalize_header_name(str(row.get("field", "")))
		if not field_name:
			continue
		if field_name in record:
			raise ValueError(f"Duplicate field {field_name!r} in field/value record table.")
		record[field_name] = str(row.get("value", "")).strip()
	return record


def validate_table_headers(table_name: str, table: dict[str, object] | None, required_headers: set[str]) -> None:
	if table is None:
		raise ValueError(f"Required table not found: {table_name}")
	headers = {str(header).strip().lower() for header in table.get("headers", [])}
	missing = sorted(required_headers.difference(headers))
	if missing:
		raise ValueError(f"Table {table_name!r} is missing required columns: {missing}")


def validate_record_fields(record_name: str, record: dict[str, str], required_fields: set[str]) -> None:
	missing = sorted(field for field in required_fields if not record.get(field, "").strip())
	if missing:
		raise ValueError(f"Record {record_name!r} is missing required fields: {missing}")


def build_section_summaries(sections: list[dict[str, object]]) -> list[dict[str, object]]:
	return [
		{
			"title": section["title"],
			"raw_title": section["raw_title"],
			"level": section["level"],
			"heading_path": section["heading_path"],
			"section_type": classify_section(section),
		}
		for section in sections
	]


def build_operator_rows(
	tables: list[dict[str, object]],
	*,
	include_inactive: bool,
) -> list[dict[str, str]]:
	operator_rows: list[dict[str, str]] = []
	for table in tables:
		heading_path = [str(item).strip().lower() for item in table.get("heading_path", [])]
		if "base table" not in heading_path or not is_field_value_table(table):
			continue
		record = convert_field_value_table_to_record(table)
		if not record:
			continue
		validate_record_fields(str(table.get("heading", "")), record, OPERATOR_REQUIRED_FIELDS)
		status = record.get("status", "").strip().lower()
		if not include_inactive and status and status != "active":
			continue
		record["operator_block_heading"] = str(table.get("heading", "")).strip()
		record["heading_path"] = " > ".join(str(item) for item in table.get("heading_path", []))
		operator_rows.append(record)
	return operator_rows


def infer_registry_layer(registry_path: Path, requested_layer: str) -> str:
	if requested_layer not in LAYER0_ALLOWED_LAYERS:
		raise ValueError("generate_schema_from_segmentation_registry.py currently supports only layer0 registries.")
	if requested_layer == "layer0":
		return "layer0"
	registry_name = registry_path.name.lower()
	if "layer0" in registry_name or "segmentation" in registry_name:
		return "layer0"
	raise ValueError("Could not infer a Layer 0 segmentation registry. Pass --registry-layer layer0 explicitly.")


def collapse_internal_whitespace(value: str) -> str:
	return re.sub(r"\s+", " ", value.strip())


def normalize_multiline_text(value: str) -> dict[str, object]:
	raw_text = value.strip()
	lines = [collapse_internal_whitespace(line) for line in raw_text.splitlines() if line.strip()]
	return {
		"raw": raw_text,
		"lines": lines,
		"single_line": " | ".join(lines),
	}


def normalize_scalar_value(field_name: str, value: str) -> str:
	normalized = collapse_internal_whitespace(value)
	if field_name == "status":
		return normalized.lower()
	return normalized


def coerce_heading_path(value: object) -> list[str]:
	if isinstance(value, list):
		return [collapse_internal_whitespace(str(item)) for item in value if str(item).strip()]
	if isinstance(value, str):
		return [part.strip() for part in value.split(">") if part.strip()]
	return []


def normalize_registry_metadata(registry_metadata: dict[str, str]) -> dict[str, str]:
	return {
		field_name: normalize_scalar_value(field_name, value)
		for field_name, value in registry_metadata.items()
	}


def build_normalized_row(
	row: dict[str, str],
	*,
	section_name: str,
	source_table_type: str,
	source_heading: str,
	source_heading_path: list[str],
	source_row_index: int,
	source_text_fields: set[str],
	provenance_only_fields: set[str] | None = None,
) -> dict[str, object]:
	provenance_only_fields = provenance_only_fields or set()
	execution_fields: dict[str, str] = {}
	source_text: dict[str, dict[str, object]] = {}
	missing_execution_fields: list[str] = []
	missing_source_text_fields: list[str] = []

	for field_name, value in row.items():
		if field_name in provenance_only_fields:
			continue
		if field_name in source_text_fields:
			normalized_text = normalize_multiline_text(value)
			source_text[field_name] = normalized_text
			if not normalized_text["single_line"]:
				missing_source_text_fields.append(field_name)
			continue
		normalized_value = normalize_scalar_value(field_name, value)
		execution_fields[field_name] = normalized_value
		if not normalized_value:
			missing_execution_fields.append(field_name)

	if execution_fields.get("block_rule_id", "") and execution_fields.get("component_id", ""):
		row_identifier = f"{execution_fields['block_rule_id']}::{execution_fields['component_id']}"
	else:
		row_identifier = next(
			(
				execution_fields.get(candidate, "")
				for candidate in ("rule_id", "block_rule_id", "segment_id", "field", "template_id")
				if execution_fields.get(candidate, "")
			),
			f"{section_name}_row_{source_row_index}",
		)

	return {
		"row_id": row_identifier,
		"meta": {
			"section_name": section_name,
			"source_table_type": source_table_type,
			"source_heading": source_heading,
			"source_heading_path": source_heading_path,
			"source_row_index": source_row_index,
		},
		"execution_fields": execution_fields,
		"source_text": source_text,
		"validation": {
			"missing_execution_fields": missing_execution_fields,
			"missing_source_text_fields": missing_source_text_fields,
			"is_complete": not missing_execution_fields and not missing_source_text_fields,
		},
	}


def normalize_identifier_construction_rules(rows: list[dict[str, str]]) -> list[dict[str, object]]:
	return [
		build_normalized_row(
			row,
			section_name="identifier_construction_rules",
			source_table_type="markdown_table",
			source_heading="identifier construction rules",
			source_heading_path=["identifier construction rules"],
			source_row_index=row_index,
			source_text_fields=IDENTIFIER_RULE_SOURCE_TEXT_FIELDS,
		)
		for row_index, row in enumerate(rows, start=1)
	]


def normalize_reuse_rules(rows: list[dict[str, str]]) -> list[dict[str, object]]:
	return [
		build_normalized_row(
			row,
			section_name="reuse_rules",
			source_table_type="markdown_table",
			source_heading="reuse rule table",
			source_heading_path=["reuse rule table"],
			source_row_index=row_index,
			source_text_fields=set(),
		)
		for row_index, row in enumerate(rows, start=1)
	]


def normalize_component_block_rules(rows: list[dict[str, str]]) -> list[dict[str, object]]:
	return [
		build_normalized_row(
			row,
			section_name="component_block_rules",
			source_table_type="markdown_table",
			source_heading="component block rule table",
			source_heading_path=["component block rule table"],
			source_row_index=row_index,
			source_text_fields=COMPONENT_BLOCK_SOURCE_TEXT_FIELDS,
		)
		for row_index, row in enumerate(rows, start=1)
	]


def normalize_operator_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
	normalized_rows: list[dict[str, object]] = []
	for row_index, row in enumerate(rows, start=1):
		normalized_rows.append(
			build_normalized_row(
				row,
				section_name="operator_rows",
				source_table_type="field_value_record",
				source_heading=row.get("operator_block_heading", ""),
				source_heading_path=coerce_heading_path(row.get("heading_path", [])),
				source_row_index=row_index,
				source_text_fields=OPERATOR_SOURCE_TEXT_FIELDS,
				provenance_only_fields=PROVENANCE_ONLY_FIELDS,
			)
		)
	return normalized_rows


def validate_unique_execution_field(
	rows: list[dict[str, object]],
	field_name: str,
	section_name: str,
) -> list[str]:
	seen_values: dict[str, str] = {}
	errors: list[str] = []
	for row in rows:
		execution_fields = row.get("execution_fields", {})
		if not isinstance(execution_fields, dict):
			continue
		value = str(execution_fields.get(field_name, "")).strip()
		if not value:
			continue
		if value in seen_values:
			errors.append(
				f"Duplicate {field_name} in {section_name}: {value!r} appears in {seen_values[value]!r} and {row.get('row_id', '')!r}."
			)
			continue
		seen_values[value] = str(row.get("row_id", ""))
	return errors


def validate_unique_execution_tuple(
	rows: list[dict[str, object]],
	field_names: tuple[str, ...],
	section_name: str,
) -> list[str]:
	seen_values: dict[tuple[str, ...], str] = {}
	errors: list[str] = []
	for row in rows:
		execution_fields = row.get("execution_fields", {})
		if not isinstance(execution_fields, dict):
			continue
		value_tuple = tuple(str(execution_fields.get(field_name, "")).strip() for field_name in field_names)
		if not all(value_tuple):
			continue
		if value_tuple in seen_values:
			errors.append(
				f"Duplicate {field_names!r} in {section_name}: {value_tuple!r} appears in {seen_values[value_tuple]!r} and {row.get('row_id', '')!r}."
			)
			continue
		seen_values[value_tuple] = str(row.get("row_id", ""))
	return errors


def validate_normalized_registry_payload(payload: dict[str, object]) -> dict[str, object]:
	errors: list[str] = []
	warnings: list[str] = []

	section_rows: dict[str, list[dict[str, object]]] = {
		"identifier_construction_rules": list(payload.get("identifier_construction_rules", [])),
		"reuse_rules": list(payload.get("reuse_rules", [])),
		"component_block_rules": list(payload.get("component_block_rules", [])),
		"operator_rows": list(payload.get("operator_rows", [])),
	}

	for section_name, rows in section_rows.items():
		for row in rows:
			validation = row.get("validation", {})
			if not isinstance(validation, dict):
				errors.append(f"{section_name} row {row.get('row_id', '')!r} is missing validation metadata.")
				continue
			if not bool(validation.get("is_complete", False)):
				errors.append(
					f"{section_name} row {row.get('row_id', '')!r} is incomplete: "
					f"missing execution fields={validation.get('missing_execution_fields', [])}, "
					f"missing source text fields={validation.get('missing_source_text_fields', [])}."
				)

	errors.extend(validate_unique_execution_field(section_rows["identifier_construction_rules"], "field", "identifier_construction_rules"))
	errors.extend(validate_unique_execution_field(section_rows["reuse_rules"], "rule_id", "reuse_rules"))
	errors.extend(
		validate_unique_execution_tuple(
			section_rows["component_block_rules"],
			("block_rule_id", "component_id"),
			"component_block_rules",
		)
	)
	errors.extend(validate_unique_execution_field(section_rows["operator_rows"], "segment_id", "operator_rows"))

	operator_slot_pairs: set[tuple[str, str]] = set()
	for row in section_rows["operator_rows"]:
		execution_fields = row.get("execution_fields", {})
		if not isinstance(execution_fields, dict):
			continue
		pair = (
			str(execution_fields.get("template_id", "")).strip(),
			str(execution_fields.get("local_slot", "")).strip(),
		)
		if not pair[0] or not pair[1]:
			continue
		if pair in operator_slot_pairs:
			errors.append(f"Duplicate operator template/local_slot pair detected: {pair!r}.")
			continue
		operator_slot_pairs.add(pair)

	component_block_rule_ids = {
		str(row.get("execution_fields", {}).get("block_rule_id", "")).strip()
		for row in section_rows["component_block_rules"]
		if isinstance(row.get("execution_fields", {}), dict)
	}
	for row in section_rows["reuse_rules"]:
		execution_fields = row.get("execution_fields", {})
		if not isinstance(execution_fields, dict):
			continue
		component_block_rule = str(execution_fields.get("component_block_rule", "")).strip()
		if component_block_rule and component_block_rule not in component_block_rule_ids:
			errors.append(
				f"Reuse rule {row.get('row_id', '')!r} references unknown component_block_rule {component_block_rule!r}."
			)

	registry_metadata = payload.get("registry_metadata", {})
	if not isinstance(registry_metadata, dict):
		errors.append("registry_metadata must be a JSON object.")
	else:
		for field_name in sorted(REGISTRY_METADATA_REQUIRED_FIELDS):
			if not str(registry_metadata.get(field_name, "")).strip():
				errors.append(f"registry_metadata is missing required field {field_name!r}.")

	if not section_rows["operator_rows"]:
		warnings.append("No operator rows were produced in the normalized registry.")

	return {
		"is_valid": not errors,
		"errors": errors,
		"warnings": warnings,
		"counts": {section_name: len(rows) for section_name, rows in section_rows.items()},
	}


def build_normalized_registry_payload(raw_payload: dict[str, object]) -> dict[str, object]:
	normalized_payload = {
		"generated_at_utc": datetime.now(timezone.utc).isoformat(),
		"registry_path": raw_payload["registry_path"],
		"registry_layer": raw_payload["registry_layer"],
		"normalization_version": "v1",
		"registry_metadata": normalize_registry_metadata(dict(raw_payload["registry_metadata"])),
		"identifier_construction_rules": normalize_identifier_construction_rules(
			list(raw_payload.get("identifier_construction_rules", []))
		),
		"reuse_rules": normalize_reuse_rules(list(raw_payload.get("reuse_rules", []))),
		"component_block_rules": normalize_component_block_rules(
			list(raw_payload.get("component_block_rules", []))
		),
		"operator_rows": normalize_operator_rows(list(raw_payload.get("operator_rows", []))),
	}
	validation = validate_normalized_registry_payload(normalized_payload)
	normalized_payload["validation"] = validation
	if not validation["is_valid"]:
		raise ValueError("Normalized registry validation failed:\n- " + "\n- ".join(validation["errors"]))
	return normalized_payload


def resolve_output_paths(
	registry_path: Path,
	output_dir: Path | None,
	raw_output: Path | None,
	normalized_output: Path | None,
) -> tuple[Path, Path]:
	resolved_output_dir = output_dir.resolve() if output_dir else registry_path.parent.resolve()
	resolved_output_dir.mkdir(parents=True, exist_ok=True)
	base_stem = registry_path.stem
	resolved_raw_output = (raw_output or (resolved_output_dir / f"{base_stem}_raw_registry.json")).resolve()
	resolved_normalized_output = (
		normalized_output or (resolved_output_dir / f"{base_stem}_normalized_registry.json")
	).resolve()
	resolved_raw_output.parent.mkdir(parents=True, exist_ok=True)
	resolved_normalized_output.parent.mkdir(parents=True, exist_ok=True)
	if resolved_raw_output == resolved_normalized_output:
		raise ValueError("Raw and normalized registry outputs must resolve to different file paths.")
	return resolved_raw_output, resolved_normalized_output


def build_raw_schema_payload(registry_path: Path, include_inactive: bool, registry_layer: str) -> dict[str, object]:
	lines = registry_path.read_text(encoding="utf-8").splitlines()
	sections = collect_markdown_sections(lines)
	tables = collect_markdown_tables(lines)

	registry_metadata_table = find_first_table_by_heading(tables, "registry metadata")
	identifier_rules_table = find_first_table_by_heading(tables, "identifier construction rules")
	reuse_rules_table = find_first_table_by_heading(tables, "reuse rule table")
	component_block_rules_table = find_first_table_by_heading(tables, "component block rule table")

	if registry_metadata_table is None or not is_field_value_table(registry_metadata_table):
		raise ValueError("registry metadata must be present as a field/value table")
	registry_metadata = convert_field_value_table_to_record(registry_metadata_table)
	validate_record_fields("registry metadata", registry_metadata, REGISTRY_METADATA_REQUIRED_FIELDS)

	validate_table_headers("identifier construction rules", identifier_rules_table, IDENTIFIER_RULE_REQUIRED_HEADERS)
	validate_table_headers("reuse rule table", reuse_rules_table, REUSE_RULE_REQUIRED_COLUMNS)
	validate_table_headers("component block rule table", component_block_rules_table, COMPONENT_BLOCK_RULE_REQUIRED_COLUMNS)

	reuse_rules = list(reuse_rules_table.get("rows", [])) if reuse_rules_table else []
	if not include_inactive:
		reuse_rules = [row for row in reuse_rules if str(row.get("status", "")).strip().lower() == "active"]

	component_block_rules = list(component_block_rules_table.get("rows", [])) if component_block_rules_table else []
	operator_rows = build_operator_rows(tables, include_inactive=include_inactive)

	return {
		"generated_at_utc": datetime.now(timezone.utc).isoformat(),
		"registry_path": str(registry_path.resolve()),
		"registry_layer": registry_layer,
		"registry_metadata": registry_metadata,
		"identifier_construction_rules": list(identifier_rules_table.get("rows", [])) if identifier_rules_table else [],
		"reuse_rules": reuse_rules,
		"component_block_rules": component_block_rules,
		"operator_rows": operator_rows,
		"sections": build_section_summaries(sections),
		"tables": tables,
	}


def write_json_output(output_path: Path, payload: dict[str, object]) -> None:
	output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
	args = parse_args()
	registry_path = args.registry_path.resolve()
	if not registry_path.exists():
		raise FileNotFoundError(f"Registry not found: {registry_path}")

	registry_layer = infer_registry_layer(registry_path, args.registry_layer)
	payload = build_raw_schema_payload(
		registry_path=registry_path,
		include_inactive=args.include_inactive,
		registry_layer=registry_layer,
	)
	normalized_payload = build_normalized_registry_payload(payload)
	raw_output_path, normalized_output_path = resolve_output_paths(
		registry_path=registry_path,
		output_dir=args.output_dir,
		raw_output=args.raw_output,
		normalized_output=args.normalized_output,
	)
	write_json_output(raw_output_path, payload)
	write_json_output(normalized_output_path, normalized_payload)

	print(f"Registry: {registry_path}")
	print(f"Registry layer: {registry_layer}")
	print(f"Raw registry output: {raw_output_path}")
	print(f"Normalized registry output: {normalized_output_path}")
	print(f"Reuse rules written: {len(payload['reuse_rules'])}")
	print(f"Component block rules written: {len(payload['component_block_rules'])}")
	print(f"Operator rows written: {len(payload['operator_rows'])}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())