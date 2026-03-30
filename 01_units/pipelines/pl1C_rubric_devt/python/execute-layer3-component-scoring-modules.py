#!/usr/bin/env python3
"""Execute deterministic Layer 3 component scoring modules over Layer 2 scores."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Iterable, Mapping

from component_scored_texts import load_scored_rows, write_scored_rows


CONFIDENCE_ORDER = {
	"low": 0,
	"medium": 1,
	"high": 2,
	"": 3,
}
EXCLUDED_PASSTHROUGH_FIELDS = {
	"dimension_id",
	"dimension_template_id",
	"sbo_identifier",
	"sbo_short_description",
	"dimension_definition",
	"dimension_guidance",
	"dimension_evidence_scale",
	"bound_indicator_ids",
	"source_indicator_values_json",
	"evidence_status",
	"flags_any_indicator",
	"min_confidence_indicator",
}
WIDE_EXCLUDED_FIELDS = EXCLUDED_PASSTHROUGH_FIELDS | {"source_dimension_values_json"}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Execute deterministic Layer 3 component scoring modules over Layer 2 scored CSV rows."
	)
	parser.add_argument("--layer2-scored-csv", type=Path, required=True)
	parser.add_argument("--module-dir", type=Path, required=True)
	parser.add_argument("--target-component-id", type=str, required=True)
	parser.add_argument("--output-file", type=Path, required=True)
	parser.add_argument("--submission-id-field", type=str, default="submission_id")
	parser.add_argument("--dimension-id-field", type=str, default="dimension_id")
	parser.add_argument("--value-field", type=str, default="evidence_status")
	parser.add_argument("--confidence-field", type=str, default="min_confidence_indicator")
	parser.add_argument("--flags-field", type=str, default="flags_any_indicator")
	return parser.parse_args()


def derive_wide_output_path(output_path: Path) -> Path:
	return output_path.with_name(f"{output_path.stem}-wide{output_path.suffix}")


def load_module_from_path(path: Path) -> ModuleType:
	spec = importlib.util.spec_from_file_location(path.stem, path)
	if spec is None or spec.loader is None:
		raise ImportError(f"Unable to load module from {path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def load_component_modules(module_dir: Path) -> dict[str, ModuleType]:
	modules: dict[str, ModuleType] = {}
	for module_path in sorted(module_dir.glob("*.py")):
		module = load_module_from_path(module_path)
		component_id = str(getattr(module, "COMPONENT_ID", "")).strip()
		if component_id:
			modules[component_id] = module
	return modules


def build_submission_groups(rows: Iterable[Mapping[str, str]], submission_id_field: str) -> dict[str, list[dict[str, str]]]:
	grouped_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
	for row in rows:
		submission_id = str(row.get(submission_id_field, "")).strip()
		if submission_id:
			grouped_rows[submission_id].append(dict(row))
	return dict(grouped_rows)


def normalize_confidence(value: object) -> str:
	return str(value or "").strip().lower()


def derive_min_confidence_dimension(rows: Iterable[Mapping[str, str]], confidence_field: str) -> str:
	observed_values = [normalize_confidence(row.get(confidence_field, "")) for row in rows if normalize_confidence(row.get(confidence_field, ""))]
	if not observed_values:
		return ""
	return min(observed_values, key=lambda value: CONFIDENCE_ORDER.get(value, len(CONFIDENCE_ORDER)))


def derive_flags_any_dimension(rows: Iterable[Mapping[str, str]], flags_field: str) -> str:
	observed_flags = []
	for row in rows:
		value = str(row.get(flags_field, "")).strip()
		if value:
			observed_flags.append(value)
	if not observed_flags:
		return ""
	return " | ".join(dict.fromkeys(observed_flags))


def build_dimension_value_map(rows: Iterable[Mapping[str, str]], dimension_id_field: str, value_field: str) -> dict[str, str]:
	dimension_values: dict[str, str] = {}
	for row in rows:
		dimension_id = str(row.get(dimension_id_field, "")).strip()
		if not dimension_id:
			continue
		dimension_values[dimension_id] = str(row.get(value_field, "")).strip().lower()
	return dimension_values


def build_passthrough_row(rows: list[dict[str, str]]) -> dict[str, str]:
	if not rows:
		return {}
	representative = rows[0]
	passthrough_row: dict[str, str] = {}
	for key, value in representative.items():
		if key in EXCLUDED_PASSTHROUGH_FIELDS:
			continue
		passthrough_row[key] = value
	return passthrough_row


def build_wide_output_row(output_row: dict[str, str], bound_dimension_ids: list[str]) -> dict[str, str]:
	wide_row = {key: value for key, value in output_row.items() if key not in WIDE_EXCLUDED_FIELDS}
	raw_dimension_values = str(output_row.get("source_dimension_values_json", "")).strip()
	dimension_values = json.loads(raw_dimension_values) if raw_dimension_values else {}
	if not isinstance(dimension_values, dict):
		raise ValueError("source_dimension_values_json must decode to an object.")
	for dimension_id in bound_dimension_ids:
		wide_row[dimension_id] = str(dimension_values.get(dimension_id, "")).strip()
	return wide_row


def score_submission_rows(
	module: ModuleType,
	submission_rows: list[dict[str, str]],
	dimension_id_field: str,
	value_field: str,
	confidence_field: str,
	flags_field: str,
) -> dict[str, str]:
	dimension_values = build_dimension_value_map(submission_rows, dimension_id_field=dimension_id_field, value_field=value_field)
	bound_dimension_ids = [str(dimension_id) for dimension_id in getattr(module, "BOUND_DIMENSION_IDS", [])]
	source_dimension_values = {dimension_id: dimension_values.get(dimension_id, "") for dimension_id in bound_dimension_ids}
	component_score = str(module.score_component(source_dimension_values))
	output_row = build_passthrough_row(submission_rows)
	output_row["component_id"] = str(getattr(module, "COMPONENT_ID", "")).strip()
	output_row["sbo_identifier"] = str(getattr(module, "SBO_IDENTIFIER", "")).strip()
	output_row["sbo_short_description"] = str(getattr(module, "SBO_SHORT_DESCRIPTION", "")).strip()
	output_row["component_performance_scale"] = ", ".join(getattr(module, "COMPONENT_PERFORMANCE_SCALE", []))
	output_row["bound_dimension_ids"] = ", ".join(bound_dimension_ids)
	output_row["source_dimension_values_json"] = json.dumps(source_dimension_values, ensure_ascii=True, sort_keys=True)
	output_row["component_score"] = component_score
	output_row["flags_any_dimension"] = derive_flags_any_dimension(submission_rows, flags_field=flags_field)
	output_row["min_confidence_dimension"] = derive_min_confidence_dimension(submission_rows, confidence_field=confidence_field)
	return output_row


def main() -> int:
	args = parse_args()
	try:
		rows = load_scored_rows(args.layer2_scored_csv.resolve())
		modules = load_component_modules(args.module_dir.resolve())
		module = modules.get(args.target_component_id)
		if module is None:
			raise ValueError(f"No Layer 3 module found for component_id={args.target_component_id}")
		target_rows = [row for row in rows if str(row.get("component_id", "")).strip() == args.target_component_id]
		if not target_rows:
			raise ValueError(f"No Layer 2 rows found for component_id={args.target_component_id}")
		submission_groups = build_submission_groups(target_rows, submission_id_field=args.submission_id_field)
		output_rows = [
			score_submission_rows(
				module,
				submission_rows,
				dimension_id_field=args.dimension_id_field,
				value_field=args.value_field,
				confidence_field=args.confidence_field,
				flags_field=args.flags_field,
			)
			for _, submission_rows in sorted(submission_groups.items())
		]
		output_path = args.output_file.resolve()
		write_scored_rows(output_rows, output_path)
		bound_dimension_ids = [str(dimension_id) for dimension_id in getattr(module, "BOUND_DIMENSION_IDS", [])]
		wide_output_rows = [build_wide_output_row(output_row, bound_dimension_ids) for output_row in output_rows]
		wide_output_path = derive_wide_output_path(output_path)
		write_scored_rows(wide_output_rows, wide_output_path)
	except (FileNotFoundError, ImportError, ValueError, OSError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	print(output_path)
	print(wide_output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())