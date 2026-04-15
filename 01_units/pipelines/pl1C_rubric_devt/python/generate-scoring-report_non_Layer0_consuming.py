#!/usr/bin/env python3
"""Generate a consolidated scoring markdown report for one or more components.

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
- --comparison-scope: either `iteration` or `run`.
- --run-label: optional explicit current run label.
- --baseline-iteration-label / --baseline-run-label: optional explicit
	baseline endpoint when comparing iteration outputs.

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
	cell contains a directional overlap count over positive row observations.
	For row template R and column template C, the count is the number of
	positive observations contributing to R's Base Table
	`number_scored_positive` total whose `(component_id, submission_id)` pair is
	also positive for template C.
5. A second co-incidence matrix with the same structure, but each populated
	cell is expressed as a row-conditional percentage: the share of positive row
	observations for the row template that were also positive for the column
	template.

Saturation rate definition:
- saturation_rate = number_scored_positive / number_scored

Output naming:
- Run-scope report:
	I_<assignment>_scoring_report_intra_<iteration>_<run>.md
- Iteration-scope report:
	I_<assignment>_scoring_report_inter_<iteration>_<run>.md
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from os.path import commonpath
import re
import sys
from pathlib import Path

from generate_rubric_and_manifest_from_indicator_registry_non_Layer0_consuming import (
	apply_expression_template,
	apply_token_template,
	collect_field_value_records,
	collect_section_rows,
	collect_markdown_tables,
	expand_component_pattern,
	extract_rule_template,
	find_table_by_heading,
	resolve_component_block_lookup,
	resolve_local_slot_values,
)


SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
ITERATION_RE = re.compile(r"\b(iter\d+)\b", re.IGNORECASE)
RUN_RE = re.compile(r"\b(run\d+)\b", re.IGNORECASE)
RUNNER_OUTPUT_SUBDIR = "Level1-CalibrationTesting-Outputs"
SCORING_OUTPUT_VERSION_RE = re.compile(r"_v(\d+)(?=_)")
REGISTRY_VERSION_PATH_RE = re.compile(r"(/registry_v)(\d+)(/)", re.IGNORECASE)
COMPONENT_ID_RANGE_RE = re.compile(r"Section([A-Za-z])(\{\d+\.\.\d+\}|\d+)Response")
LAYER1_SCORED_OUTPUT_RE = re.compile(
	r"^RUN_(?P<assignment>[A-Za-z0-9]+)_(?P<component_id>.+?)_Layer1_indicator_scoring_(?P<version>v\d+)_output(?:_output)?\.csv$"
)
POSITIVE_EVIDENCE_STATUS_VALUES = {
	"positive",
	"present",
	"yes",
	"true",
	"1",
	"supported",
	"met",
}


@dataclass(frozen=True)
class ComparisonEntry:
	label: str
	iteration_label: str
	run_label: str | None


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate scoring markdown files for manifest entries matching a component ID."
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
		help="Output directory for scoring report files. Defaults to <manifest_dir>/Level1-CalibrationTesting-Outputs.",
	)
	parser.add_argument(
		"--comparison-scope",
		type=str,
		choices=["iteration", "run"],
		default="iteration",
		help="Comparison scope: compare across iteration endpoints or across runs within a single iteration.",
	)
	parser.add_argument(
		"--iteration-label",
		type=str,
		required=False,
		help="Optional iteration label override, e.g. iter02.",
	)
	parser.add_argument(
		"--run-label",
		type=str,
		required=False,
		help="Optional run label override, e.g. run02.",
	)
	parser.add_argument(
		"--baseline-iteration-label",
		type=str,
		required=False,
		help="Optional baseline iteration label for iteration-scope comparisons, e.g. iter05.",
	)
	parser.add_argument(
		"--baseline-run-label",
		type=str,
		required=False,
		help="Optional baseline run label for iteration-scope comparisons, e.g. run01.",
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


def derive_run_label(input_path: Path, explicit_label: str | None) -> str | None:
	if explicit_label:
		return explicit_label.strip()
	for part in input_path.parts:
		match = RUN_RE.search(part)
		if match:
			return match.group(1).lower()
	match = RUN_RE.search(str(input_path))
	if match:
		return match.group(1).lower()
	return None


def format_numeric_label(prefix: str, number: int, width: int) -> str:
	return f"{prefix}{number:0{width}d}"


def parse_numeric_label(label: str, prefix: str) -> tuple[int, int] | None:
	match = re.fullmatch(rf"{prefix}(\d+)", label.strip().lower())
	if match is None:
		return None
	digits = match.group(1)
	return (int(digits), len(digits))


def sanitize_label_for_filename(label: str) -> str:
	return re.sub(r"[^A-Za-z0-9._-]+", "-", label.strip()).strip("-") or "report"


def format_iteration_run_label(iteration_label: str, run_label: str | None) -> str:
	if run_label:
		return f"{iteration_label}-{run_label}"
	return iteration_label


def derive_output_filename(
	component_ids: list[str],
	manifest_path: Path,
	comparison_scope: str,
	current_label: str,
	current_iteration_label: str,
	current_run_label: str | None,
	previous_label: str | None,
) -> str:
	prefix = derive_assignment_output_prefix(manifest_path)
	component_label = component_ids[0] if len(component_ids) == 1 else None
	if comparison_scope == "run":
		suffix = (
			f"intra_{sanitize_label_for_filename(current_iteration_label)}"
			f"_{sanitize_label_for_filename(current_run_label or current_label)}"
		)
	else:
		suffix = (
			f"inter_{sanitize_label_for_filename(current_iteration_label)}"
			f"_{sanitize_label_for_filename(current_run_label or current_label)}"
		)
	if len(component_ids) == 1:
		return f"{prefix}_{component_label}_scoring_report_{suffix}.md"
	return f"{prefix}_scoring_report_{suffix}.md"


def derive_previous_iteration_label(iteration_label: str) -> str | None:
	parsed = parse_numeric_label(iteration_label, "iter")
	if parsed is None:
		return None
	iteration_number, width = parsed
	if iteration_number <= 0:
		return None
	return format_numeric_label("iter", iteration_number - 1, width)


def derive_previous_run_label(run_label: str) -> str | None:
	parsed = parse_numeric_label(run_label, "run")
	if parsed is None:
		return None
	run_number, width = parsed
	if run_number <= 0:
		return None
	return format_numeric_label("run", run_number - 1, width)


def derive_iteration_history_labels(iteration_label: str) -> list[str]:
	parsed = parse_numeric_label(iteration_label, "iter")
	if parsed is None:
		return [iteration_label]
	iteration_number, width = parsed
	if iteration_number <= 0:
		return [iteration_label]
	return [format_numeric_label("iter", index, width) for index in range(1, iteration_number + 1)]


def derive_run_history_labels(run_label: str) -> list[str]:
	parsed = parse_numeric_label(run_label, "run")
	if parsed is None:
		return [run_label]
	run_number, width = parsed
	if run_number <= 0:
		return [run_label]
	return [format_numeric_label("run", index, width) for index in range(1, run_number + 1)]


def derive_delta_column_label(previous_label: str, current_label: str) -> str:
	return f"delta {previous_label}-{current_label}"


def derive_display_history_labels(history_labels: list[str]) -> list[str]:
	return list(reversed(history_labels))


def derive_display_history_pairs(history_labels: list[str]) -> list[tuple[str, str]]:
	return list(reversed(list(zip(history_labels, history_labels[1:]))))


def build_delta_table_headers(history_labels: list[str]) -> list[str]:
	display_history_labels = derive_display_history_labels(history_labels)
	headers = ["indicator", *display_history_labels]
	for previous_label, current_label in derive_display_history_pairs(history_labels):
		headers.extend(
			[
				".",
				derive_delta_column_label(previous_label, current_label),
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
	current_parsed = parse_numeric_label(current_iteration_label, "iter")
	target_parsed = parse_numeric_label(target_iteration_label, "iter")
	if current_parsed is None or target_parsed is None:
		return None
	_, current_width = current_parsed
	target_number, _ = target_parsed
	return f"{target_number:0{current_width}d}"


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
	target_text = re.sub(
		rf"/{re.escape(current_label)}(?=/|$)",
		f"/{target_label}",
		current_text,
	)
	target_version = derive_target_version_label(current_iteration_label, target_iteration_label)
	if target_version is not None:
		target_text = REGISTRY_VERSION_PATH_RE.sub(rf"\g<1>{target_version}\g<3>", target_text)
	target_ref = Path(target_text)
	if target_version is None:
		return target_ref
	updated_name = SCORING_OUTPUT_VERSION_RE.sub(f"_v{target_version}", target_ref.name, count=1)
	if updated_name == target_ref.name:
		return target_ref
	return target_ref.with_name(updated_name)


def remap_scored_input_ref_for_run(
	input_ref: Path,
	current_run_label: str,
	target_run_label: str,
) -> Path:
	if target_run_label == current_run_label:
		return input_ref
	current_text = str(input_ref)
	current_label = current_run_label.strip().lower()
	target_label = target_run_label.strip().lower()
	return Path(
		re.sub(
			rf"/{re.escape(current_label)}(?=/|$)",
			f"/{target_label}",
			current_text,
		)
	)


def derive_expected_version_label(input_ref: Path, iteration_label: str | None = None) -> str | None:
	version_match = SCORING_OUTPUT_VERSION_RE.search(input_ref.name)
	if version_match is not None:
		return version_match.group(1)
	if iteration_label is None:
		return None
	iteration_parsed = parse_numeric_label(iteration_label, "iter")
	if iteration_parsed is None:
		return None
	iteration_number, width = iteration_parsed
	return f"{iteration_number:0{width}d}"


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


def discover_component_deterministic_scored_csv_paths_in_dir(
	directory: Path,
	component_id: str,
	expected_version_label: str | None = None,
) -> list[Path]:
	if not directory.exists() or not directory.is_dir():
		return []
	if expected_version_label:
		combined_pattern = f"*{component_id}*_Layer1_indicator_scoring_v{expected_version_label}_output.csv"
	else:
		combined_pattern = f"*{component_id}*_Layer1_indicator_scoring_v*_output.csv"
	combined_matches = sorted(
		candidate_path
		for candidate_path in directory.glob(combined_pattern)
		if candidate_path.is_file() and not candidate_path.name.endswith("-wide.csv")
	)
	if combined_matches:
		return combined_matches
	if expected_version_label:
		per_indicator_pattern = f"*{component_id}*_Layer1_indicator_module_v{expected_version_label}_*_output.csv"
	else:
		per_indicator_pattern = f"*{component_id}*_Layer1_indicator_module_v*_*_output.csv"
	return sorted(
		candidate_path
		for candidate_path in directory.glob(per_indicator_pattern)
		if candidate_path.is_file() and not candidate_path.name.endswith("-wide.csv")
	)


def discover_component_scored_csv_paths_in_dir(
	directory: Path,
	component_id: str,
	expected_version_label: str | None = None,
) -> list[Path]:
	deterministic_matches = discover_component_deterministic_scored_csv_paths_in_dir(
		directory,
		component_id,
		expected_version_label,
	)
	if deterministic_matches:
		return deterministic_matches
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
	current_run_label: str | None = None,
	target_run_label: str | None = None,
) -> list[Path]:
	target_input_ref = remap_scored_input_ref_for_iteration(
		current_input_ref,
		current_iteration_label,
		target_iteration_label,
	)
	if current_run_label and target_run_label:
		target_input_ref = remap_scored_input_ref_for_run(target_input_ref, current_run_label, target_run_label)
	return resolve_component_scored_csv_paths(
		target_input_ref,
		component_id,
		derive_expected_version_label(target_input_ref, target_iteration_label),
	)


def find_numeric_label_container(input_ref: Path, prefix: str) -> Path | None:
	search_roots = [input_ref]
	search_roots.extend(input_ref.parents)
	for candidate in search_roots:
		if parse_numeric_label(candidate.name, prefix) is not None:
			return candidate
	return None


def list_numeric_child_labels(parent_dir: Path, prefix: str) -> list[str]:
	if not parent_dir.exists() or not parent_dir.is_dir():
		return []
	labels = [
		child.name.lower()
		for child in parent_dir.iterdir()
		if child.is_dir() and parse_numeric_label(child.name, prefix) is not None
	]
	return sorted(labels, key=lambda label: parse_numeric_label(label, prefix) or (0, 0))


def discover_resolvable_run_labels_for_iteration(
	current_input_refs: list[Path],
	component_ids: list[str],
	current_iteration_label: str,
	target_iteration_label: str,
) -> list[str]:
	if not current_input_refs:
		return []
	first_target_ref = remap_scored_input_ref_for_iteration(
		current_input_refs[0],
		current_iteration_label,
		target_iteration_label,
	)
	run_container = find_numeric_label_container(first_target_ref, "run")
	if run_container is None:
		return []
	candidate_labels = list_numeric_child_labels(run_container.parent, "run")
	resolvable_labels: list[str] = []
	for candidate_label in candidate_labels:
		all_components_resolved = True
		for component_id, current_input_ref in zip(component_ids, current_input_refs):
			target_ref = remap_scored_input_ref_for_iteration(
				current_input_ref,
				current_iteration_label,
				target_iteration_label,
			)
			target_ref = remap_scored_input_ref_for_run(target_ref, run_container.name.lower(), candidate_label)
			resolved_paths = resolve_component_scored_csv_paths(
				target_ref,
				component_id,
				derive_expected_version_label(target_ref, target_iteration_label),
			)
			if not resolved_paths:
				all_components_resolved = False
				break
		if all_components_resolved:
			resolvable_labels.append(candidate_label)
	return resolvable_labels


def resolve_target_run_label(
	current_input_refs: list[Path],
	component_ids: list[str],
	current_iteration_label: str,
	target_iteration_label: str,
	explicit_run_label: str | None,
	fallback_run_label: str | None,
) -> str | None:
	if explicit_run_label:
		return explicit_run_label.strip().lower()
	if target_iteration_label == current_iteration_label and fallback_run_label:
		return fallback_run_label.strip().lower()
	resolvable_labels = discover_resolvable_run_labels_for_iteration(
		current_input_refs,
		component_ids,
		current_iteration_label,
		target_iteration_label,
	)
	if resolvable_labels:
		return resolvable_labels[-1]
	return fallback_run_label.strip().lower() if fallback_run_label else None


def build_iteration_comparison_entries(
	current_iteration_label: str,
	current_run_label: str | None,
	baseline_iteration_label: str | None,
	baseline_run_label: str | None,
	component_ids: list[str],
	current_input_refs: list[Path],
) -> list[ComparisonEntry]:
	iteration_labels = [baseline_iteration_label] if baseline_iteration_label else derive_iteration_history_labels(current_iteration_label)
	entries: list[ComparisonEntry] = []
	for iteration_label in iteration_labels:
		if iteration_label is None:
			continue
		target_run_label = resolve_target_run_label(
			current_input_refs,
			component_ids,
			current_iteration_label,
			iteration_label,
			baseline_run_label if iteration_label == baseline_iteration_label else None,
			current_run_label,
		)
		entries.append(
			ComparisonEntry(
				label=format_iteration_run_label(iteration_label, target_run_label),
				iteration_label=iteration_label,
				run_label=target_run_label,
			)
		)
	current_label = format_iteration_run_label(current_iteration_label, current_run_label)
	if not entries or entries[-1].label != current_label:
		entries.append(
			ComparisonEntry(
				label=current_label,
				iteration_label=current_iteration_label,
				run_label=current_run_label,
			)
		)
	return entries


def build_run_comparison_entries(current_iteration_label: str, current_run_label: str) -> list[ComparisonEntry]:
	return [
		ComparisonEntry(label=run_label, iteration_label=current_iteration_label, run_label=run_label)
		for run_label in derive_run_history_labels(current_run_label)
	]


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


def build_indicator_counts_by_label(
	component_ids: list[str],
	history_labels: list[str],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
) -> dict[str, dict[str, dict[str, int]]]:
	counts_by_indicator: dict[str, dict[str, dict[str, int]]] = {}
	for history_label in history_labels:
		for component_id in component_ids:
			for row in historical_rows_by_label.get(history_label, {}).get(component_id, []):
				indicator_id = (row.get("indicator_id") or "").strip()
				if not indicator_id:
					continue
				counts_by_indicator.setdefault(indicator_id, {})
				counts_by_indicator[indicator_id].setdefault(
					history_label,
					{"positive": 0, "number_scored": 0},
				)
				counts_by_indicator[indicator_id][history_label]["number_scored"] += 1
				if is_positive_scored_row(row):
					counts_by_indicator[indicator_id][history_label]["positive"] += 1
	return counts_by_indicator


def build_template_counts_by_label(
	component_ids: list[str],
	history_labels: list[str],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
	base_row_reverse_lookup: dict[tuple[str, str], dict[str, str]],
) -> dict[str, dict[str, dict[str, int]]]:
	counts_by_template: dict[str, dict[str, dict[str, int]]] = {}
	for history_label in history_labels:
		for component_id in component_ids:
			for row in historical_rows_by_label.get(history_label, {}).get(component_id, []):
				indicator_id = (row.get("indicator_id") or "").strip()
				if not indicator_id:
					continue
				base_row_info = base_row_reverse_lookup.get((component_id, indicator_id))
				if base_row_info is None:
					continue
				template_id = (base_row_info.get("template_id") or "").strip()
				if not template_id:
					continue
				counts_by_template.setdefault(template_id, {})
				counts_by_template[template_id].setdefault(
					history_label,
					{"positive": 0, "number_scored": 0},
				)
				counts_by_template[template_id][history_label]["number_scored"] += 1
				if is_positive_scored_row(row):
					counts_by_template[template_id][history_label]["positive"] += 1
	return counts_by_template


def build_template_component_counts_by_label(
	component_ids: list[str],
	history_labels: list[str],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
	base_row_reverse_lookup: dict[tuple[str, str], dict[str, str]],
) -> dict[str, dict[str, dict[str, dict[str, int]]]]:
	counts_by_template_component: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
	for history_label in history_labels:
		for component_id in component_ids:
			for row in historical_rows_by_label.get(history_label, {}).get(component_id, []):
				indicator_id = (row.get("indicator_id") or "").strip()
				if not indicator_id:
					continue
				base_row_info = base_row_reverse_lookup.get((component_id, indicator_id))
				if base_row_info is None:
					continue
				template_id = (base_row_info.get("template_id") or "").strip()
				if not template_id:
					continue
				counts_by_template_component.setdefault(template_id, {})
				counts_by_template_component[template_id].setdefault(component_id, {})
				counts_by_template_component[template_id][component_id].setdefault(
					history_label,
					{"positive": 0, "number_scored": 0},
				)
				counts_by_template_component[template_id][component_id][history_label]["number_scored"] += 1
				if is_positive_scored_row(row):
					counts_by_template_component[template_id][component_id][history_label]["positive"] += 1
	return counts_by_template_component


def classify_variance_rate(variance_rate: float) -> str:
	if variance_rate == 0:
		return "stable"
	if variance_rate > 0 and variance_rate < 0.05:
		return "low_variance"
	if variance_rate >= 0.05 and variance_rate <= 0.10:
		return "borderline_unstable"
	return "unstable"


def format_signed_deltas(deltas: list[int]) -> str:
	if not deltas:
		return ""
	return ", ".join(f"{delta:+d}" for delta in deltas)


def count_sign_flips(deltas: list[int]) -> int:
	non_zero_signs = [1 if delta > 0 else -1 for delta in deltas if delta != 0]
	if len(non_zero_signs) < 2:
		return 0
	return sum(
		1
		for previous_sign, current_sign in zip(non_zero_signs, non_zero_signs[1:])
		if previous_sign != current_sign
	)


def classify_coarse_run_pattern(deltas: list[int]) -> str:
	non_zero_deltas = [delta for delta in deltas if delta != 0]
	if not non_zero_deltas:
		return "flat"
	if len(non_zero_deltas) == 1:
		return "spike_up" if non_zero_deltas[0] > 0 else "spike_down"
	if all(delta > 0 for delta in non_zero_deltas):
		return "drifting_up"
	if all(delta < 0 for delta in non_zero_deltas):
		return "drifting_down"
	if any(delta > 0 for delta in non_zero_deltas) and any(delta < 0 for delta in non_zero_deltas):
		return "reversal"
	return "mixed"


def classify_fine_run_pattern(deltas: list[int]) -> str:
	non_zero_deltas = [delta for delta in deltas if delta != 0]
	if not non_zero_deltas:
		return "flat"
	if len(non_zero_deltas) == 1:
		return "spike_up" if non_zero_deltas[0] > 0 else "spike_down"
	sign_flips = count_sign_flips(deltas)
	if sign_flips >= max(len(non_zero_deltas) - 1, 1) and len(non_zero_deltas) >= 3:
		return "oscillating"
	if sign_flips > 0:
		return "mixed"
	direction = "up" if non_zero_deltas[0] > 0 else "down"
	magnitudes = [abs(delta) for delta in non_zero_deltas]
	if len(magnitudes) >= 2:
		if all(current <= previous for previous, current in zip(magnitudes, magnitudes[1:])) and any(
			current < previous for previous, current in zip(magnitudes, magnitudes[1:])
		):
			return f"converging_{direction}"
		if all(current >= previous for previous, current in zip(magnitudes, magnitudes[1:])) and any(
			current > previous for previous, current in zip(magnitudes, magnitudes[1:])
		):
			return f"diverging_{direction}"
	return f"drifting_{direction}"


def classify_run_pattern(deltas: list[int], run_count: int) -> str:
	if run_count <= 3:
		return classify_coarse_run_pattern(deltas)
	return classify_fine_run_pattern(deltas)


def build_run_pattern_note(run_count: int) -> str:
	coarse_labels = "flat, drifting_up, drifting_down, reversal, spike_up, spike_down, mixed"
	if run_count <= 3:
		return (
			f"Observed run-pattern labels use the coarse vocabulary available with {run_count} runs: {coarse_labels}. "
			"Finer-grained labels such as converging_up, converging_down, diverging_up, diverging_down, and oscillating are not emitted until at least 4 runs are available."
		)
	return (
		f"Observed run-pattern labels use the expanded vocabulary available with {run_count} runs. "
		f"The coarse labels ({coarse_labels}) remain available, and finer-grained labels such as converging_up, converging_down, diverging_up, diverging_down, and oscillating are emitted when supported by the run history."
	)


def build_item_metric_note() -> str:
	return (
		"Item-level metrics align each item across runs using the union of observed item keys. "
		"For indicator rows, items are submission_ids within a component-indicator pair. "
		"For template rows, flip_rate, consensus_rate, and ici are recomputed from pooled component-indicator-submission tuples across all expanded indicators mapped to the template, while max_item_disagreement is the maximum component-level disagreement count. "
		"Missing observations are treated as empty cells when computing disagreements and consensus."
	)


def format_ratio(numerator: int, denominator: int) -> str:
	if denominator <= 0:
		return "0.000"
	return f"{(numerator / denominator):.3f}"


def build_item_histories_by_component_indicator(
	stability_labels: list[str],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
) -> dict[tuple[str, str], dict[str, list[str]]]:
	label_positions = {label: index for index, label in enumerate(stability_labels)}
	item_histories: dict[tuple[str, str], dict[str, list[str]]] = {}
	for history_label in stability_labels:
		label_index = label_positions[history_label]
		for component_id, rows in historical_rows_by_label.get(history_label, {}).items():
			for row in rows:
				indicator_id = (row.get("indicator_id") or "").strip()
				submission_id = (row.get("submission_id") or "").strip()
				if not indicator_id or not submission_id:
					continue
				group_key = (component_id, indicator_id)
				group_histories = item_histories.setdefault(group_key, {})
				item_history = group_histories.setdefault(submission_id, [""] * len(stability_labels))
				item_history[label_index] = summarize_score_value(row.get("evidence_status") or "")
	return item_histories


def build_item_histories_by_template(
	stability_labels: list[str],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
	base_row_reverse_lookup: dict[tuple[str, str], dict[str, str]],
) -> dict[str, dict[tuple[str, str, str], list[str]]]:
	label_positions = {label: index for index, label in enumerate(stability_labels)}
	item_histories: dict[str, dict[tuple[str, str, str], list[str]]] = {}
	for history_label in stability_labels:
		label_index = label_positions[history_label]
		for component_id, rows in historical_rows_by_label.get(history_label, {}).items():
			for row in rows:
				indicator_id = (row.get("indicator_id") or "").strip()
				submission_id = (row.get("submission_id") or "").strip()
				if not indicator_id or not submission_id:
					continue
				base_row_info = base_row_reverse_lookup.get((component_id, indicator_id))
				if base_row_info is None:
					continue
				template_id = (base_row_info.get("template_id") or "").strip()
				if not template_id:
					continue
				group_histories = item_histories.setdefault(template_id, {})
				item_key = (component_id, indicator_id, submission_id)
				item_history = group_histories.setdefault(item_key, [""] * len(stability_labels))
				item_history[label_index] = summarize_score_value(row.get("evidence_status") or "")
	return item_histories


def build_item_histories_by_template_component(
	stability_labels: list[str],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
	base_row_reverse_lookup: dict[tuple[str, str], dict[str, str]],
) -> dict[str, dict[str, dict[tuple[str, str], list[str]]]]:
	label_positions = {label: index for index, label in enumerate(stability_labels)}
	item_histories: dict[str, dict[str, dict[tuple[str, str], list[str]]]] = {}
	for history_label in stability_labels:
		label_index = label_positions[history_label]
		for component_id, rows in historical_rows_by_label.get(history_label, {}).items():
			for row in rows:
				indicator_id = (row.get("indicator_id") or "").strip()
				submission_id = (row.get("submission_id") or "").strip()
				if not indicator_id or not submission_id:
					continue
				base_row_info = base_row_reverse_lookup.get((component_id, indicator_id))
				if base_row_info is None:
					continue
				template_id = (base_row_info.get("template_id") or "").strip()
				if not template_id:
					continue
				template_histories = item_histories.setdefault(template_id, {})
				component_histories = template_histories.setdefault(component_id, {})
				item_key = (indicator_id, submission_id)
				item_history = component_histories.setdefault(item_key, [""] * len(stability_labels))
				item_history[label_index] = summarize_score_value(row.get("evidence_status") or "")
	return item_histories


def calculate_item_stability_metrics(item_histories: dict[object, list[str]]) -> dict[str, int | str]:
	total_items = len(item_histories)
	if total_items == 0:
		return {
			"flip_rate": "0.000",
			"consensus_rate": "0.000",
			"max_item_disagreement": "0",
			"ici": "0.000",
		}
	comparison_count = max(len(next(iter(item_histories.values()))) - 1, 0)
	disagreements_by_pair = [0] * comparison_count
	consensus_items = 0
	ever_flip_items = 0
	for item_history in item_histories.values():
		if len(set(item_history)) == 1:
			consensus_items += 1
		has_flip = False
		for pair_index in range(comparison_count):
			if item_history[pair_index] == item_history[pair_index + 1]:
				continue
			disagreements_by_pair[pair_index] += 1
			has_flip = True
		if has_flip:
			ever_flip_items += 1
	total_comparisons = total_items * comparison_count
	return {
		"flip_rate": format_ratio(sum(disagreements_by_pair), total_comparisons),
		"consensus_rate": format_ratio(consensus_items, total_items),
		"max_item_disagreement": str(max(disagreements_by_pair) if disagreements_by_pair else 0),
		"ici": format_ratio(ever_flip_items, total_items),
	}


def calculate_max_component_item_disagreement(
	template_component_item_histories: dict[str, dict[tuple[str, str], list[str]]],
) -> str:
	max_disagreement = 0
	for component_histories in template_component_item_histories.values():
		component_metrics = calculate_item_stability_metrics(component_histories)
		max_disagreement = max(max_disagreement, int(str(component_metrics["max_item_disagreement"])))
	return str(max_disagreement)


def calculate_max_component_template_variance_rate(
	stability_labels: list[str],
	template_component_counts_by_label: dict[str, dict[str, dict[str, int]]],
	sample_size: int,
) -> float:
	component_variance_rates: list[float] = []
	for component_counts_by_label in template_component_counts_by_label.values():
		number_scored_counts = [
			component_counts_by_label.get(label, {}).get("number_scored", 0)
			for label in stability_labels
		]
		positive_counts = [
			component_counts_by_label.get(label, {}).get("positive", 0)
			for label in stability_labels
		]
		absolute_deltas = [
			abs(current_count - previous_count)
			for previous_count, current_count in zip(positive_counts, positive_counts[1:])
		]
		max_delta = max(absolute_deltas) if absolute_deltas else 0
		denominator = max(number_scored_counts) if any(number_scored_counts) else (sample_size if sample_size > 0 else 1)
		component_variance_rates.append(max_delta / denominator)
	if not component_variance_rates:
		return 0.0
	return max(component_variance_rates)


def extract_signed_deltas_from_stability_row(stability_labels: list[str], row: list[str]) -> list[int]:
	abs_delta_count = max(len(stability_labels) - 1, 0)
	variance_rate_index = 1 + len(stability_labels) + abs_delta_count + 1
	signed_delta_start = variance_rate_index + 1
	range_delta_index = signed_delta_start + abs_delta_count
	signed_delta_cells = row[signed_delta_start:range_delta_index]
	signed_deltas: list[int] = []
	for cell in signed_delta_cells:
		value = cell.strip()
		if not value:
			continue
		signed_deltas.append(int(value))
	return signed_deltas


def build_indicator_stability_sections(
	stability_labels: list[str],
	counts_by_indicator: dict[str, dict[str, dict[str, int]]],
	sample_size: int,
) -> tuple[list[str], dict[str, list[list[str]]]]:
	if len(stability_labels) < 3:
		return ([], {})
	classification_rows: dict[str, list[list[str]]] = {
		"stable": [],
		"low_variance": [],
		"borderline_unstable": [],
		"unstable": [],
	}
	denominator = sample_size if sample_size > 0 else 1
	for indicator_id in sorted(counts_by_indicator, key=indicator_sort_key):
		positive_counts = [
			counts_by_indicator[indicator_id].get(label, {}).get("positive", 0)
			for label in stability_labels
		]
		absolute_deltas = [
			abs(current_count - previous_count)
			for previous_count, current_count in zip(positive_counts, positive_counts[1:])
		]
		signed_deltas = [
			current_count - previous_count
			for previous_count, current_count in zip(positive_counts, positive_counts[1:])
		]
		max_delta = max(absolute_deltas) if absolute_deltas else 0
		variance_rate = max_delta / denominator
		range_delta = max(positive_counts) - min(positive_counts)
		range_rate = range_delta / denominator
		classification = classify_variance_rate(variance_rate)
		row = [indicator_id]
		row.extend(str(count) for count in positive_counts)
		row.extend(str(delta) for delta in absolute_deltas)
		row.append(str(max_delta))
		row.append(f"{variance_rate:.3f}")
		row.extend(f"{delta:+d}" for delta in signed_deltas)
		row.append(str(range_delta))
		row.append(f"{range_rate:.3f}")
		classification_rows[classification].append(row)
	return (stability_labels, classification_rows)


def build_stability_table_headers(stability_labels: list[str]) -> list[str]:
	headers = ["indicator", *stability_labels]
	for previous_label, current_label in zip(stability_labels, stability_labels[1:]):
		headers.append(f"delta {previous_label}-{current_label}")
	headers.extend(["max_delta", "variance_rate"])
	for previous_label, current_label in zip(stability_labels, stability_labels[1:]):
		headers.append(f"signed_delta {previous_label}-{current_label}")
	headers.extend(["range_delta", "range_rate"])
	return headers


def build_intra_report_variance_summary_rows(
	stability_labels: list[str],
	indicator_rows: list[list[str]],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
	sample_size: int,
) -> list[list[str]]:
	if len(stability_labels) < 3:
		return []

	denominator = sample_size if sample_size > 0 else 1
	item_histories_by_component_indicator = build_item_histories_by_component_indicator(
		stability_labels,
		historical_rows_by_label,
	)

	summary_rows: list[list[str]] = []
	for indicator_row in indicator_rows:
		component_id = indicator_row[0]
		indicator_id = indicator_row[1]
		sbo_short_description = indicator_row[2]
		positive_counts = []
		for label in stability_labels:
			rows = historical_rows_by_label.get(label, {}).get(component_id, [])
			positive_counts.append(
				sum(
					1
					for row in rows
					if (row.get("indicator_id") or "").strip() == indicator_id and is_positive_scored_row(row)
				)
			)
		absolute_deltas = [
			abs(current_count - previous_count)
			for previous_count, current_count in zip(positive_counts, positive_counts[1:])
		]
		signed_deltas = [
			current_count - previous_count
			for previous_count, current_count in zip(positive_counts, positive_counts[1:])
		]
		max_delta = max(absolute_deltas) if absolute_deltas else 0
		variance_rate = max_delta / denominator
		classification = classify_variance_rate(variance_rate)
		run_pattern = classify_run_pattern(signed_deltas, len(stability_labels))
		item_metrics = calculate_item_stability_metrics(
			item_histories_by_component_indicator.get((component_id, indicator_id), {})
		)
		summary_rows.append(
			[
				component_id,
				indicator_id,
				sbo_short_description,
				format_signed_deltas(signed_deltas),
				run_pattern,
				str(item_metrics["max_item_disagreement"]),
				str(item_metrics["flip_rate"]),
				str(item_metrics["consensus_rate"]),
				str(item_metrics["ici"]),
				str(max_delta),
				f"{variance_rate:.3f}",
				"x" if classification == "stable" else "",
				"x" if classification == "low_variance" else "",
				"x" if classification == "borderline_unstable" else "",
				"x" if classification == "unstable" else "",
			]
		)
	return summary_rows


def build_intra_report_template_variance_summary_rows(
	stability_labels: list[str],
	base_rows: list[list[str]],
	template_counts_by_label: dict[str, dict[str, dict[str, int]]],
	template_item_histories: dict[str, dict[tuple[str, str, str], list[str]]],
	template_component_counts_by_label: dict[str, dict[str, dict[str, dict[str, int]]]],
	template_component_item_histories: dict[str, dict[str, dict[tuple[str, str], list[str]]]],
	sample_size: int,
) -> list[list[str]]:
	if len(stability_labels) < 3:
		return []

	summary_rows: list[list[str]] = []
	for base_row in base_rows:
		template_id = base_row[0]
		local_slot = base_row[1]
		expanded_indicator_ids = base_row[2]
		sbo_short_description = base_row[3]
		number_scored_counts = [
			template_counts_by_label.get(template_id, {}).get(label, {}).get("number_scored", 0)
			for label in stability_labels
		]
		positive_counts = [
			template_counts_by_label.get(template_id, {}).get(label, {}).get("positive", 0)
			for label in stability_labels
		]
		absolute_deltas = [
			abs(current_count - previous_count)
			for previous_count, current_count in zip(positive_counts, positive_counts[1:])
		]
		signed_deltas = [
			current_count - previous_count
			for previous_count, current_count in zip(positive_counts, positive_counts[1:])
		]
		max_delta = max(absolute_deltas) if absolute_deltas else 0
		variance_rate = calculate_max_component_template_variance_rate(
			stability_labels,
			template_component_counts_by_label.get(template_id, {}),
			sample_size,
		)
		classification = classify_variance_rate(variance_rate)
		run_pattern = classify_run_pattern(signed_deltas, len(stability_labels))
		item_metrics = calculate_item_stability_metrics(template_item_histories.get(template_id, {}))
		max_component_item_disagreement = calculate_max_component_item_disagreement(
			template_component_item_histories.get(template_id, {})
		)
		summary_rows.append(
			[
				template_id,
				local_slot,
				expanded_indicator_ids,
				sbo_short_description,
				format_signed_deltas(signed_deltas),
				run_pattern,
				max_component_item_disagreement,
				str(item_metrics["flip_rate"]),
				str(item_metrics["consensus_rate"]),
				str(item_metrics["ici"]),
				str(max_delta),
				f"{variance_rate:.3f}",
				"x" if classification == "stable" else "",
				"x" if classification == "low_variance" else "",
				"x" if classification == "borderline_unstable" else "",
				"x" if classification == "unstable" else "",
			]
		)
	return summary_rows


def build_inter_report_saturation_summary_rows(
	previous_label: str | None,
	current_label: str,
	indicator_rows: list[list[str]],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
) -> list[list[str]]:
	if previous_label is None:
		return []

	counts_by_label_component_indicator: dict[str, dict[tuple[str, str], tuple[int, int]]] = {}
	for label in [previous_label, current_label]:
		component_indicator_counts: dict[tuple[str, str], tuple[int, int]] = {}
		for component_id, rows in historical_rows_by_label.get(label, {}).items():
			counts_by_indicator: dict[str, list[int]] = {}
			for row in rows:
				indicator_id = (row.get("indicator_id") or "").strip()
				if not indicator_id:
					continue
				counts = counts_by_indicator.setdefault(indicator_id, [0, 0])
				counts[0] += 1
				if is_positive_scored_row(row):
					counts[1] += 1
			for indicator_id, counts in counts_by_indicator.items():
				component_indicator_counts[(component_id, indicator_id)] = (counts[0], counts[1])
		counts_by_label_component_indicator[label] = component_indicator_counts

	summary_rows: list[list[str]] = []
	for indicator_row in indicator_rows:
		component_id = indicator_row[0]
		indicator_id = indicator_row[1]
		sbo_short_description = indicator_row[2]
		previous_counts = counts_by_label_component_indicator.get(previous_label, {}).get((component_id, indicator_id), (0, 0))
		current_counts = counts_by_label_component_indicator.get(current_label, {}).get((component_id, indicator_id), (0, 0))
		summary_rows.append(
			[
				component_id,
				indicator_id,
				sbo_short_description,
				format_rate(previous_counts[1], previous_counts[0]),
				format_rate(current_counts[1], current_counts[0]),
			]
		)
	return summary_rows


def build_iteration_stability_entries(
	current_iteration_label: str,
	current_run_label: str | None,
	component_ids: list[str],
	current_input_refs: list[Path],
) -> list[ComparisonEntry]:
	entries = build_iteration_comparison_entries(
		current_iteration_label=current_iteration_label,
		current_run_label=current_run_label,
		baseline_iteration_label=None,
		baseline_run_label=None,
		component_ids=component_ids,
		current_input_refs=current_input_refs,
	)
	return entries[-3:]


def quote_yaml_string(value: str) -> str:
	escaped = value.replace("\\", "\\\\").replace('"', '\\"')
	return f'"{escaped}"'


def render_yaml_frontmatter(
	output_path: Path,
	comparison_scope: str,
	current_label: str,
	history_labels: list[str],
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
		f"comparison_scope: {quote_yaml_string(comparison_scope)}\n",
		f"current_label: {quote_yaml_string(current_label)}\n",
		"manifest_input:\n",
		f"  path: {quote_yaml_string(str(manifest_path))}\n",
		"indicator_registry:\n",
		f"  path: {quote_yaml_string(str(registry_path))}\n",
		"history_labels:\n",
	]
	for history_label in history_labels:
		lines.append(f"  - {quote_yaml_string(history_label)}\n")
	lines.append("component_ids:\n")
	for component_id in component_ids:
		lines.append(f"  - {quote_yaml_string(component_id)}\n")
	lines.append("scored_csv_paths:\n")
	for scored_csv_path in scored_csv_paths:
		lines.append(f"  - {quote_yaml_string(str(scored_csv_path))}\n")
	lines.append("---\n")
	return "".join(lines)


def build_base_row_reverse_lookup(registry_path: Path) -> dict[tuple[str, str], dict[str, str]]:
	tables = collect_markdown_tables(registry_path)
	base_row_required_columns = {
		"template_id",
		"local_slot",
	}
	base_rows = collect_section_rows(
		tables,
		"base table",
		required_columns=base_row_required_columns,
		allow_field_value_records=True,
	)
	if not base_rows:
		base_rows = collect_field_value_records(
			tables,
			required_columns=base_row_required_columns,
		)
	reuse_table = find_table_by_heading(tables, "reuse rule table")
	component_block_rule_table = find_table_by_heading(tables, "component block rule table")
	if not base_rows or reuse_table is None:
		return {}

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

	def expand_component_ids_from_layer0_pattern(pattern: str) -> list[str]:
		matches = COMPONENT_ID_RANGE_RE.findall(pattern)
		component_ids: list[str] = []
		for block_prefix, range_token in matches:
			if range_token.startswith("{") and range_token.endswith("}") and ".." in range_token:
				start_text, end_text = range_token[1:-1].split("..", 1)
				start = int(start_text)
				end = int(end_text)
				for block_number in range(start, end + 1):
					component_ids.append(f"Section{block_prefix}{block_number}Response")
			else:
				component_ids.append(f"Section{block_prefix}{int(range_token)}Response")
		return component_ids

	def derive_legacy_layer1_indicator_id(component_id: str, local_slot: str) -> str:
		match = re.fullmatch(r"SectionB(\d+)Response", component_id)
		if match is None:
			return local_slot
		slot_match = re.fullmatch(r"0?(\d+)", local_slot)
		if slot_match is None:
			return local_slot
		return f"I{match.group(1)}{slot_match.group(1)}"

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

	if {
		"template_group",
		"applies_to_layer0_record_pattern",
		"component_block_rule",
		"local_slot_source",
		"sbo_identifier_format",
	}.issubset(reuse_headers):
		for reuse_row in reuse_rows:
			template_group = reuse_row.get("template_group", "").strip()
			layer0_pattern = reuse_row.get("applies_to_layer0_record_pattern", "").strip()
			local_slot_source = reuse_row.get("local_slot_source", "").strip()
			if local_slot_source not in {"template.local_slot", "local_slot", "template_local_slot"}:
				continue
			matching_base_rows = [
				row for row in base_rows if row.get("template_id", "").strip().startswith(f"{template_group}_")
			]
			for component_id in expand_component_ids_from_layer0_pattern(layer0_pattern):
				for base_row in matching_base_rows:
					local_slot = base_row.get("local_slot", "").strip()
					if not local_slot:
						continue
					register_mapping(component_id, local_slot, base_row, reuse_row)
					legacy_indicator_id = derive_legacy_layer1_indicator_id(component_id, local_slot)
					if legacy_indicator_id != local_slot:
						register_mapping(component_id, legacy_indicator_id, base_row, reuse_row)
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


def parse_json_object(value: str) -> dict[str, object]:
	text = value.strip()
	if not text:
		return {}
	try:
		parsed = json.loads(text)
	except json.JSONDecodeError:
		return {}
	return parsed if isinstance(parsed, dict) else {}


def resolve_submission_id_from_row(row: dict[str, str]) -> str:
	for field_name in ["submission_id", "participant_id"]:
		value = (row.get(field_name) or "").strip()
		if value:
			return value
	return ""


def derive_layer1_input_csv_path_from_scored_csv(scored_csv_path: Path, component_id: str) -> Path | None:
	match = LAYER1_SCORED_OUTPUT_RE.match(scored_csv_path.name)
	if match is None:
		return None
	if match.group("component_id") != component_id:
		return None
	if len(scored_csv_path.parents) < 4:
		return None
	registry_dir = scored_csv_path.parents[3]
	run_label = scored_csv_path.parents[1].name
	assignment = match.group("assignment")
	version = match.group("version")
	return (
		registry_dir
		/ "02_scoring_inputs"
		/ run_label
		/ "layer1_from_layer0"
		/ f"{assignment}_Layer1_input_from_Layer0_{component_id}_{version}.csv"
	)


def derive_layer0_stitched_csv_path_from_scored_csv(scored_csv_path: Path) -> Path | None:
	if len(scored_csv_path.parents) < 4:
		return None
	registry_dir = scored_csv_path.parents[3]
	run_label = scored_csv_path.parents[1].name
	stitched_dir = registry_dir / "03_diagnostics" / run_label / "layer0_runtime"
	if not stitched_dir.exists() or not stitched_dir.is_dir():
		return None
	matches = sorted(stitched_dir.glob("*output-wide-stitched.csv"))
	if not matches:
		return None
	return matches[0]


def index_input_rows_by_component_submission(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
	indexed_rows: dict[tuple[str, str], dict[str, str]] = {}
	for row in rows:
		component_id = (row.get("component_id") or "").strip()
		submission_id = resolve_submission_id_from_row(row)
		if not component_id or not submission_id:
			continue
		indexed_rows[(component_id, submission_id)] = row
	return indexed_rows


def format_source_submission_entry(component_id: str, submission_id: str, source_response_text: str) -> str:
	identifier = f"{component_id} / submission_id={submission_id}" if component_id else f"submission_id={submission_id}"
	text = source_response_text.strip() or "(missing source submission text)"
	return f"{identifier}\n{text}"


def append_source_submission_entry(
	bucket_entries: dict[str, list[str]],
	bucket_seen_entries: dict[str, set[str]],
	segment_bucket: str,
	entry: str,
) -> None:
	seen = bucket_seen_entries.setdefault(segment_bucket, set())
	if entry in seen:
		return
	seen.add(entry)
	bucket_entries.setdefault(segment_bucket, []).append(entry)


def append_segment_detail_row(
	detail_rows: list[tuple[str, str]],
	detail_row_seen: set[tuple[str, str]],
	entry: str,
	segment_bucket: str,
) -> None:
	row_key = (entry, segment_bucket)
	if row_key in detail_row_seen:
		return
	detail_row_seen.add(row_key)
	detail_rows.append(row_key)


def normalize_segment_bucket_label(value: str) -> str:
	text = value.strip()
	if text:
		return text
	return "(blank segment text)"


def escape_markdown_table_cell(value: str) -> str:
	normalized = value.replace("\r\n", "\n").replace("\r", "\n")
	return normalized.replace("|", "\\|").replace("\n", "<br>")


def highlight_segment_text_in_submission(source_entry: str, segment_text: str) -> str:
	normalized_entry = source_entry.replace("\r\n", "\n").replace("\r", "\n")
	normalized_segment = segment_text.replace("\r\n", "\n").replace("\r", "\n").strip()
	if not normalized_segment:
		return normalized_entry
	if normalized_segment in {"(blank segment text)", "(missing Layer 1 input row)"}:
		return normalized_entry
	exact_pattern = re.compile(re.escape(normalized_segment))
	if exact_pattern.search(normalized_entry):
		return exact_pattern.sub(lambda match: f"<mark>{match.group(0)}</mark>", normalized_entry)
	ignore_case_pattern = re.compile(re.escape(normalized_segment), re.IGNORECASE)
	if ignore_case_pattern.search(normalized_entry):
		return ignore_case_pattern.sub(lambda match: f"<mark>{match.group(0)}</mark>", normalized_entry)
	return normalized_entry


def build_segment_summary_rows(segment_counts: Counter[str], evidence_status: str) -> list[list[str]]:
	rows: list[list[str]] = []
	for segment_text, count in sorted(segment_counts.items(), key=lambda item: (-item[1], item[0].lower())):
		rows.append([
			escape_markdown_table_cell(evidence_status),
			escape_markdown_table_cell(segment_text),
			str(count),
		])
	return rows


def build_segment_detail_rows(detail_rows: list[tuple[str, str]]) -> list[list[str]]:
	rows: list[list[str]] = []
	for source_entry, segment_text in sorted(detail_rows, key=lambda item: (item[0].lower(), item[1].lower())):
		highlighted_source_entry = highlight_segment_text_in_submission(source_entry, segment_text)
		rows.append([
			escape_markdown_table_cell(highlighted_source_entry),
			escape_markdown_table_cell(segment_text),
		])
	return rows


def derive_indicator_segment_report_filename(
	manifest_path: Path,
	component_id: str,
	indicator_id: str,
	comparison_scope: str,
	current_label: str,
	current_iteration_label: str,
	current_run_label: str | None,
) -> str:
	prefix = derive_assignment_output_prefix(manifest_path)
	if comparison_scope == "run":
		suffix = (
			f"intra_{sanitize_label_for_filename(current_iteration_label)}"
			f"_{sanitize_label_for_filename(current_run_label or current_label)}"
		)
	else:
		suffix = (
			f"inter_{sanitize_label_for_filename(current_iteration_label)}"
			f"_{sanitize_label_for_filename(current_run_label or current_label)}"
		)
	return f"{prefix}_{component_id}_{indicator_id}_segment_report_{suffix}.md"


def format_slot_group_label(local_slot: str) -> str:
	slot_match = re.fullmatch(r"0?(\d+)", local_slot.strip())
	if slot_match is None:
		return local_slot.strip() or "slot"
	return f"I*{slot_match.group(1)}"


def derive_indicator_slot_group_report_filename(
	manifest_path: Path,
	local_slot: str,
	comparison_scope: str,
	current_label: str,
	current_iteration_label: str,
	current_run_label: str | None,
) -> str:
	prefix = derive_assignment_output_prefix(manifest_path)
	slot_match = re.fullmatch(r"0?(\d+)", local_slot.strip())
	slot_token = slot_match.group(1) if slot_match is not None else sanitize_label_for_filename(local_slot)
	if comparison_scope == "run":
		suffix = (
			f"intra_{sanitize_label_for_filename(current_iteration_label)}"
			f"_{sanitize_label_for_filename(current_run_label or current_label)}"
		)
	else:
		suffix = (
			f"inter_{sanitize_label_for_filename(current_iteration_label)}"
			f"_{sanitize_label_for_filename(current_run_label or current_label)}"
		)
	return f"{prefix}_Ix{slot_token}_segment_report_{suffix}.md"


def render_indicator_segment_report(
	*,
	output_path: Path,
	manifest_path: Path,
	comparison_scope: str,
	current_label: str,
	component_id: str,
	indicator_id: str,
	sbo_identifier: str,
	sbo_short_description: str,
	bound_segment_id: str,
	segment_field: str,
	scored_csv_path: Path | None,
	input_csv_path: Path | None,
	status_counts: Counter[str],
	matching_segment_counts: Counter[str],
	non_matching_segment_counts: Counter[str],
	matching_detail_entries: list[tuple[str, str]],
	non_matching_detail_entries: list[tuple[str, str]],
	matching_row_count: int,
	non_matching_row_count: int,
	missing_input_row_count: int,
) -> str:
	parts = [
		"---",
		f'generated_at_utc: "{datetime.now(timezone.utc).isoformat(timespec="seconds")}"',
		"generator:",
		f'  script: "{Path(__file__).resolve()}"',
		"output_file:",
		f'  path: "{output_path}"',
		f'  name: "{output_path.name}"',
		f'comparison_scope: "{comparison_scope}"',
		f'current_label: "{current_label}"',
		f'manifest_input: "{manifest_path}"',
		f'component_id: "{component_id}"',
		f'indicator_id: "{indicator_id}"',
		f'sbo_identifier: "{sbo_identifier}"',
		f'bound_segment_id: "{bound_segment_id}"',
		"---",
		"",
		f"## {output_path.name.removesuffix('.md')}",
		"",
		render_markdown_table(
			["metric", "value"],
			[
				["component_id", component_id],
				["indicator_id", indicator_id],
				["sbo_identifier", sbo_identifier],
				["sbo_short_description", sbo_short_description],
				["bound_segment_id", bound_segment_id or "(unbound)"],
				["segment_field", segment_field or "evidence_text"],
				["scored_csv", str(scored_csv_path) if scored_csv_path is not None else ""],
				["layer1_input_csv", str(input_csv_path) if input_csv_path is not None else ""],
				["matching_row_count", str(matching_row_count)],
				["non_matching_row_count", str(non_matching_row_count)],
				["missing_input_row_count", str(missing_input_row_count)],
				["unique_matching_segment_texts", str(len(matching_segment_counts))],
				["unique_non_matching_segment_texts", str(len(non_matching_segment_counts))],
			],
		),
		"",
		"### Evidence Status Counts",
		"",
	]
	status_rows = [
		[escape_markdown_table_cell(status or "(blank evidence_status)"), str(count)]
		for status, count in sorted(status_counts.items(), key=lambda item: (-item[1], item[0].lower()))
	]
	if status_rows:
		parts.append(render_markdown_table(["evidence_status", "count"], status_rows))
	else:
		parts.append("No scored rows.")
	parts.extend([
		"",
		"### Indicator-Segment Texts Summary",
		"",
		"#### Matching Segment Texts Summary",
		"",
	])
	matching_summary_rows = build_segment_summary_rows(matching_segment_counts, "present")
	if matching_summary_rows:
		parts.append(render_markdown_table(["evidence_status", "segment_text", "count"], matching_summary_rows))
	else:
		parts.append("No matching segment texts.")
	parts.extend([
		"",
		"#### Non-Matching Segment Texts Summary",
		"",
	])
	non_matching_summary_rows = build_segment_summary_rows(non_matching_segment_counts, "not_present")
	if non_matching_summary_rows:
		parts.append(render_markdown_table(["evidence_status", "segment_text", "count"], non_matching_summary_rows))
	else:
		parts.append("No non-matching segment texts.")
	parts.extend([
		"",
		"### Indicator-Segment Texts Detail",
		"",
		"#### Matching Segment Texts Detail",
		"",
	])
	matching_detail_rows = build_segment_detail_rows(matching_detail_entries)
	if matching_detail_rows:
		parts.append(render_markdown_table(["original_submission", "segment_text"], matching_detail_rows))
	else:
		parts.append("No matching segment details.")
	parts.extend([
		"",
		"#### Non-Matching Segment Texts Detail",
		"",
	])
	non_matching_detail_rows = build_segment_detail_rows(non_matching_detail_entries)
	if non_matching_detail_rows:
		parts.append(render_markdown_table(["original_submission", "segment_text"], non_matching_detail_rows))
	else:
		parts.append("No non-matching segment details.")
	parts.append("")
	return "\n".join(parts)


def render_indicator_slot_group_segment_report(
	*,
	output_path: Path,
	manifest_path: Path,
	comparison_scope: str,
	current_label: str,
	local_slot: str,
	template_ids: list[str],
	indicator_members: list[list[str]],
	status_counts: Counter[str],
	matching_segment_counts: Counter[str],
	non_matching_segment_counts: Counter[str],
	matching_detail_entries: list[tuple[str, str]],
	non_matching_detail_entries: list[tuple[str, str]],
	matching_row_count: int,
	non_matching_row_count: int,
	missing_input_row_count: int,
) -> str:
	group_label = format_slot_group_label(local_slot)
	parts = [
		"---",
		f'generated_at_utc: "{datetime.now(timezone.utc).isoformat(timespec="seconds")}"',
		"generator:",
		f'  script: "{Path(__file__).resolve()}"',
		"output_file:",
		f'  path: "{output_path}"',
		f'  name: "{output_path.name}"',
		f'comparison_scope: "{comparison_scope}"',
		f'current_label: "{current_label}"',
		f'manifest_input: "{manifest_path}"',
		f'local_slot: "{local_slot}"',
		f'group_label: "{group_label}"',
		"---",
		"",
		f"## {output_path.name.removesuffix('.md')}",
		"",
		render_markdown_table(
			["metric", "value"],
			[
				["group_label", group_label],
				["local_slot", local_slot],
				["template_ids", ", ".join(template_ids)],
				["indicator_ids", ", ".join(row[1] for row in indicator_members)],
				["component_ids", ", ".join(row[0] for row in indicator_members)],
				["matching_row_count", str(matching_row_count)],
				["non_matching_row_count", str(non_matching_row_count)],
				["missing_input_row_count", str(missing_input_row_count)],
				["unique_matching_segment_texts", str(len(matching_segment_counts))],
				["unique_non_matching_segment_texts", str(len(non_matching_segment_counts))],
			],
		),
		"",
		"### Indicator Members",
		"",
		render_markdown_table(
			[
				"component_id",
				"indicator_id",
				"bound_segment_id",
				"matching_rows",
				"non_matching_rows",
				"sbo_short_description",
			],
			indicator_members,
		),
		"",
		"### Evidence Status Counts",
		"",
	]
	status_rows = [
		[escape_markdown_table_cell(status or "(blank evidence_status)"), str(count)]
		for status, count in sorted(status_counts.items(), key=lambda item: (-item[1], item[0].lower()))
	]
	if status_rows:
		parts.append(render_markdown_table(["evidence_status", "count"], status_rows))
	else:
		parts.append("No scored rows.")
	parts.extend([
		"",
		"### Indicator-Segment Texts Summary",
		"",
		"#### Matching Segment Texts Summary",
		"",
	])
	matching_summary_rows = build_segment_summary_rows(matching_segment_counts, "present")
	if matching_summary_rows:
		parts.append(render_markdown_table(["evidence_status", "segment_text", "count"], matching_summary_rows))
	else:
		parts.append("No matching segment texts.")
	parts.extend([
		"",
		"#### Non-Matching Segment Texts Summary",
		"",
	])
	non_matching_summary_rows = build_segment_summary_rows(non_matching_segment_counts, "not_present")
	if non_matching_summary_rows:
		parts.append(render_markdown_table(["evidence_status", "segment_text", "count"], non_matching_summary_rows))
	else:
		parts.append("No non-matching segment texts.")
	parts.extend([
		"",
		"### Indicator-Segment Texts Detail",
		"",
		"#### Matching Segment Texts Detail",
		"",
	])
	matching_detail_rows = build_segment_detail_rows(matching_detail_entries)
	if matching_detail_rows:
		parts.append(render_markdown_table(["original_submission", "segment_text"], matching_detail_rows))
	else:
		parts.append("No matching segment details.")
	parts.extend([
		"",
		"#### Non-Matching Segment Texts Detail",
		"",
	])
	non_matching_detail_rows = build_segment_detail_rows(non_matching_detail_entries)
	if non_matching_detail_rows:
		parts.append(render_markdown_table(["original_submission", "segment_text"], non_matching_detail_rows))
	else:
		parts.append("No non-matching segment details.")
	parts.append("")
	return "\n".join(parts)


def build_comparison_diff_rows(
	component_ids: list[str],
	current_rows_by_component: dict[str, list[dict[str, str]]],
	previous_rows_by_component: dict[str, list[dict[str, str]]],
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
	history_labels: list[str],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
) -> list[list[str]]:
	display_history_labels = derive_display_history_labels(history_labels)
	indexes_by_label: dict[str, dict[str, dict[tuple[str, str], dict[str, str]]]] = {}
	for history_label in history_labels:
		component_indexes: dict[str, dict[tuple[str, str], dict[str, str]]] = {}
		for component_id, rows in historical_rows_by_label.get(history_label, {}).items():
			component_indexes[component_id] = {
				(
					(row.get("indicator_id") or "").strip(),
					(row.get("submission_id") or "").strip(),
				): row
				for row in rows
				if (row.get("indicator_id") or "").strip() and (row.get("submission_id") or "").strip()
			}
		indexes_by_label[history_label] = component_indexes

	history_rows: list[list[str]] = []
	for changed_row in changed_diff_rows:
		component_id, indicator_id, submission_id = changed_row[:3]
		row_values = [component_id, indicator_id, submission_id]
		for history_label in display_history_labels:
			row = indexes_by_label.get(history_label, {}).get(component_id, {}).get((indicator_id, submission_id))
			row_values.append(summarize_score_value(row.get("evidence_status") or "") if row is not None else "")
		history_rows.append(row_values)
	return history_rows


def build_indicator_delta_rows(
	component_ids: list[str],
	history_labels: list[str],
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
) -> list[list[str]]:
	display_history_labels = derive_display_history_labels(history_labels)
	display_history_pairs = derive_display_history_pairs(history_labels)
	counts_by_indicator = build_indicator_counts_by_label(
		component_ids,
		history_labels,
		historical_rows_by_label,
	)

	rows: list[list[str]] = []
	for indicator_id in sorted(counts_by_indicator, key=indicator_sort_key):
		row = [indicator_id]
		positive_counts_by_iteration = {
			history_label: counts_by_indicator[indicator_id].get(history_label, {}).get("positive", 0)
			for history_label in history_labels
		}
		row.extend(str(positive_counts_by_iteration[history_label]) for history_label in display_history_labels)
		for previous_label, current_label in display_history_pairs:
			previous_count = positive_counts_by_iteration[previous_label]
			current_count = positive_counts_by_iteration[current_label]
			number_scored = counts_by_indicator[indicator_id].get(current_label, {}).get("number_scored", 0)
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


def format_source_scored_csvs_label(scored_csv_paths: list[Path]) -> str:
	if not scored_csv_paths:
		return ""
	if len(scored_csv_paths) == 1:
		common_prefix = scored_csv_paths[0].parent
	else:
		common_prefix = Path(commonpath([str(path) for path in scored_csv_paths]))
	prefix_label = str(common_prefix)
	if not prefix_label.endswith("/"):
		prefix_label = f"{prefix_label}/"
	suffix_labels: list[str] = []
	for path in scored_csv_paths:
		try:
			suffix_labels.append(str(path.relative_to(common_prefix)))
		except ValueError:
			suffix_labels.append(path.name)
	return "<br>".join([prefix_label, *suffix_labels])


def insert_blank_rows_between_groups(rows: list[list[str]], group_keys: list[object]) -> list[list[str]]:
	if not rows:
		return rows
	grouped_rows: list[list[str]] = []
	previous_group_key = None
	column_count = len(rows[0])
	for row, group_key in zip(rows, group_keys):
		if previous_group_key is not None and group_key != previous_group_key:
			grouped_rows.append([""] * column_count)
		grouped_rows.append(row)
		previous_group_key = group_key
	return grouped_rows


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
	positive_observation_keys_by_template: dict[str, list[tuple[str, str]]],
	positive_presence_keys_by_template: dict[str, set[tuple[str, str]]],
) -> dict[str, dict[str, int]]:
	count_matrix: dict[str, dict[str, int]] = {}
	for row_template_id in template_ids:
		count_matrix[row_template_id] = {}
		row_observation_keys = positive_observation_keys_by_template.get(row_template_id, [])
		for column_template_id in template_ids:
			column_presence_keys = positive_presence_keys_by_template.get(column_template_id, set())
			count_matrix[row_template_id][column_template_id] = sum(
				1 for observation_key in row_observation_keys if observation_key in column_presence_keys
			)
	return count_matrix


def render_coincidence_matrix(
	template_ids: list[str],
	positive_observation_keys_by_template: dict[str, list[tuple[str, str]]],
	positive_presence_keys_by_template: dict[str, set[tuple[str, str]]],
	as_percentage: bool,
) -> str:
	labels_by_template = derive_unique_template_labels(template_ids)
	count_matrix = build_coincidence_count_matrix(
		template_ids,
		positive_observation_keys_by_template,
		positive_presence_keys_by_template,
	)
	headers = ["template", *[labels_by_template[template_id] for template_id in template_ids]]
	rows: list[list[str]] = []

	for row_template_id in template_ids:
		row_values = [labels_by_template[row_template_id]]
		row_denominator = len(positive_observation_keys_by_template.get(row_template_id, []))
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


def base_summary_sort_key(base_row: dict[str, object]) -> tuple[int, str, str]:
	return base_table_sort_key([
		str(base_row["template_id"]),
		str(base_row["local_slot"]),
	])


def build_indicator_order_maps(
	component_ids: list[str],
	base_summary_rows: dict[str, dict[str, object]],
	base_row_reverse_lookup: dict[tuple[str, str], dict[str, str]],
) -> tuple[dict[str, tuple[int, int, str]], dict[tuple[str, str], tuple[int, int, int, str, str]]]:
	template_indicator_order: dict[tuple[str, str], int] = {}
	indicator_order: dict[str, tuple[int, int, str]] = {}
	for template_rank, base_key in enumerate(sorted(base_summary_rows, key=lambda key: base_summary_sort_key(base_summary_rows[key]))):
		base_row = base_summary_rows[base_key]
		for indicator_rank, indicator_id in enumerate(sorted(base_row["expanded_indicator_ids"])):
			template_indicator_order[(str(base_row["template_id"]), indicator_id)] = indicator_rank
			indicator_order.setdefault(indicator_id, (template_rank, indicator_rank, indicator_id.lower()))

	component_position = {component_id: index for index, component_id in enumerate(component_ids)}
	component_indicator_order: dict[tuple[str, str], tuple[int, int, int, str, str]] = {}
	for component_indicator_key, base_row_info in base_row_reverse_lookup.items():
		component_id, indicator_id = component_indicator_key
		template_id = base_row_info.get("template_id", "")
		default_indicator_order = indicator_order.get(
			indicator_id,
			(10**9, 10**9, indicator_id.lower()),
		)
		component_indicator_order[component_indicator_key] = (
			default_indicator_order[0],
			template_indicator_order.get((template_id, indicator_id), default_indicator_order[1]),
			component_position.get(component_id, 10**9),
			indicator_id.lower(),
			component_id.lower(),
		)

	return indicator_order, component_indicator_order


def indicator_row_sort_key(
	row: list[str],
	component_indicator_order: dict[tuple[str, str], tuple[int, int, int, str, str]],
) -> tuple[int, int, int, str, str]:
	component_id = row[0]
	indicator_id = row[1]
	return component_indicator_order.get(
		(component_id, indicator_id),
		(10**9, 10**9, 10**9, indicator_id.lower(), component_id.lower()),
	)


def indicator_only_row_sort_key(
	row: list[str],
	indicator_order: dict[str, tuple[int, int, str]],
) -> tuple[int, int, str]:
	indicator_id = row[0]
	return indicator_order.get(indicator_id, (10**9, 10**9, indicator_id.lower()))


def diff_row_sort_key(
	row: list[str],
	component_indicator_order: dict[tuple[str, str], tuple[int, int, int, str, str]],
) -> tuple[int, int, int, str, str, str, str]:
	component_id = row[0]
	indicator_id = row[1]
	submission_id = row[2]
	indicator_key = component_indicator_order.get(
		(component_id, indicator_id),
		(10**9, 10**9, 10**9, indicator_id.lower(), component_id.lower()),
	)
	extra = tuple(cell.lower() for cell in row[3:])
	return (*indicator_key, submission_id.lower(), *extra)


def component_indicator_group_key(
	row: list[str],
	component_indicator_order: dict[tuple[str, str], tuple[int, int, int, str, str]],
) -> tuple[int, int]:
	component_id = row[0]
	indicator_id = row[1]
	order = component_indicator_order.get(
		(component_id, indicator_id),
		(10**9, 10**9, 10**9, indicator_id.lower(), component_id.lower()),
	)
	return (order[0], order[1])


def component_template_group_key(
	row: list[str],
	component_indicator_order: dict[tuple[str, str], tuple[int, int, int, str, str]],
) -> int:
	component_id = row[0]
	indicator_id = row[1]
	order = component_indicator_order.get(
		(component_id, indicator_id),
		(10**9, 10**9, 10**9, indicator_id.lower(), component_id.lower()),
	)
	return order[0]


def indicator_template_group_key(
	row: list[str],
	indicator_order: dict[str, tuple[int, int, str]],
) -> int:
	indicator_id = row[0]
	order = indicator_order.get(indicator_id, (10**9, 10**9, indicator_id.lower()))
	return order[0]


def is_positive_scored_row(row: dict[str, str]) -> bool:
	status = (row.get("evidence_status") or "").strip().lower()
	return status in POSITIVE_EVIDENCE_STATUS_VALUES


def render_consolidated_scoring_stats_document(
	output_path: Path,
	registry_path: Path,
	base_row_reverse_lookup: dict[tuple[str, str], dict[str, str]],
	component_ids: list[str],
	manifest_path: Path,
	comparison_scope: str,
	current_label: str,
	history_labels: list[str],
	previous_label: str | None,
	sample_size: int,
	scored_csv_paths: list[Path],
	total_scored_rows: int,
	indicator_delta_rows: list[list[str]],
	stability_labels: list[str],
	stability_sections: dict[str, list[list[str]]],
	added_diff_rows: list[list[str]],
	removed_diff_rows: list[list[str]],
	changed_score_history_rows: list[list[str]],
	missing_previous_components: list[str],
	indicator_rows: list[list[str]],
	base_rows: list[list[str]],
	indicator_order: dict[str, tuple[int, int, str]],
	component_indicator_order: dict[tuple[str, str], tuple[int, int, int, str, str]],
	coincidence_count_matrix: str,
	coincidence_percent_matrix: str,
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]],
) -> str:
	component_label = component_ids[0] if len(component_ids) == 1 else ", ".join(component_ids)
	source_csv_label = format_source_scored_csvs_label(scored_csv_paths)
	comparison_axis_label = "run" if comparison_scope == "run" else "iteration endpoint"
	stability_title = "Run Repeatability Flags" if comparison_scope == "run" else "Stability Flags"
	if comparison_scope == "run":
		stability_description_lines = [
			"Run-scope repeatability flags are computed across all resolved runs for the current iteration.",
			"Each consecutive run-to-run delta contributes to the summary metrics, and `max_delta` / `range_delta` summarize the full run history rather than only the most recent pair.",
		]
	else:
		stability_description_lines = [
			"Iteration-scope stability flags are computed from exactly two consecutive iteration-endpoint comparisons.",
			"The section uses the latest three resolvable iteration endpoints ending at the current run, so the stability signal stays anchored to recent iteration-to-iteration movement even when the diff report baseline is set explicitly.",
		]
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
	delta_table_headers = build_delta_table_headers(history_labels)
	parts = [
		render_yaml_frontmatter(output_path, comparison_scope, current_label, history_labels, manifest_path, registry_path, component_ids, scored_csv_paths),
		f"## {output_path.name.removesuffix('.md')}",
		"",
		"Saturation rate is defined here as number_scored_positive divided by number_scored for each indicator.",
		"Percent co-incidence values are row-conditional: each populated cell shows the share of positive samples for the row template that were also positive for the column template.",
		"Important: the Base Table saturation section and the co-incidence matrices use different counting semantics.",
		"The Base Table saturation section aggregates summed indicator-instance counts across the expanded indicators mapped to each template.",
		"The co-incidence matrices instead operate at the submission level: for a template, a submission counts as positive only if it is positive for every expanded indicator mapped to that template across the included components.",
		"",
		"### Overview",
		"",
		render_markdown_table(
			["metric", "value"],
			[
				["comparison_scope", comparison_scope],
				["current_label", current_label],
				["comparison_axis", comparison_axis_label],
				["history_labels", ", ".join(history_labels)],
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
			insert_blank_rows_between_groups(
				indicator_rows,
				[
					component_template_group_key(row, component_indicator_order)
					for row in indicator_rows
				],
			),
		),
		"",
		"### Indicator saturation, base",
		"",
		render_markdown_table(base_table_headers, base_rows),
		"",
		"### Co-incidence matrix",
		"",
		"Interpretation: each cell is a directional raw overlap count over positive row observations.",
		"For row template R and column template C, the number is the count of positive observations contributing to R's Base Table number_scored_positive whose (component_id, submission_id) pair is also positive for C.",
		"This count matrix is not generally symmetric: the value at (R, C) need not match the value at (C, R).",
		"Diagonal cells equal the row template's Base Table number_scored_positive, because every positive row observation for R overlaps with itself.",
		"",
		coincidence_count_matrix,
		"",
		"### Co-incidence matrix, row-conditional percent",
		"",
		"Interpretation: each cell is directional over the same positive row observations used in the raw count matrix.",
		"For a row template R and column template C, the value is the percentage of R's positive row observations whose (component_id, submission_id) pair is also positive for C.",
		"This percent matrix is not generally symmetric: the value at (R, C) need not match the value at (C, R).",
		"Diagonal cells are 100% when the row template has at least one positive sample, because every positive sample for R overlaps with itself.",
		"",
		coincidence_percent_matrix,
		"",
	]
	diff_report_parts = ["### Diff Report", ""]
	if previous_label is None:
		diff_report_parts.extend([f"Previous {comparison_axis_label} could not be derived from the current inputs.", ""])
	else:
		diff_report_parts.extend(
			[
			f"Current {comparison_axis_label}: {current_label}",
			f"Previous {comparison_axis_label}: {previous_label}",
			]
		)
		if missing_previous_components:
			diff_report_parts.append(
				f"Previous {comparison_axis_label} scored CSVs were not found for: " + ", ".join(sorted(missing_previous_components))
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
							f"{current_label}-score",
						],
							insert_blank_rows_between_groups(
								added_diff_rows,
								[
									component_template_group_key(row, component_indicator_order)
									for row in added_diff_rows
								],
							),
					),
				]
			)
		else:
			diff_report_parts.extend(["", "#### Added Rows", "", f"No added rows found relative to the previous {comparison_axis_label}."])
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
							f"{previous_label}-score",
						],
							insert_blank_rows_between_groups(
								removed_diff_rows,
								[
									component_template_group_key(row, component_indicator_order)
									for row in removed_diff_rows
								],
							),
					),
				]
			)
		else:
			diff_report_parts.extend(["", "#### Removed Rows", "", f"No removed rows found relative to the previous {comparison_axis_label}."])
		if changed_score_history_rows:
			display_history_labels = derive_display_history_labels(history_labels)
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
							*[f"{history_label}-score" for history_label in display_history_labels],
						],
							insert_blank_rows_between_groups(
								changed_score_history_rows,
								[
									component_template_group_key(row, component_indicator_order)
									for row in changed_score_history_rows
								],
							),
					),
				]
			)
		else:
			diff_report_parts.extend(["", "#### Changed Scores", "", f"No score changes found between the current and previous {comparison_axis_label}."])
		diff_report_parts.extend(
			[
				"",
				"#### Delta Table",
				"",
				render_markdown_table(
					delta_table_headers,
					insert_blank_rows_between_groups(
						indicator_delta_rows,
						[
							indicator_template_group_key(row, indicator_order)
							for row in indicator_delta_rows
						],
					),
				),
			]
		)
		diff_report_parts.extend(["", f"#### {stability_title}", ""])
		diff_report_parts.extend(stability_description_lines)
		diff_report_parts.append("")
		if len(stability_labels) < 3:
			diff_report_parts.extend(
				[
					f"At least three labels are required to compute {stability_title.lower()}; available labels: {', '.join(stability_labels or history_labels)}.",
				]
			)
		else:
			stability_headers = build_stability_table_headers(stability_labels)
			diff_report_parts.extend(
				[
					f"sample_size: {sample_size}",
					f"Labels used: {', '.join(stability_labels)}",
				]
			)
			for classification in ["stable", "low_variance", "borderline_unstable", "unstable"]:
				diff_report_parts.extend(["", f"##### {classification}", ""])
				rows = stability_sections.get(classification, [])
				if rows:
					diff_report_parts.append(
						render_markdown_table(
							stability_headers,
							insert_blank_rows_between_groups(
								rows,
								[
									indicator_template_group_key(row, indicator_order)
									for row in rows
								],
							),
						)
					)
				else:
					diff_report_parts.append("No indicators.")
			if comparison_scope == "run":
				intra_report_variance_summary_rows = build_intra_report_variance_summary_rows(
					stability_labels,
					indicator_rows,
					historical_rows_by_label,
					sample_size,
				)
				template_counts_by_label = build_template_counts_by_label(
					component_ids,
					stability_labels,
					historical_rows_by_label,
					base_row_reverse_lookup,
				)
				template_component_counts_by_label = build_template_component_counts_by_label(
					component_ids,
					stability_labels,
					historical_rows_by_label,
					base_row_reverse_lookup,
				)
				template_item_histories = build_item_histories_by_template(
					stability_labels,
					historical_rows_by_label,
					base_row_reverse_lookup,
				)
				template_component_item_histories = build_item_histories_by_template_component(
					stability_labels,
					historical_rows_by_label,
					base_row_reverse_lookup,
				)
				intra_report_template_variance_summary_rows = build_intra_report_template_variance_summary_rows(
					stability_labels,
					base_rows,
					template_counts_by_label,
					template_item_histories,
					template_component_counts_by_label,
					template_component_item_histories,
					sample_size,
				)
				diff_report_parts.extend([
					"",
					"#### Indicator Variance Summary (Individual)",
					"",
					f"Source report: {output_path.name}",
					build_run_pattern_note(len(stability_labels)),
					build_item_metric_note(),
					"",
				])
				if intra_report_variance_summary_rows:
					diff_report_parts.append(
						render_markdown_table(
							[
								"component_id",
								"indicator_id",
								"sbo_short_description",
								"adjacent_deltas",
								"run_pattern",
								"max_item_disagreement",
								"flip_rate",
								"consensus_rate (target ≥ 0.95)",
								"ici (target ≤ 0.10)",
								"max_delta",
								"variance_rate (target ≤ 0.05)",
								"stable",
								"low_variance",
								"borderline_unstable",
								"unstable",
							],
							insert_blank_rows_between_groups(
								intra_report_variance_summary_rows,
								[
									component_template_group_key(row, component_indicator_order)
									for row in intra_report_variance_summary_rows
								],
							),
						)
					)
				else:
					diff_report_parts.append("No indicators.")
				diff_report_parts.extend([
					"",
					"#### Indicator Variance Summary (Template)",
					"",
					f"Source report: {output_path.name}",
					build_run_pattern_note(len(stability_labels)),
					"For template rows, adjacent_deltas and run_pattern are derived from pooled template deltas; flip_rate, consensus_rate, and ici are recomputed from pooled item labels; max_item_disagreement is the maximum component-level disagreement count; variance_rate is the maximum component-level variance_rate across contributing components.",
					build_item_metric_note(),
					"",
				])
				if intra_report_template_variance_summary_rows:
					diff_report_parts.append(
						render_markdown_table(
							[
								"template_id",
								"local_slot",
								"expanded_indicator_ids",
								"sbo_short_description",
								"adjacent_deltas",
								"run_pattern",
								"max_item_disagreement",
								"flip_rate",
								"consensus_rate (target ≥ 0.95)",
								"ici (target ≤ 0.10)",
								"max_delta",
								"variance_rate (target ≤ 0.05)",
								"stable",
								"low_variance",
								"borderline_unstable",
								"unstable",
							],
							intra_report_template_variance_summary_rows,
						)
					)
				else:
					diff_report_parts.append("No templates.")
			else:
				inter_report_saturation_summary_rows = build_inter_report_saturation_summary_rows(
					previous_label,
					current_label,
					indicator_rows,
					historical_rows_by_label,
				)
				diff_report_parts.extend(["", "#### Indicator Saturation Summary", ""])
				if previous_label is None:
					diff_report_parts.append("Previous comparison label could not be derived.")
				elif inter_report_saturation_summary_rows:
					diff_report_parts.append(
						render_markdown_table(
							[
								"component_id",
								"indicator_id",
								"sbo_short_description",
								f"{previous_label}_saturation_rate",
								f"{current_label}_saturation_rate",
							],
							insert_blank_rows_between_groups(
								inter_report_saturation_summary_rows,
								[
									component_template_group_key(row, component_indicator_order)
									for row in inter_report_saturation_summary_rows
								],
							),
						)
					)
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
	comparison_scope = args.comparison_scope
	iteration_label = derive_iteration_label(manifest_path, args.iteration_label)
	run_label = derive_run_label(scored_csv_input_refs[0] if scored_csv_input_refs else manifest_path, args.run_label)
	baseline_iteration_label = args.baseline_iteration_label.strip().lower() if args.baseline_iteration_label else None
	baseline_run_label = args.baseline_run_label.strip().lower() if args.baseline_run_label else None
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
	if comparison_scope == "run" and run_label is None:
		print(
			"Error: run-scope comparisons require a run label derivable from --run-label or the scored input paths.",
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
	if comparison_scope == "run":
		comparison_entries = build_run_comparison_entries(iteration_label, run_label)
		stability_entries = comparison_entries
		current_label = run_label
	else:
		comparison_entries = build_iteration_comparison_entries(
			current_iteration_label=iteration_label,
			current_run_label=run_label,
			baseline_iteration_label=baseline_iteration_label,
			baseline_run_label=baseline_run_label,
			component_ids=component_ids,
			current_input_refs=scored_csv_input_refs,
		)
		stability_entries = build_iteration_stability_entries(
			current_iteration_label=iteration_label,
			current_run_label=run_label,
			component_ids=component_ids,
			current_input_refs=scored_csv_input_refs,
		)
		current_label = format_iteration_run_label(iteration_label, run_label)
	history_labels = [entry.label for entry in comparison_entries]
	stability_labels_for_loading = [entry.label for entry in stability_entries]
	labels_for_count_loading = list(dict.fromkeys([*history_labels, *stability_labels_for_loading]))
	all_comparison_entries: dict[str, ComparisonEntry] = {
		entry.label: entry for entry in [*comparison_entries, *stability_entries]
	}
	historical_rows_by_label: dict[str, dict[str, list[dict[str, str]]]] = {
		current_label: dict(scored_rows_by_component)
	}
	for comparison_entry in all_comparison_entries.values():
		if comparison_entry.label == current_label:
			continue
		historical_rows_by_label[comparison_entry.label] = {}
		for component_id, scored_csv_input_ref in zip(component_ids, scored_csv_input_refs):
			history_scored_csv_paths = derive_scored_csv_paths_for_iteration(
				scored_csv_input_ref,
				component_id,
				iteration_label,
				comparison_entry.iteration_label,
				run_label,
				comparison_entry.run_label,
			)
			if not history_scored_csv_paths:
				continue
			historical_rows_by_label[comparison_entry.label][component_id] = load_scored_rows_from_paths(
				history_scored_csv_paths
			)
	previous_label = history_labels[-2] if len(history_labels) >= 2 else None
	previous_rows_by_component: dict[str, list[dict[str, str]]] = {}
	missing_previous_components: list[str] = []
	if previous_label is not None:
		previous_entry = next((entry for entry in comparison_entries if entry.label == previous_label), None)
		for component_id, scored_csv_input_ref in zip(component_ids, scored_csv_input_refs):
			if previous_entry is None:
				missing_previous_components.append(component_id)
				continue
			previous_scored_csv_paths = derive_scored_csv_paths_for_iteration(
				scored_csv_input_ref,
				component_id,
				iteration_label,
				previous_entry.iteration_label,
				run_label,
				previous_entry.run_label,
			)
			if not previous_scored_csv_paths:
				missing_previous_components.append(component_id)
				continue
			previous_rows_by_component[component_id] = load_scored_rows_from_paths(previous_scored_csv_paths)
	indicator_delta_rows = build_indicator_delta_rows(
		component_ids,
		history_labels,
		historical_rows_by_label,
	)
	counts_by_indicator = build_indicator_counts_by_label(
		component_ids,
		labels_for_count_loading,
		historical_rows_by_label,
	)
	stability_labels, stability_sections = build_indicator_stability_sections(
		stability_labels_for_loading,
		counts_by_indicator,
		sample_size,
	)
	added_diff_rows, removed_diff_rows, changed_diff_rows = build_comparison_diff_rows(
		component_ids,
		scored_rows_by_component,
		previous_rows_by_component,
	)
	changed_score_history_rows = build_changed_score_history_rows(
		changed_diff_rows,
		history_labels,
		historical_rows_by_label,
	)
	total_scored_rows = sum(len(rows) for rows in scored_rows_by_component.values())
	lines = manifest_path.read_text(encoding="utf-8").splitlines()
	indicator_summary_rows: dict[str, list[str]] = {}
	indicator_segment_specs: dict[tuple[str, str], dict[str, str]] = {}
	base_summary_rows: dict[str, dict[str, object]] = {}
	positive_observation_keys_by_template: dict[str, list[tuple[str, str]]] = {}
	positive_presence_keys_by_template: dict[str, set[tuple[str, str]]] = {}

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
				payload = parse_json_object((components.get("indicator_scoring_payload_json") or "").strip())
				indicator_segment_specs[(matching_component_id, indicator_id)] = {
					"component_id": matching_component_id,
					"indicator_id": indicator_id,
					"sbo_identifier": (components.get("sbo_identifier") or "").strip(),
					"sbo_short_description": (components.get("sbo_short_description") or "").strip(),
					"bound_segment_id": str(payload.get("bound_segment_id") or "").strip(),
				}
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
						positive_observation_keys_by_template[base_key] = []
						positive_presence_keys_by_template[base_key] = set()
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
							observation_key = (matching_component_id, submission_id)
							positive_observation_keys_by_template[base_key].append(observation_key)
							positive_presence_keys_by_template[base_key].add(observation_key)
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
	indicator_order, component_indicator_order = build_indicator_order_maps(
		component_ids,
		base_summary_rows,
		base_row_reverse_lookup,
	)
	consolidated_indicator_rows.sort(
		key=lambda row: indicator_row_sort_key(row, component_indicator_order)
	)
	added_diff_rows.sort(key=lambda row: diff_row_sort_key(row, component_indicator_order))
	removed_diff_rows.sort(key=lambda row: diff_row_sort_key(row, component_indicator_order))
	changed_score_history_rows.sort(key=lambda row: diff_row_sort_key(row, component_indicator_order))
	indicator_delta_rows.sort(key=lambda row: indicator_only_row_sort_key(row, indicator_order))
	for classification_rows in stability_sections.values():
		classification_rows.sort(key=lambda row: indicator_only_row_sort_key(row, indicator_order))
	ordered_template_ids = [row[0] for row in consolidated_base_rows]
	coincidence_count_matrix = render_coincidence_matrix(
		ordered_template_ids,
		positive_observation_keys_by_template,
		positive_presence_keys_by_template,
		False,
	)
	coincidence_percent_matrix = render_coincidence_matrix(
		ordered_template_ids,
		positive_observation_keys_by_template,
		positive_presence_keys_by_template,
		True,
	)
	consolidated_output_path = output_dir / derive_output_filename(
		component_ids,
		manifest_path,
		comparison_scope,
		current_label,
		iteration_label,
		run_label,
		previous_label,
	)
	consolidated_output_path.write_text(
		render_consolidated_scoring_stats_document(
			output_path=consolidated_output_path,
			registry_path=registry_path,
			base_row_reverse_lookup=base_row_reverse_lookup,
			component_ids=component_ids,
			manifest_path=manifest_path,
			comparison_scope=comparison_scope,
			current_label=current_label,
			history_labels=history_labels,
			previous_label=previous_label,
			sample_size=sample_size,
			scored_csv_paths=scored_csv_paths,
			total_scored_rows=total_scored_rows,
			indicator_delta_rows=indicator_delta_rows,
			stability_labels=stability_labels,
			stability_sections=stability_sections,
			added_diff_rows=added_diff_rows,
			removed_diff_rows=removed_diff_rows,
			changed_score_history_rows=changed_score_history_rows,
			missing_previous_components=missing_previous_components,
			indicator_rows=consolidated_indicator_rows,
			base_rows=consolidated_base_rows,
			indicator_order=indicator_order,
			component_indicator_order=component_indicator_order,
			coincidence_count_matrix=coincidence_count_matrix,
			coincidence_percent_matrix=coincidence_percent_matrix,
				historical_rows_by_label=historical_rows_by_label,
		),
		encoding="utf-8",
	)
	input_rows_by_component_submission: dict[str, dict[tuple[str, str], dict[str, str]]] = {}
	input_csv_path_by_component: dict[str, Path] = {}
	scored_csv_path_by_component: dict[str, Path] = {}
	stitched_csv_path_by_component: dict[str, Path] = {}
	source_rows_by_component_submission: dict[str, dict[tuple[str, str], dict[str, str]]] = {}
	stitched_rows_by_path: dict[Path, dict[tuple[str, str], dict[str, str]]] = {}
	slot_group_reports: dict[str, dict[str, object]] = {}
	for component_id in component_ids:
		resolved_scored_paths = component_scored_csv_paths.get(component_id, [])
		if not resolved_scored_paths:
			continue
		scored_csv_path_by_component[component_id] = resolved_scored_paths[0]
		input_csv_path = derive_layer1_input_csv_path_from_scored_csv(resolved_scored_paths[0], component_id)
		if input_csv_path is None or not input_csv_path.exists() or not input_csv_path.is_file():
			continue
		input_csv_path_by_component[component_id] = input_csv_path
		input_rows_by_component_submission[component_id] = index_input_rows_by_component_submission(
			load_scored_rows(input_csv_path)
		)
		stitched_csv_path = derive_layer0_stitched_csv_path_from_scored_csv(resolved_scored_paths[0])
		if stitched_csv_path is None or not stitched_csv_path.exists() or not stitched_csv_path.is_file():
			continue
		stitched_csv_path_by_component[component_id] = stitched_csv_path
		stitched_index = stitched_rows_by_path.get(stitched_csv_path)
		if stitched_index is None:
			stitched_index = index_input_rows_by_component_submission(load_scored_rows(stitched_csv_path))
			stitched_rows_by_path[stitched_csv_path] = stitched_index
		source_rows_by_component_submission[component_id] = stitched_index
	for component_id, indicator_id in sorted(
		indicator_segment_specs,
		key=lambda key: component_indicator_order.get(
			key,
			(10**9, 10**9, 10**9, key[1].lower(), key[0].lower()),
		),
	):
		indicator_spec = indicator_segment_specs[(component_id, indicator_id)]
		base_row_info = base_row_reverse_lookup.get((component_id, indicator_id), {})
		local_slot = (base_row_info.get("local_slot") or "").strip()
		template_id = (base_row_info.get("template_id") or "").strip()
		bound_segment_id = indicator_spec.get("bound_segment_id", "")
		segment_field = f"segment_text_{component_id}__{bound_segment_id}" if bound_segment_id else ""
		status_counts: Counter[str] = Counter()
		matching_segment_counts: Counter[str] = Counter()
		non_matching_segment_counts: Counter[str] = Counter()
		matching_detail_entries: list[tuple[str, str]] = []
		non_matching_detail_entries: list[tuple[str, str]] = []
		matching_detail_seen_entries: set[tuple[str, str]] = set()
		non_matching_detail_seen_entries: set[tuple[str, str]] = set()
		matching_row_count = 0
		non_matching_row_count = 0
		missing_input_row_count = 0
		input_rows_index = input_rows_by_component_submission.get(component_id, {})
		source_rows_index = source_rows_by_component_submission.get(component_id, {})
		for scored_row in scored_rows_by_component.get(component_id, []):
			if (scored_row.get("indicator_id") or "").strip() != indicator_id:
				continue
			evidence_status = (scored_row.get("evidence_status") or "").strip()
			status_counts[evidence_status or "(blank evidence_status)"] += 1
			submission_id = resolve_submission_id_from_row(scored_row)
			input_row = input_rows_index.get((component_id, submission_id))
			source_row = source_rows_index.get((component_id, submission_id))
			source_submission_entry = format_source_submission_entry(
				component_id,
				submission_id,
				(source_row.get("source_response_text") or "") if source_row is not None else "",
			)
			if input_row is None:
				segment_bucket = "(missing Layer 1 input row)"
				missing_input_row_count += 1
			else:
				segment_value = (input_row.get(segment_field) or "").strip() if segment_field else (input_row.get("evidence_text") or "").strip()
				segment_bucket = normalize_segment_bucket_label(segment_value)
			if is_positive_scored_row(scored_row):
				matching_segment_counts[segment_bucket] += 1
				append_segment_detail_row(
					matching_detail_entries,
					matching_detail_seen_entries,
					source_submission_entry,
					segment_bucket,
				)
				matching_row_count += 1
			else:
				non_matching_segment_counts[segment_bucket] += 1
				append_segment_detail_row(
					non_matching_detail_entries,
					non_matching_detail_seen_entries,
					source_submission_entry,
					segment_bucket,
				)
				non_matching_row_count += 1
		indicator_output_path = output_dir / derive_indicator_segment_report_filename(
			manifest_path,
			component_id,
			indicator_id,
			comparison_scope,
			current_label,
			iteration_label,
			run_label,
		)
		indicator_output_path.write_text(
			render_indicator_segment_report(
				output_path=indicator_output_path,
				manifest_path=manifest_path,
				comparison_scope=comparison_scope,
				current_label=current_label,
				component_id=component_id,
				indicator_id=indicator_id,
				sbo_identifier=indicator_spec.get("sbo_identifier", ""),
				sbo_short_description=indicator_spec.get("sbo_short_description", ""),
				bound_segment_id=bound_segment_id,
				segment_field=segment_field,
				scored_csv_path=scored_csv_path_by_component.get(component_id),
				input_csv_path=input_csv_path_by_component.get(component_id),
				status_counts=status_counts,
				matching_segment_counts=matching_segment_counts,
				non_matching_segment_counts=non_matching_segment_counts,
				matching_detail_entries=matching_detail_entries,
				non_matching_detail_entries=non_matching_detail_entries,
				matching_row_count=matching_row_count,
				non_matching_row_count=non_matching_row_count,
				missing_input_row_count=missing_input_row_count,
			),
			encoding="utf-8",
		)
		if local_slot:
			group_report = slot_group_reports.setdefault(
				local_slot,
				{
					"template_ids": set(),
					"indicator_members": [],
					"status_counts": Counter(),
					"matching_segment_counts": Counter(),
					"non_matching_segment_counts": Counter(),
					"matching_detail_entries": [],
					"non_matching_detail_entries": [],
					"matching_detail_seen_entries": set(),
					"non_matching_detail_seen_entries": set(),
					"matching_row_count": 0,
					"non_matching_row_count": 0,
					"missing_input_row_count": 0,
				},
			)
			if template_id:
				group_report["template_ids"].add(template_id)
			group_report["indicator_members"].append(
				[
					component_id,
					indicator_id,
					bound_segment_id,
					str(matching_row_count),
					str(non_matching_row_count),
					indicator_spec.get("sbo_short_description", ""),
				]
			)
			group_report["status_counts"].update(status_counts)
			group_report["matching_segment_counts"].update(matching_segment_counts)
			group_report["non_matching_segment_counts"].update(non_matching_segment_counts)
			for entry, segment_bucket in matching_detail_entries:
				append_segment_detail_row(
					group_report["matching_detail_entries"],
					group_report["matching_detail_seen_entries"],
					entry,
					segment_bucket,
				)
			for entry, segment_bucket in non_matching_detail_entries:
				append_segment_detail_row(
					group_report["non_matching_detail_entries"],
					group_report["non_matching_detail_seen_entries"],
					entry,
					segment_bucket,
				)
			group_report["matching_row_count"] += matching_row_count
			group_report["non_matching_row_count"] += non_matching_row_count
			group_report["missing_input_row_count"] += missing_input_row_count
	for local_slot, group_report in sorted(slot_group_reports.items(), key=lambda item: item[0]):
		group_report_output_path = output_dir / derive_indicator_slot_group_report_filename(
			manifest_path,
			local_slot,
			comparison_scope,
			current_label,
			iteration_label,
			run_label,
		)
		group_members = sorted(
			group_report["indicator_members"],
			key=lambda row: component_indicator_order.get(
				(row[0], row[1]),
				(10**9, 10**9, 10**9, row[1].lower(), row[0].lower()),
			),
		)
		group_report_output_path.write_text(
			render_indicator_slot_group_segment_report(
				output_path=group_report_output_path,
				manifest_path=manifest_path,
				comparison_scope=comparison_scope,
				current_label=current_label,
				local_slot=local_slot,
				template_ids=sorted(group_report["template_ids"]),
				indicator_members=group_members,
				status_counts=group_report["status_counts"],
				matching_segment_counts=group_report["matching_segment_counts"],
				non_matching_segment_counts=group_report["non_matching_segment_counts"],
				matching_detail_entries=group_report["matching_detail_entries"],
				non_matching_detail_entries=group_report["non_matching_detail_entries"],
				matching_row_count=int(group_report["matching_row_count"]),
				non_matching_row_count=int(group_report["non_matching_row_count"]),
				missing_input_row_count=int(group_report["missing_input_row_count"]),
			),
			encoding="utf-8",
		)
	print(consolidated_output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())