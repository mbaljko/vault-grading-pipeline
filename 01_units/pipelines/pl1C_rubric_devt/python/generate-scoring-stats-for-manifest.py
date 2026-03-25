#!/usr/bin/env python3
"""Generate scoring-stats markdown files for manifest entries matching a component ID.

This script mirrors the manifest iteration behavior of
run-itp-report-for-manifest.py, but instead of invoking the LLM runner it
produces a markdown scoring-stats file for each matching SBO row.

Arguments:
- --sbo-manifest-file: markdown manifest file to parse.
- --component-id: string token used to select matching manifest rows.
- --file-with-scored-texts: CSV used to collect scoring rows by indicator_id.
- --output-dir: optional explicit output directory. Defaults to
  <manifest_dir>/Level1-CalibrationTesting-Outputs.

Per matching row behavior:
1. Extract the manifest row into a components dict.
2. Filter scored CSV rows matching the manifest row's indicator_id.
3. Compute indicator-level scoring stats.
4. Write one consolidated markdown scoring-stats report named
	<component_id>_output_scoring_stats_report.md in the output directory.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
RUNNER_OUTPUT_SUBDIR = "Level1-CalibrationTesting-Outputs"
POSITIVE_EVIDENCE_STATUS_VALUES = {
	"positive",
	"present",
	"yes",
	"true",
	"1",
	"supported",
	"met",
}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate scoring-stats markdown files for manifest entries matching a component ID."
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
		help="Output directory for scoring-stats files. Defaults to <manifest_dir>/Level1-CalibrationTesting-Outputs.",
	)
	return parser.parse_args()


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


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
	header_line = "| " + " | ".join(headers) + " |"
	separator_line = "| " + " | ".join("---" for _ in headers) + " |"
	body_lines = ["| " + " | ".join(row) + " |" for row in rows]
	return "\n".join([header_line, separator_line, *body_lines])


def format_rate(numerator: int, denominator: int) -> str:
	if denominator <= 0:
		return "0.0%"
	return f"{(numerator / denominator * 100):.1f}%"


def is_positive_scored_row(row: dict[str, str]) -> bool:
	status = (row.get("evidence_status") or "").strip().lower()
	return status in POSITIVE_EVIDENCE_STATUS_VALUES


def render_consolidated_scoring_stats_document(
	component_id: str,
	scored_csv_path: Path,
	total_scored_rows: int,
	indicator_rows: list[list[str]],
) -> str:
	parts = [
		f"## {component_id}_output_scoring_stats_report",
		"",
		"Saturation rate is defined here as number_scored_positive divided by number_scored for each indicator.",
		"",
		render_markdown_table(
			["metric", "value"],
			[
				["component_id", component_id],
				["source_scored_csv", str(scored_csv_path)],
				["total_scored_rows", str(total_scored_rows)],
				["positive_evidence_status_values", ", ".join(sorted(POSITIVE_EVIDENCE_STATUS_VALUES))],
			],
		),
		"",
		"### Indicator saturation",
		"",
		render_markdown_table(
			["indicator_id", "saturation_rate", "number_scored", "number_scored_positive"],
			indicator_rows,
		),
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
	total_scored_rows = len(scored_rows)
	lines = manifest_path.read_text(encoding="utf-8").splitlines()
	indicator_summary_rows: dict[str, list[str]] = {}

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
				indicator_id = (components.get("indicator_id") or "").strip() or "<missing>"
				matching_scored_rows = find_matching_scored_rows(components, scored_rows)
				number_scored = len(matching_scored_rows)
				number_scored_positive = sum(1 for row in matching_scored_rows if is_positive_scored_row(row))
				indicator_summary_rows[indicator_id] = [
					indicator_id,
					format_rate(number_scored_positive, number_scored),
					str(number_scored),
					str(number_scored_positive),
				]
			i += 1

	consolidated_indicator_rows = [indicator_summary_rows[key] for key in sorted(indicator_summary_rows)]
	consolidated_output_path = output_dir / f"{component_id}_output_scoring_stats_report.md"
	consolidated_output_path.write_text(
		render_consolidated_scoring_stats_document(
			component_id=component_id,
			scored_csv_path=scored_csv_path,
			total_scored_rows=total_scored_rows,
			indicator_rows=consolidated_indicator_rows,
		),
		encoding="utf-8",
	)
	print(consolidated_output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())