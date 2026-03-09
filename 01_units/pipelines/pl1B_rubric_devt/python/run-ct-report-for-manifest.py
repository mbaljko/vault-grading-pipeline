#!/usr/bin/env python3
"""Filter manifest markdown lines by component ID.

This script reads a markdown file and prints to stdout only the lines that
contain the provided `--component-id` string.

Arguments:
- --sbo-manifest-file: path to the markdown file to scan.
- --component-id: string token used to match lines.

Output:
- For each matching line, exactly two lines are written:
	1) `sbo_identifier` only
	2) a JSON payload containing only the table row components mapped from the
		 table header to row values
- If the markdown file is missing, an error is written to stderr and the script
	exits with code 1.

Example:
		python run-ct-report-for-manifest.py \
			--sbo-manifest-file /path/to/Layer1_ScoringManifest_PPP_v01.md \
			--component-id SectionCResponse
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SBO_IDENTIFIER_RE = re.compile(r"\bI_[A-Za-z0-9_]+\b")
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Print markdown lines that contain the specified component ID."
	)
	parser.add_argument(
		"--sbo-manifest-file",
		type=Path,
		required=True,
		help="Path to the markdown file to read.",
	)
	parser.add_argument(
		"--component-id",
		type=str,
		required=True,
		help="Component ID used to filter matching lines.",
	)
	return parser.parse_args()


def extract_sbo_identifier(line: str) -> str:
	"""Extract SBO identifier token from a manifest line."""
	match = SBO_IDENTIFIER_RE.search(line)
	if match:
		return match.group(0)
	return "UNKNOWN_SBO_IDENTIFIER"


def parse_markdown_cells(line: str) -> list[str]:
	parts = [part.strip() for part in line.strip().split("|")]
	if parts and parts[0] == "":
		parts = parts[1:]
	if parts and parts[-1] == "":
		parts = parts[:-1]
	return parts


def is_separator_row(cells: list[str]) -> bool:
	if not cells:
		return False
	return all(bool(SEPARATOR_CELL_RE.match(cell.replace(" ", ""))) for cell in cells)


def main() -> int:
	args = parse_args()
	markdown_path = args.sbo_manifest_file
	component_id = args.component_id

	if not markdown_path.exists() or not markdown_path.is_file():
		print(f"Error: markdown file not found: {markdown_path}", file=sys.stderr)
		return 1

	with markdown_path.open("r", encoding="utf-8") as f:
		lines = f.readlines()

	i = 0
	while i < len(lines):
		line = lines[i]
		if not line.lstrip().startswith("|"):
			i += 1
			continue

		header_cells = parse_markdown_cells(line)
		if i + 1 >= len(lines):
			i += 1
			continue

		separator_cells = parse_markdown_cells(lines[i + 1])
		if not is_separator_row(separator_cells):
			i += 1
			continue

		i += 2
		while i < len(lines) and lines[i].lstrip().startswith("|"):
			row_line = lines[i]
			row_cells = parse_markdown_cells(row_line)
			if is_separator_row(row_cells):
				i += 1
				continue

			if component_id in row_line:
				padded = row_cells + [""] * (len(header_cells) - len(row_cells))
				components = {
					header_cells[idx]: padded[idx]
					for idx in range(len(header_cells))
				}
				sbo_identifier = extract_sbo_identifier(row_line)
				print(sbo_identifier)
				print(json.dumps(components, ensure_ascii=False))

			i += 1

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
