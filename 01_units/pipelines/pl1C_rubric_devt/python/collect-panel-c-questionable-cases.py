#!/usr/bin/env python3
"""Collect Panel A/B/C sections from stitched ITP worksheets.

This script scans a directory for stitched ITP worksheet markdown files,
including both current `*_output_stitched_worksheet.md` files and legacy
`*_output_stitched.md` files, extracts one or more Panel A/B/C sections from
each file, and writes combined markdown reports.

Arguments:
- `--input-dir`: directory containing stitched worksheet markdown files.
- `--output-file`: optional explicit output file path. Defaults to
	`<input-dir>/I_<assessment>_all_panel_<panel>.md` when the assessment token can be
	inferred from stitched filenames, otherwise `<input-dir>/I_all_panel_<panel>.md`.
- `--sbo-manifest-file`: optional scoring manifest path used to resolve the
	matching indicator registry and group collected sections by Base Table rows.
- `--panel`: optional repeatable panel selector. Supported values are `A`, `B`,
	and `C`. When omitted, the script writes all three aggregate reports.

Output behavior:
- Writes one combined markdown document per selected panel.
- Includes one section per stitched worksheet that contains the target panel
	 subsection.
- Skips files that do not contain the target subsection.

Section-boundary behavior:
- Extraction starts at the exact panel heading for the selected panel.
- Extraction stops at the next heading with level 1 through 5, so nested level 6
  headings remain part of the captured section.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from generate_rubric_and_manifest_from_indicator_registry import (
	apply_expression_template,
	apply_token_template,
	collect_markdown_tables,
	expand_component_pattern,
	extract_rule_template,
	find_table_by_heading,
	resolve_component_block_lookup,
	resolve_local_slot_values,
)


STITCHED_REPORT_GLOBS = ["*_output_stitched_worksheet.md", "*_output_stitched.md"]
STOP_HEADING_RE = re.compile(r"^\s*#{1,5}\s+")
ASSESSMENT_FROM_STITCHED_RE = re.compile(r"^I_([A-Za-z0-9]+)_")
PANEL_SPECS = {
	"A": {
		"slug": "panel_a",
		"title": "Panel A — Clear positives",
		"heading_re": re.compile(r"^\s*#####\s*Panel\s+A\s+—\s+Clear\s+positives\s*$"),
	},
	"B": {
		"slug": "panel_b",
		"title": "Panel B — Borderline cases",
		"heading_re": re.compile(r"^\s*#####\s*Panel\s+B\s+—\s+Borderline\s+cases\s*$"),
	},
	"C": {
		"slug": "panel_c",
		"title": "Panel C — Questionable cases",
		"heading_re": re.compile(r"^\s*#####\s*Panel\s+C\s+—\s+Questionable\s+cases\s*$"),
	},
}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Collect Panel A/B/C sections from stitched ITP reports."
	)
	parser.add_argument(
		"--input-dir",
		type=Path,
		required=True,
		help="Directory containing stitched worksheet markdown files.",
	)
	parser.add_argument(
		"--sbo-manifest-file",
		type=Path,
		required=False,
		help="Optional scoring manifest path used to resolve Base Table grouping.",
	)
	parser.add_argument(
		"--panel",
		type=str,
		required=False,
		action="append",
		choices=sorted(PANEL_SPECS.keys()),
		help="Panel selector to aggregate. Repeat to write multiple reports; defaults to A, B, and C.",
	)
	parser.add_argument(
		"--output-file",
		type=Path,
		required=False,
		help="Optional explicit output markdown file path.",
	)
	return parser.parse_args()


def default_output_path(input_dir: Path, panel_key: str) -> Path:
	assessment_id = derive_assessment_id_from_stitched_reports(find_stitched_report_paths(input_dir))
	prefix = f"I_{assessment_id}" if assessment_id else "I"
	return input_dir / f"{prefix}_all_{PANEL_SPECS[panel_key]['slug']}.md"


def find_stitched_report_paths(input_dir: Path) -> list[Path]:
	seen_paths: set[Path] = set()
	stitched_paths: list[Path] = []
	for glob_pattern in STITCHED_REPORT_GLOBS:
		for path in sorted(input_dir.glob(glob_pattern)):
			if not path.is_file() or path in seen_paths:
				continue
			seen_paths.add(path)
			stitched_paths.append(path)
	return stitched_paths


def derive_assessment_id_from_stitched_reports(stitched_paths: list[Path]) -> str | None:
	for path in stitched_paths:
		match = ASSESSMENT_FROM_STITCHED_RE.match(path.stem)
		if match:
			return match.group(1)
	return None


def resolve_indicator_registry_path(manifest_path: Path | None) -> Path | None:
	if manifest_path is None:
		return None
	candidate = manifest_path.parent / manifest_path.name.replace("ScoringManifest", "IndicatorRegistry")
	if candidate.exists() and candidate.is_file():
		return candidate
	return None


def build_base_row_reverse_lookup(registry_path: Path) -> tuple[dict[tuple[str, str], dict[str, str]], list[tuple[str, str]]]:
	tables = collect_markdown_tables(registry_path)
	base_table = find_table_by_heading(tables, "base table")
	reuse_table = find_table_by_heading(tables, "reuse rule table")
	component_block_rule_table = find_table_by_heading(tables, "component block rule table")
	if base_table is None or reuse_table is None:
		return {}, []

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
	base_order = [
		(row.get("template_id", "").strip(), row.get("sbo_short_description", "").strip())
		for row in base_rows
		if row.get("template_id", "").strip()
	]

	def register_mapping(component_id: str, indicator_id: str, base_row: dict[str, str]) -> None:
		reverse_lookup[(component_id, indicator_id)] = {
			"template_id": base_row.get("template_id", "").strip() or "<missing_template_id>",
			"local_slot": base_row.get("local_slot", "").strip(),
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
				register_mapping(component_id, indicator_id, base_row)
		return reverse_lookup, base_order

	if {
		"template_group",
		"applies_to_component_pattern",
		"component_block_rule",
		"local_slot_source",
		"indicator_id_format",
	}.issubset(reuse_headers):
		if component_block_rule_table is None:
			return reverse_lookup, base_order
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
					register_mapping(component_id, indicator_id, base_row)
		return reverse_lookup, base_order

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
					register_mapping(component_id, indicator_id, base_row)
	return reverse_lookup, base_order


def parse_first_markdown_table(markdown_text: str) -> dict[str, str]:
	lines = markdown_text.splitlines()
	for index, line in enumerate(lines):
		if not line.lstrip().startswith("|"):
			continue
		if index + 2 >= len(lines):
			continue
		header_cells = [part.strip() for part in line.strip().strip("|").split("|")]
		separator_line = lines[index + 1].strip()
		if not separator_line.startswith("|"):
			continue
		value_line = lines[index + 2]
		if not value_line.lstrip().startswith("|"):
			continue
		value_cells = [part.strip() for part in value_line.strip().strip("|").split("|")]
		if len(header_cells) != len(value_cells):
			continue
		return {header_cells[cell_index]: value_cells[cell_index] for cell_index in range(len(header_cells))}
	return {}


def extract_target_section(markdown_text: str, panel_key: str) -> str | None:
	target_heading_re = PANEL_SPECS[panel_key]["heading_re"]
	lines = markdown_text.splitlines(keepends=True)
	search_start_index = 0
	if lines and lines[0].strip() == "---":
		for index in range(1, len(lines)):
			if lines[index].strip() == "---":
				search_start_index = index + 1
				break
	start_index: int | None = None

	for index in range(search_start_index, len(lines)):
		line = lines[index]
		if target_heading_re.match(line.strip()):
			start_index = index
			break

	if start_index is None:
		return None

	end_index = len(lines)
	for index in range(start_index + 1, len(lines)):
		if STOP_HEADING_RE.match(lines[index]) and not target_heading_re.match(lines[index].strip()):
			end_index = index
			break

	section_text = "".join(lines[start_index:end_index]).strip()
	if not section_text:
		return None
	return section_text + "\n"


def render_combined_report(
	input_dir: Path,
	stitched_paths: list[Path],
	panel_key: str,
	manifest_path: Path | None = None,
) -> str:
	registry_path = resolve_indicator_registry_path(manifest_path)
	base_row_reverse_lookup, base_order = build_base_row_reverse_lookup(registry_path) if registry_path else ({}, [])
	grouped_sections: dict[str, list[tuple[str, Path, str]]] = {}
	ungrouped_sections: list[tuple[str, Path, str]] = []
	panel_title = PANEL_SPECS[panel_key]["title"]
	output_lines = [
		f"# {panel_title}\n",
		"\n",
		f"- Input directory: {input_dir}\n",
		f"- Stitched reports scanned: {len(stitched_paths)}\n",
	]

	matched_count = 0
	for stitched_path in stitched_paths:
		section_text = extract_target_section(stitched_path.read_text(encoding="utf-8"), panel_key)
		if section_text is None:
			continue

		matched_count += 1
		metadata = parse_first_markdown_table(section_text)
		component_id = (metadata.get("component_id") or "").strip()
		indicator_id = (metadata.get("indicator_id") or "").strip()
		sbo_short_description = (metadata.get("sbo_short_description") or stitched_path.stem).strip()
		indicator_heading = f"{indicator_id} — {sbo_short_description}" if indicator_id else stitched_path.stem
		group_info = base_row_reverse_lookup.get((component_id, indicator_id)) if component_id and indicator_id else None
		if group_info is None:
			ungrouped_sections.append((indicator_heading, stitched_path, section_text))
			continue
		group_key = group_info["template_id"]
		grouped_sections.setdefault(group_key, []).append((indicator_heading, stitched_path, section_text))

	for template_id, template_description in base_order:
		sections = grouped_sections.get(template_id)
		if not sections:
			continue
		output_lines.extend([
			"\n",
			f"## {template_id} — {template_description}\n",
		])
		for indicator_heading, stitched_path, section_text in sections:
			output_lines.extend(
				[
					"\n",
					f"### {indicator_heading}\n",
					"\n",
					f"- Source file: {stitched_path}\n",
					"\n",
					section_text,
				]
			)

	if ungrouped_sections:
		output_lines.extend(["\n", "## Ungrouped\n"])
		for indicator_heading, stitched_path, section_text in ungrouped_sections:
			output_lines.extend(
				[
					"\n",
					f"### {indicator_heading}\n",
					"\n",
					f"- Source file: {stitched_path}\n",
					"\n",
					section_text,
				]
			)

	if matched_count == 0:
		output_lines.extend(
			[
				"\n",
				f"No `{PANEL_SPECS[panel_key]['title']}` sections were found.\n",
			]
		)

	return "".join(output_lines)


def main() -> int:
	args = parse_args()
	input_dir = args.input_dir
	manifest_path = args.sbo_manifest_file.resolve() if args.sbo_manifest_file else None
	selected_panels = args.panel or ["A", "B", "C"]

	if not input_dir.exists() or not input_dir.is_dir():
		print(f"Error: input directory not found: {input_dir}", file=sys.stderr)
		return 1
	if manifest_path is not None and (not manifest_path.exists() or not manifest_path.is_file()):
		print(f"Error: scoring manifest file not found: {manifest_path}", file=sys.stderr)
		return 1
	if args.output_file is not None and len(selected_panels) != 1:
		print("Error: --output-file can only be used when exactly one --panel is selected.", file=sys.stderr)
		return 1

	stitched_paths = find_stitched_report_paths(input_dir)
	output_paths: list[Path] = []
	for panel_key in selected_panels:
		output_file = args.output_file if args.output_file is not None else default_output_path(input_dir, panel_key)
		output_text = render_combined_report(input_dir, stitched_paths, panel_key, manifest_path)
		output_file.parent.mkdir(parents=True, exist_ok=True)
		output_file.write_text(output_text, encoding="utf-8")
		output_paths.append(output_file)
	for output_path in output_paths:
		print(output_path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())