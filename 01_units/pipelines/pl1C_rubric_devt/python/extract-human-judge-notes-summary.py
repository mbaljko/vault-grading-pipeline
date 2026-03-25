#!/usr/bin/env python3
"""Extract submission-level score and validation labels from panel reports.

The script can either read a single panel-report markdown file or scan a
diagnostics directory. When scanning a directory, it reads `I_<assessment>_all_panel_*`
reports first and then `I_<assessment>_Sec*_*_output_stitched.md` reports second,
so the stitched files act as a backfill source if rows are missing from the
aggregate panel reports.

Output columns:
- `source_panel`
- `component_id`
- `indicator_id`
- `submission_id`
- `<iteration>-score`: `P` for `present`, `N` for `not_present`
- `<iteration>-validation`: `TP`, `FP`, `TN`, or `FN` parsed from
  `human_judge_notes`
- `false_score`: echoes `FP` or `FN` when validation surfaced a false score
- `human_judge_notes_detail`: explanatory note text with the validation label removed

The iteration label is inferred from the input path when possible, e.g. `iter01`.
Use `--iteration-label` to override it explicitly.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import re
import sys
from pathlib import Path
from generate_rubric_and_manifest_from_indicator_registry import (
	apply_expression_template,
	apply_token_template,
	collect_markdown_tables as collect_registry_markdown_tables,
	expand_component_pattern,
	extract_rule_template,
	find_table_by_heading,
	resolve_component_block_lookup,
	resolve_local_slot_values,
)


ITERATION_RE = re.compile(r"\b(iter\d+)\b", re.IGNORECASE)
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
VALIDATION_LABEL_RE = re.compile(r"\b(TP|FP|TN|FN)\b", re.IGNORECASE)
SOURCE_FILE_RE = re.compile(r"^\s*-\s+Source file:\s+(.+?)\s*$")
PANEL_HEADING_RE = re.compile(r"^\s*#{1,6}\s*Panel\s+([ABC])\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Extract submission-level validation labels from panel reports."
	)
	input_group = parser.add_mutually_exclusive_group(required=True)
	input_group.add_argument(
		"--panel-report-file",
		type=Path,
		required=False,
		help="Path to a single panel report markdown file.",
	)
	input_group.add_argument(
		"--input-dir",
		type=Path,
		required=False,
		help="Directory containing aggregate and stitched panel reports.",
	)
	parser.add_argument(
		"--primary-glob",
		type=str,
		required=False,
		default="I_*_all_panel_*.md",
		help="Primary file glob used when scanning --input-dir.",
	)
	parser.add_argument(
		"--secondary-glob",
		type=str,
		required=False,
		default="I_*_Sec*_*_output_stitched.md",
		help="Secondary file glob used when scanning --input-dir.",
	)
	parser.add_argument(
		"--output-file",
		type=Path,
		required=False,
		help="Optional output markdown path. Defaults beside the input report.",
	)
	parser.add_argument(
		"--indicator-registry",
		type=Path,
		required=False,
		help="Optional indicator registry used to map indicators back to block_rule_id groups.",
	)
	parser.add_argument(
		"--iteration-label",
		type=str,
		required=False,
		help="Optional iteration label override, e.g. iter01.",
	)
	return parser.parse_args()


def parse_markdown_cells(line: str) -> list[str]:
	parts = [part.strip() for part in line.strip().split("|")]
	if parts and parts[0] == "":
		parts = parts[1:]
	if parts and parts[-1] == "":
		parts = parts[:-1]
	return parts


def is_markdown_separator_row(cells: list[str]) -> bool:
	if not cells:
		return False
	return all(bool(SEPARATOR_CELL_RE.match(cell.replace(" ", ""))) for cell in cells)


def escape_markdown_cell(value: str) -> str:
	return value.replace("|", "\\|").replace("\n", " ").strip()


def format_markdown_row(cells: list[str]) -> str:
	return "| " + " | ".join(escape_markdown_cell(cell) for cell in cells) + " |\n"


def quote_yaml_string(value: str) -> str:
	escaped = value.replace("\\", "\\\\").replace('"', '\\"')
	return f'"{escaped}"'


def render_yaml_frontmatter(
	output_path: Path,
	iteration_label: str,
	source_paths: list[Path],
	primary_count: int,
	secondary_count: int,
	registry_path: Path | None,
) -> str:
	lines = [
		"---\n",
		f"generated_at_utc: {quote_yaml_string(datetime.now(timezone.utc).isoformat(timespec='seconds'))}\n",
		"generator:\n",
		f"  script: {quote_yaml_string(str(Path(__file__).resolve()))}\n",
		"output_file:\n",
		f"  path: {quote_yaml_string(str(output_path))}\n",
		f"  name: {quote_yaml_string(output_path.name)}\n",
		f"iteration_label: {quote_yaml_string(iteration_label)}\n",
		"source_files:\n",
		f"  scanned: {len(source_paths)}\n",
		f"  primary_aggregate_count: {primary_count}\n",
		f"  secondary_stitched_count: {secondary_count}\n",
		"  paths:\n",
	]
	for source_path in source_paths:
		lines.append(f"    - {quote_yaml_string(str(source_path))}\n")
	if registry_path is not None:
		lines.extend(
			[
				"indicator_registry:\n",
				f"  path: {quote_yaml_string(str(registry_path))}\n",
			]
		)
	lines.append("---\n\n")
	return "".join(lines)


def collect_markdown_tables(markdown_text: str) -> list[list[list[str]]]:
	lines = markdown_text.splitlines()
	tables: list[list[list[str]]] = []
	index = 0
	while index < len(lines):
		if not lines[index].lstrip().startswith("|"):
			index += 1
			continue
		table_lines: list[list[str]] = []
		while index < len(lines) and lines[index].lstrip().startswith("|"):
			table_lines.append(parse_markdown_cells(lines[index]))
			index += 1
		if table_lines:
			tables.append(table_lines)
	return tables


def normalize_header_name(value: str) -> str:
	return value.strip().lower().replace("-", "_").replace(" ", "_")


def derive_iteration_label(input_path: Path, explicit_label: str | None) -> str:
	if explicit_label:
		return explicit_label.strip()
	for part in input_path.parts:
		match = ITERATION_RE.search(part)
		if match:
			return match.group(1).lower()
	match = ITERATION_RE.search(str(input_path))
	if match:
		return match.group(1).lower()
	return "iteration"


def default_output_path(input_path: Path, iteration_label: str) -> Path:
	return input_path.with_name(f"{input_path.stem}_human_judge_notes_summary_{iteration_label}.md")


def default_output_path_for_dir(input_dir: Path, iteration_label: str) -> Path:
	return input_dir / f"human_judge_notes_summary_{iteration_label}.md"


def map_score_label(evidence_status: str) -> str:
	normalized = evidence_status.strip().lower()
	if normalized == "present":
		return "P"
	if normalized == "not_present":
		return "N"
	return ""


def parse_validation_label(human_judge_notes: str) -> str:
	matches = {match.group(1).upper() for match in VALIDATION_LABEL_RE.finditer(human_judge_notes)}
	if not matches:
		return ""
	if len(matches) > 1:
		raise ValueError(
			f"Expected at most one validation label in human_judge_notes, found {sorted(matches)} in: {human_judge_notes!r}"
		)
	return next(iter(matches))


def parse_human_judge_notes_detail(human_judge_notes: str) -> str:
	validation_label = parse_validation_label(human_judge_notes)
	if not validation_label:
		return human_judge_notes.strip()
	detail = VALIDATION_LABEL_RE.sub("", human_judge_notes, count=1).strip()
	detail = re.sub(r"^[\s:;,.\-]+", "", detail)
	detail = re.sub(r"\s+", " ", detail)
	return detail.strip()


def derive_false_score_flag(validation_label: str) -> str:
	normalized = validation_label.strip().upper()
	if normalized in {"FP", "FN"}:
		return normalized
	return ""


def build_report_heading(output_filename: str, iteration_label: str) -> str:
	if iteration_label and iteration_label.lower() not in output_filename.lower():
		return f"{output_filename} ({iteration_label})"
	return output_filename


def build_indicator_reverse_lookup(registry_path: Path) -> dict[tuple[str, str], dict[str, str]]:
	tables = collect_registry_markdown_tables(registry_path)
	base_table = find_table_by_heading(tables, "base table")
	reuse_table = find_table_by_heading(tables, "reuse rule table")
	component_block_rule_table = find_table_by_heading(tables, "component block rule table")
	if base_table is None or reuse_table is None:
		return {}

	base_rows = list(base_table["rows"])
	reuse_rows = list(reuse_table["rows"])
	reuse_headers = set(reuse_table["headers"])
	base_by_template_id = {
		row.get("template_id", "").strip(): row for row in base_rows if row.get("template_id", "").strip()
	}
	base_by_local_slot = {
		row.get("local_slot", "").strip(): row for row in base_rows if row.get("local_slot", "").strip()
	}
	reverse_lookup: dict[tuple[str, str], dict[str, str]] = {}

	def register_mapping(component_id: str, indicator_id: str, block_rule_id: str, base_row: dict[str, str]) -> None:
		reverse_lookup[(component_id, indicator_id)] = {
			"block_rule_id": block_rule_id,
			"template_id": base_row.get("template_id", "").strip(),
			"sbo_short_description": base_row.get("sbo_short_description", "").strip(),
		}

	if {"indicator_id", "component_id"}.issubset(reuse_headers):
		for reuse_row in reuse_rows:
			template_id = reuse_row.get("template_id", "").strip()
			local_slot = reuse_row.get("local_slot", "").strip()
			base_row = base_by_template_id.get(template_id) if template_id else None
			if base_row is None and local_slot:
				base_row = base_by_local_slot.get(local_slot)
			if base_row is None:
				continue
			component_id = reuse_row.get("component_id", "").strip()
			indicator_id = reuse_row.get("indicator_id", "").strip()
			if component_id and indicator_id:
				register_mapping(
					component_id,
					indicator_id,
					reuse_row.get("rule_id", "").strip() or template_id or local_slot,
					base_row,
				)
		return reverse_lookup

	if {
		"template_group",
		"applies_to_component_pattern",
		"component_block_rule",
		"local_slot_source",
		"indicator_id_format",
	}.issubset(reuse_headers):
		if component_block_rule_table is None:
			return reverse_lookup
		component_block_lookup = resolve_component_block_lookup(list(component_block_rule_table["rows"]))
		for reuse_row in reuse_rows:
			template_group = reuse_row.get("template_group", "").strip()
			component_pattern = reuse_row.get("applies_to_component_pattern", "").strip()
			block_rule_id = reuse_row.get("component_block_rule", "").strip()
			local_slot_source = reuse_row.get("local_slot_source", "").strip()
			indicator_id_format = reuse_row.get("indicator_id_format", "").strip()
			matching_base_rows = [
				row for row in base_rows if row.get("template_id", "").strip().startswith(f"{template_group}_")
			]
			for component_id, template_values in expand_component_pattern(component_pattern):
				component_block = component_block_lookup.get((block_rule_id, component_id))
				if component_block is None:
					continue
				for base_row in matching_base_rows:
					expression_values = {
						**template_values,
						**resolve_local_slot_values(base_row, local_slot_source),
						"component_block": component_block,
					}
					indicator_id = apply_expression_template(indicator_id_format, expression_values)
					register_mapping(component_id, indicator_id, f"{block_rule_id}_{component_block}", base_row)
		return reverse_lookup

	if {"template_group", "applies_to_component_pattern", "indicator_id_rule"}.issubset(reuse_headers):
		for reuse_row in reuse_rows:
			template_group = reuse_row.get("template_group", "").strip()
			component_pattern = reuse_row.get("applies_to_component_pattern", "").strip()
			indicator_id_template = extract_rule_template(reuse_row.get("indicator_id_rule", "").strip())
			matching_base_rows = [
				row for row in base_rows if row.get("template_id", "").strip().startswith(f"{template_group}_")
			]
			for component_id, template_values in expand_component_pattern(component_pattern):
				for base_row in matching_base_rows:
					indicator_id = apply_token_template(
						indicator_id_template,
						{**template_values, "local_slot": base_row.get("local_slot", "").strip()},
					)
					register_mapping(
						component_id,
						indicator_id,
						reuse_row.get("rule_id", "").strip() or template_group,
						base_row,
					)
	return reverse_lookup


def enrich_records_with_block_rule(
	records: list[dict[str, str]], indicator_lookup: dict[tuple[str, str], dict[str, str]]
) -> list[dict[str, str]]:
	for record in records:
		lookup = indicator_lookup.get((record["component_id"], record["indicator_id"]))
		record["block_rule_id"] = lookup.get("block_rule_id", "") if lookup else ""
		record["template_id"] = lookup.get("template_id", "") if lookup else ""
		record["sbo_short_description"] = lookup.get("sbo_short_description", "") if lookup else ""
	return records


def block_rule_sort_key(block_rule_id: str) -> tuple[int, str]:
	normalized = block_rule_id.strip().lower()
	if normalized.startswith("core"):
		return (0, normalized)
	if normalized.startswith("adv"):
		return (1, normalized)
	if "_core_" in normalized:
		return (0, normalized)
	if "_adv_" in normalized:
		return (1, normalized)
	return (2, normalized)


def template_sort_key(template_id: str) -> tuple[int, str]:
	normalized = template_id.strip().lower()
	if "_core_" in normalized:
		return (0, normalized)
	if "_adv_" in normalized:
		return (1, normalized)
	return (2, normalized)


def source_panel_sort_key(source_panel: str) -> tuple[int, str]:
	normalized = source_panel.strip().lower()
	if normalized == "panel_a":
		return (0, normalized)
	if normalized == "panel_b":
		return (1, normalized)
	if normalized == "panel_c":
		return (2, normalized)
	return (3, normalized)


def extract_submission_rows(markdown_text: str, input_path: Path) -> list[dict[str, str]]:
	lines = markdown_text.splitlines()
	records: list[dict[str, str]] = []
	current_report_key = input_path.name
	current_component_id = ""
	current_indicator_id = ""
	current_source_panel = ""
	index = 0
	while index < len(lines):
		source_match = SOURCE_FILE_RE.match(lines[index])
		if source_match:
			current_report_key = Path(source_match.group(1).strip()).name
			current_component_id = ""
			current_indicator_id = ""
			current_source_panel = ""
			index += 1
			continue
		panel_match = PANEL_HEADING_RE.match(lines[index])
		if panel_match:
			current_source_panel = f"panel_{panel_match.group(1).lower()}"
			index += 1
			continue
		if not lines[index].lstrip().startswith("|"):
			index += 1
			continue
		table_lines: list[list[str]] = []
		while index < len(lines) and lines[index].lstrip().startswith("|"):
			table_lines.append(parse_markdown_cells(lines[index]))
			index += 1
		if not table_lines:
			continue
		headers = [normalize_header_name(cell) for cell in table_lines[0]]
		if "indicator_id" in headers:
			header_index = {header: idx for idx, header in enumerate(headers)}
			data_start = 1
			if len(table_lines) > 1 and is_markdown_separator_row(table_lines[1]):
				data_start = 2
			if data_start < len(table_lines):
				row = table_lines[data_start]
				if len(row) < len(headers):
					row = row + [""] * (len(headers) - len(row))
				if "component_id" in header_index:
					current_component_id = row[header_index["component_id"]].strip()
				current_indicator_id = row[header_index["indicator_id"]].strip()
			continue
		if not {"submission_id", "evidence_status", "human_judge_notes"}.issubset(headers):
			continue
		header_index = {header: idx for idx, header in enumerate(headers)}
		data_start = 1
		if len(table_lines) > 1 and is_markdown_separator_row(table_lines[1]):
			data_start = 2
		for row in table_lines[data_start:]:
			if is_markdown_separator_row(row):
				continue
			if len(row) < len(headers):
				row = row + [""] * (len(headers) - len(row))
			submission_id = row[header_index["submission_id"]].strip()
			if not submission_id:
				continue
			human_judge_notes = row[header_index["human_judge_notes"]].strip()
			records.append(
				{
					"report_key": current_report_key,
					"component_id": current_component_id,
					"block_rule_id": "",
						"source_panel": current_source_panel,
					"indicator_id": current_indicator_id,
					"submission_id": submission_id,
					"score": map_score_label(row[header_index["evidence_status"]].strip()),
					"validation": parse_validation_label(human_judge_notes),
					"human_judge_notes_detail": parse_human_judge_notes_detail(human_judge_notes),
				}
			)
	return records


def collect_input_paths(input_dir: Path, primary_glob: str, secondary_glob: str) -> list[Path]:
	primary_paths = sorted(path for path in input_dir.glob(primary_glob) if path.is_file())
	secondary_paths = sorted(path for path in input_dir.glob(secondary_glob) if path.is_file())
	return primary_paths + secondary_paths


def merge_records(source_paths: list[Path]) -> list[dict[str, str]]:
	records: list[dict[str, str]] = []
	seen_record_keys: set[tuple[str, str, str, str, str, str]] = set()
	seen_submission_keys: dict[tuple[str, str, str], dict[str, str]] = {}
	for input_path in source_paths:
		for record in extract_submission_rows(input_path.read_text(encoding="utf-8"), input_path):
			submission_key = (record["report_key"], record["indicator_id"], record["submission_id"])
			existing_submission = seen_submission_keys.get(submission_key)
			if existing_submission is not None:
				if (
					existing_submission["score"]
					and record["score"]
					and existing_submission["score"] != record["score"]
				):
					raise ValueError(
						"Found conflicting rows for report/submission key "
						f"{submission_key}: existing={existing_submission}, new={record}"
					)
				if (
					existing_submission["validation"]
					and record["validation"]
					and existing_submission["validation"] != record["validation"]
				):
					raise ValueError(
						"Found conflicting rows for report/submission key "
						f"{submission_key}: existing={existing_submission}, new={record}"
					)
				if not existing_submission["score"] and record["score"]:
					existing_submission["score"] = record["score"]
				if not existing_submission["validation"] and record["validation"]:
					existing_submission["validation"] = record["validation"]
				if not existing_submission.get("human_judge_notes_detail", "") and record.get("human_judge_notes_detail", ""):
					existing_submission["human_judge_notes_detail"] = record["human_judge_notes_detail"]
				continue
			record_key = (
				record["report_key"],
				record["component_id"],
				record["indicator_id"],
				record["submission_id"],
				record["score"],
				record["validation"],
			)
			if record_key in seen_record_keys:
				continue
			seen_record_keys.add(record_key)
			seen_submission_keys[submission_key] = record
			records.append(record)
	return records


def render_output_report(
	source_paths: list[Path],
	iteration_label: str,
	output_path: Path,
	registry_path: Path | None,
	records: list[dict[str, str]],
) -> str:
	score_column = f"{iteration_label}-score"
	validation_column = f"{iteration_label}-validation"
	false_score_column = "false_score"
	report_heading = build_report_heading(output_path.name, iteration_label)
	sorted_records = sorted(
		records,
		key=lambda record: (
			template_sort_key(record.get("template_id", "")),
			source_panel_sort_key(record.get("source_panel", "")),
			record.get("component_id", ""),
			record.get("indicator_id", ""),
			record.get("submission_id", ""),
		),
	)
	primary_count = sum(1 for path in source_paths if "_all_panel_" in path.name)
	secondary_count = len(source_paths) - primary_count
	grouped_rows: dict[str, list[dict[str, str]]] = {}
	for record in sorted_records:
		group_key = record.get("template_id", "") or "ungrouped"
		grouped_rows.setdefault(group_key, []).append(record)
	template_summary_rows: list[list[str]] = []
	for template_id, group_records in grouped_rows.items():
		template_description = group_records[0].get("sbo_short_description", "").strip()
		component_ids = sorted({record.get("component_id", "") for record in group_records if record.get("component_id", "")})
		indicator_ids = sorted({record.get("indicator_id", "") for record in group_records if record.get("indicator_id", "")})
		template_summary_rows.append(
			[
				template_id,
				template_description,
				", ".join(component_ids),
				str(len(indicator_ids)),
				str(len(group_records)),
			]
		)
	lines = [
		render_yaml_frontmatter(output_path, iteration_label, source_paths, primary_count, secondary_count, registry_path),
		f"## {report_heading}\n",
		"\n",
		f"- Source files scanned: {len(source_paths)}\n",
		f"- Primary aggregate files scanned: {primary_count}\n",
		f"- Secondary stitched files scanned: {secondary_count}\n",
		"- Rows are grouped into separate tables by template_id.\n",
		f"- Rows extracted: {len(records)}\n",
		f"- Template groups: {len(grouped_rows)}\n",
	]
	if template_summary_rows:
		lines.extend(
			[
				"\n",
				"### Template Summary\n",
				"\n",
				format_markdown_row(["template_id", "sbo_short_description", "component_ids", "indicator_count", "row_count"]),
				format_markdown_row(["---", "---", "---", "---", "---"]),
			]
		)
		for summary_row in template_summary_rows:
			lines.append(format_markdown_row(summary_row))
	if grouped_rows:
		lines.extend(
			[
				"\n",
				"### Indicator Validation Reports\n",
			]
		)
	for template_id, group_records in grouped_rows.items():
		template_description = group_records[0].get("sbo_short_description", "").strip()
		heading = f"{template_id} — {template_description}" if template_description else template_id
		lines.extend(
			[
				"\n",
				f"#### {heading}\n",
				"\n",
				format_markdown_row(["source_panel", "component_id", "indicator_id", "submission_id", score_column, validation_column, false_score_column]),
				format_markdown_row(["---", "---", "---", "---", "---", "---", "---"]),
			]
		)
		for record in group_records:
			validation_label = record["validation"]
			lines.append(
				format_markdown_row(
					[
						record.get("source_panel", ""),
						record.get("component_id", ""),
						record["indicator_id"],
						record["submission_id"],
						record["score"],
						validation_label,
						derive_false_score_flag(validation_label),
					]
				)
			)
	false_score_groups = {
		template_id: [record for record in group_records if derive_false_score_flag(record.get("validation", ""))]
		for template_id, group_records in grouped_rows.items()
	}
	false_score_groups = {
		template_id: group_records for template_id, group_records in false_score_groups.items() if group_records
	}
	if false_score_groups:
		lines.extend(
			[
				"\n",
				"### False Scores\n",
			]
		)
		for template_id, group_records in false_score_groups.items():
			template_description = group_records[0].get("sbo_short_description", "").strip()
			heading = f"{template_id} — {template_description}" if template_description else template_id
			lines.extend(
				[
					"\n",
					f"#### {heading}\n",
					"\n",
					format_markdown_row(
						[
							"source_panel",
							"component_id",
							"indicator_id",
							"submission_id",
							score_column,
							validation_column,
							false_score_column,
							"human_judge_notes_detail",
						]
					),
					format_markdown_row(["---", "---", "---", "---", "---", "---", "---", "---"]),
				]
			)
			for record in group_records:
				validation_label = record["validation"]
				lines.append(
					format_markdown_row(
						[
							record.get("source_panel", ""),
							record.get("component_id", ""),
							record["indicator_id"],
							record["submission_id"],
							record["score"],
							validation_label,
							derive_false_score_flag(validation_label),
							record.get("human_judge_notes_detail", ""),
						]
					)
				)
	return "".join(lines)


def main() -> int:
	args = parse_args()
	if args.panel_report_file is not None:
		input_path = args.panel_report_file.resolve()
		if not input_path.exists() or not input_path.is_file():
			print(f"Error: panel report file not found: {input_path}", file=sys.stderr)
			return 1
		source_paths = [input_path]
		iteration_source = input_path
	else:
		input_dir = args.input_dir.resolve()
		if not input_dir.exists() or not input_dir.is_dir():
			print(f"Error: input directory not found: {input_dir}", file=sys.stderr)
			return 1
		source_paths = collect_input_paths(input_dir, args.primary_glob, args.secondary_glob)
		if not source_paths:
			print(
				f"Error: no panel reports matched in {input_dir} for primary glob {args.primary_glob!r} "
				f"or secondary glob {args.secondary_glob!r}",
				file=sys.stderr,
			)
			return 1
		iteration_source = input_dir

	iteration_label = derive_iteration_label(iteration_source, args.iteration_label)
	if args.panel_report_file is not None:
		output_path = args.output_file.resolve() if args.output_file else default_output_path(input_path, iteration_label)
	else:
		output_path = args.output_file.resolve() if args.output_file else default_output_path_for_dir(input_dir, iteration_label)
	registry_path = args.indicator_registry.resolve() if args.indicator_registry else None
	if registry_path is not None and (not registry_path.exists() or not registry_path.is_file()):
		print(f"Error: indicator registry file not found: {registry_path}", file=sys.stderr)
		return 1
	try:
		records = merge_records(source_paths)
		if registry_path is not None:
			records = enrich_records_with_block_rule(records, build_indicator_reverse_lookup(registry_path))
	except ValueError as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	output_text = render_output_report(source_paths, iteration_label, output_path, registry_path, records)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(output_text, encoding="utf-8")
	print(output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())