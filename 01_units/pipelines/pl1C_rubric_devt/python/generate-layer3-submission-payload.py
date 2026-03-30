#!/usr/bin/env python3
"""Combine Layer 3 component scoring outputs into a submission-level payload CSV."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from component_scored_texts import load_scored_rows, write_scored_rows


CONFIDENCE_ORDER = {
	"low": 0,
	"medium": 1,
	"high": 2,
	"": 3,
}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Combine Layer 3 component scoring outputs into a submission-level payload CSV."
	)
	parser.add_argument("--input-file", dest="input_files", action="append", type=Path, required=True)
	parser.add_argument("--output-file", type=Path, required=True)
	parser.add_argument("--submission-id-field", type=str, default="submission_id")
	parser.add_argument("--component-id-field", type=str, default="component_id")
	parser.add_argument("--sbo-identifier-field", type=str, default="sbo_identifier")
	parser.add_argument("--score-field", type=str, default="component_score")
	parser.add_argument("--flags-field", type=str, default="flags_any_dimension")
	parser.add_argument("--confidence-field", type=str, default="min_confidence_dimension")
	return parser.parse_args()


def normalize_confidence(value: object) -> str:
	return str(value or "").strip().lower()


def sort_submission_ids(values: set[str]) -> list[str]:
	def sort_key(value: str) -> tuple[int, object]:
		stripped = value.strip()
		if stripped.isdigit():
			return (0, int(stripped))
		return (1, stripped)

	return sorted(values, key=sort_key)


def aggregate_flags(values: list[str]) -> str:
	non_empty_values = [value.strip() for value in values if value.strip()]
	if not non_empty_values:
		return ""
	return " | ".join(dict.fromkeys(non_empty_values))


def aggregate_min_confidence(values: list[str]) -> str:
	normalized_values = [normalize_confidence(value) for value in values if normalize_confidence(value)]
	if not normalized_values:
		return ""
	return min(normalized_values, key=lambda value: CONFIDENCE_ORDER.get(value, len(CONFIDENCE_ORDER)))


def build_output_rows(
	input_files: list[Path],
	submission_id_field: str,
	component_id_field: str,
	sbo_identifier_field: str,
	score_field: str,
	flags_field: str,
	confidence_field: str,
) -> list[dict[str, str]]:
	rows_by_submission: dict[str, dict[str, str]] = {}
	flags_by_submission: dict[str, list[str]] = defaultdict(list)
	confidence_by_submission: dict[str, list[str]] = defaultdict(list)
	component_order: list[tuple[str, str]] = []
	seen_components: set[tuple[str, str]] = set()

	for input_file in input_files:
		for row in load_scored_rows(input_file):
			submission_id = str(row.get(submission_id_field, "")).strip()
			component_id = str(row.get(component_id_field, "")).strip()
			sbo_identifier = str(row.get(sbo_identifier_field, "")).strip()
			if not submission_id or not component_id:
				continue
			component_key = (component_id, sbo_identifier)
			if component_key not in seen_components:
				seen_components.add(component_key)
				component_order.append(component_key)
			output_row = rows_by_submission.setdefault(submission_id, {submission_id_field: submission_id})
			output_row[f"component_score__{component_id}"] = str(row.get(score_field, "")).strip()
			if sbo_identifier:
				output_row[f"component_score__{sbo_identifier}"] = str(row.get(score_field, "")).strip()
			flags_by_submission[submission_id].append(str(row.get(flags_field, "")))
			confidence_by_submission[submission_id].append(str(row.get(confidence_field, "")))

	for submission_id in sort_submission_ids(set(rows_by_submission.keys())):
		output_row = rows_by_submission[submission_id]
		for component_id, sbo_identifier in component_order:
			output_row.setdefault(f"component_score__{component_id}", "")
			if sbo_identifier:
				output_row.setdefault(f"component_score__{sbo_identifier}", "")
			output_row["flags_any_component"] = aggregate_flags(flags_by_submission[submission_id])
			output_row["min_confidence_component"] = aggregate_min_confidence(confidence_by_submission[submission_id])

	return [rows_by_submission[submission_id] for submission_id in sort_submission_ids(set(rows_by_submission.keys()))]


def main() -> int:
	args = parse_args()
	output_rows = build_output_rows(
		input_files=[input_file.resolve() for input_file in args.input_files],
		submission_id_field=args.submission_id_field,
		component_id_field=args.component_id_field,
		sbo_identifier_field=args.sbo_identifier_field,
		score_field=args.score_field,
		flags_field=args.flags_field,
		confidence_field=args.confidence_field,
	)
	write_scored_rows(output_rows, args.output_file.resolve())
	print(args.output_file.resolve())
	return 0


if __name__ == "__main__":
	raise SystemExit(main())