#!/usr/bin/env python3
"""Append response_text to scored CSV rows by submission_id.

Usage:
	python stitch_scored_csv_with_response_text.py \
		--input-file-scored path/to/scored.csv \
		--input-file-response-texts path/to/responses.csv \
		--output-file path/to/stitched.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Append response_text to a scored CSV using submission_id matches."
	)
	parser.add_argument(
		"--input-file-scored",
		type=Path,
		required=True,
		help="Scored CSV to enrich.",
	)
	parser.add_argument(
		"--input-file-response-texts",
		type=Path,
		required=True,
		help="CSV containing submission_id and response_text.",
	)
	parser.add_argument(
		"--output-file",
		type=Path,
		required=True,
		help="Destination CSV path.",
	)
	return parser.parse_args()


def _normalized_field_lookup(fieldnames: list[str] | None) -> dict[str, str]:
	if not fieldnames:
		return {}
	return {name.strip().lower(): name for name in fieldnames if name}


def build_response_text_lookup(input_path: Path) -> dict[str, str]:
	lookup: dict[str, str] = {}

	with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.DictReader(handle)
		normalized = _normalized_field_lookup(reader.fieldnames)
		submission_key = normalized.get("submission_id")
		response_text_key = normalized.get("response_text")
		if not submission_key or not response_text_key:
			raise ValueError(
				f"Expected columns 'submission_id' and 'response_text' in {input_path}"
			)

		for row in reader:
			raw_submission_id = (row.get(submission_key) or "").strip()
			if not raw_submission_id:
				continue
			if raw_submission_id in lookup:
				continue
			lookup[raw_submission_id] = row.get(response_text_key) or ""

	return lookup


def stitch_scored_csv(scored_path: Path, response_lookup: dict[str, str], output_path: Path) -> int:
	with scored_path.open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.DictReader(handle)
		if not reader.fieldnames:
			raise ValueError(f"No CSV header found in {scored_path}")

		normalized = _normalized_field_lookup(reader.fieldnames)
		submission_key = normalized.get("submission_id")
		if not submission_key:
			raise ValueError(f"Expected column 'submission_id' in {scored_path}")

		fieldnames = list(reader.fieldnames)
		if "response_text" not in fieldnames:
			fieldnames.append("response_text")

		output_path.parent.mkdir(parents=True, exist_ok=True)
		matched_rows = 0

		with output_path.open("w", encoding="utf-8", newline="") as output_handle:
			writer = csv.DictWriter(output_handle, fieldnames=fieldnames)
			writer.writeheader()

			for row in reader:
				submission_id = (row.get(submission_key) or "").strip()
				response_text = response_lookup.get(submission_id, "")
				if response_text:
					matched_rows += 1
				row["response_text"] = response_text
				writer.writerow({field: row.get(field, "") for field in fieldnames})

	return matched_rows


def main() -> int:
	args = parse_args()
	if not args.input_file_scored.is_file():
		print(f"Error: scored CSV not found: {args.input_file_scored}", file=sys.stderr)
		return 1
	if not args.input_file_response_texts.is_file():
		print(
			f"Error: response-text CSV not found: {args.input_file_response_texts}",
			file=sys.stderr,
		)
		return 1

	try:
		response_lookup = build_response_text_lookup(args.input_file_response_texts)
		matched_rows = stitch_scored_csv(
			args.input_file_scored,
			response_lookup,
			args.output_file,
		)
	except ValueError as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	print(f"Wrote {args.output_file} ({matched_rows} matched rows)")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())