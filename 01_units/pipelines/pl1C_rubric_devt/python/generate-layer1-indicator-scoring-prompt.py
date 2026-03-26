#!/usr/bin/env python3
"""Deterministically render scaffold token assignments from runner-style inputs.

This script accepts the same core file inputs as the prompt runner:
- --prompt-instructions-file
- --prompt-input-file
- --output-dir
- --output-file-stem
- --output-format

It validates the three-block payload grammar, extracts PARAM_TARGET_COMPONENT_ID,
filters the Layer 1 scoring manifest to that component, and writes one output
file per indicator row containing token assignments for scaffold substitution.
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
MANIFEST_REQUIRED_HEADERS = [
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


def resolve_output_path(output_dir: Path, output_file_stem: str, output_format: str, indicator_id: str) -> Path:
	return output_dir / f"{output_file_stem}_{indicator_id}.{output_format.lstrip('.')}"


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


def parse_assignment_payload_metadata(assignment_payload_block: str) -> dict[str, str]:
	assessment_id = extract_single_fenced_value(assignment_payload_block, "assessment_id")
	submission_identifier_field = extract_single_fenced_value(
		assignment_payload_block,
		"canonical_submission_level_identifier_field",
	)
	wrapper_handling_rule_bullets = extract_wrapper_handling_rule_bullets(assignment_payload_block)
	return {
		"assessment_id": assessment_id,
		"submission_identifier_field": submission_identifier_field,
		"wrapper_handling_rule_bullets": wrapper_handling_rule_bullets,
	}


def extract_wrapper_handling_rule_bullets(assignment_payload_block: str) -> str:
	heading = "### Wrapper Handling Rules for response_text"
	start_index = assignment_payload_block.find(heading)
	if start_index == -1:
		raise ValueError("Assignment payload block is missing the wrapper handling rules section.")
	section_lines = assignment_payload_block[start_index:].splitlines()[1:]
	bullet_lines: list[str] = []
	for line in section_lines:
		if line.startswith("### "):
			break
		if line.startswith("- "):
			bullet_lines.append(line.rstrip())
	if not bullet_lines:
		raise ValueError("Wrapper handling rules section does not contain bullet lines.")
	return "\n".join(bullet_lines)


def parse_markdown_cells(line: str) -> list[str]:
	parts = [part.strip() for part in line.strip().split("|")]
	if parts and parts[0] == "":
		parts = parts[1:]
	if parts and parts[-1] == "":
		parts = parts[:-1]
	return [normalize_markdown_cell(part) for part in parts]


def normalize_markdown_cell(value: str) -> str:
	normalized = value.strip()
	if len(normalized) >= 2 and normalized.startswith("`") and normalized.endswith("`"):
		return normalized[1:-1].strip()
	return normalized


def find_manifest_table_lines(manifest_block: str) -> tuple[list[str], list[str]]:
	lines = manifest_block.splitlines()
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


def manifest_headers_are_supported(headers: list[str]) -> bool:
	return all(required_header in headers for required_header in MANIFEST_REQUIRED_HEADERS)


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


def render_token_assignment(token: str, value: str) -> str:
	return f"{token}\n{value}" if value else f"{token}\n"


def build_token_assignments(
	assignment_payload_metadata: dict[str, str],
	target_component_id: str,
	row: dict[str, str],
) -> str:
	token_blocks = [
		render_token_assignment("[[ASSESSMENT_ID]]", assignment_payload_metadata["assessment_id"]),
		render_token_assignment("[[TARGET_COMPONENT_ID]]", target_component_id),
		render_token_assignment("[[TARGET_INDICATOR_ID]]", row["indicator_id"]),
		render_token_assignment(
			"[[SUBMISSION_IDENTIFIER_FIELD]]",
			assignment_payload_metadata["submission_identifier_field"],
		),
		render_token_assignment(
			"[[WRAPPER_HANDLING_RULE_BULLETS]]",
			assignment_payload_metadata["wrapper_handling_rule_bullets"],
		),
		render_token_assignment("[[INDICATOR_ID]]", row["indicator_id"]),
		render_token_assignment("[[SBO_SHORT_DESCRIPTION]]", row["sbo_short_description"]),
		render_token_assignment("[[INDICATOR_DEFINITION]]", row["indicator_definition"]),
		render_token_assignment("[[ASSESSMENT_GUIDANCE]]", row["assessment_guidance"]),
		render_token_assignment("[[EMBEDDED_EVALUATOR_GUIDANCE]]", row["evaluation_notes"]),
	]
	decision_procedure_block = row.get("decision_procedure", "").strip()
	if decision_procedure_block:
		token_blocks.append(
			render_token_assignment("[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]", decision_procedure_block)
		)
	return "\n\n".join(token_blocks) + "\n"


def main() -> int:
	args = parse_args()
	try:
		prompt_instructions_text = read_text_file(args.prompt_instructions_file.resolve())
		prompt_input_text = read_text_file(args.prompt_input_file.resolve())
		validate_prompt_instructions(prompt_instructions_text)
		parameter_block, assignment_payload_block, manifest_block = split_payload_blocks(prompt_input_text)
		target_component_id = parse_target_component_id(parameter_block)
		validate_assignment_payload_block(assignment_payload_block)
		assignment_payload_metadata = parse_assignment_payload_metadata(assignment_payload_block)
		manifest_rows = parse_manifest_rows(manifest_block)
		filtered_rows = filter_manifest_rows(manifest_rows, target_component_id)
		output_dir = args.output_dir.resolve()
		output_dir.mkdir(parents=True, exist_ok=True)
		output_paths: list[Path] = []
		for row in filtered_rows:
			indicator_id = row["indicator_id"].strip()
			output_path = resolve_output_path(output_dir, args.output_file_stem, args.output_format, indicator_id)
			output_text = build_token_assignments(assignment_payload_metadata, target_component_id, row)
			output_path.write_text(output_text, encoding="utf-8")
			output_paths.append(output_path)
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	for output_path in output_paths:
		print(output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())