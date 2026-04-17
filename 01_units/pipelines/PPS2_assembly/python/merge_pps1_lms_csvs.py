#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def normalize_value(value: str | None) -> str:
    return (value or "").strip()


def split_user_name(user_value: str, username_value: str) -> tuple[str, str]:
    parts = [part for part in user_value.split() if part]
    if not parts:
        fallback = username_value.strip() or "Unknown"
        return "", fallback
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def load_participant_lookup(participants_csv_path: Path) -> dict[str, tuple[str, str]]:
    lookup: dict[str, tuple[str, str]] = {}
    with participants_csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise SystemExit(f"Participants CSV has no header row: {participants_csv_path}")

        for row in reader:
            email = normalize_value(row.get("Email address")).casefold()
            if not email:
                continue

            identity = (
                normalize_value(row.get("First name")),
                normalize_value(row.get("Last name")),
            )
            lookup[email] = identity
            local_part = email.split("@", 1)[0]
            if local_part:
                lookup.setdefault(local_part.casefold(), identity)
    return lookup


def resolve_student_key(row: dict[str, str], participant_lookup: dict[str, tuple[str, str]]) -> tuple[str, str]:
    user_value = normalize_value(row.get("User"))
    username_value = normalize_value(row.get("Username"))
    email_value = normalize_value(row.get("Email address")).casefold()

    participant = participant_lookup.get(email_value) or participant_lookup.get(username_value.casefold())
    if participant is not None:
        given_name, family_name = participant
        display_name = " ".join(part for part in (given_name, family_name) if part) or username_value or email_value or user_value
        return f"roster:{given_name.casefold()}|{family_name.casefold()}", display_name

    fallback_given_name, fallback_family_name = split_user_name(user_value, username_value)
    if email_value:
        return f"email:{email_value}", email_value
    if username_value:
        return f"username:{username_value.casefold()}", username_value
    fallback_display = " ".join(part for part in (fallback_given_name, fallback_family_name) if part) or user_value or "unknown"
    return f"user:{fallback_display.casefold()}", fallback_display


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge PPS1 LMS CSV exports and abort on duplicate student entries.",
    )
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--participants-csv-path", type=Path, required=True)
    parser.add_argument("sources", nargs="+", type=Path)
    return parser.parse_args()


def normalized(value: str | None) -> str:
    return (value or "").strip().casefold()


def main() -> int:
    args = parse_args()
    if not args.sources:
        raise SystemExit("At least one source CSV is required")

    participant_lookup = load_participant_lookup(args.participants_csv_path)
    fieldnames: list[str] | None = None
    rows: list[dict[str, str]] = []
    seen_student: dict[str, str] = {}
    duplicate_messages: list[str] = []

    for source_path in args.sources:
        with source_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames:
                raise SystemExit(f"CSV file has no header row: {source_path}")

            current_fieldnames = list(reader.fieldnames)
            if fieldnames is None:
                fieldnames = current_fieldnames
            elif current_fieldnames != fieldnames:
                raise SystemExit(
                    "CSV headers do not match across PPS1 sources:\n"
                    f"  first: {args.sources[0]}\n"
                    f"  mismatched: {source_path}"
                )

            for row_index, row in enumerate(reader, start=2):
                user = normalize_value(row.get("User"))
                location = f"{source_path.name}:row {row_index}"
                student_key, student_label = resolve_student_key(row, participant_lookup)

                previous = seen_student.get(student_key)
                if previous:
                    duplicate_messages.append(
                        f"duplicate student {student_label!r}: {previous} and {location} (User={user!r})"
                    )
                else:
                    seen_student[student_key] = location

                rows.append(row)

    if duplicate_messages:
        raise SystemExit("Duplicate PPS1 LMS entries detected:\n- " + "\n- ".join(duplicate_messages))

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    with args.output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())