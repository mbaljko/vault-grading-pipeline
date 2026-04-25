#!/usr/bin/env python3
"""Execute deterministic Layer 1 indicator-scoring modules over a Layer 1 input CSV.

This script is an executor only. It does not implement Layer 1 registry
`normalisation_rule`, `decision_rule`, or `match_policy` semantics itself.

Control flow:
- this script loads generated per-indicator modules from `--module-dir`
- each generated module exposes `score_indicator_row(...)`
- that generated function delegates to `layer1_indicator_scoring_runtime.py`
- the runtime is therefore the authoritative implementation surface for
	`normalisation_rule`, `decision_rule`, `match_policy`, and bound-segment
	text resolution

Implementation notes for supported `normalisation_rule` handling,
`decision_rule` values, legacy aliases, and bound-segment resolution policies
live in `layer1_indicator_scoring_runtime.py`.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import sys
from datetime import timezone, datetime
from pathlib import Path
from types import ModuleType

from component_scored_texts import load_scored_rows, write_scored_rows
from layer1_recovery_overlay import (
	apply_recovery_overlay_to_l1_scores,
	build_recovery_membership_index,
	load_recovery_allowlist_csv,
	parse_bool,
)


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
	parser.add_argument("--source-response-text-csv", type=Path, required=False)
	parser.add_argument("--recovery-allowlist-csv", type=Path, required=False, action="append")
	parser.add_argument("--recovery-now-utc", type=str, required=False)
	return parser.parse_args()


def utc_now_iso() -> str:
	return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_recovery_registry_rows_from_allowlist(
	allowlist_rows: list[dict[str, str]],
	*,
	recovery_source_ref: str,
) -> list[dict[str, str]]:
	registry_rows: list[dict[str, str]] = []
	seen_keys: set[tuple[str, str]] = set()
	for row in allowlist_rows:
		if not parse_bool(row.get("active", ""), default=False):
			continue
		component_id = str(row.get("component_id", "") or "").strip()
		parent_indicator_id = str(row.get("parent_indicator_id", "") or "").strip()
		recovery_indicator_id = str(row.get("recovery_indicator_id", "") or "").strip()
		if not component_id or not parent_indicator_id:
			continue
		key = (component_id, parent_indicator_id)
		if key in seen_keys:
			continue
		seen_keys.add(key)
		registry_rows.append(
			{
				"component_id": component_id,
				"indicator_id": recovery_indicator_id or f"{parent_indicator_id}_RECOVERY",
				"indicator_kind": "recovery",
				"sibling_of_indicator_id": parent_indicator_id,
				"recovery_mode": "manual_allowlist",
				"recovery_precedence": "force_present",
				"recovery_list_ref": recovery_source_ref,
				"status": "active",
			}
		)
	return registry_rows


def apply_recovery_overlay_if_configured(
	scored_rows: list[dict[str, str]],
	*,
	recovery_allowlist_csvs: list[Path] | None,
	recovery_now_utc: str | None,
) -> list[dict[str, str]]:
	if not recovery_allowlist_csvs:
		return scored_rows
	allowlist_rows: list[dict[str, str]] = []
	recovery_source_refs: list[str] = []
	for recovery_allowlist_csv in recovery_allowlist_csvs:
		allowlist_path = recovery_allowlist_csv.resolve()
		if not allowlist_path.exists() or not allowlist_path.is_file():
			print(
				f"Notice: recovery overlay skipped missing allowlist CSV: {allowlist_path}",
				file=sys.stderr,
			)
			continue
		try:
			loaded_rows = load_recovery_allowlist_csv(str(allowlist_path))
		except (FileNotFoundError, ValueError) as exc:
			print(f"Notice: recovery overlay skipped for {allowlist_path}: {exc}", file=sys.stderr)
			continue
		if loaded_rows:
			allowlist_rows.extend(loaded_rows)
			recovery_source_refs.append(str(allowlist_path))
	if not allowlist_rows:
		return scored_rows
	membership_index = build_recovery_membership_index(allowlist_rows)
	recovery_registry_rows = build_recovery_registry_rows_from_allowlist(
		allowlist_rows,
		recovery_source_ref=",".join(recovery_source_refs),
	)
	if not recovery_registry_rows:
		return scored_rows
	return apply_recovery_overlay_to_l1_scores(
		scored_rows,
		recovery_registry_rows=recovery_registry_rows,
		membership_index=membership_index,
		now_utc=(recovery_now_utc or utc_now_iso()),
	)


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


def load_indicator_modules(module_dir: Path, target_component_id: str, module_file_stem: str) -> list[ModuleType]:
	if not module_dir.exists() or not module_dir.is_dir():
		raise FileNotFoundError(f"Module directory not found: {module_dir}")
	loaded_modules: list[ModuleType] = []
	seen_indicator_ids: set[str] = set()
	module_pattern = f"{module_file_stem}_*.py" if module_file_stem.strip() else "*.py"
	for index, module_path in enumerate(sorted(module_dir.glob(module_pattern))):
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
		raise ValueError(
			f"No Layer 1 modules found for component_id={target_component_id} in {module_dir} matching {module_pattern}"
		)
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


def resolve_submission_id_from_row(row: dict[str, str]) -> str:
	for field_name in ["submission_id", "participant_id"]:
		value = str(row.get(field_name, "") or "").strip()
		if value:
			return value
	return ""


def derive_layer0_stitched_csv_path_from_layer1_input(input_csv_path: Path) -> Path | None:
	if len(input_csv_path.parents) < 4:
		return None
	registry_dir = input_csv_path.parents[3]
	run_label = input_csv_path.parents[1].name
	candidate_dirs = [
		registry_dir / "03_diagnostics" / run_label / "layer0_runtime",
		registry_dir / "02_scoring_outputs" / run_label / "layer0_1_engine_outputs_postprocessed",
	]
	for stitched_dir in candidate_dirs:
		if not stitched_dir.exists() or not stitched_dir.is_dir():
			continue
		matches = sorted(stitched_dir.glob("*output-wide-stitched.csv"))
		if matches:
			return matches[0]
	return None


def resolve_source_response_text_csv(
	explicit_source_csv: Path | None,
	input_csv_path: Path,
) -> Path | None:
	if explicit_source_csv is not None:
		candidate = explicit_source_csv.resolve()
		if candidate.exists() and candidate.is_file():
			return candidate
		print(
			f"Notice: source_response_text enrichment skipped: explicit source file not found: {candidate}",
			file=sys.stderr,
		)
		return None
	derived = derive_layer0_stitched_csv_path_from_layer1_input(input_csv_path)
	if derived is None:
		print(
			"Notice: source_response_text enrichment skipped: no stitched Layer 0 source file could be derived from --layer1-input-csv",
			file=sys.stderr,
		)
		return None
	if not derived.exists() or not derived.is_file():
		print(
			f"Notice: source_response_text enrichment skipped: derived source file not found: {derived}",
			file=sys.stderr,
		)
		return None
	return derived.resolve()


def index_rows_by_component_submission(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
	indexed_rows: dict[tuple[str, str], dict[str, str]] = {}
	for row in rows:
		component_id = str(row.get("component_id", "") or "").strip()
		submission_id = resolve_submission_id_from_row(row)
		if not component_id or not submission_id:
			continue
		indexed_rows[(component_id, submission_id)] = row
	return indexed_rows


def enrich_rows_with_source_response_text(
	rows: list[dict[str, str]],
	input_csv_path: Path,
	explicit_source_csv: Path | None = None,
) -> list[dict[str, str]]:
	stitched_csv_path = resolve_source_response_text_csv(explicit_source_csv, input_csv_path)
	if stitched_csv_path is None:
		return rows
	stitched_rows = load_scored_rows(stitched_csv_path)
	if stitched_rows and "source_response_text" not in stitched_rows[0]:
		print(
			f"Notice: source_response_text enrichment skipped: source file has no 'source_response_text' column: {stitched_csv_path}",
			file=sys.stderr,
		)
		return rows
	stitched_index = index_rows_by_component_submission(stitched_rows)
	enriched_rows: list[dict[str, str]] = []
	matched_rows = 0
	for row in rows:
		component_id = str(row.get("component_id", "") or "").strip()
		submission_id = resolve_submission_id_from_row(row)
		enriched_row = dict(row)
		stitched_row = stitched_index.get((component_id, submission_id))
		if stitched_row is not None:
			stitched_source_text = str(stitched_row.get("source_response_text", "") or "")
			if stitched_source_text:
				enriched_row["source_response_text"] = stitched_source_text
				matched_rows += 1
		enriched_rows.append(enriched_row)
	if matched_rows == 0:
		print(
			f"Notice: source_response_text enrichment skipped: no matching rows found in source file {stitched_csv_path}",
			file=sys.stderr,
		)
	return enriched_rows


def resolve_output_path(output_dir: Path, output_file_stem: str, output_format: str, indicator_id: str) -> Path:
	return output_dir / f"{output_file_stem}_{indicator_id}_output.{output_format.lstrip('.')}"


def derive_wide_output_path(output_path: Path) -> Path:
	return output_path.with_name(f"{output_path.stem}-wide{output_path.suffix}")


def derive_stitched_wide_output_path(output_path: Path) -> Path:
	return output_path.with_name(f"{output_path.stem}-wide-stitched{output_path.suffix}")


def derive_version_family_prefix(output_file_stem: str) -> str:
	match = re.match(r"^(.*)_v\d+$", output_file_stem)
	if match is None:
		return output_file_stem
	return match.group(1)


def remove_stale_indicator_outputs(output_dir: Path, output_file_stem: str, output_format: str) -> None:
	extension = output_format.lstrip('.')
	family_prefix = derive_version_family_prefix(output_file_stem)
	for existing_path in output_dir.glob(f"{family_prefix}_v*_*_output.{extension}"):
		if existing_path.is_file():
			existing_path.unlink()


def remove_stale_combined_outputs(combined_output_path: Path) -> None:
	match = re.match(r"^(.*)_v\d+_output$", combined_output_path.stem)
	if match is None:
		for existing_path in [combined_output_path, derive_wide_output_path(combined_output_path)]:
			if existing_path.exists() and existing_path.is_file():
				existing_path.unlink()
		return
	family_prefix = match.group(1)
	for existing_path in combined_output_path.parent.glob(f"{family_prefix}_v*_output{combined_output_path.suffix}"):
		if existing_path.is_file():
			existing_path.unlink()
	for existing_path in combined_output_path.parent.glob(f"{family_prefix}_v*_output-wide{combined_output_path.suffix}"):
		if existing_path.is_file():
			existing_path.unlink()


def write_grouped_wide_csv(headers: list[str], rows: list[list[str]], output_path: Path) -> None:
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding="utf-8", newline="") as handle:
		writer = csv.writer(handle)
		writer.writerow(headers)
		writer.writerows(rows)



def build_wide_rows(
	combined_rows: list[dict[str, str]],
	target_component_id: str,
	*,
	source_response_text_by_submission: dict[str, str] | None = None,
) -> tuple[list[str], list[list[str]]]:
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
		if source_response_text_by_submission is not None:
			source_response_text = source_response_text_by_submission.get(submission_id, "")
			if source_response_text and not wide_row.get("source_response_text", ""):
				wide_row["source_response_text"] = source_response_text
		wide_row[f"indicator_{indicator_id}_evidence_status"] = row.get("evidence_status", "")
		wide_row[f"indicator_{indicator_id}_flags"] = row.get("flags", "")
	headers = ["submission_id", "component_id"]
	if source_response_text_by_submission is not None:
		headers.append("source_response_text")
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
		input_rows = enrich_rows_with_source_response_text(
			input_rows,
			args.layer1_input_csv.resolve(),
			args.source_response_text_csv,
		)
		component_rows = filter_component_rows(input_rows, args.target_component_id)
		modules = load_indicator_modules(args.module_dir.resolve(), args.target_component_id, args.output_file_stem)
		output_dir = args.output_dir.resolve()
		output_dir.mkdir(parents=True, exist_ok=True)
		remove_stale_indicator_outputs(output_dir, args.output_file_stem, args.output_format)
		if args.combined_output_file is not None:
			remove_stale_combined_outputs(args.combined_output_file.resolve())
		combined_rows: list[dict[str, str]] = []
		source_response_text_by_submission = {
			resolve_submission_id_from_row(row): str(row.get("source_response_text", "") or "")
			for row in component_rows
			if resolve_submission_id_from_row(row)
		}
		for module in modules:
			indicator_id = str(getattr(module, "INDICATOR_ID", "")).strip()
			indicator_rows = [module.score_indicator_row(row) for row in component_rows]
			indicator_rows = apply_recovery_overlay_if_configured(
				indicator_rows,
				recovery_allowlist_csvs=args.recovery_allowlist_csv,
				recovery_now_utc=args.recovery_now_utc,
			)
			output_path = resolve_output_path(output_dir, args.output_file_stem, args.output_format, indicator_id)
			write_scored_rows(indicator_rows, output_path)
			combined_rows.extend(indicator_rows)
		if args.combined_output_file is not None:
			combined_output_path = args.combined_output_file.resolve()
			write_scored_rows(combined_rows, combined_output_path)
			headers, wide_rows = build_wide_rows(combined_rows, args.target_component_id)
			write_grouped_wide_csv(headers, wide_rows, derive_wide_output_path(combined_output_path))
			stitched_headers, stitched_wide_rows = build_wide_rows(
				combined_rows,
				args.target_component_id,
				source_response_text_by_submission=source_response_text_by_submission,
			)
			write_grouped_wide_csv(
				stitched_headers,
				stitched_wide_rows,
				derive_stitched_wide_output_path(combined_output_path),
			)
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())