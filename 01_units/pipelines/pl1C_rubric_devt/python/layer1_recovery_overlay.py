#!/usr/bin/env python3
"""Layer 1 recovery-indicator validation and effective-status overlay scaffold.

This module is intentionally standalone and not yet wired into existing Layer 1
execution recipes. It provides a deterministic contract for:

1. validating recovery sibling registry rows
2. validating recovery allowlist CSV rows
3. computing recovery/effective status overlays on scored Layer 1 rows
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REQUIRED_ALLOWLIST_COLUMNS = {
    "component_id",
    "parent_indicator_id",
    "submission_id",
    "recovery_indicator_id",
    "reason_code",
    "added_by",
    "added_at_utc",
    "expires_at_utc",
    "active",
}


def parse_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "active"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "inactive"}:
        return False
    return default


def parse_utc_timestamp(value: str) -> datetime:
    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("timestamp is blank")
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_recovery_allowlist_csv(csv_path: str) -> list[dict[str, str]]:
    path = Path(csv_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Recovery allowlist CSV not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Recovery allowlist CSV is missing header row")
        missing_columns = REQUIRED_ALLOWLIST_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            missing_display = ", ".join(sorted(missing_columns))
            raise ValueError(f"Recovery allowlist CSV missing required columns: {missing_display}")
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            rows.append({key: str(raw_row.get(key, "") or "").strip() for key in reader.fieldnames})
    return rows


def load_registry_rows_from_json(json_path: str) -> list[dict[str, object]]:
    path = Path(json_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Registry JSON not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(row) for row in payload if isinstance(row, Mapping)]
    if isinstance(payload, Mapping):
        if isinstance(payload.get("rows"), list):
            return [dict(row) for row in payload["rows"] if isinstance(row, Mapping)]
    raise ValueError("Registry JSON must be a list of row objects or an object with a 'rows' list")


def load_scored_rows_csv(csv_path: str) -> list[dict[str, str]]:
    path = Path(csv_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Scored CSV not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Scored CSV is missing header row")
        rows = [{key: str(raw_row.get(key, "") or "").strip() for key in reader.fieldnames} for raw_row in reader]
    return rows


def normalize_registry_indicator_kind(row: Mapping[str, object]) -> str:
    return str(row.get("indicator_kind", "primary") or "primary").strip().lower()


def validate_recovery_registry_rows(
    registry_rows: list[dict[str, object]],
    *,
    require_active_parent: bool = True,
) -> list[str]:
    errors: list[str] = []
    primary_by_component_and_indicator: dict[tuple[str, str], dict[str, object]] = {}

    for row in registry_rows:
        component_id = str(row.get("component_id", "") or "").strip()
        indicator_id = str(row.get("indicator_id", "") or "").strip()
        if not component_id or not indicator_id:
            continue
        if normalize_registry_indicator_kind(row) != "recovery":
            primary_by_component_and_indicator[(component_id, indicator_id)] = row

    for index, row in enumerate(registry_rows, start=1):
        if normalize_registry_indicator_kind(row) != "recovery":
            continue
        row_label = f"registry row {index}"
        component_id = str(row.get("component_id", "") or "").strip()
        indicator_id = str(row.get("indicator_id", "") or "").strip()
        sibling_of = str(row.get("sibling_of_indicator_id", "") or "").strip()

        if not indicator_id:
            errors.append(f"{row_label}: recovery row missing indicator_id")
        if not component_id:
            errors.append(f"{row_label}: recovery row missing component_id")
        if not sibling_of:
            errors.append(f"{row_label}: recovery row missing sibling_of_indicator_id")
            continue

        parent_row = primary_by_component_and_indicator.get((component_id, sibling_of))
        if parent_row is None:
            errors.append(
                f"{row_label}: sibling_of_indicator_id '{sibling_of}' does not reference a primary indicator in component '{component_id}'"
            )
        elif require_active_parent and str(parent_row.get("status", "active") or "active").strip().lower() != "active":
            errors.append(f"{row_label}: sibling primary indicator '{sibling_of}' is not active")

        recovery_mode = str(row.get("recovery_mode", "") or "").strip()
        if recovery_mode and recovery_mode != "manual_allowlist":
            errors.append(f"{row_label}: unsupported recovery_mode '{recovery_mode}'")

        recovery_precedence = str(row.get("recovery_precedence", "") or "").strip()
        if recovery_precedence and recovery_precedence != "force_present":
            errors.append(f"{row_label}: unsupported recovery_precedence '{recovery_precedence}'")

        row_active = str(row.get("status", "active") or "active").strip().lower() == "active"
        recovery_list_ref = str(row.get("recovery_list_ref", "") or "").strip()
        if row_active and not recovery_list_ref:
            errors.append(f"{row_label}: active recovery row missing recovery_list_ref")

    return errors


def validate_recovery_allowlist_rows(
    allowlist_rows: list[dict[str, str]],
    *,
    known_submission_ids: set[str],
    known_parent_indicator_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    active_seen_keys: set[tuple[str, str, str]] = set()

    for index, row in enumerate(allowlist_rows, start=1):
        row_label = f"allowlist row {index}"
        component_id = str(row.get("component_id", "") or "").strip()
        parent_indicator_id = str(row.get("parent_indicator_id", "") or "").strip()
        submission_id = str(row.get("submission_id", "") or "").strip()
        active = parse_bool(row.get("active", ""), default=False)

        if not component_id:
            errors.append(f"{row_label}: missing component_id")
        if not parent_indicator_id:
            errors.append(f"{row_label}: missing parent_indicator_id")
        if not submission_id:
            errors.append(f"{row_label}: missing submission_id")

        if not str(row.get("added_by", "") or "").strip():
            errors.append(f"{row_label}: missing added_by")

        added_at_utc = str(row.get("added_at_utc", "") or "").strip()
        try:
            parse_utc_timestamp(added_at_utc)
        except ValueError:
            errors.append(f"{row_label}: invalid added_at_utc '{added_at_utc}'")

        expires_at_utc = str(row.get("expires_at_utc", "") or "").strip()
        if expires_at_utc:
            try:
                parse_utc_timestamp(expires_at_utc)
            except ValueError:
                errors.append(f"{row_label}: invalid expires_at_utc '{expires_at_utc}'")

        if active:
            if submission_id and submission_id not in known_submission_ids:
                errors.append(f"{row_label}: unknown submission_id '{submission_id}'")
            if parent_indicator_id and parent_indicator_id not in known_parent_indicator_ids:
                errors.append(f"{row_label}: unknown parent_indicator_id '{parent_indicator_id}'")
            dedupe_key = (component_id, parent_indicator_id, submission_id)
            if dedupe_key in active_seen_keys:
                errors.append(
                    f"{row_label}: duplicate active allowlist key component_id='{component_id}', parent_indicator_id='{parent_indicator_id}', submission_id='{submission_id}'"
                )
            active_seen_keys.add(dedupe_key)

    return errors


def build_recovery_membership_index(
    allowlist_rows: list[dict[str, str]],
) -> dict[tuple[str, str, str], dict[str, str]]:
    index: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in allowlist_rows:
        if not parse_bool(row.get("active", ""), default=False):
            continue
        key = (
            str(row.get("component_id", "") or "").strip(),
            str(row.get("parent_indicator_id", "") or "").strip(),
            str(row.get("submission_id", "") or "").strip(),
        )
        index[key] = dict(row)
    return index


def score_recovery_indicator_membership(
    *,
    component_id: str,
    parent_indicator_id: str,
    submission_id: str,
    membership_index: Mapping[tuple[str, str, str], dict[str, str]],
    now_utc: str,
) -> tuple[str, dict[str, str]]:
    key = (component_id, parent_indicator_id, submission_id)
    entry = membership_index.get(key)
    if entry is None:
        return (
            "not_present",
            {
                "reason_code": "",
                "recovery_indicator_id": "",
                "flags": "recovery_list_miss",
            },
        )

    now_value = parse_utc_timestamp(now_utc)
    expires_at_utc = str(entry.get("expires_at_utc", "") or "").strip()
    if expires_at_utc:
        expires_value = parse_utc_timestamp(expires_at_utc)
        if expires_value < now_value:
            return (
                "not_present",
                {
                    "reason_code": str(entry.get("reason_code", "") or "").strip(),
                    "recovery_indicator_id": str(entry.get("recovery_indicator_id", "") or "").strip(),
                    "flags": "recovery_row_expired",
                },
            )

    return (
        "present",
        {
            "reason_code": str(entry.get("reason_code", "") or "").strip(),
            "recovery_indicator_id": str(entry.get("recovery_indicator_id", "") or "").strip(),
            "flags": "recovery_list_match",
        },
    )


def build_active_recovery_sibling_lookup(
    recovery_registry_rows: list[dict[str, object]],
) -> dict[tuple[str, str], dict[str, object]]:
    lookup: dict[tuple[str, str], dict[str, object]] = {}
    for row in recovery_registry_rows:
        if normalize_registry_indicator_kind(row) != "recovery":
            continue
        if str(row.get("status", "active") or "active").strip().lower() != "active":
            continue
        component_id = str(row.get("component_id", "") or "").strip()
        sibling_of = str(row.get("sibling_of_indicator_id", "") or "").strip()
        if component_id and sibling_of:
            lookup[(component_id, sibling_of)] = dict(row)
    return lookup


def merge_flags(existing_flags: str, new_flags: list[str]) -> str:
    merged: list[str] = []
    for candidate in [*str(existing_flags or "").split(","), *new_flags]:
        flag = candidate.strip()
        if not flag or flag == "none" or flag in merged:
            continue
        merged.append(flag)
    return ",".join(merged) if merged else "none"


def apply_recovery_overlay_to_l1_scores(
    scored_rows: list[dict[str, str]],
    *,
    recovery_registry_rows: list[dict[str, object]],
    membership_index: Mapping[tuple[str, str, str], dict[str, str]],
    now_utc: str,
) -> list[dict[str, str]]:
    recovery_lookup = build_active_recovery_sibling_lookup(recovery_registry_rows)
    overlay_rows: list[dict[str, str]] = []

    for row in scored_rows:
        output_row = dict(row)
        component_id = str(row.get("component_id", "") or "").strip()
        parent_indicator_id = str(row.get("indicator_id", "") or "").strip()
        submission_id = str(row.get("submission_id", "") or "").strip()
        primary_status = str(row.get("evidence_status", "not_present") or "not_present").strip() or "not_present"

        recovery_cfg = recovery_lookup.get((component_id, parent_indicator_id))
        recovery_flags: list[str] = []
        recovery_status = "not_present"
        recovery_indicator_id = ""
        recovery_reason_code = ""
        recovery_source_ref = ""

        if recovery_cfg is not None:
            recovery_source_ref = str(recovery_cfg.get("recovery_list_ref", "") or "").strip()
            recovery_status, recovery_meta = score_recovery_indicator_membership(
                component_id=component_id,
                parent_indicator_id=parent_indicator_id,
                submission_id=submission_id,
                membership_index=membership_index,
                now_utc=now_utc,
            )
            recovery_indicator_id = str(recovery_meta.get("recovery_indicator_id", "") or "").strip() or str(
                recovery_cfg.get("indicator_id", "") or ""
            ).strip()
            recovery_reason_code = str(recovery_meta.get("reason_code", "") or "").strip()
            recovery_meta_flags = str(recovery_meta.get("flags", "") or "").strip()
            if recovery_meta_flags:
                recovery_flags.extend(flag.strip() for flag in recovery_meta_flags.split(",") if flag.strip())
        
        if primary_status == "present":
            effective_status = "present"
        elif recovery_status == "present":
            effective_status = "present"
            recovery_flags.append("present_via_recovery")
        else:
            effective_status = "not_present"

        output_row["evidence_status_primary"] = primary_status
        output_row["evidence_status_recovery"] = recovery_status
        output_row["evidence_status_effective"] = effective_status
        output_row["recovery_applied"] = "true" if recovery_status == "present" else "false"
        output_row["recovery_indicator_id_used"] = recovery_indicator_id
        output_row["recovery_reason_code"] = recovery_reason_code
        output_row["recovery_source_ref"] = recovery_source_ref
        output_row["flags"] = merge_flags(str(row.get("flags", "") or ""), recovery_flags)
        overlay_rows.append(output_row)

    return overlay_rows


def write_rows_to_csv(rows: list[dict[str, str]], output_csv: str) -> None:
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Cannot write overlay CSV: rows are empty")
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and apply Layer 1 recovery-indicator overlays.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate registry rows and recovery allowlist rows")
    validate_parser.add_argument("--registry-json", required=True)
    validate_parser.add_argument("--allowlist-csv", required=True)
    validate_parser.add_argument("--scored-csv", required=True)

    overlay_parser = subparsers.add_parser("overlay", help="Apply recovery overlay to scored Layer 1 CSV rows")
    overlay_parser.add_argument("--registry-json", required=True)
    overlay_parser.add_argument("--allowlist-csv", required=True)
    overlay_parser.add_argument("--scored-csv", required=True)
    overlay_parser.add_argument("--output-csv", required=True)
    overlay_parser.add_argument("--now-utc", default=utc_now_iso())

    return parser.parse_args()


def run_validation(registry_rows: list[dict[str, object]], allowlist_rows: list[dict[str, str]], scored_rows: list[dict[str, str]]) -> list[str]:
    known_submission_ids = {str(row.get("submission_id", "") or "").strip() for row in scored_rows if row.get("submission_id")}
    known_parent_indicator_ids = {
        str(row.get("indicator_id", "") or "").strip()
        for row in registry_rows
        if normalize_registry_indicator_kind(row) != "recovery" and str(row.get("indicator_id", "") or "").strip()
    }
    registry_errors = validate_recovery_registry_rows(registry_rows)
    allowlist_errors = validate_recovery_allowlist_rows(
        allowlist_rows,
        known_submission_ids=known_submission_ids,
        known_parent_indicator_ids=known_parent_indicator_ids,
    )
    return [*registry_errors, *allowlist_errors]


def main() -> int:
    args = parse_args()
    registry_rows = load_registry_rows_from_json(args.registry_json)
    allowlist_rows = load_recovery_allowlist_csv(args.allowlist_csv)
    scored_rows = load_scored_rows_csv(args.scored_csv)

    validation_errors = run_validation(registry_rows, allowlist_rows, scored_rows)
    if validation_errors:
        for error in validation_errors:
            print(f"ERROR: {error}")
        return 1

    if args.command == "validate":
        print(
            f"OK: registry_rows={len(registry_rows)} allowlist_rows={len(allowlist_rows)} scored_rows={len(scored_rows)}"
        )
        return 0

    membership_index = build_recovery_membership_index(allowlist_rows)
    overlay_rows = apply_recovery_overlay_to_l1_scores(
        scored_rows,
        recovery_registry_rows=registry_rows,
        membership_index=membership_index,
        now_utc=args.now_utc,
    )
    write_rows_to_csv(overlay_rows, args.output_csv)
    print(args.output_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
