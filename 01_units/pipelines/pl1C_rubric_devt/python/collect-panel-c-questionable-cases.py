#!/usr/bin/env python3
"""Collect Panel C questionable-case sections from stitched ITP worksheets.

This script scans a directory for stitched ITP worksheet markdown files,
including both current `*_output_stitched_worksheet.md` files and legacy
`*_output_stitched.md` files, extracts the section headed
`##### Panel C — Questionable cases` from each file, and writes a single
combined markdown report.

Arguments:
- `--input-dir`: directory containing stitched worksheet markdown files.
- `--output-file`: optional explicit output file path. Defaults to
	`<input-dir>/I_<assessment>_all_panel_c.md` when the assessment token can be
	inferred from stitched filenames, otherwise `<input-dir>/I_all_panel_c.md`.

Output behavior:
- Writes one combined markdown document.
- Includes one section per stitched worksheet that contains the target Panel C
  subsection.
- Skips files that do not contain the target subsection.

Section-boundary behavior:
- Extraction starts at the exact heading `##### Panel C — Questionable cases`.
- Extraction stops at the next heading with level 1 through 5, so nested level 6
  headings remain part of the captured section.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


STITCHED_REPORT_GLOBS = ["*_output_stitched_worksheet.md", "*_output_stitched.md"]
TARGET_HEADING = "##### Panel C — Questionable cases"
TARGET_HEADING_RE = re.compile(r"^\s*#####\s*Panel\s+C\s+—\s+Questionable\s+cases\s*$")
STOP_HEADING_RE = re.compile(r"^\s*#{1,5}\s+")
ASSESSMENT_FROM_STITCHED_RE = re.compile(r"^I_([A-Za-z0-9]+)_")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Collect Panel C questionable-case sections from stitched ITP reports."
	)
	parser.add_argument(
		"--input-dir",
		type=Path,
		required=True,
		help="Directory containing stitched worksheet markdown files.",
	)
	parser.add_argument(
		"--output-file",
		type=Path,
		required=False,
		help="Optional explicit output markdown file path.",
	)
	return parser.parse_args()


def default_output_path(input_dir: Path) -> Path:
	assessment_id = derive_assessment_id_from_stitched_reports(find_stitched_report_paths(input_dir))
	prefix = f"I_{assessment_id}" if assessment_id else "I"
	return input_dir / f"{prefix}_all_panel_c.md"


def find_stitched_report_paths(input_dir: Path) -> list[Path]:
	seen_paths: set[Path] = set()
	stitched_paths: list[Path] = []
	for glob_pattern in STITCHED_REPORT_GLOBS:
		for path in sorted(input_dir.glob(glob_pattern)):
			if not path.is_file() or path in seen_paths:
				continue
			seen_paths.add(path)
			stitched_paths.append(path)
	return stitched_paths


def derive_assessment_id_from_stitched_reports(stitched_paths: list[Path]) -> str | None:
	for path in stitched_paths:
		match = ASSESSMENT_FROM_STITCHED_RE.match(path.stem)
		if match:
			return match.group(1)
	return None


def extract_target_section(markdown_text: str) -> str | None:
	lines = markdown_text.splitlines(keepends=True)
	search_start_index = 0
	if lines and lines[0].strip() == "---":
		for index in range(1, len(lines)):
			if lines[index].strip() == "---":
				search_start_index = index + 1
				break
	start_index: int | None = None

	for index in range(search_start_index, len(lines)):
		line = lines[index]
		if TARGET_HEADING_RE.match(line.strip()):
			start_index = index
			break

	if start_index is None:
		return None

	end_index = len(lines)
	for index in range(start_index + 1, len(lines)):
		if STOP_HEADING_RE.match(lines[index]) and not TARGET_HEADING_RE.match(lines[index].strip()):
			end_index = index
			break

	section_text = "".join(lines[start_index:end_index]).strip()
	if not section_text:
		return None
	return section_text + "\n"


def render_combined_report(input_dir: Path, stitched_paths: list[Path]) -> str:
	output_lines = [
		"# Panel C — Questionable cases\n",
		"\n",
		f"- Input directory: {input_dir}\n",
		f"- Stitched reports scanned: {len(stitched_paths)}\n",
	]

	matched_count = 0
	for stitched_path in stitched_paths:
		section_text = extract_target_section(stitched_path.read_text(encoding="utf-8"))
		if section_text is None:
			continue

		matched_count += 1
		output_lines.extend(
			[
				"\n",
				f"## {stitched_path.stem}\n",
				"\n",
				f"- Source file: {stitched_path}\n",
				"\n",
				section_text,
			]
		)

	if matched_count == 0:
		output_lines.extend(
			[
				"\n",
				f"No `{TARGET_HEADING}` sections were found.\n",
			]
		)

	return "".join(output_lines)


def main() -> int:
	args = parse_args()
	input_dir = args.input_dir
	output_file = args.output_file or default_output_path(input_dir)

	if not input_dir.exists() or not input_dir.is_dir():
		print(f"Error: input directory not found: {input_dir}", file=sys.stderr)
		return 1

	stitched_paths = find_stitched_report_paths(input_dir)
	output_text = render_combined_report(input_dir, stitched_paths)
	output_file.parent.mkdir(parents=True, exist_ok=True)
	output_file.write_text(output_text, encoding="utf-8")
	print(output_file)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())