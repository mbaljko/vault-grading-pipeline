#!/usr/bin/env python3
"""Summarize scored CSV rows for manifest entries matching a component ID.

This script mirrors the manifest iteration behavior of
run-itp-report-for-manifest.py, but instead of invoking the LLM runner it
produces a markdown summary file for each matching SBO row.

Arguments:
- --sbo-manifest-file: markdown manifest file to parse.
- --component-id: string token used to select matching manifest rows.
- --file-with-scored-texts: CSV used to collect scoring rows by indicator_id.
- --output-dir: optional explicit output directory. Defaults to
  <manifest_dir>/Level1-CalibrationTesting-Outputs.

Per matching row behavior:
1. Extract the manifest row into a components dict.
2. Filter scored CSV rows matching the manifest row's indicator_id.
3. Compute summary statistics for evidence_status, confidence, flags, and
   evaluation_notes coverage.
4. Write a markdown summary file named
   <sbo_identifier>_output_summary.md in the output directory.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path


SBO_IDENTIFIER_RE = re.compile(r"\bI_[A-Za-z0-9_]+\b")
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
RUNNER_OUTPUT_SUBDIR = "Level1-CalibrationTesting-Outputs"


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Summarize scored CSV rows for manifest entries matching a component ID."
	)
	parser.add_argument(
		"--sbo-manifest-file",
		type=Path,
		required=True,
		help="Path to the markdown manifest file to read.",
	)
	parser.add_argument(
		"--component-id",
		type=str,
		required=True,
		help="Component ID used to filter matching manifest rows.",
	)
	parser.add_argument(
		"--file-with-scored-texts",
		type=Path,
		required=True,
		help="Path to scored-texts CSV input file.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		required=False,
		help="Output directory for summary files. Defaults to <manifest_dir>/Level1-CalibrationTesting-Outputs.",
	)
	return parser.parse_args()


def extract_sbo_identifier(line: str) -> str:
	match = SBO_IDENTIFIER_RE.search(line)
	if match:
		return match.group(0)
	return "UNKNOWN_SBO_IDENTIFIER"


def normalize_markdown_cell(value: str) -> str:
	stripped = value.strip()
	if re.fullmatch(r"`[^`]*`", stripped):
		return stripped[1:-1].strip()
	return stripped


def parse_markdown_cells(line: str) -> list[str]:
	parts = [part.strip() for part in line.strip().split("|")]
	if parts and parts[0] == "":
		parts = parts[1:]
	if parts and parts[-1] == "":
		parts = parts[:-1]
	return [normalize_markdown_cell(part) for part in parts]


def is_separator_row(cells: list[str]) -> bool:
	if not cells:
		return False
	return all(bool(SEPARATOR_CELL_RE.match(cell.replace(" ", ""))) for cell in cells)


def load_scored_rows(input_path: Path) -> list[dict[str, str]]:
	rows: list[dict[str, str]] = []
	with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.DictReader(handle)
		if not reader.fieldnames:
			return rows

		for raw_row in reader:
			normalized_row: dict[str, str] = {}
			for key, value in raw_row.items():
				if key is None:
					continue
				normalized_row[key.strip()] = (value or "").strip()
			rows.append(normalized_row)
	return rows


def find_matching_scored_rows(
	manifest_components: dict[str, str],
	scored_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
	indicator_id = (manifest_components.get("indicator_id") or "").strip()
	if not indicator_id:
		return []

	matches: list[dict[str, str]] = []
	for row in scored_rows:
		if (row.get("indicator_id") or "").strip() == indicator_id:
			matches.append(row)
	return matches


def count_values(rows: list[dict[str, str]], field_name: str) -> Counter[str]:
	counter: Counter[str] = Counter()
	for row in rows:
		value = (row.get(field_name) or "").strip() or "<blank>"
		counter[value] += 1
	return counter


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
	header_line = "| " + " | ".join(headers) + " |"
	separator_line = "| " + " | ".join("---" for _ in headers) + " |"
	body_lines = ["| " + " | ".join(row) + " |" for row in rows]
	return "\n".join([header_line, separator_line, *body_lines])


def render_counter_table(counter: Counter[str], total_rows: int) -> str:
	rows: list[list[str]] = []
	for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
		percentage = f"{(count / total_rows * 100):.1f}%" if total_rows else "0.0%"
		rows.append([value, str(count), percentage])
	return render_markdown_table(["value", "count", "percent"], rows)


def render_summary_document(
	sbo_identifier: str,
	components: dict[str, str],
	matching_rows: list[dict[str, str]],
	scored_csv_path: Path,
) -> str:
	total_rows = len(matching_rows)
	unique_submission_ids = len(
		{(row.get("submission_id") or "").strip() for row in matching_rows if (row.get("submission_id") or "").strip()}
	)
	non_empty_notes = sum(1 for row in matching_rows if (row.get("evaluation_notes") or "").strip())
	blank_notes = total_rows - non_empty_notes

	evidence_status_counts = count_values(matching_rows, "evidence_status")
	confidence_counts = count_values(matching_rows, "confidence")
	flags_counts = count_values(matching_rows, "flags")

	parts = [
		f"## {sbo_identifier}_output_summary",
		"",
		"### 1. Manifest row",
		"",
		render_markdown_table(
			["field", "value"],
			[[key, value] for key, value in components.items()],
		),
		"",
		"### 2. Scoring coverage summary",
		"",
		render_markdown_table(
			["metric", "value"],
			[
				["source_scored_csv", str(scored_csv_path)],
				["matched_rows", str(total_rows)],
				["unique_submission_ids", str(unique_submission_ids)],
				["rows_with_evaluation_notes", str(non_empty_notes)],
				["rows_with_blank_evaluation_notes", str(blank_notes)],
			],
		),
		"",
		"### 3. Evidence status distribution",
		"",
		render_counter_table(evidence_status_counts, total_rows),
		"",
		"### 4. Confidence distribution",
		"",
		render_counter_table(confidence_counts, total_rows),
		"",
		"### 5. Flags distribution",
		"",
		render_counter_table(flags_counts, total_rows),
		"",
	]
	return "\n".join(parts)


def main() -> int:
	args = parse_args()
	manifest_path = args.sbo_manifest_file.resolve()
	component_id = args.component_id
	scored_csv_path = args.file_with_scored_texts.resolve()
	output_dir = args.output_dir.resolve() if args.output_dir else manifest_path.parent / RUNNER_OUTPUT_SUBDIR

	if not manifest_path.exists() or not manifest_path.is_file():
		print(f"Error: markdown file not found: {manifest_path}", file=sys.stderr)
		return 1
	if not scored_csv_path.exists() or not scored_csv_path.is_file():
		print(f"Error: scored-texts file not found: {scored_csv_path}", file=sys.stderr)
		return 1

	output_dir.mkdir(parents=True, exist_ok=True)
	scored_rows = load_scored_rows(scored_csv_path)
	lines = manifest_path.read_text(encoding="utf-8").splitlines()

	i = 0
	while i < len(lines):
		line = lines[i]
		if not line.lstrip().startswith("|"):
			i += 1
			continue

		header_cells = parse_markdown_cells(line)
		if i + 1 >= len(lines):
			i += 1
			continue

		separator_cells = parse_markdown_cells(lines[i + 1])
		if not is_separator_row(separator_cells):
			i += 1
			continue

		i += 2
		while i < len(lines) and lines[i].lstrip().startswith("|"):
			row_line = lines[i]
			row_cells = parse_markdown_cells(row_line)
			if is_separator_row(row_cells):
				i += 1
				continue

			if component_id in row_line:
				padded = row_cells + [""] * (len(header_cells) - len(row_cells))
				components = {header_cells[idx]: padded[idx] for idx in range(len(header_cells))}
				sbo_identifier = extract_sbo_identifier(row_line)
				matching_scored_rows = find_matching_scored_rows(components, scored_rows)
				summary_text = render_summary_document(
					sbo_identifier=sbo_identifier,
					components=components,
					matching_rows=matching_scored_rows,
					scored_csv_path=scored_csv_path,
				)
				output_path = output_dir / f"{sbo_identifier}_output_summary.md"
				output_path.write_text(summary_text, encoding="utf-8")
				print(output_path)
			i += 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())