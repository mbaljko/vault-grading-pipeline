#!/usr/bin/env python3
"""Execute deterministic Layer 4 submission scoring modules over Layer 3 submission payload rows."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from component_scored_texts import load_scored_rows, write_scored_rows


WIDE_TRAILING_FIELDS = ["flags_any_component", "min_confidence_component"]
WIDE_METADATA_EXCLUDED_FIELDS = {
	"submission_performance_scale",
	"bound_component_ids",
	"source_component_scores_json",
	"source_component_numeric_values_json",
	"sbo_identifier",
	"sbo_short_description",
}
WIDE_BASE_FIELDS = ["submission_id", "submission_score", "submission_numeric_score"]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Execute deterministic Layer 4 submission scoring modules over Layer 3 submission payload rows."
	)
	parser.add_argument("--layer3-submission-payload-csv", type=Path, required=True)
	parser.add_argument("--response-text-csv", type=Path)
	parser.add_argument("--stitched-wide-output-file", type=Path)
	parser.add_argument("--module-dir", type=Path, required=True)
	parser.add_argument("--target-assessment-id", type=str, required=True)
	parser.add_argument("--output-file", type=Path, required=True)
	parser.add_argument("--submission-id-field", type=str, default="submission_id")
	parser.add_argument("--flags-field", type=str, default="flags_any_component")
	parser.add_argument("--confidence-field", type=str, default="min_confidence_component")
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


def load_submission_modules(module_dir: Path) -> dict[str, ModuleType]:
	modules: dict[str, ModuleType] = {}
	for module_path in sorted(module_dir.glob("*.py")):
		module = load_module_from_path(module_path)
		assessment_id = str(getattr(module, "ASSESSMENT_ID", "")).strip()
		if assessment_id:
			modules[assessment_id] = module
	return modules


def format_numeric(value: float) -> str:
	return f"{value:.2f}"


def build_component_score_map(row: dict[str, str], bound_component_ids: list[str]) -> dict[str, str]:
	component_scores: dict[str, str] = {}
	for component_id in bound_component_ids:
		field_name = f"component_score__{component_id}"
		component_scores[component_id] = str(row.get(field_name, "")).strip()
	return component_scores


def build_response_text_lookup(response_text_csv: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
	component_order: list[str] = []
	seen_component_ids: set[str] = set()
	lookup: dict[str, dict[str, str]] = {}
	for row in load_scored_rows(response_text_csv):
		submission_id = str(row.get("submission_id", "")).strip()
		component_id = str(row.get("component_id", "")).strip()
		response_text = str(row.get("response_text", ""))
		if not submission_id or not component_id:
			continue
		if component_id not in seen_component_ids:
			seen_component_ids.add(component_id)
			component_order.append(component_id)
		lookup.setdefault(submission_id, {})[component_id] = response_text
	return component_order, lookup


def load_grouped_csv_rows(path: Path) -> tuple[list[str], list[list[str]]]:
	with path.open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.reader(handle)
		try:
			headers = next(reader)
		except StopIteration:
			return [], []
		rows = [list(row) for row in reader]
	return headers, rows


def load_layer3_wide_blocks(layer3_submission_payload_csv: Path) -> list[dict[str, object]]:
	wide_paths = sorted(layer3_submission_payload_csv.parent.glob("*_Layer3_component_scoring_*_output-wide.csv"))
	blocks: list[dict[str, object]] = []
	for wide_path in wide_paths:
		headers, rows = load_grouped_csv_rows(wide_path)
		if not headers or "submission_id" not in headers or "." not in headers:
			continue
		first_separator_index = headers.index(".")
		last_separator_index = len(headers) - 1 - headers[::-1].index(".")
		if first_separator_index >= last_separator_index:
			continue
		submission_id_index = headers.index("submission_id")
		block_headers = headers[first_separator_index + 1:last_separator_index]
		rows_by_submission: dict[str, list[str]] = {}
		for row in rows:
			padded_row = list(row) + [""] * max(0, len(headers) - len(row))
			submission_id = str(padded_row[submission_id_index]).strip()
			if not submission_id:
				continue
			rows_by_submission[submission_id] = padded_row[first_separator_index + 1:last_separator_index]
		blocks.append(
			{
				"headers": block_headers,
				"rows_by_submission": rows_by_submission,
			}
		)
	return blocks


def score_submission_row(
	module: ModuleType,
	row: dict[str, str],
	submission_id_field: str,
	flags_field: str,
	confidence_field: str,
) -> dict[str, str]:
	bound_component_ids = [str(component_id) for component_id in getattr(module, "BOUND_COMPONENT_IDS", [])]
	component_scores = build_component_score_map(row, bound_component_ids)
	result = module.score_submission(component_scores)
	source_component_numeric_values = {
		component_id: format_numeric(float(value))
		for component_id, value in dict(result["source_component_numeric_values"]).items()
	}
	output_row = dict(row)
	output_row[submission_id_field] = str(row.get(submission_id_field, "")).strip()
	output_row["sbo_identifier"] = str(getattr(module, "SBO_IDENTIFIER", "")).strip()
	output_row["sbo_short_description"] = str(getattr(module, "SBO_SHORT_DESCRIPTION", "")).strip()
	output_row["submission_performance_scale"] = ", ".join(getattr(module, "SUBMISSION_PERFORMANCE_SCALE", []))
	output_row["bound_component_ids"] = ", ".join(bound_component_ids)
	output_row["source_component_scores_json"] = json.dumps(component_scores, ensure_ascii=True, sort_keys=True)
	output_row["source_component_numeric_values_json"] = json.dumps(source_component_numeric_values, ensure_ascii=True, sort_keys=True)
	output_row["submission_numeric_score"] = format_numeric(float(result["submission_numeric_score"]))
	output_row["submission_score"] = str(result["submission_score"])
	output_row["flags_any_component"] = str(row.get(flags_field, "")).strip()
	output_row["min_confidence_component"] = str(row.get(confidence_field, "")).strip()
	return output_row


def build_wide_output_rows(
	output_rows: list[dict[str, str]],
	bound_component_ids: list[str],
	layer3_wide_blocks: list[dict[str, object]],
	response_component_ids: list[str] | None = None,
	response_text_lookup: dict[str, dict[str, str]] | None = None,
) -> tuple[list[str], list[list[str]]]:
	if not output_rows:
		return [], []
	component_score_fields = [f"component_score__{component_id}" for component_id in bound_component_ids]
	component_numeric_headers = [f"{component_id}_numeric" for component_id in bound_component_ids]
	response_text_headers = [f"{component_id}_response_text" for component_id in (response_component_ids or [])]
	base_fieldnames = [fieldname for fieldname in WIDE_BASE_FIELDS if fieldname in output_rows[0]]
	headers = list(base_fieldnames)
	if component_score_fields:
		headers.append(".")
		headers.extend(bound_component_ids)
	if component_numeric_headers:
		headers.append(".")
		headers.extend(component_numeric_headers)
	if response_text_headers:
		headers.append(".")
		headers.extend(response_text_headers)
	if layer3_wide_blocks:
		headers.append(".")
		for index, block in enumerate(layer3_wide_blocks):
			headers.extend([str(header) for header in block["headers"]])
			if index < len(layer3_wide_blocks) - 1:
				headers.append(".")
	if WIDE_TRAILING_FIELDS:
		headers.append(".")
		headers.extend(WIDE_TRAILING_FIELDS)

	wide_rows: list[list[str]] = []
	for output_row in output_rows:
		raw_numeric_values = str(output_row.get("source_component_numeric_values_json", "")).strip()
		numeric_values = json.loads(raw_numeric_values) if raw_numeric_values else {}
		if not isinstance(numeric_values, dict):
			raise ValueError("source_component_numeric_values_json must decode to an object.")
		wide_row = [output_row.get(fieldname, "") for fieldname in base_fieldnames]
		if component_score_fields:
			wide_row.append("")
			for fieldname in component_score_fields:
				wide_row.append(output_row.get(fieldname, ""))
		if component_numeric_headers:
			wide_row.append("")
			for component_id in bound_component_ids:
				wide_row.append(str(numeric_values.get(component_id, "")))
		if response_text_headers:
			wide_row.append("")
			submission_id = str(output_row.get("submission_id", "")).strip()
			for component_id in (response_component_ids or []):
				wide_row.append((response_text_lookup or {}).get(submission_id, {}).get(component_id, ""))
		if layer3_wide_blocks:
			wide_row.append("")
			submission_id = str(output_row.get("submission_id", "")).strip()
			for index, block in enumerate(layer3_wide_blocks):
				block_headers = [str(header) for header in block["headers"]]
				rows_by_submission = dict(block["rows_by_submission"])
				wide_row.extend(rows_by_submission.get(submission_id, [""] * len(block_headers)))
				if index < len(layer3_wide_blocks) - 1:
					wide_row.append("")
		if WIDE_TRAILING_FIELDS:
			wide_row.append("")
			for fieldname in WIDE_TRAILING_FIELDS:
				wide_row.append(output_row.get(fieldname, ""))
		wide_rows.append(wide_row)
	return headers, wide_rows


def main() -> int:
	args = parse_args()
	try:
		rows = load_scored_rows(args.layer3_submission_payload_csv.resolve())
		modules = load_submission_modules(args.module_dir.resolve())
		module = modules.get(args.target_assessment_id)
		if module is None:
			raise ValueError(f"No Layer 4 module found for assessment_id={args.target_assessment_id}")
		output_rows = [
			score_submission_row(
				module,
				row,
				submission_id_field=args.submission_id_field,
				flags_field=args.flags_field,
				confidence_field=args.confidence_field,
			)
			for row in rows
		]
		output_path = args.output_file.resolve()
		write_scored_rows(output_rows, output_path)
		bound_component_ids = [str(component_id) for component_id in getattr(module, "BOUND_COMPONENT_IDS", [])]
		layer3_wide_blocks = load_layer3_wide_blocks(args.layer3_submission_payload_csv.resolve())
		wide_output_path = derive_wide_output_path(output_path)
		wide_headers, wide_output_rows = build_wide_output_rows(output_rows, bound_component_ids, layer3_wide_blocks)
		write_grouped_wide_csv(wide_headers, wide_output_rows, wide_output_path)
		if args.response_text_csv is not None:
			response_component_ids, response_text_lookup = build_response_text_lookup(args.response_text_csv.resolve())
			stitched_output_path = (
				args.stitched_wide_output_file.resolve()
				if args.stitched_wide_output_file is not None
				else derive_stitched_wide_output_path(output_path)
			)
			stitched_headers, stitched_rows = build_wide_output_rows(
				output_rows,
				bound_component_ids,
				layer3_wide_blocks,
				response_component_ids,
				response_text_lookup,
			)
			write_grouped_wide_csv(stitched_headers, stitched_rows, stitched_output_path)
	except (FileNotFoundError, ImportError, ValueError, OSError, json.JSONDecodeError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	print(output_path)
	print(wide_output_path)
	if args.response_text_csv is not None:
		print(args.stitched_wide_output_file.resolve() if args.stitched_wide_output_file is not None else derive_stitched_wide_output_path(output_path))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())