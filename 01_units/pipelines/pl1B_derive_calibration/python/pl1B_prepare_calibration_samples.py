#!/usr/bin/env python3

"""Prepare component-scoped calibration sample CSVs from a componentised input CSV.

This script consumes a long-form componentised CSV containing at least
``submission_id``, ``component_id``, and ``response_text``. It ports the sampling
rule from the Power Query workflow in
``01_units/pipelines/pl1B_derive_calibration/excel/03_sampling.pq``:

- build one long-format row per ``submission_id`` x ``component_id``
- compute ``response_wc`` for each cleaned response payload
- ignore empty / zero-word rows when sampling
- rank remaining rows by ``response_wc`` within each component
- drop the shortest and longest eligible row for that component
- sample up to ``m`` interior rows by uniform spacing over the wc-ranked rows

The output is one CSV per component, suitable for calibration scoring flows.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare one sampled calibration CSV per component_id from a componentised input CSV "
            "using the Power Query sampling rule."
        )
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        required=True,
        help="Path to the componentised CSV file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where component-scoped calibration sample CSVs will be written.",
    )
    parser.add_argument(
        "--output-file-template",
        required=True,
        help=(
            "Filename template for each sampled component CSV. Must contain {component_id}, "
            "for example AP2B_calibration_sample_2026_03_24_{component_id}.csv."
        ),
    )
    parser.add_argument(
        "--component-id",
        action="append",
        default=[],
        help=(
            "Optional component_id to sample. Repeat the argument or pass a comma-separated list. "
            "If omitted, all response components are sampled."
        ),
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=30,
        help="Maximum number of sampled interior rows to keep per component_id. Default: 30.",
    )
    return parser.parse_args()


def load_csv_rows(input_path: Path) -> list[dict[str, str]]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header row: {input_path}")

        rows: list[dict[str, str]] = []
        for raw_row in reader:
            normalized_row = {
                key.strip(): (value or "")
                for key, value in raw_row.items()
                if key is not None
            }
            if not any(value.strip() for value in normalized_row.values()):
                continue
            rows.append(normalized_row)
    return rows


def normalize_requested_component_ids(requested_component_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in requested_component_ids:
        for component_id in raw_value.split(","):
            candidate = component_id.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
    return normalized


def unwrap_response_payload(response_text: str) -> str:
    if not response_text:
        return ""
    lines = response_text.splitlines()
    if len(lines) >= 4 and lines[0].startswith("+++submission_id=") and lines[1].strip() == "+++":
        try:
            closing_index = lines.index("+++", 2)
        except ValueError:
            return response_text.strip()
        return "\n".join(lines[2:closing_index]).strip()
    return response_text.strip()


def classify_response_presence(payload: str) -> str:
    if not payload:
        return "EMPTY"
    placeholder_statuses = {
        "<<EMPTY>>": "EMPTY",
        "<<BLANKS>>": "BLANKS",
        "<<EMPTY_AFTER_CLEANING>>": "EMPTY_AFTER_CLEANING",
    }
    return placeholder_statuses.get(payload, "NONEMPTY")


def word_count_payload(value: str) -> int:
    normalized = value.replace("\n", " ").replace("\r", " ").strip()
    if not normalized:
        return 0
    return len([part for part in normalized.split(" ") if part])


def build_component_rows(
    raw_rows: list[dict[str, str]],
    requested_component_ids: list[str] | None = None,
) -> list[dict[str, str | int]]:
    required_columns = {"submission_id", "component_id", "response_text"}
    available_columns = set(raw_rows[0].keys()) if raw_rows else set()
    missing_columns = sorted(required_columns.difference(available_columns))
    if missing_columns:
        missing_display = ", ".join(missing_columns)
        raise ValueError(f"Input CSV is missing required column(s): {missing_display}")

    allowed_components = set(requested_component_ids or [])
    output_rows: list[dict[str, str | int]] = []
    for raw_row in raw_rows:
        component_id = raw_row.get("component_id", "").strip()
        if requested_component_ids and component_id not in allowed_components:
            continue

        submission_id = raw_row.get("submission_id", "").strip()
        response_text = raw_row.get("response_text", "")
        payload = unwrap_response_payload(response_text)
        response_presence = classify_response_presence(payload)
        output_rows.append(
            {
                "submission_id": submission_id,
                "component_id": component_id,
                "response_presence": response_presence,
                "response_wc": word_count_payload(payload),
                "response_text": response_text,
            }
        )

    if requested_component_ids:
        missing_component_ids = sorted(set(requested_component_ids).difference({row["component_id"] for row in output_rows}))
        if missing_component_ids:
            missing_display = ", ".join(missing_component_ids)
            raise ValueError(f"Requested component_id values not found in input CSV: {missing_display}")

    return output_rows


def sample_interior_uniform_rows(rows: list[dict[str, str | int]], sample_size: int) -> list[dict[str, str | int]]:
    eligible_rows = [row for row in rows if int(row.get("response_wc", 0)) > 0]
    rows_sorted = sorted(eligible_rows, key=lambda row: (int(row.get("response_wc", 0)), str(row.get("submission_id", ""))))
    total_rows = len(rows_sorted)
    if total_rows <= 2:
        return []

    interior_rows = rows_sorted[1:-1]
    interior_count = len(interior_rows)
    if interior_count == 0:
        return []
    if sample_size <= 0:
        return []
    if interior_count <= sample_size:
        return list(interior_rows)
    if sample_size == 1:
        return [interior_rows[interior_count // 2]]

    sampled_indexes: list[int] = []
    seen_indexes: set[int] = set()
    for sample_index in range(sample_size):
        interior_index = (sample_index * (interior_count - 1)) // (sample_size - 1)
        if interior_index in seen_indexes:
            continue
        seen_indexes.add(interior_index)
        sampled_indexes.append(interior_index)

    return [interior_rows[index] for index in sampled_indexes]


def group_rows_by_component(rows: list[dict[str, str | int]]) -> dict[str, list[dict[str, str | int]]]:
    grouped_rows: dict[str, list[dict[str, str | int]]] = defaultdict(list)
    for row in rows:
        component_id = str(row.get("component_id", "") or "")
        if component_id:
            grouped_rows[component_id].append(row)
    return dict(grouped_rows)


def resolve_output_path(output_dir: Path, output_file_template: str, component_id: str) -> Path:
    if "{component_id}" not in output_file_template:
        raise ValueError("--output-file-template must include the token {component_id}.")
    return output_dir / output_file_template.format(component_id=component_id)


def write_component_rows(output_path: Path, rows: list[dict[str, str | int]]) -> None:
    fieldnames = [
        "submission_id",
        "component_id",
        "response_presence",
        "response_wc",
        "response_text",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({fieldname: row.get(fieldname, "") for fieldname in fieldnames})


def print_summary(
    component_rows: list[dict[str, str | int]],
    sampled_rows_by_component: dict[str, list[dict[str, str | int]]],
    output_paths: dict[str, Path],
) -> None:
    print(f"[summary] component_rows={len(component_rows)}")
    print(f"[summary] sampled_components={len(sampled_rows_by_component)}")
    for component_id in sorted(sampled_rows_by_component):
        print(f"[summary] sampled_rows[{component_id}]={len(sampled_rows_by_component[component_id])}")
        print(f"[summary] output[{component_id}]={output_paths[component_id]}")


def main() -> int:
    args = parse_args()
    if args.sample_size < 0:
        raise ValueError(f"--sample-size must be non-negative, received: {args.sample_size}")

    input_path = args.input_path.resolve()
    output_dir = args.output_dir.resolve()
    requested_component_ids = normalize_requested_component_ids(args.component_id)

    raw_rows = load_csv_rows(input_path)
    component_rows = build_component_rows(
        raw_rows,
        requested_component_ids=requested_component_ids,
    )
    grouped_rows = group_rows_by_component(component_rows)

    sampled_rows_by_component: dict[str, list[dict[str, str | int]]] = {}
    output_paths: dict[str, Path] = {}
    for component_id in sorted(grouped_rows):
        sampled_rows = sample_interior_uniform_rows(grouped_rows[component_id], args.sample_size)
        output_path = resolve_output_path(output_dir, args.output_file_template, component_id)
        write_component_rows(output_path, sampled_rows)
        sampled_rows_by_component[component_id] = sampled_rows
        output_paths[component_id] = output_path

    print(f"[source_input] path={input_path}")
    print(f"[output_dir] path={output_dir}")
    print(f"[sample_size] value={args.sample_size}")
    print_summary(
        component_rows,
        sampled_rows_by_component,
        output_paths,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())