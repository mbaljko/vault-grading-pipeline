#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from import_pps1_csv_to_json import (
    DEFAULT_SCHEMA_PATH,
    build_audit_summary_report,
    build_pps1_text_development_summary_report,
    load_audit_rows_from_csv,
    load_pps1_text_development_rows_from_csv,
    load_schema,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Annotate staged PPS1 JSON files with STUDENT_POOL and IS_SAMPLE and promote them into final destination directories.",
    )
    parser.add_argument("--staged-dir", type=Path, required=True, help="Flat buffer directory containing staged JSON files.")
    parser.add_argument(
        "--sample-source-dir",
        type=Path,
        required=True,
        help="Temporary directory containing the importer-generated sample JSON files.",
    )
    parser.add_argument("--activity-group-csv", type=Path, required=True, help="Roster CSV containing section membership columns.")
    parser.add_argument("--audit-csv", type=Path, required=True, help="Importer audit CSV containing generated JSON filenames and emails.")
    parser.add_argument(
        "--group-output-root",
        type=Path,
        required=True,
        help="Root directory under which roster-derived output group directories will be created using CSV column headings.",
    )
    parser.add_argument(
        "--all-minus-sas-output-dir",
        type=Path,
        required=True,
        help="Final destination directory for non-SAS JSON files.",
    )
    parser.add_argument("--sample-output-dir", type=Path, required=True, help="Final destination directory for sampled JSON files.")
    return parser.parse_args()


def clear_json_files(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for existing_path in directory.glob("*.json"):
        existing_path.unlink()


def load_student_pool_by_filename(directories: list[Path]) -> dict[str, str]:
    student_pool_by_filename: dict[str, str] = {}
    for directory in directories:
        for json_path in directory.glob("*.json"):
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            student_pool = payload.get("STUDENT_POOL")
            if isinstance(student_pool, str) and student_pool:
                student_pool_by_filename[json_path.name] = student_pool
    return student_pool_by_filename


def load_group_memberships(activity_group_csv: Path) -> dict[str, set[str]]:
    group_memberships: dict[str, set[str]] = {}
    with activity_group_csv.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = [field_name.strip() for field_name in reader.fieldnames or [] if field_name and field_name.strip()]
        non_group_columns = {"First name", "Last name", "Email address"}
        group_columns = [field_name for field_name in fieldnames if field_name not in non_group_columns]
        group_memberships = {group_name: set() for group_name in group_columns}
        for row in reader:
            email = (row.get("Email address") or "").strip().casefold()
            if not email:
                continue
            for group_name in group_columns:
                if (row.get(group_name) or "").strip():
                    group_memberships[group_name].add(email)
    return group_memberships


def choose_student_pool(matched_groups: list[str]) -> str | None:
    legacy_groups = {"student_data_SAS_SecM", "student_data_SAS_SecO"}
    specific_groups = [group_name for group_name in matched_groups if group_name not in legacy_groups]
    if len(specific_groups) > 1:
        raise ValueError(
            "Roster membership is ambiguous: multiple specific output groups are marked: "
            + ", ".join(sorted(specific_groups))
        )
    if specific_groups:
        return specific_groups[0]

    matched_legacy_groups = [group_name for group_name in matched_groups if group_name in legacy_groups]
    if len(matched_legacy_groups) > 1:
        raise ValueError(
            "Roster membership is ambiguous: multiple legacy section groups are marked: "
            + ", ".join(sorted(matched_legacy_groups))
        )
    if matched_legacy_groups:
        return matched_legacy_groups[0]
    return None


def main() -> int:
    args = parse_args()

    filename_to_email: dict[str, str] = {}
    with args.audit_csv.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            output_json_path = (row.get("output_json_path") or "").strip()
            email = (row.get("email_address") or "").strip().casefold()
            if output_json_path and email:
                filename_to_email[Path(output_json_path).name] = email

    group_memberships = load_group_memberships(args.activity_group_csv)
    group_output_dirs = {
        group_name: args.group_output_root / group_name
        for group_name in sorted(group_memberships)
    }

    sample_filenames = {path.name for path in args.sample_source_dir.glob("*.json")}

    clear_json_files(args.all_minus_sas_output_dir)
    clear_json_files(args.sample_output_dir)
    for output_dir in group_output_dirs.values():
        clear_json_files(output_dir)

    promoted_counts: dict[str, int] = {"student_data_all_MINUS_SAS": 0}
    for group_name in group_output_dirs:
        promoted_counts[group_name] = 0
    sampled = 0

    for staged_path in sorted(args.staged_dir.glob("*.json")):
        filename = staged_path.name
        email = filename_to_email.get(filename, "")
        matched_groups = [group_name for group_name, emails in group_memberships.items() if email in emails]

        try:
            selected_group = choose_student_pool(matched_groups)
        except ValueError as error:
            raise ValueError(
                f"Roster membership is ambiguous for {filename}: email {email} appears in multiple output groups: {', '.join(sorted(matched_groups))}"
            ) from error

        if selected_group:
            student_pool = selected_group
            primary_output_dir = group_output_dirs[student_pool]
        else:
            student_pool = "student_data_all_MINUS_SAS"
            primary_output_dir = args.all_minus_sas_output_dir

        is_sample = filename in sample_filenames

        payload = json.loads(staged_path.read_text(encoding="utf-8"))
        payload.pop("B3_CONCEPT_NOTE", None)
        payload.pop("C3_CONCEPT_NOTE", None)
        payload.pop("D3_CONCEPT_NOTE", None)
        payload["STUDENT_POOL"] = student_pool
        payload["IS_SAMPLE"] = is_sample
        staged_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        primary_target_path = primary_output_dir / filename
        shutil.copy2(staged_path, primary_target_path)

        if is_sample:
            shutil.copy2(primary_target_path, args.sample_output_dir / filename)
            sampled += 1
        promoted_counts[student_pool] = promoted_counts.get(student_pool, 0) + 1

    print(f"Promoted {promoted_counts['student_data_all_MINUS_SAS']} JSON files to {args.all_minus_sas_output_dir}")
    print(f"Copied {sampled} sampled JSON files to {args.sample_output_dir}")
    for group_name, output_dir in group_output_dirs.items():
        print(f"Promoted {promoted_counts.get(group_name, 0)} JSON files to {output_dir}")

    schema = load_schema(DEFAULT_SCHEMA_PATH)
    audit_rows = load_audit_rows_from_csv(args.audit_csv, schema)
    student_pool_by_filename = load_student_pool_by_filename(
        [
            args.all_minus_sas_output_dir,
            *group_output_dirs.values(),
            args.sample_output_dir,
        ]
    )
    args.audit_csv.with_suffix(".md").write_text(
        build_audit_summary_report(schema, audit_rows, student_pool_by_filename=student_pool_by_filename),
        encoding="utf-8",
    )

    tagset_csv = args.audit_csv.with_name(args.audit_csv.stem + "_pps1_tagset_extraction.csv")
    if tagset_csv.exists():
        tagset_rows = load_pps1_text_development_rows_from_csv(tagset_csv, schema)
        tagset_csv.with_suffix(".md").write_text(
            build_pps1_text_development_summary_report(
                schema,
                tagset_rows,
                student_pool_by_filename=student_pool_by_filename,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())