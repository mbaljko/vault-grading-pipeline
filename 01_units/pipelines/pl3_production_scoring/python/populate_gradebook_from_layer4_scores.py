#!/usr/bin/env python3
"""Populate an LMS gradebook CSV with Layer 4 submission scores.

This script copies scores from a Layer 4 wide-stitched output file into a
gradebook CSV by resolving each gradebook row to a canonical submission_id.

High-level flow:
1. Load score source rows from --scored-input (.csv or .xlsx).
2. Build identity indices from --canonical-population-input.
3. Resolve each gradebook row to submission_id using multiple signals.
4. Write a new gradebook CSV with populated grade (and optional feedback).

Inputs:
- --gradebook-input
  Destination-style CSV to populate. Must contain Identifier, Full name,
  Email address, and the configured grade column (default: Grade).
- --canonical-population-input
  Bridge table used for identity matching. Must contain submission_id,
  GW.Identifier, GW.Full name, User, and Username.
- --scored-input
  Layer 4 wide-stitched score file (.csv or .xlsx) with submission_id.
- --column-grade-for-upload
  Excel column letter (e.g. C) identifying the numeric score column in --scored-input.
- --column-feedback-comment
  Excel column letter (e.g. BS) identifying the feedback comment column in --scored-input.

Matching strategy (per gradebook row):
- Identifier -> GW.Identifier
- Full name -> GW.Full name and User (case/whitespace normalized)
- Email local part -> Username

Behavior and safeguards:
- If multiple canonical submission_ids match one gradebook row, execution
  fails with an ambiguity error.
- If no canonical match is found, the row is left unchanged.
- If a matched row has a score, the grade column is updated.
- If Feedback comments exists in both source and destination schemas, it is
  copied to the destination row.
- Source submission_ids with scores that never map to any gradebook row are
  emitted as ALERT lines on stderr after writing output.

Example:
	python populate_gradebook_from_layer4_scores.py \
		--gradebook-input path/to/Grades-tmp.csv \
		--canonical-population-input path/to/AP3_pipeline1A_canonical_population_table.csv \
		--scored-input path/to/RUN_AP3B_submission_Layer4_submission_scoring_output_v01-wide-stitched.xlsx \
		--output-file path/to/Grades-tmp-populated.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET




def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Populate a gradebook CSV Grade column from Layer 4 submission_numeric_score values."
	)
	parser.add_argument(
		"--gradebook-input",
		type=Path,
		required=True,
		help="Gradebook CSV to populate, such as Grades-tmp.csv.",
	)
	parser.add_argument(
		"--canonical-population-input",
		type=Path,
		required=True,
		help="Canonical population table that bridges gradebook identities to submission_id.",
	)
	parser.add_argument(
		"--scored-input",
		type=Path,
		required=True,
		help="Wide-stitched Layer 4 scoring file (.csv or .xlsx) containing submission_id.",
	)
	parser.add_argument(
		"--column-grade-for-upload",
		required=True,
		help="Excel column letter (e.g. C) for the numeric score column in --scored-input.",
	)
	parser.add_argument(
		"--column-feedback-comment",
		required=True,
		help="Excel column letter (e.g. BS) for the feedback comment column in --scored-input.",
	)
	parser.add_argument(
		"--output-file",
		type=Path,
		required=True,
		help="Destination CSV path.",
	)
	parser.add_argument(
		"--grade-column",
		default="Grade",
		help="Gradebook column to populate. Defaults to 'Grade'.",
	)
	return parser.parse_args()


def _normalized_field_lookup(fieldnames: list[str] | None) -> dict[str, str]:
	if not fieldnames:
		return {}
	return {name.strip().lower(): name for name in fieldnames if name}


def _require_column(normalized_fields: dict[str, str], column_name: str, file_path: Path) -> str:
	column = normalized_fields.get(column_name.strip().lower())
	if not column:
		raise ValueError(f"Expected column '{column_name}' in {file_path}")
	return column


def _normalize_text(value: str) -> str:
	collapsed = re.sub(r"\s+", " ", (value or "").strip().lower())
	return collapsed


def _cell_reference_to_index(cell_reference: str) -> int:
	column_letters = ""
	for character in cell_reference:
		if character.isalpha():
			column_letters += character.upper()
		else:
			break
	index = 0
	for character in column_letters:
		index = (index * 26) + (ord(character) - ord("A") + 1)
	return max(index - 1, 0)


def _xlsx_shared_strings(zip_file: ZipFile) -> list[str]:
	shared_strings_path = "xl/sharedStrings.xml"
	if shared_strings_path not in zip_file.namelist():
		return []

	namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
	root = ET.fromstring(zip_file.read(shared_strings_path))
	values: list[str] = []
	for string_item in root.findall("main:si", namespace):
		values.append("".join(text_node.text or "" for text_node in string_item.iterfind(".//main:t", namespace)))
	return values


def _xlsx_first_sheet_path(zip_file: ZipFile) -> str:
	workbook_namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
	rel_namespace = {"pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships"}
	workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
	relationships = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
	relationship_map = {
		rel.attrib["Id"]: rel.attrib["Target"]
		for rel in relationships.findall("pkgrel:Relationship", rel_namespace)
	}
	first_sheet = workbook.find("main:sheets/main:sheet", workbook_namespace)
	if first_sheet is None:
		raise ValueError("No worksheet found in XLSX workbook")
	relationship_id = first_sheet.attrib.get(
		"{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
	)
	if not relationship_id or relationship_id not in relationship_map:
		raise ValueError("Could not resolve first worksheet in XLSX workbook")
	return "xl/" + relationship_map[relationship_id].lstrip("/")


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str], namespace: dict[str, str]) -> str:
	cell_type = cell.attrib.get("t")
	if cell_type == "inlineStr":
		return "".join(text_node.text or "" for text_node in cell.iterfind(".//main:t", namespace))

	value = cell.findtext("main:v", default="", namespaces=namespace)
	if cell_type == "s" and value:
		return shared_strings[int(value)]
	if cell_type == "b":
		return "TRUE" if value == "1" else "FALSE"
	return value or ""


def iter_scored_rows(scored_input: Path) -> tuple[list[str], list[dict[str, str]]]:
	if scored_input.suffix.lower() == ".csv":
		with scored_input.open("r", encoding="utf-8-sig", newline="") as handle:
			reader = csv.DictReader(handle)
			fieldnames = list(reader.fieldnames or [])
			if not fieldnames:
				raise ValueError(f"No header row found in {scored_input}")
				return fieldnames, []
			return fieldnames, [dict(row) for row in reader]

	if scored_input.suffix.lower() != ".xlsx":
		raise ValueError(f"Unsupported scored input format for {scored_input}; expected .csv or .xlsx")

	namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
	with ZipFile(scored_input) as zip_file:
		shared_strings = _xlsx_shared_strings(zip_file)
		sheet_path = _xlsx_first_sheet_path(zip_file)
		sheet_root = ET.fromstring(zip_file.read(sheet_path))

	rows = sheet_root.findall(".//main:sheetData/main:row", namespace)
	if not rows:
		raise ValueError(f"No worksheet rows found in {scored_input}")

	parsed_rows: list[list[str]] = []
	max_columns = 0
	for row in rows:
		values_by_index: dict[int, str] = {}
		for cell in row.findall("main:c", namespace):
			cell_reference = cell.attrib.get("r", "")
			column_index = _cell_reference_to_index(cell_reference)
			values_by_index[column_index] = _xlsx_cell_value(cell, shared_strings, namespace)
		if values_by_index:
			row_values = [""] * (max(values_by_index) + 1)
			for column_index, value in values_by_index.items():
				row_values[column_index] = value
		else:
			row_values = []
		max_columns = max(max_columns, len(row_values))
		parsed_rows.append(row_values)

	parsed_rows = [row + ([""] * (max_columns - len(row))) for row in parsed_rows]
	fieldnames = parsed_rows[0]
	if not fieldnames:
		raise ValueError(f"No header row found in {scored_input}")

	data_rows: list[dict[str, str]] = []
	for row_values in parsed_rows[1:]:
		data_rows.append(
			{
				fieldnames[index]: row_values[index] if index < len(row_values) else ""
				for index in range(len(fieldnames))
			}
		)

	return fieldnames, data_rows


def _email_local_part(email_address: str) -> str:
	value = (email_address or "").strip().lower()
	if not value or "@" not in value:
		return ""
	return value.split("@", 1)[0].strip()


def load_source_lookup(
	scored_input: Path,
	grade_column_ref: str,
	feedback_column_ref: str,
) -> dict[str, dict[str, str]]:
	source_lookup: dict[str, dict[str, str]] = {}
	fieldnames, rows = iter_scored_rows(scored_input)
	normalized_fields = _normalized_field_lookup(fieldnames)
	submission_id_key = _require_column(normalized_fields, "submission_id", scored_input)

	grade_col_index = _cell_reference_to_index(grade_column_ref)
	if grade_col_index >= len(fieldnames):
		raise ValueError(
			f"--column-grade-for-upload '{grade_column_ref}' (index {grade_col_index}) is out of range for {scored_input}"
		)
	score_key = fieldnames[grade_col_index]

	feedback_col_index = _cell_reference_to_index(feedback_column_ref)
	feedback_key = fieldnames[feedback_col_index] if feedback_col_index < len(fieldnames) else None

	for row in rows:
		submission_id = (row.get(submission_id_key) or "").strip()
		if not submission_id:
			continue
		score_value = (row.get(score_key) or "").strip()
		feedback_value = (row.get(feedback_key) or "") if feedback_key else ""
		existing_value = source_lookup.get(submission_id)
		if existing_value is not None and existing_value.get("score", "") != score_value:
			raise ValueError(
				f"Conflicting submission_numeric_score values for submission_id {submission_id} in {scored_input}"
			)
		if existing_value is not None and existing_value.get("feedback_comments", "") != feedback_value:
			raise ValueError(
				f"Conflicting Feedback comments values for submission_id {submission_id} in {scored_input}"
			)
		source_lookup[submission_id] = {
			"score": score_value,
			"feedback_comments": feedback_value,
		}

	return source_lookup


def _add_index_value(index: dict[str, set[str]], key: str, submission_id: str) -> None:
	if key:
		index[key].add(submission_id)


def load_canonical_indices(canonical_input: Path) -> dict[str, dict[str, set[str]]]:
	indices = {
		"gw_identifier": defaultdict(set),
		"gw_full_name": defaultdict(set),
		"user": defaultdict(set),
		"username": defaultdict(set),
	}

	with canonical_input.open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.DictReader(handle)
		normalized_fields = _normalized_field_lookup(reader.fieldnames)
		submission_id_key = _require_column(normalized_fields, "submission_id", canonical_input)
		gw_identifier_key = _require_column(normalized_fields, "GW.Identifier", canonical_input)
		gw_full_name_key = _require_column(normalized_fields, "GW.Full name", canonical_input)
		user_key = _require_column(normalized_fields, "User", canonical_input)
		username_key = _require_column(normalized_fields, "Username", canonical_input)

		for row in reader:
			submission_id = (row.get(submission_id_key) or "").strip()
			if not submission_id:
				continue

			_add_index_value(
				indices["gw_identifier"],
				(row.get(gw_identifier_key) or "").strip(),
				submission_id,
			)
			_add_index_value(
				indices["gw_full_name"],
				_normalize_text(row.get(gw_full_name_key) or ""),
				submission_id,
			)
			_add_index_value(
				indices["user"],
				_normalize_text(row.get(user_key) or ""),
				submission_id,
			)
			_add_index_value(
				indices["username"],
				_normalize_text(row.get(username_key) or ""),
				submission_id,
			)

	return indices


def resolve_submission_id(
	grade_row: dict[str, str],
	gradebook_input: Path,
	indices: dict[str, dict[str, set[str]]],
	identifier_key: str,
	full_name_key: str,
	email_key: str,
) -> str:
	candidate_ids: set[str] = set()
	match_evidence: list[str] = []

	identifier_value = (grade_row.get(identifier_key) or "").strip()
	if identifier_value:
		matched = indices["gw_identifier"].get(identifier_value, set())
		if matched:
			candidate_ids.update(matched)
			match_evidence.append(f"Identifier={identifier_value}")

	full_name_value = _normalize_text(grade_row.get(full_name_key) or "")
	if full_name_value:
		for index_name in ("gw_full_name", "user"):
			matched = indices[index_name].get(full_name_value, set())
			if matched:
				candidate_ids.update(matched)
				match_evidence.append(f"Full name={grade_row.get(full_name_key, '')}")

	email_local_part = _normalize_text(_email_local_part(grade_row.get(email_key) or ""))
	if email_local_part:
		matched = indices["username"].get(email_local_part, set())
		if matched:
			candidate_ids.update(matched)
			match_evidence.append(f"Email local part={email_local_part}")

	if not candidate_ids:
		return ""
	if len(candidate_ids) > 1:
		raise ValueError(
			"Ambiguous canonical match for gradebook row in "
			f"{gradebook_input}: {match_evidence or ['<no evidence>']} -> {sorted(candidate_ids)}"
		)
	return next(iter(candidate_ids))


def populate_gradebook(
	gradebook_input: Path,
	canonical_input: Path,
	scored_input: Path,
	output_file: Path,
	grade_column: str,
	grade_column_ref: str,
	feedback_column_ref: str,
) -> tuple[int, list[tuple[str, str]]]:
	source_lookup = load_source_lookup(scored_input, grade_column_ref, feedback_column_ref)
	canonical_indices = load_canonical_indices(canonical_input)
	used_submission_ids: set[str] = set()

	with gradebook_input.open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.DictReader(handle)
		if not reader.fieldnames:
			raise ValueError(f"No CSV header found in {gradebook_input}")

		normalized_fields = _normalized_field_lookup(reader.fieldnames)
		identifier_key = _require_column(normalized_fields, "Identifier", gradebook_input)
		full_name_key = _require_column(normalized_fields, "Full name", gradebook_input)
		email_key = _require_column(normalized_fields, "Email address", gradebook_input)
		actual_grade_column = _require_column(normalized_fields, grade_column, gradebook_input)
		feedback_column = normalized_fields.get("feedback comments")

		fieldnames = list(reader.fieldnames)
		matched_rows = 0

		output_file.parent.mkdir(parents=True, exist_ok=True)
		with output_file.open("w", encoding="utf-8", newline="") as output_handle:
			writer = csv.DictWriter(output_handle, fieldnames=fieldnames)
			writer.writeheader()

			for row in reader:
				submission_id = resolve_submission_id(
					grade_row=row,
					gradebook_input=gradebook_input,
					indices=canonical_indices,
					identifier_key=identifier_key,
					full_name_key=full_name_key,
					email_key=email_key,
				)
				if not submission_id:
					writer.writerow({field: row.get(field, "") for field in fieldnames})
					continue

				used_submission_ids.add(submission_id)
				source_values = source_lookup.get(submission_id, {})
				score_value = source_values.get("score", "")
				if score_value:
					matched_rows += 1
					row[actual_grade_column] = score_value
				if feedback_column:
					row[feedback_column] = source_values.get("feedback_comments", "")

				writer.writerow({field: row.get(field, "") for field in fieldnames})

	alert_rows = sorted(
		[
			(submission_id, source_values.get("score", ""))
			for submission_id, source_values in source_lookup.items()
			if source_values.get("score", "") and submission_id not in used_submission_ids
		],
		key=lambda item: item[0],
	)
	return matched_rows, alert_rows


def main() -> int:
	args = parse_args()
	for input_path in (
		args.gradebook_input,
		args.canonical_population_input,
		args.scored_input,
	):
		if not input_path.is_file():
			print(f"Error: input file not found: {input_path}", file=sys.stderr)
			return 1

	try:
		matched_rows, alert_rows = populate_gradebook(
			gradebook_input=args.gradebook_input,
			canonical_input=args.canonical_population_input,
			scored_input=args.scored_input,
			output_file=args.output_file,
			grade_column=args.grade_column,
			grade_column_ref=args.column_grade_for_upload,
			feedback_column_ref=args.column_feedback_comment,
		)
	except ValueError as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	print(f"Wrote {args.output_file} ({matched_rows} grades populated)")
	for submission_id, score_value in alert_rows:
		print(
			f"ALERT: source grade with submission_id {submission_id} and submission_numeric_score {score_value} did not match any destination row",
			file=sys.stderr,
		)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())