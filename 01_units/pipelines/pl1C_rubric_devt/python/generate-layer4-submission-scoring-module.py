#!/usr/bin/env python3
"""Generate a deterministic Layer 4 submission scoring module from a Layer 4 manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


MANIFEST_REQUIRED_HEADERS = [
	"sbo_identifier",
	"sbo_short_description",
	"submission_definition",
	"submission_performance_scale",
	"submission_scoring_payload_json",
]
KNOWN_SUBMISSION_PERFORMANCE_ORDER = {
	"not_demonstrated": 0,
	"below_expectations": 1,
	"approaching_expectations": 2,
	"meets_expectations": 3,
	"exceeds_expectations": 4,
}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate a deterministic Layer 4 submission scoring module from a Layer 4 manifest."
	)
	parser.add_argument("--manifest-file", type=Path, required=True)
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
	raise ValueError("Layer 4 scoring manifest table was not found.")


def parse_manifest_rows(manifest_text: str) -> list[dict[str, str]]:
	headers, row_lines = find_manifest_table_lines(manifest_text)
	rows: list[dict[str, str]] = []
	for row_line in row_lines:
		cells = parse_markdown_cells(row_line)
		if len(cells) != len(headers):
			raise ValueError("Manifest row does not match expected column count.")
		rows.append({headers[index]: cells[index].strip() for index in range(len(headers))})
	return rows


def parse_scoring_payload(payload_json: str) -> dict[str, object]:
	if not payload_json.strip():
		raise ValueError("Layer 4 manifest row is missing submission_scoring_payload_json.")
	payload = json.loads(payload_json)
	for required_key in [
		"assessment_id",
		"input_component_tokens",
		"component_bindings",
		"bound_component_ids",
		"component_value_map",
		"numeric_cutpoints",
	]:
		if required_key not in payload:
			raise ValueError(f"Layer 4 scoring payload is missing required key: {required_key}")
	return payload


def resolve_output_path(output_dir: Path, output_file_stem: str, output_format: str) -> Path:
	return output_dir / f"{output_file_stem}.{output_format.lstrip('.')}"


def parse_submission_performance_scale(raw_value: str) -> list[str]:
	values = []
	for part in raw_value.split(","):
		normalized = normalize_markdown_cell(part).strip().strip("`")
		if normalized:
			values.append(normalized)
	if values and all(value in KNOWN_SUBMISSION_PERFORMANCE_ORDER for value in values):
		return sorted(values, key=lambda value: KNOWN_SUBMISSION_PERFORMANCE_ORDER[value])
	return values


def build_module_source(row: dict[str, str], payload: dict[str, object]) -> str:
	assessment_id = str(payload["assessment_id"])
	input_component_tokens = [str(token) for token in payload["input_component_tokens"]]
	component_bindings = {str(key): str(value) for key, value in dict(payload["component_bindings"]).items()}
	bound_component_ids = [str(component_id) for component_id in payload["bound_component_ids"]]
	component_value_map = {
		str(key): float(value)
		for key, value in dict(payload["component_value_map"]).items()
	}
	numeric_cutpoints = [dict(cutpoint) for cutpoint in payload["numeric_cutpoints"]]
	submission_performance_scale = parse_submission_performance_scale(row.get("submission_performance_scale", ""))

	docstring = (
		f'"""Deterministic Layer 4 scorer for {assessment_id}.\n\n'
		f'{row.get("submission_definition", "").strip()}\n"""'
	)
	return "\n".join(
		[
			"#!/usr/bin/env python3",
			docstring,
			"",
			"from __future__ import annotations",
			"",
			"from typing import Mapping",
			"",
			f"ASSESSMENT_ID = {assessment_id!r}",
			f"SBO_IDENTIFIER = {row['sbo_identifier']!r}",
			f"SBO_SHORT_DESCRIPTION = {row['sbo_short_description']!r}",
			f"SUBMISSION_PERFORMANCE_SCALE = {submission_performance_scale!r}",
			f"INPUT_COMPONENT_TOKENS = {input_component_tokens!r}",
			f"COMPONENT_BINDINGS = {json.dumps(component_bindings, ensure_ascii=True, indent=4, sort_keys=True)}",
			f"BOUND_COMPONENT_IDS = {bound_component_ids!r}",
			f"COMPONENT_VALUE_MAP = {json.dumps(component_value_map, ensure_ascii=True, indent=4, sort_keys=True)}",
			f"NUMERIC_CUTPOINTS = {json.dumps(numeric_cutpoints, ensure_ascii=True, indent=4)}",
			"",
			"def normalize_scale_value(value: object) -> str:",
			"\tnormalized = str(value or '').strip().lower()",
			"\treturn '_'.join(part for part in normalized.replace('-', ' ').split() if part)",
			"",
			"def resolve_component_numeric_values(component_scores: Mapping[str, str]) -> dict[str, float]:",
			"\tnumeric_values: dict[str, float] = {}",
			"\tfor component_id in BOUND_COMPONENT_IDS:",
			"\t\traw_score = component_scores.get(component_id, '')",
			"\t\tnormalized_score = normalize_scale_value(raw_score)",
			"\t\tif not normalized_score:",
			"\t\t\traise ValueError(f'Missing Layer 3 component score for {component_id}.')",
			"\t\tif normalized_score not in COMPONENT_VALUE_MAP:",
			"\t\t\traise ValueError(f'Unsupported Layer 3 component score {raw_score!r} for {component_id}.')",
			"\t\tnumeric_values[component_id] = float(COMPONENT_VALUE_MAP[normalized_score])",
			"\treturn numeric_values",
			"",
			"def score_submission(component_scores: Mapping[str, str]) -> dict[str, object]:",
			"\tnumeric_values = resolve_component_numeric_values(component_scores)",
			"\tsubmission_numeric_score = sum(numeric_values.values())",
			"\tfor cutpoint in NUMERIC_CUTPOINTS:",
			"\t\tnumeric_minimum = float(cutpoint['numeric_minimum'])",
			"\t\tnumeric_maximum = float(cutpoint['numeric_maximum'])",
			"\t\tif numeric_minimum - 1e-9 <= submission_numeric_score <= numeric_maximum + 1e-9:",
			"\t\t\treturn {",
			"\t\t\t\t'submission_numeric_score': submission_numeric_score,",
			"\t\t\t\t'submission_score': str(cutpoint['resultant_scale_value']),",
			"\t\t\t\t'source_component_numeric_values': numeric_values,",
			"\t\t\t}",
			"\traise ValueError(f'No Layer 4 cutpoint matched numeric score {submission_numeric_score:.4f}.')",
			"",
			"__all__ = [",
			"\t'ASSESSMENT_ID',",
			"\t'SBO_IDENTIFIER',",
			"\t'SBO_SHORT_DESCRIPTION',",
			"\t'SUBMISSION_PERFORMANCE_SCALE',",
			"\t'INPUT_COMPONENT_TOKENS',",
			"\t'COMPONENT_BINDINGS',",
			"\t'BOUND_COMPONENT_IDS',",
			"\t'COMPONENT_VALUE_MAP',",
			"\t'NUMERIC_CUTPOINTS',",
			"\t'normalize_scale_value',",
			"\t'resolve_component_numeric_values',",
			"\t'score_submission',",
			"]",
			"",
		]
	)


def main() -> int:
	args = parse_args()
	try:
		manifest_text = read_text_file(args.manifest_file.resolve())
		manifest_rows = parse_manifest_rows(manifest_text)
		if len(manifest_rows) != 1:
			raise ValueError("Layer 4 module generation expects exactly one manifest row.")
		row = manifest_rows[0]
		payload = parse_scoring_payload(row["submission_scoring_payload_json"])
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