#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


RESPONSE_TEXT_COLUMN = "response_text"
SUBMISSION_ID_COLUMN = "submission_id"
HEADER_BLOCK_RE = re.compile(r"\A\+\+\+(?P<header>[^\n]+)\n\+\+\+\n?", re.DOTALL)
FOOTER_BLOCK_RE = re.compile(r"\n?\+\+\+\s*\Z", re.DOTALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean segmentation input rows, invoke the shared LLM runner, and write a normalized CSV output."
    )
    parser.add_argument("--input-path", type=Path, required=True, help="Source file for segmentation input.")
    parser.add_argument("--output-path", type=Path, required=True, help="Destination CSV file for cleaned segmentation rows.")
    parser.add_argument(
        "--runner-prompt-path",
        type=Path,
        required=True,
        help="Prompt instructions file passed through to the shared LLM runner.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature passed to the shared LLM runner.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="Top-p value passed to the shared LLM runner.",
    )
    parser.add_argument(
        "--runner-dry-run",
        action="store_true",
        help="Pass --dry-run through to the shared LLM runner instead of calling the API.",
    )
    return parser.parse_args()


def load_csv_rows(input_path: Path) -> tuple[list[dict[str, str]], str]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header row: {input_path}")

        normalized_fieldnames = {field.strip().lower(): field for field in reader.fieldnames if field}
        response_text_key = normalized_fieldnames.get(RESPONSE_TEXT_COLUMN)
        if response_text_key is None:
            raise ValueError(
                f"CSV is missing required '{RESPONSE_TEXT_COLUMN}' column: {input_path}"
            )

        rows: list[dict[str, str]] = []
        for raw_row in reader:
            normalized_row: dict[str, str] = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                normalized_row[key.strip()] = (value or "")
            rows.append(normalized_row)

    return rows, response_text_key


def extract_response_payload(response_text: str) -> tuple[str, str]:
    stripped_text = response_text.strip()
    header_info = ""

    header_match = HEADER_BLOCK_RE.match(stripped_text)
    if header_match:
        header_info = header_match.group("header").strip()
        stripped_text = stripped_text[header_match.end():]

    stripped_text = FOOTER_BLOCK_RE.sub("", stripped_text).strip()
    return header_info, stripped_text


def extract_submission_id(row: dict[str, str], header_info: str) -> str:
    submission_id = row.get(SUBMISSION_ID_COLUMN, "").strip()
    if submission_id:
        return submission_id

    prefix = "submission_id="
    if header_info.startswith(prefix):
        return header_info[len(prefix):].strip()

    return ""


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError(f"Could not locate repository root from: {start}")


def resolve_runner_script_path() -> Path:
    repo_root = find_repo_root(Path(__file__).resolve().parent)
    runner_script_path = repo_root / "01_units/apps/prompt_runners/invoke_chatgpt_API.py"
    if not runner_script_path.exists():
        raise FileNotFoundError(f"Runner script not found: {runner_script_path}")
    return runner_script_path


def invoke_runner_for_row(
    runner_script_path: Path,
    runner_prompt_path: Path,
    cleaned_response_text: str,
    submission_id: str,
    row_index: int,
    temperature: float,
    top_p: float,
    runner_dry_run: bool,
) -> tuple[str, str]:
    file_stem_base = submission_id or f"row_{row_index:04d}"
    file_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", file_stem_base).strip("_") or f"row_{row_index:04d}"

    with tempfile.TemporaryDirectory(prefix=f"segment_runner_{file_stem}_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        prompt_input_path = temp_dir / f"{file_stem}_input.txt"
        prompt_input_path.write_text(cleaned_response_text, encoding="utf-8")

        command = [
            sys.executable,
            str(runner_script_path),
            "--prompt-instructions-file",
            str(runner_prompt_path),
            "--prompt-input-file",
            str(prompt_input_path),
            "--temperature",
            str(temperature),
            "--top-p",
            str(top_p),
            "--output-dir",
            str(temp_dir),
            "--output-file-stem",
            file_stem,
            "--output-format",
            "json",
        ]
        if runner_dry_run:
            command.append("--dry-run")

        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            stderr_text = completed.stderr.strip() or completed.stdout.strip()
            return "", stderr_text or f"Runner failed for row {row_index}."

        if runner_dry_run:
            return "", ""

        extracted_json_path = temp_dir / f"{file_stem}_output.json"
        if not extracted_json_path.exists():
            return "", f"Runner output file was not created: {extracted_json_path}"

        payload = json.loads(extracted_json_path.read_text(encoding="utf-8"))
        extracted_output_text = payload.get("extracted_output_text", "")
        if not isinstance(extracted_output_text, str):
            return "", f"Runner output payload is missing string extracted_output_text for row {row_index}."

        return extracted_output_text, ""


def prepare_segmentation_rows(
    input_path: Path,
    runner_script_path: Path,
    runner_prompt_path: Path,
    temperature: float,
    top_p: float,
    runner_dry_run: bool,
) -> list[dict[str, str]]:
    rows, response_text_key = load_csv_rows(input_path)
    prepared_rows: list[dict[str, str]] = []

    for row_index, row in enumerate(rows, start=1):
        response_text = row.get(response_text_key, "")
        header_info, cleaned_text = extract_response_payload(response_text)
        submission_id = extract_submission_id(row, header_info)
        llm_output_text, llm_error = invoke_runner_for_row(
            runner_script_path=runner_script_path,
            runner_prompt_path=runner_prompt_path,
            cleaned_response_text=cleaned_text,
            submission_id=submission_id,
            row_index=row_index,
            temperature=temperature,
            top_p=top_p,
            runner_dry_run=runner_dry_run,
        )
        prepared_rows.append(
            {
                "submission_id": submission_id,
                "submission_header": header_info,
                "cleaned_response_text": cleaned_text,
                "llm_output_text": llm_output_text,
                "llm_error": llm_error,
            }
        )

    return prepared_rows


def write_segmentation_rows(output_path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "submission_id",
        "submission_header",
        "cleaned_response_text",
        "llm_output_text",
        "llm_error",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> int:
    args = parse_args()

    input_path = args.input_path.resolve()
    output_path = args.output_path.resolve()
    runner_prompt_path = args.runner_prompt_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not runner_prompt_path.exists():
        raise FileNotFoundError(f"Runner prompt file not found: {runner_prompt_path}")

    runner_script_path = resolve_runner_script_path()
    segmentation_rows = prepare_segmentation_rows(
        input_path=input_path,
        runner_script_path=runner_script_path,
        runner_prompt_path=runner_prompt_path,
        temperature=args.temperature,
        top_p=args.top_p,
        runner_dry_run=args.runner_dry_run,
    )
    for row in segmentation_rows:
        print(row["cleaned_response_text"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_segmentation_rows(output_path, segmentation_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())