#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from component_scored_texts import load_scored_rows_from_paths, resolve_component_scored_csv_paths, write_scored_rows


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Materialize one component-scoped scored CSV from a scoring-output directory or file reference."
	)
	parser.add_argument("--input-ref", type=Path, required=True, help="Scored input directory or file reference.")
	parser.add_argument("--component-id", type=str, required=True, help="Component ID used to select matching scored files.")
	parser.add_argument(
		"--expected-version-label",
		type=str,
		required=False,
		help="Optional version label used to filter per-indicator outputs, e.g. 05.",
	)
	parser.add_argument("--output-file", type=Path, required=True, help="Path for the combined scored CSV.")
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	input_paths = resolve_component_scored_csv_paths(
		args.input_ref.resolve(strict=False),
		args.component_id,
		args.expected_version_label,
	)
	if not input_paths:
		print(
			f"Error: no scored CSV inputs matched component_id={args.component_id} under {args.input_ref}",
			file=sys.stderr,
		)
		return 1
	rows = load_scored_rows_from_paths(input_paths)
	write_scored_rows(rows, args.output_file)
	print(args.output_file)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())