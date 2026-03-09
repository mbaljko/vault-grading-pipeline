#!/usr/bin/env python3
"""Print Panel A/B/C markdown tables augmented with response_text.

Usage:
	python response_text_stitcher.py \
		--input-file-base path/to/file.md \
		--input-file-response-texts path/to/response_texts.md

Behavior:
	- Reads Panel A/B/C tables from --input-file-base.
	- Re-emits each panel table as a valid markdown table.
	- Adds `response_text` as a fourth column using submission_id matches from
	  --input-file-response-texts.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


PANEL_HEADER_RE = re.compile(r"^\s*#{5}\s*Panel\s+[ABC]\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Print table lines from Panel A/B/C in a markdown file."
	)
	parser.add_argument(
		"--input-file-base",
		type=Path,
		required=True,
		help="Fallback markdown input file.",
	)
	parser.add_argument(
		"--input-file-response-texts",
		type=Path,
		required=True,
		help="File used to look up rows by submission_id.",
	)
	return parser.parse_args()


def _parse_markdown_cells(line: str) -> list[str]:
	parts = [part.strip() for part in line.strip().split("|")]
	if parts and parts[0] == "":
		parts = parts[1:]
	if parts and parts[-1] == "":
		parts = parts[:-1]
	return parts


def _is_markdown_separator_row(cells: list[str]) -> bool:
	if not cells:
		return False
	return all(bool(SEPARATOR_CELL_RE.match(cell.replace(" ", ""))) for cell in cells)


def _extract_submission_id_from_table_line(line: str) -> str | None:
	if not line.lstrip().startswith("|"):
		return None

	cells = _parse_markdown_cells(line)
	if not cells:
		return None
	if _is_markdown_separator_row(cells):
		return None
	if cells[0].lower() == "submission_id":
		return None

	submission_id = cells[0].strip()
	if submission_id.isdigit():
		return submission_id
	return None


def build_response_text_lookup(input_path: Path) -> dict[str, str]:
	"""Build submission_id -> response_text mapping from a CSV input file."""
	lookup: dict[str, str] = {}

	with input_path.open("r", encoding="utf-8-sig", newline="") as f:
		reader = csv.DictReader(f)
		if not reader.fieldnames:
			return lookup

		normalized = {name.strip().lower(): name for name in reader.fieldnames if name}
		submission_key = normalized.get("submission_id")
		response_text_key = normalized.get("response_text")
		if not submission_key or not response_text_key:
			return lookup

		for row in reader:
			raw_submission_id = (row.get(submission_key) or "").strip()
			if not raw_submission_id or not raw_submission_id.isdigit():
				continue
			if raw_submission_id in lookup:
				continue

			lookup[raw_submission_id] = row.get(response_text_key) or ""

	return lookup


def _escape_markdown_cell(value: str) -> str:
	return value.replace("|", "\\|").replace("\n", " ").strip()


def _format_markdown_row(cells: list[str]) -> str:
	escaped = [_escape_markdown_cell(cell) for cell in cells]
	return "| " + " | ".join(escaped) + " |\n"


def _print_augmented_panel_table(table_lines: list[str], response_lookup: dict[str, str]) -> None:
	if not table_lines:
		return

	rows = [_parse_markdown_cells(line) for line in table_lines if line.lstrip().startswith("|")]
	if not rows:
		return

	header = rows[0]
	if not header:
		return

	n_cols = len(header)
	augmented_header = header + ["response_text"]
	sys.stdout.write(_format_markdown_row(augmented_header))
	sys.stdout.write(_format_markdown_row(["---"] * len(augmented_header)))

	data_start = 1
	if len(rows) > 1 and _is_markdown_separator_row(rows[1]):
		data_start = 2

	for row in rows[data_start:]:
		if _is_markdown_separator_row(row):
			continue

		if len(row) < n_cols:
			row = row + [""] * (n_cols - len(row))
		elif len(row) > n_cols:
			row = row[:n_cols]

		submission_id = row[0].strip()
		response_text = response_lookup.get(submission_id, "") if submission_id.isdigit() else ""
		sys.stdout.write(_format_markdown_row(row + [response_text]))


def print_panel_table_lines(input_path: Path, response_lookup: dict[str, str]) -> None:
	"""Print augmented markdown tables for Panel A/B/C sections."""
	in_target_panel = False
	panel_heading = ""
	table_lines: list[str] = []
	table_printed = False

	def flush_panel_table() -> None:
		nonlocal table_lines, table_printed
		if table_printed or not panel_heading or not table_lines:
			return
		sys.stdout.write(panel_heading + "\n\n")
		_print_augmented_panel_table(table_lines, response_lookup)
		sys.stdout.write("\n")
		table_printed = True

	with input_path.open("r", encoding="utf-8") as f:
		for line in f:
			if PANEL_HEADER_RE.match(line):
				flush_panel_table()
				in_target_panel = True
				panel_heading = line.rstrip("\n")
				table_lines = []
				table_printed = False
				continue

			if not in_target_panel:
				continue

			if HEADING_RE.match(line):
				flush_panel_table()
				in_target_panel = False
				continue

			if line.lstrip().startswith("|"):
				table_lines.append(line)
			elif table_lines:
				flush_panel_table()

	flush_panel_table()


def main() -> int:
	args = parse_args()
	input_path = args.input_file_base
	response_texts_path = args.input_file_response_texts

	if not input_path.exists() or not input_path.is_file():
		print(f"Error: input file not found: {input_path}", file=sys.stderr)
		return 1
	if not response_texts_path.exists() or not response_texts_path.is_file():
		print(f"Error: response-texts file not found: {response_texts_path}", file=sys.stderr)
		return 1

	response_lookup = build_response_text_lookup(response_texts_path)
	print_panel_table_lines(input_path, response_lookup)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
