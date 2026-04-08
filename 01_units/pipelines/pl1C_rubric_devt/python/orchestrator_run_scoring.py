#!/usr/bin/env python3
"""Orchestrate prompt-runner scoring for either whole-payload or per-row execution.

This module sits in front of the shared API runner and provides one extra layer
of execution control for grading workflows that need either:

- a single scoring call over the full prompt payload, or
- one scoring call per response row followed by CSV reassembly.

The script preserves the existing prompt-runner command-line contract as much as
possible. Most arguments are passed through unchanged to the underlying runner.
The orchestrator itself adds only a small number of control arguments,
primarily ``--api-runner-script`` and ``--scoring-mode``.

Execution modes:

- ``batch``:
	Forward the request directly to the supplied API runner script. This is the
	simplest mode and is appropriate when the prompt and input payload are meant
	to be processed in one invocation.
- ``single-response``:
	Read the prompt input payload, split it into one runtime unit per response,
	invoke the supplied API runner once for each unit, and merge the resulting
	CSV outputs into one final CSV artifact. This is useful when per-response
	isolation improves reliability, debuggability, or output discipline.

Input handling:

- CSV payloads are split into one header-plus-one-data-row payload per call.
- Non-CSV payloads are split on non-empty lines, with one line sent per call.
- Empty rows or lines are skipped.

Output handling:

- In ``batch`` mode, output generation is delegated entirely to the shared
	runner.
- In ``single-response`` mode, this script writes the merged CSV output and a
	companion run-metadata JSON file that records timing, runner configuration,
	request paths, and CSV header information.

This module does not interpret scoring semantics. It only manages invocation
shape, output-path resolution, and post-run aggregation.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument(
		"--api-runner-script",
		type=Path,
		required=True,
		help="Path to the shared API runner script to invoke for each scoring call.",
	)
	parser.add_argument(
		"--scoring-mode",
		choices=["batch", "single-response"],
		default="batch",
		help="Run one API call for the full payload or one call per response row.",
	)
	parser.add_argument("--prompt-input-file", type=Path, default=None)
	parser.add_argument("--prompt-input-json", default=None)
	parser.add_argument("--prompt-instructions-file", type=Path, default=None)
	parser.add_argument("--output-dir", type=Path, default=None)
	parser.add_argument("--output-file-stem", default=None)
	parser.add_argument("--output-format", action="append", default=None)
	parser.add_argument("--save-full-api-response", action="store_true")
	parser.add_argument("--dry-run", action="store_true")
	args, _ = parser.parse_known_args(argv)
	return args, strip_orchestrator_args(argv)


def strip_orchestrator_args(argv: list[str]) -> list[str]:
	filtered: list[str] = []
	skip_next = False
	for token in argv:
		if skip_next:
			skip_next = False
			continue
		if token == "--api-runner-script":
			skip_next = True
			continue
		if token.startswith("--api-runner-script="):
			continue
		if token == "--scoring-mode":
			skip_next = True
			continue
		if token.startswith("--scoring-mode="):
			continue
		filtered.append(token)
	return filtered


def strip_option(argv: list[str], option: str, takes_value: bool) -> list[str]:
	filtered: list[str] = []
	skip_next = False
	for token in argv:
		if skip_next:
			skip_next = False
			continue
		if token == option:
			skip_next = takes_value
			continue
		if takes_value and token.startswith(f"{option}="):
			continue
		filtered.append(token)
	return filtered


def resolve_output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
	stem = resolve_output_stem(args)
	if args.output_dir:
		output_dir = args.output_dir.resolve()
		output_dir.mkdir(parents=True, exist_ok=True)
	elif args.prompt_instructions_file:
		output_dir = args.prompt_instructions_file.resolve().parent
	else:
		output_dir = Path(__file__).resolve().parent
	return output_dir / f"{stem}_output.csv", output_dir / f"{stem}_run_metadata.json"


def resolve_output_stem(args: argparse.Namespace) -> str:
	return args.output_file_stem or (
		args.prompt_instructions_file.stem if args.prompt_instructions_file else "invoke_chatgpt_API"
	)


def iter_single_response_payloads(prompt_input_file: Path) -> list[str]:
	raw_text = prompt_input_file.read_text(encoding="utf-8-sig")
	if prompt_input_file.suffix.lower() == ".csv":
		reader = csv.reader(io.StringIO(raw_text))
		rows = list(reader)
		if len(rows) < 2:
			raise ValueError(f"Single-response mode requires at least one data row: {prompt_input_file}")
		header = rows[0]
		payloads: list[str] = []
		for row in rows[1:]:
			if not any(cell.strip() for cell in row):
				continue
			buffer = io.StringIO()
			writer = csv.writer(buffer, lineterminator="\n")
			writer.writerow(header)
			writer.writerow(row)
			payloads.append(buffer.getvalue())
		if not payloads:
			raise ValueError(f"Single-response mode found no non-empty data rows: {prompt_input_file}")
		return payloads

	lines = [line for line in raw_text.splitlines() if line.strip()]
	if not lines:
		raise ValueError(f"Single-response mode found no non-empty lines: {prompt_input_file}")
	return [f"{line}\n" for line in lines]


def read_csv_rows(csv_path: Path) -> list[list[str]]:
	with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
		return list(csv.reader(handle))


def merge_csv_outputs(csv_paths: list[Path], final_output_path: Path) -> tuple[int, list[str]]:
	merged_header: list[str] | None = None
	merged_rows: list[list[str]] = []
	for csv_path in csv_paths:
		rows = read_csv_rows(csv_path)
		if not rows:
			continue
		header, *data_rows = rows
		if merged_header is None:
			merged_header = header
		elif header != merged_header:
			raise ValueError(
				"Single-response scoring produced inconsistent CSV headers; "
				f"expected {merged_header!r}, got {header!r} from {csv_path}"
			)
		merged_rows.extend(data_rows)

	if merged_header is None:
		raise ValueError("Single-response scoring produced no CSV output to merge.")

	final_output_path.parent.mkdir(parents=True, exist_ok=True)
	with final_output_path.open("w", encoding="utf-8-sig", newline="") as handle:
		writer = csv.writer(handle)
		writer.writerow(merged_header)
		writer.writerows(merged_rows)
	return len(merged_rows), merged_header


def write_metadata_output(
	metadata_path: Path,
	args: argparse.Namespace,
	final_output_path: Path,
	response_count: int,
	header: list[str],
	elapsed_seconds: float,
) -> None:
	metadata = {
		"generated_at_utc": datetime.now(timezone.utc).isoformat(),
		"runner": {
			"script_path": str(Path(__file__).resolve()),
			"api_runner_script": str(args.api_runner_script.resolve()),
			"mode": args.scoring_mode,
			"elapsed_seconds": round(elapsed_seconds, 3),
		},
		"request": {
			"prompt_input_path": str(args.prompt_input_file.resolve()) if args.prompt_input_file else None,
			"prompt_instructions_path": (
				str(args.prompt_instructions_file.resolve()) if args.prompt_instructions_file else None
			),
			"output_formats": args.output_format or ["csv"],
			"dry_run": bool(args.dry_run),
		},
		"response_count": response_count,
		"csv_header": header,
		"artifacts": {
			"csv": str(final_output_path.resolve()),
		},
	}
	metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def format_elapsed_hms(elapsed_seconds: float) -> str:
	total_seconds = max(0, int(round(elapsed_seconds)))
	hours, remainder = divmod(total_seconds, 3600)
	minutes, seconds = divmod(remainder, 60)
	return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def print_timing_summary(args: argparse.Namespace, elapsed_seconds: float, exit_code: int) -> None:
	print(
		"Completed scoring orchestrator\n"
		f"exit_code={exit_code}\n"
		f"mode={args.scoring_mode}\n"
		f"elapsed_seconds={elapsed_seconds:.3f}\n"
		f"elapsed_hms={format_elapsed_hms(elapsed_seconds)}"
	)


def invoke_runner(runner_path: Path, runner_args: list[str]) -> int:
	command = [sys.executable, str(runner_path), *runner_args]
	completed = subprocess.run(command, check=False)
	return completed.returncode


def run_single_response_mode(
	runner_path: Path,
	args: argparse.Namespace,
	forwarded_args: list[str],
) -> int:
	if args.prompt_input_json:
		raise ValueError("Single-response mode requires --prompt-input-file, not --prompt-input-json.")
	if not args.prompt_input_file:
		raise ValueError("Single-response mode requires --prompt-input-file.")
	if args.save_full_api_response:
		raise ValueError("Single-response mode does not support --save-full-api-response.")
	if args.dry_run:
		raise ValueError("Single-response mode does not support --dry-run.")
	requested_formats = set(args.output_format or ["csv"])
	if requested_formats != {"csv"}:
		raise ValueError("Single-response mode currently supports only --output-format csv.")

	base_args = strip_option(forwarded_args, "--prompt-input-file", takes_value=True)
	base_args = strip_option(base_args, "--output-dir", takes_value=True)
	base_args = strip_option(base_args, "--output-file-stem", takes_value=True)
	base_args = strip_option(base_args, "--output-format", takes_value=True)

	payloads = iter_single_response_payloads(args.prompt_input_file)
	final_output_path, metadata_path = resolve_output_paths(args)
	final_output_stem = resolve_output_stem(args)
	start_ts = time.perf_counter()
	invocation_csv_paths: list[Path] = []

	with tempfile.TemporaryDirectory(prefix="run-scoring-orchestrator-") as temp_dir_str:
		temp_dir = Path(temp_dir_str)
		for index, payload_text in enumerate(payloads, start=1):
			temp_input_path = temp_dir / f"prompt_input_{index:05d}.txt"
			temp_stem = f"{final_output_stem}__part_{index:05d}"
			temp_input_path.write_text(payload_text, encoding="utf-8")
			runner_args = [
				*base_args,
				"--prompt-input-file",
				str(temp_input_path),
				"--output-dir",
				str(temp_dir),
				"--output-file-stem",
				temp_stem,
				"--output-format",
				"csv",
			]
			print(
				f"Running response scoring (single-response) {index}/{len(payloads)} "
				f"for {args.prompt_input_file}"
			)
			exit_code = invoke_runner(runner_path, runner_args)
			if exit_code != 0:
				return exit_code
			invocation_csv_paths.append(temp_dir / f"{temp_stem}_output.csv")

		response_count, header = merge_csv_outputs(invocation_csv_paths, final_output_path)
	elapsed_seconds = time.perf_counter() - start_ts

	write_metadata_output(
		metadata_path=metadata_path,
		args=args,
		final_output_path=final_output_path,
		response_count=response_count,
		header=header,
		elapsed_seconds=elapsed_seconds,
	)
	print(f"Wrote aggregated CSV output: {final_output_path}")
	print(f"Wrote orchestrator metadata: {metadata_path}")
	return 0


def resolve_runner_path(args: argparse.Namespace) -> Path:
	runner_path = args.api_runner_script.resolve()
	if not runner_path.is_file():
		raise FileNotFoundError(f"Prompt runner not found: {runner_path}")
	return runner_path


def main() -> int:
	args, forwarded_args = parse_args(sys.argv[1:])
	start_ts = time.perf_counter()
	exit_code = 1
	try:
		runner_path = resolve_runner_path(args)
		if args.scoring_mode == "single-response":
			exit_code = run_single_response_mode(runner_path, args, forwarded_args)
			return exit_code

		exit_code = invoke_runner(runner_path, forwarded_args)
		return exit_code
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		exit_code = 1
		return exit_code
	finally:
		print_timing_summary(args, time.perf_counter() - start_ts, exit_code)


if __name__ == "__main__":
	raise SystemExit(main())