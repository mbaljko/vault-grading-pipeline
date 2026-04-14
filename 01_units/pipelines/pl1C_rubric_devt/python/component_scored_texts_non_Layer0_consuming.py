from __future__ import annotations

import csv
import re
from pathlib import Path


SCORING_OUTPUT_VERSION_RE = re.compile(r"_v(\d+)(?=_)")


def derive_expected_version_label(input_ref: Path, fallback_label: str | None = None) -> str | None:
	version_match = SCORING_OUTPUT_VERSION_RE.search(input_ref.name)
	if version_match is not None:
		return version_match.group(1)
	if fallback_label is None:
		return None
	fallback_match = re.search(r"(\d+)", fallback_label)
	if fallback_match is None:
		return None
	return fallback_match.group(1)


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
	return sorted(candidate for candidate in directory.glob(pattern) if candidate.is_file())


def discover_component_single_scored_csv_paths_in_dir(directory: Path, component_id: str) -> list[Path]:
	if not directory.exists() or not directory.is_dir():
		return []
	exact_matches = sorted(
		candidate
		for candidate in directory.glob(f"*{component_id}*_Layer1_SBO_scoring_prompt_v*_output.csv")
		if candidate.is_file()
	)
	if exact_matches:
		return exact_matches
	duplicated_suffix_matches = sorted(
		candidate
		for candidate in directory.glob(f"*{component_id}*_Layer1_SBO_scoring_prompt_v*_output_output.csv")
		if candidate.is_file()
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
	single_matches = discover_component_single_scored_csv_paths_in_dir(directory, component_id)
	if single_matches:
		return single_matches
	return sorted(
		candidate for candidate in directory.glob(f"*{component_id}*output*.csv") if candidate.is_file()
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


def load_scored_rows_from_paths(input_paths: list[Path]) -> list[dict[str, str]]:
	rows: list[dict[str, str]] = []
	for input_path in input_paths:
		rows.extend(load_scored_rows(input_path))
	return rows


def write_scored_rows(rows: list[dict[str, str]], output_path: Path) -> None:
	fieldnames: list[str] = []
	seen: set[str] = set()
	for row in rows:
		for key in row.keys():
			if key not in seen:
				seen.add(key)
				fieldnames.append(key)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding="utf-8", newline="") as handle:
		writer = csv.DictWriter(handle, fieldnames=fieldnames)
		writer.writeheader()
		for row in rows:
			writer.writerow({field: row.get(field, "") for field in fieldnames})