#!/usr/bin/env python3
"""Parse a Layer 0 segmentation registry markdown file into raw tabular JSON.

This script currently implements Step 1 of the schema-generation workflow:

- read registry Markdown contents
- detect section boundaries
- parse Markdown tables into normalized row dictionaries
- preserve multiline field/value records
- validate required columns for known Layer 0 table types
- emit raw JSON structures including registry_metadata, reuse_rules,
  component_block_rules, and operator_rows

The command-line contract mostly mirrors
generate_rubric_and_manifest_from_indicator_registry.py, but this step writes
one JSON artifact.
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
		"--rubric-output",
		type=Path,
		help="Explicit primary JSON output file path.",
	)
	parser.add_argument(
		"--manifest-output",
		type=Path,
		help="Explicit secondary JSON output file path.",
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


def resolve_output_path(
	registry_path: Path,
	output_dir: Path | None,
	rubric_output: Path | None,
	manifest_output: Path | None,
) -> Path:
	resolved_output_dir = output_dir.resolve() if output_dir else registry_path.parent.resolve()
	resolved_output_dir.mkdir(parents=True, exist_ok=True)
	base_stem = registry_path.stem
	output_path = rubric_output or manifest_output or (resolved_output_dir / f"{base_stem}_schema.json")
	resolved_output_path = output_path.resolve()
	resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
	return resolved_output_path


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
	output_path = resolve_output_path(
		registry_path=registry_path,
		output_dir=args.output_dir,
		rubric_output=args.rubric_output,
		manifest_output=args.manifest_output,
	)
	write_json_output(output_path, payload)

	print(f"Registry: {registry_path}")
	print(f"Registry layer: {registry_layer}")
	print(f"JSON output: {output_path}")
	print(f"Reuse rules written: {len(payload['reuse_rules'])}")
	print(f"Component block rules written: {len(payload['component_block_rules'])}")
	print(f"Operator rows written: {len(payload['operator_rows'])}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())