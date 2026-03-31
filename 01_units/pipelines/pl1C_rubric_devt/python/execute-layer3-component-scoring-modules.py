#!/usr/bin/env python3
"""Execute deterministic Layer 3 component scoring modules over Layer 2 scores."""

from __future__ import annotations

import argparse
import csv
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
WIDE_TRAILING_FIELDS = ["flags_any_dimension", "min_confidence_dimension"]
WIDE_METADATA_EXCLUDED_FIELDS = {"component_performance_scale", "bound_dimension_ids"}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Execute deterministic Layer 3 component scoring modules over Layer 2 scored CSV rows."
	)
	parser.add_argument("--layer2-scored-csv", type=Path, required=True)
	parser.add_argument("--response-text-csv", type=Path)
	parser.add_argument("--stitched-wide-output-file", type=Path)
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


def derive_stitched_wide_output_path(output_path: Path) -> Path:
	return output_path.with_name(f"{output_path.stem}-wide-stitched{output_path.suffix}")


def write_grouped_wide_csv(headers: list[str], rows: list[list[str]], output_path: Path) -> None:
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding="utf-8", newline="") as handle:
		writer = csv.writer(handle)
		writer.writerow(headers)
		writer.writerows(rows)


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


def build_response_text_lookup(response_text_csv: Path) -> dict[str, str]:
	lookup: dict[str, str] = {}
	for row in load_scored_rows(response_text_csv):
		submission_id = str(row.get("submission_id", "")).strip()
		if not submission_id or submission_id in lookup:
			continue
		lookup[submission_id] = str(row.get("response_text", ""))
	return lookup


def build_dimension_scale_lookup(rows: Iterable[Mapping[str, str]], dimension_id_field: str) -> dict[str, dict[str, int]]:
	lookup: dict[str, dict[str, int]] = {}
	for row in rows:
		dimension_id = str(row.get(dimension_id_field, "")).strip()
		if not dimension_id or dimension_id in lookup:
			continue
		raw_scale = str(row.get("dimension_evidence_scale", "")).strip()
		scale_values = [part.strip() for part in raw_scale.split(",") if part.strip()]
		lookup[dimension_id] = {value: index for index, value in enumerate(scale_values)}
	return lookup


def build_component_scale_lookup(output_rows: list[dict[str, str]]) -> dict[str, int]:
	if not output_rows:
		return {}
	raw_scale = str(output_rows[0].get("component_performance_scale", "")).strip()
	scale_values = [part.strip() for part in raw_scale.split(",") if part.strip()]
	return {value: index for index, value in enumerate(scale_values)}


def ordinalize_dimension_value(value: str, ordinal_lookup: dict[str, int]) -> str:
	normalized_value = value.strip()
	if not normalized_value:
		return ""
	if normalized_value not in ordinal_lookup:
		return normalized_value
	return f"{ordinal_lookup[normalized_value]}-{normalized_value}"


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


def parse_bound_ids(raw_value: object) -> list[str]:
	return [part.strip() for part in str(raw_value or "").split(",") if part.strip()]


def build_dimension_indicator_groups(
	submission_groups: dict[str, list[dict[str, str]]],
	bound_dimension_ids: list[str],
	dimension_id_field: str,
) -> list[tuple[str, list[str]]]:
	indicator_ids_by_dimension: dict[str, list[str]] = {dimension_id: [] for dimension_id in bound_dimension_ids}
	for submission_rows in submission_groups.values():
		for row in submission_rows:
			dimension_id = str(row.get(dimension_id_field, "")).strip()
			if dimension_id not in indicator_ids_by_dimension or indicator_ids_by_dimension[dimension_id]:
				continue
			indicator_ids_by_dimension[dimension_id] = parse_bound_ids(row.get("bound_indicator_ids", ""))
	return [(dimension_id, indicator_ids_by_dimension.get(dimension_id, [])) for dimension_id in bound_dimension_ids]


def build_indicator_values_by_dimension(
	submission_rows: list[dict[str, str]],
	dimension_id_field: str,
	bound_dimension_ids: list[str],
) -> dict[str, dict[str, str]]:
	values_by_dimension: dict[str, dict[str, str]] = {dimension_id: {} for dimension_id in bound_dimension_ids}
	for row in submission_rows:
		dimension_id = str(row.get(dimension_id_field, "")).strip()
		if dimension_id not in values_by_dimension:
			continue
		raw_indicator_values = str(row.get("source_indicator_values_json", "")).strip()
		indicator_values = json.loads(raw_indicator_values) if raw_indicator_values else {}
		if not isinstance(indicator_values, dict):
			raise ValueError("source_indicator_values_json must decode to an object.")
		values_by_dimension[dimension_id] = {str(key).strip(): str(value).strip() for key, value in indicator_values.items()}
	return values_by_dimension


def build_wide_output_rows(
	submission_groups: dict[str, list[dict[str, str]]],
	output_rows: list[dict[str, str]],
	bound_dimension_ids: list[str],
	dimension_id_field: str,
	dimension_scale_lookup: dict[str, dict[str, int]],
	response_text_lookup: dict[str, str] | None = None,
) -> tuple[list[str], list[list[str]]]:
	component_scale_lookup = build_component_scale_lookup(output_rows)
	base_fieldnames = [
		key
		for key in output_rows[0].keys()
		if key not in WIDE_EXCLUDED_FIELDS and key not in WIDE_TRAILING_FIELDS and key not in WIDE_METADATA_EXCLUDED_FIELDS
	] if output_rows else []
	dimension_indicator_groups = build_dimension_indicator_groups(submission_groups, bound_dimension_ids, dimension_id_field)
	output_rows_by_submission = {
		str(output_row.get("submission_id", "")).strip(): output_row
		for output_row in output_rows
		if str(output_row.get("submission_id", "")).strip()
	}
	headers = list(base_fieldnames)
	if response_text_lookup is not None:
		headers.append(".")
		headers.append("response_text")
	if bound_dimension_ids:
		headers.append(".")
		headers.extend(bound_dimension_ids)
	if dimension_indicator_groups:
		headers.append(".")
		for index, (dimension_id, indicator_ids) in enumerate(dimension_indicator_groups):
			for indicator_id in indicator_ids:
				headers.append(f"{dimension_id}_{indicator_id}")
			if index < len(dimension_indicator_groups) - 1:
				headers.append(".")
	if WIDE_TRAILING_FIELDS:
		headers.append(".")
		headers.extend(WIDE_TRAILING_FIELDS)

	wide_rows: list[list[str]] = []
	for submission_id in sorted(submission_groups):
		output_row = output_rows_by_submission.get(submission_id)
		if output_row is None:
			continue
		raw_dimension_values = str(output_row.get("source_dimension_values_json", "")).strip()
		dimension_values = json.loads(raw_dimension_values) if raw_dimension_values else {}
		if not isinstance(dimension_values, dict):
			raise ValueError("source_dimension_values_json must decode to an object.")
		indicator_values_by_dimension = build_indicator_values_by_dimension(
			submission_groups[submission_id],
			dimension_id_field,
			bound_dimension_ids,
		)
		wide_row: list[str] = []
		for fieldname in base_fieldnames:
			field_value = output_row.get(fieldname, "")
			if fieldname == "component_score":
				field_value = ordinalize_dimension_value(str(field_value), component_scale_lookup)
			wide_row.append(field_value)
		if response_text_lookup is not None:
			wide_row.append("")
			wide_row.append(response_text_lookup.get(submission_id, ""))
		if bound_dimension_ids:
			wide_row.append("")
			for dimension_id in bound_dimension_ids:
				wide_row.append(
					ordinalize_dimension_value(
						str(dimension_values.get(dimension_id, "")).strip(),
						dimension_scale_lookup.get(dimension_id, {}),
					)
				)
		if dimension_indicator_groups:
			wide_row.append("")
			for index, (dimension_id, indicator_ids) in enumerate(dimension_indicator_groups):
				for indicator_id in indicator_ids:
					wide_row.append(indicator_values_by_dimension.get(dimension_id, {}).get(indicator_id, ""))
				if index < len(dimension_indicator_groups) - 1:
					wide_row.append("")
		if WIDE_TRAILING_FIELDS:
			wide_row.append("")
			for fieldname in WIDE_TRAILING_FIELDS:
				wide_row.append(output_row.get(fieldname, ""))
		wide_rows.append(wide_row)
	return headers, wide_rows


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
		dimension_scale_lookup = build_dimension_scale_lookup(target_rows, args.dimension_id_field)
		wide_output_path = derive_wide_output_path(output_path)
		wide_headers, wide_output_rows = build_wide_output_rows(
			submission_groups,
			output_rows,
			bound_dimension_ids,
			args.dimension_id_field,
			dimension_scale_lookup,
		)
		write_grouped_wide_csv(wide_headers, wide_output_rows, wide_output_path)
		if args.response_text_csv is not None:
			response_text_lookup = build_response_text_lookup(args.response_text_csv.resolve())
			stitched_output_path = (
				args.stitched_wide_output_file.resolve()
				if args.stitched_wide_output_file is not None
				else derive_stitched_wide_output_path(output_path)
			)
			stitched_headers, stitched_rows = build_wide_output_rows(
				submission_groups,
				output_rows,
				bound_dimension_ids,
				args.dimension_id_field,
				dimension_scale_lookup,
				response_text_lookup,
			)
			write_grouped_wide_csv(stitched_headers, stitched_rows, stitched_output_path)
	except (FileNotFoundError, ImportError, ValueError, OSError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	print(output_path)
	print(wide_output_path)
	if args.response_text_csv is not None:
		print(args.stitched_wide_output_file.resolve() if args.stitched_wide_output_file is not None else derive_stitched_wide_output_path(output_path))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())