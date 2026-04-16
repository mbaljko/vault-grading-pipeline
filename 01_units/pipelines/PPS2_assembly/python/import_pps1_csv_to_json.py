#!/usr/bin/env python3
"""Import PPS1 LMS CSV data into per-student JSON files.

The script uses the key layout from a template JSON file, fills fields that can be
derived from the LMS export, writes one JSON file per CSV row into an "all"
directory, and copies a random sample into a second directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
from pathlib import Path
from typing import Any


DEFAULT_CSV_PATH = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/"
    "LMS_exported_data/PPS1 - Post-Practice Synthesis, Part 1-411-records-20260416_2145-comma_separated.csv"
)
DEFAULT_TEMPLATE_JSON_PATH = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/student_data/S042.json"
)
DEFAULT_ALL_OUTPUT_DIR = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/student_data_all"
)
DEFAULT_SAMPLE_OUTPUT_DIR = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/student_data"
)

ALL_DIMENSIONS = [
    "B-1",
    "B-2",
    "B-3",
    "C-1",
    "C-2",
    "C-3",
    "D-1",
    "D-2",
    "D-3",
]

SHORT_TO_DOTTED_DIMENSION = {
    "B-1": "B.2.1",
    "B-2": "B.2.2",
    "B-3": "B.2.3",
    "C-1": "C.2.1",
    "C-2": "C.2.2",
    "C-3": "C.2.3",
    "D-1": "D.2.1",
    "D-2": "D.2.2",
    "D-3": "D.2.3",
}

DOTTED_TO_SHORT_DIMENSION = {value: key for key, value in SHORT_TO_DOTTED_DIMENSION.items()}

DIRECT_FIELD_MAP = {
    "B11Response": "B-1-PPP",
    "B12Response": "B-2-PPP",
    "B13Response": "B-3-PPP",
    "B21Response": "B-1-PPS1",
    "B22Response": "B-2-PPS1",
    "B23Response": "B-3-PPS1",
    "B3 PPS Concept List": "B3 PPS Concept List",
    "B3Interpretation": "B3Interpretation",
    "B3Use": "B3Use",
    "C11Response": "C-1-PPP",
    "C12Response": "C-2-PPP",
    "C13Response": "C-3-PPP",
    "C21Response": "C-1-PPS1",
    "C22Response": "C-2-PPS1",
    "C23Response": "C-3-PPS1",
    "C3 PPS Concept List": "C3 PPS Concept List",
    "C3Interpretation": "C3Interpretation",
    "C3Use": "C3Use",
    "D11Response": "D-1-PPP",
    "D12Response": "D-2-PPP",
    "D13Response": "D-3-PPP",
    "D21Response": "D-1-PPS1",
    "D22Response": "D-2-PPS1",
    "D23Response": "D-3-PPS1",
    "D3 PPS Concept List": "D3 PPS Concept List",
    "D3Interpretation": "D3Interpretation",
    "D3Use": "D3Use",
    "E21Response": "E-1-PPS1",
    "E22Response": "E-2-PPS1",
    "E23Response": "E-3-PPS1",
    "E24Response": "E-4-PPS1",
    "E25Response": "E-5-PPS1",
    "GenAIAttestation": "GenAIAttestation",
}

GRID_STATUS_MAP = {
    "E2_00_GridResponse": "stable",
    "E2_10_GridResponse": "stable",
    "E2_01_GridResponse": "in tension",
    "E2_11_GridResponse": "in tension",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PPS1 LMS CSV rows into per-student JSON files.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--template-json", type=Path, default=DEFAULT_TEMPLATE_JSON_PATH)
    parser.add_argument("--all-output-dir", type=Path, default=DEFAULT_ALL_OUTPUT_DIR)
    parser.add_argument("--sample-output-dir", type=Path, default=DEFAULT_SAMPLE_OUTPUT_DIR)
    parser.add_argument("--sample-size", type=int, default=5)
    parser.add_argument("--sample-seed", type=int)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def load_template_keys(template_json_path: Path) -> list[str]:
    data = json.loads(template_json_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Template JSON must contain an object: {template_json_path}")
    return list(data.keys())


def normalize_value(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def sanitize_filename(raw_value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_value.strip())
    cleaned = cleaned.strip("._")
    return cleaned or fallback


def split_user_name(user_value: str, username_value: str) -> tuple[str, str]:
    parts = [part for part in user_value.split() if part]
    if not parts:
        fallback = username_value.strip() or "Unknown"
        return "", fallback
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def build_empty_record(template_keys: list[str]) -> dict[str, str]:
    return {key: "" for key in template_keys}


def checked(value: str) -> bool:
    normalized = value.strip().casefold()
    return normalized in {"✓", "true", "yes", "1"}


def derive_development_value(row: dict[str, str], prefix: str) -> str:
    if checked(normalize_value(row.get(f"{prefix}_shift"))):
        return "Shift"
    if checked(normalize_value(row.get(f"{prefix}_cont"))):
        return "Cont/Reinf"
    if checked(normalize_value(row.get(f"{prefix}_intro"))):
        return "Intro"
    return ""


def populate_status_values(record: dict[str, str], row: dict[str, str]) -> None:
    for grid_key, status_value in GRID_STATUS_MAP.items():
        dimension_value = normalize_value(row.get(grid_key))
        short_dimension = DOTTED_TO_SHORT_DIMENSION.get(dimension_value)
        if not short_dimension:
            continue
        record[f"{short_dimension}-status"] = status_value


def populate_development_values(record: dict[str, str], row: dict[str, str]) -> None:
    for dimension in ALL_DIMENSIONS:
        prefix = SHORT_TO_DOTTED_DIMENSION[dimension].replace(".", "")
        record[f"{dimension}-devt"] = derive_development_value(row, prefix)


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def select_section_dimensions(record: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    priority = ordered_unique(
        [dimension for dimension in ALL_DIMENSIONS if record.get(f"{dimension}-status")]
        + [dimension for dimension in ALL_DIMENSIONS if record.get(f"{dimension}-devt")]
        + ALL_DIMENSIONS
    )
    section1 = priority[:3]
    remaining = [dimension for dimension in priority if dimension not in section1]
    section2 = remaining[:3]
    tension_dims = [dimension for dimension in ALL_DIMENSIONS if record.get(f"{dimension}-status") == "in tension"]
    tension_priority = ordered_unique(tension_dims + section2 + remaining)
    section3 = tension_priority[:2]
    return section1, section2, section3


def populate_section_fields(record: dict[str, str]) -> None:
    section1_dims, section2_dims, section3_dims = select_section_dimensions(record)

    for index, dimension in enumerate(section1_dims, start=1):
        record[f"Sec1_TS{index}_dim"] = SHORT_TO_DOTTED_DIMENSION[dimension]
        record[f"Sec1_TS{index}_PPP"] = record.get(f"{dimension}-PPP", "")
        record[f"Sec1_TS{index}_PPS1"] = record.get(f"{dimension}-PPS1", "")

    for index, dimension in enumerate(section2_dims, start=1):
        record[f"Sec2_V{index}_dim"] = SHORT_TO_DOTTED_DIMENSION[dimension]
        record[f"Sec2_V{index}_PPP"] = record.get(f"{dimension}-PPP", "")
        record[f"Sec2_V{index}_PPS1"] = record.get(f"{dimension}-PPS1", "")

    for index, dimension in enumerate(section3_dims, start=1):
        record[f"SecC_T{index}_dim"] = SHORT_TO_DOTTED_DIMENSION[dimension]
        record[f"SecC_T{index}_PPS1"] = record.get(f"{dimension}-PPS1", "")

    if section2_dims:
        record["CLM_01_dimension"] = SHORT_TO_DOTTED_DIMENSION[section2_dims[0]]
        record["CLM_01_text"] = record.get(f"{section2_dims[0]}-PPS1", "")
    if len(section2_dims) > 1:
        record["CLM_02_text"] = record.get(f"{section2_dims[1]}-PPS1", "")
    if len(section2_dims) > 2:
        record["CLM_03_text"] = record.get(f"{section2_dims[2]}-PPS1", "")


def build_record(template_keys: list[str], row: dict[str, str]) -> dict[str, str]:
    record = build_empty_record(template_keys)

    user_value = normalize_value(row.get("User"))
    username_value = normalize_value(row.get("Username"))
    given_name, family_name = split_user_name(user_value, username_value)

    record["participant_id"] = username_value or sanitize_filename(user_value, "unknown")
    record["GIVEN_NAME"] = given_name
    record["FAMILY_NAME"] = family_name

    for csv_key, json_key in DIRECT_FIELD_MAP.items():
        if json_key in record:
            record[json_key] = normalize_value(row.get(csv_key))

    populate_development_values(record, row)
    populate_status_values(record, row)
    populate_section_fields(record)

    return record


def make_output_filename(row: dict[str, str], used_names: set[str], row_index: int) -> str:
    user_value = normalize_value(row.get("User"))
    username_value = normalize_value(row.get("Username"))
    base_name = sanitize_filename(user_value, username_value or f"row_{row_index:04d}")
    if base_name not in used_names:
        used_names.add(base_name)
        return f"{base_name}.json"

    fallback_name = sanitize_filename(username_value, f"row_{row_index:04d}")
    candidate = f"{base_name}__{fallback_name}" if fallback_name else f"{base_name}__{row_index:04d}"
    counter = 2
    unique_candidate = candidate
    while unique_candidate in used_names:
        unique_candidate = f"{candidate}_{counter}"
        counter += 1
    used_names.add(unique_candidate)
    return f"{unique_candidate}.json"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def duplicate_sample(all_paths: list[Path], sample_output_dir: Path, sample_size: int, sample_seed: int | None) -> list[Path]:
    sample_output_dir.mkdir(parents=True, exist_ok=True)
    if not all_paths or sample_size <= 0:
        return []
    count = min(sample_size, len(all_paths))
    chooser = random.Random(sample_seed) if sample_seed is not None else random.SystemRandom()
    selected_paths = chooser.sample(all_paths, count)
    copied_paths: list[Path] = []
    for source_path in selected_paths:
        target_path = sample_output_dir / source_path.name
        shutil.copy2(source_path, target_path)
        copied_paths.append(target_path)
    return copied_paths


def main() -> int:
    args = parse_args()
    template_keys = load_template_keys(args.template_json)
    args.all_output_dir.mkdir(parents=True, exist_ok=True)

    written_paths: list[Path] = []
    used_names: set[str] = set()

    with args.csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header row: {args.csv_path}")

        for row_index, row in enumerate(reader, start=1):
            record = build_record(template_keys, row)
            file_name = make_output_filename(row, used_names, row_index)
            output_path = args.all_output_dir / file_name
            write_json(output_path, record)
            written_paths.append(output_path)
            if args.verbose:
                print(f"Wrote {output_path}")

    copied_paths = duplicate_sample(
        all_paths=written_paths,
        sample_output_dir=args.sample_output_dir,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
    )

    print(f"Wrote {len(written_paths)} JSON files to {args.all_output_dir}")
    print(f"Copied {len(copied_paths)} sampled JSON files to {args.sample_output_dir}")
    if args.verbose and copied_paths:
        for copied_path in copied_paths:
            print(f"Sampled {copied_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())