#!/usr/bin/env python3
"""Deterministically render [[EMBEDDED_INDICATOR_TABLE_ROWS]] from runner-style inputs.

This script accepts the same core file inputs as the prompt runner:
- --prompt-instructions-file
- --prompt-input-file
- --output-dir
- --output-file-stem
- --output-format

It validates the three-block payload grammar, extracts PARAM_TARGET_COMPONENT_ID,
filters the Layer 1 scoring manifest to that component, and writes only the
rendered embedded indicator table body rows to the output file.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PAYLOAD_DELIMITER = "§§§"
EMBEDDED_ROWS_TOKEN = "[[EMBEDDED_INDICATOR_TABLE_ROWS]]"
PARAMETER_RE = re.compile(r"^PARAM_TARGET_COMPONENT_ID\s*=\s*(\S.*?)\s*$")
FENCED_VALUE_TEMPLATE = r"(?ms)^{}\s*$\n```(?:text)?\n(.*?)\n```"
MANIFEST_HEADERS = [
	"component_id",
	"sbo_identifier",
	"indicator_id",
	"sbo_short_description",
	"indicator_definition",
	"assessment_guidance",
	"evaluation_notes",
]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Render deterministic embedded indicator table rows from a runner-style prompt payload."
	)
	parser.add_argument("--prompt-instructions-file", type=Path, required=True)
	parser.add_argument("--prompt-input-file", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--output-file-stem", type=str, required=True)
	parser.add_argument("--output-format", type=str, default="md")
	parser.add_argument("--timeout-seconds", type=int, default=600)
	parser.add_argument("--temperature", type=float, default=0.0)
	parser.add_argument("--top-p", type=float, default=1.0)
	return parser.parse_args()


def read_text_file(path: Path) -> str:
	if not path.exists() or not path.is_file():
		raise FileNotFoundError(f"File not found: {path}")
	return path.read_text(encoding="utf-8")


def resolve_output_path(output_dir: Path, output_file_stem: str, output_format: str) -> Path:
	return output_dir / f"{output_file_stem}.{output_format.lstrip('.')}"


def split_payload_blocks(payload_text: str) -> tuple[str, str, str]:
	lines = payload_text.splitlines()
	if not lines:
		raise ValueError("Prompt input payload is empty.")
	delimiter_indexes = [index for index, line in enumerate(lines) if line.strip() == PAYLOAD_DELIMITER]
	if len(delimiter_indexes) != 3:
		raise ValueError("Prompt input payload must contain exactly three delimiter lines.")
	if delimiter_indexes[0] != 0:
		raise ValueError("No text may appear before the first delimiter.")
	if lines[-1].strip() == PAYLOAD_DELIMITER:
		raise ValueError("No additional delimiter may appear after the manifest block.")
	parameter_block = "\n".join(lines[delimiter_indexes[0] + 1 : delimiter_indexes[1]]).strip("\n")
	assignment_payload_block = "\n".join(lines[delimiter_indexes[1] + 1 : delimiter_indexes[2]]).strip("\n")
	manifest_block = "\n".join(lines[delimiter_indexes[2] + 1 :]).strip("\n")
	if not parameter_block or not assignment_payload_block or not manifest_block:
		raise ValueError("Prompt input payload must contain exactly three non-empty blocks.")
	return (parameter_block, assignment_payload_block, manifest_block)


def parse_target_component_id(parameter_block: str) -> str:
	non_empty_lines = [line.strip() for line in parameter_block.splitlines() if line.strip()]
	if len(non_empty_lines) != 1:
		raise ValueError("Parameter block must contain exactly one non-empty line.")
	match = PARAMETER_RE.fullmatch(non_empty_lines[0])
	if not match:
		raise ValueError("Parameter block must match 'PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>'.")
	return match.group(1).strip()


def extract_single_fenced_value(text: str, label: str) -> str:
	pattern = re.compile(FENCED_VALUE_TEMPLATE.format(re.escape(label)))
	match = pattern.search(text)
	if match is None:
		raise ValueError(f"Required fenced value not found for label: {label}")
	return match.group(1).strip()


def validate_assignment_payload_block(assignment_payload_block: str) -> None:
	if "AssignmentPayloadSpec" not in assignment_payload_block:
		raise ValueError("Assignment payload block does not look like an AssignmentPayloadSpec artefact.")
	assessment_id = extract_single_fenced_value(assignment_payload_block, "assessment_id") if "assessment_id\n```" in assignment_payload_block else None
	if assessment_id is None:
		if "assessment_id" not in assignment_payload_block:
			raise ValueError("Assignment payload block is missing assessment_id.")
	_ = extract_single_fenced_value(assignment_payload_block, "canonical_submission_level_identifier_field")
	response_field_name = extract_single_fenced_value(assignment_payload_block, "response_field_name")
	if response_field_name != "response_text":
		raise ValueError("Assignment payload block must declare response_field_name as response_text.")
	for required_token in ["component_id", "response_text"]:
		if required_token not in assignment_payload_block:
			raise ValueError(f"Assignment payload block is missing required token: {required_token}")


def parse_markdown_cells(line: str) -> list[str]:
	parts = [part.strip() for part in line.strip().split("|")]
	if parts and parts[0] == "":
		parts = parts[1:]
	if parts and parts[-1] == "":
		parts = parts[:-1]
	return parts


def find_manifest_table_lines(manifest_block: str) -> tuple[list[str], list[str]]:
	lines = manifest_block.splitlines()
	for index, line in enumerate(lines[:-1]):
		headers = parse_markdown_cells(line)
		if headers != MANIFEST_HEADERS:
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


def parse_manifest_rows(manifest_block: str) -> list[dict[str, str]]:
	headers, row_lines = find_manifest_table_lines(manifest_block)
	rows: list[dict[str, str]] = []
	for row_line in row_lines:
		cells = parse_markdown_cells(row_line)
		if len(cells) != len(headers):
			raise ValueError("Manifest row does not match expected column count.")
		rows.append({headers[index]: cells[index].strip() for index in range(len(headers))})
	return rows


def validate_prompt_instructions(prompt_instructions_text: str) -> None:
	if EMBEDDED_ROWS_TOKEN not in prompt_instructions_text:
		raise ValueError(f"Prompt instructions file is missing required token: {EMBEDDED_ROWS_TOKEN}")


def filter_manifest_rows(rows: list[dict[str, str]], target_component_id: str) -> list[dict[str, str]]:
	filtered_rows = [row for row in rows if row.get("component_id", "").strip() == target_component_id]
	if not filtered_rows:
		raise ValueError("Filtered manifest is empty for PARAM_TARGET_COMPONENT_ID.")
	indicator_ids = [row.get("indicator_id", "").strip() for row in filtered_rows]
	if any(not indicator_id for indicator_id in indicator_ids):
		raise ValueError("Filtered manifest rows must contain non-empty indicator_id values.")
	if len(set(indicator_ids)) != len(indicator_ids):
		raise ValueError("Duplicate indicator_id values detected within filtered manifest rows.")
	return filtered_rows


def format_manifest_value(value: str) -> str:
	normalized = re.sub(r"\s+", " ", value.strip())
	return normalized.replace("|", r"\|")


def render_embedded_indicator_table_rows(filtered_rows: list[dict[str, str]]) -> str:
	rendered_rows = []
	for row in filtered_rows:
		rendered_rows.append(
			"| {} | {} | {} | {} | {} |".format(
				format_manifest_value(row.get("indicator_id", "")),
				format_manifest_value(row.get("sbo_short_description", "")),
				format_manifest_value(row.get("indicator_definition", "")),
				format_manifest_value(row.get("assessment_guidance", "")),
				format_manifest_value(row.get("evaluation_notes", "")),
			)
		)
	return "\n".join(rendered_rows) + "\n"


def main() -> int:
	args = parse_args()
	try:
		prompt_instructions_text = read_text_file(args.prompt_instructions_file.resolve())
		prompt_input_text = read_text_file(args.prompt_input_file.resolve())
		validate_prompt_instructions(prompt_instructions_text)
		parameter_block, assignment_payload_block, manifest_block = split_payload_blocks(prompt_input_text)
		target_component_id = parse_target_component_id(parameter_block)
		validate_assignment_payload_block(assignment_payload_block)
		manifest_rows = parse_manifest_rows(manifest_block)
		filtered_rows = filter_manifest_rows(manifest_rows, target_component_id)
		rendered_rows = render_embedded_indicator_table_rows(filtered_rows)
		output_path = resolve_output_path(args.output_dir.resolve(), args.output_file_stem, args.output_format)
		output_path.parent.mkdir(parents=True, exist_ok=True)
		output_path.write_text(rendered_rows, encoding="utf-8")
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	print(output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())