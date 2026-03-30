#!/usr/bin/env python3
"""Generate deterministic Layer 2 dimension scoring modules from a Layer 2 scoring manifest.

This script reads a Layer 2 scoring manifest, filters it to one component, and
writes one Python module per dimension row. Each generated module implements the
dimension-scoring logic deterministically over a set of Layer 1 indicator
values, without invoking an LLM.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MANIFEST_REQUIRED_HEADERS = [
	"component_id",
	"sbo_identifier",
	"dimension_id",
	"sbo_short_description",
	"dimension_definition",
	"dimension_template_id",
	"dimension_evidence_scale",
	"dimension_scoring_payload_json",
]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate deterministic Layer 2 dimension scoring modules from a Layer 2 scoring manifest."
	)
	parser.add_argument("--manifest-file", type=Path, required=True)
	parser.add_argument("--target-component-id", type=str, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--output-file-stem", type=str, required=True)
	parser.add_argument("--output-format", type=str, default="py")
	return parser.parse_args()


def read_text_file(path: Path) -> str:
	if not path.exists() or not path.is_file():
		raise FileNotFoundError(f"File not found: {path}")
	return path.read_text(encoding="utf-8")


def normalize_markdown_cell(value: str) -> str:
	normalized = value.strip()
	if len(normalized) >= 2 and normalized.startswith("`") and normalized.endswith("`"):
		return normalized[1:-1].strip()
	return normalized


def parse_markdown_cells(line: str) -> list[str]:
	parts = [part.strip() for part in line.strip().split("|")]
	if parts and parts[0] == "":
		parts = parts[1:]
	if parts and parts[-1] == "":
		parts = parts[:-1]
	return [normalize_markdown_cell(part) for part in parts]


def manifest_headers_are_supported(headers: list[str]) -> bool:
	return all(required_header in headers for required_header in MANIFEST_REQUIRED_HEADERS)


def find_manifest_table_lines(manifest_text: str) -> tuple[list[str], list[str]]:
	lines = manifest_text.splitlines()
	for index, line in enumerate(lines[:-1]):
		headers = parse_markdown_cells(line)
		if not manifest_headers_are_supported(headers):
			continue
		separator = parse_markdown_cells(lines[index + 1])
		if not separator or not all(set(cell.replace(" ", "")) <= {"-", ":"} for cell in separator):
			continue
		row_lines: list[str] = []
		cursor = index + 2
		while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
			row_lines.append(lines[cursor])
			cursor += 1
		return (headers, row_lines)
	raise ValueError("Layer 2 scoring manifest table was not found.")


def parse_manifest_rows(manifest_text: str) -> list[dict[str, str]]:
	headers, row_lines = find_manifest_table_lines(manifest_text)
	rows: list[dict[str, str]] = []
	for row_line in row_lines:
		cells = parse_markdown_cells(row_line)
		if len(cells) != len(headers):
			raise ValueError("Manifest row does not match expected column count.")
		rows.append({headers[index]: cells[index].strip() for index in range(len(headers))})
	return rows


def filter_manifest_rows(rows: list[dict[str, str]], target_component_id: str) -> list[dict[str, str]]:
	filtered_rows = [row for row in rows if row.get("component_id", "").strip() == target_component_id]
	if not filtered_rows:
		raise ValueError("Filtered manifest is empty for target component_id.")
	dimension_ids = [row.get("dimension_id", "").strip() for row in filtered_rows]
	if any(not dimension_id for dimension_id in dimension_ids):
		raise ValueError("Filtered manifest rows must contain non-empty dimension_id values.")
	if len(set(dimension_ids)) != len(dimension_ids):
		raise ValueError("Duplicate dimension_id values detected within filtered manifest rows.")
	return filtered_rows


def parse_scoring_payload(payload_json: str) -> dict[str, object]:
	if not payload_json.strip():
		raise ValueError("Layer 2 manifest row is missing dimension_scoring_payload_json.")
	payload = json.loads(payload_json)
	for required_key in ["dimension_template_id", "input_indicator_tokens", "bound_indicator_ids", "derivation_rules"]:
		if required_key not in payload:
			raise ValueError(f"Layer 2 scoring payload is missing required key: {required_key}")
	input_indicator_tokens = payload["input_indicator_tokens"]
	bound_indicator_ids = payload["bound_indicator_ids"]
	if not isinstance(input_indicator_tokens, list) or not isinstance(bound_indicator_ids, list):
		raise ValueError("Layer 2 scoring payload indicator tokens and bound indicator IDs must be lists.")
	if len(input_indicator_tokens) != len(bound_indicator_ids):
		raise ValueError("Layer 2 scoring payload indicator token count must match bound indicator ID count.")
	return payload


def resolve_output_path(output_dir: Path, output_file_stem: str, output_format: str, dimension_id: str) -> Path:
	return output_dir / f"{output_file_stem}_{dimension_id}.{output_format.lstrip('.')}"


def parse_dimension_evidence_scale(raw_value: str) -> list[str]:
	return [part.strip() for part in raw_value.split(",") if part.strip()]


def build_module_source(row: dict[str, str], payload: dict[str, object]) -> str:
	bound_indicator_ids = [str(indicator_id) for indicator_id in payload["bound_indicator_ids"]]
	dimension_evidence_scale = parse_dimension_evidence_scale(row.get("dimension_evidence_scale", ""))
	indicator_tokens = [str(token) for token in payload["input_indicator_tokens"]]
	derivation_rules = [dict(rule) for rule in payload["derivation_rules"]]
	concrete_rules = []
	for rule in derivation_rules:
		conditions = {}
		for token, indicator_id in zip(indicator_tokens, bound_indicator_ids):
			conditions[indicator_id] = str(rule.get("conditions", {}).get(token, "")).strip()
		concrete_rules.append(
			{
				"resultant_scale_value": str(rule.get("resultant_scale_value", "")).strip(),
				"conditions": conditions,
			}
		)

	docstring = (
		f'"""Deterministic Layer 2 scorer for {row["dimension_id"]} ({row["component_id"]}).\n\n'
		f'{row.get("dimension_definition", "").strip()}\n"""'
	)
	return "\n".join(
		[
			"#!/usr/bin/env python3",
			docstring,
			"",
			"from __future__ import annotations",
			"",
			"from typing import Iterable, Mapping",
			"",
			f"ASSESSMENT_ID = {row['sbo_identifier'].split('_')[1]!r}",
			f"COMPONENT_ID = {row['component_id']!r}",
			f"DIMENSION_ID = {row['dimension_id']!r}",
			f"DIMENSION_TEMPLATE_ID = {row['dimension_template_id']!r}",
			f"SBO_IDENTIFIER = {row['sbo_identifier']!r}",
			f"SBO_SHORT_DESCRIPTION = {row['sbo_short_description']!r}",
			f"DIMENSION_EVIDENCE_SCALE = {dimension_evidence_scale!r}",
			f"BOUND_INDICATOR_IDS = {bound_indicator_ids!r}",
			f"DERIVATION_RULES = {json.dumps(concrete_rules, ensure_ascii=True, indent=4)}",
			"",
			"def normalize_indicator_value(value: object) -> str:",
			"\treturn str(value or '').strip().lower()",
			"",
			"def rule_matches(indicator_values: Mapping[str, str], rule: Mapping[str, object]) -> bool:",
			"\tconditions = rule.get('conditions', {})",
			"\tif not isinstance(conditions, Mapping):",
			"\t\traise ValueError('Rule conditions must be a mapping.')",
			"\tfor indicator_id, expected_value in conditions.items():",
			"\t\texpected = normalize_indicator_value(expected_value)",
			"\t\tif expected in {'', '*'}:",
			"\t\t\tcontinue",
			"\t\tobserved = normalize_indicator_value(indicator_values.get(str(indicator_id), ''))",
			"\t\tif observed != expected:",
			"\t\t\treturn False",
			"\treturn True",
			"",
			"def score_dimension(indicator_values: Mapping[str, str]) -> str:",
			"\tfor rule in DERIVATION_RULES:",
			"\t\tif rule_matches(indicator_values, rule):",
			"\t\t\treturn str(rule['resultant_scale_value'])",
			"\traise ValueError(f'No derivation rule matched for {DIMENSION_ID}.')",
			"",
			"def build_indicator_value_map(rows: Iterable[Mapping[str, object]], indicator_id_field: str = 'indicator_id', value_field: str = 'evidence_status') -> dict[str, str]:",
			"\tindicator_values: dict[str, str] = {}",
			"\tfor row in rows:",
			"\t\tindicator_id = str(row.get(indicator_id_field, '')).strip()",
			"\t\tif not indicator_id:",
			"\t\t\tcontinue",
			"\t\tindicator_values[indicator_id] = normalize_indicator_value(row.get(value_field, ''))",
			"\treturn indicator_values",
			"",
			"def score_dimension_rows(rows: Iterable[Mapping[str, object]], indicator_id_field: str = 'indicator_id', value_field: str = 'evidence_status') -> str:",
			"\treturn score_dimension(build_indicator_value_map(rows, indicator_id_field=indicator_id_field, value_field=value_field))",
			"",
			"__all__ = [",
			"\t'ASSESSMENT_ID',",
			"\t'COMPONENT_ID',",
			"\t'DIMENSION_ID',",
			"\t'DIMENSION_TEMPLATE_ID',",
			"\t'SBO_IDENTIFIER',",
			"\t'SBO_SHORT_DESCRIPTION',",
			"\t'DIMENSION_EVIDENCE_SCALE',",
			"\t'BOUND_INDICATOR_IDS',",
			"\t'DERIVATION_RULES',",
			"\t'build_indicator_value_map',",
			"\t'rule_matches',",
			"\t'score_dimension',",
			"\t'score_dimension_rows',",
			"]",
			"",
		]
	)


def main() -> int:
	args = parse_args()
	try:
		manifest_text = read_text_file(args.manifest_file.resolve())
		manifest_rows = parse_manifest_rows(manifest_text)
		filtered_rows = filter_manifest_rows(manifest_rows, args.target_component_id)
		output_dir = args.output_dir.resolve()
		output_dir.mkdir(parents=True, exist_ok=True)
		output_paths: list[Path] = []
		for row in filtered_rows:
			dimension_id = row["dimension_id"].strip()
			payload = parse_scoring_payload(row["dimension_scoring_payload_json"])
			output_path = resolve_output_path(output_dir, args.output_file_stem, args.output_format, dimension_id)
			output_text = build_module_source(row, payload)
			output_path.write_text(output_text, encoding="utf-8")
			output_paths.append(output_path)
	except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	for output_path in output_paths:
		print(output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())