#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


DEFAULT_INPUT_ROOT = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/input"
)
DEFAULT_OUTPUT_PATH = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/JSON_reports/json_analysis_report.md"
)
PRIMARY_DATASET_DIR_NAMES = (
    "student_data_all_MINUS_SAS",
    "student_data_SAS_SecM",
    "student_data_SAS_SecO",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate markdown analysis reports over promoted PPS2 JSON files.",
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=DEFAULT_INPUT_ROOT,
        help="Root directory containing the promoted JSON dataset directories.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Markdown report path to write.",
    )
    return parser.parse_args()


def load_promoted_json_records(input_root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for dir_name in PRIMARY_DATASET_DIR_NAMES:
        directory = input_root / dir_name
        if not directory.exists():
            continue
        for json_path in sorted(directory.glob("*.json")):
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            records.append(
                {
                    "path": json_path,
                    "student_pool": payload.get("STUDENT_POOL", ""),
                }
            )
    return records


def build_file_count_analysis(records: list[dict[str, object]]) -> list[str]:
    counts_by_pool: dict[str, int] = defaultdict(int)
    for record in records:
        student_pool = str(record.get("student_pool") or "")
        if student_pool:
            counts_by_pool[student_pool] += 1

    lines = [
        "## File Count",
        "",
        "### All data",
        "",
        f"- Number of files: {len(records)}",
    ]

    for student_pool in sorted(counts_by_pool):
        lines.extend(
            [
                "",
                f"### {student_pool}",
                "",
                f"- Number of files: {counts_by_pool[student_pool]}",
            ]
        )

    return lines


def build_report(records: list[dict[str, object]]) -> str:
    lines = [
        "# JSON Analysis Report",
        "",
        "Primary promoted JSON datasets only: sample-overlay and buffer directories are excluded.",
        "",
    ]
    lines.extend(build_file_count_analysis(records))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    records = load_promoted_json_records(args.input_root)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(build_report(records), encoding="utf-8")
    print(f"Wrote JSON analysis report to {args.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())