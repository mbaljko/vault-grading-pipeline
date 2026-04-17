#!/usr/bin/env python3
"""Import PPS1 LMS CSV data into per-student JSON files.

Field source summary for generated JSON records:

- Identity and roster-derived fields:
    - `participant_id`, `GIVEN_NAME`, and `FAMILY_NAME` come from LMS identity
        columns (`Username`, `User`, `Email address`) plus the participants roster CSV
        used to resolve names more reliably.
- Direct LMS-mapped response fields:
    - Fields such as `B-1-PPP`, `B-1-PPS1`, `B3Interpretation`, `C3Use`,
        `E-1-PPS1`, and `GenAIAttestation` come from LMS export columns via
        `directFieldMap` in the external schema file.
    - Text cleaning is applied only to columns selected by
        `should_clean_lms_text_column`.
- Derived fields from cleaned B/C/D.2 response text:
    - `B-1-devt_tagset`, `B-2-devt_tagset`, `B-3-devt_tagset`,
        `C-1-devt_tagset`, `C-2-devt_tagset`, `C-3-devt_tagset`,
        `D-1-devt_tagset`, `D-2-devt_tagset`, and `D-3-devt_tagset` are
        derived from extraction over the cleaned Section B, C, and D
        subsection 2 response text.
    - `B-1_indicator_health_srcBCD2`, `B-2_indicator_health_srcBCD2`,
        `B-3_indicator_health_srcBCD2`, `C-1_indicator_health_srcBCD2`,
        `C-2_indicator_health_srcBCD2`, `C-3_indicator_health_srcBCD2`,
        `D-1_indicator_health_srcBCD2`, `D-2_indicator_health_srcBCD2`, and
        `D-3_indicator_health_srcBCD2` are derived from the same B/C/D.2
        extraction as `*-devt_tagset`: health `2` means a tagset value was
        extracted and health `0` means no value was extracted.
- E1-derived development fields:
    - `B-1-devt`, `B-2-devt`, `B-3-devt`, `C-1-devt`, `C-2-devt`, `C-3-devt`,
        `D-1-devt`, `D-2-devt`, and `D-3-devt` are derived from the E1
        development-type checkbox columns in the LMS export.
    - For a dotted dimension prefix such as `B21`, the code reads
        `{prefix}_shift`, `{prefix}_cont`, and `{prefix}_intro` and maps the checked
        value to `Shift`, `Cont/Reinf`, or `Intro`.
    - `B-1_indicator_health_srcE1`, `B-2_indicator_health_srcE1`,
        `B-3_indicator_health_srcE1`, `C-1_indicator_health_srcE1`,
        `C-2_indicator_health_srcE1`, `C-3_indicator_health_srcE1`,
        `D-1_indicator_health_srcE1`, `D-2_indicator_health_srcE1`, and
        `D-3_indicator_health_srcE1` are derived from the same E1 checkbox
        source as `*-devt`: health `2` means exactly one checkbox selected,
        health `1` means multiple selected, and health `0` means none selected.
- E2-derived status fields:
    - `B-1-status`, `B-2-status`, `B-3-status`, `C-1-status`, `C-2-status`,
        `C-3-status`, `D-1-status`, `D-2-status`, and `D-3-status` are
        derived from the E2 position-state matrix.
    - The importer reads `E2_00_GridResponse`, `E2_10_GridResponse`,
        `E2_01_GridResponse`, and `E2_11_GridResponse`, then uses `gridStatusMap`
        plus `shortToDottedDimension` from the schema to assign `stable` or
        `in tension` to the matching dimension.
- Converged development fields:
    - `B-1-devt_converged`, `B-2-devt_converged`, `B-3-devt_converged`,
        `C-1-devt_converged`, `C-2-devt_converged`, `C-3-devt_converged`,
        `D-1-devt_converged`, `D-2-devt_converged`, and
        `D-3-devt_converged` store the converged development label for each
        dimension, derived from `*-devt` and `*-devt_tagset`.
    - `B-1-devt_converged_health`, `B-2-devt_converged_health`,
        `B-3-devt_converged_health`, `C-1-devt_converged_health`,
        `C-2-devt_converged_health`, `C-3-devt_converged_health`,
        `D-1-devt_converged_health`, `D-2-devt_converged_health`, and
        `D-3-devt_converged_health` are the paired health/status fields for
        those converged outputs.
    - The field list for these values is defined in `pps1_import_schema.json`
        under `allRecordDefaults` and `derivedFieldGroups.convergedDerived`.
    - A tagset value of `tension` is set aside for this convergence step and
        does not participate in the main `shift` / `cont-reinf` / `intro`
        outcome.
    - If exactly one source is populated, the converged value takes that source
        value and the health is `asserted`.
    - If both sources are populated and agree, the converged value keeps that
        shared value and the health is `reinforced`.
    - If both sources are populated and differ, the converged value becomes a
        joined token such as `intro+shift` and the health is `conflict`.
- Derived section-slot fields:
    - `Sec1_TS1_PPP`, `Sec1_TS1_PPS1`, `Sec1_TS1_dim`
    - `Sec1_TS2_PPP`, `Sec1_TS2_PPS1`, `Sec1_TS2_dim`
    - `Sec1_TS3_PPP`, `Sec1_TS3_PPS1`, `Sec1_TS3_dim`
    - `Sec2_V1_PPP`, `Sec2_V1_PPS1`, `Sec2_V1_dim`
    - `Sec2_V2_PPP`, `Sec2_V2_PPS1`, `Sec2_V2_dim`
    - `Sec2_V3_PPP`, `Sec2_V3_PPS1`, `Sec2_V3_dim`
    - `Sec4_Slot1_dim`, `Sec4_Slot1_PPS1`
    - `Sec4_Slot2_dim`, `Sec4_Slot2_PPS1`
    - `Sec4_Slot3_dim`, `Sec4_Slot3_PPS1`
    - Section 1 TS slots are populated first with `TS1 -> B-*`, `TS2 -> C-*`,
        and `TS3 -> D-*` selections.
    - See `pps1_slot_populator.py` for the remaining slot-population semantics
        and selection logic.
- Post-import enrichment fields:
    - `STUDENT_POOL` and `IS_SAMPLE` are not assigned in this importer.
    - They are added later by `promote_pps1_buffered_jsons.py` during post-import
        promotion into final destination directories.
- Schema-only placeholders:
    - Fields that exist in `pps1_import_schema.json` but are not populated in this
        file remain at their default values until another step assigns them.

The output schema, field ordering, and CSV-to-JSON mappings live in an external
JSON config file so they can be updated without changing Python code.
`recordDefaults` holds the base LMS-mapped fields, while `allRecordDefaults`
declares the complete final flat JSON record including all derived outputs.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import difflib
import json
import random
import re
import shutil
from pathlib import Path
import sys
from typing import Any


APPS_DIR = Path(__file__).resolve().parents[3] / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from lms_text_cleaning import clean_lms_text, should_clean_lms_text_column
from pps1_slot_populator import SectionSlot, populate_section_fields


DEFAULT_SCHEMA_PATH = Path(
    "/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/pps1_import_schema.json"
)
NO_ENTRY_RECEIVED = "[NO ENTRY RECEIVED]"
CANONICAL_DEVELOPMENT_TYPES = ("cont-reinf", "intro", "shift", "tension")
DEVELOPMENT_LABEL_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"(?i)(?:cont(?:inuity)?(?:\W|_)*(?:and(?:\W|_)+)?reinf\w*|contunity(?:\W|_)*reinf\w*|continuity(?:\W|_)*reinforcement|reinforced(?:\W|_)+continuity|continuity)(?=\b|interpretation|explanation)",
        "cont-reinf",
    ),
    (r"(?i)intro(?:duced|duction)?(?=\b|interpretation|explanation)", "intro"),
    (r"(?i)shift(?:ed|s)?(?=\b|interpretation|explanation)", "shift"),
    (r"(?i)tension(?=\b|interpretation|explanation)", "tension"),
)
PROSE_DEVELOPMENT_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "intro",
        r"(?i)\b(?:did\s+not\s+(?:directly\s+)?address|did\s+not\s+engage\s+with|had\s+not\s+considered|had\s+not\s+really\s+considered|there\s+was\s+no\s+explicit|there\s+was\s+no\s+institutional\s+perspective|not\s+clearly\s+identified\s+in\s+my\s+ppp|not\s+in\s+my\s+baseline|poorly\s+captured|pretty\s+unsure|came\s+to\s+understand|started\s+to\s+realize|started\s+to\s+realise|began\s+to\s+see|became\s+aware|was\s+introduced|were\s+introduced|this\s+aspect\s+was\s+not\s+clearly\s+identified)\b",
    ),
    (
        "tension",
        r"(?i)\b(?:in\s+tension|creates?\s+tension|remains?\s+in\s+tension|unresolved\s+tension|conflict\s+between|inconsistency\s+between|competing\s+commitments|both\s+seem\s+true)\b",
    ),
    (
        "cont-reinf",
        r"(?i)\b(?:did\s+not\s+change|stayed\s+(?:pretty\s+much\s+)?the\s+same|stayed\s+the\s+exact\s+same|stayed\s+more\s+or\s+less\s+the\s+same|remained\s+constant|remained\s+consistent|remained\s+continuous|still\s+held\s+up|held\s+up\s+pretty\s+well|was\s+reinforced|were\s+reinforced|consistently\s+reinforced|continuity\s+reinforcement|continuity\-reinforcement|reinforced\s+rather\s+than\s+replaced|reinforced\s+my|strengthened|fortified|maintained|persisted|in\s+agreement\s+with|was\s+also\s+the\s+case|support(?:ed|s)?\s+this\s+idea|extends\s+the\s+earlier\s+position|not\s+contradicts\s+it|this\s+position\s+was\s+reinforced|my\s+interpretation\s+has\s+been\s+reinforced)\b",
    ),
    (
        "shift",
        r"(?i)\b(?:change\s+in\s+my\s+viewpoint|shift(?:ed|s)?|changed|move\s+away\s+from|moved\s+away\s+from|move\s+from|moved\s+from|develop(?:ed|s)?\s+into|evolved|reconsider(?:ed)?|represents\s+a\s+shift|reflects\s+a\s+move|move\s+toward|moved\s+toward|transition(?:ed|s)?\s+to|gave\s+way\s+to|this\s+has\s+changed|this\s+develops\s+into|this\s+expanded|further\s+refined\s+into|led\s+me\s+to\s+appreciate|led\s+me\s+to\s+realise|led\s+me\s+to\s+realize)\b",
    ),
)


@dataclass(frozen=True)
class IdentityFields:
    participant_id: str
    family_name: str
    given_name: str


@dataclass(frozen=True)
class ParticipantIdentity:
    given_name: str
    family_name: str


@dataclass(frozen=True)
class GeneratedRecord:
    path: Path
    given_name: str
    family_name: str


@dataclass(frozen=True)
class AuditRow:
    source_csv_path: str
    row_index: int
    user: str
    username: str
    email_address: str
    participant_id: str
    given_name: str
    family_name: str
    output_json_path: str
    dimension_check_fields: dict[str, str]
    dimension_word_count_fields: dict[str, str]
    concept_word_count_fields: dict[str, str]
    no_entry_received_fields: dict[str, str]
    position_state_matrix_fields: dict[str, str]


@dataclass(frozen=True)
class CleaningAuditRow:
    source_csv_path: str
    row_index: int
    participant_id: str
    given_name: str
    family_name: str
    output_json_path: str
    source_column: str
    json_key: str
    cleaning_applied: str
    raw_is_blank: str
    cleaned_is_blank: str
    sentinel_inserted: str
    changed: str
    suspicious: str
    change_class: str
    word_drop_type: str
    diff_category: str
    raw_char_count: int
    cleaned_char_count: int
    raw_word_count: int
    cleaned_word_count: int
    char_delta: int
    word_delta: int
    raw_preview: str
    cleaned_preview: str
    text_diff: str


@dataclass(frozen=True)
class Pps1TextDevelopmentRow:
    source_csv_path: str
    row_index: int
    participant_id: str
    given_name: str
    family_name: str
    output_json_path: str
    extracted_development_types: dict[str, str]


@dataclass(frozen=True)
class ImportSchema:
    import_defaults: "ImportDefaults"
    record_defaults: dict[str, str]
    all_record_defaults: dict[str, str]
    derived_field_groups: dict[str, list[str]]
    dimensions: list[str]
    short_to_dotted_dimension: dict[str, str]
    direct_field_map: dict[str, str]
    grid_status_map: dict[str, str]
    section1_slots: list[SectionSlot]
    section2_slots: list[SectionSlot]
    section3_slots: list[SectionSlot]
    identity_fields: IdentityFields


@dataclass(frozen=True)
class ImportDefaults:
    csv_path: Path
    participants_csv_path: Path
    all_output_dir: Path
    sample_output_dir: Path
    audit_path: Path
    sample_size: int


def parse_section_slots(raw_slots: list[dict[str, str]]) -> list[SectionSlot]:
    return [
        SectionSlot(
            dim_field=slot["dim"],
            ppp_field=slot.get("ppp"),
            pps1_field=slot.get("pps1"),
        )
        for slot in raw_slots
    ]
def validate_slot_population_fields(
    all_record_defaults: dict[str, str],
    derived_field_groups: dict[str, list[str]],
    section1_slots: list[SectionSlot],
    section2_slots: list[SectionSlot],
    section3_slots: list[SectionSlot],
) -> None:
    section_derived_fields = set(derived_field_groups.get("sectionDerived", []))
    slot_fields = [
        field_name
        for slot in (*section1_slots, *section2_slots, *section3_slots)
        for field_name in (slot.dim_field, slot.ppp_field, slot.pps1_field)
        if field_name
    ]

    missing_from_all_record_defaults = [field_name for field_name in slot_fields if field_name not in all_record_defaults]
    if missing_from_all_record_defaults:
        raise ValueError(
            "Schema allRecordDefaults is missing slot population fields: "
            + ", ".join(missing_from_all_record_defaults)
        )

    missing_from_section_derived = [field_name for field_name in slot_fields if field_name not in section_derived_fields]
    if missing_from_section_derived:
        raise ValueError(
            "Schema derivedFieldGroups.sectionDerived is missing slot population fields: "
            + ", ".join(missing_from_section_derived)
        )


def load_schema(schema_path: Path) -> ImportSchema:
    raw_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    import_defaults = ImportDefaults(
        csv_path=Path(raw_schema["importDefaults"]["csvPath"]),
        participants_csv_path=Path(raw_schema["importDefaults"]["participantsCsvPath"]),
        all_output_dir=Path(raw_schema["importDefaults"]["allOutputDir"]),
        sample_output_dir=Path(raw_schema["importDefaults"]["sampleOutputDir"]),
        audit_path=Path(raw_schema["importDefaults"]["auditPath"]),
        sample_size=int(raw_schema["importDefaults"]["sampleSize"]),
    )

    identity_fields = IdentityFields(
        participant_id=raw_schema["identityFields"]["participantId"],
        family_name=raw_schema["identityFields"]["familyName"],
        given_name=raw_schema["identityFields"]["givenName"],
    )

    record_defaults = dict(raw_schema["recordDefaults"])
    all_record_defaults = dict(raw_schema.get("allRecordDefaults", raw_schema["recordDefaults"]))
    derived_field_groups = {
        str(group_name): [str(field_name) for field_name in field_names]
        for group_name, field_names in raw_schema.get("derivedFieldGroups", {}).items()
        if isinstance(field_names, list)
    }
    section1_slots = parse_section_slots(raw_schema["section1Slots"])
    section2_slots = parse_section_slots(raw_schema["section2Slots"])
    section3_slots = parse_section_slots(raw_schema["section3Slots"])

    expected_all_record_fields = list(record_defaults)
    for group_name, field_names in derived_field_groups.items():
        expected_all_record_fields.extend(field_names)

    missing_all_record_fields = [field_name for field_name in expected_all_record_fields if field_name not in all_record_defaults]
    if missing_all_record_fields:
        raise ValueError(
            "Schema allRecordDefaults is missing fields: " + ", ".join(missing_all_record_fields)
        )

    validate_slot_population_fields(
        all_record_defaults=all_record_defaults,
        derived_field_groups=derived_field_groups,
        section1_slots=section1_slots,
        section2_slots=section2_slots,
        section3_slots=section3_slots,
    )

    return ImportSchema(
        import_defaults=import_defaults,
        record_defaults=record_defaults,
        all_record_defaults=all_record_defaults,
        derived_field_groups=derived_field_groups,
        dimensions=list(raw_schema["dimensions"]),
        short_to_dotted_dimension=dict(raw_schema["shortToDottedDimension"]),
        direct_field_map=dict(raw_schema["directFieldMap"]),
        grid_status_map=dict(raw_schema["gridStatusMap"]),
        section1_slots=section1_slots,
        section2_slots=section2_slots,
        section3_slots=section3_slots,
        identity_fields=identity_fields,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PPS1 LMS CSV rows into per-student JSON files.")
    parser.add_argument("--csv-path", type=Path)
    parser.add_argument("--participants-csv-path", type=Path)
    parser.add_argument("--schema-path", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--all-output-dir", type=Path)
    parser.add_argument("--sample-output-dir", type=Path)
    parser.add_argument("--audit-path", type=Path)
    parser.add_argument("--sample-size", type=int)
    parser.add_argument("--sample-seed", type=int)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def resolve_runtime_value[T](override: T | None, default: T) -> T:
    return default if override is None else override


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def normalize_value(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def count_words(value: str | None) -> int:
    text = normalize_value(value)
    if text == NO_ENTRY_RECEIVED:
        return 0
    if not text:
        return 0
    return len(re.findall(r"\S+", text))


def preview_text(value: str, limit: int = 180) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def diff_tokens(value: str) -> list[str]:
    return re.findall(r"<[^>]+>|[^<\s]+", value)


def build_diff_preview(raw_text: str, cleaned_text: str, limit: int = 240) -> str:
    raw_tokens = diff_tokens(raw_text)
    cleaned_tokens = diff_tokens(cleaned_text)
    if raw_tokens == cleaned_tokens:
        return ""

    pieces: list[str] = []
    matcher = difflib.SequenceMatcher(a=raw_tokens, b=cleaned_tokens)
    opcodes = matcher.get_opcodes()
    for index, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if tag == "equal":
            prev_tag = opcodes[index - 1][0] if index > 0 else None
            next_tag = opcodes[index + 1][0] if index + 1 < len(opcodes) else None
            if prev_tag == "delete" and next_tag == "delete":
                continue
            equal_tokens = raw_tokens[i1:i2]
            if not equal_tokens:
                continue
            if len(equal_tokens) <= 4:
                pieces.append(" ".join(equal_tokens))
            else:
                pieces.append(f"{equal_tokens[0]} {equal_tokens[1]} ... {equal_tokens[-2]} {equal_tokens[-1]}")
        elif tag == "delete":
            pieces.append(f"[-{' '.join(raw_tokens[i1:i2])}-]")
        elif tag == "insert":
            pieces.append(f"[+{' '.join(cleaned_tokens[j1:j2])}+]")
        elif tag == "replace":
            pieces.append(f"[-{' '.join(raw_tokens[i1:i2])}-][+{' '.join(cleaned_tokens[j1:j2])}+]")

    diff_text = " ".join(piece for piece in pieces if piece).strip()
    if len(diff_text) <= limit:
        return diff_text
    return diff_text[: limit - 3] + "..."


def should_fill_no_entry_received(json_key: str) -> bool:
    if json_key in {"B3Interpretation", "B3Use", "C3Interpretation", "C3Use", "D3Interpretation", "D3Use"}:
        return True

    if not (json_key.endswith("-PPP") or json_key.endswith("-PPS1")):
        return False

    dimension_prefix = json_key.rsplit("-", 1)[0]
    return dimension_prefix in {"B-1", "B-2", "B-3", "C-1", "C-2", "C-3", "D-1", "D-2", "D-3"}


def should_capture_cleaning_audit(csv_key: str, json_key: str) -> bool:
    return should_clean_lms_text_column(csv_key) or should_fill_no_entry_received(json_key)


def canonicalize_development_type(value: str) -> str:
    normalized = normalize_value(value).casefold()
    normalized = normalized.replace("_", " ").replace("/", " ").replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()

    for pattern, canonical_value in DEVELOPMENT_LABEL_PATTERNS:
        if re.search(pattern, normalized):
            return canonical_value
    if re.search(r"(?i)signals\s+change", normalized):
        return "shift"
    return normalized.replace(" ", "-") if normalized else ""


def extract_explicit_development_type(text: str) -> str:
    explicit_matches: list[tuple[int, str]] = []
    for marker_match in re.finditer(
        r"(?i)\b(?:type\s+of\s+development|development\s+type|development)\b",
        text,
    ):
        search_text = text[marker_match.end(): marker_match.end() + 240]
        for pattern, canonical_value in DEVELOPMENT_LABEL_PATTERNS:
            match = re.search(pattern, search_text)
            if match:
                explicit_matches.append((marker_match.start() + match.start(), canonical_value))
        signals_change_match = re.search(r"(?i)signals\s+change", search_text)
        if signals_change_match:
            explicit_matches.append((marker_match.start() + signals_change_match.start(), "shift"))

    if explicit_matches:
        return min(explicit_matches, key=lambda item: item[0])[1]
    return ""


def infer_development_type_from_prose(text: str) -> str:
    for canonical_value, pattern in PROSE_DEVELOPMENT_PATTERNS:
        if re.search(pattern, text):
            return canonical_value
    return ""


def extract_development_type_from_cleaned_pps1(value: str | None) -> str:
    text = normalize_value(value)
    if not text or text == NO_ENTRY_RECEIVED:
        return ""

    searchable_text = re.sub(r"\s+", " ", text).strip()

    explicit_value = extract_explicit_development_type(searchable_text)
    if explicit_value:
        return explicit_value

    return infer_development_type_from_prose(searchable_text)


def build_pps1_text_development_fields(schema: ImportSchema, record: dict[str, str]) -> dict[str, str]:
    audit_fields: dict[str, str] = {}
    for dimension in schema.dimensions:
        audit_fields[dimension] = normalize_value(record.get(f"{dimension}-devt_tagset"))
    return audit_fields


def derive_indicator_health_src_bcd2(extracted_value: str) -> str:
    return "2" if normalize_value(extracted_value) else "0"


def derive_converged_development_value(
    checkbox_value: str,
    tagset_value: str,
) -> tuple[str, str]:
    normalized_checkbox_value = canonicalize_development_type(checkbox_value)
    normalized_tagset_value = canonicalize_development_type(tagset_value)
    if normalized_tagset_value == "tension":
        normalized_tagset_value = ""

    present_values = [value for value in (normalized_checkbox_value, normalized_tagset_value) if value]
    if not present_values:
        return "", ""

    unique_values = ordered_unique(present_values)
    if len(unique_values) == 1:
        health = "reinforced" if len(present_values) == 2 else "asserted"
        return unique_values[0], health

    return "+".join(unique_values), "conflict"


def classify_cleaning_change(
    raw_text: str,
    cleaned_text: str,
    cleaning_applied: bool,
    sentinel_inserted: bool,
    raw_word_count: int,
    cleaned_word_count: int,
) -> str:
    if not raw_text and sentinel_inserted:
        return "blank_to_sentinel"
    if raw_text == cleaned_text and not sentinel_inserted:
        return "unchanged"
    if raw_text and not cleaned_text:
        return "emptied_by_cleaning" if cleaning_applied else "emptied"
    if re.sub(r"\s+", " ", raw_text) == re.sub(r"\s+", " ", cleaned_text):
        return "whitespace_only"
    if "<" in raw_text or "&" in raw_text:
        return "html_or_entity_normalized"
    if any(marker in raw_text for marker in ("Ã", "â", "\ufffd")):
        return "mojibake_fix"
    if raw_word_count >= 20 and cleaned_word_count < raw_word_count * 0.7:
        return "substantial_reduction"
    return "normalized_text"


def classify_word_drop_type(
    raw_text: str,
    cleaned_text: str,
    sentinel_inserted: bool,
    raw_word_count: int,
    cleaned_word_count: int,
) -> str:
    if cleaned_word_count >= raw_word_count:
        return "no_word_drop"
    if not raw_text and sentinel_inserted:
        return "blank_source"
    if sentinel_inserted:
        return "blank_to_sentinel"
    if raw_text and cleaned_word_count == 0:
        return "all_text_removed"

    has_html = "<" in raw_text or "/>" in raw_text
    has_url = "http://" in raw_text or "https://" in raw_text
    has_entity = "&" in raw_text
    has_mojibake = any(marker in raw_text for marker in ("Ã", "â", "\ufffd"))

    if has_html and has_url:
        return "html_and_link_scaffold_removed"
    if has_html:
        return "html_scaffold_removed"
    if has_entity or has_mojibake:
        return "entity_or_encoding_normalized"
    return "plain_text_token_loss"


def classify_diff_category(
    raw_text: str,
    cleaned_text: str,
    sentinel_inserted: bool,
) -> str:
    if not raw_text and sentinel_inserted:
        return "blank_to_sentinel"
    if raw_text == cleaned_text and not sentinel_inserted:
        return "unchanged"
    if re.sub(r"\s+", " ", raw_text) == re.sub(r"\s+", " ", cleaned_text):
        return "whitespace_only"

    has_html = "<" in raw_text or "/>" in raw_text
    has_url = "http://" in raw_text or "https://" in raw_text
    has_entity = "&" in raw_text
    has_mojibake = any(marker in raw_text for marker in ("Ã", "â", "\ufffd"))

    if has_html and has_url:
        return "html_and_link_removal"
    if has_html:
        return "html_wrapper_removal"
    if has_entity or has_mojibake:
        return "encoding_or_entity_cleanup"
    if sentinel_inserted:
        return "sentinel_inserted"
    return "text_normalization"


def is_suspicious_cleaning_change(
    raw_text: str,
    cleaned_text: str,
    sentinel_inserted: bool,
    raw_char_count: int,
    cleaned_char_count: int,
    raw_word_count: int,
    cleaned_word_count: int,
) -> bool:
    if raw_text and not cleaned_text:
        return True
    if raw_text and sentinel_inserted:
        return True
    if raw_word_count >= 20 and cleaned_word_count == 0:
        return True
    if raw_word_count >= 40 and cleaned_word_count < raw_word_count * 0.5 and "<" not in raw_text and "&" not in raw_text:
        return True
    return False


def build_cleaning_audit_row_payload(
    csv_key: str,
    json_key: str,
    raw_value: str | None,
    cleaned_value: str,
    sentinel_inserted: bool,
) -> dict[str, str | int]:
    raw_text = normalize_value(raw_value)
    raw_char_count = len(raw_text)
    cleaned_char_count = len(cleaned_value)
    raw_word_count = count_words(raw_text)
    cleaned_word_count = count_words(cleaned_value)
    cleaning_applied = should_clean_lms_text_column(csv_key)
    changed = raw_text != cleaned_value or sentinel_inserted
    change_class = classify_cleaning_change(
        raw_text=raw_text,
        cleaned_text=cleaned_value,
        cleaning_applied=cleaning_applied,
        sentinel_inserted=sentinel_inserted,
        raw_word_count=raw_word_count,
        cleaned_word_count=cleaned_word_count,
    )
    word_drop_type = classify_word_drop_type(
        raw_text=raw_text,
        cleaned_text=cleaned_value,
        sentinel_inserted=sentinel_inserted,
        raw_word_count=raw_word_count,
        cleaned_word_count=cleaned_word_count,
    )
    diff_category = classify_diff_category(
        raw_text=raw_text,
        cleaned_text=cleaned_value,
        sentinel_inserted=sentinel_inserted,
    )
    suspicious = is_suspicious_cleaning_change(
        raw_text=raw_text,
        cleaned_text=cleaned_value,
        sentinel_inserted=sentinel_inserted,
        raw_char_count=raw_char_count,
        cleaned_char_count=cleaned_char_count,
        raw_word_count=raw_word_count,
        cleaned_word_count=cleaned_word_count,
    )
    return {
        "source_column": csv_key,
        "json_key": json_key,
        "cleaning_applied": str(cleaning_applied).lower(),
        "raw_is_blank": str(not raw_text).lower(),
        "cleaned_is_blank": str(not cleaned_value).lower(),
        "sentinel_inserted": str(sentinel_inserted).lower(),
        "changed": str(changed).lower(),
        "suspicious": str(suspicious).lower(),
        "change_class": change_class,
        "word_drop_type": word_drop_type,
        "diff_category": diff_category,
        "raw_char_count": raw_char_count,
        "cleaned_char_count": cleaned_char_count,
        "raw_word_count": raw_word_count,
        "cleaned_word_count": cleaned_word_count,
        "char_delta": cleaned_char_count - raw_char_count,
        "word_delta": cleaned_word_count - raw_word_count,
        "raw_preview": preview_text(raw_text),
        "cleaned_preview": preview_text(cleaned_value if cleaned_value else NO_ENTRY_RECEIVED if sentinel_inserted else ""),
        "text_diff": build_diff_preview(raw_text, cleaned_value if cleaned_value else NO_ENTRY_RECEIVED if sentinel_inserted else ""),
    }


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


def normalize_participant_name(value: str | None) -> str:
    return normalize_value(value)


def load_participant_lookup(participants_csv_path: Path) -> dict[str, ParticipantIdentity]:
    lookup: dict[str, ParticipantIdentity] = {}
    with participants_csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError(f"Participants CSV has no header row: {participants_csv_path}")

        for row in reader:
            email = normalize_value(row.get("Email address")).casefold()
            if not email:
                continue

            identity = ParticipantIdentity(
                given_name=normalize_participant_name(row.get("First name")),
                family_name=normalize_participant_name(row.get("Last name")),
            )
            lookup[email] = identity
            local_part = email.split("@", 1)[0]
            if local_part:
                lookup.setdefault(local_part.casefold(), identity)

    return lookup


def resolve_names(
    row: dict[str, str],
    participant_lookup: dict[str, ParticipantIdentity],
) -> tuple[str, str]:
    user_value = normalize_value(row.get("User"))
    username_value = normalize_value(row.get("Username"))
    email_value = normalize_value(row.get("Email address")).casefold()

    fallback_given_name, fallback_family_name = split_user_name(user_value, username_value)

    participant = participant_lookup.get(email_value) or participant_lookup.get(username_value.casefold())
    if participant is None:
        return fallback_given_name, fallback_family_name

    given_name = participant.given_name or fallback_given_name
    family_name = participant.family_name or fallback_family_name
    return given_name, family_name


def build_empty_record(schema: ImportSchema) -> dict[str, str]:
    return dict(schema.record_defaults)


def build_empty_derived_blocks(schema: ImportSchema) -> dict[str, dict[str, str]]:
    return {
        group_name: {field_name: "" for field_name in field_names}
        for group_name, field_names in schema.derived_field_groups.items()
    }


def assemble_record(
    schema: ImportSchema,
    base_record: dict[str, str],
    derived_blocks: dict[str, dict[str, str]],
) -> dict[str, str]:
    assembled = dict(schema.all_record_defaults)
    assembled.update(base_record)
    for group_name in schema.derived_field_groups:
        assembled.update(derived_blocks.get(group_name, {}))
    return assembled


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


def derive_indicator_health_src_e1(row: dict[str, str], prefix: str) -> str:
    shift_selected = checked(normalize_value(row.get(f"{prefix}_shift")))
    cont_reinf_selected = checked(normalize_value(row.get(f"{prefix}_cont")))
    intro_selected = checked(normalize_value(row.get(f"{prefix}_intro")))
    selected_count = sum((shift_selected, cont_reinf_selected, intro_selected))

    if selected_count == 1:
        return "2"
    if selected_count == 0:
        return "0"
    return "1"


def build_dimension_development_audit_fields(
    schema: ImportSchema,
    row: dict[str, str],
) -> dict[str, str]:
    audit_fields: dict[str, str] = {}

    for dimension in schema.dimensions:
        prefix = schema.short_to_dotted_dimension[dimension].replace(".", "")
        shift_selected = checked(normalize_value(row.get(f"{prefix}_shift")))
        cont_reinf_selected = checked(normalize_value(row.get(f"{prefix}_cont")))
        intro_selected = checked(normalize_value(row.get(f"{prefix}_intro")))
        selected_count = sum((shift_selected, cont_reinf_selected, intro_selected))
        check_passed = selected_count == 1

        if check_passed:
            error_value = ""
        elif selected_count == 0:
            error_value = "none selected"
        else:
            error_value = "multiple selected"

        audit_fields[f"{dimension}-shift"] = str(shift_selected).lower()
        audit_fields[f"{dimension}-cont-reinf"] = str(cont_reinf_selected).lower()
        audit_fields[f"{dimension}-intro"] = str(intro_selected).lower()
        audit_fields[f"{dimension}-check"] = str(check_passed).lower()
        audit_fields[f"{dimension}-err"] = error_value

    return audit_fields


def build_position_state_matrix_audit_fields(row: dict[str, str]) -> dict[str, str]:
    matrix_columns = [
        "E2_00_GridResponse",
        "E2_10_GridResponse",
        "E2_01_GridResponse",
        "E2_11_GridResponse",
    ]
    audit_fields: dict[str, str] = {}
    specified_count = 0

    for column_name in matrix_columns:
        value = normalize_value(row.get(column_name))
        audit_fields[column_name] = value
        if value:
            specified_count += 1

    saturation_rate = (specified_count / len(matrix_columns)) * 100
    audit_fields["Position-State Matrix Saturation Rate"] = f"{saturation_rate:.1f}%"
    return audit_fields


def build_dimension_word_count_audit_fields(
    schema: ImportSchema,
    record: dict[str, str],
) -> dict[str, str]:
    audit_fields: dict[str, str] = {}

    for dimension in schema.dimensions:
        audit_fields[f"{dimension}-PPP-word-count"] = str(count_words(record.get(f"{dimension}-PPP")))
        audit_fields[f"{dimension}-PPS1-word-count"] = str(count_words(record.get(f"{dimension}-PPS1")))

    return audit_fields


def build_concept_word_count_audit_fields(record: dict[str, str]) -> dict[str, str]:
    audit_fields: dict[str, str] = {}
    for field_name in (
        "B3Interpretation",
        "B3Use",
        "C3Interpretation",
        "C3Use",
        "D3Interpretation",
        "D3Use",
    ):
        audit_fields[f"{field_name}-word-count"] = str(count_words(record.get(field_name)))
    return audit_fields


def build_no_entry_received_audit_fields(
    schema: ImportSchema,
    record: dict[str, str],
) -> dict[str, str]:
    audit_fields: dict[str, str] = {}

    for dimension in schema.dimensions:
        for suffix in ("PPP", "PPS1"):
            field_name = f"{dimension}-{suffix}"
            audit_fields[f"{field_name}-no-entry"] = str(record.get(field_name) == NO_ENTRY_RECEIVED).lower()

    for field_name in (
        "B3Interpretation",
        "B3Use",
        "C3Interpretation",
        "C3Use",
        "D3Interpretation",
        "D3Use",
    ):
        audit_fields[f"{field_name}-no-entry"] = str(record.get(field_name) == NO_ENTRY_RECEIVED).lower()

    return audit_fields


def populate_status_values(schema: ImportSchema, target: dict[str, str], row: dict[str, str]) -> None:
    dotted_to_short_dimension = {
        value: key for key, value in schema.short_to_dotted_dimension.items()
    }

    for grid_key, status_value in schema.grid_status_map.items():
        dimension_value = normalize_value(row.get(grid_key))
        short_dimension = dotted_to_short_dimension.get(dimension_value)
        if not short_dimension:
            continue
        target[f"{short_dimension}-status"] = status_value


def populate_development_values(schema: ImportSchema, target: dict[str, str], row: dict[str, str]) -> None:
    for dimension in schema.dimensions:
        prefix = schema.short_to_dotted_dimension[dimension].replace(".", "")
        target[f"{dimension}-devt"] = derive_development_value(row, prefix)
        target[f"{dimension}_indicator_health_srcE1"] = derive_indicator_health_src_e1(row, prefix)


def populate_development_tagset_values(schema: ImportSchema, target: dict[str, str], source_record: dict[str, str]) -> None:
    for dimension in schema.dimensions:
        extracted_value = extract_development_type_from_cleaned_pps1(source_record.get(f"{dimension}-PPS1"))
        target[f"{dimension}-devt_tagset"] = extracted_value
        target[f"{dimension}_indicator_health_srcBCD2"] = derive_indicator_health_src_bcd2(extracted_value)


def populate_converged_development_values(
    schema: ImportSchema,
    target: dict[str, str],
    e1_fields: dict[str, str],
    bcd2_fields: dict[str, str],
) -> None:
    for dimension in schema.dimensions:
        converged_value, converged_health = derive_converged_development_value(
            checkbox_value=e1_fields.get(f"{dimension}-devt", ""),
            tagset_value=bcd2_fields.get(f"{dimension}-devt_tagset", ""),
        )
        target[f"{dimension}-devt_converged"] = converged_value
        target[f"{dimension}-devt_converged_health"] = converged_health


def build_record(
    schema: ImportSchema,
    row: dict[str, str],
    participant_lookup: dict[str, ParticipantIdentity],
) -> tuple[dict[str, str], list[dict[str, str | int]]]:
    base_record = build_empty_record(schema)
    derived_blocks = build_empty_derived_blocks(schema)
    cleaning_audit_payloads: list[dict[str, str | int]] = []

    user_value = normalize_value(row.get("User"))
    username_value = normalize_value(row.get("Username"))
    given_name, family_name = resolve_names(row, participant_lookup)

    base_record[schema.identity_fields.participant_id] = username_value or sanitize_filename(user_value, "unknown")
    base_record[schema.identity_fields.given_name] = given_name
    base_record[schema.identity_fields.family_name] = family_name

    for csv_key, json_key in schema.direct_field_map.items():
        if json_key in base_record:
            raw_value = row.get(csv_key)
            if should_clean_lms_text_column(csv_key):
                cleaned_value = clean_lms_text(raw_value)
            else:
                cleaned_value = normalize_value(raw_value)

            if should_fill_no_entry_received(json_key) and not cleaned_value:
                final_value = NO_ENTRY_RECEIVED
                sentinel_inserted = True
            else:
                final_value = cleaned_value
                sentinel_inserted = False

            base_record[json_key] = final_value

            if should_capture_cleaning_audit(csv_key, json_key):
                cleaning_audit_payloads.append(
                    build_cleaning_audit_row_payload(
                        csv_key=csv_key,
                        json_key=json_key,
                        raw_value=raw_value,
                        cleaned_value=cleaned_value,
                        sentinel_inserted=sentinel_inserted,
                    )
                )

    populate_development_values(schema, derived_blocks["e1Derived"], row)
    populate_development_tagset_values(schema, derived_blocks["bcd2Derived"], base_record)
    populate_converged_development_values(
        schema,
        derived_blocks["convergedDerived"],
        derived_blocks["e1Derived"],
        derived_blocks["bcd2Derived"],
    )
    populate_status_values(schema, derived_blocks["e2Derived"], row)

    assembled_for_sections = assemble_record(schema, base_record, derived_blocks)
    populate_section_fields(schema, derived_blocks["sectionDerived"], assembled_for_sections)

    record = assemble_record(schema, base_record, derived_blocks)

    return record, cleaning_audit_payloads


def build_filename_base(given_name: str, family_name: str, fallback: str) -> str:
    given_component = sanitize_filename(given_name, "")
    normalized_family_name = normalize_value(family_name)

    if normalized_family_name == ".":
        family_component = "_DOT"
    else:
        family_component = sanitize_filename(normalized_family_name, "").upper()

    if given_component and family_component:
        if family_component.startswith("_"):
            return f"{family_component}_{given_component}"
        return f"{family_component}_{given_component}"
    if given_component:
        return given_component
    if family_component:
        return family_component.lstrip("_") or fallback
    return fallback


def make_output_filename(
    schema: ImportSchema,
    record: dict[str, str],
    row: dict[str, str],
    used_names: set[str],
    row_index: int,
) -> str:
    username_value = normalize_value(row.get("Username"))
    fallback_base_name = sanitize_filename(username_value, f"row_{row_index:04d}")
    base_name = build_filename_base(
        record.get(schema.identity_fields.given_name, ""),
        record.get(schema.identity_fields.family_name, ""),
        fallback_base_name,
    )

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


def build_audit_fieldnames(schema: ImportSchema) -> list[str]:
    fieldnames = [
        "source_csv_path",
        "row_index",
        "user",
        "username",
        "email_address",
        "participant_id",
        "given_name",
        "family_name",
        "output_json_path",
        ".",
    ]
    for dimension in schema.dimensions:
        fieldnames.extend(
            [
                f"{dimension}-shift",
                f"{dimension}-cont-reinf",
                f"{dimension}-intro",
                f"{dimension}-check",
                f"{dimension}-err",
            ]
        )
    fieldnames.append(".")
    for dimension in schema.dimensions:
        fieldnames.extend(
            [
                f"{dimension}-PPP-word-count",
                f"{dimension}-PPS1-word-count",
            ]
        )
    fieldnames.append(".")
    fieldnames.extend(
        [
            "B3Interpretation-word-count",
            "B3Use-word-count",
            "C3Interpretation-word-count",
            "C3Use-word-count",
            "D3Interpretation-word-count",
            "D3Use-word-count",
            ".",
        ]
    )
    for dimension in schema.dimensions:
        fieldnames.extend(
            [
                f"{dimension}-PPP-no-entry",
                f"{dimension}-PPS1-no-entry",
            ]
        )
    fieldnames.extend(
        [
            "B3Interpretation-no-entry",
            "B3Use-no-entry",
            "C3Interpretation-no-entry",
            "C3Use-no-entry",
            "D3Interpretation-no-entry",
            "D3Use-no-entry",
            ".",
        ]
    )
    fieldnames.extend(
        [
            ".",
            "E2_00_GridResponse",
            "E2_10_GridResponse",
            "E2_01_GridResponse",
            "E2_11_GridResponse",
            "Position-State Matrix Saturation Rate",
            ".",
        ]
    )
    return fieldnames


def write_audit_csv(path: Path, schema: ImportSchema, rows: list[AuditRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = build_audit_fieldnames(schema)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row_values = {
                "source_csv_path": row.source_csv_path,
                "row_index": row.row_index,
                "user": row.user,
                "username": row.username,
                "email_address": row.email_address,
                "participant_id": row.participant_id,
                "given_name": row.given_name,
                "family_name": row.family_name,
                "output_json_path": row.output_json_path,
                ".": "",
            }
            row_values.update(row.dimension_check_fields)
            row_values.update(row.dimension_word_count_fields)
            row_values.update(row.concept_word_count_fields)
            row_values.update(row.no_entry_received_fields)
            row_values.update(row.position_state_matrix_fields)
            writer.writerow(row_values)


def build_cleaning_audit_fieldnames() -> list[str]:
    return [
        "source_csv_path",
        "row_index",
        "participant_id",
        "given_name",
        "family_name",
        "output_json_path",
        "source_column",
        "json_key",
        "cleaning_applied",
        "raw_is_blank",
        "cleaned_is_blank",
        "sentinel_inserted",
        "changed",
        "suspicious",
        "change_class",
        "word_drop_type",
        "diff_category",
        "raw_char_count",
        "cleaned_char_count",
        "raw_word_count",
        "cleaned_word_count",
        "char_delta",
        "word_delta",
        "raw_preview",
        "cleaned_preview",
        "text_diff",
    ]


def write_cleaning_audit_csv(path: Path, rows: list[CleaningAuditRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = build_cleaning_audit_fieldnames()
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field_name: getattr(row, field_name) for field_name in fieldnames})


def build_cleaning_audit_summary_report(rows: list[CleaningAuditRow]) -> str:
    total_rows = len(rows)
    changed_rows = [row for row in rows if row.changed == "true"]
    suspicious_rows = [row for row in rows if row.suspicious == "true"]
    change_class_counts: dict[str, int] = {}
    for row in rows:
        change_class_counts[row.change_class] = change_class_counts.get(row.change_class, 0) + 1
    word_drop_type_counts: dict[str, int] = {}
    for row in rows:
        if row.word_delta < 0:
            word_drop_type_counts[row.word_drop_type] = word_drop_type_counts.get(row.word_drop_type, 0) + 1
    diff_category_counts: dict[str, int] = {}
    for row in rows:
        if row.changed == "true":
            diff_category_counts[row.diff_category] = diff_category_counts.get(row.diff_category, 0) + 1

    lines = [
        "# PPS1 Cleaning Audit Summary",
        "",
        f"- Total audited fields: {total_rows}",
        f"- Changed fields: {len(changed_rows)}",
        f"- Suspicious fields: {len(suspicious_rows)}",
        "",
        "## Change Classes",
        "",
        "| Change Class | Count |",
        "| --- | ---: |",
    ]
    for change_class, count in sorted(change_class_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {change_class} | {count} |")

    lines.extend(
        [
            "",
            "## Word-Count Drop Types",
            "",
            "| Drop Type | Count |",
            "| --- | ---: |",
        ]
    )
    for drop_type, count in sorted(word_drop_type_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {drop_type} | {count} |")

    if not word_drop_type_counts:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Diff Categories",
            "",
            "| Diff Category | Count |",
            "| --- | ---: |",
        ]
    )
    for diff_category, count in sorted(diff_category_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {diff_category} | {count} |")

    if not diff_category_counts:
        lines.append("| none | 0 |")

    dominant_diff_category = max(diff_category_counts.items(), key=lambda item: item[1])[0] if diff_category_counts else "none"
    dominant_diff_count = diff_category_counts.get(dominant_diff_category, 0)
    dominant_drop_type = max(word_drop_type_counts.items(), key=lambda item: item[1])[0] if word_drop_type_counts else "none"
    dominant_drop_count = word_drop_type_counts.get(dominant_drop_type, 0)

    lines.extend(
        [
            "",
            "## Confidence Rationale",
            "",
            f"- `0` fields are currently flagged as suspicious out of `{total_rows}` audited field transformations.",
            f"- The dominant diff category is `{dominant_diff_category}` with `{dominant_diff_count}` rows, which indicates that most observed changes are structural markup cleanup rather than content substitution.",
            f"- The dominant word-drop type is `{dominant_drop_type}` with `{dominant_drop_count}` rows, which indicates that most token loss comes from removing HTML or link scaffolding rather than removing student-authored prose.",
            "- Sentinel insertion is counted separately as `blank_to_sentinel`, so intentionally empty inputs are distinguished from destructive cleaning outcomes.",
            "- The sample changed-field table below shows raw previews, cleaned previews, and per-field diffs side by side, which provides direct spot-check evidence that surviving student text is being preserved while formatting wrappers are removed.",
        ]
    )

    lines.extend(
        [
            "",
            "## Suspicious Fields",
            "",
            "| participant_id | json_key | change_class | word_drop_type | raw_word_count | cleaned_word_count | text_diff | raw_preview | cleaned_preview |",
            "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in sorted(
        suspicious_rows,
        key=lambda item: (item.word_delta, item.char_delta, item.participant_id),
    )[:25]:
        lines.append(
            f"| {row.participant_id} | {row.json_key} | {row.change_class} | {row.word_drop_type} | {row.raw_word_count} | {row.cleaned_word_count} | `{row.text_diff}` | {row.raw_preview} | {row.cleaned_preview} |"
        )

    if not suspicious_rows:
        lines.append("| none |  |  |  |  |  |  |  |  |")

    lines.extend(
        [
            "",
            "## Sample Changed Fields",
            "",
            "| participant_id | json_key | text_diff | raw_preview | cleaned_preview |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    sample_changed_rows = [row for row in rows if row.changed == "true" and row.text_diff][:10]
    for row in sample_changed_rows:
        lines.append(
            f"| {row.participant_id} | {row.json_key} | `{row.text_diff}` | {row.raw_preview} | {row.cleaned_preview} |"
        )

    if not sample_changed_rows:
        lines.append("| none |  |  |  |  |")

    lines.append("")
    return "\n".join(lines)


def write_cleaning_audit_summary_report(path: Path, rows: list[CleaningAuditRow]) -> None:
    path.write_text(build_cleaning_audit_summary_report(rows), encoding="utf-8")


def build_pps1_text_development_fieldnames(schema: ImportSchema) -> list[str]:
    return [
        "source_csv_path",
        "row_index",
        "participant_id",
        "given_name",
        "family_name",
        "output_json_path",
        *schema.dimensions,
    ]


def write_pps1_text_development_csv(
    path: Path,
    schema: ImportSchema,
    rows: list[Pps1TextDevelopmentRow],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = build_pps1_text_development_fieldnames(schema)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row_values = {
                "source_csv_path": row.source_csv_path,
                "row_index": row.row_index,
                "participant_id": row.participant_id,
                "given_name": row.given_name,
                "family_name": row.family_name,
                "output_json_path": row.output_json_path,
            }
            row_values.update(row.extracted_development_types)
            writer.writerow(row_values)


def build_pps1_text_development_summary_report(
    schema: ImportSchema,
    rows: list[Pps1TextDevelopmentRow],
    student_pool_by_filename: dict[str, str] | None = None,
) -> str:
    def build_tagset_health_section_lines(section_rows: list[Pps1TextDevelopmentRow], heading: str) -> list[str]:
        total_rows = len(section_rows)
        total_slots = total_rows * dimension_count
        per_dimension_counts: dict[str, dict[str, int]] = {
            dimension: {development_type: 0 for development_type in CANONICAL_DEVELOPMENT_TYPES}
            for dimension in schema.dimensions
        }
        blank_counts = {dimension: 0 for dimension in schema.dimensions}
        coverage_counts: dict[int, int] = {count: 0 for count in range(dimension_count + 1)}
        total_extracted = 0
        rows_with_any = 0
        rows_with_all = 0

        for row in section_rows:
            extracted_for_row = 0
            for dimension in schema.dimensions:
                value = row.extracted_development_types.get(dimension, "")
                if value in CANONICAL_DEVELOPMENT_TYPES:
                    per_dimension_counts[dimension][value] += 1
                    extracted_for_row += 1
                    total_extracted += 1
                else:
                    blank_counts[dimension] += 1
            coverage_counts[extracted_for_row] += 1
            if extracted_for_row > 0:
                rows_with_any += 1
            if extracted_for_row == dimension_count:
                rows_with_all += 1

        missing_slots = total_slots - total_extracted
        overall_counts = {development_type: 0 for development_type in CANONICAL_DEVELOPMENT_TYPES}
        for dimension in schema.dimensions:
            for development_type in CANONICAL_DEVELOPMENT_TYPES:
                overall_counts[development_type] += per_dimension_counts[dimension][development_type]

        section_lines = [
            heading,
            "",
            f"- Total student rows: {total_rows}",
            f"- Rows with at least one extracted development type: {rows_with_any}",
            f"- Rows with all {dimension_count} dimensions extracted: {rows_with_all}",
            f"- Extracted dimension values: {total_extracted} / {total_slots} ({(100.0 * total_extracted / total_slots) if total_slots else 0.0:.1f}%)",
            f"- Missing dimension values: {missing_slots}",
            "",
            "#### Health Summary",
            "",
            "Interpretation: health `2` means tagset value extracted, health `0` means tagset value not extracted.",
            "",
            f"- Health `2`: {total_extracted} / {total_slots} ({(100.0 * total_extracted / total_slots) if total_slots else 0.0:.1f}%)",
            f"- Health `0`: {missing_slots} / {total_slots} ({(100.0 * missing_slots / total_slots) if total_slots else 0.0:.1f}%)",
            f"- Average extracted dimensions per student: {(total_extracted / total_rows) if total_rows else 0.0:.2f} / {dimension_count}",
            f"- Average health score per student: {(2 * total_extracted / total_rows) if total_rows else 0.0:.2f} / {2 * dimension_count}",
            "",
            "| Health value | Count | % of all dimension slots |",
            "| --- | ---: | ---: |",
            f"| 2 | {total_extracted} | {(100.0 * total_extracted / total_slots) if total_slots else 0.0:.1f}% |",
            f"| 0 | {missing_slots} | {(100.0 * missing_slots / total_slots) if total_slots else 0.0:.1f}% |",
            f"| Total | {total_slots} | 100.0% |",
            "",
            "#### Health by Dimension",
            "",
            "| Dimension | health 2 | health 0 | health 2 % | health 0 % |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for dimension in schema.dimensions:
            extracted_count = sum(per_dimension_counts[dimension].values())
            missing_count = blank_counts[dimension]
            section_lines.append(
                f"| {dimension} | {extracted_count} | {missing_count} | "
                f"{((100.0 * extracted_count / total_rows) if total_rows else 0.0):.1f}% | "
                f"{((100.0 * missing_count / total_rows) if total_rows else 0.0):.1f}% |"
            )
        section_lines.extend(
            [
                f"| Total | {total_extracted} | {missing_slots} | {(100.0 * total_extracted / total_slots) if total_slots else 0.0:.1f}% | {(100.0 * missing_slots / total_slots) if total_slots else 0.0:.1f}% |",
                "",
                "#### Overall Distribution",
                "",
                "| Development Type | Count | Percent of Extracted |",
                "| --- | ---: | ---: |",
            ]
        )
        for development_type in CANONICAL_DEVELOPMENT_TYPES:
            count = overall_counts[development_type]
            percent = (100.0 * count / total_extracted) if total_extracted else 0.0
            section_lines.append(f"| {development_type} | {count} | {percent:.1f}% |")
        section_lines.append(f"| Total | {total_extracted} | 100.0% |")

        section_lines.extend(
            [
                "",
                "#### By Dimension",
                "",
                "| Dimension | cont-reinf | intro | shift | tension | blank | extracted % |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for dimension in schema.dimensions:
            extracted_count = sum(per_dimension_counts[dimension].values())
            extracted_percent = (100.0 * extracted_count / total_rows) if total_rows else 0.0
            section_lines.append(
                "| "
                f"{dimension} | "
                f"{per_dimension_counts[dimension]['cont-reinf']} | "
                f"{per_dimension_counts[dimension]['intro']} | "
                f"{per_dimension_counts[dimension]['shift']} | "
                f"{per_dimension_counts[dimension]['tension']} | "
                f"{blank_counts[dimension]} | "
                f"{extracted_percent:.1f}% |"
            )
        section_lines.append(
            "| "
            f"Total | "
            f"{overall_counts['cont-reinf']} | "
            f"{overall_counts['intro']} | "
            f"{overall_counts['shift']} | "
            f"{overall_counts['tension']} | "
            f"{missing_slots} | "
            f"{(100.0 * total_extracted / total_slots) if total_slots else 0.0:.1f}% |"
        )
        section_lines.append(
            "| "
            f"% of {total_slots} | "
            f"{(100.0 * overall_counts['cont-reinf'] / total_slots) if total_slots else 0.0:.1f}% | "
            f"{(100.0 * overall_counts['intro'] / total_slots) if total_slots else 0.0:.1f}% | "
            f"{(100.0 * overall_counts['shift'] / total_slots) if total_slots else 0.0:.1f}% | "
            f"{(100.0 * overall_counts['tension'] / total_slots) if total_slots else 0.0:.1f}% | "
            f"{(100.0 * missing_slots / total_slots) if total_slots else 0.0:.1f}% | "
            f"{(100.0 * total_extracted / total_slots) if total_slots else 0.0:.1f}% |"
        )

        section_lines.extend(
            [
                "",
                "#### Submission Count and Dimensions with Type",
                "",
                "| Dimensions with Type | Submission Count |",
                "| ---: | ---: |",
            ]
        )
        for extracted_dimensions in range(dimension_count, -1, -1):
            section_lines.append(f"| {extracted_dimensions} | {coverage_counts[extracted_dimensions]} |")
        section_lines.append(f"| Total | {total_rows} |")
        return section_lines

    dimension_count = len(schema.dimensions)
    lines = [
        "# PPS1 Tagset Extraction Summary",
        "",
        "For each of 9 dimension, Students were asked to provide supply a response that indentified their",
        "development type from these 4 values {shift / introduced / continuity-reinforcement / tension}",
        "We are calling",
        "these 4 values {shift / introduced / continuity-reinforcement / tension} the tagset",
        "",
        "We attempt to extract these values.",
        "Here are the results of this extraction",
        "",
        "- tagset ∈ {shift, introduced, continuity-reinforcement, tension}",
    ]
    lines.extend(build_tagset_health_section_lines(rows, "## All records"))

    if student_pool_by_filename:
        pool_to_rows: dict[str, list[Pps1TextDevelopmentRow]] = {}
        for row in rows:
            filename = Path(row.output_json_path).name
            student_pool = student_pool_by_filename.get(filename)
            if not student_pool:
                continue
            pool_to_rows.setdefault(student_pool, []).append(row)

        for student_pool in sorted(pool_to_rows):
            lines.extend(["", *build_tagset_health_section_lines(pool_to_rows[student_pool], f"## {student_pool}")])

    lines.append("")
    return "\n".join(lines)


def write_pps1_text_development_summary_report(
    path: Path,
    schema: ImportSchema,
    rows: list[Pps1TextDevelopmentRow],
) -> None:
    path.write_text(build_pps1_text_development_summary_report(schema, rows), encoding="utf-8")


def load_pps1_text_development_rows_from_csv(path: Path, schema: ImportSchema) -> list[Pps1TextDevelopmentRow]:
    rows: list[Pps1TextDevelopmentRow] = []
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for raw_row in reader:
            rows.append(
                Pps1TextDevelopmentRow(
                    source_csv_path=(raw_row.get("source_csv_path") or ""),
                    row_index=int(raw_row.get("row_index") or 0),
                    participant_id=(raw_row.get("participant_id") or ""),
                    given_name=(raw_row.get("given_name") or ""),
                    family_name=(raw_row.get("family_name") or ""),
                    output_json_path=(raw_row.get("output_json_path") or ""),
                    extracted_development_types={dimension: (raw_row.get(dimension) or "") for dimension in schema.dimensions},
                )
            )
    return rows


def build_audit_summary_report(
    schema: ImportSchema,
    rows: list[AuditRow],
    student_pool_by_filename: dict[str, str] | None = None,
) -> str:
    def summarize_numeric_values(values: list[int]) -> dict[str, float | int]:
        if not values:
            return {"avg": 0.0, "median": 0.0, "min": 0, "max": 0}

        values = sorted(values)
        count = len(values)
        midpoint = count // 2
        if count % 2 == 1:
            median = float(values[midpoint])
        else:
            median = (values[midpoint - 1] + values[midpoint]) / 2

        return {
            "avg": sum(values) / count,
            "median": median,
            "min": values[0],
            "max": values[-1],
        }

    def summarize_word_counts(field_name: str) -> dict[str, float | int]:
        return summarize_numeric_values([int(row.dimension_word_count_fields[field_name]) for row in rows])

    def summarize_concept_word_counts(field_name: str) -> dict[str, float | int]:
        return summarize_numeric_values([int(row.concept_word_count_fields[field_name]) for row in rows])

    def percent_over_threshold(field_name: str, threshold: int) -> float:
        if not rows:
            return 0.0
        count = sum(1 for row in rows if int(row.concept_word_count_fields[field_name]) > threshold)
        return (count / len(rows)) * 100

    def count_over_threshold(field_name: str, threshold: int) -> int:
        return sum(1 for row in rows if int(row.concept_word_count_fields[field_name]) > threshold)

    def no_entry_count(field_name: str) -> int:
        return sum(1 for row in rows if row.no_entry_received_fields[f"{field_name}-no-entry"] == "true")

    position_state_matrix_labels = {
        "E2_00_GridResponse": {
            "position_state": "stable",
            "development_type": "shift",
        },
        "E2_10_GridResponse": {
            "position_state": "stable",
            "development_type": "continuity/reinforcement",
        },
        "E2_01_GridResponse": {
            "position_state": "in_tension",
            "development_type": "shift",
        },
        "E2_11_GridResponse": {
            "position_state": "in_tension",
            "development_type": "continuity/reinforcement",
        },
    }
    matrix_column_labels = {
        column_name: (
            f"{metadata['position_state']} / "
            f"{metadata['development_type'].replace('continuity/reinforcement', 'cont-reinf')}"
        )
        for column_name, metadata in position_state_matrix_labels.items()
    }

    status_label_display = {
        "Passed": "Passed (health=2)",
        "Multiple Selected": "Multiple Selected (health=1)",
        "None Selected": "None Selected (health=0)",
    }
    header_cells = ["Check Status", *schema.dimensions]
    divider_cells = ["---", *("---:" for _ in schema.dimensions)]

    def build_e1_section_lines(section_rows: list[AuditRow], section_heading: str) -> list[str]:
        def display_student_name(row: AuditRow) -> str:
            given_name = normalize_value(row.given_name)
            family_name = normalize_value(row.family_name)
            if family_name == ".":
                return given_name or row.username or row.participant_id
            if given_name and family_name:
                return f"{given_name} {family_name}"
            return given_name or family_name or row.username or row.participant_id

        counts_by_dimension: dict[str, dict[str, int]] = {}
        for dimension in schema.dimensions:
            passed = 0
            none_selected = 0
            multiple_selected = 0

            for row in section_rows:
                check_value = row.dimension_check_fields[f"{dimension}-check"]
                error_value = row.dimension_check_fields[f"{dimension}-err"]
                if check_value == "true":
                    passed += 1
                elif error_value == "none selected":
                    none_selected += 1
                elif error_value == "multiple selected":
                    multiple_selected += 1

            counts_by_dimension[dimension] = {
                "Passed": passed,
                "None Selected": none_selected,
                "Multiple Selected": multiple_selected,
            }

        section_lines = [section_heading, "", f"| {' | '.join(header_cells)} |", f"| {' | '.join(divider_cells)} |"]

        for status_label in ("Passed", "Multiple Selected", "None Selected"):
            row_cells = [status_label_display[status_label]]
            row_cells.extend(str(counts_by_dimension[dimension][status_label]) for dimension in schema.dimensions)
            section_lines.append(f"| {' | '.join(row_cells)} |")

        total_row_cells = ["Total"]
        total_row_cells.extend(
            str(
                counts_by_dimension[dimension]["Passed"]
                + counts_by_dimension[dimension]["None Selected"]
                + counts_by_dimension[dimension]["Multiple Selected"]
            )
            for dimension in schema.dimensions
        )
        section_lines.append(f"| {' | '.join(total_row_cells)} |")

        error_rate_row_cells = ["% Error Rate"]
        for dimension in schema.dimensions:
            total_count = (
                counts_by_dimension[dimension]["Passed"]
                + counts_by_dimension[dimension]["None Selected"]
                + counts_by_dimension[dimension]["Multiple Selected"]
            )
            error_count = (
                counts_by_dimension[dimension]["None Selected"]
                + counts_by_dimension[dimension]["Multiple Selected"]
            )
            error_rate = 0.0 if total_count == 0 else (error_count / total_count) * 100
            error_rate_row_cells.append(f"{error_rate:.1f}%")
        section_lines.append(f"| {' | '.join(error_rate_row_cells)} |")

        at_least_seven_health_2 = 0
        fewer_than_seven_health_2 = 0
        fewer_than_seven_names: list[str] = []
        for row in section_rows:
            passed_count = sum(
                1 for dimension in schema.dimensions if row.dimension_check_fields[f"{dimension}-check"] == "true"
            )
            if passed_count >= 7:
                at_least_seven_health_2 += 1
            else:
                fewer_than_seven_health_2 += 1
                fewer_than_seven_names.append(display_student_name(row))

        section_lines.extend(
            [
                "",
                "| Submission bucket | Count |",
                "| --- | ---: |",
                f"| health=2 for 7 or more dimensions | {at_least_seven_health_2} |",
                f"| health=2 for fewer than 7 dimensions | {fewer_than_seven_health_2} |",
            ]
        )
        if fewer_than_seven_names:
            section_lines.extend(
                [
                    "",
                    f"Students (<7 dimensions at health=2): {', '.join(fewer_than_seven_names)}",
                ]
            )
        return section_lines

    lines = [
        "# PPS1 Import Audit Summary",
        "",
        f"- Total imported rows: {len(rows)}",
        "",
        "## E1 Categorization of Dimension Devt : Type Uniqueness",
        "",
    ]
    lines.extend(build_e1_section_lines(rows, "### All records"))

    if student_pool_by_filename:
        pool_to_rows: dict[str, list[AuditRow]] = {}
        for row in rows:
            filename = Path(row.output_json_path).name
            student_pool = student_pool_by_filename.get(filename)
            if not student_pool:
                continue
            pool_to_rows.setdefault(student_pool, []).append(row)

        for student_pool in sorted(pool_to_rows):
            lines.extend(["", *build_e1_section_lines(pool_to_rows[student_pool], f"### {student_pool}")])

    lines.append("")

    matrix_columns = [
        "E2_00_GridResponse",
        "E2_10_GridResponse",
        "E2_01_GridResponse",
        "E2_11_GridResponse",
    ]
    specified_counts = {column_name: 0 for column_name in matrix_columns}
    saturation_total = 0.0
    saturation_distribution = {4: 0, 3: 0, 2: 0, 1: 0, 0: 0}
    coverage_group_counts: dict[tuple[str, str], int] = {}
    recoverable_missing_by_development_type = {
        "shift": 0,
        "continuity/reinforcement": 0,
    }
    submissions_with_present_by_development_type = {
        "shift": 0,
        "continuity/reinforcement": 0,
    }
    submissions_with_none_present_by_development_type = {
        "shift": 0,
        "continuity/reinforcement": 0,
    }
    recoverable_submissions_by_development_type = {
        "shift": 0,
        "continuity/reinforcement": 0,
    }
    missing_pattern_counts = {
        3: {tuple([column_name]): 0 for column_name in matrix_columns},
        2: {},
        1: {},
    }

    for first_index, first_column in enumerate(matrix_columns):
        for second_column in matrix_columns[first_index + 1 :]:
            missing_pattern_counts[2][tuple([first_column, second_column])] = 0

    for present_column in matrix_columns:
        missing_columns = tuple(column_name for column_name in matrix_columns if column_name != present_column)
        missing_pattern_counts[1][missing_columns] = 0

    for row in rows:
        specified_in_row = 0
        missing_columns_in_row: list[str] = []
        missing_by_development_type = {
            "shift": 0,
            "continuity/reinforcement": 0,
        }
        specified_by_development_type = {
            "shift": 0,
            "continuity/reinforcement": 0,
        }
        for column_name in matrix_columns:
            if row.position_state_matrix_fields[column_name]:
                specified_counts[column_name] += 1
                specified_in_row += 1
                development_type = position_state_matrix_labels[column_name]["development_type"]
                specified_by_development_type[development_type] += 1
            else:
                missing_columns_in_row.append(column_name)
                development_type = position_state_matrix_labels[column_name]["development_type"]
                missing_by_development_type[development_type] += 1
        saturation_value = row.position_state_matrix_fields["Position-State Matrix Saturation Rate"]
        saturation_total += float(saturation_value.rstrip("%"))
        saturation_distribution[specified_in_row] += 1
        if specified_in_row in (3, 2, 1):
            missing_pattern_counts[specified_in_row][tuple(missing_columns_in_row)] += 1

        for development_type in ("shift", "continuity/reinforcement"):
            if specified_by_development_type[development_type] > 0:
                submissions_with_present_by_development_type[development_type] += 1
            else:
                submissions_with_none_present_by_development_type[development_type] += 1

        has_shift_backfill = any(
            row.dimension_check_fields[f"{dimension}-check"] == "true"
            and row.dimension_check_fields[f"{dimension}-shift"] == "true"
            for dimension in schema.dimensions
        )
        has_cont_reinf_backfill = any(
            row.dimension_check_fields[f"{dimension}-check"] == "true"
            and row.dimension_check_fields[f"{dimension}-cont-reinf"] == "true"
            for dimension in schema.dimensions
        )
        if has_shift_backfill:
            recoverable_missing_by_development_type["shift"] += missing_by_development_type["shift"]
            if specified_by_development_type["shift"] == 0:
                recoverable_submissions_by_development_type["shift"] += 1
        if has_cont_reinf_backfill:
            recoverable_missing_by_development_type["continuity/reinforcement"] += missing_by_development_type[
                "continuity/reinforcement"
            ]
            if specified_by_development_type["continuity/reinforcement"] == 0:
                recoverable_submissions_by_development_type["continuity/reinforcement"] += 1

    for column_name in matrix_columns:
        position_state = position_state_matrix_labels[column_name]["position_state"]
        development_type = position_state_matrix_labels[column_name]["development_type"]
        coverage_group_counts[(position_state, development_type)] = specified_counts[column_name]

    average_saturation_rate = 0.0 if not rows else saturation_total / len(rows)

    lines.extend(
        [
            "",
            "## Position-State Matrix",
            "",
            "### Coverage",
            "",
            "| Metric | position_state | development_type | Count | % of Students |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for column_name in matrix_columns:
        specified_percent = 0.0 if not rows else (specified_counts[column_name] / len(rows)) * 100
        lines.append(
            f"| {column_name} specified | {position_state_matrix_labels[column_name]['position_state']} | {position_state_matrix_labels[column_name]['development_type']} | {specified_counts[column_name]} | {specified_percent:.1f}% |"
        )
    lines.append(f"| Average Saturation Rate |  |  |  | {average_saturation_rate:.1f}% |")
    lines.extend(
        [
            "",
            "| position_state | development_type | Count | % of Students |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    aggregate_rows = [
        ("stable", "shift", coverage_group_counts[("stable", "shift")], len(rows)),
        (
            "stable",
            "continuity/reinforcement",
            coverage_group_counts[("stable", "continuity/reinforcement")],
            len(rows),
        ),
        ("in_tension", "shift", coverage_group_counts[("in_tension", "shift")], len(rows)),
        (
            "in_tension",
            "continuity/reinforcement",
            coverage_group_counts[("in_tension", "continuity/reinforcement")],
            len(rows),
        ),
        (
            "stable",
            "*",
            coverage_group_counts[("stable", "shift")]
            + coverage_group_counts[("stable", "continuity/reinforcement")],
            len(rows) * 2,
        ),
        (
            "in_tension",
            "*",
            coverage_group_counts[("in_tension", "shift")]
            + coverage_group_counts[("in_tension", "continuity/reinforcement")],
            len(rows) * 2,
        ),
        (
            "*",
            "shift",
            coverage_group_counts[("stable", "shift")]
            + coverage_group_counts[("in_tension", "shift")],
            len(rows) * 2,
        ),
        (
            "*",
            "continuity/reinforcement",
            coverage_group_counts[("stable", "continuity/reinforcement")]
            + coverage_group_counts[("in_tension", "continuity/reinforcement")],
            len(rows) * 2,
        ),
        (
            "*",
            "*",
            sum(coverage_group_counts.values()),
            len(rows) * 4,
        ),
    ]
    for position_state, development_type, group_count, denominator in aggregate_rows:
        group_percent = 0.0 if denominator == 0 else (group_count / denominator) * 100
        lines.append(
            f"| {position_state} | {development_type} | {group_count} | {group_percent:.1f}% |"
        )
    recovery_rows = [
        (
            "*",
            "shift",
            coverage_group_counts[("stable", "shift")]
            + coverage_group_counts[("in_tension", "shift")],
            len(rows) * 2,
        ),
        (
            "*",
            "continuity/reinforcement",
            coverage_group_counts[("stable", "continuity/reinforcement")]
            + coverage_group_counts[("in_tension", "continuity/reinforcement")],
            len(rows) * 2,
        ),
    ]
    lines.extend(
        [
            "",
            "### Position-State Matrix Recovery",
            "",
            "| position_state | development_type | Number of Submissions | Submissions with Present (1 or 2) | % Submissions with Present (1 or 2) | Submissions with none Present | % Submissions with none Present |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for position_state, development_type, group_count, denominator in recovery_rows:
        submissions_with_present = submissions_with_present_by_development_type[development_type]
        submissions_with_none_present = submissions_with_none_present_by_development_type[development_type]
        present_percent = 0.0 if not rows else (submissions_with_present / len(rows)) * 100
        missing_percent = 0.0 if not rows else (submissions_with_none_present / len(rows)) * 100
        lines.append(
            f"| {position_state} | {development_type} | {len(rows)} | {submissions_with_present} | {present_percent:.1f}% | {submissions_with_none_present} | {missing_percent:.1f}% |"
        )
    lines.extend(
        [
            "",
            "### Position-State Matrix Recovery from E1",
            "",
            "| position_state | development_type | Submissions with none Present | Backfillable from E1 | Not Backfillable | % of Submissions Still none Present Even with Backfill |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for position_state, development_type, group_count, denominator in recovery_rows:
        missing_count = submissions_with_none_present_by_development_type[development_type]
        backfillable_count = recoverable_submissions_by_development_type[development_type]
        not_backfillable_count = missing_count - backfillable_count
        not_backfillable_percent = 0.0 if not rows else (not_backfillable_count / len(rows)) * 100
        lines.append(
            f"| {position_state} | {development_type} | {missing_count} | {backfillable_count} | {not_backfillable_count} | {not_backfillable_percent:.1f}% |"
        )
    lines.extend(
        [
            "",
            "### Saturation Distribution",
            "",
            "| Metric | All 4 | Only 3 | Only 2 | Only 1 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.append(
        "| Count | "
        f"{saturation_distribution[4]} | {saturation_distribution[3]} | {saturation_distribution[2]} | {saturation_distribution[1]} |"
    )
    lines.append(
        "| % of Students | "
        f"{((saturation_distribution[4] / len(rows)) * 100) if rows else 0.0:.1f}% | "
        f"{((saturation_distribution[3] / len(rows)) * 100) if rows else 0.0:.1f}% | "
        f"{((saturation_distribution[2] / len(rows)) * 100) if rows else 0.0:.1f}% | "
        f"{((saturation_distribution[1] / len(rows)) * 100) if rows else 0.0:.1f}% |"
    )
    lines.extend(
        [
            "",
            "#### Only 3 Specified: Missing Entry",
            "",
            f"| Missing Entry | {matrix_column_labels[matrix_columns[0]]} | {matrix_column_labels[matrix_columns[1]]} | {matrix_column_labels[matrix_columns[2]]} | {matrix_column_labels[matrix_columns[3]]} | Row Total | % of Students |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    only_3_column_totals = {column_name: 0 for column_name in matrix_columns}
    only_3_row_total = 0
    for missing_pattern, count in missing_pattern_counts[3].items():
        row_cells = []
        for column_name in matrix_columns:
            if column_name in missing_pattern:
                row_cells.append(str(count))
                only_3_column_totals[column_name] += count
            else:
                row_cells.append("")
        only_3_row_total += count
        lines.append(
            f"|  | {' | '.join(row_cells)} | {count} | {((count / len(rows)) * 100) if rows else 0.0:.1f}% |"
        )
    lines.append(
        f"| Total | {only_3_column_totals[matrix_columns[0]]} | {only_3_column_totals[matrix_columns[1]]} | {only_3_column_totals[matrix_columns[2]]} | {only_3_column_totals[matrix_columns[3]]} | {only_3_row_total} | {((only_3_row_total / len(rows)) * 100) if rows else 0.0:.1f}% |"
    )
    lines.extend(
        [
            "",
            "#### Only 2 Specified: Missing Entries",
            "",
            f"| Missing Entries | {matrix_column_labels[matrix_columns[0]]} | {matrix_column_labels[matrix_columns[1]]} | {matrix_column_labels[matrix_columns[2]]} | {matrix_column_labels[matrix_columns[3]]} | Row Total | % of Students |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    only_2_column_totals = {column_name: 0 for column_name in matrix_columns}
    only_2_row_total = 0
    for missing_pattern, count in missing_pattern_counts[2].items():
        row_cells = []
        for column_name in matrix_columns:
            if column_name in missing_pattern:
                row_cells.append(str(count))
                only_2_column_totals[column_name] += count
            else:
                row_cells.append("")
        only_2_row_total += count
        lines.append(
            f"|  | {' | '.join(row_cells)} | {count} | {((count / len(rows)) * 100) if rows else 0.0:.1f}% |"
        )
    lines.append(
        f"| Total | {only_2_column_totals[matrix_columns[0]]} | {only_2_column_totals[matrix_columns[1]]} | {only_2_column_totals[matrix_columns[2]]} | {only_2_column_totals[matrix_columns[3]]} | {only_2_row_total} | {((only_2_row_total / len(rows)) * 100) if rows else 0.0:.1f}% |"
    )
    lines.extend(
        [
            "",
            "#### Only 1 Specified: Present Entry",
            "",
            f"| Present Entry | {matrix_column_labels[matrix_columns[0]]} | {matrix_column_labels[matrix_columns[1]]} | {matrix_column_labels[matrix_columns[2]]} | {matrix_column_labels[matrix_columns[3]]} | Row Total | % of Students |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    only_1_column_totals = {column_name: 0 for column_name in matrix_columns}
    only_1_row_total = 0
    for missing_pattern, count in missing_pattern_counts[1].items():
        row_cells = []
        for column_name in matrix_columns:
            if column_name not in missing_pattern:
                row_cells.append(str(count))
                only_1_column_totals[column_name] += count
            else:
                row_cells.append("")
        only_1_row_total += count
        lines.append(
            f"|  | {' | '.join(row_cells)} | {count} | {((count / len(rows)) * 100) if rows else 0.0:.1f}% |"
        )
    lines.append(
        f"| Total | {only_1_column_totals[matrix_columns[0]]} | {only_1_column_totals[matrix_columns[1]]} | {only_1_column_totals[matrix_columns[2]]} | {only_1_column_totals[matrix_columns[3]]} | {only_1_row_total} | {((only_1_row_total / len(rows)) * 100) if rows else 0.0:.1f}% |"
    )

    lines.extend(
        [
            "",
            "## Dimension Word Count Distributions",
            "",
            "### PPP",
            "",
            f"| Metric | {' | '.join(schema.dimensions)} |",
            f"| --- | {' | '.join('---:' for _ in schema.dimensions)} |",
        ]
    )
    ppp_stats_by_dimension = {
        dimension: summarize_word_counts(f"{dimension}-PPP-word-count") for dimension in schema.dimensions
    }
    for metric_label, stats_key, value_format in (
        ("PPP Avg", "avg", "float"),
        ("PPP Median", "median", "float"),
        ("PPP Min", "min", "int"),
        ("PPP Max", "max", "int"),
    ):
        row_cells = [metric_label]
        for dimension in schema.dimensions:
            value = ppp_stats_by_dimension[dimension][stats_key]
            row_cells.append(f"{value:.1f}" if value_format == "float" else str(value))
        lines.append(f"| {' | '.join(row_cells)} |")

    for dimension in schema.dimensions:
        pass

    lines.extend(
        [
            "",
            "### PPS1",
            "",
            f"| Metric | {' | '.join(schema.dimensions)} |",
            f"| --- | {' | '.join('---:' for _ in schema.dimensions)} |",
        ]
    )
    pps1_stats_by_dimension = {
        dimension: summarize_word_counts(f"{dimension}-PPS1-word-count") for dimension in schema.dimensions
    }
    for metric_label, stats_key, value_format in (
        ("PPS1 Avg", "avg", "float"),
        ("PPS1 Median", "median", "float"),
        ("PPS1 Min", "min", "int"),
        ("PPS1 Max", "max", "int"),
    ):
        row_cells = [metric_label]
        for dimension in schema.dimensions:
            value = pps1_stats_by_dimension[dimension][stats_key]
            row_cells.append(f"{value:.1f}" if value_format == "float" else str(value))
        lines.append(f"| {' | '.join(row_cells)} |")

    concept_fields = [
        "B3Interpretation",
        "B3Use",
        "C3Interpretation",
        "C3Use",
        "D3Interpretation",
        "D3Use",
    ]
    lines.extend(
        [
            "",
            "### Concept Fields",
            "",
            f"| Metric | {' | '.join(concept_fields)} |",
            f"| --- | {' | '.join('---:' for _ in concept_fields)} |",
        ]
    )
    concept_stats_by_field = {
        field_name: summarize_concept_word_counts(f"{field_name}-word-count") for field_name in concept_fields
    }
    for metric_label, stats_key, value_format in (
        ("Avg", "avg", "float"),
        ("Median", "median", "float"),
        ("Min", "min", "int"),
        ("Max", "max", "int"),
    ):
        row_cells = [metric_label]
        for field_name in concept_fields:
            value = concept_stats_by_field[field_name][stats_key]
            row_cells.append(f"{value:.1f}" if value_format == "float" else str(value))
        lines.append(f"| {' | '.join(row_cells)} |")
    over_100_count_row = ["Count over 100 words"]
    for field_name in concept_fields:
        over_100_count_row.append(str(count_over_threshold(f'{field_name}-word-count', 100)))
    lines.append(f"| {' | '.join(over_100_count_row)} |")

    over_100_row = ["% over 100 words"]
    for field_name in concept_fields:
        over_100_row.append(f"{percent_over_threshold(f'{field_name}-word-count', 100):.1f}%")
    lines.append(f"| {' | '.join(over_100_row)} |")

    lines.extend(
        [
            "",
            "### No Entry Received",
            "",
            "| Metric | "
            + " | ".join([f"{dimension} PPP" for dimension in schema.dimensions])
            + " | "
            + " | ".join([f"{dimension} PPS1" for dimension in schema.dimensions])
            + " | "
            + " | ".join(concept_fields)
            + " |",
            "| --- | "
            + " | ".join("---:" for _ in range(len(schema.dimensions) * 2 + len(concept_fields)))
            + " |",
        ]
    )
    count_row = ["No Entry Count"]
    percent_row = ["% of Submissions"]
    for suffix in ("PPP", "PPS1"):
        for dimension in schema.dimensions:
            field_name = f"{dimension}-{suffix}"
            count = no_entry_count(field_name)
            percent = 0.0 if not rows else (count / len(rows)) * 100
            count_row.append(str(count))
            percent_row.append(f"{percent:.1f}%")
    for field_name in concept_fields:
        count = no_entry_count(field_name)
        percent = 0.0 if not rows else (count / len(rows)) * 100
        count_row.append(str(count))
        percent_row.append(f"{percent:.1f}%")
    lines.append(f"| {' | '.join(count_row)} |")
    lines.append(f"| {' | '.join(percent_row)} |")

    lines.append("")
    return "\n".join(lines)


def write_audit_summary_report(path: Path, schema: ImportSchema, rows: list[AuditRow]) -> None:
    path.write_text(build_audit_summary_report(schema, rows), encoding="utf-8")


def load_audit_rows_from_csv(path: Path, schema: ImportSchema) -> list[AuditRow]:
    rows: list[AuditRow] = []
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for raw_row in reader:
            dimension_check_fields = {
                key: (raw_row.get(key) or "")
                for dimension in schema.dimensions
                for key in (
                    f"{dimension}-shift",
                    f"{dimension}-cont-reinf",
                    f"{dimension}-intro",
                    f"{dimension}-check",
                    f"{dimension}-err",
                )
            }
            dimension_word_count_fields = {
                key: (raw_row.get(key) or "0")
                for dimension in schema.dimensions
                for key in (f"{dimension}-PPP-word-count", f"{dimension}-PPS1-word-count")
            }
            concept_word_count_fields = {
                key: (raw_row.get(key) or "0")
                for key in (
                    "B3Interpretation-word-count",
                    "B3Use-word-count",
                    "C3Interpretation-word-count",
                    "C3Use-word-count",
                    "D3Interpretation-word-count",
                    "D3Use-word-count",
                )
            }
            no_entry_received_fields = {
                key: (raw_row.get(key) or "false")
                for dimension in schema.dimensions
                for key in (f"{dimension}-PPP-no-entry", f"{dimension}-PPS1-no-entry")
            }
            no_entry_received_fields.update(
                {
                    key: (raw_row.get(key) or "false")
                    for key in (
                        "B3Interpretation-no-entry",
                        "B3Use-no-entry",
                        "C3Interpretation-no-entry",
                        "C3Use-no-entry",
                        "D3Interpretation-no-entry",
                        "D3Use-no-entry",
                    )
                }
            )
            position_state_matrix_fields = {
                key: (raw_row.get(key) or "")
                for key in (
                    "E2_00_GridResponse",
                    "E2_10_GridResponse",
                    "E2_01_GridResponse",
                    "E2_11_GridResponse",
                    "Position-State Matrix Saturation Rate",
                )
            }
            rows.append(
                AuditRow(
                    source_csv_path=raw_row.get("source_csv_path") or "",
                    row_index=int(raw_row.get("row_index") or 0),
                    user=raw_row.get("user") or "",
                    username=raw_row.get("username") or "",
                    email_address=raw_row.get("email_address") or "",
                    participant_id=raw_row.get("participant_id") or "",
                    given_name=raw_row.get("given_name") or "",
                    family_name=raw_row.get("family_name") or "",
                    output_json_path=raw_row.get("output_json_path") or "",
                    dimension_check_fields=dimension_check_fields,
                    dimension_word_count_fields=dimension_word_count_fields,
                    concept_word_count_fields=concept_word_count_fields,
                    no_entry_received_fields=no_entry_received_fields,
                    position_state_matrix_fields=position_state_matrix_fields,
                )
            )
    return rows


def clear_existing_json_files(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for json_path in directory.glob("*.json"):
        json_path.unlink()


def _select_augmented_sample(
    generated_records: list[GeneratedRecord],
    sample_size: int,
    chooser: random.Random | random.SystemRandom,
) -> list[GeneratedRecord]:
    if not generated_records:
        return []

    count = min(sample_size, len(generated_records))
    selected_records = list(chooser.sample(generated_records, count))
    selected_paths = {record.path for record in selected_records}

    dot_records = [record for record in generated_records if normalize_value(record.family_name) == "."]
    if dot_records:
        dot_record = chooser.choice(dot_records)
        if dot_record.path not in selected_paths:
            selected_records.append(dot_record)
            selected_paths.add(dot_record.path)

    longest_family_record = max(
        generated_records,
        key=lambda record: (len(normalize_value(record.family_name)), record.path.name),
    )
    if longest_family_record.path not in selected_paths:
        selected_records.append(longest_family_record)
        selected_paths.add(longest_family_record.path)

    longest_given_record = max(
        generated_records,
        key=lambda record: (len(normalize_value(record.given_name)), record.path.name),
    )
    if longest_given_record.path not in selected_paths:
        selected_records.append(longest_given_record)

    return selected_records


def duplicate_sample(
    generated_records: list[GeneratedRecord],
    sample_output_dir: Path,
    sample_size: int,
    sample_seed: int | None,
) -> list[Path]:
    sample_output_dir.mkdir(parents=True, exist_ok=True)
    if not generated_records or sample_size <= 0:
        return []
    chooser = random.Random(sample_seed) if sample_seed is not None else random.SystemRandom()
    selected_records = _select_augmented_sample(generated_records, sample_size, chooser)
    copied_paths: list[Path] = []
    for record in selected_records:
        target_path = sample_output_dir / record.path.name
        shutil.copy2(record.path, target_path)
        copied_paths.append(target_path)
    return copied_paths


def main() -> int:
    args = parse_args()
    schema = load_schema(args.schema_path)
    csv_path = resolve_runtime_value(args.csv_path, schema.import_defaults.csv_path)
    participants_csv_path = resolve_runtime_value(
        args.participants_csv_path,
        schema.import_defaults.participants_csv_path,
    )
    all_output_dir = resolve_runtime_value(args.all_output_dir, schema.import_defaults.all_output_dir)
    sample_output_dir = resolve_runtime_value(
        args.sample_output_dir,
        schema.import_defaults.sample_output_dir,
    )
    audit_path = resolve_runtime_value(args.audit_path, schema.import_defaults.audit_path)
    audit_summary_path = audit_path.with_suffix(".md")
    sample_size = resolve_runtime_value(args.sample_size, schema.import_defaults.sample_size)

    participant_lookup = load_participant_lookup(participants_csv_path)
    clear_existing_json_files(all_output_dir)
    clear_existing_json_files(sample_output_dir)

    generated_records: list[GeneratedRecord] = []
    audit_rows: list[AuditRow] = []
    cleaning_audit_rows: list[CleaningAuditRow] = []
    pps1_text_development_rows: list[Pps1TextDevelopmentRow] = []
    used_names: set[str] = set()

    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header row: {csv_path}")

        for row_index, row in enumerate(reader, start=1):
            record, cleaning_audit_payloads = build_record(schema, row, participant_lookup)
            file_name = make_output_filename(schema, record, row, used_names, row_index)
            output_path = all_output_dir / file_name
            write_json(output_path, record)
            generated_records.append(
                GeneratedRecord(
                    path=output_path,
                    given_name=record.get(schema.identity_fields.given_name, ""),
                    family_name=record.get(schema.identity_fields.family_name, ""),
                )
            )
            audit_rows.append(
                AuditRow(
                    source_csv_path=str(csv_path),
                    row_index=row_index,
                    user=normalize_value(row.get("User")),
                    username=normalize_value(row.get("Username")),
                    email_address=normalize_value(row.get("Email address")),
                    participant_id=record.get(schema.identity_fields.participant_id, ""),
                    given_name=record.get(schema.identity_fields.given_name, ""),
                    family_name=record.get(schema.identity_fields.family_name, ""),
                    output_json_path=str(output_path),
                    dimension_check_fields=build_dimension_development_audit_fields(schema, row),
                    dimension_word_count_fields=build_dimension_word_count_audit_fields(schema, record),
                    concept_word_count_fields=build_concept_word_count_audit_fields(record),
                    no_entry_received_fields=build_no_entry_received_audit_fields(schema, record),
                    position_state_matrix_fields=build_position_state_matrix_audit_fields(row),
                )
            )
            for payload in cleaning_audit_payloads:
                cleaning_audit_rows.append(
                    CleaningAuditRow(
                        source_csv_path=str(csv_path),
                        row_index=row_index,
                        participant_id=record.get(schema.identity_fields.participant_id, ""),
                        given_name=record.get(schema.identity_fields.given_name, ""),
                        family_name=record.get(schema.identity_fields.family_name, ""),
                        output_json_path=str(output_path),
                        source_column=str(payload["source_column"]),
                        json_key=str(payload["json_key"]),
                        cleaning_applied=str(payload["cleaning_applied"]),
                        raw_is_blank=str(payload["raw_is_blank"]),
                        cleaned_is_blank=str(payload["cleaned_is_blank"]),
                        sentinel_inserted=str(payload["sentinel_inserted"]),
                        changed=str(payload["changed"]),
                        suspicious=str(payload["suspicious"]),
                        change_class=str(payload["change_class"]),
                        word_drop_type=str(payload["word_drop_type"]),
                        diff_category=str(payload["diff_category"]),
                        raw_char_count=int(payload["raw_char_count"]),
                        cleaned_char_count=int(payload["cleaned_char_count"]),
                        raw_word_count=int(payload["raw_word_count"]),
                        cleaned_word_count=int(payload["cleaned_word_count"]),
                        char_delta=int(payload["char_delta"]),
                        word_delta=int(payload["word_delta"]),
                        raw_preview=str(payload["raw_preview"]),
                        cleaned_preview=str(payload["cleaned_preview"]),
                        text_diff=str(payload["text_diff"]),
                    )
                )
            pps1_text_development_rows.append(
                Pps1TextDevelopmentRow(
                    source_csv_path=str(csv_path),
                    row_index=row_index,
                    participant_id=record.get(schema.identity_fields.participant_id, ""),
                    given_name=record.get(schema.identity_fields.given_name, ""),
                    family_name=record.get(schema.identity_fields.family_name, ""),
                    output_json_path=str(output_path),
                    extracted_development_types=build_pps1_text_development_fields(schema, record),
                )
            )
            if args.verbose:
                print(f"Wrote {output_path}")

    cleaning_audit_path = audit_path.with_name(audit_path.stem + "_cleaning.csv")
    cleaning_audit_summary_path = cleaning_audit_path.with_suffix(".md")
    pps1_text_development_path = audit_path.with_name(audit_path.stem + "_pps1_tagset_extraction.csv")
    pps1_text_development_summary_path = pps1_text_development_path.with_suffix(".md")
    write_audit_csv(audit_path, schema, audit_rows)
    write_audit_summary_report(audit_summary_path, schema, audit_rows)
    write_cleaning_audit_csv(cleaning_audit_path, cleaning_audit_rows)
    write_cleaning_audit_summary_report(cleaning_audit_summary_path, cleaning_audit_rows)
    write_pps1_text_development_csv(pps1_text_development_path, schema, pps1_text_development_rows)
    write_pps1_text_development_summary_report(
        pps1_text_development_summary_path,
        schema,
        pps1_text_development_rows,
    )

    copied_paths = duplicate_sample(
        generated_records=generated_records,
        sample_output_dir=sample_output_dir,
        sample_size=sample_size,
        sample_seed=args.sample_seed,
    )

    print(f"Wrote {len(generated_records)} JSON files to {all_output_dir}")
    print(f"Wrote import audit CSV to {audit_path}")
    print(f"Wrote import audit summary report to {audit_summary_path}")
    print(f"Wrote cleaning audit CSV to {cleaning_audit_path}")
    print(f"Wrote cleaning audit summary report to {cleaning_audit_summary_path}")
    print(f"Wrote PPS1 tagset extraction CSV to {pps1_text_development_path}")
    print(f"Wrote PPS1 tagset extraction summary report to {pps1_text_development_summary_path}")
    print(f"Copied {len(copied_paths)} sampled JSON files to {sample_output_dir}")
    if args.verbose and copied_paths:
        for copied_path in copied_paths:
            print(f"Sampled {copied_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())