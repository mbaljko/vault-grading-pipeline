#!/usr/bin/env python3
"""Generate a consolidated scoring-stats markdown report for one or more components.

This script mirrors the manifest iteration behavior of
run-itp-report-for-manifest.py, but instead of invoking the LLM runner it
parses the scoring manifest, aligns one or more scored CSV inputs to the
requested component IDs, and writes a single consolidated markdown report.

Arguments:
- --indicator-registry: markdown indicator registry file used to reverse
	expanded indicators back to Base Table rows for registry-level aggregation.
- --sbo-manifest-file: markdown manifest file to parse.
- --component-id: repeatable component identifier used to select matching
	manifest rows. Repeat this flag to combine multiple components in one run.
- --file-with-scored-texts: repeatable scored CSV path aligned positionally
	with --component-id. Each CSV is only used for its paired component.
- --output-dir: optional explicit output directory. Defaults to
	<manifest_dir>/Level1-CalibrationTesting-Outputs.

Report contents:
1. A metadata table showing the included component IDs, source scored CSVs,
	 total scored row count across all supplied CSVs, and the set of
	 evidence_status values treated as positive.
2. An indicator-level table with these columns:
	 - component_id
	 - indicator_id
	 - saturation_rate
	 - number_scored
	 - number_scored_positive
3. A Base Table aggregation that reverses reuse expansion back to registry
	 template rows and reports the same stats at the base-row level.

Saturation rate definition:
- saturation_rate = number_scored_positive / number_scored

Output naming:
- Single-component run:
	<component_id>_output_scoring_stats_report.md
- Multi-component run:
	all_components_output_scoring_stats_report.md
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from generate_rubric_and_manifest_from_indicator_registry import (
	apply_expression_template,
	apply_token_template,
	collect_markdown_tables,
	expand_component_pattern,
	extract_rule_template,
	find_table_by_heading,
	resolve_component_block_lookup,
	resolve_local_slot_values,
)


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
		"--indicator-registry",
		type=Path,
		required=True,
		help="Path to the markdown indicator registry file used for base-table aggregation.",
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
		action="append",
		help="Component ID used to filter matching manifest rows. Repeat to combine multiple components into one report.",
	)
	parser.add_argument(
		"--file-with-scored-texts",
		type=Path,
		required=True,
		action="append",
		help="Path to scored-texts CSV input file. Repeat in the same order as --component-id.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		required=False,
		help="Output directory for scoring-stats files. Defaults to <manifest_dir>/Level1-CalibrationTesting-Outputs.",
	)
	return parser.parse_args()


def derive_output_filename(component_ids: list[str]) -> str:
	if len(component_ids) == 1:
		return f"{component_ids[0]}_output_scoring_stats_report.md"
	return "all_components_output_scoring_stats_report.md"


def build_base_row_reverse_lookup(registry_path: Path) -> dict[tuple[str, str], dict[str, str]]:
	tables = collect_markdown_tables(registry_path)
	base_table = find_table_by_heading(tables, "base table")
	reuse_table = find_table_by_heading(tables, "reuse rule table")
	component_block_rule_table = find_table_by_heading(tables, "component block rule table")
	if base_table is None or reuse_table is None:
		return {}

	base_rows = list(base_table["rows"])
	reuse_rows = list(reuse_table["rows"])
	reuse_headers = set(reuse_table["headers"])
	base_by_template_id = {
		row.get("template_id", "").strip(): row for row in base_rows if row.get("template_id", "").strip()
	}
	base_by_local_slot = {
		row.get("local_slot", "").strip(): row for row in base_rows if row.get("local_slot", "").strip()
	}
	reverse_lookup: dict[tuple[str, str], dict[str, str]] = {}

	def register_mapping(component_id: str, indicator_id: str, base_row: dict[str, str], reuse_row: dict[str, str]) -> None:
		reverse_lookup[(component_id, indicator_id)] = {
			"template_id": base_row.get("template_id", "").strip() or "<missing_template_id>",
			"local_slot": base_row.get("local_slot", "").strip(),
			"sbo_short_description": base_row.get("sbo_short_description", "").strip(),
			"expansion_mode": reuse_row.get("expansion_mode", "").strip() or "<unspecified>",
		}

	if {"indicator_id", "component_id"}.issubset(reuse_headers):
		for reuse_row in reuse_rows:
			template_id = reuse_row.get("template_id", "").strip()
			local_slot = reuse_row.get("local_slot", "").strip()
			base_row = None
			if template_id:
				base_row = base_by_template_id.get(template_id)
			if base_row is None and local_slot:
				base_row = base_by_local_slot.get(local_slot)
			if base_row is None:
				continue
			component_id = reuse_row.get("component_id", "").strip()
			indicator_id = reuse_row.get("indicator_id", "").strip()
			if component_id and indicator_id:
				register_mapping(component_id, indicator_id, base_row, reuse_row)
		return reverse_lookup

	if {
		"template_group",
		"applies_to_component_pattern",
		"component_block_rule",
		"local_slot_source",
		"indicator_id_format",
	}.issubset(reuse_headers):
		if component_block_rule_table is None:
			return reverse_lookup
		component_block_lookup = resolve_component_block_lookup(list(component_block_rule_table["rows"]))
		for reuse_row in reuse_rows:
			template_group = reuse_row.get("template_group", "").strip()
			component_pattern = reuse_row.get("applies_to_component_pattern", "").strip()
			block_rule_id = reuse_row.get("component_block_rule", "").strip()
			local_slot_source = reuse_row.get("local_slot_source", "").strip()
			indicator_id_format = reuse_row.get("indicator_id_format", "").strip()
			matching_base_rows = [
				row for row in base_rows if row.get("template_id", "").strip().startswith(f"{template_group}_")
			]
			for component_id, template_values in expand_component_pattern(component_pattern):
				component_block = component_block_lookup.get((block_rule_id, component_id))
				if component_block is None:
					continue
				for base_row in matching_base_rows:
					expression_values = {
						**template_values,
						**resolve_local_slot_values(base_row, local_slot_source),
						"component_block": component_block,
					}
					indicator_id = apply_expression_template(indicator_id_format, expression_values)
					register_mapping(component_id, indicator_id, base_row, reuse_row)
		return reverse_lookup

	if {"template_group", "applies_to_component_pattern", "indicator_id_rule"}.issubset(reuse_headers):
		for reuse_row in reuse_rows:
			template_group = reuse_row.get("template_group", "").strip()
			component_pattern = reuse_row.get("applies_to_component_pattern", "").strip()
			indicator_id_template = extract_rule_template(reuse_row.get("indicator_id_rule", "").strip())
			matching_base_rows = [
				row for row in base_rows if row.get("template_id", "").strip().startswith(f"{template_group}_")
			]
			for component_id, template_values in expand_component_pattern(component_pattern):
				for base_row in matching_base_rows:
					indicator_id = apply_token_template(
						indicator_id_template,
						{**template_values, "local_slot": base_row.get("local_slot", "").strip()},
					)
					register_mapping(component_id, indicator_id, base_row, reuse_row)
	return reverse_lookup


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


def base_table_sort_key(row: list[str]) -> tuple[int, str, str]:
	template_id = row[0]
	template_id_lower = template_id.lower()
	if "_core_" in template_id_lower:
		group_rank = 0
	elif "_adv_" in template_id_lower:
		group_rank = 1
	else:
		group_rank = 2
	return (group_rank, template_id_lower, row[1].lower())


def is_positive_scored_row(row: dict[str, str]) -> bool:
	status = (row.get("evidence_status") or "").strip().lower()
	return status in POSITIVE_EVIDENCE_STATUS_VALUES


def render_consolidated_scoring_stats_document(
	component_ids: list[str],
	scored_csv_paths: list[Path],
	total_scored_rows: int,
	indicator_rows: list[list[str]],
	base_rows: list[list[str]],
) -> str:
	component_label = component_ids[0] if len(component_ids) == 1 else ", ".join(component_ids)
	source_csv_label = "\n".join(str(path) for path in scored_csv_paths)
	parts = [
		f"## {derive_output_filename(component_ids).removesuffix('.md')}",
		"",
		"Saturation rate is defined here as number_scored_positive divided by number_scored for each indicator.",
		"",
		render_markdown_table(
			["metric", "value"],
			[
				["component_ids", component_label],
				["source_scored_csvs", source_csv_label],
				["total_scored_rows", str(total_scored_rows)],
				["positive_evidence_status_values", ", ".join(sorted(POSITIVE_EVIDENCE_STATUS_VALUES))],
			],
		),
		"",
		"### Indicator saturation, all",
		"",
		render_markdown_table(
			[
				"component_id",
				"indicator_id",
				"sbo_short_description",
				"saturation_rate",
				"number_scored",
				"number_scored_positive",
			],
			indicator_rows,
		),
		"",
		"### Indicator saturation, base",
		"",
		render_markdown_table(
			[
				"template_id",
				"local_slot",
				"sbo_short_description",
				"expansion_mode",
				"saturation_rate",
				"number_scored",
				"number_scored_positive",
			],
			base_rows,
		),
		"",
	]
	return "\n".join(parts)


def main() -> int:
	args = parse_args()
	registry_path = args.indicator_registry.resolve()
	manifest_path = args.sbo_manifest_file.resolve()
	component_ids = [component_id.strip() for component_id in args.component_id if component_id.strip()]
	scored_csv_paths = [path.resolve() for path in args.file_with_scored_texts]
	output_dir = args.output_dir.resolve() if args.output_dir else manifest_path.parent / RUNNER_OUTPUT_SUBDIR

	if not component_ids:
		print("Error: at least one --component-id value is required.", file=sys.stderr)
		return 1
	if len(component_ids) != len(scored_csv_paths):
		print(
			"Error: --component-id and --file-with-scored-texts must be provided the same number of times.",
			file=sys.stderr,
		)
		return 1

	if not registry_path.exists() or not registry_path.is_file():
		print(f"Error: indicator registry file not found: {registry_path}", file=sys.stderr)
		return 1
	if not manifest_path.exists() or not manifest_path.is_file():
		print(f"Error: markdown file not found: {manifest_path}", file=sys.stderr)
		return 1
	for scored_csv_path in scored_csv_paths:
		if not scored_csv_path.exists() or not scored_csv_path.is_file():
			print(f"Error: scored-texts file not found: {scored_csv_path}", file=sys.stderr)
			return 1

	output_dir.mkdir(parents=True, exist_ok=True)
	base_row_reverse_lookup = build_base_row_reverse_lookup(registry_path)
	scored_rows_by_component = {
		component_id: load_scored_rows(scored_csv_path)
		for component_id, scored_csv_path in zip(component_ids, scored_csv_paths)
	}
	total_scored_rows = sum(len(rows) for rows in scored_rows_by_component.values())
	lines = manifest_path.read_text(encoding="utf-8").splitlines()
	indicator_summary_rows: dict[str, list[str]] = {}
	base_summary_rows: dict[str, list[str | int]] = {}

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

			matching_component_id = next((component_id for component_id in component_ids if component_id in row_line), None)
			if matching_component_id is not None:
				padded = row_cells + [""] * (len(header_cells) - len(row_cells))
				components = {header_cells[idx]: padded[idx] for idx in range(len(header_cells))}
				indicator_id = (components.get("indicator_id") or "").strip() or "<missing>"
				matching_scored_rows = find_matching_scored_rows(
					components,
					scored_rows_by_component[matching_component_id],
				)
				number_scored = len(matching_scored_rows)
				number_scored_positive = sum(1 for row in matching_scored_rows if is_positive_scored_row(row))
				indicator_summary_rows[f"{matching_component_id}::{indicator_id}"] = [
					matching_component_id,
					indicator_id,
					(components.get("sbo_short_description") or "").strip(),
					format_rate(number_scored_positive, number_scored),
					str(number_scored),
					str(number_scored_positive),
				]
				base_row_info = base_row_reverse_lookup.get((matching_component_id, indicator_id))
				if base_row_info is not None:
					base_key = base_row_info["template_id"]
					if base_key not in base_summary_rows:
						base_summary_rows[base_key] = [
							base_row_info["template_id"],
							base_row_info["local_slot"],
							base_row_info["sbo_short_description"],
							base_row_info["expansion_mode"],
							0,
							0,
						]
					base_summary_rows[base_key][4] = int(base_summary_rows[base_key][4]) + number_scored
					base_summary_rows[base_key][5] = int(base_summary_rows[base_key][5]) + number_scored_positive
			i += 1

	consolidated_indicator_rows = [indicator_summary_rows[key] for key in sorted(indicator_summary_rows)]
	consolidated_base_rows: list[list[str]] = []
	for key in sorted(base_summary_rows):
		template_id, local_slot, description, expansion_mode, number_scored, number_scored_positive = base_summary_rows[key]
		consolidated_base_rows.append(
			[
				str(template_id),
				str(local_slot),
				str(description),
				str(expansion_mode),
				format_rate(int(number_scored_positive), int(number_scored)),
				str(number_scored),
				str(number_scored_positive),
			]
		)
	consolidated_base_rows.sort(key=base_table_sort_key)
	consolidated_output_path = output_dir / derive_output_filename(component_ids)
	consolidated_output_path.write_text(
		render_consolidated_scoring_stats_document(
			component_ids=component_ids,
			scored_csv_paths=scored_csv_paths,
			total_scored_rows=total_scored_rows,
			indicator_rows=consolidated_indicator_rows,
			base_rows=consolidated_base_rows,
		),
		encoding="utf-8",
	)
	print(consolidated_output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())