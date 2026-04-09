#!/usr/bin/env python3
"""Merge scoring output CSV files and pivot them into one wide CSV artifact.

This utility consumes one input path and one output path, with an optional glob
filter when the input path is a directory:

- if ``--input-path`` is a file, that file is treated as the sole CSV input
- if ``--input-path`` is a directory, matching ``.csv`` files are discovered
  recursively and merged in lexical path order
- if ``--input-glob`` is provided with a directory input, only matching CSV
  files are included

All input CSV files must share the same header row. The utility first merges the
matched long-format rows, optionally joins the original scoring-input CSV used
to generate those outputs, then pivots the merged rows into one wide row per
``submission_id`` × ``component_id``.

Wide-format behavior:

- one output column is created for each unique ``segment_id`` using the name
	``segment_text_<segment_id>``
- when ``--source-csv`` is provided, the stitched output also includes
	``source_submission_id`` and ``source_response_text`` from the original
	scoring input matched on ``submission_id`` × ``component_id``
- the value written to each ``segment_text_<segment_id>`` column is the source
	row's ``segment_text`` value
- the remaining non-key fields are suffixed with the segment id, for example
	``operator_id_DemandA`` or ``extraction_notes_DemandA``
- wide columns are grouped by field prefix, with spacer columns named ``.``
	inserted between groups
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import OrderedDict
from pathlib import Path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Merge scoring output CSV files into one wide CSV.")
	parser.add_argument(
		"--input-path",
		type=Path,
		required=True,
		help="Input CSV file or directory containing CSV files to merge.",
	)
	parser.add_argument(
		"--output-path",
		type=Path,
		required=True,
		help="Path for the merged wide-format CSV output file.",
	)
	parser.add_argument(
		"--input-glob",
		type=str,
		default="*.csv",
		help="Optional glob used when --input-path is a directory. Defaults to *.csv.",
	)
	parser.add_argument(
		"--source-csv",
		type=Path,
		help="Optional source input CSV used by l0c-rs-py; joined on submission_id and component_id.",
	)
	return parser.parse_args()


def resolve_input_csv_paths(input_path: Path, output_path: Path, input_glob: str) -> list[Path]:
	resolved_input = input_path.resolve(strict=False)
	resolved_output = output_path.resolve(strict=False)

	if resolved_input.is_file():
		if resolved_input.suffix.lower() != ".csv":
			raise ValueError(f"Input file is not a CSV: {resolved_input}")
		if resolved_input == resolved_output:
			raise ValueError("Input path and output path must be different.")
		return [resolved_input]

	if resolved_input.is_dir():
		csv_paths = sorted(
			path
			for path in resolved_input.rglob(input_glob)
			if path.is_file() and path.resolve() != resolved_output
		)
		if not csv_paths:
			raise ValueError(
				f"No CSV files found under input directory: {resolved_input} matching glob {input_glob!r}"
			)
		return csv_paths

	raise FileNotFoundError(f"Input path not found: {resolved_input}")


def read_csv_rows(csv_path: Path) -> list[list[str]]:
	with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
		return list(csv.reader(handle))


def merge_csv_files(input_paths: list[Path]) -> tuple[list[str], list[list[str]]]:
	merged_header: list[str] | None = None
	merged_rows: list[list[str]] = []

	for csv_path in input_paths:
		rows = read_csv_rows(csv_path)
		if not rows:
			continue

		header, *data_rows = rows
		if merged_header is None:
			merged_header = header
		elif header != merged_header:
			raise ValueError(
				"Input CSV headers do not match; "
				f"expected {merged_header!r}, got {header!r} from {csv_path}"
			)

		merged_rows.extend(data_rows)

	if merged_header is None:
		raise ValueError("No non-empty CSV content was found to merge.")

	return merged_header, merged_rows


def load_source_lookup(source_csv_path: Path | None) -> dict[tuple[str, str], dict[str, str]]:
	if source_csv_path is None:
		return {}

	resolved_path = source_csv_path.resolve(strict=False)
	if not resolved_path.is_file():
		raise FileNotFoundError(f"Source CSV not found: {resolved_path}")

	rows = read_csv_rows(resolved_path)
	if not rows:
		raise ValueError(f"Source CSV is empty: {resolved_path}")

	header, *data_rows = rows
	required_columns = {"submission_id", "component_id", "response_text"}
	missing = required_columns.difference(header)
	if missing:
		raise ValueError(
			"Cannot join source CSV; missing required columns: "
			f"{sorted(missing)!r} in {resolved_path}"
		)

	index_by_name = {name: idx for idx, name in enumerate(header)}
	source_lookup: dict[tuple[str, str], dict[str, str]] = {}
	for row in data_rows:
		padded_row = row + [""] * (len(header) - len(row))
		submission_id = padded_row[index_by_name["submission_id"]].strip()
		component_id = padded_row[index_by_name["component_id"]].strip()
		if not submission_id or not component_id:
			continue

		key = (submission_id, component_id)
		candidate = {
			"source_submission_id": submission_id,
			"source_response_text": padded_row[index_by_name["response_text"]].strip(),
		}
		existing = source_lookup.get(key)
		if existing is not None and existing != candidate:
			raise ValueError(
				"Conflicting duplicate rows found in source CSV for "
				f"submission_id={submission_id!r}, component_id={component_id!r}"
			)
		source_lookup[key] = candidate

	return source_lookup


def build_wide_header(segment_ids: list[str]) -> list[str]:
	header = ["submission_id", "component_id", "source_submission_id", "source_response_text"]
	column_groups = [
		"segment_text",
		"operator_id",
		"extraction_status",
		"extraction_notes",
	]
	for group_index, column_prefix in enumerate(column_groups):
		if group_index > 0:
			header.append(".")
		for segment_id in segment_ids:
			header.append(f"{column_prefix}_{segment_id}")
	header.append(".")
	header.append("missing_audit")
	return header


def build_missing_audit(wide_row: dict[str, str], segment_ids: list[str]) -> str:
	audit_failures: list[str] = []
	for segment_id in segment_ids:
		status = wide_row.get(f"extraction_status_{segment_id}", "").strip().lower()
		segment_text = wide_row.get(f"segment_text_{segment_id}", "").strip()
		if status == "missing" and segment_text:
			audit_failures.append(f"{segment_id}:missing_has_text")
		elif status == "ok" and not segment_text:
			audit_failures.append(f"{segment_id}:ok_missing_text")
	if not audit_failures:
		return "ok"
	return ";".join(audit_failures)


def set_pivot_value(target_row: dict[str, str], field_name: str, value: str, segment_id: str) -> None:
	existing = target_row.get(field_name, "")
	if existing and value and existing != value:
		raise ValueError(
			f"Conflicting values for {field_name!r} in segment_id={segment_id!r}: "
			f"{existing!r} vs {value!r}"
		)
	if value:
		target_row[field_name] = value


def pivot_rows_to_wide(
	header: list[str],
	rows: list[list[str]],
	source_lookup: dict[tuple[str, str], dict[str, str]],
) -> tuple[list[str], list[list[str]]]:
	required_columns = {
		"submission_id",
		"component_id",
		"operator_id",
		"segment_id",
		"segment_text",
		"extraction_status",
		"extraction_notes",
	}
	missing = required_columns.difference(header)
	if missing:
		raise ValueError(f"Cannot pivot merged CSV; missing required columns: {sorted(missing)!r}")

	index_by_name = {name: idx for idx, name in enumerate(header)}
	segment_ids = sorted(
		{
			row[index_by_name["segment_id"]].strip()
			for row in rows
			if len(row) > index_by_name["segment_id"] and row[index_by_name["segment_id"]].strip()
		}
	)
	wide_header = build_wide_header(segment_ids)
	wide_rows: OrderedDict[tuple[str, str], dict[str, str]] = OrderedDict()

	for row in rows:
		padded_row = row + [""] * (len(header) - len(row))
		submission_id = padded_row[index_by_name["submission_id"]].strip()
		component_id = padded_row[index_by_name["component_id"]].strip()
		segment_id = padded_row[index_by_name["segment_id"]].strip()
		if not submission_id or not component_id or not segment_id:
			continue

		key = (submission_id, component_id)
		wide_row = wide_rows.setdefault(
			key,
			{
				"submission_id": submission_id,
				"component_id": component_id,
				"source_submission_id": "",
				"source_response_text": "",
			},
		)

		if source_lookup:
			source_row = source_lookup.get(key)
			if source_row is None:
				raise ValueError(
					"No matching row found in source CSV for "
					f"submission_id={submission_id!r}, component_id={component_id!r}"
				)
			set_pivot_value(
				wide_row,
				"source_submission_id",
				source_row["source_submission_id"],
				segment_id,
			)
			set_pivot_value(
				wide_row,
				"source_response_text",
				source_row["source_response_text"],
				segment_id,
			)

		set_pivot_value(
			wide_row,
			f"segment_text_{segment_id}",
			padded_row[index_by_name["segment_text"]].strip(),
			segment_id,
		)
		set_pivot_value(
			wide_row,
			f"operator_id_{segment_id}",
			padded_row[index_by_name["operator_id"]].strip(),
			segment_id,
		)
		set_pivot_value(
			wide_row,
			f"extraction_status_{segment_id}",
			padded_row[index_by_name["extraction_status"]].strip(),
			segment_id,
		)
		set_pivot_value(
			wide_row,
			f"extraction_notes_{segment_id}",
			padded_row[index_by_name["extraction_notes"]].strip(),
			segment_id,
		)

	for wide_row in wide_rows.values():
		wide_row["missing_audit"] = build_missing_audit(wide_row, segment_ids)

	wide_data_rows = [[wide_row.get(column_name, "") for column_name in wide_header] for wide_row in wide_rows.values()]
	return wide_header, wide_data_rows


def write_csv_file(output_path: Path, header: list[str], rows: list[list[str]]) -> int:
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
		writer = csv.writer(handle)
		writer.writerow(header)
		writer.writerows(rows)
	return len(rows)


def main() -> int:
	args = parse_args()
	try:
		input_paths = resolve_input_csv_paths(args.input_path, args.output_path, args.input_glob)
		merged_header, merged_rows = merge_csv_files(input_paths)
		source_lookup = load_source_lookup(args.source_csv)
		wide_header, wide_rows = pivot_rows_to_wide(merged_header, merged_rows, source_lookup)
		row_count = write_csv_file(args.output_path, wide_header, wide_rows)
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	print(
		"Merged scoring output CSVs\n"
		f"input_count={len(input_paths)}\n"
		f"input_glob={args.input_glob}\n"
		f"source_csv={args.source_csv.resolve() if args.source_csv else ''}\n"
		f"row_count={row_count}\n"
		f"header_columns={len(wide_header)}\n"
		f"output_path={args.output_path.resolve()}"
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())