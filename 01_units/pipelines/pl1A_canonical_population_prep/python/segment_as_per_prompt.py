#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = next(
    (candidate for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents] if (candidate / ".git").exists()),
    None,
)
RESPONSE_TEXT_COLUMN = "response_text"
SUBMISSION_ID_COLUMN = "submission_id"
HEADER_BLOCK_RE = re.compile(r"\A\+\+\+(?P<header>[^\n]+)\n\+\+\+\n?", re.DOTALL)
FOOTER_BLOCK_RE = re.compile(r"\n?\+\+\+\s*\Z", re.DOTALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run prompt-driven segmentation through the shared LLM runner."
    )
    parser.add_argument("--input-path", type=Path, required=True, help="Source file for segmentation input.")
    parser.add_argument("--output-path", type=Path, required=True, help="Destination markdown file for runner output.")
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
        help="Sampling temperature forwarded to invoke_chatgpt_API.py.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="Top-p value forwarded to invoke_chatgpt_API.py.",
    )
    parser.add_argument(
        "--runner-dry-run",
        action="store_true",
        help="Forward --dry-run to invoke_chatgpt_API.py.",
    )
    return parser.parse_args()


def derive_runner_stem(output_path: Path) -> str:
    stem = output_path.stem
    if stem.endswith("_output"):
        return stem[:-7]
    return stem


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


def prepare_segmentation_rows(input_path: Path) -> list[dict[str, str]]:
    rows, response_text_key = load_csv_rows(input_path)
    prepared_rows: list[dict[str, str]] = []

    for row in rows:
        response_text = row.get(response_text_key, "")
        header_info, cleaned_text = extract_response_payload(response_text)
        submission_id = extract_submission_id(row, header_info)
        prepared_rows.append(
            {
                "submission_id": submission_id,
                "submission_header": header_info,
                "cleaned_response_text": cleaned_text,
            }
        )

    return prepared_rows


def write_segmentation_rows(output_path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["submission_id", "submission_header", "cleaned_response_text"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> int:
    args = parse_args()
    if REPO_ROOT is None:
        raise RuntimeError("Could not locate repository root from script path.")

    input_path = args.input_path.resolve()
    output_path = args.output_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    segmentation_rows = prepare_segmentation_rows(input_path)
    for row in segmentation_rows:
        print(row["cleaned_response_text"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_segmentation_rows(output_path, segmentation_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())