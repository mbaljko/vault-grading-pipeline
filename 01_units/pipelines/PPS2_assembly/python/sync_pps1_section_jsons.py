#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync a section-specific PPS1 JSON directory from the importer audit CSV and activity-group roster.",
    )
    parser.add_argument("--section-column", required=True, help="Roster CSV column to use for section membership.")
    parser.add_argument("--section-output-dir", type=Path, required=True, help="Directory to populate with section JSON files.")
    parser.add_argument("--activity-group-csv", type=Path, required=True, help="Roster CSV containing section membership columns.")
    parser.add_argument("--audit-csv", type=Path, required=True, help="Importer audit CSV containing email to output_json_path mappings.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Optional directory containing the promoted JSON files. When provided, audit CSV filenames are resolved relative to this directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.section_output_dir.mkdir(parents=True, exist_ok=True)

    for existing_path in args.section_output_dir.glob("*.json"):
        existing_path.unlink()

    audit_lookup: dict[str, Path] = {}
    with args.audit_csv.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            email = (row.get("email_address") or "").strip().casefold()
            output_json_path = (row.get("output_json_path") or "").strip()
            if email and output_json_path:
                audit_lookup[email] = Path(output_json_path)

    copied = 0
    missing = 0
    with args.activity_group_csv.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if not (row.get(args.section_column) or "").strip():
                continue

            email = (row.get("Email address") or "").strip().casefold()
            source_path = audit_lookup.get(email)
            if source_path is None:
                missing += 1
                continue

            if args.source_dir is not None:
                source_path = args.source_dir / source_path.name

            if not source_path.exists():
                missing += 1
                continue

            shutil.copy2(source_path, args.section_output_dir / source_path.name)
            copied += 1

    print(f"Synced {copied} JSON files to {args.section_output_dir}")
    if missing:
        print(f"Skipped {missing} roster rows with no generated JSON", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())