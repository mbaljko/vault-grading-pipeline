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
4. A co-incidence matrix over Base Table `template_id` values, where each
	cell contains the count of positive scored submissions that
	appear in both the row and column template sets.
5. A second co-incidence matrix with the same structure, but each populated
	cell is expressed as a row-conditional percentage: the share of positive
	samples for the row template that were also positive for the column template.

Saturation rate definition:
- saturation_rate = number_scored_positive / number_scored

Output naming:
- Single-component run:
	I_<assignment>_<component_id>_output_scoring_stats_report_<iteration>.md
- Multi-component run:
	I_<assignment>_all_components_output_scoring_stats_report_<iteration>.md
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
ITERATION_RE = re.compile(r"\b(iter\d+)\b", re.IGNORECASE)
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
	parser.add_argument(
		"--iteration-label",
		type=str,
		required=False,
		help="Optional iteration label override, e.g. iter02.",
	)
	return parser.parse_args()


def derive_assignment_output_prefix(manifest_path: Path) -> str:
	match = re.match(r"^([A-Za-z0-9]+)_Layer1_", manifest_path.name)
	if not match:
		return "I"
	return f"I_{match.group(1)}"


def derive_iteration_label(input_path: Path, explicit_label: str | None) -> str:
	if explicit_label:
		return explicit_label.strip()
	for part in input_path.parts:
		match = ITERATION_RE.search(part)
		if match:
			return match.group(1).lower()
	match = ITERATION_RE.search(str(input_path))
	if match:
		return match.group(1).lower()
	return "iteration"


def derive_output_filename(component_ids: list[str], manifest_path: Path, iteration_label: str) -> str:
	prefix = derive_assignment_output_prefix(manifest_path)
	if len(component_ids) == 1:
		return f"{prefix}_{component_ids[0]}_output_scoring_stats_report_{iteration_label}.md"
	return f"{prefix}_all_components_output_scoring_stats_report_{iteration_label}.md"


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


def derive_unique_template_labels(template_ids: list[str]) -> dict[str, str]:
	tokenized_template_ids = {template_id: template_id.split("_") for template_id in template_ids}
	preferred_labels: dict[str, str] = {}
	preferred_counts: dict[str, int] = {}
	for template_id, tokens in tokenized_template_ids.items():
		if len(tokens) >= 2 and tokens[-2] in {"core", "adv"}:
			preferred_label = f"{tokens[-2]}_{tokens[-1]}"
			preferred_labels[template_id] = preferred_label
			preferred_counts[preferred_label] = preferred_counts.get(preferred_label, 0) + 1

	labels_by_template: dict[str, str] = {}
	for template_id, preferred_label in preferred_labels.items():
		if preferred_counts[preferred_label] == 1:
			labels_by_template[template_id] = preferred_label

	for width in range(1, max((len(tokens) for tokens in tokenized_template_ids.values()), default=0) + 1):
		candidate_labels: dict[str, str] = {}
		candidate_counts: dict[str, int] = {}
		for template_id, tokens in tokenized_template_ids.items():
			if template_id in labels_by_template:
				continue
			candidate_label = "_".join(tokens[-width:])
			candidate_labels[template_id] = candidate_label
			candidate_counts[candidate_label] = candidate_counts.get(candidate_label, 0) + 1
		for template_id, candidate_label in candidate_labels.items():
			if candidate_counts[candidate_label] == 1:
				labels_by_template[template_id] = candidate_label
	for template_id in template_ids:
		labels_by_template.setdefault(template_id, template_id)
	return labels_by_template


def build_coincidence_count_matrix(
	template_ids: list[str],
	positive_submission_ids_by_template: dict[str, set[str]],
) -> dict[str, dict[str, int]]:
	count_matrix: dict[str, dict[str, int]] = {}
	for row_template_id in template_ids:
		count_matrix[row_template_id] = {}
		row_submission_ids = positive_submission_ids_by_template.get(row_template_id, set())
		for column_template_id in template_ids:
			column_submission_ids = positive_submission_ids_by_template.get(column_template_id, set())
			count_matrix[row_template_id][column_template_id] = len(row_submission_ids & column_submission_ids)
	return count_matrix


def collapse_template_positive_submission_ids(
	positive_submission_ids_by_template_indicator: dict[str, dict[str, set[str]]],
	template_ids: list[str],
) -> dict[str, set[str]]:
	collapsed: dict[str, set[str]] = {}
	for template_id in template_ids:
		indicator_sets = list(positive_submission_ids_by_template_indicator.get(template_id, {}).values())
		if not indicator_sets:
			collapsed[template_id] = set()
			continue
		intersection = set(indicator_sets[0])
		for submission_ids in indicator_sets[1:]:
			intersection &= submission_ids
		collapsed[template_id] = intersection
	return collapsed


def render_coincidence_matrix(
	template_ids: list[str],
	positive_submission_ids_by_template: dict[str, set[str]],
	as_percentage: bool,
) -> str:
	labels_by_template = derive_unique_template_labels(template_ids)
	count_matrix = build_coincidence_count_matrix(template_ids, positive_submission_ids_by_template)
	headers = ["template", *[labels_by_template[template_id] for template_id in template_ids]]
	rows: list[list[str]] = []

	for row_template_id in template_ids:
		row_values = [labels_by_template[row_template_id]]
		row_denominator = len(positive_submission_ids_by_template.get(row_template_id, set()))
		for column_index, column_template_id in enumerate(template_ids):
			cell_count = count_matrix[row_template_id][column_template_id]
			if as_percentage:
				if template_ids[column_index] == row_template_id:
					row_values.append("-")
					continue
				row_values.append(format_rate(cell_count, row_denominator))
			else:
				row_values.append(str(cell_count))
		rows.append(row_values)
	return render_markdown_table(headers, rows)


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
	manifest_path: Path,
	iteration_label: str,
	scored_csv_paths: list[Path],
	total_scored_rows: int,
	indicator_rows: list[list[str]],
	base_rows: list[list[str]],
	coincidence_count_matrix: str,
	coincidence_percent_matrix: str,
) -> str:
	component_label = component_ids[0] if len(component_ids) == 1 else ", ".join(component_ids)
	source_csv_label = "\n".join(str(path) for path in scored_csv_paths)
	base_table_headers = [
		"template_id",
		"local_slot",
		"expanded_indicator_ids",
		"sbo_short_description",
		"saturation_rate",
		"number_scored",
		"number_scored_positive",
		*[f"saturation_rate_{component_id}" for component_id in component_ids],
	]
	parts = [
		f"## {derive_output_filename(component_ids, manifest_path, iteration_label).removesuffix('.md')}",
		"",
		"Saturation rate is defined here as number_scored_positive divided by number_scored for each indicator.",
		"Percent co-incidence values are row-conditional: each populated cell shows the share of positive samples for the row template that were also positive for the column template.",
		"Important: the Base Table saturation section and the co-incidence matrices use different counting semantics.",
		"The Base Table saturation section aggregates summed indicator-instance counts across the expanded indicators mapped to each template.",
		"The co-incidence matrices instead operate at the submission level: for a template, a submission counts as positive only if it is positive for every expanded indicator mapped to that template across the included components.",
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
		render_markdown_table(base_table_headers, base_rows),
		"",
		"### Co-incidence matrix",
		"",
		"Interpretation: each cell is a raw overlap count. For each template, a submission is counted as positive only if it is positive for every expanded indicator mapped to that template across the included components.",
		"For row template R and column template C, the number is the count of submissions that satisfy that template-level positive condition for both R and C.",
		"This count matrix is symmetric, so the value at (R, C) matches the value at (C, R).",
		"Diagonal cells are self-overlap counts, so they equal the number of positive submissions for that template.",
		"",
		coincidence_count_matrix,
		"",
		"### Co-incidence matrix, row-conditional percent",
		"",
		"Interpretation: each cell is directional. Template-level positivity again means a submission is positive for every expanded indicator mapped to that template across the included components.",
		"For a row template R and column template C, the value is the percentage of submissions positive for R that were also positive for C.",
		"This percent matrix is not generally symmetric: the value at (R, C) need not match the value at (C, R).",
		"Diagonal cells are 100% when the row template has at least one positive sample, because every positive sample for R overlaps with itself.",
		"",
		coincidence_percent_matrix,
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
	iteration_label = derive_iteration_label(manifest_path, args.iteration_label)

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
	base_summary_rows: dict[str, dict[str, object]] = {}
	positive_submission_ids_by_template_indicator: dict[str, dict[str, set[str]]] = {}

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
					template_indicator_key = f"{matching_component_id}::{indicator_id}"
					if base_key not in base_summary_rows:
						base_summary_rows[base_key] = {
							"template_id": base_row_info["template_id"],
							"local_slot": base_row_info["local_slot"],
							"expanded_indicator_ids": set(),
							"sbo_short_description": base_row_info["sbo_short_description"],
							"expansion_mode": base_row_info["expansion_mode"],
							"number_scored": 0,
							"number_scored_positive": 0,
							"per_component_counts": {
								component_id: {"number_scored": 0, "number_scored_positive": 0}
								for component_id in component_ids
							},
						}
						positive_submission_ids_by_template_indicator[base_key] = {}
					positive_submission_ids_by_template_indicator[base_key].setdefault(template_indicator_key, set())
					base_summary_rows[base_key]["expanded_indicator_ids"].add(indicator_id)
					base_summary_rows[base_key]["number_scored"] = int(base_summary_rows[base_key]["number_scored"]) + number_scored
					base_summary_rows[base_key]["number_scored_positive"] = int(base_summary_rows[base_key]["number_scored_positive"]) + number_scored_positive
					component_counts = base_summary_rows[base_key]["per_component_counts"]
					component_counts[matching_component_id]["number_scored"] += number_scored
					component_counts[matching_component_id]["number_scored_positive"] += number_scored_positive
					for row in matching_scored_rows:
						if not is_positive_scored_row(row):
							continue
						submission_id = (row.get("submission_id") or "").strip()
						if submission_id:
							positive_submission_ids_by_template_indicator[base_key][template_indicator_key].add(submission_id)
			i += 1

	consolidated_indicator_rows = [indicator_summary_rows[key] for key in sorted(indicator_summary_rows)]
	consolidated_base_rows: list[list[str]] = []
	for key in sorted(base_summary_rows):
		base_row = base_summary_rows[key]
		template_id = str(base_row["template_id"])
		local_slot = str(base_row["local_slot"])
		expanded_indicator_ids = ", ".join(sorted(base_row["expanded_indicator_ids"]))
		description = str(base_row["sbo_short_description"])
		number_scored = int(base_row["number_scored"])
		number_scored_positive = int(base_row["number_scored_positive"])
		component_rate_columns = []
		for component_id in component_ids:
			component_counts = base_row["per_component_counts"][component_id]
			component_rate_columns.append(
				format_rate(component_counts["number_scored_positive"], component_counts["number_scored"])
			)
		consolidated_base_rows.append(
			[
				template_id,
				local_slot,
				expanded_indicator_ids,
				description,
				format_rate(number_scored_positive, number_scored),
				str(number_scored),
				str(number_scored_positive),
				*component_rate_columns,
			]
		)
	consolidated_base_rows.sort(key=base_table_sort_key)
	ordered_template_ids = [row[0] for row in consolidated_base_rows]
	positive_submission_ids_by_template = collapse_template_positive_submission_ids(
		positive_submission_ids_by_template_indicator,
		ordered_template_ids,
	)
	coincidence_count_matrix = render_coincidence_matrix(
		ordered_template_ids,
		positive_submission_ids_by_template,
		False,
	)
	coincidence_percent_matrix = render_coincidence_matrix(
		ordered_template_ids,
		positive_submission_ids_by_template,
		True,
	)
	consolidated_output_path = output_dir / derive_output_filename(component_ids, manifest_path, iteration_label)
	consolidated_output_path.write_text(
		render_consolidated_scoring_stats_document(
			component_ids=component_ids,
			manifest_path=manifest_path,
			iteration_label=iteration_label,
			scored_csv_paths=scored_csv_paths,
			total_scored_rows=total_scored_rows,
			indicator_rows=consolidated_indicator_rows,
			base_rows=consolidated_base_rows,
			coincidence_count_matrix=coincidence_count_matrix,
			coincidence_percent_matrix=coincidence_percent_matrix,
		),
		encoding="utf-8",
	)
	print(consolidated_output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())