#!/usr/bin/env python3
"""Deterministically render scaffold instances from runner-style inputs.

This script accepts the same core file inputs as the prompt runner plus a
scaffold template file:
- --scaffold-file
- --prompt-input-file
- --output-dir
- --output-file-stem
- --output-format

It validates the three-block payload grammar, extracts PARAM_TARGET_COMPONENT_ID,
filters the Layer 0 or Layer 1 manifest to that component, and writes one output
file per operator/indicator row by instantiating the provided scaffold template.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PAYLOAD_DELIMITER = "§§§"
PARAMETER_RE = re.compile(r"^PARAM_TARGET_COMPONENT_ID\s*=\s*(\S.*?)\s*$")
FENCED_VALUE_TEMPLATE = r"(?ms)^{}\s*$\n```(?:text)?\n(.*?)\n```"
LAYER1_MANIFEST_REQUIRED_HEADERS = [
	"component_id",
	"sbo_identifier",
	"indicator_id",
	"sbo_short_description",
	"indicator_definition",
	"assessment_guidance",
	"evaluation_notes",
]
LAYER0_MANIFEST_REQUIRED_HEADERS = [
	"component_id",
	"sbo_identifier",
	"operator_id",
	"segment_id",
	"sbo_short_description",
	"operator_definition",
	"operator_guidance",
	"evaluation_notes",
]
LAYER1_SCAFFOLD_REQUIRED_TOKENS = [
	"[[ASSESSMENT_ID]]",
	"[[TARGET_COMPONENT_ID]]",
	"[[TARGET_INDICATOR_ID]]",
	"[[SUBMISSION_IDENTIFIER_FIELD]]",
	"[[EVIDENCE_FIELD_NAME]]",
	"[[WRAPPER_HANDLING_RULE_BULLETS]]",
	"[[INDICATOR_ID]]",
	"[[SBO_SHORT_DESCRIPTION]]",
	"[[INDICATOR_DEFINITION]]",
	"[[ASSESSMENT_GUIDANCE]]",
	"[[EMBEDDED_EVALUATOR_GUIDANCE]]",
]
LAYER0_SCAFFOLD_REQUIRED_TOKENS = [
	"[[ASSESSMENT_ID]]",
	"[[TARGET_COMPONENT_ID]]",
	"[[TARGET_OPERATOR_ID]]",
	"[[CANONICAL_SEGMENT_ID]]",
	"[[SUBMISSION_IDENTIFIER_FIELD]]",
	"[[WRAPPER_HANDLING_RULE_BULLETS]]",
	"[[OPERATOR_ID]]",
	"[[SBO_SHORT_DESCRIPTION]]",
	"[[OPERATOR_DEFINITION]]",
	"[[OPERATOR_GUIDANCE]]",
	"[[FAILURE_MODE_GUIDANCE]]",
]
SCAFFOLD_OPTIONAL_TOKENS = ["[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]"]
DEFAULT_DECISION_PROCEDURE_BLOCK = "- No embedded decision procedure is provided for this indicator."


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Render deterministic scaffold instances from a runner-style prompt payload."
	)
	parser.add_argument("--scaffold-file", type=Path, required=True)
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


def resolve_output_path(output_dir: Path, output_file_stem: str, output_format: str, item_id: str) -> Path:
	return output_dir / f"{output_file_stem}_{item_id}.{output_format.lstrip('.')}"


def remove_stale_generated_outputs(output_dir: Path, output_file_stem: str, output_format: str) -> None:
	extension = output_format.lstrip('.')
	for existing_path in output_dir.glob(f"{output_file_stem}_*.{extension}"):
		if existing_path.is_file():
			existing_path.unlink()


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
	if "AssignmentPayloadSpec" not in assignment_payload_block and "Layer1InputContract" not in assignment_payload_block:
		raise ValueError(
			"Assignment payload block does not look like an AssignmentPayloadSpec or Layer1InputContract artefact."
		)
	assessment_id = extract_single_fenced_value(assignment_payload_block, "assessment_id") if "assessment_id\n```" in assignment_payload_block else None
	if assessment_id is None:
		if "assessment_id" not in assignment_payload_block:
			raise ValueError("Assignment payload block is missing assessment_id.")
	_ = extract_single_fenced_value(assignment_payload_block, "canonical_submission_level_identifier_field")
	response_field_name = extract_single_fenced_value(assignment_payload_block, "response_field_name")
	for required_token in ["component_id", response_field_name]:
		if required_token not in assignment_payload_block:
			raise ValueError(f"Assignment payload block is missing required token: {required_token}")


def parse_assignment_payload_metadata(assignment_payload_block: str) -> dict[str, str]:
	assessment_id = extract_single_fenced_value(assignment_payload_block, "assessment_id")
	submission_identifier_field = extract_single_fenced_value(
		assignment_payload_block,
		"canonical_submission_level_identifier_field",
	)
	response_field_name = extract_single_fenced_value(assignment_payload_block, "response_field_name")
	wrapper_handling_rule_bullets = extract_wrapper_handling_rule_bullets(
		assignment_payload_block,
		response_field_name,
	)
	return {
		"assessment_id": assessment_id,
		"submission_identifier_field": submission_identifier_field,
		"evidence_field_name": response_field_name,
		"wrapper_handling_rule_bullets": wrapper_handling_rule_bullets,
	}


def extract_wrapper_handling_rule_bullets(assignment_payload_block: str, response_field_name: str) -> str:
	heading = f"### Wrapper Handling Rules for {response_field_name}"
	start_index = assignment_payload_block.find(heading)
	if start_index == -1:
		raise ValueError(
			f"Assignment payload block is missing the wrapper handling rules section for {response_field_name}."
		)
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


def find_manifest_table_lines(manifest_block: str) -> tuple[str, list[str], list[str]]:
	lines = manifest_block.splitlines()
	for index, line in enumerate(lines[:-1]):
		headers = parse_markdown_cells(line)
		schema = detect_manifest_schema(headers)
		if schema is None:
			continue
		separator = parse_markdown_cells(lines[index + 1])
		if not separator or not all(set(cell.replace(" ", "")) <= {"-", ":"} for cell in separator):
			continue
		row_lines: list[str] = []
		cursor = index + 2
		while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
			row_lines.append(lines[cursor])
			cursor += 1
		return (schema, headers, row_lines)
	raise ValueError("Supported Layer 0 or Layer 1 manifest table was not found.")


def detect_manifest_schema(headers: list[str]) -> str | None:
	if all(required_header in headers for required_header in LAYER1_MANIFEST_REQUIRED_HEADERS):
		return "layer1"
	if all(required_header in headers for required_header in LAYER0_MANIFEST_REQUIRED_HEADERS):
		return "layer0"
	return None


def parse_manifest_rows(manifest_block: str) -> tuple[str, list[dict[str, str]]]:
	schema, headers, row_lines = find_manifest_table_lines(manifest_block)
	rows: list[dict[str, str]] = []
	for row_line in row_lines:
		cells = parse_markdown_cells(row_line)
		if len(cells) != len(headers):
			raise ValueError("Manifest row does not match expected column count.")
		rows.append({headers[index]: cells[index].strip() for index in range(len(headers))})
	return schema, rows


def extract_scaffold_body(scaffold_text: str) -> str:
	def extract_primary_render_body(body_text: str) -> str:
		quadruple_fence_match = re.search(r"(?ms)^[ \t]*````\n(.*?)\n[ \t]*````", body_text)
		if quadruple_fence_match is not None:
			return quadruple_fence_match.group(1).strip() + "\n"
		return body_text

	if scaffold_text.startswith("---\n"):
		parts = scaffold_text.split("\n---\n", 1)
		if len(parts) != 2:
			raise ValueError("Scaffold file has malformed YAML frontmatter.")
		return extract_primary_render_body(parts[1])
	return extract_primary_render_body(scaffold_text)


def validate_scaffold(scaffold_body: str, required_tokens: list[str]) -> None:
	missing_tokens = [token for token in required_tokens if token not in scaffold_body]
	if missing_tokens:
		raise ValueError(f"Scaffold file is missing required token(s): {missing_tokens}")


def render_scaffold(scaffold_body: str, token_values: dict[str, str]) -> str:
	rendered = scaffold_body
	for token, value in token_values.items():
		if not value:
			raise ValueError(f"Missing value for required scaffold token: {token}")
		rendered = rendered.replace(token, value)
	for token in SCAFFOLD_OPTIONAL_TOKENS:
		rendered = rendered.replace(token, token_values.get(token, ""))
	unreplaced_tokens = sorted(set(re.findall(r"\[\[[A-Z0-9_]+\]\]", rendered)))
	if unreplaced_tokens:
		raise ValueError(f"Unreplaced scaffold token(s) remain: {unreplaced_tokens}")
	return rendered


def filter_manifest_rows(rows: list[dict[str, str]], target_component_id: str, item_id_field: str) -> list[dict[str, str]]:
	filtered_rows = [row for row in rows if row.get("component_id", "").strip() == target_component_id]
	if not filtered_rows:
		raise ValueError("Filtered manifest is empty for PARAM_TARGET_COMPONENT_ID.")
	item_ids = [row.get(item_id_field, "").strip() for row in filtered_rows]
	if any(not item_id for item_id in item_ids):
		raise ValueError(f"Filtered manifest rows must contain non-empty {item_id_field} values.")
	if len(set(item_ids)) != len(item_ids):
		raise ValueError(f"Duplicate {item_id_field} values detected within filtered manifest rows.")
	return filtered_rows


def format_manifest_value(value: str) -> str:
	normalized = re.sub(r"\s+", " ", value.strip())
	return normalized.replace("|", r"\|")


def build_token_values(
	schema: str,
	assignment_payload_metadata: dict[str, str],
	target_component_id: str,
	row: dict[str, str],
) -> dict[str, str]:
	decision_procedure_block = render_decision_procedure_block(row.get("decision_procedure", ""))
	if schema == "layer0":
		return {
			"[[ASSESSMENT_ID]]": assignment_payload_metadata["assessment_id"],
			"[[TARGET_COMPONENT_ID]]": target_component_id,
			"[[TARGET_OPERATOR_ID]]": row["operator_id"],
			"[[CANONICAL_SEGMENT_ID]]": row["segment_id"],
			"[[SUBMISSION_IDENTIFIER_FIELD]]": assignment_payload_metadata["submission_identifier_field"],
			"[[WRAPPER_HANDLING_RULE_BULLETS]]": assignment_payload_metadata["wrapper_handling_rule_bullets"],
			"[[OPERATOR_ID]]": row["operator_id"],
			"[[SBO_SHORT_DESCRIPTION]]": row["sbo_short_description"],
			"[[OPERATOR_DEFINITION]]": row["operator_definition"],
			"[[OPERATOR_GUIDANCE]]": row["operator_guidance"],
			"[[FAILURE_MODE_GUIDANCE]]": row["evaluation_notes"],
			"[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]": decision_procedure_block,
		}
	return {
		"[[ASSESSMENT_ID]]": assignment_payload_metadata["assessment_id"],
		"[[TARGET_COMPONENT_ID]]": target_component_id,
		"[[TARGET_INDICATOR_ID]]": row["indicator_id"],
		"[[SUBMISSION_IDENTIFIER_FIELD]]": assignment_payload_metadata["submission_identifier_field"],
		"[[EVIDENCE_FIELD_NAME]]": assignment_payload_metadata["evidence_field_name"],
		"[[WRAPPER_HANDLING_RULE_BULLETS]]": assignment_payload_metadata["wrapper_handling_rule_bullets"],
		"[[INDICATOR_ID]]": row["indicator_id"],
		"[[SBO_SHORT_DESCRIPTION]]": row["sbo_short_description"],
		"[[INDICATOR_DEFINITION]]": row["indicator_definition"],
		"[[ASSESSMENT_GUIDANCE]]": row["assessment_guidance"],
		"[[EMBEDDED_EVALUATOR_GUIDANCE]]": row["evaluation_notes"],
		"[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]": decision_procedure_block,
	}


def manifest_schema_config(schema: str) -> tuple[str, list[str]]:
	if schema == "layer0":
		return "operator_id", LAYER0_SCAFFOLD_REQUIRED_TOKENS
	return "indicator_id", LAYER1_SCAFFOLD_REQUIRED_TOKENS


def render_decision_procedure_block(decision_procedure: str) -> str:
	normalized = decision_procedure.strip()
	if not normalized:
		return DEFAULT_DECISION_PROCEDURE_BLOCK
	return normalized


def main() -> int:
	args = parse_args()
	try:
		scaffold_text = read_text_file(args.scaffold_file.resolve())
		prompt_input_text = read_text_file(args.prompt_input_file.resolve())
		scaffold_body = extract_scaffold_body(scaffold_text)
		parameter_block, assignment_payload_block, manifest_block = split_payload_blocks(prompt_input_text)
		target_component_id = parse_target_component_id(parameter_block)
		validate_assignment_payload_block(assignment_payload_block)
		assignment_payload_metadata = parse_assignment_payload_metadata(assignment_payload_block)
		schema, manifest_rows = parse_manifest_rows(manifest_block)
		item_id_field, required_tokens = manifest_schema_config(schema)
		validate_scaffold(scaffold_body, required_tokens)
		filtered_rows = filter_manifest_rows(manifest_rows, target_component_id, item_id_field)
		output_dir = args.output_dir.resolve()
		output_dir.mkdir(parents=True, exist_ok=True)
		remove_stale_generated_outputs(output_dir, args.output_file_stem, args.output_format)
		output_paths: list[Path] = []
		for row in filtered_rows:
			item_id = row[item_id_field].strip()
			output_path = resolve_output_path(output_dir, args.output_file_stem, args.output_format, item_id)
			token_values = build_token_values(schema, assignment_payload_metadata, target_component_id, row)
			output_text = render_scaffold(scaffold_body, token_values)
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