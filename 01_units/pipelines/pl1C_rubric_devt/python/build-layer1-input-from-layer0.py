#!/usr/bin/env python3
"""Build a Layer 1 evidence contract and per-component payloads from Layer 0 stitched outputs."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


FENCED_VALUE_TEMPLATE = r"(?ms)^{}\s*$\n```(?:text)?\n(.*?)\n```"


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Build Layer 1 scoring inputs from Layer 0 stitched wide CSV outputs."
	)
	parser.add_argument("--assignment-payload-file", type=Path, required=True)
	parser.add_argument("--layer1-manifest-file", type=Path, required=True)
	parser.add_argument("--layer0-input", type=Path, required=True)
	parser.add_argument("--layer0-input-glob", type=str, default="*.csv")
	parser.add_argument("--output-contract-file", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--output-file-template", type=str, required=True)
	return parser.parse_args()


def read_text_file(path: Path) -> str:
	resolved = path.resolve()
	if not resolved.exists() or not resolved.is_file():
		raise FileNotFoundError(f"File not found: {resolved}")
	return resolved.read_text(encoding="utf-8")


def extract_single_fenced_value(text: str, label: str) -> str:
	pattern = re.compile(FENCED_VALUE_TEMPLATE.format(re.escape(label)))
	match = pattern.search(text)
	if match is None:
		raise ValueError(f"Required fenced value not found for label: {label}")
	return match.group(1).strip()


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


def parse_layer1_manifest_component_ids(manifest_text: str) -> list[str]:
	lines = manifest_text.splitlines()
	for index, line in enumerate(lines[:-1]):
		headers = parse_markdown_cells(line)
		if not {"component_id", "indicator_id"}.issubset(headers):
			continue
		separator = parse_markdown_cells(lines[index + 1])
		if not separator or not all(set(cell.replace(" ", "")) <= {"-", ":"} for cell in separator):
			continue
		component_ids: list[str] = []
		seen: set[str] = set()
		cursor = index + 2
		component_index = headers.index("component_id")
		while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
			cells = parse_markdown_cells(lines[cursor])
			if len(cells) != len(headers):
				raise ValueError("Layer 1 manifest row does not match expected column count.")
			component_id = cells[component_index].strip()
			if component_id and component_id not in seen:
				seen.add(component_id)
				component_ids.append(component_id)
			cursor += 1
		if component_ids:
			return component_ids
	raise ValueError("Supported Layer 1 manifest table was not found.")


def resolve_input_csv_paths(input_path: Path, input_glob: str) -> list[Path]:
	resolved = input_path.resolve(strict=False)
	if resolved.is_file():
		if resolved.suffix.lower() != ".csv":
			raise ValueError(f"Layer 0 input file is not a CSV: {resolved}")
		return [resolved]
	if resolved.is_dir():
		csv_paths = sorted(path for path in resolved.rglob(input_glob) if path.is_file())
		if not csv_paths:
			raise ValueError(
				f"No Layer 0 stitched CSV files found under {resolved} matching glob {input_glob!r}"
			)
		return csv_paths
	raise FileNotFoundError(f"Layer 0 input path not found: {resolved}")


def load_csv_rows(csv_paths: list[Path]) -> tuple[list[str], list[dict[str, str]]]:
	merged_fieldnames: list[str] | None = None
	merged_rows: list[dict[str, str]] = []
	for csv_path in csv_paths:
		with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
			reader = csv.DictReader(handle)
			fieldnames = reader.fieldnames or []
			if not fieldnames:
				continue
			if merged_fieldnames is None:
				merged_fieldnames = fieldnames
			elif fieldnames != merged_fieldnames:
				raise ValueError(
					"Layer 0 stitched CSV headers do not match across inputs; "
					f"expected {merged_fieldnames!r}, got {fieldnames!r} from {csv_path}"
				)
			for raw_row in reader:
				merged_rows.append({name: (raw_row.get(name) or "").strip() for name in fieldnames})
	if merged_fieldnames is None or not merged_rows:
		raise ValueError("No Layer 0 stitched data rows were found.")
	return merged_fieldnames, merged_rows


def build_evidence_text(segment_items: list[tuple[str, str]]) -> str:
	parts: list[str] = []
	for segment_id, segment_text in segment_items:
		if segment_text:
			parts.append(f"[{segment_id}]\n{segment_text}")
	return "\n\n".join(parts)


def validate_single_row_per_submission_component(
	identifier_field: str,
	component_id: str,
	rows: list[dict[str, str]],
) -> None:
	seen_identifiers: set[str] = set()
	duplicate_identifiers: list[str] = []
	for row in rows:
		runtime_identifier = row.get("source_submission_id") or row.get(identifier_field) or row.get("submission_id")
		normalized_identifier = str(runtime_identifier or "").strip()
		if not normalized_identifier:
			continue
		if normalized_identifier in seen_identifiers:
			duplicate_identifiers.append(normalized_identifier)
			continue
		seen_identifiers.add(normalized_identifier)
	if duplicate_identifiers:
		raise ValueError(
			"Layer 1-on-Layer0 flattened input contract assumes exactly one Layer 0 stitched row per "
			f"{identifier_field} × component_id. Found duplicate rows for component_id={component_id!r}: "
			+ ", ".join(sorted(set(duplicate_identifiers)))
		)


def format_timestamp(timestamp_seconds: float) -> str:
	return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc).isoformat(timespec="seconds")


def render_derived_file_header(source_paths: list[Path]) -> str:
	source_descriptors = []
	for source_path in source_paths:
		source_stat = source_path.stat()
		source_descriptors.append(
			f"{source_path} (SOURCE_TIMESTAMP_UTC: {format_timestamp(source_stat.st_mtime)})"
		)
	generated_timestamp = format_timestamp(datetime.now(tz=timezone.utc).timestamp())
	return (
		"<!-- DO NOT EDIT DIRECTLY. THIS IS A DERIVED FILE. "
		f"SOURCES: {' ; '.join(source_descriptors)} | GENERATED_AT_UTC: {generated_timestamp} -->"
	)


def write_component_payload(
	output_path: Path,
	identifier_field: str,
	segment_columns: list[str],
	rows: list[dict[str, str]],
) -> int:
	fieldnames = [
		identifier_field,
		"component_id",
		"evidence_text",
		"evidence_segment_ids",
		"evidence_segment_count",
		*segment_columns,
	]
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding="utf-8", newline="") as handle:
		writer = csv.DictWriter(handle, fieldnames=fieldnames)
		writer.writeheader()
		for row in rows:
			writer.writerow({fieldname: row.get(fieldname, "") for fieldname in fieldnames})
	return len(rows)


def render_contract_markdown(
	title_stem: str,
	assessment_id: str,
	identifier_field: str,
	component_ids: list[str],
	segment_columns_by_component: dict[str, list[str]],
) -> str:
	lines = [
		f"## {title_stem}",
		"### Purpose",
		"This document defines the Layer 1 input contract derived from deterministic Layer 0 stitched outputs.",
		"",
		"This contract is used when Layer 1 indicator scoring operates on extracted evidence segments rather than raw student submissions.",
		"",
		"### Assessment Identity",
		"",
		"assessment_id",
		"```text",
		assessment_id,
		"```",
		"",
		"dataset_origin",
		"```text",
		"Derived from Layer 0 deterministic stitched outputs",
		"```",
		"",
		"### Canonical Identifier Fields",
		"",
		"canonical_submission_level_identifier_field",
		"```text",
		identifier_field,
		"```",
		"",
		"### Canonical Evidence Field",
		"",
		"response_field_name",
		"```text",
		"evidence_text",
		"```",
		"",
		"response_field_type",
		"```text",
		"text",
		"```",
		"",
		"response_description",
		"Concatenated Layer 0 extracted segment texts for one submission and one component. Segment identifiers are preserved inline.",
		"",
		"evidence_rule",
		"```text",
		"explicit Layer 0 extracted evidence only; do not recover omitted source text",
		"```",
		"",
		"### Canonical Dataset Structure",
		"",
		"```text",
		identifier_field,
		"component_id",
		"evidence_text",
		"evidence_segment_ids",
		"evidence_segment_count",
		"segment_text_<segment_id>",
		"```",
		"",
		"Canonical structural unit:",
		"```text",
		f"{identifier_field} × component_id",
		"```",
		"",
		"### Components (Authoritative Set)",
		"",
		"component_ids",
		"```text",
		*component_ids,
		"```",
	]
	for component_id in component_ids:
		segment_columns = segment_columns_by_component.get(component_id, [])
		segment_labels = [column.removeprefix("segment_text_") for column in segment_columns]
		lines.extend(
			[
				"",
				f"#### {component_id}",
				"segment_columns",
				"```text",
				*(segment_labels or ["(none)"]),
				"```",
			]
		)
	lines.extend(
		[
			"",
			"### Wrapper Handling Rules for evidence_text",
			"- `evidence_text` is produced from deterministic Layer 0 segment extraction and should be consumed as written.",
			"- Do not attempt to reconstruct omitted raw-response context from segment ordering or gaps.",
			"- Use only `evidence_text` and the emitted `segment_text_<segment_id>` columns present in the runtime row.",
			"",
			"### Structural Invariants",
			"1. Every Layer 1 runtime row must represent exactly one canonical submission identifier and one component.",
			"2. This flattened Layer 1-on-Layer0 contract assumes exactly one claim-like Layer 0 stitched row per canonical submission identifier and component.",
			"3. If Layer 0 emits multiple stitched rows for the same canonical submission identifier and component, this builder must fail rather than merge them silently.",
			"4. `evidence_text` must be derived only from non-empty Layer 0 `segment_text_<segment_id>` values for that row.",
			"5. `evidence_segment_ids` must preserve the same ordering used to construct `evidence_text`.",
			"6. The raw source response text is not part of this contract.",
		]
	)
	return "\n".join(lines)


def main() -> int:
	args = parse_args()
	try:
		assignment_payload_text = read_text_file(args.assignment_payload_file)
		manifest_text = read_text_file(args.layer1_manifest_file)
		assessment_id = extract_single_fenced_value(assignment_payload_text, "assessment_id")
		identifier_field = extract_single_fenced_value(
			assignment_payload_text,
			"canonical_submission_level_identifier_field",
		)
		component_ids = parse_layer1_manifest_component_ids(manifest_text)
		fieldnames, stitched_rows = load_csv_rows(resolve_input_csv_paths(args.layer0_input, args.layer0_input_glob))
		segment_columns = [field for field in fieldnames if field.startswith("segment_text_")]
		if not segment_columns:
			raise ValueError("Layer 0 stitched input does not contain any segment_text_<segment_id> columns.")

		output_dir = args.output_dir.resolve()
		output_dir.mkdir(parents=True, exist_ok=True)
		segment_columns_by_component: dict[str, list[str]] = {}
		for component_id in component_ids:
			component_rows: list[dict[str, str]] = []
			component_source_rows = [row for row in stitched_rows if row.get("component_id", "") == component_id]
			validate_single_row_per_submission_component(identifier_field, component_id, component_source_rows)
			component_segment_columns = [
				column
				for column in segment_columns
				if any(
					row.get("component_id", "") == component_id and row.get(column, "")
					for row in stitched_rows
				)
			]
			segment_columns_by_component[component_id] = component_segment_columns
			for row in component_source_rows:
				runtime_identifier = row.get("source_submission_id") or row.get(identifier_field) or row.get("submission_id")
				if not runtime_identifier:
					raise ValueError(
						f"Layer 0 stitched row for component_id={component_id!r} is missing a canonical submission identifier."
					)
				segment_items = [
					(column.removeprefix("segment_text_"), row.get(column, ""))
					for column in component_segment_columns
					if row.get(column, "")
				]
				component_rows.append(
					{
						identifier_field: runtime_identifier,
						"component_id": component_id,
						"evidence_text": build_evidence_text(segment_items),
						"evidence_segment_ids": "|".join(segment_id for segment_id, _ in segment_items),
						"evidence_segment_count": str(len(segment_items)),
						**{column: row.get(column, "") for column in component_segment_columns},
					}
				)
			output_path = output_dir / args.output_file_template.format(component_id=component_id)
			row_count = write_component_payload(output_path, identifier_field, component_segment_columns, component_rows)
			print(f"Wrote {row_count} rows to {output_path}")

		output_contract_path = args.output_contract_file.resolve()
		contract_text = render_contract_markdown(
			output_contract_path.stem,
			assessment_id,
			identifier_field,
			component_ids,
			segment_columns_by_component,
		)
		output_contract_path.parent.mkdir(parents=True, exist_ok=True)
		contract_text = (
			render_derived_file_header(
				[
					args.assignment_payload_file.resolve(),
					args.layer1_manifest_file.resolve(),
				]
			)
			+ "\n\n"
			+ contract_text
		)
		output_contract_path.write_text(contract_text + "\n", encoding="utf-8")
		print(f"Wrote contract to {output_contract_path}")
	except (FileNotFoundError, ValueError, KeyError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())