#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from import_pps1_csv_to_json import DEFAULT_SCHEMA_PATH, load_audit_rows_from_csv, load_schema, build_audit_summary_report


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
        "--all-minus-sas-output-dir",
        type=Path,
        required=True,
        help="Final destination directory for non-SAS JSON files.",
    )
    parser.add_argument("--sample-output-dir", type=Path, required=True, help="Final destination directory for sampled JSON files.")
    parser.add_argument("--section-m-output-dir", type=Path, required=True, help="Final destination directory for Section M JSON files.")
    parser.add_argument("--section-o-output-dir", type=Path, required=True, help="Final destination directory for Section O JSON files.")
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

    section_m_emails: set[str] = set()
    section_o_emails: set[str] = set()
    with args.activity_group_csv.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            email = (row.get("Email address") or "").strip().casefold()
            if not email:
                continue
            if (row.get("student_data_SAS_SecM") or "").strip():
                section_m_emails.add(email)
            if (row.get("student_data_SAS_SecO") or "").strip():
                section_o_emails.add(email)

    sample_filenames = {path.name for path in args.sample_source_dir.glob("*.json")}

    clear_json_files(args.all_minus_sas_output_dir)
    clear_json_files(args.sample_output_dir)
    clear_json_files(args.section_m_output_dir)
    clear_json_files(args.section_o_output_dir)

    promoted_all_minus_sas = 0
    sampled = 0
    promoted_sec_m = 0
    promoted_sec_o = 0

    for staged_path in sorted(args.staged_dir.glob("*.json")):
        filename = staged_path.name
        email = filename_to_email.get(filename, "")
        in_section_m = email in section_m_emails
        in_section_o = email in section_o_emails

        if in_section_m and in_section_o:
            raise ValueError(f"Roster membership is ambiguous for {filename}: email {email} appears in both SAS sections")

        if in_section_m:
            student_pool = "student_data_SAS_SecM"
            primary_output_dir = args.section_m_output_dir
        elif in_section_o:
            student_pool = "student_data_SAS_SecO"
            primary_output_dir = args.section_o_output_dir
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
        shutil.move(str(staged_path), primary_target_path)

        if is_sample:
            shutil.copy2(primary_target_path, args.sample_output_dir / filename)
            sampled += 1
        if student_pool == "student_data_SAS_SecM":
            promoted_sec_m += 1
        elif student_pool == "student_data_SAS_SecO":
            promoted_sec_o += 1
        else:
            promoted_all_minus_sas += 1

    print(f"Promoted {promoted_all_minus_sas} JSON files to {args.all_minus_sas_output_dir}")
    print(f"Copied {sampled} sampled JSON files to {args.sample_output_dir}")
    print(f"Promoted {promoted_sec_m} Section M JSON files to {args.section_m_output_dir}")
    print(f"Promoted {promoted_sec_o} Section O JSON files to {args.section_o_output_dir}")

    schema = load_schema(DEFAULT_SCHEMA_PATH)
    audit_rows = load_audit_rows_from_csv(args.audit_csv, schema)
    student_pool_by_filename = load_student_pool_by_filename(
        [
            args.all_minus_sas_output_dir,
            args.section_m_output_dir,
            args.section_o_output_dir,
            args.sample_output_dir,
        ]
    )
    args.audit_csv.with_suffix(".md").write_text(
        build_audit_summary_report(schema, audit_rows, student_pool_by_filename=student_pool_by_filename),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())