from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from openpyxl import Workbook


IDENTITY_COLUMNS = ["Identifier", "Full name", "Email address"]
GRADE_COLUMN = "Grade"
FEEDBACK_COLUMN_CANDIDATES = ["Feedback comments", "Feedback"]
SEPARATOR_COLUMN = "."
WEIGHTED_SCORE_COLUMN = "submission_numeric_score"
WEIGHTED_DENOMINATOR_COLUMN = "submission_numeric_score_denominator"
AGGREGATED_FEEDBACK_COLUMN = "Feedback comments"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge component-level gradebook outputs for one assignment umbrella directory."
    )
    parser.add_argument(
        "--assignment-root",
        type=Path,
        required=True,
        help="Assignment umbrella directory, such as ./PPP or ./PPS1-umbrella.",
    )
    return parser.parse_args()


def load_pipeline_paths_config(assignment_dir: Path) -> dict[str, object] | None:
    candidates = [
        assignment_dir / "pipeline_paths.json",
        assignment_dir / "pipeline_paths.jsom",
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def resolve_output_csv_from_config(assignment_dir: Path, config: dict[str, object]) -> Path:
    layer4_prod = config.get("layer4_prod")
    if not isinstance(layer4_prod, dict):
        raise ValueError(f"Missing layer4_prod block in {assignment_dir / 'pipeline_paths.json'}")

    release = layer4_prod.get("release", {})
    if not isinstance(release, dict):
        release = {}
    iteration = str(release.get("iteration", "")).strip()
    filename_version = str(release.get("filename_version", "")).strip()

    populate = layer4_prod.get("populate_gradebook_export")
    if not isinstance(populate, dict):
        raise ValueError(
            f"Missing layer4_prod.populate_gradebook_export block in {assignment_dir / 'pipeline_paths.json'}"
        )

    output = populate.get("output")
    if not isinstance(output, dict):
        raise ValueError(
            f"Missing layer4_prod.populate_gradebook_export.output block in {assignment_dir / 'pipeline_paths.json'}"
        )

    def expand(value: str) -> str:
        expanded = value
        if iteration:
            expanded = expanded.replace("{iteration}", iteration)
        if filename_version:
            expanded = expanded.replace("{filename_version}", filename_version)
        return expanded

    base = expand(str(output.get("base", "") or ""))
    dir_part = expand(str(output.get("dir", "") or ""))
    run = expand(str(output.get("run", "") or ""))
    subdir = expand(str(output.get("run_relative_subdir", "") or ""))
    filename = expand(str(output.get("filename", "") or ""))
    if not filename:
        raise ValueError(
            f"Missing output.filename in layer4_prod.populate_gradebook_export.output for {assignment_dir.name}"
        )

    # pipeline_paths values are rooted under assignment_dir/01_pipelines/
    root = assignment_dir / "01_pipelines"
    csv_path = (root / base / dir_part / run / subdir / filename).resolve()
    return csv_path


def read_grade_rows(csv_path: Path) -> tuple[list[str], list[dict[str, str]], str]:
    if not csv_path.exists() or not csv_path.is_file():
        raise FileNotFoundError(f"Expected gradebook CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {csv_path}")
        rows = [dict(row) for row in reader]
        headers = list(reader.fieldnames)

    for column in IDENTITY_COLUMNS + [GRADE_COLUMN]:
        if column not in headers:
            raise ValueError(f"Missing required column '{column}' in {csv_path}")

    feedback_column = next((name for name in FEEDBACK_COLUMN_CANDIDATES if name in headers), "")
    if not feedback_column:
        raise ValueError(
            f"Missing feedback column in {csv_path}. Expected one of: {FEEDBACK_COLUMN_CANDIDATES}"
        )

    return headers, rows, feedback_column


def identity_key(row: dict[str, str]) -> tuple[str, str, str]:
    return tuple((row.get(column, "") or "").strip() for column in IDENTITY_COLUMNS)


def validate_and_index_identity_rows(
    source_name: str,
    rows: list[dict[str, str]],
) -> dict[tuple[str, str, str], dict[str, str]]:
    index: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = identity_key(row)
        if key in index:
            raise ValueError(f"Duplicate identity row detected in {source_name}: {key}")
        index[key] = row
    return index


def aggregate_feedback_for_identity(
    key: tuple[str, str, str],
    source_data: list[tuple[str, dict[tuple[str, str, str], dict[str, str]], str]],
) -> str:
    values: list[str] = []
    for _source_name, rows_by_id, feedback_column in source_data:
        text = (rows_by_id[key].get(feedback_column, "") or "").strip()
        if text:
            values.append(text)
    return "\n\n".join(values)


def load_component_weights(weights_path: Path) -> dict[str, str]:
    """Load component weights from JSON.

    Supported shapes:
    - {"PPS1E1": 0.2, "PPS1E21": 0.1}
    - {"weights": {"PPS1E1": 0.2, ...}}
    Keys may include or omit the "Weight_" prefix.
    """
    if not weights_path.is_file():
        return {}

    raw_text = weights_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return {}

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return {}

    if not isinstance(payload, dict):
        return {}

    candidate = payload.get("weights")
    if isinstance(candidate, dict):
        source = candidate
    else:
        source = payload

    result: dict[str, str] = {}
    for key, value in source.items():
        if not isinstance(key, str):
            continue
        normalized_key = key.removeprefix("Weight_")
        if isinstance(value, dict):
            nested_weight = value.get("weight")
            if nested_weight is None:
                continue
            result[normalized_key] = str(nested_weight)
        else:
            result[normalized_key] = str(value)
    return result


def _parse_float(value: str) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def weighted_sum_and_denominator(
    grade_values: list[str],
    weight_values: list[str],
) -> tuple[str, str]:
    total = 0.0
    denominator = 0.0
    terms = 0
    for grade_raw, weight_raw in zip(grade_values, weight_values):
        grade = _parse_float(grade_raw)
        weight = _parse_float(weight_raw)
        if grade is None or weight is None:
            continue
        total += grade * weight
        denominator += weight
        terms += 1

    if terms == 0:
        return "", ""
    return f"{total:.2f}", f"{denominator:.2f}"


def write_xlsx(
    output_path: Path,
    ordered_identity_keys: list[tuple[str, str, str]],
    source_data: list[tuple[str, dict[tuple[str, str, str], dict[str, str]], str]],
    component_weights: dict[str, str],
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "component_grades"

    header = list(IDENTITY_COLUMNS)
    duplicated_grade_headers: list[str] = []
    duplicated_weight_headers: list[str] = []
    for source_name, _rows_by_id, _feedback_column in source_data:
        header.append(f"Grade_{source_name}")
        header.append(f"Feedback_{source_name}")
        duplicated_weight_headers.append(f"Weight_{source_name}")
        duplicated_grade_headers.append(f"Grade_{source_name}")
    header.append(SEPARATOR_COLUMN)
    for weight_header, grade_header in zip(duplicated_weight_headers, duplicated_grade_headers):
        header.append(weight_header)
        header.append(grade_header)
    header.append(SEPARATOR_COLUMN)
    header.append(WEIGHTED_SCORE_COLUMN)
    header.append(WEIGHTED_DENOMINATOR_COLUMN)
    header.append(AGGREGATED_FEEDBACK_COLUMN)
    sheet.append(header)

    for key in ordered_identity_keys:
        row_out = list(key)
        duplicated_grade_values: list[str] = []
        duplicated_weight_values: list[str] = []
        for _source_name, rows_by_id, feedback_column in source_data:
            source_row = rows_by_id[key]
            grade_value = (source_row.get(GRADE_COLUMN, "") or "").strip()
            row_out.append(grade_value)
            row_out.append((source_row.get(feedback_column, "") or "").strip())
            duplicated_grade_values.append(grade_value)
            duplicated_weight_values.append(component_weights.get(_source_name, ""))
        row_out.append("")
        for weight_value, grade_value in zip(duplicated_weight_values, duplicated_grade_values):
            row_out.append(weight_value)
            row_out.append(grade_value)
        row_out.append("")
        weighted_score, weighted_denominator = weighted_sum_and_denominator(
            duplicated_grade_values,
            duplicated_weight_values,
        )
        row_out.append(weighted_score)
        row_out.append(weighted_denominator)
        row_out.append(aggregate_feedback_for_identity(key, source_data))
        sheet.append(row_out)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


def write_template_csv(
    output_path: Path,
    iteration: str,
    ordered_identity_keys: list[tuple[str, str, str]],
    source_data: list[tuple[str, dict[tuple[str, str, str], dict[str, str]], str]],
) -> None:
    """Write a template CSV with standard gradebook submission columns."""
    header = [
        "Identifier",
        "Full name",
        "Email address",
        "Status",
        "Grade",
        "Maximum Grade",
        "Grade can be changed",
        "Last modified (submission)",
        "Online text",
        "Last modified (grade)",
        "Feedback comments",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for key in ordered_identity_keys:
            row_out = {
                "Identifier": key[0],
                "Full name": key[1],
                "Email address": key[2],
                "Status": "",
                "Grade": "",
                "Maximum Grade": "",
                "Grade can be changed": "",
                "Last modified (submission)": "",
                "Online text": "",
                "Last modified (grade)": "",
                "Feedback comments": "",
            }
            writer.writerow(row_out)


def main() -> int:
    args = parse_args()
    assignment_root = args.assignment_root.resolve()
    if not assignment_root.is_dir():
        raise FileNotFoundError(f"Assignment root not found: {assignment_root}")

    token = assignment_root.name
    grades_release_dir = assignment_root / "04_grades_release"
    output_xlsx = grades_release_dir / f"{token}_component_grade_feedback_merged.xlsx"
    weights_path = grades_release_dir / f"{token}_weights.json"
    component_weights = load_component_weights(weights_path)

    assignment_dirs = sorted(
        [path for path in assignment_root.iterdir() if path.is_dir()],
        key=lambda path: path.name,
    )

    discovered: list[tuple[str, Path]] = []
    skipped_missing_csv: list[tuple[str, Path]] = []
    first_config: dict[str, object] | None = None
    first_iteration = ""
    
    for assignment_dir in assignment_dirs:
        config = load_pipeline_paths_config(assignment_dir)
        if config is None:
            continue
        if first_config is None:
            first_config = config
            layer4_prod = config.get("layer4_prod", {})
            if isinstance(layer4_prod, dict):
                release = layer4_prod.get("release", {})
                if isinstance(release, dict):
                    first_iteration = str(release.get("iteration", "")).strip()
        csv_path = resolve_output_csv_from_config(assignment_dir, config)
        if not csv_path.exists() or not csv_path.is_file():
            skipped_missing_csv.append((assignment_dir.name, csv_path))
            continue
        discovered.append((assignment_dir.name, csv_path))

    if not discovered:
        raise ValueError(f"No assignment subdirectories with pipeline_paths.json found under {assignment_root}")

    source_data: list[tuple[str, dict[tuple[str, str, str], dict[str, str]], str]] = []
    baseline_keys: set[tuple[str, str, str]] | None = None
    ordered_identity_keys: list[tuple[str, str, str]] = []

    for source_name, csv_path in discovered:
        _headers, rows, feedback_column = read_grade_rows(csv_path)
        rows_by_id = validate_and_index_identity_rows(source_name, rows)
        current_keys = set(rows_by_id.keys())

        if baseline_keys is None:
            baseline_keys = current_keys
            ordered_identity_keys = list(rows_by_id.keys())
        else:
            if current_keys != baseline_keys:
                missing_from_current = sorted(baseline_keys - current_keys)
                extra_in_current = sorted(current_keys - baseline_keys)
                raise ValueError(
                    "Identity precondition failed for source "
                    f"{source_name}. Missing keys: {missing_from_current[:3]} "
                    f"Extra keys: {extra_in_current[:3]}"
                )
            # Verify identity text values are identical across sources.
            for key in baseline_keys:
                baseline_identifier, baseline_name, baseline_email = key
                current_identifier, current_name, current_email = key
                if (
                    baseline_identifier != current_identifier
                    or baseline_name != current_name
                    or baseline_email != current_email
                ):
                    raise ValueError(f"Identity values mismatch for key {key} in source {source_name}")

        source_data.append((source_name, rows_by_id, feedback_column))

    write_xlsx(output_xlsx, ordered_identity_keys, source_data, component_weights)
    
    # Write template CSV with standard gradebook submission columns
    template_filename = f"{token}_Grades_iter{first_iteration}.csv"
    template_path = grades_release_dir / template_filename
    write_template_csv(template_path, first_iteration, ordered_identity_keys, source_data)

    print(f"ASST_ROOT: {assignment_root}")
    print(f"Grades release dir: {grades_release_dir}")
    print(f"Token: {token}")
    print(f"Iteration: {first_iteration}")
    print(f"Input sources found: {len(source_data)}")
    for source_name, csv_path in discovered:
        print(f"- {source_name}: {csv_path}")
    if skipped_missing_csv:
        print(f"Skipped missing CSVs: {len(skipped_missing_csv)}")
        for source_name, csv_path in skipped_missing_csv:
            print(f"- {source_name}: {csv_path}")
    print(f"Rows merged: {len(ordered_identity_keys)}")
    print(f"Output XLSX: {output_xlsx}")
    print(f"Template CSV: {template_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
