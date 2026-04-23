#!/usr/bin/env python3
"""Generate deterministic Layer 1 indicator scoring modules from a Layer 1 manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from layer1_indicator_scoring_runtime import (
	SUPPORTED_BOUND_SEGMENT_RESOLUTION_POLICIES,
	SUPPORTED_DECISION_RULES,
	normalize_decision_rule_name,
)


MANIFEST_REQUIRED_HEADERS = [
	"component_id",
	"sbo_identifier",
	"indicator_id",
	"sbo_short_description",
	"indicator_definition",
	"assessment_guidance",
	"evaluation_notes",
	"decision_procedure",
	"indicator_scoring_payload_json",
]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate deterministic Layer 1 indicator scoring modules from a Layer 1 scoring manifest."
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
	raise ValueError("Layer 1 scoring manifest table was not found.")


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
	indicator_ids = [row.get("indicator_id", "").strip() for row in filtered_rows]
	if any(not indicator_id for indicator_id in indicator_ids):
		raise ValueError("Filtered manifest rows must contain non-empty indicator_id values.")
	if len(set(indicator_ids)) != len(indicator_ids):
		raise ValueError("Duplicate indicator_id values detected within filtered manifest rows.")
	return filtered_rows


def parse_scoring_payload(payload_json: str) -> dict[str, object]:
	if not payload_json.strip():
		raise ValueError("Layer 1 manifest row is missing indicator_scoring_payload_json.")
	payload = json.loads(payload_json)
	for required_key in [
		"scoring_mode",
		"dependency_type",
		"bound_segment_id",
		"normalisation_rule",
		"match_policy",
		"decision_rule",
	]:
		if required_key not in payload:
			raise ValueError(f"Layer 1 scoring payload is missing required key: {required_key}")
	decision_rule = normalize_decision_rule_name(str(payload.get("decision_rule", "") or "").strip())
	if decision_rule not in SUPPORTED_DECISION_RULES:
		raise ValueError(f"Unsupported Layer 1 decision_rule: {decision_rule}")
	payload["decision_rule"] = decision_rule
	bound_segment_resolution_policy = str(payload.get("bound_segment_resolution_policy", "") or "").strip()
	if not bound_segment_resolution_policy:
		bound_segment_resolution_policy = "hard_stay"
	if bound_segment_resolution_policy not in SUPPORTED_BOUND_SEGMENT_RESOLUTION_POLICIES:
		raise ValueError(
			f"Unsupported Layer 1 bound_segment_resolution_policy: {bound_segment_resolution_policy}"
		)
	payload["bound_segment_resolution_policy"] = bound_segment_resolution_policy
	return payload


def resolve_output_path(output_dir: Path, output_file_stem: str, output_format: str, indicator_id: str) -> Path:
	return output_dir / f"{output_file_stem}_{indicator_id}.{output_format.lstrip('.')}"


def derive_version_family_prefix(output_file_stem: str) -> str:
	match = re.match(r"^(.*)_v\d+$", output_file_stem)
	if match is None:
		return output_file_stem
	return match.group(1)


def remove_stale_generated_modules(output_dir: Path, output_file_stem: str, output_format: str) -> None:
	extension = output_format.lstrip('.')
	family_prefix = derive_version_family_prefix(output_file_stem)
	for existing_path in output_dir.glob(f"{family_prefix}_v*.{extension}"):
		if existing_path.is_file():
			existing_path.unlink()


def build_module_source(row: dict[str, str], payload: dict[str, object]) -> str:
	docstring = (
		f'"""Deterministic Layer 1 scorer for {row["indicator_id"]} ({row["component_id"]}).\n\n'
		f'{row.get("indicator_definition", "").strip()}\n"""'
	)
	payload_json = json.dumps(payload, ensure_ascii=True, indent=4, sort_keys=True)
	return "\n".join(
		[
			"#!/usr/bin/env python3",
			docstring,
			"",
			"from __future__ import annotations",
			"",
			"from typing import Mapping",
			"",
			"from layer1_indicator_scoring_runtime import score_indicator_from_row",
			"",
			f"COMPONENT_ID = {row['component_id']!r}",
			f"INDICATOR_ID = {row['indicator_id']!r}",
			f"SBO_IDENTIFIER = {row['sbo_identifier']!r}",
			f"SBO_SHORT_DESCRIPTION = {row['sbo_short_description']!r}",
			f"INDICATOR_DEFINITION = {row['indicator_definition']!r}",
			f"ASSESSMENT_GUIDANCE = {row['assessment_guidance']!r}",
			f"EVALUATION_NOTES = {row.get('evaluation_notes', '')!r}",
			f"DECISION_PROCEDURE = {row.get('decision_procedure', '')!r}",
			f"SCORING_PAYLOAD = {payload_json}",
			"",
			"def score_indicator_row(row: Mapping[str, object]) -> dict[str, str]:",
			"\treturn score_indicator_from_row(",
			"\t\trow,",
			"\t\tcomponent_id=COMPONENT_ID,",
			"\t\tindicator_id=INDICATOR_ID,",
			"\t\tpayload=SCORING_PAYLOAD,",
			"\t\tdefault_evaluation_notes=EVALUATION_NOTES,",
			"\t)",
			"",
			"__all__ = [",
			"\t'COMPONENT_ID',",
			"\t'INDICATOR_ID',",
			"\t'SBO_IDENTIFIER',",
			"\t'SBO_SHORT_DESCRIPTION',",
			"\t'INDICATOR_DEFINITION',",
			"\t'ASSESSMENT_GUIDANCE',",
			"\t'EVALUATION_NOTES',",
			"\t'DECISION_PROCEDURE',",
			"\t'SCORING_PAYLOAD',",
			"\t'score_indicator_row',",
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
		remove_stale_generated_modules(output_dir, args.output_file_stem, args.output_format)
		output_paths: list[Path] = []
		for row in filtered_rows:
			indicator_id = row["indicator_id"].strip()
			payload = parse_scoring_payload(row["indicator_scoring_payload_json"])
			output_path = resolve_output_path(output_dir, args.output_file_stem, args.output_format, indicator_id)
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