#!/usr/bin/env python3
"""Execute compiled Layer 0 OperatorSpecs against a runtime CSV dataset."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from layer0_runtime import execute_batch_from_spec_path, write_diagnostics_jsonl, write_results_csv


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Run the deterministic Layer 0 operator engine over a runtime CSV dataset."
	)
	parser.add_argument(
		"--runtime-input",
		type=Path,
		required=True,
		help="Path to a runtime CSV containing submission_id, component_id, and response_text.",
	)
	parser.add_argument(
		"--operator-specs",
		type=Path,
		required=True,
		help="Path to compiled operator specs in JSON or Python form.",
	)
	parser.add_argument(
		"--output-csv",
		type=Path,
		required=True,
		help="Path to write the extraction results CSV.",
	)
	parser.add_argument(
		"--diagnostics-output",
		type=Path,
		help="Optional path to write runtime diagnostics JSONL.",
	)
	parser.add_argument(
		"--component-id",
		help="Optional component_id filter applied before executing the operator engine.",
	)
	return parser.parse_args()


def load_runtime_rows(path: Path) -> list[dict[str, object]]:
	runtime_path = path.resolve()
	if not runtime_path.exists():
		raise FileNotFoundError(f"Runtime input not found: {runtime_path}")
	with runtime_path.open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.DictReader(handle)
		rows = [dict(row) for row in reader]
	if not rows:
		raise ValueError(f"Runtime input CSV contains no data rows: {runtime_path}")
	return rows


def main() -> int:
	args = parse_args()
	runtime_rows = load_runtime_rows(args.runtime_input)
	if args.component_id:
		runtime_rows = [row for row in runtime_rows if str(row.get("component_id", "")) == args.component_id]
		if not runtime_rows:
			raise ValueError(
				f"Runtime input CSV contains no rows for component_id={args.component_id}: {args.runtime_input.resolve()}"
			)
	results, diagnostics = execute_batch_from_spec_path(runtime_rows, str(args.operator_specs.resolve()))
	write_results_csv(str(args.output_csv.resolve()), results)
	if args.diagnostics_output is not None:
		write_diagnostics_jsonl(str(args.diagnostics_output.resolve()), diagnostics)

	print(f"Runtime input: {args.runtime_input.resolve()}")
	if args.component_id:
		print(f"Component filter: {args.component_id}")
	print(f"Operator specs: {args.operator_specs.resolve()}")
	print(f"Results CSV: {args.output_csv.resolve()}")
	if args.diagnostics_output is not None:
		print(f"Diagnostics JSONL: {args.diagnostics_output.resolve()}")
	print(f"Extraction rows written: {len(results)}")
	print(f"Diagnostics written: {len(diagnostics)}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())