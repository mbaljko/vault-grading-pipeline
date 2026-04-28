from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


ASST_ROOT = Path("/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPP")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 1 (trivial): collect assignment component counts from a grades CSV."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        required=True,
        help="Path to the input grades CSV.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional output path for component counts CSV. Defaults next to input.",
    )
    parser.add_argument(
        "--component-field",
        type=str,
        default="component_id",
        help="CSV column name that stores the assignment component id.",
    )
    return parser.parse_args()


def read_component_counts(input_csv: Path, component_field: str) -> tuple[int, Counter[str]]:
    if not input_csv.exists() or not input_csv.is_file():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    with input_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"No header found in CSV: {input_csv}")
        if component_field not in reader.fieldnames:
            raise ValueError(
                f"Missing required column '{component_field}' in {input_csv}. "
                f"Found columns: {reader.fieldnames}"
            )

        counts: Counter[str] = Counter()
        total_rows = 0
        for row in reader:
            total_rows += 1
            component_id = (row.get(component_field) or "").strip() or "<blank>"
            counts[component_id] += 1

    return total_rows, counts


def write_component_counts(output_csv: Path, counts: Counter[str]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["component_id", "row_count"])
        writer.writeheader()
        for component_id, row_count in sorted(counts.items(), key=lambda item: item[0]):
            writer.writerow({"component_id": component_id, "row_count": row_count})


def main() -> None:
    args = parse_args()
    input_csv = args.input_csv.resolve()
    output_csv = (
        args.output_csv.resolve()
        if args.output_csv is not None
        else input_csv.with_name(f"{input_csv.stem}_component_counts.csv")
    )

    total_rows, counts = read_component_counts(input_csv, args.component_field)
    write_component_counts(output_csv, counts)

    print(f"Input: {input_csv}")
    print(f"Rows scanned: {total_rows}")
    print(f"Unique components: {len(counts)}")
    print(f"Output: {output_csv}")


if __name__ == "__main__":
    main()
