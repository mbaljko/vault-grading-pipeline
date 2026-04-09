#!/usr/bin/env python3
"""Merge scoring output CSV files into one combined CSV artifact.

This utility is intentionally simple. It consumes one input path and one output
path, with an optional glob filter when the input path is a directory:

- if ``--input-path`` is a file, that file is treated as the sole CSV input
- if ``--input-path`` is a directory, all ``.csv`` files under that directory
  are discovered recursively and merged in lexical path order
- if ``--input-glob`` is provided with a directory input, only matching CSV
	files are included

All input CSV files must share the same header row. The merged output contains
the header once followed by all data rows from all matched files.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Merge scoring output CSV files into one CSV.")
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
		help="Path for the merged CSV output file.",
	)
	parser.add_argument(
		"--input-glob",
		type=str,
		default="*.csv",
		help="Optional glob used when --input-path is a directory. Defaults to *.csv.",
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


def merge_csv_files(input_paths: list[Path], output_path: Path) -> tuple[int, list[str]]:
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

	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
		writer = csv.writer(handle)
		writer.writerow(merged_header)
		writer.writerows(merged_rows)

	return len(merged_rows), merged_header


def main() -> int:
	args = parse_args()
	try:
		input_paths = resolve_input_csv_paths(args.input_path, args.output_path, args.input_glob)
		row_count, header = merge_csv_files(input_paths, args.output_path)
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	print(
		"Merged scoring output CSVs\n"
		f"input_count={len(input_paths)}\n"
		f"input_glob={args.input_glob}\n"
		f"row_count={row_count}\n"
		f"header_columns={len(header)}\n"
		f"output_path={args.output_path.resolve()}"
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())