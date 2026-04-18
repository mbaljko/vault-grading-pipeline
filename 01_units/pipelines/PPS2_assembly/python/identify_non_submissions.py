#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

from import_pps1_csv_to_json import (
    DEFAULT_SCHEMA_PATH,
    build_filename_base,
    load_participant_lookup,
    load_schema,
    normalize_participant_name,
    normalize_value,
    sanitize_filename,
)


DEFAULT_ACTIVITY_GROUP_CSV_PATH = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/LMS_exported_data/courseid_164725_participants_ACTIVITY_GROUP.csv"
)
DEFAULT_SUBMISSION_CSV_PATHS = (
    Path(
        "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/LMS_exported_data/PPS1 - Post-Practice Synthesis, Part 1 (accommodated)-10-records-20260417_2228-comma_separated.csv"
    ),
    Path(
        "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/LMS_exported_data/PPS1 - Post-Practice Synthesis, Part 1-411-records-20260416_2145-comma_separated_REMOVED_2_DUP_RECORDS_ACCOMMODATED.csv"
    ),
)
DEFAULT_NON_SUBMISSIONS_OUTPUT_DIR = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/input/NON_SUBMISSIONS"
)


@dataclass(frozen=True)
class EnrolledStudent:
    email_address: str
    participant_id: str
    given_name: str
    family_name: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Identify enrolled students with no PPS1 submission and emit placeholder JSON records.",
    )
    parser.add_argument("--schema-path", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--participants-csv-path", type=Path)
    parser.add_argument("--activity-group-csv-path", type=Path, default=DEFAULT_ACTIVITY_GROUP_CSV_PATH)
    parser.add_argument(
        "--submission-csv-path",
        type=Path,
        action="append",
        dest="submission_csv_paths",
        help="Submission CSV to scan for submitted students. May be repeated.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_NON_SUBMISSIONS_OUTPUT_DIR)
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--summary-report-path", type=Path)
    return parser.parse_args()


def clear_json_files(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for json_path in directory.glob("*.json"):
        json_path.unlink()


def build_blank_record(schema) -> dict[str, object]:
    return {key: "" for key in schema.all_record_defaults}


def resolve_roster_names(
    row: dict[str, str],
    participant_lookup,
) -> tuple[str, str]:
    email_value = normalize_value(row.get("Email address")).casefold()
    local_part = email_value.split("@", 1)[0] if email_value else ""
    participant = participant_lookup.get(email_value) or participant_lookup.get(local_part.casefold())

    given_name = normalize_participant_name(row.get("First name"))
    family_name = normalize_participant_name(row.get("Last name"))

    if participant is not None:
        if not given_name:
            given_name = participant.given_name
        if not family_name or family_name == ".":
            if participant.family_name:
                family_name = participant.family_name

    return given_name, family_name


def load_enrolled_students(activity_group_csv_path: Path, participant_lookup) -> dict[str, EnrolledStudent]:
    enrolled_by_email: dict[str, EnrolledStudent] = {}
    with activity_group_csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError(f"Activity group CSV has no header row: {activity_group_csv_path}")

        for row in reader:
            email_address = normalize_value(row.get("Email address")).casefold()
            if not email_address:
                continue

            given_name, family_name = resolve_roster_names(row, participant_lookup)
            participant_id = sanitize_filename(email_address.split("@", 1)[0], "unknown")
            enrolled_student = EnrolledStudent(
                email_address=email_address,
                participant_id=participant_id,
                given_name=given_name,
                family_name=family_name,
            )

            existing = enrolled_by_email.get(email_address)
            if existing is not None and existing != enrolled_student:
                raise ValueError(
                    "Conflicting enrolled-student rows for email "
                    f"{email_address}: {existing} vs {enrolled_student}"
                )
            enrolled_by_email[email_address] = enrolled_student

    return enrolled_by_email


def load_submitted_emails(submission_csv_paths: list[Path]) -> set[str]:
    submitted_emails: set[str] = set()
    for submission_csv_path in submission_csv_paths:
        with submission_csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames:
                raise ValueError(f"Submission CSV has no header row: {submission_csv_path}")

            for row in reader:
                email_address = normalize_value(row.get("Email address")).casefold()
                if email_address:
                    submitted_emails.add(email_address)
    return submitted_emails


def make_non_submission_filename(student: EnrolledStudent, used_names: set[str]) -> str:
    fallback_base_name = sanitize_filename(student.participant_id, "unknown")
    base_name = build_filename_base(student.given_name, student.family_name, fallback_base_name)

    candidate = base_name
    counter = 2
    while candidate in used_names:
        candidate = f"{base_name}_{counter}"
        counter += 1
    used_names.add(candidate)
    return f"{candidate}.json"


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["json_file", "email_address", "participant_id", "given_name", "family_name"],
        )
        writer.writeheader()
        writer.writerows(rows)


def build_summary_report(
    activity_group_csv_path: Path,
    submission_csv_paths: list[Path],
    enrolled_count: int,
    submitted_count: int,
    manifest_rows: list[dict[str, str]],
) -> str:
    lines = [
        "# Non-Submissions Summary",
        "",
        f"- Activity-group roster CSV: {activity_group_csv_path}",
        f"- Submission CSV count: {len(submission_csv_paths)}",
        f"- Enrolled students in roster: {enrolled_count}",
        f"- Students with submissions: {submitted_count}",
        f"- Identified non-submitters: {len(manifest_rows)}",
        "",
        "## Submission CSV Inputs",
        "",
    ]

    for submission_csv_path in submission_csv_paths:
        lines.append(f"- {submission_csv_path}")

    lines.extend(
        [
            "",
            "## Non-Submitters",
            "",
            "| JSON file | Email address | participant_id | Given name | Family name |",
            "| --- | --- | --- | --- | --- |",
        ]
    )

    if not manifest_rows:
        lines.append("| (none) |  |  |  |  |")
        return "\n".join(lines) + "\n"

    for row in manifest_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["json_file"],
                    row["email_address"],
                    row["participant_id"],
                    row["given_name"],
                    row["family_name"],
                ]
            )
            + " |"
        )

    return "\n".join(lines) + "\n"


def write_summary_report(
    path: Path,
    activity_group_csv_path: Path,
    submission_csv_paths: list[Path],
    enrolled_count: int,
    submitted_count: int,
    manifest_rows: list[dict[str, str]],
) -> None:
    path.write_text(
        build_summary_report(
            activity_group_csv_path=activity_group_csv_path,
            submission_csv_paths=submission_csv_paths,
            enrolled_count=enrolled_count,
            submitted_count=submitted_count,
            manifest_rows=manifest_rows,
        ),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    schema = load_schema(args.schema_path)
    participants_csv_path = args.participants_csv_path or schema.import_defaults.participants_csv_path
    submission_csv_paths = args.submission_csv_paths or list(DEFAULT_SUBMISSION_CSV_PATHS)
    manifest_path = args.manifest_path or (args.output_dir / "NON_SUBMISSIONS_manifest.csv")
    summary_report_path = args.summary_report_path or (args.output_dir / "NON_SUBMISSIONS_summary.md")

    participant_lookup = load_participant_lookup(participants_csv_path)
    enrolled_by_email = load_enrolled_students(args.activity_group_csv_path, participant_lookup)
    submitted_emails = load_submitted_emails(submission_csv_paths)
    non_submitters = [enrolled_by_email[email] for email in sorted(enrolled_by_email) if email not in submitted_emails]

    clear_json_files(args.output_dir)

    manifest_rows: list[dict[str, str]] = []
    used_names: set[str] = set()
    for student in non_submitters:
        record = build_blank_record(schema)
        record[schema.identity_fields.participant_id] = student.participant_id
        record[schema.identity_fields.given_name] = student.given_name
        record[schema.identity_fields.family_name] = student.family_name
        record["EMAIL_ADDRESS"] = student.email_address
        record["STUDENT_POOL"] = "NON_SUBMISSIONS"
        record["IS_SAMPLE"] = False
        record["NON_SUBMISSION"] = True
        record["NON_SUBMISSION_REASON"] = "No PPS1 submission found in the configured LMS export CSV inputs"

        file_name = make_non_submission_filename(student, used_names)
        output_path = args.output_dir / file_name
        output_path.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        manifest_rows.append(
            {
                "json_file": file_name,
                "email_address": student.email_address,
                "participant_id": student.participant_id,
                "given_name": student.given_name,
                "family_name": student.family_name,
            }
        )

    write_manifest(manifest_path, manifest_rows)
    write_summary_report(
        summary_report_path,
        activity_group_csv_path=args.activity_group_csv_path,
        submission_csv_paths=submission_csv_paths,
        enrolled_count=len(enrolled_by_email),
        submitted_count=len(submitted_emails),
        manifest_rows=manifest_rows,
    )

    print(f"Enrolled students in activity-group roster: {len(enrolled_by_email)}")
    print(f"Students with submissions across {len(submission_csv_paths)} CSV files: {len(submitted_emails)}")
    print(f"Identified non-submitters: {len(non_submitters)}")
    print(f"Wrote placeholder JSON files to {args.output_dir}")
    print(f"Wrote manifest CSV to {manifest_path}")
    print(f"Wrote summary report to {summary_report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())