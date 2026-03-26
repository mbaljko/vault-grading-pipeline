#!/usr/bin/env python3
"""Generate a Layer 1 indicator scoring prompt for a single component.

This script mirrors the existing justfile workflow used to build a temporary
payload from an assignment payload file and a scoring manifest, then optionally
invoke the configured prompt runner to generate the final scoring prompt.

Usage modes:
1. Build the payload only with --emit-payload-only.
2. Build the payload and invoke the prompt runner.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PAYLOAD_DELIMITER = "§§§"


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate a Layer 1 indicator scoring prompt for a single component."
	)
	parser.add_argument(
		"--assignment-payload-file",
		type=Path,
		required=True,
		help="Path to the assignment payload markdown file.",
	)
	parser.add_argument(
		"--scoring-manifest-file",
		type=Path,
		required=True,
		help="Path to the Layer 1 scoring manifest markdown file.",
	)
	parser.add_argument(
		"--target-component-id",
		type=str,
		required=True,
		help="Component ID to embed in the payload, e.g. SectionB1Response.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		required=True,
		help="Directory where the payload and generated prompt output should be written.",
	)
	parser.add_argument(
		"--output-file-stem",
		type=str,
		required=True,
		help="Output file stem passed to the prompt runner.",
	)
	parser.add_argument(
		"--prompt-instructions-file",
		type=Path,
		required=False,
		help="Prompt instructions file passed to the prompt runner.",
	)
	parser.add_argument(
		"--prompt-runner",
		type=Path,
		required=False,
		help="Path to the prompt runner script to invoke after building the payload.",
	)
	parser.add_argument(
		"--payload-file",
		type=Path,
		required=False,
		help="Explicit payload file path. Defaults to <output-dir>/TMP_generate_l1_scoring_prompt_payload.md.",
	)
	parser.add_argument(
		"--output-format",
		type=str,
		default="md",
		help="Output format passed to the prompt runner. Defaults to md.",
	)
	parser.add_argument(
		"--timeout-seconds",
		type=int,
		default=600,
		help="Timeout passed to the prompt runner. Defaults to 600.",
	)
	parser.add_argument(
		"--temperature",
		type=float,
		default=0.0,
		help="Temperature passed to the prompt runner. Defaults to 0.0.",
	)
	parser.add_argument(
		"--top-p",
		type=float,
		default=1.0,
		help="Top-p passed to the prompt runner. Defaults to 1.0.",
	)
	parser.add_argument(
		"--emit-payload-only",
		action="store_true",
		help="Write the payload file and stop without invoking the prompt runner.",
	)
	return parser.parse_args()


def read_text_file(path: Path) -> str:
	if not path.exists() or not path.is_file():
		raise FileNotFoundError(f"File not found: {path}")
	return path.read_text(encoding="utf-8")


def build_payload_text(component_id: str, assignment_payload_text: str, scoring_manifest_text: str) -> str:
	return (
		f"{PAYLOAD_DELIMITER}\n"
		f"PARAM_TARGET_COMPONENT_ID = {component_id}\n"
		f"{PAYLOAD_DELIMITER}\n"
		f"{assignment_payload_text}"
		f"\n{PAYLOAD_DELIMITER}\n"
		f"{scoring_manifest_text}"
	)


def resolve_payload_path(output_dir: Path, explicit_payload_path: Path | None) -> Path:
	if explicit_payload_path is not None:
		return explicit_payload_path
	return output_dir / "TMP_generate_l1_scoring_prompt_payload.md"


def write_payload_file(payload_path: Path, payload_text: str) -> None:
	payload_path.parent.mkdir(parents=True, exist_ok=True)
	payload_path.write_text(payload_text, encoding="utf-8")


def build_prompt_runner_command(args: argparse.Namespace, payload_path: Path) -> list[str]:
	if args.prompt_runner is None:
		raise ValueError("--prompt-runner is required unless --emit-payload-only is used.")
	if args.prompt_instructions_file is None:
		raise ValueError("--prompt-instructions-file is required unless --emit-payload-only is used.")
	if not args.prompt_runner.exists() or not args.prompt_runner.is_file():
		raise FileNotFoundError(f"Prompt runner not found: {args.prompt_runner}")
	if not args.prompt_instructions_file.exists() or not args.prompt_instructions_file.is_file():
		raise FileNotFoundError(f"Prompt instructions file not found: {args.prompt_instructions_file}")
	return [
		sys.executable,
		str(args.prompt_runner),
		"--prompt-instructions-file",
		str(args.prompt_instructions_file),
		"--prompt-input-file",
		str(payload_path),
		"--output-dir",
		str(args.output_dir),
		"--output-file-stem",
		args.output_file_stem,
		"--output-format",
		args.output_format,
		"--timeout-seconds",
		str(args.timeout_seconds),
		"--temperature",
		str(args.temperature),
		"--top-p",
		str(args.top_p),
	]


def main() -> int:
	args = parse_args()
	assignment_payload_file = args.assignment_payload_file.resolve()
	scoring_manifest_file = args.scoring_manifest_file.resolve()
	output_dir = args.output_dir.resolve()
	payload_path = resolve_payload_path(output_dir, args.payload_file.resolve() if args.payload_file else None)

	try:
		assignment_payload_text = read_text_file(assignment_payload_file)
		scoring_manifest_text = read_text_file(scoring_manifest_file)
		payload_text = build_payload_text(
			args.target_component_id.strip(),
			assignment_payload_text,
			scoring_manifest_text,
		)
		write_payload_file(payload_path, payload_text)
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	if args.emit_payload_only:
		print(payload_path)
		return 0

	try:
		command = build_prompt_runner_command(args, payload_path)
	except (FileNotFoundError, ValueError) as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	completed = subprocess.run(command, check=False)
	return completed.returncode


if __name__ == "__main__":
	raise SystemExit(main())