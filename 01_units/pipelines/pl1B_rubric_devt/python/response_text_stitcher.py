#!/usr/bin/env python3
"""Print only Panel A/B/C table lines from a markdown input file.

Usage:
	python response_text_stitcher.py --input-file-based path/to/file.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PANEL_HEADER_RE = re.compile(r"^\s*#{5}\s*Panel\s+[ABC]\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s*#{1,6}\s+")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Print every line from a file.")
	parser.add_argument(
		"--input-file-based",
		type=Path,
		required=True,
		help="Path to the input file whose lines will be printed to stdout.",
	)
	return parser.parse_args()


def print_panel_table_lines(input_path: Path) -> None:
	"""Print table rows that appear under Panel A/B/C sections."""
	in_target_panel = False

	with input_path.open("r", encoding="utf-8") as f:
		for line in f:
			if PANEL_HEADER_RE.match(line):
				in_target_panel = True
				continue

			if in_target_panel and HEADING_RE.match(line):
				in_target_panel = False

			if in_target_panel and line.lstrip().startswith("|"):
				sys.stdout.write(line)


def main() -> int:
	args = parse_args()
	input_path = args.input_file_based

	if not input_path.exists() or not input_path.is_file():
		print(f"Error: input file not found: {input_path}", file=sys.stderr)
		return 1

	print_panel_table_lines(input_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
