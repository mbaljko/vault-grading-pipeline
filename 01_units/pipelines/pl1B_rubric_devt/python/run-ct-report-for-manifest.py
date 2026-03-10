#!/usr/bin/env python3
"""Run L1 CT prompt runner for manifest rows that match a component ID.

This script scans markdown table rows in `--sbo-manifest-file`, selects rows
whose raw row line contains `--component-id`, and builds per-row payload inputs
for `invoke_chatgpt_with_payload.py`.

Arguments:
- `--sbo-manifest-file`: markdown manifest to parse.
- `--component-id`: string token used to select matching table rows.
- `--file-with-response-texts`: validated input file path (reserved for
  payload augmentation).
- `--file-with-scored-texts`: CSV used to find matching rows by `indicator_id`.

Per matching row behavior:
1. Extract `sbo_identifier` from the row and print it to stdout.
2. Build `components` from markdown header/value cells.
3. Build `scored_payload` with `matching_scored_rows` filtered by
	`indicator_id`.
4. Write payload file `<sbo_identifier>_payload.json` in manifest directory.
	Payload file content is text with delimiters:
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
RUNNER_OUTPUT_SUBDIR = "llm_runner_outputs"


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
) -> None:
	"""Invoke the same runner behavior as justfile target l1-ct-secC."""
	if REPO_ROOT is None:
		raise RuntimeError("Could not locate repository root from script path.")

	runner_script = REPO_ROOT / RUNNER_SCRIPT_RELATIVE
	prompt_file = REPO_ROOT / L1_CT_PROMPT_FILE_RELATIVE
	payload_file = payload_dir / f"{output_file_stem}_payload.json"
	runner_output_dir = payload_dir / RUNNER_OUTPUT_SUBDIR
	runner_output_dir.mkdir(parents=True, exist_ok=True)

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
		#"--dry-run",
	]
	subprocess.run(cmd, check=True)


def main() -> int:
	args = parse_args()
	markdown_path = args.sbo_manifest_file
	component_id = args.component_id
	response_texts_path = args.file_with_response_texts
	scored_texts_path = args.file_with_scored_texts

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
				run_l1_ct_for_payload(
					payload_dir,
					components,
					scored_payload,
					sbo_identifier,
				)
			i += 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
