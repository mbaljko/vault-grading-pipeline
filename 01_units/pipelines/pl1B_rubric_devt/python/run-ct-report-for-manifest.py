#!/usr/bin/env python3
"""Run L1 CT prompt runner for manifest rows that match a component ID, then stitch response texts.

This script scans markdown table rows in `--sbo-manifest-file`, selects rows
whose raw row line contains `--component-id`, and for each matching row:
invokes `invoke_chatgpt_with_payload.py` to produce an LLM output markdown
file, then stitches response texts from `--file-with-response-texts` into
Panel A/B/C tables in that output.

Arguments:
- `--sbo-manifest-file`: markdown manifest file to parse.
- `--component-id`: string token used to select matching table rows.
- `--file-with-response-texts`: CSV file with `submission_id` and
  `response_text` columns; used to augment Panel tables in stitching step.
- `--file-with-scored-texts`: CSV used to find matching rows by `indicator_id`.
- `--runner-dry-run`: when set, forwards `--dry-run` to
	`invoke_chatgpt_with_payload.py`.

Per matching row behavior:
1. Extract `sbo_identifier` from the row and print it to stdout.
2. Build `components` dict from markdown header/value cells.
3. Build `scored_payload` with `matching_scored_rows` filtered by
	`indicator_id`.
4. Write payload file `<sbo_identifier>_payload.json` in the manifest
	directory. Payload file content is delimiter-separated text:
	- `===`
	- JSON for `components`
	- `===`
	- JSON for `scored_payload`
	- `===`
5. Invoke `invoke_chatgpt_with_payload.py` with:
	- `--prompt-file` from `L1_CT_PROMPT_FILE_RELATIVE`
	- `--payload-file` from step 4
	- `--output-file-stem <sbo_identifier>`
	- `--output-dir <manifest_dir>/<RUNNER_OUTPUT_SUBDIR>`
	- `--output-format md`
	Returns the path to the LLM output markdown file.
6. Apply response text stitching to the LLM output file:
	- Reads `--file-with-response-texts` CSV to build a
	  `submission_id -> response_text` lookup.
	- Copies the LLM output markdown verbatim, with the YAML front matter
	  passed through unchanged (plus a `post_processing` field appended
	  before the closing `---`).
	- Replaces each Panel A/B/C table with an augmented version that adds
	  a `response_text` column populated by submission_id lookup.
	- Writes output to `<llm_output_stem>_stitched.md` in the same directory.

Exit behavior:
- Returns 1 with stderr message when required input files are missing.

Example:
	python run-ct-report-for-manifest.py \
		--sbo-manifest-file /path/to/Layer1_ScoringManifest_PPP_v01.md \
		--component-id SectionCResponse \
		--file-with-response-texts /path/to/response_texts.csv \
		--file-with-scored-texts /path/to/scored_texts.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path


SBO_IDENTIFIER_RE = re.compile(r"\bI_[A-Za-z0-9_]+\b")
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
PANEL_HEADER_RE = re.compile(r"^\s*#{5}\s*Panel\s+[ABC]\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT: Path | None = next(
	(candidate for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents] if (candidate / ".git").exists()),
	None,
)
RUNNER_SCRIPT_RELATIVE = Path("01_units/apps/prompt_runners/invoke_chatgpt_with_payload.py")
L1_CT_PROMPT_FILE_RELATIVE = Path(
	"01_units/pipelines/pl1B_rubric_devt/llm_prompt/"
	"pl1B_prompt_stage13_Layer1_Generate_Calibration_Triage_Report_singleSBO.md"
)
RUNNER_OUTPUT_SUBDIR = "Level1-CalibrationTesting-Outputs"


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
	parser.add_argument(
		"--file-with-response-texts",
		type=Path,
		required=True,
		help="Path to response-texts input file for payload augmentation.",
	)
	parser.add_argument(
		"--file-with-scored-texts",
		type=Path,
		required=True,
		help="Path to scored-texts input file for payload augmentation.",
	)
	parser.add_argument(
		"--runner-dry-run",
		action="store_true",
		help="Forward --dry-run to invoke_chatgpt_with_payload.py.",
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


def load_scored_rows(input_path: Path) -> list[dict[str, str]]:
	"""Load scored-text rows from CSV as normalized dictionaries."""
	rows: list[dict[str, str]] = []
	with input_path.open("r", encoding="utf-8-sig", newline="") as f:
		reader = csv.DictReader(f)
		if not reader.fieldnames:
			return rows

		for raw_row in reader:
			normalized_row: dict[str, str] = {}
			for key, value in raw_row.items():
				if key is None:
					continue
				normalized_row[key.strip()] = (value or "").strip()
			rows.append(normalized_row)

	return rows


def find_matching_scored_rows(
	manifest_components: dict[str, str],
	scored_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
	"""Find scored-text rows matching the current manifest row by indicator_id."""
	indicator_id = (manifest_components.get("indicator_id") or "").strip()
	if not indicator_id:
		return []

	matches: list[dict[str, str]] = []
	for row in scored_rows:
		if (row.get("indicator_id") or "").strip() == indicator_id:
			matches.append(row)

	return matches


def run_l1_ct_for_payload(
	payload_dir: Path,
	components: dict[str, str],
	scored_payload: dict[str, object],
	output_file_stem: str,
	runner_dry_run: bool,
) -> Path:
	"""Invoke the same runner behavior as justfile target l1-ct-secC.
	
	Returns the path to the markdown output file written by the runner.
	"""
	if REPO_ROOT is None:
		raise RuntimeError("Could not locate repository root from script path.")

	runner_script = REPO_ROOT / RUNNER_SCRIPT_RELATIVE
	prompt_file = REPO_ROOT / L1_CT_PROMPT_FILE_RELATIVE
	payload_file = payload_dir / f"{output_file_stem}_payload.json"
	runner_output_dir = payload_dir / RUNNER_OUTPUT_SUBDIR
	runner_output_dir.mkdir(parents=True, exist_ok=True)
	runner_output_file = runner_output_dir / f"{output_file_stem}_output.md"

	components_json = json.dumps(components, indent=2, ensure_ascii=False)
	scored_payload_json = json.dumps(scored_payload, indent=2, ensure_ascii=False)
	payload_body = (
		"===\n"
		f"{components_json}\n"
		"===\n"
		f"{scored_payload_json}\n"
		"===\n"
	)
	payload_file.write_text(payload_body, encoding="utf-8")

	cmd = [
		sys.executable,
		str(runner_script),
		"--output-format",
		"md",
		"--output-dir",
		str(runner_output_dir),
		"--prompt-file",
		str(prompt_file),
		"--payload-file",
		str(payload_file),
		"--output-file-stem",
		output_file_stem,
	]
	if runner_dry_run:
		cmd.append("--dry-run")
	subprocess.run(cmd, check=True)
	
	return runner_output_file


def apply_response_text_stitcher(
	runner_output_file: Path,
	response_texts_file: Path,
	components: dict[str, str],
) -> Path:
	"""Apply response text stitching to runner output markdown file.

	Augments Panel A/B/C sections by:
	- Inserting the manifest row as a markdown table immediately after each
	  Panel A/B/C heading.
	- Adding a response_text column to each Panel table, matched by
	  submission_id from the response_texts CSV.
	Returns the path to the stitched output markdown file in the same directory.
	"""
	# Build lookup: submission_id -> response_text
	response_lookup: dict[str, str] = {}
	with response_texts_file.open("r", encoding="utf-8-sig", newline="") as f:
		reader = csv.DictReader(f)
		if not reader.fieldnames:
			response_lookup = {}
		else:
			normalized = {name.strip().lower(): name for name in reader.fieldnames if name}
			submission_key = normalized.get("submission_id")
			response_text_key = normalized.get("response_text")
			if submission_key and response_text_key:
				for row in reader:
					raw_submission_id = (row.get(submission_key) or "").strip()
					if raw_submission_id and raw_submission_id.isdigit() and raw_submission_id not in response_lookup:
						response_lookup[raw_submission_id] = row.get(response_text_key) or ""
	
	# Read input markdown and render augmented version
	with runner_output_file.open("r", encoding="utf-8") as f:
		markdown_lines = f.readlines()
	
	augmented_lines: list[str] = []
	i = 0
	in_target_panel = False
	
	# Skip YAML front matter block (--- ... ---) before processing markdown structure
	# Inject post_processing field before the closing --- line
	if markdown_lines and markdown_lines[0].rstrip() == "---":
		augmented_lines.append(markdown_lines[0])
		i = 1
		while i < len(markdown_lines):
			if markdown_lines[i].rstrip() == "---":
				augmented_lines.append(f"post_processing: response_text_stitched\n")
				augmented_lines.append(markdown_lines[i])
				i += 1
				break
			augmented_lines.append(markdown_lines[i])
			i += 1

	while i < len(markdown_lines):
		line = markdown_lines[i]
		
		if PANEL_HEADER_RE.match(line):
			in_target_panel = True
			augmented_lines.append(line)
			augmented_lines.append("\n")
			augmented_lines.extend(_render_manifest_row_table(components))
			augmented_lines.append("\n")
			i += 1
			continue
		
		if in_target_panel and HEADING_RE.match(line):
			in_target_panel = False
		
		if in_target_panel and line.lstrip().startswith("|"):
			# Collect full table
			table_lines: list[str] = []
			while i < len(markdown_lines) and markdown_lines[i].lstrip().startswith("|"):
				table_lines.append(markdown_lines[i])
				i += 1
			
			# Augment and append
			augmented_lines.extend(_augment_panel_table(table_lines, response_lookup))
			continue
		
		augmented_lines.append(line)
		i += 1
	
	# Derive output filename from runner output file stem + "_stitched"
	output_text = "".join(augmented_lines)
	output_path = runner_output_file.parent / f"{runner_output_file.stem}_stitched{runner_output_file.suffix}"
	output_path.write_text(output_text, encoding="utf-8")
	return output_path


def _render_manifest_row_table(components: dict[str, str]) -> list[str]:
	"""Render the manifest row components dict as a single-row markdown table."""
	if not components:
		return []
	headers = list(components.keys())
	values = [components[h] for h in headers]
	return [
		_format_markdown_row(headers),
		_format_markdown_row(["---"] * len(headers)),
		_format_markdown_row(values),
	]


def _parse_markdown_cells(line: str) -> list[str]:
	"""Parse pipe-delimited markdown table cells from a line."""
	parts = [part.strip() for part in line.strip().split("|")]
	if parts and parts[0] == "":
		parts = parts[1:]
	if parts and parts[-1] == "":
		parts = parts[:-1]
	return parts


def _is_markdown_separator_row(cells: list[str]) -> bool:
	"""Check if cells form a markdown table separator row."""
	if not cells:
		return False
	return all(bool(SEPARATOR_CELL_RE.match(cell.replace(" ", ""))) for cell in cells)


def _escape_markdown_cell(value: str) -> str:
	"""Escape pipe characters and remove newlines from markdown cell."""
	return value.replace("|", "\\|").replace("\n", " ").strip()


def _format_markdown_row(cells: list[str]) -> str:
	"""Format cells as markdown table row."""
	escaped = [_escape_markdown_cell(cell) for cell in cells]
	return "| " + " | ".join(escaped) + " |\n"


def _augment_panel_table(table_lines: list[str], response_lookup: dict[str, str]) -> list[str]:
	"""Augment a Panel A/B/C table with response_text column."""
	if not table_lines:
		return []
	
	rows = [_parse_markdown_cells(line) for line in table_lines if line.lstrip().startswith("|")]
	if not rows:
		return []
	
	header = rows[0]
	if not header:
		return []
	
	n_cols = len(header)
	output_lines: list[str] = []
	augmented_header = header + ["response_text"]
	output_lines.append(_format_markdown_row(augmented_header))
	output_lines.append(_format_markdown_row(["---"] * len(augmented_header)))
	
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
		output_lines.append(_format_markdown_row(row + [response_text]))
	
	return output_lines


def main() -> int:
	args = parse_args()
	markdown_path = args.sbo_manifest_file
	component_id = args.component_id
	response_texts_path = args.file_with_response_texts
	scored_texts_path = args.file_with_scored_texts
	runner_dry_run = args.runner_dry_run

	if not markdown_path.exists() or not markdown_path.is_file():
		print(f"Error: markdown file not found: {markdown_path}", file=sys.stderr)
		return 1
	if not response_texts_path.exists() or not response_texts_path.is_file():
		print(f"Error: response-texts file not found: {response_texts_path}", file=sys.stderr)
		return 1
	if not scored_texts_path.exists() or not scored_texts_path.is_file():
		print(f"Error: scored-texts file not found: {scored_texts_path}", file=sys.stderr)
		return 1

	payload_dir = markdown_path.resolve().parent

	scored_rows = load_scored_rows(scored_texts_path)

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
				matching_scored_rows = find_matching_scored_rows(components, scored_rows)
				scored_payload = {"matching_scored_rows": matching_scored_rows}
				print(sbo_identifier)
				#print(json.dumps(components, ensure_ascii=False))
				#print(json.dumps(scored_payload, ensure_ascii=False))
				runner_output_file = run_l1_ct_for_payload(
					payload_dir,
					components,
					scored_payload,
					sbo_identifier,
					runner_dry_run,
				)
				# Apply response text stitching to the runner output
				stitched_output_file = apply_response_text_stitcher(
					runner_output_file,
					response_texts_path,
					components,
				)
				# TODO: process stitched_output_file for further downstream handling
			i += 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
