#!/usr/bin/env python3
"""Extract submission-level score and validation labels from a stitched panel report.

The script reads a single stitched panel-report markdown file, finds all panel
tables that include `submission_id`, `evidence_status`, and `human_judge_notes`,
and writes a compact markdown report with one row per scored submission.

Output columns:
- `submission_id`
- `<iteration>-score`: `P` for `present`, `N` for `not_present`
- `<iteration>-validation`: `TP`, `FP`, `TN`, or `FN` parsed from
  `human_judge_notes`

The iteration label is inferred from the input path when possible, e.g. `iter01`.
Use `--iteration-label` to override it explicitly.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ITERATION_RE = re.compile(r"\b(iter\d+)\b", re.IGNORECASE)
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
VALIDATION_LABEL_RE = re.compile(r"\b(TP|FP|TN|FN)\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Extract submission-level validation labels from a stitched panel report."
	)
	parser.add_argument(
		"--panel-report-file",
		type=Path,
		required=True,
		help="Path to a stitched panel report markdown file.",
	)
	parser.add_argument(
		"--output-file",
		type=Path,
		required=False,
		help="Optional output markdown path. Defaults beside the input report.",
	)
	parser.add_argument(
		"--iteration-label",
		type=str,
		required=False,
		help="Optional iteration label override, e.g. iter01.",
	)
	return parser.parse_args()


def parse_markdown_cells(line: str) -> list[str]:
	parts = [part.strip() for part in line.strip().split("|")]
	if parts and parts[0] == "":
		parts = parts[1:]
	if parts and parts[-1] == "":
		parts = parts[:-1]
	return parts


def is_markdown_separator_row(cells: list[str]) -> bool:
	if not cells:
		return False
	return all(bool(SEPARATOR_CELL_RE.match(cell.replace(" ", ""))) for cell in cells)


def escape_markdown_cell(value: str) -> str:
	return value.replace("|", "\\|").replace("\n", " ").strip()


def format_markdown_row(cells: list[str]) -> str:
	return "| " + " | ".join(escape_markdown_cell(cell) for cell in cells) + " |\n"


def collect_markdown_tables(markdown_text: str) -> list[list[list[str]]]:
	lines = markdown_text.splitlines()
	tables: list[list[list[str]]] = []
	index = 0
	while index < len(lines):
		if not lines[index].lstrip().startswith("|"):
			index += 1
			continue
		table_lines: list[list[str]] = []
		while index < len(lines) and lines[index].lstrip().startswith("|"):
			table_lines.append(parse_markdown_cells(lines[index]))
			index += 1
		if table_lines:
			tables.append(table_lines)
	return tables


def normalize_header_name(value: str) -> str:
	return value.strip().lower().replace("-", "_").replace(" ", "_")


def derive_iteration_label(input_path: Path, explicit_label: str | None) -> str:
	if explicit_label:
		return explicit_label.strip()
	for part in input_path.parts:
		match = ITERATION_RE.search(part)
		if match:
			return match.group(1).lower()
	match = ITERATION_RE.search(str(input_path))
	if match:
		return match.group(1).lower()
	return "iteration"


def default_output_path(input_path: Path) -> Path:
	return input_path.with_name(f"{input_path.stem}_human_judge_notes_summary.md")


def map_score_label(evidence_status: str) -> str:
	normalized = evidence_status.strip().lower()
	if normalized == "present":
		return "P"
	if normalized == "not_present":
		return "N"
	return ""


def parse_validation_label(human_judge_notes: str) -> str:
	matches = {match.group(1).upper() for match in VALIDATION_LABEL_RE.finditer(human_judge_notes)}
	if not matches:
		return ""
	if len(matches) > 1:
		raise ValueError(
			f"Expected at most one validation label in human_judge_notes, found {sorted(matches)} in: {human_judge_notes!r}"
		)
	return next(iter(matches))


def extract_submission_rows(markdown_text: str) -> list[dict[str, str]]:
	records_by_submission_id: dict[str, dict[str, str]] = {}
	ordered_submission_ids: list[str] = []

	for table in collect_markdown_tables(markdown_text):
		if not table:
			continue
		headers = [normalize_header_name(cell) for cell in table[0]]
		if not {"submission_id", "evidence_status", "human_judge_notes"}.issubset(headers):
			continue
		header_index = {header: idx for idx, header in enumerate(headers)}
		data_start = 1
		if len(table) > 1 and is_markdown_separator_row(table[1]):
			data_start = 2

		for row in table[data_start:]:
			if is_markdown_separator_row(row):
				continue
			if len(row) < len(headers):
				row = row + [""] * (len(headers) - len(row))
			submission_id = row[header_index["submission_id"]].strip()
			if not submission_id:
				continue
			evidence_status = row[header_index["evidence_status"]].strip()
			validation = parse_validation_label(row[header_index["human_judge_notes"]].strip())
			record = {
				"submission_id": submission_id,
				"score": map_score_label(evidence_status),
				"validation": validation,
			}
			existing = records_by_submission_id.get(submission_id)
			if existing is not None and existing != record:
				raise ValueError(
					"Found conflicting rows for submission_id "
					f"{submission_id}: existing={existing}, new={record}"
				)
			if existing is None:
				ordered_submission_ids.append(submission_id)
				records_by_submission_id[submission_id] = record

	return [records_by_submission_id[submission_id] for submission_id in ordered_submission_ids]


def render_output_report(input_path: Path, iteration_label: str, records: list[dict[str, str]]) -> str:
	score_column = f"{iteration_label}-score"
	validation_column = f"{iteration_label}-validation"
	lines = [
		"# Human judge notes summary\n",
		"\n",
		f"- Source panel report: {input_path}\n",
		f"- Rows extracted: {len(records)}\n",
		"\n",
		format_markdown_row(["submission_id", score_column, validation_column]),
		format_markdown_row(["---", "---", "---"]),
	]
	for record in records:
		lines.append(
			format_markdown_row(
				[
					record["submission_id"],
					record["score"],
					record["validation"],
				]
			)
		)
	return "".join(lines)


def main() -> int:
	args = parse_args()
	input_path = args.panel_report_file.resolve()
	output_path = args.output_file.resolve() if args.output_file else default_output_path(input_path)

	if not input_path.exists() or not input_path.is_file():
		print(f"Error: panel report file not found: {input_path}", file=sys.stderr)
		return 1

	iteration_label = derive_iteration_label(input_path, args.iteration_label)
	try:
		records = extract_submission_rows(input_path.read_text(encoding="utf-8"))
	except ValueError as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	output_text = render_output_report(input_path, iteration_label, records)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(output_text, encoding="utf-8")
	print(output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())