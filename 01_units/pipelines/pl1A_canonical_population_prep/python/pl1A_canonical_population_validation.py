#!/usr/bin/env python3

"""Build the canonical-population CSV from LMS-export and grading worksheet inputs.

This ports the validation and cleaning logic from the Power Query pipeline into Python.
It reads the canonical-population / LMS-export CSV plus the grading worksheet CSV,
matches LMS rows to the grading worksheet by normalized name, expands response columns
into a long canonical structure, and writes the canonical-population CSV used by later
pipeline steps.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


NON_BREAKING_SPACE = chr(160)
LEADING_ALLOWED_RE = re.compile(r"[a-z0-9]")
TRAILING_DIGITS_RE = re.compile(r"(\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read the canonical-population CSV and grading worksheet CSV, join them by "
            "normalized name, and write the canonical-population CSV."
        ),
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        required=True,
        help="Path to the canonical-population CSV file.",
    )
    parser.add_argument(
        "--gradework-sheet-input-path",
        type=Path,
        required=True,
        help="Path to the grading worksheet CSV file.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        help=(
            "Destination CSV file. If omitted, the script writes next to --input-path using "
            "the suffix '-canonical-population'."
        ),
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


def collapse_spaces(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = value
    for _ in range(10):
        collapsed = collapsed.replace("  ", " ")
    return collapsed


def strip_leading_junk(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    for index, character in enumerate(stripped.lower()):
        if LEADING_ALLOWED_RE.fullmatch(character):
            return stripped[index:]
    return ""


def extract_trailing_digits(value: str | None) -> str | None:
    if value is None:
        return None
    match = TRAILING_DIGITS_RE.search(value.strip())
    if match is None:
        return None
    return match.group(1)


def norm_name_key(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace(NON_BREAKING_SPACE, " ")
    text = " ".join(text.splitlines())
    text = collapse_spaces(text.strip())
    if text is None:
        return None
    text = strip_leading_junk(text.lower())
    if text is None:
        return None
    return text or None


def build_gw_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    keyed_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = norm_name_key(row.get("Full name"))
        if key is not None:
            keyed_rows[key].append(row)
    return keyed_rows


def build_output_rows(
    raw_rows: list[dict[str, str]],
    gw_index: dict[str, list[dict[str, str]]],
) -> list[dict[str, str | int | None]]:
    output_rows: list[dict[str, str | int | None]] = []

    for row in raw_rows:
        key_name = norm_name_key(row.get("User"))
        gw_matches = gw_index.get(key_name or "", []) if key_name is not None else []
        gw_name_count = len(gw_matches) or None

        resolved_row: dict[str, str] | None = gw_matches[0] if len(gw_matches) == 1 else None
        gw_identifier = resolved_row.get("Identifier", "") if resolved_row else ""
        gw_full_name = resolved_row.get("Full name", "") if resolved_row else ""
        submission_id = extract_trailing_digits(gw_identifier)

        if gw_name_count is None:
            join_status = "no_match"
        elif gw_name_count == 1 and submission_id is not None:
            join_status = "matched_unique"
        else:
            join_status = "excluded_ambiguous"

        output_rows.append(
            {
                "User": row.get("User", ""),
                "Username": row.get("Username", ""),
                "__key_name": key_name,
                "GW.Full name": gw_full_name,
                "GW.Identifier": gw_identifier,
                "submission_id": submission_id,
                "__join_status": join_status,
                "__gw_name_count": gw_name_count,
            }
        )

    return output_rows


def normalise_html_quotes(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value
    if len(normalized) >= 2 and normalized.startswith('"') and normalized.endswith('"'):
        normalized = normalized[1:-1]
    return normalized.replace('""', '"')


def sanitise_mojibake(value: str | None) -> str | None:
    if value is None:
        return None
    replacements = [
        ("¬†", " "),
        ("‚Äî", "—"),
        ("‚Äú", "“"),
        ("‚Äù", "”"),
        ("‚Äò", "‘"),
        ("‚Äô", "’"),
        (NON_BREAKING_SPACE, " "),
    ]
    result = value
    for source, target in replacements:
        result = result.replace(source, target)
    return result.strip()


def strip_tags(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"<[^>]*>", "", value).strip()


def strip_html_fast_plain(raw: Any) -> str | None:
    if raw is None:
        return None
    text = normalise_html_quotes(str(raw))
    text = sanitise_mojibake(text)
    if text is None:
        return None
    for token in ["<br />", "<br/>", "<br>", "</p>"]:
        text = text.replace(token, "\n")
    text = strip_tags(text)
    return sanitise_mojibake(text)


def remove_whitespace_and_zero_width(value: str | None) -> str | None:
    if value is None:
        return None
    characters_to_remove = {
        " ",
        "\t",
        "\n",
        "\r",
        NON_BREAKING_SPACE,
        chr(65279),
        chr(8203),
        chr(8204),
        chr(8205),
    }
    return "".join(character for character in value if character not in characters_to_remove)


def is_effectively_blank(value: str | None) -> bool:
    if value is None:
        return True
    return len(remove_whitespace_and_zero_width(value) or "") == 0


def classify_presence(raw: Any) -> tuple[str | None, str]:
    raw_text = None if raw is None else str(raw)
    raw_is_null = raw is None
    raw_is_empty = raw_text == ""
    raw_is_blanks_only = raw_text not in (None, "") and is_effectively_blank(raw_text)

    cleaned_plain = strip_html_fast_plain(raw)
    cleaned_is_blank = is_effectively_blank(cleaned_plain)

    if raw_is_null:
        status = "NULL"
    elif raw_is_empty:
        status = "EMPTY"
    elif raw_is_blanks_only:
        status = "BLANKS"
    elif cleaned_is_blank:
        status = "EMPTY_AFTER_CLEANING"
    else:
        status = "NONEMPTY"

    return cleaned_plain, status


def word_count_payload(value: str | None) -> int:
    if value is None:
        return 0
    normalized = value.replace("\n", " ").replace("\r", " ").strip()
    if not normalized:
        return 0
    return len([part for part in normalized.split(" ") if part])


def build_validation_map(
    validation_rows: list[dict[str, str | int | None]],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in validation_rows:
        if row.get("__join_status") != "matched_unique":
            continue
        user = str(row.get("User", "") or "")
        submission_id = str(row.get("submission_id", "") or "")
        if user and submission_id:
            mapping[user] = submission_id
    return mapping


def infer_response_columns(raw_rows: list[dict[str, str]]) -> list[str]:
    if not raw_rows:
        return []
    all_columns = list(raw_rows[0].keys())
    if "Tags" not in all_columns:
        raise ValueError("Expected column 'Tags' not found. Cannot infer response columns.")
    tags_pos = all_columns.index("Tags")
    return all_columns[:tags_pos]


def build_response_payload(response_presence: str, response_text_clean: str | None) -> str:
    if response_presence == "NULL":
        return ""
    if response_presence == "EMPTY":
        return "<<EMPTY>>"
    if response_presence == "BLANKS":
        return "<<BLANKS>>"
    if response_presence == "EMPTY_AFTER_CLEANING":
        return "<<EMPTY_AFTER_CLEANING>>"
    return response_text_clean or ""


def wrap_response_text(payload: str, submission_id: str) -> str:
    return f"+++submission_id={submission_id}\n+++\n{payload}\n+++\n"


def build_canonical_population_rows(
    raw_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str | int | None]],
) -> list[dict[str, str | int]]:
    validation_map = build_validation_map(validation_rows)
    response_columns = infer_response_columns(raw_rows)
    canonical_rows: list[dict[str, str | int]] = []

    for raw_row in raw_rows:
        user = raw_row.get("User", "")
        submission_id = validation_map.get(user)
        if submission_id is None:
            continue

        for component_id in response_columns:
            response_text_clean, response_presence = classify_presence(raw_row.get(component_id))
            response_payload = build_response_payload(response_presence, response_text_clean)
            canonical_rows.append(
                {
                    "submission_id": submission_id,
                    "component_id": component_id,
                    "response_presence": response_presence,
                    "response_text": wrap_response_text(response_payload, submission_id),
                }
            )

    return canonical_rows


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}-canonical-population.csv")


def write_output_rows(output_path: Path, rows: list[dict[str, str | int]]) -> None:
    fieldnames = [
        "submission_id",
        "component_id",
        "response_presence",
        "response_text",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def print_summary(
    validation_rows: list[dict[str, str | int | None]],
    canonical_rows: list[dict[str, str | int]],
    output_path: Path,
) -> None:
    status_counts = Counter(str(row.get("__join_status", "")) for row in validation_rows)
    print(f"[summary] validation_rows={len(validation_rows)}")
    for status, count in sorted(status_counts.items()):
        print(f"[summary] join_status[{status}]={count}")
    print(f"[summary] canonical_population_rows={len(canonical_rows)}")
    print(f"[summary] output_path={output_path}")


def main() -> int:
    args = parse_args()
    input_path = args.input_path.resolve()
    gradework_sheet_input_path = args.gradework_sheet_input_path.resolve()
    output_path = args.output_path.resolve() if args.output_path else default_output_path(input_path)

    raw_rows = load_csv_rows(input_path)
    gw_rows = load_csv_rows(gradework_sheet_input_path)
    gw_index = build_gw_index(gw_rows)
    validation_rows = build_output_rows(raw_rows, gw_index)
    canonical_rows = build_canonical_population_rows(raw_rows, validation_rows)
    write_output_rows(output_path, canonical_rows)

    print(f"[canonical_population] path={input_path}")
    print(f"[gradework_sheet] path={gradework_sheet_input_path}")
    print(f"[output] path={output_path}")
    print_summary(validation_rows, canonical_rows, output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())