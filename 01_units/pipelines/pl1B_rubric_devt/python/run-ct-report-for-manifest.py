#!/usr/bin/env python3
"""Read a markdown file and print every line to stdout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Print all lines from a markdown file.")
	parser.add_argument(
		"--markdown-file",
		type=Path,
		required=True,
		help="Path to the markdown file to print.",
	)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	markdown_path = args.markdown_file

	if not markdown_path.exists() or not markdown_path.is_file():
		print(f"Error: markdown file not found: {markdown_path}", file=sys.stderr)
		return 1

	with markdown_path.open("r", encoding="utf-8") as f:
		for line in f:
			sys.stdout.write(line)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
