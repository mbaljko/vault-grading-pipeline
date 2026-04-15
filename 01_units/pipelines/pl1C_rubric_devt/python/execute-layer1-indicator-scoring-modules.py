#!/usr/bin/env python3
"""Execute deterministic Layer 1 indicator-scoring modules over a Layer 1 input CSV."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

from component_scored_texts import load_scored_rows, write_scored_rows


REQUIRED_INPUT_FIELDS = {"component_id"}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Execute generated Layer 1 indicator-scoring modules over a Layer 1 input CSV."
	)
	parser.add_argument("--layer1-input-csv", type=Path, required=True)
	parser.add_argument("--module-dir", type=Path, required=True)
	parser.add_argument("--target-component-id", type=str, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--output-file-stem", type=str, required=True)
	parser.add_argument("--output-format", type=str, default="csv")
	parser.add_argument("--combined-output-file", type=Path, required=False)
	return parser.parse_args()


def load_module_from_path(module_path: Path, module_name: str) -> ModuleType:
	spec = importlib.util.spec_from_file_location(module_name, module_path)
	if spec is None or spec.loader is None:
		raise ValueError(f"Unable to load module spec from {module_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def indicator_sort_key(indicator_id: str) -> tuple[int, str]:
	match = re.fullmatch(r"(\d+)", indicator_id)
	if match is None:
		return (10**9, indicator_id)
	return (int(match.group(1)), indicator_id)


def validate_indicator_module(module: ModuleType, module_path: Path, target_component_id: str) -> None:
	for attribute_name in [
		"COMPONENT_ID",
		"INDICATOR_ID",
		"SBO_IDENTIFIER",
		"SCORING_PAYLOAD",
		"score_indicator_row",
	]:
		if not hasattr(module, attribute_name):
			raise ValueError(f"Module {module_path} is missing required attribute: {attribute_name}")
	if str(getattr(module, "COMPONENT_ID", "")).strip() != target_component_id:
		raise ValueError(
			f"Module {module_path} is for component_id={getattr(module, 'COMPONENT_ID', '')}, expected {target_component_id}"
		)
	if not callable(getattr(module, "score_indicator_row", None)):
		raise ValueError(f"Module {module_path} does not expose a callable score_indicator_row function")


def load_indicator_modules(module_dir: Path, target_component_id: str) -> list[ModuleType]:
	if not module_dir.exists() or not module_dir.is_dir():
		raise FileNotFoundError(f"Module directory not found: {module_dir}")
	loaded_modules: list[ModuleType] = []
	seen_indicator_ids: set[str] = set()
	for index, module_path in enumerate(sorted(module_dir.glob("*.py"))):
		module = load_module_from_path(module_path, f"layer1_indicator_module_{index}")
		if str(getattr(module, "COMPONENT_ID", "")).strip() != target_component_id:
			continue
		validate_indicator_module(module, module_path, target_component_id)
		indicator_id = str(getattr(module, "INDICATOR_ID", "")).strip()
		if not indicator_id:
			raise ValueError(f"Module {module_path} is missing INDICATOR_ID")
		if indicator_id in seen_indicator_ids:
			raise ValueError(f"Duplicate INDICATOR_ID detected across modules: {indicator_id}")
		seen_indicator_ids.add(indicator_id)
		loaded_modules.append(module)
	if not loaded_modules:
		raise ValueError(f"No Layer 1 modules found for component_id={target_component_id} in {module_dir}")
	return sorted(loaded_modules, key=lambda module: indicator_sort_key(str(getattr(module, "INDICATOR_ID", ""))))


def validate_input_rows(rows: list[dict[str, str]], csv_path: Path) -> None:
	if not rows:
		raise ValueError(f"Layer 1 input CSV is empty: {csv_path}")
	available_fields = set().union(*(row.keys() for row in rows))
	missing_fields = sorted(REQUIRED_INPUT_FIELDS - available_fields)
	if missing_fields:
		raise ValueError(f"Layer 1 input CSV is missing required field(s): {missing_fields}")


def filter_component_rows(rows: list[dict[str, str]], target_component_id: str) -> list[dict[str, str]]:
	filtered_rows = [
		row for row in rows if str(row.get("component_id", "") or "").strip() == target_component_id
	]
	if not filtered_rows:
		raise ValueError(f"No Layer 1 input rows found for component_id={target_component_id}")
	return filtered_rows


def resolve_output_path(output_dir: Path, output_file_stem: str, output_format: str, indicator_id: str) -> Path:
	return output_dir / f"{output_file_stem}_{indicator_id}_output.{output_format.lstrip('.')}"


def derive_wide_output_path(output_path: Path) -> Path:
	return output_path.with_name(f"{output_path.stem}-wide{output_path.suffix}")


def write_grouped_wide_csv(headers: list[str], rows: list[list[str]], output_path: Path) -> None:
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding="utf-8", newline="") as handle:
		writer = csv.writer(handle)
		writer.writerow(headers)
		writer.writerows(rows)


def build_wide_rows(combined_rows: list[dict[str, str]], target_component_id: str) -> tuple[list[str], list[list[str]]]:
	grouped_by_submission: dict[str, dict[str, str]] = {}
	indicator_ids = sorted({row.get("indicator_id", "") for row in combined_rows if row.get("indicator_id", "")}, key=indicator_sort_key)
	for row in combined_rows:
		submission_id = str(row.get("submission_id", "") or "").strip()
		indicator_id = str(row.get("indicator_id", "") or "").strip()
		if not submission_id or not indicator_id:
			continue
		wide_row = grouped_by_submission.setdefault(
			submission_id,
			{"submission_id": submission_id, "component_id": target_component_id},
		)
		wide_row[f"indicator_{indicator_id}_evidence_status"] = row.get("evidence_status", "")
		wide_row[f"indicator_{indicator_id}_flags"] = row.get("flags", "")
	headers = ["submission_id", "component_id"]
	for indicator_id in indicator_ids:
		headers.extend([
			f"indicator_{indicator_id}_evidence_status",
			f"indicator_{indicator_id}_flags",
		])
	rows = [[grouped_by_submission[submission_id].get(header, "") for header in headers] for submission_id in sorted(grouped_by_submission)]
	return headers, rows


def main() -> int:
	args = parse_args()
	try:
		input_rows = load_scored_rows(args.layer1_input_csv.resolve())
		validate_input_rows(input_rows, args.layer1_input_csv)
		component_rows = filter_component_rows(input_rows, args.target_component_id)
		modules = load_indicator_modules(args.module_dir.resolve(), args.target_component_id)
		output_dir = args.output_dir.resolve()
		output_dir.mkdir(parents=True, exist_ok=True)
		combined_rows: list[dict[str, str]] = []
		for module in modules:
			indicator_id = str(getattr(module, "INDICATOR_ID", "")).strip()
			indicator_rows = [module.score_indicator_row(row) for row in component_rows]
			output_path = resolve_output_path(output_dir, args.output_file_stem, args.output_format, indicator_id)
			write_scored_rows(indicator_rows, output_path)
			combined_rows.extend(indicator_rows)
		if args.combined_output_file is not None:
			combined_output_path = args.combined_output_file.resolve()
			write_scored_rows(combined_rows, combined_output_path)
			headers, wide_rows = build_wide_rows(combined_rows, args.target_component_id)
			write_grouped_wide_csv(headers, wide_rows, derive_wide_output_path(combined_output_path))
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())