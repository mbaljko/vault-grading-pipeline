#!/usr/bin/env python3
"""Generate deterministic Layer 3 component scoring modules from a Layer 3 scoring manifest.

This script reads a Layer 3 scoring manifest, filters it to one component, and
writes one Python module per component row. Each generated module implements
the component-scoring logic deterministically over a set of Layer 2 dimension
values, without invoking an LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


MANIFEST_REQUIRED_HEADERS = [
	"component_id",
	"sbo_identifier",
	"sbo_short_description",
	"component_definition",
	"component_performance_scale",
	"component_scoring_payload_json",
]
KNOWN_COMPONENT_PERFORMANCE_ORDER = {
	"not_demonstrated": 0,
	"below_expectations": 1,
	"approaching_expectations": 2,
	"meets_expectations": 3,
	"exceeds_expectations": 4,
}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate deterministic Layer 3 component scoring modules from a Layer 3 scoring manifest."
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
	raise ValueError("Layer 3 scoring manifest table was not found.")


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
	return filtered_rows


def parse_scoring_payload(
	payload_json: str,
	*,
	manifest_path: Path,
	component_id: str,
	sbo_identifier: str,
) -> dict[str, object]:
	if not payload_json.strip():
		raise ValueError(
			"Layer 3 manifest row is missing component_scoring_payload_json. "
			f"Checked manifest={manifest_path}, component_id={component_id!r}, sbo_identifier={sbo_identifier!r}."
		)
	payload = json.loads(payload_json)
	for required_key in ["component_id", "input_dimension_tokens", "bound_dimension_ids", "derivation_rules"]:
		if required_key not in payload:
			raise ValueError(f"Layer 3 scoring payload is missing required key: {required_key}")
	input_dimension_tokens = payload["input_dimension_tokens"]
	bound_dimension_ids = payload["bound_dimension_ids"]
	if not isinstance(input_dimension_tokens, list) or not isinstance(bound_dimension_ids, list):
		raise ValueError("Layer 3 scoring payload dimension tokens and bound dimension IDs must be lists.")
	if len(input_dimension_tokens) != len(bound_dimension_ids):
		raise ValueError("Layer 3 scoring payload dimension token count must match bound dimension ID count.")
	return payload


def resolve_output_path(output_dir: Path, output_file_stem: str, output_format: str) -> Path:
	return output_dir / f"{output_file_stem}.{output_format.lstrip('.')}"


def parse_component_performance_scale(raw_value: str) -> list[str]:
	values = []
	for part in raw_value.split(","):
		normalized = normalize_markdown_cell(part).strip().strip("`")
		if normalized:
			values.append(normalized)
	if values and all(value in KNOWN_COMPONENT_PERFORMANCE_ORDER for value in values):
		return sorted(values, key=lambda value: KNOWN_COMPONENT_PERFORMANCE_ORDER[value])
	return values


def build_module_source(row: dict[str, str], payload: dict[str, object]) -> str:
	bound_dimension_ids = [str(dimension_id) for dimension_id in payload["bound_dimension_ids"]]
	component_performance_scale = parse_component_performance_scale(row.get("component_performance_scale", ""))
	dimension_tokens = [str(token) for token in payload["input_dimension_tokens"]]
	derivation_rules = [dict(rule) for rule in payload["derivation_rules"]]
	concrete_rules = []
	for rule in derivation_rules:
		conditions = {}
		for token, dimension_id in zip(dimension_tokens, bound_dimension_ids):
			conditions[dimension_id] = str(rule.get("conditions", {}).get(token, "")).strip()
		concrete_rules.append(
			{
				"resultant_scale_value": str(rule.get("resultant_scale_value", "")).strip(),
				"conditions": conditions,
			}
		)

	docstring = (
		f'"""Deterministic Layer 3 scorer for {row["component_id"]}.\n\n'
		f'{row.get("component_definition", "").strip()}\n"""'
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
			f"SBO_IDENTIFIER = {row['sbo_identifier']!r}",
			f"SBO_SHORT_DESCRIPTION = {row['sbo_short_description']!r}",
			f"COMPONENT_PERFORMANCE_SCALE = {component_performance_scale!r}",
			f"BOUND_DIMENSION_IDS = {bound_dimension_ids!r}",
			f"DERIVATION_RULES = {json.dumps(concrete_rules, ensure_ascii=True, indent=4)}",
			"",
			"def normalize_dimension_value(value: object) -> str:",
			"\treturn str(value or '').strip().lower()",
			"",
			"def condition_is_met(observed_value: str, expected_value: str, ordinal_lookup: Mapping[str, int] | None = None) -> bool:",
			"\texpected = normalize_dimension_value(expected_value)",
			"\tif expected in {'', '*'}:",
			"\t\treturn True",
			"\tobserved = normalize_dimension_value(observed_value)",
			"\tif ordinal_lookup:",
			"\t\tobserved_rank = ordinal_lookup.get(observed)",
			"\t\texpected_rank = ordinal_lookup.get(expected)",
			"\t\tif observed_rank is not None and expected_rank is not None:",
			"\t\t\treturn observed_rank >= expected_rank",
			"\treturn observed == expected",
			"",
			"def rule_matches(dimension_values: Mapping[str, str], rule: Mapping[str, object], dimension_scale_lookup: Mapping[str, Mapping[str, int]] | None = None) -> bool:",
			"\tconditions = rule.get('conditions', {})",
			"\tif not isinstance(conditions, Mapping):",
			"\t\traise ValueError('Rule conditions must be a mapping.')",
			"\tfor dimension_id, expected_value in conditions.items():",
			"\t\tordinal_lookup = dimension_scale_lookup.get(str(dimension_id), {}) if dimension_scale_lookup else {}",
			"\t\tobserved = normalize_dimension_value(dimension_values.get(str(dimension_id), ''))",
			"\t\tif not condition_is_met(observed, str(expected_value), ordinal_lookup):",
			"\t\t\treturn False",
			"\treturn True",
			"",
			"def score_component(dimension_values: Mapping[str, str], dimension_scale_lookup: Mapping[str, Mapping[str, int]] | None = None) -> str:",
			"\tfor rule in DERIVATION_RULES:",
			"\t\tif rule_matches(dimension_values, rule, dimension_scale_lookup=dimension_scale_lookup):",
			"\t\t\treturn str(rule['resultant_scale_value'])",
			"\traise ValueError(f'No derivation rule matched for {COMPONENT_ID}.')",
			"",
			"def build_dimension_value_map(rows: Iterable[Mapping[str, object]], dimension_id_field: str = 'dimension_id', value_field: str = 'evidence_status') -> dict[str, str]:",
			"\tdimension_values: dict[str, str] = {}",
			"\tfor row in rows:",
			"\t\tdimension_id = str(row.get(dimension_id_field, '')).strip()",
			"\t\tif not dimension_id:",
			"\t\t\tcontinue",
			"\t\tdimension_values[dimension_id] = normalize_dimension_value(row.get(value_field, ''))",
			"\treturn dimension_values",
			"",
			"def score_component_rows(rows: Iterable[Mapping[str, object]], dimension_id_field: str = 'dimension_id', value_field: str = 'evidence_status', dimension_scale_lookup: Mapping[str, Mapping[str, int]] | None = None) -> str:",
			"\treturn score_component(",
			"\t\tbuild_dimension_value_map(rows, dimension_id_field=dimension_id_field, value_field=value_field),",
			"\t\tdimension_scale_lookup=dimension_scale_lookup,",
			"\t)",
			"",
			"__all__ = [",
			"\t'ASSESSMENT_ID',",
			"\t'COMPONENT_ID',",
			"\t'SBO_IDENTIFIER',",
			"\t'SBO_SHORT_DESCRIPTION',",
			"\t'COMPONENT_PERFORMANCE_SCALE',",
			"\t'BOUND_DIMENSION_IDS',",
			"\t'DERIVATION_RULES',",
			"\t'build_dimension_value_map',",
			"\t'condition_is_met',",
			"\t'rule_matches',",
			"\t'score_component',",
			"\t'score_component_rows',",
			"]",
			"",
		]
	)


def main() -> int:
	args = parse_args()
	try:
		manifest_path = args.manifest_file.resolve()
		manifest_text = read_text_file(manifest_path)
		manifest_rows = parse_manifest_rows(manifest_text)
		filtered_rows = filter_manifest_rows(manifest_rows, args.target_component_id)
		if len(filtered_rows) != 1:
			raise ValueError("Layer 3 module generation expects exactly one manifest row per component.")
		row = filtered_rows[0]
		payload = parse_scoring_payload(
			row["component_scoring_payload_json"],
			manifest_path=manifest_path,
			component_id=str(row.get("component_id", "") or "").strip(),
			sbo_identifier=str(row.get("sbo_identifier", "") or "").strip(),
		)
		output_dir = args.output_dir.resolve()
		output_dir.mkdir(parents=True, exist_ok=True)
		output_path = resolve_output_path(output_dir, args.output_file_stem, args.output_format)
		output_text = build_module_source(row, payload)
		output_path.write_text(output_text, encoding="utf-8")
	except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	print(output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())