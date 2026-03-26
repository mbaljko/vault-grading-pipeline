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
from datetime import datetime, timezone
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
SCORING_OUTPUT_VERSION_RE = re.compile(r"_v(\d+)(?=_)")
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
	parser.add_argument(
		"--sample-size",
		type=int,
		required=False,
		default=30,
		help="Sample size denominator used for stability diagnostics. Defaults to 30.",
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


def derive_previous_iteration_label(iteration_label: str) -> str | None:
	match = re.fullmatch(r"iter(\d+)", iteration_label.strip().lower())
	if not match:
		return None
	iteration_number = int(match.group(1))
	if iteration_number <= 0:
		return None
	return f"iter{iteration_number - 1:0{len(match.group(1))}d}"


def derive_iteration_history_labels(iteration_label: str) -> list[str]:
	match = re.fullmatch(r"iter(\d+)", iteration_label.strip().lower())
	if not match:
		return [iteration_label]
	iteration_digits = match.group(1)
	iteration_number = int(iteration_digits)
	if iteration_number <= 0:
		return [iteration_label]
	return [f"iter{index:0{len(iteration_digits)}d}" for index in range(1, iteration_number + 1)]


def derive_delta_column_label(previous_iteration_label: str, current_iteration_label: str) -> str:
	previous_match = re.fullmatch(r"iter(\d+)", previous_iteration_label.strip().lower())
	current_match = re.fullmatch(r"iter(\d+)", current_iteration_label.strip().lower())
	if previous_match and current_match:
		return f"delta{previous_match.group(1)}-{current_match.group(1)}"
	return f"delta {previous_iteration_label}-{current_iteration_label}"


def build_delta_table_headers(iteration_history_labels: list[str]) -> list[str]:
	headers = ["indicator", *iteration_history_labels]
	for previous_iteration_label, current_iteration_label in zip(iteration_history_labels, iteration_history_labels[1:]):
		headers.extend(
			[
				".",
				derive_delta_column_label(previous_iteration_label, current_iteration_label),
				"-high",
				"-med",
				"-low",
				"stable",
				"+low",
				"+mod",
				"+high",
			]
		)
	return headers


def derive_target_version_label(current_iteration_label: str, target_iteration_label: str) -> str | None:
	current_match = re.fullmatch(r"iter(\d+)", current_iteration_label.strip().lower())
	target_match = re.fullmatch(r"iter(\d+)", target_iteration_label.strip().lower())
	if current_match is None or target_match is None:
		return None
	return f"{int(target_match.group(1)):0{len(current_match.group(1))}d}"


def remap_scored_input_ref_for_iteration(
	input_ref: Path,
	current_iteration_label: str,
	target_iteration_label: str,
) -> Path:
	if target_iteration_label == current_iteration_label:
		return input_ref
	current_label = current_iteration_label.strip().lower()
	target_label = target_iteration_label.strip().lower()
	current_text = str(input_ref)
	target_text = current_text.replace(f"/{current_label}/", f"/{target_label}/")
	target_ref = Path(target_text)
	target_version = derive_target_version_label(current_iteration_label, target_iteration_label)
	if target_version is None:
		return target_ref
	updated_name = SCORING_OUTPUT_VERSION_RE.sub(f"_v{target_version}", target_ref.name, count=1)
	if updated_name == target_ref.name:
		return target_ref
	return target_ref.with_name(updated_name)


def derive_expected_version_label(input_ref: Path, iteration_label: str | None = None) -> str | None:
	version_match = SCORING_OUTPUT_VERSION_RE.search(input_ref.name)
	if version_match is not None:
		return version_match.group(1)
	if iteration_label is None:
		return None
	iteration_match = re.fullmatch(r"iter(\d+)", iteration_label.strip().lower())
	if iteration_match is None:
		return None
	return iteration_match.group(1)


def discover_component_py_scored_csv_paths_in_dir(
	directory: Path,
	component_id: str,
	expected_version_label: str | None = None,
) -> list[Path]:
	if not directory.exists() or not directory.is_dir():
		return []
	if expected_version_label:
		pattern = f"*{component_id}*_Layer1_SBO_scoring_prompt_py_v{expected_version_label}_*_output_output.csv"
	else:
		pattern = f"*{component_id}*_Layer1_SBO_scoring_prompt_py_v*_*_output_output.csv"
	return sorted(
		candidate_path
		for candidate_path in directory.glob(pattern)
		if candidate_path.is_file()
	)


def discover_component_legacy_scored_csv_paths_in_dir(directory: Path, component_id: str) -> list[Path]:
	if not directory.exists() or not directory.is_dir():
		return []
	exact_matches = sorted(
		candidate_path
		for candidate_path in directory.glob(f"*{component_id}*_Layer1_SBO_scoring_prompt_v*_output.csv")
		if candidate_path.is_file()
	)
	if exact_matches:
		return exact_matches
	duplicated_suffix_matches = sorted(
		candidate_path
		for candidate_path in directory.glob(f"*{component_id}*_Layer1_SBO_scoring_prompt_v*_output_output.csv")
		if candidate_path.is_file()
	)
	if duplicated_suffix_matches:
		return duplicated_suffix_matches
	return []


def discover_component_scored_csv_paths_in_dir(
	directory: Path,
	component_id: str,
	expected_version_label: str | None = None,
) -> list[Path]:
	py_matches = discover_component_py_scored_csv_paths_in_dir(directory, component_id, expected_version_label)
	if py_matches:
		return py_matches
	legacy_matches = discover_component_legacy_scored_csv_paths_in_dir(directory, component_id)
	if legacy_matches:
		return legacy_matches
	return sorted(
		candidate_path for candidate_path in directory.glob(f"*{component_id}*output*.csv") if candidate_path.is_file()
	)


def resolve_component_scored_csv_paths(
	input_ref: Path,
	component_id: str,
	expected_version_label: str | None = None,
) -> list[Path]:
	if input_ref.exists():
		if input_ref.is_dir():
			return discover_component_scored_csv_paths_in_dir(input_ref, component_id, expected_version_label)
		if input_ref.is_file():
			py_matches = discover_component_py_scored_csv_paths_in_dir(
				input_ref.parent,
				component_id,
				expected_version_label or derive_expected_version_label(input_ref),
			)
			if py_matches and input_ref in py_matches:
				return py_matches
			return [input_ref]

	parent_dir = input_ref.parent
	if not parent_dir.exists() or not parent_dir.is_dir():
		return []

	legacy_duplicate = parent_dir / input_ref.name.replace("_output.csv", "_output_output.csv")
	if legacy_duplicate.name != input_ref.name and legacy_duplicate.exists() and legacy_duplicate.is_file():
		return [legacy_duplicate]

	return discover_component_scored_csv_paths_in_dir(parent_dir, component_id, expected_version_label)


def derive_scored_csv_paths_for_iteration(
	current_input_ref: Path,
	component_id: str,
	current_iteration_label: str,
	target_iteration_label: str,
) -> list[Path]:
	target_input_ref = remap_scored_input_ref_for_iteration(
		current_input_ref,
		current_iteration_label,
		target_iteration_label,
	)
	return resolve_component_scored_csv_paths(
		target_input_ref,
		component_id,
		derive_expected_version_label(target_input_ref, target_iteration_label),
	)


def load_scored_rows_from_paths(input_paths: list[Path]) -> list[dict[str, str]]:
	rows: list[dict[str, str]] = []
	for input_path in input_paths:
		rows.extend(load_scored_rows(input_path))
	return rows


def summarize_score_value(evidence_status: str) -> str:
	normalized = evidence_status.strip().lower()
	if normalized == "present":
		return "P"
	if normalized == "not_present":
		return "N"
	return evidence_status.strip()


def build_variance_bucket_cells(delta: int, variance_rate: float) -> list[str]:
	formatted_rate = f"{variance_rate:.3f}"
	buckets = {
		"-high": "",
		"-med": "",
		"-low": "",
		"stable": "",
		"+low": "",
		"+mod": "",
		"+high": "",
	}
	if delta == 0:
		buckets["stable"] = formatted_rate
	elif delta < 0:
		if variance_rate <= 0.05:
			buckets["-low"] = formatted_rate
		elif variance_rate <= 0.10:
			buckets["-med"] = formatted_rate
		else:
			buckets["-high"] = formatted_rate
	else:
		if variance_rate <= 0.05:
			buckets["+low"] = formatted_rate
		elif variance_rate <= 0.10:
			buckets["+mod"] = formatted_rate
		else:
			buckets["+high"] = formatted_rate
	return [
		buckets["-high"],
		buckets["-med"],
		buckets["-low"],
		buckets["stable"],
		buckets["+low"],
		buckets["+mod"],
		buckets["+high"],
	]


def indicator_sort_key(indicator_id: str) -> tuple[int, str]:
	match = re.fullmatch(r"[A-Za-z]+(\d+)", indicator_id)
	if match:
		return (int(match.group(1)), indicator_id)
	return (10**9, indicator_id)


def build_indicator_counts_by_iteration(
	component_ids: list[str],
	iteration_history_labels: list[str],
	historical_rows_by_iteration: dict[str, dict[str, list[dict[str, str]]]],
) -> dict[str, dict[str, dict[str, int]]]:
	counts_by_indicator: dict[str, dict[str, dict[str, int]]] = {}
	for iteration_history_label in iteration_history_labels:
		for component_id in component_ids:
			for row in historical_rows_by_iteration.get(iteration_history_label, {}).get(component_id, []):
				indicator_id = (row.get("indicator_id") or "").strip()
				if not indicator_id:
					continue
				counts_by_indicator.setdefault(indicator_id, {})
				counts_by_indicator[indicator_id].setdefault(
					iteration_history_label,
					{"positive": 0, "number_scored": 0},
				)
				counts_by_indicator[indicator_id][iteration_history_label]["number_scored"] += 1
				if is_positive_scored_row(row):
					counts_by_indicator[indicator_id][iteration_history_label]["positive"] += 1
	return counts_by_indicator


def classify_variance_rate(variance_rate: float) -> str:
	if variance_rate == 0:
		return "stable"
	if variance_rate > 0 and variance_rate < 0.05:
		return "low_variance"
	if variance_rate >= 0.05 and variance_rate <= 0.10:
		return "borderline_unstable"
	return "unstable"


def build_indicator_stability_sections(
	iteration_history_labels: list[str],
	counts_by_indicator: dict[str, dict[str, dict[str, int]]],
	sample_size: int,
) -> tuple[list[str], dict[str, list[list[str]]]]:
	if len(iteration_history_labels) < 3:
		return ([], {})
	stability_iteration_labels = iteration_history_labels[-3:]
	classification_rows: dict[str, list[list[str]]] = {
		"stable": [],
		"low_variance": [],
		"borderline_unstable": [],
		"unstable": [],
	}
	denominator = sample_size if sample_size > 0 else 1
	for indicator_id in sorted(counts_by_indicator, key=indicator_sort_key):
		iteration_counts = [
			counts_by_indicator[indicator_id].get(iteration_label, {}).get("positive", 0)
			for iteration_label in stability_iteration_labels
		]
		iter01_count, iter02_count, iter03_count = iteration_counts
		delta_12 = abs(iter02_count - iter01_count)
		delta_23 = abs(iter03_count - iter02_count)
		max_delta = max(delta_12, delta_23)
		variance_rate = max_delta / denominator
		signed_delta_12 = iter02_count - iter01_count
		signed_delta_23 = iter03_count - iter02_count
		range_delta = max(iter01_count, iter02_count, iter03_count) - min(iter01_count, iter02_count, iter03_count)
		range_rate = range_delta / denominator
		classification = classify_variance_rate(variance_rate)
		classification_rows[classification].append(
			[
				indicator_id,
				str(iter01_count),
				str(iter02_count),
				str(iter03_count),
				str(delta_12),
				str(delta_23),
				str(max_delta),
				f"{variance_rate:.3f}",
				f"{signed_delta_12:+d}",
				f"{signed_delta_23:+d}",
				str(range_delta),
				f"{range_rate:.3f}",
			]
		)
	return (stability_iteration_labels, classification_rows)


def quote_yaml_string(value: str) -> str:
	escaped = value.replace("\\", "\\\\").replace('"', '\\"')
	return f'"{escaped}"'


def render_yaml_frontmatter(
	output_path: Path,
	iteration_label: str,
	manifest_path: Path,
	registry_path: Path,
	component_ids: list[str],
	scored_csv_paths: list[Path],
) -> str:
	lines = [
		"---\n",
		f"generated_at_utc: {quote_yaml_string(datetime.now(timezone.utc).isoformat(timespec='seconds'))}\n",
		"generator:\n",
		f"  script: {quote_yaml_string(str(Path(__file__).resolve()))}\n",
		"output_file:\n",
		f"  path: {quote_yaml_string(str(output_path))}\n",
		f"  name: {quote_yaml_string(output_path.name)}\n",
		f"iteration_label: {quote_yaml_string(iteration_label)}\n",
		"manifest_input:\n",
		f"  path: {quote_yaml_string(str(manifest_path))}\n",
		"indicator_registry:\n",
		f"  path: {quote_yaml_string(str(registry_path))}\n",
		"component_ids:\n",
	]
	for component_id in component_ids:
		lines.append(f"  - {quote_yaml_string(component_id)}\n")
	lines.append("scored_csv_paths:\n")
	for scored_csv_path in scored_csv_paths:
		lines.append(f"  - {quote_yaml_string(str(scored_csv_path))}\n")
	lines.append("---\n")
	return "".join(lines)


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
				normalized_key = key.strip().lstrip("\ufeff")
				normalized_row[normalized_key] = (value or "").strip()
			rows.append(normalized_row)
	return rows


def build_iteration_diff_rows(
	component_ids: list[str],
	current_rows_by_component: dict[str, list[dict[str, str]]],
	previous_rows_by_component: dict[str, list[dict[str, str]]],
	previous_iteration_label: str,
	current_iteration_label: str,
) -> tuple[list[list[str]], list[list[str]], list[list[str]]]:
	added_rows: list[list[str]] = []
	removed_rows: list[list[str]] = []
	changed_rows: list[list[str]] = []
	for component_id in component_ids:
		current_rows = current_rows_by_component.get(component_id, [])
		previous_rows = previous_rows_by_component.get(component_id, [])
		current_index = {
			(
				(row.get("indicator_id") or "").strip(),
				(row.get("submission_id") or "").strip(),
			): row
			for row in current_rows
			if (row.get("indicator_id") or "").strip() and (row.get("submission_id") or "").strip()
		}
		previous_index = {
			(
				(row.get("indicator_id") or "").strip(),
				(row.get("submission_id") or "").strip(),
			): row
			for row in previous_rows
			if (row.get("indicator_id") or "").strip() and (row.get("submission_id") or "").strip()
		}
		for row in current_rows:
			indicator_id = (row.get("indicator_id") or "").strip()
			submission_id = (row.get("submission_id") or "").strip()
			if not indicator_id or not submission_id:
				continue
			previous_row = previous_index.get((indicator_id, submission_id))
			if previous_row is None:
				added_rows.append(
					[
						component_id,
						indicator_id,
						submission_id,
						summarize_score_value(row.get("evidence_status") or ""),
					]
				)
				continue
			current_score = summarize_score_value(row.get("evidence_status") or "")
			previous_score = summarize_score_value(previous_row.get("evidence_status") or "")
			if current_score == previous_score:
				continue
			changed_rows.append(
				[
					component_id,
					indicator_id,
					submission_id,
					previous_score,
					current_score,
				]
			)
		for row in previous_rows:
			indicator_id = (row.get("indicator_id") or "").strip()
			submission_id = (row.get("submission_id") or "").strip()
			if not indicator_id or not submission_id:
				continue
			if (indicator_id, submission_id) in current_index:
				continue
			removed_rows.append(
				[
					component_id,
					indicator_id,
					submission_id,
					summarize_score_value(row.get("evidence_status") or ""),
				]
			)
	return (
		sorted(added_rows, key=lambda row: (row[0], row[1], row[2], row[3])),
		sorted(removed_rows, key=lambda row: (row[0], row[1], row[2], row[3])),
		sorted(changed_rows, key=lambda row: (row[0], row[1], row[2], row[3], row[4])),
	)


def build_changed_score_history_rows(
	changed_diff_rows: list[list[str]],
	iteration_history_labels: list[str],
	historical_rows_by_iteration: dict[str, dict[str, list[dict[str, str]]]],
) -> list[list[str]]:
	indexes_by_iteration: dict[str, dict[str, dict[tuple[str, str], dict[str, str]]]] = {}
	for iteration_label in iteration_history_labels:
		component_indexes: dict[str, dict[tuple[str, str], dict[str, str]]] = {}
		for component_id, rows in historical_rows_by_iteration.get(iteration_label, {}).items():
			component_indexes[component_id] = {
				(
					(row.get("indicator_id") or "").strip(),
					(row.get("submission_id") or "").strip(),
				): row
				for row in rows
				if (row.get("indicator_id") or "").strip() and (row.get("submission_id") or "").strip()
			}
		indexes_by_iteration[iteration_label] = component_indexes

	history_rows: list[list[str]] = []
	for changed_row in changed_diff_rows:
		component_id, indicator_id, submission_id = changed_row[:3]
		row_values = [component_id, indicator_id, submission_id]
		for iteration_label in iteration_history_labels:
			row = indexes_by_iteration.get(iteration_label, {}).get(component_id, {}).get((indicator_id, submission_id))
			row_values.append(summarize_score_value(row.get("evidence_status") or "") if row is not None else "")
		history_rows.append(row_values)
	return history_rows


def build_indicator_delta_rows(
	component_ids: list[str],
	iteration_history_labels: list[str],
	historical_rows_by_iteration: dict[str, dict[str, list[dict[str, str]]]],
) -> list[list[str]]:
	counts_by_indicator = build_indicator_counts_by_iteration(
		component_ids,
		iteration_history_labels,
		historical_rows_by_iteration,
	)

	rows: list[list[str]] = []
	for indicator_id in sorted(counts_by_indicator, key=indicator_sort_key):
		row = [indicator_id]
		positive_counts_by_iteration = {
			iteration_history_label: counts_by_indicator[indicator_id].get(iteration_history_label, {}).get("positive", 0)
			for iteration_history_label in iteration_history_labels
		}
		row.extend(str(positive_counts_by_iteration[iteration_history_label]) for iteration_history_label in iteration_history_labels)
		for previous_iteration_label, current_iteration_label in zip(iteration_history_labels, iteration_history_labels[1:]):
			previous_count = positive_counts_by_iteration[previous_iteration_label]
			current_count = positive_counts_by_iteration[current_iteration_label]
			number_scored = counts_by_indicator[indicator_id].get(current_iteration_label, {}).get("number_scored", 0)
			delta = current_count - previous_count
			absolute_delta = abs(delta)
			variance_rate = absolute_delta / number_scored if number_scored > 0 else 0.0
			row.extend([
				"",
				f"{delta:+d}",
				*build_variance_bucket_cells(delta, variance_rate),
			])
		rows.append(row)
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
	output_path: Path,
	registry_path: Path,
	component_ids: list[str],
	manifest_path: Path,
	iteration_label: str,
	iteration_history_labels: list[str],
	previous_iteration_label: str | None,
	sample_size: int,
	scored_csv_paths: list[Path],
	total_scored_rows: int,
	indicator_delta_rows: list[list[str]],
	stability_iteration_labels: list[str],
	stability_sections: dict[str, list[list[str]]],
	added_diff_rows: list[list[str]],
	removed_diff_rows: list[list[str]],
	changed_score_history_rows: list[list[str]],
	missing_previous_components: list[str],
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
	delta_table_headers = build_delta_table_headers(iteration_history_labels)
	parts = [
		render_yaml_frontmatter(output_path, iteration_label, manifest_path, registry_path, component_ids, scored_csv_paths),
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
	diff_report_parts = ["### Diff Report", ""]
	if previous_iteration_label is None:
		diff_report_parts.extend(["Previous iteration could not be derived from the current iteration label.", ""])
	else:
		diff_report_parts.extend(
			[
			f"Current iteration: {iteration_label}",
			f"Previous iteration: {previous_iteration_label}",
			]
		)
		if missing_previous_components:
			diff_report_parts.append(
				"Previous iteration scored CSVs were not found for: " + ", ".join(sorted(missing_previous_components))
			)
		if added_diff_rows:
			diff_report_parts.extend(
				[
					"",
					"#### Added Rows",
					"",
					render_markdown_table(
						[
							"component_id",
							"indicator_id",
							"submission_id",
							f"{iteration_label}-score",
						],
						added_diff_rows,
					),
				]
			)
		else:
			diff_report_parts.extend(["", "#### Added Rows", "", "No added rows found relative to the previous iteration."])
		if removed_diff_rows:
			diff_report_parts.extend(
				[
					"",
					"#### Removed Rows",
					"",
					render_markdown_table(
						[
							"component_id",
							"indicator_id",
							"submission_id",
							f"{previous_iteration_label}-score",
						],
						removed_diff_rows,
					),
				]
			)
		else:
			diff_report_parts.extend(["", "#### Removed Rows", "", "No removed rows found relative to the previous iteration."])
		if changed_score_history_rows:
			diff_report_parts.extend(
				[
					"",
					"#### Changed Scores",
					"",
					render_markdown_table(
						[
							"component_id",
							"indicator_id",
							"submission_id",
							*[f"{history_iteration_label}-score" for history_iteration_label in iteration_history_labels],
						],
						changed_score_history_rows,
					),
				]
			)
		else:
			diff_report_parts.extend(["", "#### Changed Scores", "", "No score changes found between the current and previous iteration."])
		diff_report_parts.extend(
			[
				"",
				"#### Delta Table",
				"",
				render_markdown_table(
					delta_table_headers,
					indicator_delta_rows,
				),
			]
		)
		diff_report_parts.extend(["", "#### Stability Flags", ""])
		if len(stability_iteration_labels) < 3:
			diff_report_parts.extend(
				[
					f"At least three iterations are required to compute stability flags; available iterations: {', '.join(iteration_history_labels)}.",
				]
			)
		else:
			stability_headers = [
				"indicator",
				stability_iteration_labels[0],
				stability_iteration_labels[1],
				stability_iteration_labels[2],
				"delta_12",
				"delta_23",
				"max_delta",
				"variance_rate",
				"signed_delta_12",
				"signed_delta_23",
				"range_delta",
				"range_rate",
			]
			diff_report_parts.extend(
				[
					f"sample_size: {sample_size}",
					f"Iterations used: {', '.join(stability_iteration_labels)}",
				]
			)
			for classification in ["stable", "low_variance", "borderline_unstable", "unstable"]:
				diff_report_parts.extend(["", f"##### {classification}", ""])
				rows = stability_sections.get(classification, [])
				if rows:
					diff_report_parts.append(render_markdown_table(stability_headers, rows))
				else:
					diff_report_parts.append("No indicators.")
	diff_report_parts.append("")
	parts.extend(diff_report_parts)
	return "\n".join(parts)


def main() -> int:
	args = parse_args()
	registry_path = args.indicator_registry.resolve()
	manifest_path = args.sbo_manifest_file.resolve()
	component_ids = [component_id.strip() for component_id in args.component_id if component_id.strip()]
	scored_csv_input_refs = [path.resolve(strict=False) for path in args.file_with_scored_texts]
	output_dir = args.output_dir.resolve() if args.output_dir else manifest_path.parent / RUNNER_OUTPUT_SUBDIR
	iteration_label = derive_iteration_label(manifest_path, args.iteration_label)
	sample_size = args.sample_size

	if not component_ids:
		print("Error: at least one --component-id value is required.", file=sys.stderr)
		return 1
	if len(component_ids) != len(scored_csv_input_refs):
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

	component_scored_csv_paths: dict[str, list[Path]] = {}
	missing_scored_inputs: list[str] = []
	for component_id, input_ref in zip(component_ids, scored_csv_input_refs):
		resolved_paths = resolve_component_scored_csv_paths(
			input_ref,
			component_id,
			derive_expected_version_label(input_ref, iteration_label),
		)
		if not resolved_paths:
			missing_scored_inputs.append(f"{component_id}: {input_ref}")
			continue
		component_scored_csv_paths[component_id] = resolved_paths
	if missing_scored_inputs:
		print(
			"Error: scored-text inputs could not be resolved for: " + "; ".join(missing_scored_inputs),
			file=sys.stderr,
		)
		return 1
	scored_csv_paths = [
		resolved_path
		for component_id in component_ids
		for resolved_path in component_scored_csv_paths.get(component_id, [])
	]

	output_dir.mkdir(parents=True, exist_ok=True)
	base_row_reverse_lookup = build_base_row_reverse_lookup(registry_path)
	scored_rows_by_component = {
		component_id: load_scored_rows_from_paths(component_scored_csv_paths[component_id])
		for component_id in component_ids
	}
	iteration_history_labels = derive_iteration_history_labels(iteration_label)
	historical_rows_by_iteration: dict[str, dict[str, list[dict[str, str]]]] = {
		iteration_label: dict(scored_rows_by_component)
	}
	for history_iteration_label in iteration_history_labels:
		if history_iteration_label == iteration_label:
			continue
		historical_rows_by_iteration[history_iteration_label] = {}
		for component_id, scored_csv_input_ref in zip(component_ids, scored_csv_input_refs):
			history_scored_csv_paths = derive_scored_csv_paths_for_iteration(
				scored_csv_input_ref,
				component_id,
				iteration_label,
				history_iteration_label,
			)
			if not history_scored_csv_paths:
				continue
			historical_rows_by_iteration[history_iteration_label][component_id] = load_scored_rows_from_paths(
				history_scored_csv_paths
			)
	previous_iteration_label = derive_previous_iteration_label(iteration_label)
	previous_rows_by_component: dict[str, list[dict[str, str]]] = {}
	missing_previous_components: list[str] = []
	if previous_iteration_label is not None:
		for component_id, scored_csv_input_ref in zip(component_ids, scored_csv_input_refs):
			previous_scored_csv_paths = derive_scored_csv_paths_for_iteration(
				scored_csv_input_ref,
				component_id,
				iteration_label,
				previous_iteration_label,
			)
			if not previous_scored_csv_paths:
				missing_previous_components.append(component_id)
				continue
			previous_rows_by_component[component_id] = load_scored_rows_from_paths(previous_scored_csv_paths)
	indicator_delta_rows = build_indicator_delta_rows(
		component_ids,
		iteration_history_labels,
		historical_rows_by_iteration,
	)
	counts_by_indicator = build_indicator_counts_by_iteration(
		component_ids,
		iteration_history_labels,
		historical_rows_by_iteration,
	)
	stability_iteration_labels, stability_sections = build_indicator_stability_sections(
		iteration_history_labels,
		counts_by_indicator,
		sample_size,
	)
	added_diff_rows, removed_diff_rows, changed_diff_rows = build_iteration_diff_rows(
		component_ids,
		scored_rows_by_component,
		previous_rows_by_component,
		previous_iteration_label or "previous_iteration",
		iteration_label,
	)
	changed_score_history_rows = build_changed_score_history_rows(
		changed_diff_rows,
		iteration_history_labels,
		historical_rows_by_iteration,
	)
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
			output_path=consolidated_output_path,
			registry_path=registry_path,
			component_ids=component_ids,
			manifest_path=manifest_path,
			iteration_label=iteration_label,
			iteration_history_labels=iteration_history_labels,
			previous_iteration_label=previous_iteration_label,
			sample_size=sample_size,
			scored_csv_paths=scored_csv_paths,
			total_scored_rows=total_scored_rows,
				indicator_delta_rows=indicator_delta_rows,
			stability_iteration_labels=stability_iteration_labels,
			stability_sections=stability_sections,
			added_diff_rows=added_diff_rows,
			removed_diff_rows=removed_diff_rows,
			changed_score_history_rows=changed_score_history_rows,
			missing_previous_components=missing_previous_components,
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