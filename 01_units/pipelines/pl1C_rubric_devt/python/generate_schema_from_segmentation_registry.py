#!/usr/bin/env python3
"""Parse a Layer 0 segmentation registry into raw and normalized artifacts.

This script currently implements:

- Step 1: parse registry Markdown into a raw registry JSON artifact
- Step 1: emit a normalized registry JSON artifact that separates execution
  fields from source text while preserving provenance
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


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
COMPONENT_BLOCK_RULE_COMPATIBILITY_ALIASES = {
	"source_component_id": "component_id",
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
COMPONENT_BLOCK_SOURCE_TEXT_FIELDS: set[str] = set()
OPERATOR_SOURCE_TEXT_FIELDS = {
	"operator_short_description",
	"operator_definition",
	"operator_guidance",
	"failure_mode_guidance",
	"decision_procedure",
}
PROVENANCE_ONLY_FIELDS = {"operator_block_heading", "heading_path"}
NORMALIZED_REQUIRED_SECTIONS = {
	"registry_metadata",
	"identifier_construction_rules",
	"reuse_rules",
	"component_block_rules",
	"operator_templates",
}
EXPANDED_INSTANCE_REQUIRED_FIELDS = {
	"assessment_id",
	"component_id",
	"cid",
	"template_id",
	"local_slot",
	"operator_id",
	"operator_identifier",
	"operator_identifier_shortid",
	"operator_short_description",
	"operator_definition",
	"operator_guidance",
	"failure_mode_guidance",
	"decision_procedure",
	"output_mode",
	"segment_id",
	"template_group",
	"rule_id",
	"component_block",
	"instance_status",
	"source_template_id",
	"source_rule_id",
}
INTERACT_ANCHOR_PATTERNS = [
	"interact with",
	"interacts with",
	"intersect with",
	"intersects with",
]
KNOWN_STOP_MARKERS = {
	"comma",
	"sentence_start",
	"conjunction_boundary",
	"through",
	"clause_boundary",
	"shaping",
	"by",
	"comma_new_clause",
	"subordinate_extension",
	"sentence_end",
}
FAMILY_BY_LOCAL_SLOT = {
	"00": "claim_text_passthrough_if_anchor",
	"01": "left_np_before_anchor",
	"02": "right_np_after_anchor_before_marker",
	"03": "span_after_marker_before_marker",
	"04": "right_np_after_anchor_before_marker",
	"05": "local_effect_phrase_after_marker",
}
STOP_MARKERS_BY_LOCAL_SLOT = {
	"01": ["comma", "sentence_start", "conjunction_boundary"],
	"02": ["through", "comma", "clause_boundary"],
	"03": ["shaping", "comma", "clause_boundary"],
	"04": ["by", "comma", "clause_boundary"],
	"05": ["comma_new_clause", "subordinate_extension", "sentence_end"],
}
TARGET_TYPE_BY_LOCAL_SLOT = {
	"01": "noun_phrase",
	"02": "noun_phrase",
	"03": "noun_phrase",
	"04": "noun_phrase",
	"05": "local_effect_phrase",
}
FAMILY_BEHAVIOR = {
	"left_np_before_anchor": {
		"direction": "left",
		"start_rule": "immediate_pre_anchor",
		"end_rule": "anchor_left_boundary",
		"allow_coordination": False,
		"skip_later_candidates": False,
	},
	"right_np_after_anchor_before_marker": {
		"direction": "right",
		"start_rule": "immediate_post_anchor",
		"end_rule": "first_stop_marker",
		"allow_coordination": False,
		"skip_later_candidates": False,
	},
	"span_after_marker_before_marker": {
		"direction": "right",
		"start_rule": "immediate_post_anchor",
		"end_rule": "first_stop_marker",
		"allow_coordination": True,
		"skip_later_candidates": False,
	},
	"local_effect_phrase_after_marker": {
		"direction": "right",
		"start_rule": "immediate_post_anchor",
		"end_rule": "local_effect_boundary",
		"allow_coordination": True,
		"skip_later_candidates": False,
	},
	"status_only_anchor_detector": {
		"direction": "none",
		"start_rule": "anchor_match_only",
		"end_rule": "none",
		"allow_coordination": False,
		"skip_later_candidates": False,
	},
	"claim_text_passthrough_if_anchor": {
		"direction": "none",
		"start_rule": "full_text_if_anchor_match",
		"end_rule": "full_text",
		"allow_coordination": False,
		"skip_later_candidates": False,
	},
}

ALLOW_COORDINATION_TEMPLATE_OVERRIDES = {
	"B_claim_seg_01": False,
	"B_claim_seg_02": True,
	"B_claim_seg_03": True,
	"B_claim_seg_04": True,
	"B_claim_seg_05": True,
}

ALLOW_COORDINATION_TEXT_FIELDS = (
	"operator_definition",
	"operator_guidance",
	"decision_procedure",
)

ALLOW_COORDINATION_SIGNAL_PHRASES = (
	"coordination",
	"compact coordination",
	"x and y",
	"comma-separated",
	"extend the span",
	"full coordinated phrase",
	"include the full coordinated phrase",
	"continues through compact coordination",
)


@dataclass(frozen=True)
class OperatorSpec:
	assessment_id: str
	component_id: str
	cid: str
	template_id: str
	local_slot: str
	operator_id: str
	operator_identifier: str
	operator_identifier_shortid: str
	operator_short_description: str
	segment_id: str
	output_mode: Literal["span", "status_only"]
	family: str
	anchor_patterns: list[str]
	direction: str | None
	start_rule: str | None
	end_rule: str | None
	stop_markers: list[str]
	target_type: str
	allow_coordination: bool
	skip_later_candidates: bool
	operator_definition: str
	operator_guidance: str
	failure_mode_guidance: str
	decision_procedure: str
	missing_status: str
	ambiguous_status: str
	malformed_status: str
	instance_status: str


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate raw, normalized, expanded, and compiled registry outputs from a Layer 0 segmentation registry."
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


def collect_coordination_text(row: dict[str, object]) -> str:
	parts: list[str] = []
	for field_name in ALLOW_COORDINATION_TEXT_FIELDS:
		value = str(row.get(field_name, "")).strip().lower()
		if value:
			parts.append(value)
	return "\n".join(parts)


def detect_coordination_support(row: dict[str, object]) -> bool:
	coordination_text = collect_coordination_text(row)
	if not coordination_text:
		return False
	return any(signal_phrase in coordination_text for signal_phrase in ALLOW_COORDINATION_SIGNAL_PHRASES)


def default_allow_coordination_for_family(family: str) -> bool:
	default_by_family = {
		"left_np_before_anchor": False,
		"right_np_after_anchor_before_marker": False,
		"span_after_marker_before_marker": False,
		"local_effect_phrase_after_marker": True,
		"status_only_anchor_detector": False,
	}
	return default_by_family.get(family, False)


def derive_allow_coordination(row: dict[str, object], family: str) -> bool:
	template_id = str(row.get("template_id", "")).strip()
	if template_id in ALLOW_COORDINATION_TEMPLATE_OVERRIDES:
		return ALLOW_COORDINATION_TEMPLATE_OVERRIDES[template_id]
	if detect_coordination_support(row):
		return True
	return default_allow_coordination_for_family(family)


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


def normalize_component_block_rules_table(table: dict[str, object] | None) -> dict[str, object] | None:
	if table is None:
		return None
	headers = [str(header).strip().lower() for header in table.get("headers", [])]
	if "component_id" in headers:
		return table
	if "source_component_id" not in headers:
		return table

	normalized_headers = [
		COMPONENT_BLOCK_RULE_COMPATIBILITY_ALIASES.get(header, header)
		for header in headers
	]
	normalized_rows: list[dict[str, str]] = []
	for raw_row in table.get("rows", []):
		normalized_row: dict[str, str] = {}
		for key, value in raw_row.items():
			normalized_key = COMPONENT_BLOCK_RULE_COMPATIBILITY_ALIASES.get(str(key).strip().lower(), str(key).strip().lower())
			normalized_row[normalized_key] = str(value).strip()
		normalized_rows.append(normalized_row)

	return {
		"heading": table.get("heading", ""),
		"heading_path": list(table.get("heading_path", [])),
		"headers": normalized_headers,
		"rows": normalized_rows,
	}


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
				for candidate in ("rule_id", "block_rule_id", "template_id", "segment_id", "field")
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


def normalize_operator_templates(rows: list[dict[str, str]]) -> list[dict[str, object]]:
	normalized_rows: list[dict[str, object]] = []
	for row_index, row in enumerate(rows, start=1):
		normalized_rows.append(
			build_normalized_row(
				row,
				section_name="operator_templates",
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
		"operator_templates": list(payload.get("operator_templates", [])),
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
	errors.extend(validate_unique_execution_field(section_rows["operator_templates"], "template_id", "operator_templates"))
	errors.extend(validate_unique_execution_field(section_rows["operator_templates"], "segment_id", "operator_templates"))

	operator_slot_pairs: set[tuple[str, str]] = set()
	for row in section_rows["operator_templates"]:
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

	if not section_rows["operator_templates"]:
		warnings.append("No operator templates were produced in the normalized registry.")

	return {
		"is_valid": not errors,
		"errors": errors,
		"warnings": warnings,
		"counts": {section_name: len(rows) for section_name, rows in section_rows.items()},
	}


def build_normalized_registry_payload(raw_payload: dict[str, object]) -> dict[str, object]:
	operator_templates = normalize_operator_templates(list(raw_payload.get("operator_rows", [])))
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
		"operator_templates": operator_templates,
		"operator_rows": operator_templates,
	}
	validation = validate_normalized_registry_payload(normalized_payload)
	normalized_payload["validation"] = validation
	if not validation["is_valid"]:
		raise ValueError("Normalized registry validation failed:\n- " + "\n- ".join(validation["errors"]))
	return normalized_payload


def get_row_execution_fields(row: dict[str, object]) -> dict[str, str]:
	execution_fields = row.get("execution_fields", {})
	if not isinstance(execution_fields, dict):
		raise ValueError(f"Row {row.get('row_id', '')!r} is missing execution_fields.")
	return {str(key): str(value) for key, value in execution_fields.items()}


def get_row_source_text_fields(row: dict[str, object]) -> dict[str, dict[str, object]]:
	source_text = row.get("source_text", {})
	if not isinstance(source_text, dict):
		raise ValueError(f"Row {row.get('row_id', '')!r} is missing source_text.")
	return source_text


def extract_normalized_row_value(row: dict[str, object], field_name: str) -> str:
	execution_fields = get_row_execution_fields(row)
	if field_name in execution_fields and execution_fields[field_name].strip():
		return execution_fields[field_name].strip()
	source_text = get_row_source_text_fields(row)
	entry = source_text.get(field_name)
	if isinstance(entry, dict):
		raw_value = str(entry.get("raw", "")).strip()
		if raw_value:
			return raw_value
		return str(entry.get("single_line", "")).strip()
	return ""


def load_normalized_registry(path: str | Path) -> dict[str, object]:
	registry_path = Path(path).resolve()
	data = json.loads(registry_path.read_text(encoding="utf-8"))
	if "operator_templates" not in data and "operator_rows" in data:
		data["operator_templates"] = data["operator_rows"]
	missing_sections = sorted(section for section in NORMALIZED_REQUIRED_SECTIONS if section not in data)
	if missing_sections:
		raise ValueError(f"Normalized registry is missing required sections: {missing_sections}")
	return data


def build_identifier_rule_lookup(registry: dict[str, object]) -> dict[str, str]:
	lookup: dict[str, str] = {}
	for row in list(registry.get("identifier_construction_rules", [])):
		field_name = extract_normalized_row_value(row, "field")
		rule_text = extract_normalized_row_value(row, "rule")
		if not field_name or not rule_text:
			raise ValueError(f"Malformed identifier construction row: {row!r}")
		lookup[field_name] = rule_text
	if "cid derivation rule" not in lookup and "legacy cid derivation note" in lookup:
		lookup["cid derivation rule"] = lookup["legacy cid derivation note"]
	return lookup


def resolve_component_pattern(pattern: str) -> list[str]:
	pattern = pattern.strip()
	if not pattern:
		raise ValueError("Component pattern cannot be empty.")
	range_match = re.fullmatch(r"(?P<prefix>.*)\{(?P<start>\d+)\.\.(?P<end>\d+)\}(?P<suffix>.*)", pattern)
	if range_match:
		start = int(range_match.group("start"))
		end = int(range_match.group("end"))
		if end < start:
			raise ValueError(f"Component pattern range is reversed: {pattern!r}")
		prefix = range_match.group("prefix")
		suffix = range_match.group("suffix")
		return [f"{prefix}{index}{suffix}" for index in range(start, end + 1)]
	if any(token in pattern for token in ["{", "}", "..", ","]):
		raise ValueError(f"Component pattern cannot be resolved deterministically: {pattern!r}")
	return [pattern]


def component_sort_key(component_id: str) -> tuple[object, ...]:
	match = re.fullmatch(r"Section(?P<section>[A-Za-z]+)(?P<index>\d+)Response", component_id)
	if match:
		return (match.group("section"), int(match.group("index")), component_id)
	fallback_match = re.search(r"(\d+)", component_id)
	if fallback_match:
		return (component_id[: fallback_match.start()], int(fallback_match.group(1)), component_id)
	return (component_id, 0, component_id)


def local_slot_sort_key(local_slot: str) -> tuple[int, str]:
	if re.fullmatch(r"\d+", local_slot):
		return (int(local_slot), local_slot)
	return (10**9, local_slot)


def derive_cid(component_id: str, rule_text: str) -> str:
	rule_text = collapse_internal_whitespace(rule_text)
	if "component_id" not in rule_text:
		raise ValueError(f"cid derivation rule is unsupported: {rule_text!r}")
	result = component_id
	transforms_applied = False
	for old, new in re.findall(r'replace\s+[`"]([^`"]+)[`"]\s+with\s+[`"]([^`"]+)[`"]', rule_text):
		result = result.replace(old, new)
		transforms_applied = True
	for token in re.findall(r'remove\s+[`"]([^`"]+)[`"]', rule_text):
		result = result.replace(token, "")
		transforms_applied = True
	if not transforms_applied:
		if "Section" in rule_text and "Sec" in rule_text:
			result = result.replace("Section", "Sec")
			transforms_applied = True
		if "Response" in rule_text and "remove" in rule_text.lower():
			result = result.replace("Response", "")
			transforms_applied = True
	result = result.strip()
	if not result or result == component_id or not transforms_applied:
		raise ValueError(f"cid derivation failed for component_id={component_id!r} using rule {rule_text!r}")
	return result


def build_operator_id(component_block: str, local_slot: str, fmt: str) -> str:
	try:
		operator_id = fmt.format(component_block=component_block, local_slot=local_slot)
	except KeyError as exc:
		raise ValueError(f"operator_id_format references unknown field: {exc}") from exc
	if not operator_id.strip() or "{" in operator_id or "}" in operator_id:
		raise ValueError(f"operator_id construction failed for format {fmt!r}")
	return operator_id.strip()


def build_operator_identifier(
	assessment_id: str,
	cid: str,
	operator_id: str,
	rule_text: str,
	*,
	component_block: str = "",
	claim_index: str = "X",
) -> str:
	try:
		operator_identifier = rule_text.format(
			assessment_id=assessment_id,
			cid=cid,
			component_block=component_block,
			claim_index=claim_index,
			operator_id=operator_id,
		)
	except KeyError as exc:
		raise ValueError(f"operator_identifier rule references unknown field: {exc}") from exc
	if not operator_identifier.strip() or "{" in operator_identifier or "}" in operator_identifier:
		raise ValueError(f"operator_identifier construction failed for rule {rule_text!r}")
	return operator_identifier.strip()


def build_operator_identifier_shortid(operator_id: str, rule_text: str) -> str:
	if collapse_internal_whitespace(rule_text) == "operator_id":
		return operator_id
	try:
		shortid = rule_text.format(operator_id=operator_id)
	except KeyError as exc:
		raise ValueError(f"operator_identifier_shortid rule references unknown field: {exc}") from exc
	if not shortid.strip() or "{" in shortid or "}" in shortid:
		raise ValueError(f"operator_identifier_shortid construction failed for rule {rule_text!r}")
	return shortid.strip()


def template_matches_group(template_id: str, template_group: str) -> bool:
	return template_id.startswith(f"{template_group}_")


def validate_normalized_row_required_fields(
	rows: list[dict[str, object]],
	required_fields: set[str],
	section_name: str,
) -> None:
	for row in rows:
		missing = sorted(field for field in required_fields if not extract_normalized_row_value(row, field))
		if missing:
			raise ValueError(f"{section_name} row {row.get('row_id', '')!r} is missing required fields: {missing}")


def expand_registry_instances(registry: dict[str, object]) -> dict[str, object]:
	missing_sections = sorted(section for section in NORMALIZED_REQUIRED_SECTIONS if section not in registry)
	if missing_sections:
		raise ValueError(f"Normalized registry is missing required sections: {missing_sections}")

	registry_metadata = registry.get("registry_metadata", {})
	if not isinstance(registry_metadata, dict):
		raise ValueError("registry_metadata must be present in the normalized registry.")
	assessment_id = str(registry_metadata.get("assessment_id", "")).strip()
	registry_version = str(registry_metadata.get("registry_version", "")).strip()
	if not assessment_id:
		raise ValueError("Normalized registry is missing assessment_id.")

	identifier_rules = build_identifier_rule_lookup(registry)
	for required_field in ["operator_identifier", "operator_identifier_shortid", "cid derivation rule"]:
		if required_field not in identifier_rules:
			raise ValueError(f"Identifier construction rules are missing required field {required_field!r}.")

	reuse_rules = list(registry.get("reuse_rules", []))
	component_block_rules = list(registry.get("component_block_rules", []))
	operator_templates = list(registry.get("operator_templates", []))

	validate_normalized_row_required_fields(reuse_rules, REUSE_RULE_REQUIRED_COLUMNS, "reuse_rules")
	validate_normalized_row_required_fields(component_block_rules, COMPONENT_BLOCK_RULE_REQUIRED_COLUMNS, "component_block_rules")
	validate_normalized_row_required_fields(operator_templates, OPERATOR_REQUIRED_FIELDS, "operator_templates")

	active_reuse_rules = [
		row for row in reuse_rules if extract_normalized_row_value(row, "status").strip().lower() == "active"
	]
	component_block_lookup: dict[tuple[str, str], str] = {}
	for row in component_block_rules:
		block_rule_id = extract_normalized_row_value(row, "block_rule_id")
		component_id = extract_normalized_row_value(row, "component_id")
		component_block = extract_normalized_row_value(row, "component_block")
		lookup_key = (block_rule_id, component_id)
		if lookup_key in component_block_lookup:
			raise ValueError(f"Duplicate component block mapping detected for {lookup_key!r}.")
		component_block_lookup[lookup_key] = component_block

	expanded_instances: list[dict[str, object]] = []
	for template_row in operator_templates:
		template_status = extract_normalized_row_value(template_row, "status").lower()
		if template_status != "active":
			continue
		template_id = extract_normalized_row_value(template_row, "template_id")
		matching_rules = [
			rule for rule in active_reuse_rules if template_matches_group(template_id, extract_normalized_row_value(rule, "template_group"))
		]
		if not matching_rules:
			raise ValueError(f"No active reuse rule found for active template {template_id!r}.")
		if len(matching_rules) > 1:
			raise ValueError(f"Multiple active reuse rules match template {template_id!r}.")
		reuse_rule = matching_rules[0]
		rule_assessment_id = extract_normalized_row_value(reuse_rule, "assessment_id")
		if rule_assessment_id != assessment_id:
			raise ValueError(
				f"Reuse rule {extract_normalized_row_value(reuse_rule, 'rule_id')!r} assessment_id {rule_assessment_id!r} does not match registry assessment_id {assessment_id!r}."
			)
		if extract_normalized_row_value(reuse_rule, "local_slot_source") != "template.local_slot":
			raise ValueError(
				f"Unsupported local_slot_source for reuse rule {extract_normalized_row_value(reuse_rule, 'rule_id')!r}."
			)
		component_ids = resolve_component_pattern(extract_normalized_row_value(reuse_rule, "applies_to_component_pattern"))
		for component_id in component_ids:
			component_block_lookup_key = (
				extract_normalized_row_value(reuse_rule, "component_block_rule"),
				component_id,
			)
			if component_block_lookup_key not in component_block_lookup:
				raise ValueError(
					f"Component block cannot be resolved for template {template_id!r} and component {component_id!r}."
				)
			component_block = component_block_lookup[component_block_lookup_key]
			local_slot = extract_normalized_row_value(template_row, "local_slot")
			cid = derive_cid(component_id, identifier_rules["cid derivation rule"])
			operator_id = build_operator_id(
				component_block=component_block,
				local_slot=local_slot,
				fmt=extract_normalized_row_value(reuse_rule, "operator_id_format"),
			)
			operator_identifier = build_operator_identifier(
				assessment_id=assessment_id,
				cid=cid,
				operator_id=operator_id,
				rule_text=identifier_rules["operator_identifier"],
				component_block=component_block,
				claim_index="X",
			)
			operator_identifier_shortid = build_operator_identifier_shortid(
				operator_id=operator_id,
				rule_text=identifier_rules["operator_identifier_shortid"],
			)
			expanded_instances.append(
				{
					"assessment_id": assessment_id,
					"component_id": component_id,
					"cid": cid,
					"template_id": template_id,
					"local_slot": local_slot,
					"operator_id": operator_id,
					"operator_identifier": operator_identifier,
					"operator_identifier_shortid": operator_identifier_shortid,
					"operator_short_description": extract_normalized_row_value(template_row, "operator_short_description"),
					"operator_definition": extract_normalized_row_value(template_row, "operator_definition"),
					"operator_guidance": extract_normalized_row_value(template_row, "operator_guidance"),
					"failure_mode_guidance": extract_normalized_row_value(template_row, "failure_mode_guidance"),
					"decision_procedure": extract_normalized_row_value(template_row, "decision_procedure"),
					"output_mode": extract_normalized_row_value(template_row, "output_mode"),
					"segment_id": extract_normalized_row_value(template_row, "segment_id"),
					"template_group": extract_normalized_row_value(reuse_rule, "template_group"),
					"rule_id": extract_normalized_row_value(reuse_rule, "rule_id"),
					"component_block": component_block,
					"instance_status": "active",
					"source_template_id": template_id,
					"source_rule_id": extract_normalized_row_value(reuse_rule, "rule_id"),
					"_source_template_order": int(template_row.get("meta", {}).get("source_row_index", 0)),
				}
			)

	expanded_instances.sort(
		key=lambda row: (
			component_sort_key(str(row["component_id"])),
			local_slot_sort_key(str(row["local_slot"])),
			int(row.get("_source_template_order", 0)),
		)
	)
	for row in expanded_instances:
		row.pop("_source_template_order", None)

	expanded_payload = {
		"generated_at_utc": datetime.now(timezone.utc).isoformat(),
		"assessment_id": assessment_id,
		"source_registry_version": registry_version,
		"expanded_instances": expanded_instances,
	}
	validate_expanded_instances(expanded_payload)
	return expanded_payload


def validate_expanded_instances(data: dict[str, object]) -> None:
	assessment_id = str(data.get("assessment_id", "")).strip()
	if not assessment_id:
		raise ValueError("Expanded registry is missing assessment_id.")
	expanded_instances = list(data.get("expanded_instances", []))
	if not expanded_instances:
		raise ValueError("Expanded registry output row count is zero.")

	operator_identifiers: set[str] = set()
	component_template_pairs: set[tuple[str, str]] = set()
	for row in expanded_instances:
		missing = sorted(field for field in EXPANDED_INSTANCE_REQUIRED_FIELDS if not str(row.get(field, "")).strip())
		if missing:
			raise ValueError(f"Expanded instance row is missing required fields: {missing}; row={row!r}")
		if str(row.get("instance_status", "")).strip().lower() != "active":
			raise ValueError(f"Inactive expanded instance row encountered: {row!r}")
		operator_identifier = str(row["operator_identifier"]).strip()
		if operator_identifier in operator_identifiers:
			raise ValueError(f"Duplicate operator_identifier would be emitted: {operator_identifier!r}")
		operator_identifiers.add(operator_identifier)
		pair = (str(row["component_id"]).strip(), str(row["template_id"]).strip())
		if pair in component_template_pairs:
			raise ValueError(f"Duplicate (component_id, template_id) instance would be emitted: {pair!r}")
		component_template_pairs.add(pair)


def assign_family(row: dict[str, object]) -> str:
	output_mode = str(row.get("output_mode", "")).strip().lower()
	local_slot = str(row.get("local_slot", "")).strip()
	if output_mode == "status_only":
		return "status_only_anchor_detector"
	family = FAMILY_BY_LOCAL_SLOT.get(local_slot)
	if not family:
		raise ValueError(f"Could not assign runtime family for local_slot {local_slot!r}.")
	return family


def combined_instruction_text(row: dict[str, object]) -> str:
	return " ".join(
		collapse_internal_whitespace(str(row.get(field, "")))
		for field in ["operator_definition", "operator_guidance", "failure_mode_guidance", "decision_procedure"]
	).lower()


def derive_anchor_patterns(row: dict[str, object], family: str) -> list[str]:
	text = combined_instruction_text(row)
	local_slot = str(row.get("local_slot", "")).strip()
	if family == "status_only_anchor_detector":
		if any(pattern in text for pattern in INTERACT_ANCHOR_PATTERNS):
			return INTERACT_ANCHOR_PATTERNS
		raise ValueError(f"Anchor patterns cannot be derived for status-only operator {row.get('template_id', '')!r}.")
	if local_slot == "00":
		if any(pattern in text for pattern in INTERACT_ANCHOR_PATTERNS):
			return INTERACT_ANCHOR_PATTERNS
		raise ValueError(f"Anchor patterns cannot be derived for template {row.get('template_id', '')!r}.")
	if local_slot in {"01", "02"}:
		if any(pattern in text for pattern in INTERACT_ANCHOR_PATTERNS):
			return INTERACT_ANCHOR_PATTERNS
		raise ValueError(f"Anchor patterns cannot be derived for template {row.get('template_id', '')!r}.")
	if local_slot == "03":
		if "through" in text:
			return ["through"]
		raise ValueError(f"Anchor patterns cannot be derived for template {row.get('template_id', '')!r}.")
	if local_slot == "04":
		if "shaping" in text:
			return ["shaping"]
		raise ValueError(f"Anchor patterns cannot be derived for template {row.get('template_id', '')!r}.")
	if local_slot == "05":
		if "by" in text and "shaping" in text:
			return ["by"]
		raise ValueError(f"Anchor patterns cannot be derived for template {row.get('template_id', '')!r}.")
	raise ValueError(f"Anchor patterns cannot be derived for template {row.get('template_id', '')!r}.")


def derive_stop_markers(row: dict[str, object], family: str) -> list[str]:
	if family == "status_only_anchor_detector":
		return []
	local_slot = str(row.get("local_slot", "")).strip()
	if local_slot == "00":
		return []
	if local_slot not in STOP_MARKERS_BY_LOCAL_SLOT:
		raise ValueError(f"Stop markers cannot be derived for local_slot {local_slot!r}.")
	stop_markers = STOP_MARKERS_BY_LOCAL_SLOT[local_slot]
	unknown_markers = sorted(marker for marker in stop_markers if marker not in KNOWN_STOP_MARKERS)
	if unknown_markers:
		raise ValueError(f"Unknown stop markers emitted for {row.get('template_id', '')!r}: {unknown_markers}")
	return stop_markers


def derive_target_type(row: dict[str, object], family: str) -> str:
	if family == "status_only_anchor_detector":
		return "status_only"
	local_slot = str(row.get("local_slot", "")).strip()
	if local_slot == "00":
		return "claim_text"
	target_type = TARGET_TYPE_BY_LOCAL_SLOT.get(local_slot, "")
	if not target_type:
		raise ValueError(f"Target type cannot be derived for local_slot {local_slot!r}.")
	return target_type


def compile_operator_spec(row: dict[str, object]) -> OperatorSpec:
	missing = sorted(field for field in EXPANDED_INSTANCE_REQUIRED_FIELDS if not str(row.get(field, "")).strip())
	if missing:
		raise ValueError(f"Expanded instance row is missing required fields before compilation: {missing}; row={row!r}")
	if str(row.get("instance_status", "")).strip().lower() != "active":
		raise ValueError(f"Inactive instance row encountered during compilation: {row!r}")

	family = assign_family(row)
	anchor_patterns = derive_anchor_patterns(row, family)
	stop_markers = derive_stop_markers(row, family)
	target_type = derive_target_type(row, family)
	behavior = FAMILY_BEHAVIOR.get(family)
	if behavior is None:
		raise ValueError(f"No runtime behavior defaults found for family {family!r}.")
	allow_coordination = derive_allow_coordination(row, family)

	output_mode = str(row["output_mode"]).strip().lower()
	if family == "status_only_anchor_detector":
		if output_mode != "status_only":
			raise ValueError(f"Family {family!r} is incompatible with output_mode {output_mode!r}.")
	else:
		if output_mode != "span":
			raise ValueError(f"Family {family!r} is incompatible with output_mode {output_mode!r}.")

	return OperatorSpec(
		assessment_id=str(row["assessment_id"]),
		component_id=str(row["component_id"]),
		cid=str(row["cid"]),
		template_id=str(row["template_id"]),
		local_slot=str(row["local_slot"]),
		operator_id=str(row["operator_id"]),
		operator_identifier=str(row["operator_identifier"]),
		operator_identifier_shortid=str(row["operator_identifier_shortid"]),
		operator_short_description=str(row["operator_short_description"]),
		segment_id=str(row["segment_id"]),
		output_mode=output_mode,
		family=family,
		anchor_patterns=anchor_patterns,
		direction=str(behavior["direction"]),
		start_rule=str(behavior["start_rule"]),
		end_rule=str(behavior["end_rule"]),
		stop_markers=stop_markers,
		target_type=target_type,
		allow_coordination=allow_coordination,
		skip_later_candidates=bool(behavior["skip_later_candidates"]),
		operator_definition=str(row["operator_definition"]),
		operator_guidance=str(row["operator_guidance"]),
		failure_mode_guidance=str(row["failure_mode_guidance"]),
		decision_procedure=str(row["decision_procedure"]),
		missing_status="missing",
		ambiguous_status="ambiguous",
		malformed_status="malformed",
		instance_status=str(row["instance_status"]),
	)


def validate_operator_specs(specs: list[OperatorSpec]) -> None:
	if not specs:
		raise ValueError("No OperatorSpec objects were produced.")
	seen_operator_identifiers: set[str] = set()
	seen_component_operator_ids: set[tuple[str, str]] = set()
	for spec in specs:
		if spec.instance_status.lower() != "active":
			raise ValueError(f"Inactive OperatorSpec encountered: {spec}")
		if spec.operator_identifier in seen_operator_identifiers:
			raise ValueError(f"Duplicate operator_identifier in compiled specs: {spec.operator_identifier!r}")
		seen_operator_identifiers.add(spec.operator_identifier)
		component_operator_pair = (spec.component_id, spec.operator_id)
		if component_operator_pair in seen_component_operator_ids:
			raise ValueError(f"Duplicate operator_id within component_id detected: {component_operator_pair!r}")
		seen_component_operator_ids.add(component_operator_pair)
		unknown_markers = sorted(marker for marker in spec.stop_markers if marker not in KNOWN_STOP_MARKERS)
		if unknown_markers:
			raise ValueError(f"Unknown stop marker emitted for {spec.operator_identifier!r}: {unknown_markers}")


def compile_all_operator_specs(data: dict[str, object]) -> list[OperatorSpec]:
	expanded_instances = list(data.get("expanded_instances", []))
	compiled_specs = [compile_operator_spec(row) for row in expanded_instances]
	compiled_specs.sort(
		key=lambda spec: (
			component_sort_key(spec.component_id),
			spec.operator_id,
		)
	)
	validate_operator_specs(compiled_specs)
	return compiled_specs


def build_operator_specs_payload(expanded_payload: dict[str, object]) -> dict[str, object]:
	compiled_specs = compile_all_operator_specs(expanded_payload)
	return {
		"generated_at_utc": datetime.now(timezone.utc).isoformat(),
		"assessment_id": str(expanded_payload.get("assessment_id", "")),
		"source_registry_version": str(expanded_payload.get("source_registry_version", "")),
		"spec_version": "01",
		"operator_specs": [asdict(spec) for spec in compiled_specs],
	}


def resolve_output_paths(
	registry_path: Path,
	output_dir: Path | None,
	raw_output: Path | None,
	normalized_output: Path | None,
	expanded_output: Path | None,
	operator_specs_output: Path | None,
) -> tuple[Path, Path, Path, Path]:
	resolved_output_dir = output_dir.resolve() if output_dir else registry_path.parent.resolve()
	resolved_output_dir.mkdir(parents=True, exist_ok=True)
	base_stem = registry_path.stem
	resolved_raw_output = (raw_output or (resolved_output_dir / f"{base_stem}_raw_registry.json")).resolve()
	resolved_normalized_output = (
		normalized_output or (resolved_output_dir / f"{base_stem}_normalized_registry.json")
	).resolve()
	resolved_expanded_output = (
		expanded_output or (resolved_output_dir / f"{base_stem}_expanded_registry_instances.json")
	).resolve()
	resolved_operator_specs_output = (
		operator_specs_output or (resolved_output_dir / f"{base_stem}_operator_specs.json")
	).resolve()
	for path in [
		resolved_raw_output,
		resolved_normalized_output,
		resolved_expanded_output,
		resolved_operator_specs_output,
	]:
		path.parent.mkdir(parents=True, exist_ok=True)
	resolved_paths = {
		resolved_raw_output,
		resolved_normalized_output,
		resolved_expanded_output,
		resolved_operator_specs_output,
	}
	if len(resolved_paths) != 4:
		raise ValueError("Raw, normalized, expanded, and operator-spec outputs must resolve to different file paths.")
	return (
		resolved_raw_output,
		resolved_normalized_output,
		resolved_expanded_output,
		resolved_operator_specs_output,
	)


def build_raw_schema_payload(registry_path: Path, include_inactive: bool, registry_layer: str) -> dict[str, object]:
	lines = registry_path.read_text(encoding="utf-8").splitlines()
	sections = collect_markdown_sections(lines)
	tables = collect_markdown_tables(lines)

	registry_metadata_table = find_first_table_by_heading(tables, "registry metadata")
	identifier_rules_table = find_first_table_by_heading(tables, "identifier construction rules")
	reuse_rules_table = find_first_table_by_heading(tables, "reuse rule table")
	component_block_rules_table = find_first_table_by_heading(tables, "component block rule table")
	component_block_rules_table = normalize_component_block_rules_table(component_block_rules_table)

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


def resolve_step1_output_paths(
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


def main() -> int:
	args = parse_args()
	registry_path = args.registry_path.resolve()
	if not registry_path.exists():
		raise FileNotFoundError(f"Registry not found: {registry_path}")

	registry_layer = infer_registry_layer(registry_path, args.registry_layer)
	raw_payload = build_raw_schema_payload(
		registry_path=registry_path,
		include_inactive=args.include_inactive,
		registry_layer=registry_layer,
	)
	normalized_payload = build_normalized_registry_payload(raw_payload)
	raw_output_path, normalized_output_path = resolve_step1_output_paths(
		registry_path=registry_path,
		output_dir=args.output_dir,
		raw_output=args.raw_output,
		normalized_output=args.normalized_output,
	)
	write_json_output(raw_output_path, raw_payload)
	write_json_output(normalized_output_path, normalized_payload)

	print(f"Registry: {registry_path}")
	print(f"Registry layer: {registry_layer}")
	print(f"Raw registry output: {raw_output_path}")
	print(f"Normalized registry output: {normalized_output_path}")
	print(f"Reuse rules written: {len(raw_payload['reuse_rules'])}")
	print(f"Component block rules written: {len(raw_payload['component_block_rules'])}")
	print(f"Operator templates written: {len(normalized_payload['operator_templates'])}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())