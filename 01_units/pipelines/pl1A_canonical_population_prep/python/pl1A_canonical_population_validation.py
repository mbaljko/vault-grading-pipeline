#!/usr/bin/env python3

"""Print rows from the canonical-population and gradework-sheet CSV inputs.

This is a small companion utility for quick inspection of CSV inputs during pipeline
development. It reads two CSV files with header rows and prints each row to stdout as a
single JSON object, prefixed with its 1-based row number and input label.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read the canonical-population and gradework-sheet CSV files and print each data row to stdout.",
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        required=True,
        help="Path to the canonical-population CSV file to read.",
    )
    parser.add_argument(
        "--gradework-sheet-input-path",
        type=Path,
        required=True,
        help="Path to the gradework-sheet CSV file to read.",
    )
    return parser.parse_args()


def print_csv_rows(label: str, input_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"[{label}] path={input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header row: {input_path}")

        for row_number, row in enumerate(reader, start=1):
            normalized_row = {
                (key.strip() if key is not None else ""): (value or "")
                for key, value in row.items()
                if key is not None
            }
            print(f"[{label}] row {row_number}: {json.dumps(normalized_row, ensure_ascii=False)}")


def main() -> int:
    args = parse_args()
    input_path = args.input_path.resolve()
    gradework_sheet_input_path = args.gradework_sheet_input_path.resolve()

    print_csv_rows("canonical_population", input_path)
    print_csv_rows("gradework_sheet", gradework_sheet_input_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())