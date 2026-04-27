from __future__ import annotations

import csv
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path


NOT_YET_COMPONENTISED = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/AP1-umbrella/AP1B/01_pipelines/pl1A_canonical_population/02_runs/01_cleaning/AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised.csv"
)
MASSAGED_PREV = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/AP1-umbrella/AP1B/01_pipelines/pl1A_canonical_population/02_runs/01_cleaning/AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised_massaged-prev.csv"
)
MASSAGED_OUTPUT = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/AP1-umbrella/AP1B/01_pipelines/pl1A_canonical_population/02_runs/01_cleaning/AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised_massaged.csv"
)

SUBMISSION_LINE_RE = re.compile(r"^\+\+\+\s*submission_id\s*=\s*\d+\s*$", re.IGNORECASE)
PLUS_LINE_RE = re.compile(r"^\+\+\+\s*$")
SUBMISSION_INLINE_RE = re.compile(r"submission_id\s*=\s*\d+", re.IGNORECASE)


def normalize_response_text(text: str) -> str:
    cleaned_lines: list[str] = []
    normalized_newlines = text.replace("\r\n", "\n").replace("\r", "\n")
    for raw_line in normalized_newlines.split("\n"):
        stripped = raw_line.strip()
        if SUBMISSION_LINE_RE.match(stripped):
            continue
        if PLUS_LINE_RE.match(stripped):
            continue
        stripped = SUBMISSION_INLINE_RE.sub("", stripped)
        if stripped:
            cleaned_lines.append(stripped)
    result = re.sub(r"\s+", " ", " ".join(cleaned_lines)).strip().lower()
    return result


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"No CSV header found in {path}")
        rows = [dict(row) for row in reader]
        return list(reader.fieldnames), rows


def canonical_key(row: dict[str, str], fieldnames: list[str]) -> tuple[str, ...]:
    key_parts: list[str] = []
    for field in fieldnames:
        value = row.get(field, "") or ""
        if field == "submission_id":
            key_parts.append("<ignored>")
        elif field == "response_text":
            key_parts.append(normalize_response_text(value))
        else:
            key_parts.append(value.strip())
    return tuple(key_parts)


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    source_fields, source_rows = read_rows(NOT_YET_COMPONENTISED)
    massaged_fields, massaged_rows = read_rows(MASSAGED_PREV)

    if source_fields != massaged_fields:
        raise ValueError("Input CSV schemas do not match")

    massaged_counts_by_key: dict[tuple[str, ...], int] = defaultdict(int)
    for row in massaged_rows:
        massaged_counts_by_key[canonical_key(row, massaged_fields)] += 1

    matching_source_rows: list[dict[str, str]] = []
    unmatched_source_rows: list[dict[str, str]] = []
    for row in source_rows:
        key = canonical_key(row, source_fields)
        remaining = massaged_counts_by_key.get(key, 0)
        if remaining <= 0:
            unmatched_source_rows.append(row)
            continue
        massaged_counts_by_key[key] = remaining - 1
        matching_source_rows.append(row)

    unmatched_massaged_rows: list[dict[str, str]] = []
    for row in massaged_rows:
        key = canonical_key(row, massaged_fields)
        remaining = massaged_counts_by_key.get(key, 0)
        if remaining > 0:
            unmatched_massaged_rows.append(row)
            massaged_counts_by_key[key] = remaining - 1

    best_pairs: list[dict[str, str]] = []
    if unmatched_source_rows and unmatched_massaged_rows:
        used_massaged: set[int] = set()
        for source_row in unmatched_source_rows:
            best_sim = -1
            best_idx = -1
            source_norm = normalize_response_text(source_row.get("response_text", "") or "")
            for m_idx, massaged_row in enumerate(unmatched_massaged_rows):
                if m_idx in used_massaged:
                    continue
                massaged_norm = normalize_response_text(massaged_row.get("response_text", "") or "")
                sim = SequenceMatcher(None, source_norm, massaged_norm).ratio()
                if sim > best_sim:
                    best_sim = sim
                    best_idx = m_idx
            if best_idx >= 0:
                used_massaged.add(best_idx)
                output_row = dict(unmatched_massaged_rows[best_idx])
                output_row["submission_id"] = (source_row.get("submission_id", "") or "").strip()
                best_pairs.append(output_row)

    all_output_rows = matching_source_rows + best_pairs
    write_rows(MASSAGED_OUTPUT, source_fields, all_output_rows)

    print(f"Source rows read: {len(source_rows)}")
    print(f"Massaged-prev rows read: {len(massaged_rows)}")
    print(f"Exact matches written: {len(matching_source_rows)}")
    print(f"Unmatched source rows: {len(unmatched_source_rows)}")
    print(f"Unmatched massaged rows: {len(unmatched_massaged_rows)}")
    print(f"Best-similarity pairs added: {len(best_pairs)}")
    print(f"Total rows written: {len(all_output_rows)}")
    print(f"Output written to: {MASSAGED_OUTPUT}")


if __name__ == "__main__":
    main()
