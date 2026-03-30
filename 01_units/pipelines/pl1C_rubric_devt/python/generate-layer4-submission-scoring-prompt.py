#!/usr/bin/env python3
"""Generate a Layer 4 submission scoring prompt from manifest and payload inputs."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


MANIFEST_REQUIRED_HEADERS = [
	"sbo_identifier",
	"sbo_short_description",
	"submission_definition",
	"submission_guidance",
	"evaluation_notes",
	"decision_procedure",
]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate a Layer 4 submission scoring prompt from a Layer 4 scoring manifest and a Layer 3 submission payload."
	)
	parser.add_argument("--manifest-file", type=Path, required=True)
	parser.add_argument("--payload-file", type=Path, required=True)
	parser.add_argument("--output-file", type=Path, required=True)
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


def parse_manifest_row(manifest_text: str) -> dict[str, str]:
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
		if len(row_lines) != 1:
			raise ValueError("Layer 4 scoring manifest must contain exactly one submission row.")
		cells = parse_markdown_cells(row_lines[0])
		if len(cells) != len(headers):
			raise ValueError("Manifest row does not match expected column count.")
		return {headers[index]: cells[index].strip() for index in range(len(headers))}
	raise ValueError("Layer 4 scoring manifest table was not found.")


def load_payload_header(payload_path: Path) -> list[str]:
	if not payload_path.exists() or not payload_path.is_file():
		raise FileNotFoundError(f"Payload file not found: {payload_path}")
	with payload_path.open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.reader(handle)
		try:
			headers = next(reader)
		except StopIteration as exc:
			raise ValueError("Payload CSV is empty.") from exc
	return [header.strip() for header in headers if header.strip()]


def derive_assessment_id(sbo_identifier: str) -> str:
	match = re.fullmatch(r"[A-Z]_([A-Za-z0-9]+)", sbo_identifier.strip())
	if match:
		return match.group(1)
	parts = [part for part in sbo_identifier.strip().split("_") if part]
	if len(parts) >= 2:
		return parts[1]
	return sbo_identifier.strip()


def format_bullets(values: list[str]) -> str:
	return "\n".join(f"- {value}" for value in values)


def build_prompt_text(manifest_row: dict[str, str], payload_header: list[str]) -> str:
	assessment_id = derive_assessment_id(manifest_row["sbo_identifier"])
	output_columns = ["submission_id", "submission_score"]
	if "flags_any_component" in payload_header:
		output_columns.append("flags_any_component")
	if "min_confidence_component" in payload_header:
		output_columns.append("min_confidence_component")
	return "\n".join(
		[
			f"# Layer 4 Submission Scoring Prompt: {assessment_id}",
			"",
			"## Task",
			"",
			"Score each submission row using only the Layer 3 submission payload values supplied in the input CSV.",
			"Return CSV output only. Do not add commentary, code fences, or prose.",
			"",
			"## Target Outcome",
			"",
			f"- SBO identifier: {manifest_row['sbo_identifier']}",
			f"- SBO short description: {manifest_row['sbo_short_description']}",
			f"- Submission definition: {manifest_row['submission_definition']}",
			"",
			"## Guidance",
			"",
			manifest_row["submission_guidance"],
			"",
			"## Evaluation Notes",
			"",
			manifest_row["evaluation_notes"],
			"",
			"## Decision Procedure",
			"",
			manifest_row["decision_procedure"],
			"",
			"## Input CSV Columns",
			"",
			format_bullets(payload_header),
			"",
			"## Required Output CSV Columns",
			"",
			format_bullets(output_columns),
			"",
			"## Output Rules",
			"",
			"- Preserve the input submission_id exactly.",
			"- Write one output row per input row.",
			"- Derive submission_score only from the provided component_score columns.",
			"- If flags_any_component is present in the input, copy it through unchanged.",
			"- If min_confidence_component is present in the input, copy it through unchanged.",
			"- Return a valid CSV with a header row.",
		]
	)


def main() -> int:
	args = parse_args()
	try:
		manifest_text = read_text_file(args.manifest_file.resolve())
		manifest_row = parse_manifest_row(manifest_text)
		payload_header = load_payload_header(args.payload_file.resolve())
		prompt_text = build_prompt_text(manifest_row, payload_header)
		output_path = args.output_file.resolve()
		output_path.parent.mkdir(parents=True, exist_ok=True)
		output_path.write_text(prompt_text + "\n", encoding="utf-8")
	except (FileNotFoundError, ValueError, OSError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	print(args.output_file.resolve())
	return 0


if __name__ == "__main__":
	raise SystemExit(main())