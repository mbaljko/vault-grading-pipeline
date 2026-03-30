#!/usr/bin/env python3
"""Execute deterministic Layer 2 dimension-scoring modules over a Layer 1 scored CSV.

This script loads a component-scoped Layer 1 scored CSV, groups rows by
submission_id, applies all generated Layer 2 dimension modules for the target
component, and writes one Layer 2 scored row per (submission, dimension).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

from component_scored_texts import load_scored_rows, write_scored_rows


LAYER1_REQUIRED_FIELDS = {"submission_id", "indicator_id", "evidence_status"}
CONFIDENCE_ORDER = {
	"low": 0,
	"medium": 1,
	"high": 2,
}
PASSTHROUGH_EXCLUDED_FIELDS = {
	"indicator_id",
	"dimension_id",
	"dimension_template_id",
	"sbo_identifier",
	"sbo_short_description",
	"indicator_definition",
	"assessment_guidance",
	"evaluation_notes",
	"decision_procedure",
	"confidence",
	"flags",
	"bound_indicator_ids",
	"evidence_status",
}
WIDE_EXCLUDED_FIELDS = PASSTHROUGH_EXCLUDED_FIELDS | {"source_indicator_values_json"}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Execute generated Layer 2 dimension-scoring modules over a Layer 1 scored CSV."
	)
	parser.add_argument("--layer1-scored-csv", type=Path, required=True)
	parser.add_argument("--module-dir", type=Path, required=True)
	parser.add_argument("--target-component-id", type=str, required=True)
	parser.add_argument("--output-file", type=Path, required=True)
	parser.add_argument("--submission-id-field", type=str, default="submission_id")
	parser.add_argument("--indicator-id-field", type=str, default="indicator_id")
	parser.add_argument("--value-field", type=str, default="evidence_status")
	return parser.parse_args()


def dimension_sort_key(dimension_id: str) -> tuple[int, str]:
	match = re.fullmatch(r"[A-Za-z]+(\d+)", dimension_id)
	if match is None:
		return (10**9, dimension_id)
	return (int(match.group(1)), dimension_id)


def derive_wide_output_path(output_path: Path) -> Path:
	return output_path.with_name(f"{output_path.stem}-wide{output_path.suffix}")


def load_module_from_path(module_path: Path, module_name: str) -> ModuleType:
	spec = importlib.util.spec_from_file_location(module_name, module_path)
	if spec is None or spec.loader is None:
		raise ValueError(f"Unable to load module spec from {module_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def validate_dimension_module(module: ModuleType, module_path: Path, target_component_id: str) -> None:
	for attribute_name in [
		"COMPONENT_ID",
		"DIMENSION_ID",
		"DIMENSION_TEMPLATE_ID",
		"SBO_IDENTIFIER",
		"SBO_SHORT_DESCRIPTION",
		"BOUND_INDICATOR_IDS",
		"score_dimension",
	]:
		if not hasattr(module, attribute_name):
			raise ValueError(f"Module {module_path} is missing required attribute: {attribute_name}")
	if str(getattr(module, "COMPONENT_ID", "")).strip() != target_component_id:
		raise ValueError(
			f"Module {module_path} is for component_id={getattr(module, 'COMPONENT_ID', '')}, expected {target_component_id}"
		)
	if not callable(getattr(module, "score_dimension", None)):
		raise ValueError(f"Module {module_path} does not expose a callable score_dimension function")
	bound_indicator_ids = getattr(module, "BOUND_INDICATOR_IDS", None)
	if not isinstance(bound_indicator_ids, list):
		raise ValueError(f"Module {module_path} has invalid BOUND_INDICATOR_IDS value")
	dimension_evidence_scale = getattr(module, "DIMENSION_EVIDENCE_SCALE", None)
	if dimension_evidence_scale is not None and not isinstance(dimension_evidence_scale, list):
		raise ValueError(f"Module {module_path} has invalid DIMENSION_EVIDENCE_SCALE value")


def load_dimension_modules(module_dir: Path, target_component_id: str) -> list[ModuleType]:
	if not module_dir.exists() or not module_dir.is_dir():
		raise FileNotFoundError(f"Module directory not found: {module_dir}")
	loaded_modules: list[ModuleType] = []
	seen_dimension_ids: set[str] = set()
	for index, module_path in enumerate(sorted(module_dir.glob("*.py"))):
		module = load_module_from_path(module_path, f"layer2_dimension_module_{index}")
		if str(getattr(module, "COMPONENT_ID", "")).strip() != target_component_id:
			continue
		validate_dimension_module(module, module_path, target_component_id)
		dimension_id = str(getattr(module, "DIMENSION_ID", "")).strip()
		if not dimension_id:
			raise ValueError(f"Module {module_path} is missing DIMENSION_ID")
		if dimension_id in seen_dimension_ids:
			raise ValueError(f"Duplicate DIMENSION_ID detected across modules: {dimension_id}")
		seen_dimension_ids.add(dimension_id)
		loaded_modules.append(module)
	if not loaded_modules:
		raise ValueError(f"No Layer 2 modules found for component_id={target_component_id} in {module_dir}")
	return sorted(loaded_modules, key=lambda module: dimension_sort_key(str(getattr(module, "DIMENSION_ID", ""))))


def validate_layer1_rows(rows: list[dict[str, str]], csv_path: Path) -> None:
	if not rows:
		raise ValueError(f"Layer 1 scored CSV is empty: {csv_path}")
	available_fields = set().union(*(row.keys() for row in rows))
	missing_fields = sorted(LAYER1_REQUIRED_FIELDS - available_fields)
	if missing_fields:
		raise ValueError(f"Layer 1 scored CSV is missing required field(s): {missing_fields}")


def group_rows_by_submission(
	rows: list[dict[str, str]],
	target_component_id: str,
	submission_id_field: str,
) -> dict[str, list[dict[str, str]]]:
	grouped_rows: dict[str, list[dict[str, str]]] = {}
	for row in rows:
		component_id = (row.get("component_id") or "").strip()
		if component_id and component_id != target_component_id:
			continue
		submission_id = (row.get(submission_id_field) or "").strip()
		if not submission_id:
			continue
		grouped_rows.setdefault(submission_id, []).append(row)
	if not grouped_rows:
		raise ValueError(f"No Layer 1 scored rows found for component_id={target_component_id}")
	return grouped_rows


def build_indicator_value_map(
	submission_id: str,
	rows: list[dict[str, str]],
	indicator_id_field: str,
	value_field: str,
) -> dict[str, str]:
	indicator_values: dict[str, str] = {}
	for row in rows:
		indicator_id = (row.get(indicator_id_field) or "").strip()
		if not indicator_id:
			continue
		normalized_value = str(row.get(value_field) or "").strip().lower()
		if indicator_id in indicator_values and indicator_values[indicator_id] != normalized_value:
			raise ValueError(
				f"Conflicting Layer 1 scores detected for submission_id={submission_id} indicator_id={indicator_id}"
			)
		indicator_values[indicator_id] = normalized_value
	return indicator_values


def confidence_rank(value: str) -> tuple[int, str]:
	normalized_value = value.strip().lower()
	if not normalized_value:
		return (10**9, normalized_value)
	return (CONFIDENCE_ORDER.get(normalized_value, -1), normalized_value)


def build_indicator_confidence_map(
	rows: list[dict[str, str]],
	indicator_id_field: str,
	confidence_field: str = "confidence",
) -> dict[str, str]:
	indicator_confidences: dict[str, str] = {}
	for row in rows:
		indicator_id = (row.get(indicator_id_field) or "").strip()
		if not indicator_id:
			continue
		confidence_value = (row.get(confidence_field) or "").strip()
		if not confidence_value:
			continue
		existing_value = indicator_confidences.get(indicator_id)
		if existing_value is None or confidence_rank(confidence_value) < confidence_rank(existing_value):
			indicator_confidences[indicator_id] = confidence_value
	return indicator_confidences


def derive_min_confidence_indicator(
	indicator_ids: list[str],
	indicator_confidences: dict[str, str],
) -> str:
	available_values = [
		indicator_confidences[indicator_id]
		for indicator_id in indicator_ids
		if indicator_id in indicator_confidences and indicator_confidences[indicator_id].strip()
	]
	if not available_values:
		return ""
	return min(available_values, key=confidence_rank)


def derive_flags_any_indicator(
	rows: list[dict[str, str]],
	indicator_ids: list[str],
	indicator_id_field: str,
	flags_field: str = "flags",
) -> str:
	relevant_indicator_ids = {indicator_id.strip() for indicator_id in indicator_ids if indicator_id.strip()}
	ordered_flag_values: list[str] = []
	seen_flag_values: set[str] = set()
	for row in rows:
		indicator_id = (row.get(indicator_id_field) or "").strip()
		if relevant_indicator_ids and indicator_id not in relevant_indicator_ids:
			continue
		flag_value = (row.get(flags_field) or "").strip()
		if not flag_value or flag_value.lower() == "none":
			continue
		normalized_key = flag_value.lower()
		if normalized_key in seen_flag_values:
			continue
		seen_flag_values.add(normalized_key)
		ordered_flag_values.append(flag_value)
	if not ordered_flag_values:
		return "none"
	return " | ".join(ordered_flag_values)


def build_passthrough_row(representative_row: dict[str, str]) -> dict[str, str]:
	output_row: dict[str, str] = {}
	for key, value in representative_row.items():
		if key == "confidence":
			continue
		if key in PASSTHROUGH_EXCLUDED_FIELDS:
			continue
		output_row[key] = value
	return output_row


def build_output_row(
	representative_row: dict[str, str],
	rows: list[dict[str, str]],
	module: ModuleType,
	score_value: str,
	indicator_values: dict[str, str],
	indicator_confidences: dict[str, str],
	indicator_id_field: str,
) -> dict[str, str]:
	bound_indicator_ids = [str(indicator_id) for indicator_id in getattr(module, "BOUND_INDICATOR_IDS", [])]
	bound_indicator_values = {
		indicator_id: indicator_values.get(indicator_id, "") for indicator_id in bound_indicator_ids
	}
	min_confidence_indicator = derive_min_confidence_indicator(bound_indicator_ids, indicator_confidences)
	flags_any_indicator = derive_flags_any_indicator(rows, bound_indicator_ids, indicator_id_field)
	output_row = build_passthrough_row(representative_row)
	output_row["component_id"] = str(getattr(module, "COMPONENT_ID", "")).strip()
	output_row["dimension_id"] = str(getattr(module, "DIMENSION_ID", "")).strip()
	output_row["dimension_template_id"] = str(getattr(module, "DIMENSION_TEMPLATE_ID", "")).strip()
	output_row["dimension_evidence_scale"] = ", ".join(
		str(value).strip() for value in getattr(module, "DIMENSION_EVIDENCE_SCALE", []) if str(value).strip()
	)
	output_row["sbo_identifier"] = str(getattr(module, "SBO_IDENTIFIER", "")).strip()
	output_row["sbo_short_description"] = str(getattr(module, "SBO_SHORT_DESCRIPTION", "")).strip()
	output_row["bound_indicator_ids"] = ", ".join(bound_indicator_ids)
	output_row["source_indicator_values_json"] = json.dumps(bound_indicator_values, ensure_ascii=True, sort_keys=True)
	output_row["evidence_status"] = score_value
	output_row["flags_any_indicator"] = flags_any_indicator
	output_row["min_confidence_indicator"] = min_confidence_indicator
	return output_row


def build_dimension_scale_lookup(modules: list[ModuleType]) -> dict[str, dict[str, int]]:
	lookup: dict[str, dict[str, int]] = {}
	for module in modules:
		dimension_id = str(getattr(module, "DIMENSION_ID", "")).strip()
		if not dimension_id:
			continue
		scale_values = [
			str(value).strip()
			for value in getattr(module, "DIMENSION_EVIDENCE_SCALE", [])
			if str(value).strip()
		]
		lookup[dimension_id] = {value: index for index, value in enumerate(scale_values)}
	return lookup


def ordinalize_dimension_value(value: str, ordinal_lookup: dict[str, int]) -> str:
	normalized_value = value.strip()
	if not normalized_value:
		return ""
	if normalized_value not in ordinal_lookup:
		return normalized_value
	return f"{ordinal_lookup[normalized_value]}-{normalized_value}"


def score_submission_rows(
	submission_id: str,
	rows: list[dict[str, str]],
	modules: list[ModuleType],
	indicator_id_field: str,
	value_field: str,
) -> list[dict[str, str]]:
	indicator_values = build_indicator_value_map(submission_id, rows, indicator_id_field, value_field)
	indicator_confidences = build_indicator_confidence_map(rows, indicator_id_field)
	representative_row = rows[0]
	output_rows: list[dict[str, str]] = []
	for module in modules:
		try:
			score_value = str(module.score_dimension(indicator_values)).strip()
		except Exception as exc:  # pragma: no cover - surfaced to caller with context
			raise ValueError(
				f"Layer 2 scoring failed for submission_id={submission_id} dimension_id={getattr(module, 'DIMENSION_ID', '')}: {exc}"
			) from exc
		output_rows.append(
			build_output_row(
				representative_row,
				rows,
				module,
				score_value,
				indicator_values,
				indicator_confidences,
				indicator_id_field,
			)
		)
	return output_rows


def build_wide_output_rows(
	grouped_rows: dict[str, list[dict[str, str]]],
	output_rows: list[dict[str, str]],
	dimension_scale_lookup: dict[str, dict[str, int]],
	indicator_id_field: str,
	value_field: str,
) -> list[dict[str, str]]:
	dimension_ids = sorted(
		{
			(row.get("dimension_id") or "").strip()
			for row in output_rows
			if (row.get("dimension_id") or "").strip()
		},
		key=dimension_sort_key,
	)
	indicator_ids = sorted(
		{
			(row.get(indicator_id_field) or "").strip()
			for submission_rows in grouped_rows.values()
			for row in submission_rows
			if (row.get(indicator_id_field) or "").strip()
		},
		key=dimension_sort_key,
	)
	dimension_rows_by_submission: dict[str, dict[str, dict[str, str]]] = {}
	for row in output_rows:
		submission_id = (row.get("submission_id") or "").strip()
		dimension_id = (row.get("dimension_id") or "").strip()
		if not submission_id or not dimension_id:
			continue
		dimension_rows_by_submission.setdefault(submission_id, {})[dimension_id] = row

	wide_rows: list[dict[str, str]] = []
	for submission_id in sorted(grouped_rows):
		submission_rows = grouped_rows[submission_id]
		representative_row = submission_rows[0]
		indicator_values = build_indicator_value_map(
			submission_id,
			submission_rows,
			indicator_id_field,
			value_field,
		)
		indicator_confidences = build_indicator_confidence_map(submission_rows, indicator_id_field)
		min_confidence_indicator = derive_min_confidence_indicator(indicator_ids, indicator_confidences)
		flags_any_indicator = derive_flags_any_indicator(
			submission_rows,
			indicator_ids,
			indicator_id_field,
		)
		wide_row = build_passthrough_row(representative_row)
		wide_row["component_id"] = (representative_row.get("component_id") or "").strip()
		for dimension_id in dimension_ids:
			dimension_row = dimension_rows_by_submission.get(submission_id, {}).get(dimension_id, {})
			wide_row[dimension_id] = ordinalize_dimension_value(
				(dimension_row.get("evidence_status") or "").strip(),
				dimension_scale_lookup.get(dimension_id, {}),
			)
		for indicator_id in indicator_ids:
			wide_row[indicator_id] = indicator_values.get(indicator_id, "")
		wide_row["flags_any_indicator"] = flags_any_indicator
		wide_row["min_confidence_indicator"] = min_confidence_indicator
		wide_rows.append(wide_row)
	return wide_rows


def main() -> int:
	args = parse_args()
	try:
		layer1_rows = load_scored_rows(args.layer1_scored_csv.resolve())
		validate_layer1_rows(layer1_rows, args.layer1_scored_csv)
		grouped_rows = group_rows_by_submission(
			layer1_rows,
			args.target_component_id,
			args.submission_id_field,
		)
		modules = load_dimension_modules(args.module_dir.resolve(), args.target_component_id)
		output_rows: list[dict[str, str]] = []
		for submission_id in sorted(grouped_rows):
			output_rows.extend(
				score_submission_rows(
					submission_id,
					grouped_rows[submission_id],
					modules,
					args.indicator_id_field,
					args.value_field,
				)
			)
		output_path = args.output_file.resolve()
		write_scored_rows(output_rows, output_path)
		wide_output_path = derive_wide_output_path(output_path)
		dimension_scale_lookup = build_dimension_scale_lookup(modules)
		wide_output_rows = build_wide_output_rows(
			grouped_rows,
			output_rows,
			dimension_scale_lookup,
			args.indicator_id_field,
			args.value_field,
		)
		write_scored_rows(wide_output_rows, wide_output_path)
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	print(output_path)
	print(wide_output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())