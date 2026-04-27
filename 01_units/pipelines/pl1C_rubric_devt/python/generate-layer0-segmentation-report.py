#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ap2b_l0_case_checking import (
	build_release_config,
	build_assignment_relative_path,
	discover_previous_operator_specs_path,
	expand_template,
	load_json,
	build_operator_spec_diff,
	load_pipeline_runtime,
	parse_release_from_operator_specs_path,
	resolve_operator_specs_path,
	resolve_pipeline_paths_path,
)


_VERSION_PATTERN = re.compile(r"_v\d+")
_OPERATOR_SPECS_FILENAME_PATTERN = re.compile(r"^(?P<prefix>.+)_v(?P<registry_file_version>\d+)\.json$")
_RUNTIME_CHANGE_FIELDS = [
	"segment_text",
	"extraction_status",
	"extraction_notes",
	"confidence",
	"flags",
]
_STITCHED_CHANGE_FIELD_PREFIXES = (
	"segment_text_",
	"extraction_status_",
	"extraction_notes_",
	"confidence_",
	"flags_",
)


def format_markdown_table_cell(value: str) -> str:
	text = (value or "").strip()
	if not text:
		return "(empty)"
	return text.replace("|", "\\|").replace("\n", "<br>")


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
	lines = [
		"| " + " | ".join(headers) + " |",
		"| " + " | ".join(["---"] * len(headers)) + " |",
	]
	for row in rows:
		lines.append("| " + " | ".join(row) + " |")
	return "\n".join(lines)


def sanitize_filename_fragment(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
	text = text.strip("-.")
	return text or "segment"


def resolve_assignment_prefix_from_output(main_output_md_path: Path) -> str:
	assignment_id = main_output_md_path.name.split("_", 1)[0].strip()
	return assignment_id or "ASSIGNMENT"


def split_common_path_prefix(*paths: str) -> tuple[str, list[str]]:
	normalized_paths = [str(path).strip() for path in paths if str(path).strip()]
	if not normalized_paths:
		return "", ["" for _ in paths]
	common_prefix = os.path.commonpath(normalized_paths)
	suffixes: list[str] = []
	for original_path in paths:
		path_text = str(original_path).strip()
		if not path_text:
			suffixes.append("")
			continue
		relative_path = os.path.relpath(path_text, common_prefix)
		suffixes.append("." if relative_path == "." else relative_path)
	return common_prefix, suffixes


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Compare Layer 0 runtime and stitched outputs between the current release and a baseline release."
	)
	parser.add_argument(
		"--layer0-config-key",
		default="layer0_calibration",
		help="Top-level pipeline_paths key to read Layer 0 config from (default: layer0_calibration; production: layer0_prod).",
	)
	parser.add_argument("--baseline-iteration", help="Optional baseline iteration, for example 04 or iter04.")
	parser.add_argument("--baseline-run", help="Optional baseline scoring run, defaults to the baseline release scoring_run or current scoring_run.")
	parser.add_argument("--output-md", type=Path, help="Optional Markdown output path.")
	parser.add_argument("--output-json", type=Path, help="Optional JSON output path.")
	return parser.parse_args()


def normalize_iteration(value: str) -> str:
	text = value.strip()
	if text.startswith("iter"):
		text = text[4:]
	return text


def normalize_artifact_name(filename: str) -> str:
	return _VERSION_PATTERN.sub("", filename)


def filter_preferred_artifact_files(files: dict[str, Path]) -> dict[str, Path]:
	component_scoped = {
		name: path for name, path in files.items() if "Section" in name
	}
	if component_scoped:
		return component_scoped
	return files


def read_csv_rows(path: Path) -> list[dict[str, str]]:
	with path.open("r", encoding="utf-8", newline="") as handle:
		reader = csv.DictReader(handle)
		return list(reader)


def build_submission_component_key(row: dict[str, str]) -> tuple[str, str]:
	return (
		str(row.get("component_id", "")).strip(),
		str(row.get("submission_id") or row.get("source_submission_id") or "").strip(),
	)


def escape_markdown_table_cell(value: str) -> str:
	normalized = str(value).replace("\r\n", "\n").replace("\r", "\n")
	return normalized.replace("|", "\\|").replace("\n", "<br>")


def format_original_submission_entry(component_id: str, submission_id: str, source_response_text: str) -> str:
	identifier = f"{component_id} / submission_id={submission_id}" if component_id else f"submission_id={submission_id}"
	text = source_response_text.strip() or "(missing source submission text)"
	return f"{identifier}\n{text}"


def highlight_segment_text_in_submission(source_entry: str, segment_text: str) -> str:
	normalized_entry = source_entry.replace("\r\n", "\n").replace("\r", "\n")
	normalized_segment = segment_text.replace("\r\n", "\n").replace("\r", "\n").strip()
	if not normalized_segment:
		return normalized_entry
	exact_pattern = re.compile(re.escape(normalized_segment))
	if exact_pattern.search(normalized_entry):
		return exact_pattern.sub(lambda match: f"<mark>{match.group(0)}</mark>", normalized_entry)
	ignore_case_pattern = re.compile(re.escape(normalized_segment), re.IGNORECASE)
	if ignore_case_pattern.search(normalized_entry):
		return ignore_case_pattern.sub(lambda match: f"<mark>{match.group(0)}</mark>", normalized_entry)
	return normalized_entry


def index_stitched_rows_by_component_submission(stitched_files: list[str]) -> dict[tuple[str, str], dict[str, str]]:
	indexed_rows: dict[tuple[str, str], dict[str, str]] = {}
	for file_path_text in stitched_files:
		for row in read_csv_rows(Path(file_path_text)):
			component_id, submission_id = build_submission_component_key(row)
			if not component_id or not submission_id:
				continue
			indexed_rows[(component_id, submission_id)] = row
	return indexed_rows


def sort_runtime_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
	return sorted(
		rows,
		key=lambda row: (
			row.get("component_id", ""),
			row.get("operator_id", ""),
			row.get("submission_id", ""),
			row.get("segment_text", ""),
		),
	)


def build_runtime_row_key(row: dict[str, str]) -> tuple[str, str, str, str]:
	return (
		row.get("submission_id", ""),
		row.get("component_id", ""),
		row.get("operator_id", ""),
		row.get("segment_id", ""),
	)


def build_stitched_row_key(row: dict[str, str]) -> tuple[str, str]:
	return (row.get("submission_id", ""), row.get("component_id", ""))


def collect_current_release_context(
	pipeline_paths_path: Path,
	*,
	layer0_config_key: str,
) -> tuple[dict[str, str], dict[str, Any], Path]:
	payload = load_json(pipeline_paths_path)
	if layer0_config_key == "layer0_calibration":
		release_config = build_release_config(payload)
		operator_specs_path = resolve_operator_specs_path(pipeline_paths_path).resolve()
	else:
		layer0_block = payload.get(layer0_config_key, {})
		release_block = layer0_block.get("release", {})
		iteration = normalize_iteration(str(release_block.get("iteration", "")))
		filename_version = str(release_block.get("filename_version") or iteration)
		release_config = {
			"iteration": iteration,
			"registry_version": str(release_block.get("registry_version") or iteration),
			"registry_file_version": str(release_block.get("registry_file_version") or filename_version),
			"filename_version": filename_version,
			"scoring_run": str(release_block.get("scoring_run", "")),
		}
		operator_specs_cfg = layer0_block.get("layer0_run_operator_engine", {}).get("operator_specs_input", {})
		assignment_pipelines_root = pipeline_paths_path.parent / "01_pipelines"
		operator_specs_path = (
			assignment_pipelines_root
			/ build_assignment_relative_path(operator_specs_cfg, release_config)
		).resolve()
	return release_config, payload, operator_specs_path


def discover_baseline_release(
	*,
	current_operator_specs_path: Path,
	current_release: dict[str, str],
	baseline_iteration_arg: str | None,
	baseline_run_arg: str | None,
	allow_same_release_baseline: bool = False,
) -> dict[str, str]:
	if baseline_iteration_arg:
		baseline_iteration = normalize_iteration(baseline_iteration_arg)
		return {
			"iteration": baseline_iteration,
			"registry_version": baseline_iteration,
			"registry_file_version": "",
			"scoring_run": baseline_run_arg or current_release.get("scoring_run", ""),
		}
	previous_operator_specs_path = discover_previous_operator_specs_path(current_operator_specs_path)
	if previous_operator_specs_path is None:
		if allow_same_release_baseline:
			fallback = current_release.copy()
			fallback["scoring_run"] = baseline_run_arg or current_release.get("scoring_run", "")
			return fallback
		raise FileNotFoundError(
			"Could not discover a previous Layer 0 release before "
			f"{current_operator_specs_path}. Provide --baseline-iteration (and optionally --baseline-run), "
			"or create an earlier release iteration first."
		)
	baseline_release = parse_release_from_operator_specs_path(previous_operator_specs_path)
	baseline_release["scoring_run"] = baseline_run_arg or current_release.get("scoring_run", "")
	return baseline_release

def resolve_operator_specs_path_for_release(current_operator_specs_path: Path, release_config: dict[str, str]) -> Path | None:
	current_match = _OPERATOR_SPECS_FILENAME_PATTERN.match(current_operator_specs_path.name)
	if current_match is None:
		return None
	prefix = current_match.group("prefix")
	iteration = release_config.get("iteration", "")
	if not iteration:
		return None
	registry_version = release_config.get("registry_version", "")
	candidates: list[Path] = []
	path_text = str(current_operator_specs_path)
	if "/stage13/registry_v" in path_text:
		if not registry_version:
			return None
		runs_root = current_operator_specs_path.parents[4]
		candidates = sorted(
			runs_root.glob(
				f"iter{iteration}/stage13/registry_v{registry_version}/00_rubric_sibling_files/{prefix}_v*.json"
			)
		)
	elif "/00_rubric_sibling_files/" in path_text:
		runs_root = current_operator_specs_path.parents[2]
		candidates = sorted(runs_root.glob(f"iter{iteration}/00_rubric_sibling_files/{prefix}_v*.json"))
	elif "/00_sources/prompts/" in path_text:
		runs_root = current_operator_specs_path.parents[3]
		candidates = sorted(runs_root.glob(f"iter{iteration}/00_sources/prompts/{prefix}_v*.json"))
	if not candidates:
		return None
	return candidates[-1].resolve()


def resolve_report_output_paths(
	*,
	payload: dict[str, Any],
	layer0_config_key: str,
	pipeline_paths_path: Path,
	current_release: dict[str, str],
	baseline_release: dict[str, str],
	output_md_arg: Path | None,
	output_json_arg: Path | None,
) -> tuple[Path, Path]:
	if output_md_arg and output_json_arg:
		return output_md_arg.resolve(), output_json_arg.resolve()
	report_config = payload[layer0_config_key]["layer0_segmentation_report"]["diagnostics_output"]
	assignment_pipelines_root = pipeline_paths_path.parent / "01_pipelines"
	release_for_dir = current_release.copy()
	output_dir = assignment_pipelines_root / build_assignment_relative_path(
		{**report_config, "filename": ""}, release_for_dir
	)
	filename_tokens = {**current_release, "baseline_iteration": baseline_release.get("iteration", "")}
	filename_md = expand_template(str(report_config["filename_md"]), filename_tokens)
	filename_json = expand_template(str(report_config["filename_json"]), filename_tokens)
	output_md = output_md_arg.resolve() if output_md_arg else (output_dir / filename_md).resolve()
	output_json = output_json_arg.resolve() if output_json_arg else (output_dir / filename_json).resolve()
	return output_md, output_json


def resolve_layer0_artifact_dir(
	*,
	pipeline_paths_path: Path,
	payload: dict[str, Any],
	release_config: dict[str, str],
	config_path: list[str],
) -> Path:
	config: dict[str, Any] = payload
	for key in config_path:
		config = config[key]
	assignment_pipelines_root = pipeline_paths_path.parent / "01_pipelines"
	relative_dir = "".join(
		[
			str(config.get("base", "")),
			str(config.get("dir", "")),
			str(config.get("run", "")),
			expand_template(str(config.get("run_relative_subdir", "")), release_config),
		]
	)
	return (assignment_pipelines_root / relative_dir).resolve()


def index_rows(
	rows: list[dict[str, str]],
	*,
	key_builder: Any,
) -> dict[tuple[Any, ...], dict[str, str]]:
	indexed: dict[tuple[Any, ...], dict[str, str]] = {}
	for row in rows:
		key = key_builder(row)
		indexed[key] = row
	return indexed


def compare_runtime_files(current_path: Path, baseline_path: Path) -> dict[str, Any]:
	current_rows = read_csv_rows(current_path)
	baseline_rows = read_csv_rows(baseline_path)
	current_index = index_rows(current_rows, key_builder=build_runtime_row_key)
	baseline_index = index_rows(baseline_rows, key_builder=build_runtime_row_key)
	current_extracted_segments: Counter[tuple[str, str]] = Counter(
		(row.get("segment_id", ""), row.get("segment_text", ""))
		for row in current_rows
		if row.get("segment_id", "") and row.get("segment_text", "").strip()
	)
	shared_keys = sorted(set(current_index) & set(baseline_index))
	changed_rows: list[dict[str, Any]] = []
	operator_counter: Counter[str] = Counter()
	for key in shared_keys:
		current_row = current_index[key]
		baseline_row = baseline_index[key]
		changes = []
		for field in _RUNTIME_CHANGE_FIELDS:
			if current_row.get(field, "") != baseline_row.get(field, ""):
				changes.append(
					{
						"field": field,
						"baseline": baseline_row.get(field, ""),
						"current": current_row.get(field, ""),
					}
				)
		if changes:
			changed_rows.append(
				{
					"key": list(key),
					"submission_id": current_row.get("submission_id", ""),
					"component_id": current_row.get("component_id", ""),
					"operator_id": current_row.get("operator_id", ""),
					"segment_id": current_row.get("segment_id", ""),
					"changes": changes,
				}
			)
			operator_counter[current_row.get("operator_id", "")] += 1
	return {
		"current_path": str(current_path),
		"baseline_path": str(baseline_path),
		"current_row_count": len(current_rows),
		"baseline_row_count": len(baseline_rows),
		"shared_row_count": len(shared_keys),
		"added_row_count": len(set(current_index) - set(baseline_index)),
		"removed_row_count": len(set(baseline_index) - set(current_index)),
		"changed_row_count": len(changed_rows),
		"changed_rows": changed_rows,
		"changed_operator_counts": dict(sorted(operator_counter.items())),
		"current_extracted_segments": [
			{
				"segment_id": segment_id,
				"segment_text": segment_text,
				"count": count,
			}
			for (segment_id, segment_text), count in sorted(current_extracted_segments.items())
		],
	}


def compare_stitched_files(current_path: Path, baseline_path: Path) -> dict[str, Any]:
	current_rows = read_csv_rows(current_path)
	baseline_rows = read_csv_rows(baseline_path)
	current_index = index_rows(current_rows, key_builder=build_stitched_row_key)
	baseline_index = index_rows(baseline_rows, key_builder=build_stitched_row_key)
	shared_keys = sorted(set(current_index) & set(baseline_index))
	changed_rows: list[dict[str, Any]] = []
	for key in shared_keys:
		current_row = current_index[key]
		baseline_row = baseline_index[key]
		changes = []
		field_names = sorted(
			field_name
			for field_name in set(current_row) | set(baseline_row)
			if field_name.startswith(_STITCHED_CHANGE_FIELD_PREFIXES) or field_name == "missing_audit"
		)
		for field_name in field_names:
			if current_row.get(field_name, "") != baseline_row.get(field_name, ""):
				changes.append(
					{
						"field": field_name,
						"baseline": baseline_row.get(field_name, ""),
						"current": current_row.get(field_name, ""),
					}
				)
		if changes:
			changed_rows.append(
				{
					"key": list(key),
					"submission_id": current_row.get("submission_id", ""),
					"component_id": current_row.get("component_id", ""),
					"source_response_text": current_row.get("source_response_text", ""),
					"changes": changes,
				}
			)
	return {
		"current_path": str(current_path),
		"baseline_path": str(baseline_path),
		"current_row_count": len(current_rows),
		"baseline_row_count": len(baseline_rows),
		"shared_row_count": len(shared_keys),
		"added_row_count": len(set(current_index) - set(baseline_index)),
		"removed_row_count": len(set(baseline_index) - set(current_index)),
		"changed_row_count": len(changed_rows),
		"changed_rows": changed_rows,
	}


def compare_artifact_dirs(
	*,
	current_dir: Path,
	baseline_dir: Path,
	matcher_suffix: str,
	comparator: Any,
) -> dict[str, Any]:
	current_files = {
		normalize_artifact_name(path.name): path
		for path in current_dir.glob(f"*{matcher_suffix}")
		if path.is_file()
	}
	current_files = filter_preferred_artifact_files(current_files)
	baseline_files = {
		normalize_artifact_name(path.name): path
		for path in baseline_dir.glob(f"*{matcher_suffix}")
		if path.is_file()
	}
	baseline_files = filter_preferred_artifact_files(baseline_files)
	shared_names = sorted(set(current_files) & set(baseline_files))
	per_file = [comparator(current_files[name], baseline_files[name]) for name in shared_names]
	return {
		"current_dir": str(current_dir),
		"baseline_dir": str(baseline_dir),
		"current_files": [str(current_files[name]) for name in sorted(current_files)],
		"baseline_files": [str(baseline_files[name]) for name in sorted(baseline_files)],
		"shared_file_count": len(shared_names),
		"added_files": sorted(set(current_files) - set(baseline_files)),
		"removed_files": sorted(set(baseline_files) - set(current_files)),
		"per_file": per_file,
		"changed_row_count": sum(item["changed_row_count"] for item in per_file),
	}


def build_staleness_summary(operator_specs_path: Path, file_paths: list[str]) -> dict[str, Any]:
	operator_specs_mtime = operator_specs_path.stat().st_mtime
	stale_files = []
	for file_path_text in file_paths:
		file_path = Path(file_path_text)
		if file_path.stat().st_mtime < operator_specs_mtime:
			stale_files.append(str(file_path))
	return {
		"operator_specs_path": str(operator_specs_path),
		"stale_file_count": len(stale_files),
		"stale_files": stale_files,
	}


def build_current_segment_match_details(
	*,
	current_runtime_files: list[str],
	current_stitched_files: list[str],
	current_operator_specs: list[Any],
) -> dict[str, dict[str, Any]]:
	segment_details: dict[str, dict[str, Any]] = {}
	stitched_rows_index = index_stitched_rows_by_component_submission(current_stitched_files)
	for spec in current_operator_specs:
		segment_id = str(getattr(spec, "segment_id", "")).strip()
		if not segment_id:
			continue
		segment_entry = segment_details.setdefault(
			segment_id,
			{
				"operator_ids": set(),
				"matches": [],
				"non_matches": [],
			},
		)
		operator_id = str(getattr(spec, "operator_id", "")).strip()
		if operator_id:
			segment_entry["operator_ids"].add(operator_id)

	for file_path_text in current_runtime_files:
		file_path = Path(file_path_text)
		for row in read_csv_rows(file_path):
			segment_id = str(row.get("segment_id", "")).strip()
			if not segment_id:
				continue
			segment_entry = segment_details.setdefault(
				segment_id,
				{
					"operator_ids": set(),
					"matches": [],
					"non_matches": [],
				},
			)
			operator_id = str(row.get("operator_id", "")).strip()
			if operator_id:
				segment_entry["operator_ids"].add(operator_id)
			row_payload = {
				"submission_id": str(row.get("submission_id", "")).strip(),
				"component_id": str(row.get("component_id", "")).strip(),
				"operator_id": operator_id,
				"segment_text": str(row.get("segment_text", "")).strip(),
				"extraction_status": str(row.get("extraction_status", "")).strip(),
				"confidence": str(row.get("confidence", "")).strip(),
				"flags": str(row.get("flags", "")).strip(),
				"extraction_notes": str(row.get("extraction_notes", "")).strip(),
			}
			stitched_row = stitched_rows_index.get((row_payload["component_id"], row_payload["submission_id"]))
			row_payload["original_submission"] = format_original_submission_entry(
				row_payload["component_id"],
				row_payload["submission_id"],
				str((stitched_row or {}).get("source_response_text", "")),
			)
			if row_payload["extraction_status"] == "ok":
				segment_entry["matches"].append(row_payload)
			else:
				segment_entry["non_matches"].append(row_payload)

	return {
		segment_id: {
			"operator_ids": sorted(details["operator_ids"]),
			"matches": sort_runtime_rows(details["matches"]),
			"non_matches": sort_runtime_rows(details["non_matches"]),
		}
		for segment_id, details in sorted(segment_details.items())
	}


def build_segment_match_detail_report(
	*,
	assignment_id: str,
	segment_id: str,
	detail: dict[str, Any],
	current_release: dict[str, str],
	main_report_path: Path,
) -> str:
	operator_text = ", ".join(detail.get("operator_ids", [])) or "(none)"
	match_rows = detail.get("matches", [])
	non_match_rows = detail.get("non_matches", [])
	lines = [
		f"# {assignment_id} Layer 0 Segment Detail: {segment_id}",
		"",
		"## Metadata",
		"",
		f"- Segment ID: {format_markdown_table_cell(segment_id)}",
		f"- Operators: {format_markdown_table_cell(operator_text)}",
		f"- Iteration: {format_markdown_table_cell(current_release.get('iteration', ''))}",
		f"- Scoring run: {format_markdown_table_cell(current_release.get('scoring_run', ''))}",
		f"- Parent report: {format_markdown_table_cell(str(main_report_path))}",
		f"- Match rows: {len(match_rows)}",
		f"- Non-match rows: {len(non_match_rows)}",
		"",
		"## Matches",
		"",
	]
	if match_rows:
		lines.append(
			render_markdown_table(
				["operator_id", "original_submission", "segment_text", "confidence", "flags"],
				[
					[
						format_markdown_table_cell(row.get("operator_id", "")),
						escape_markdown_table_cell(
							highlight_segment_text_in_submission(
								str(row.get("original_submission", "")),
								str(row.get("segment_text", "")),
							)
						),
						escape_markdown_table_cell(row.get("segment_text", "")),
						format_markdown_table_cell(row.get("confidence", "")),
						format_markdown_table_cell(row.get("flags", "")),
					]
					for row in match_rows
				],
			)
		)
	else:
		lines.append("No matches for this segment in the current runtime output.")
	lines.extend([
		"",
		"## Non-Matches",
		"",
	])
	if non_match_rows:
		lines.append(
			render_markdown_table(
				[
					"operator_id",
					"original_submission",
					"segment_text",
					"extraction_status",
					"extraction_notes",
					"confidence",
					"flags",
				],
				[
					[
						format_markdown_table_cell(row.get("operator_id", "")),
						escape_markdown_table_cell(
							highlight_segment_text_in_submission(
								str(row.get("original_submission", "")),
								str(row.get("segment_text", "")),
							)
						),
						escape_markdown_table_cell(row.get("segment_text", "")),
						format_markdown_table_cell(row.get("extraction_status", "")),
						format_markdown_table_cell(row.get("extraction_notes", "")),
						format_markdown_table_cell(row.get("confidence", "")),
						format_markdown_table_cell(row.get("flags", "")),
					]
					for row in non_match_rows
				],
			)
		)
	else:
		lines.append("No non-matches for this segment in the current runtime output.")
	return "\n".join(lines).rstrip() + "\n"


def build_segment_match_detail_output_paths(
	*,
	main_output_md_path: Path,
	current_release: dict[str, str],
	segment_match_details: dict[str, dict[str, Any]],
) -> dict[str, Path]:
	assignment_id = resolve_assignment_prefix_from_output(main_output_md_path)
	iteration_label = current_release.get("iteration", "").strip()
	base_stem = f"{assignment_id}_Layer0_iter{iteration_label}" if iteration_label else f"{assignment_id}_Layer0"
	return {
		segment_id: main_output_md_path.with_name(
			f"{base_stem}__segment_{sanitize_filename_fragment(segment_id)}.md"
		)
		for segment_id in sorted(segment_match_details)
	}


def build_segment_appendix_output_path(*, main_output_md_path: Path) -> Path:
	return main_output_md_path.with_name(f"{main_output_md_path.stem}__current_extracted_segments_by_type.md")


def build_runtime_extracted_segments_by_id(runtime_diff: dict[str, Any]) -> dict[str, Counter[str]]:
	runtime_extracted_segments_by_id: defaultdict[str, Counter[str]] = defaultdict(Counter)
	for item in runtime_diff.get("per_file", []):
		for segment_entry in item.get("current_extracted_segments", []):
			segment_id = segment_entry.get("segment_id", "")
			segment_text = segment_entry.get("segment_text", "")
			count = int(segment_entry.get("count", 0))
			if segment_id and segment_text:
				runtime_extracted_segments_by_id[segment_id][segment_text] += count
	return dict(runtime_extracted_segments_by_id)


def build_segment_appendix_markdown_report(payload: dict[str, Any], *, main_report_path: Path) -> str:
	assignment_id = str(payload.get("assignment_id", "")).strip() or "ASSIGNMENT"
	current_release = payload["current_release"]
	runtime_diff = payload["runtime_diff"]
	segment_match_details = payload.get("current_segment_match_details", {})
	runtime_extracted_segments_by_id = build_runtime_extracted_segments_by_id(runtime_diff)
	all_segment_ids = sorted(set(runtime_extracted_segments_by_id) | set(segment_match_details))

	lines = [
		f"# {assignment_id} Layer 0 Segment Appendix: Current Extracted Segments By Segment Type",
		"",
		f"- Parent report: `{main_report_path}`",
		f"- Iteration: {format_markdown_table_cell(current_release.get('iteration', ''))}",
		f"- Scoring run: {format_markdown_table_cell(current_release.get('scoring_run', ''))}",
	]

	if not all_segment_ids:
		lines.extend([
			"",
			"No extracted segments were found in the current runtime outputs.",
		])
		return "\n".join(lines).rstrip() + "\n"

	lines.extend([
		"",
		"## Current Extracted Segments By Segment Type",
		"",
		"This appendix lists the current release's extracted segment texts grouped by segment type, with counts for each distinct extracted text.",
	])

	for segment_id in all_segment_ids:
		lines.extend([
			"",
			f"### {format_markdown_table_cell(segment_id)}",
			"",
			"| Extracted Segment | Count |",
			"| --- | ---: |",
		])
		segment_counter = runtime_extracted_segments_by_id.get(segment_id, {})
		if segment_counter:
			for segment_text, count in sorted(segment_counter.items(), key=lambda item: (-item[1], item[0])):
				lines.append(f"| {format_markdown_table_cell(segment_text)} | {count} |")
		else:
			lines.append("| (none) | 0 |")

	return "\n".join(lines).rstrip() + "\n"


def build_markdown_report(payload: dict[str, Any]) -> str:
	assignment_id = str(payload.get("assignment_id", "")).strip() or "ASSIGNMENT"
	current_release = payload["current_release"]
	baseline_release = payload["baseline_release"]
	runtime_diff = payload["runtime_diff"]
	stitched_diff = payload["stitched_diff"]
	operator_spec_diff = payload.get("operator_spec_diff", {})
	staleness = payload.get("staleness", {})
	segment_match_details = payload.get("current_segment_match_details", {})
	lines = [
		f"# {assignment_id} Layer 0 Iter-To-Iter Diff Report",
		"",
		"## What This Report Does",
		"",
		"This report compares the current Layer 0 deterministic outputs against an earlier release.",
		"",
		"- `runtime` diffs are row-level extractor outputs keyed by submission, component, operator, and segment.",
		"- `stitched` diffs are wide per-submission views that are easier to review alongside source text.",
		"- Use this report to discover behavioral changes worth promoting into anchor or regression cases.",
		"",
		"## Release Comparison",
		"",
		"| Field | Baseline | Current |",
		"| --- | --- | --- |",
		f"| iteration | {format_markdown_table_cell(baseline_release.get('iteration', 'n/a'))} | {format_markdown_table_cell(current_release.get('iteration', 'n/a'))} |",
		f"| registry version | {format_markdown_table_cell(baseline_release.get('registry_version', 'n/a'))} | {format_markdown_table_cell(current_release.get('registry_version', 'n/a'))} |",
		f"| registry file version | {format_markdown_table_cell(baseline_release.get('registry_file_version', 'n/a') or 'n/a')} | {format_markdown_table_cell(current_release.get('registry_file_version', 'n/a'))} |",
		f"| scoring run | {format_markdown_table_cell(baseline_release.get('scoring_run', 'n/a'))} | {format_markdown_table_cell(current_release.get('scoring_run', 'n/a'))} |",
		f"- Changed operator specs: {operator_spec_diff.get('changed_operator_count', 0)}",
		f"- Runtime changed rows: {runtime_diff.get('changed_row_count', 0)}",
		f"- Stitched changed rows: {stitched_diff.get('changed_row_count', 0)}",
	]
	if staleness:
		lines.extend([
			"",
			"## Freshness Check",
			"",
			f"- Runtime/stiched files older than current operator specs: {staleness.get('stale_file_count', 0)}",
		])
		if staleness.get("stale_file_count", 0):
			lines.extend([
				"- Warning: zero output changes may be misleading if current Layer 0 runtime outputs were not regenerated after the latest operator-spec update.",
				"",
				"### Stale Files",
				"Files listed here have modification times older than the current operator-spec artifact, so they may reflect an earlier Layer 0 release rather than the current one.",
				"",
			])
			for file_path in staleness.get("stale_files", [])[:12]:
				lines.append(f"- `{file_path}`")

	runtime_operator_counts: Counter[str] = Counter()
	runtime_operator_segments: defaultdict[str, set[str]] = defaultdict(set)
	for item in runtime_diff.get("per_file", []):
		runtime_operator_counts.update(item.get("changed_operator_counts", {}))
		for changed_row in item.get("changed_rows", []):
			operator_id = changed_row.get("operator_id", "")
			segment_id = changed_row.get("segment_id", "")
			if operator_id and segment_id:
				runtime_operator_segments[operator_id].add(segment_id)
	runtime_common_prefix, runtime_dir_suffixes = split_common_path_prefix(
		runtime_diff.get("baseline_dir", ""),
		runtime_diff.get("current_dir", ""),
	)
	lines.extend([
		"",
		"## Runtime Diff Summary",
		"",
		f"- Common runtime path prefix: `{runtime_common_prefix or '(none)'}`",
		"",
		"| Runtime Location | Baseline | Current |",
		"| --- | --- | --- |",
		f"| runtime dir | {format_markdown_table_cell(runtime_dir_suffixes[0])} | {format_markdown_table_cell(runtime_dir_suffixes[1])} |",
		f"- Shared runtime files: {runtime_diff.get('shared_file_count', 0)}",
		f"- Added runtime files: {len(runtime_diff.get('added_files', []))}",
		f"- Removed runtime files: {len(runtime_diff.get('removed_files', []))}",
	])
	shared_runtime_files = runtime_diff.get("per_file", [])
	if shared_runtime_files:
		file_paths: list[str] = []
		for item in shared_runtime_files:
			baseline_path = item.get("baseline_path", "")
			current_path = item.get("current_path", "")
			if baseline_path:
				file_paths.append(baseline_path)
			if current_path:
				file_paths.append(current_path)
		files_common_prefix, _unused_suffixes = split_common_path_prefix(*file_paths)
		lines.extend([
			"",
			"### Participating Runtime Files",
			"",
			f"- Common file path prefix: `{files_common_prefix or '(none)'}`",
			"",
			"| File | Baseline Path | Current Path |",
			"| --- | --- | --- |",
		])
		for item in shared_runtime_files:
			current_path = item.get("current_path", "")
			baseline_path = item.get("baseline_path", "")
			_path_prefix, path_suffixes = split_common_path_prefix(baseline_path, current_path)
			file_name = Path(current_path).name or Path(baseline_path).name or "(unknown)"
			lines.append(
				f"| {format_markdown_table_cell(file_name)} | {format_markdown_table_cell(path_suffixes[0])} | {format_markdown_table_cell(path_suffixes[1])} |"
			)
	else:
		lines.extend(["", "No shared runtime files participated in the diff."])
	if runtime_operator_counts:
		lines.extend([
			"",
			"| Operator ID | Segment | Changed Rows |",
			"| --- | --- | ---: |",
		])
		for operator_id, count in sorted(runtime_operator_counts.items()):
			segment_value = ", ".join(sorted(runtime_operator_segments.get(operator_id, set()))) or "(unknown)"
			lines.append(
				f"| {format_markdown_table_cell(operator_id)} | {format_markdown_table_cell(segment_value)} | {count} |"
			)
	else:
		lines.extend(["", "No runtime row changes found."])

	changed_operators = operator_spec_diff.get("changed_operators", [])
	if changed_operators:
		lines.extend([
			"",
			"## Operator Spec Changes",
			"",
			"| Operator ID | Fields Changed |",
			"| --- | --- |",
		])
		for item in changed_operators:
			lines.append(
				f"| {item.get('operator_id', '')} | {', '.join(change['field'] for change in item.get('changes', []))} |"
			)

	runtime_examples = []
	for item in runtime_diff.get("per_file", []):
		runtime_examples.extend(item.get("changed_rows", []))
	if runtime_examples:
		runtime_rows_by_operator: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
		for row in runtime_examples:
			runtime_rows_by_operator[row.get("operator_id", "(unknown)")].append(row)
		lines.extend([
			"",
			"### Runtime Changes By Operator",
			"",
		])
		for operator_id in sorted(runtime_rows_by_operator):
			lines.extend([
				f"#### Operator {operator_id}",
				"",
				"| Submission | Component | Segment | Field | Baseline | Current |",
				"| --- | --- | --- | --- | --- | --- |",
			])
			for row in sorted(
				runtime_rows_by_operator[operator_id],
				key=lambda item: (
					item.get("submission_id", ""),
					item.get("component_id", ""),
					item.get("segment_id", ""),
				),
			):
				for change in row.get("changes", []):
					lines.append(
						"| {submission} | {component} | {segment} | {field} | {baseline} | {current} |".format(
							submission=format_markdown_table_cell(row.get("submission_id", "")),
							component=format_markdown_table_cell(row.get("component_id", "")),
							segment=format_markdown_table_cell(row.get("segment_id", "")),
							field=format_markdown_table_cell(change.get("field", "")),
							baseline=format_markdown_table_cell(change.get("baseline", "")),
							current=format_markdown_table_cell(change.get("current", "")),
						)
					)
			lines.append("")

	runtime_extracted_segments_by_id = build_runtime_extracted_segments_by_id(runtime_diff)

	lines.extend([
		"",
		"## Stitched Diff Summary",
		"",
		f"- Current stitched dir: `{stitched_diff.get('current_dir', '')}`",
		f"- Baseline stitched dir: `{stitched_diff.get('baseline_dir', '')}`",
		f"- Shared stitched files: {stitched_diff.get('shared_file_count', 0)}",
		f"- Added stitched files: {len(stitched_diff.get('added_files', []))}",
		f"- Removed stitched files: {len(stitched_diff.get('removed_files', []))}",
	])
	stitched_examples = []
	for item in stitched_diff.get("per_file", []):
		stitched_examples.extend(item.get("changed_rows", []))
	stitched_examples = stitched_examples[:12]
	if stitched_examples:
		lines.extend([
			"",
			"### Stitched Change Examples",
			"",
		])
		for row in stitched_examples:
			lines.extend([
				f"#### Submission {row.get('submission_id', '')} / {row.get('component_id', '')}",
				"",
				f"- Fields changed: {', '.join(change['field'] for change in row.get('changes', []))}",
			])
			response_text = row.get("source_response_text", "").strip()
			if response_text:
				lines.extend([
					"- Source text:",
					"",
					"```text",
					response_text,
					"```",
				])
			for change in row.get("changes", [])[:12]:
				field = change.get("field", "unknown")
				baseline_value = format_markdown_table_cell(change.get("baseline", ""))
				current_value = format_markdown_table_cell(change.get("current", ""))
				lines.extend([
					f"- {field}",
					"",
					"| Version | Value |",
					"| --- | --- |",
					f"| baseline | {baseline_value} |",
					f"| current | {current_value} |",
				])
			lines.append("")
	else:
		lines.extend(["", "No stitched row changes found."])

	all_segment_ids = sorted(runtime_extracted_segments_by_id)
	if all_segment_ids:
		segment_rows: list[dict[str, Any]] = []
		for segment_id in all_segment_ids:
			detail = segment_match_details.get(segment_id, {})
			match_rows = len(detail.get("matches", []))
			non_match_rows = len(detail.get("non_matches", []))
			texts_examined = match_rows + non_match_rows
			unique_extracted_texts = len(runtime_extracted_segments_by_id.get(segment_id, {}))
			distinct_components = len(
				{
					str(row.get("component_id", "")).strip()
					for row in (detail.get("matches", []) + detail.get("non_matches", []))
					if str(row.get("component_id", "")).strip()
				}
			)
			distinct_submissions = len(
				{
					str(row.get("submission_id", "")).strip()
					for row in (detail.get("matches", []) + detail.get("non_matches", []))
					if str(row.get("submission_id", "")).strip()
				}
			)
			segment_rows.append(
				{
					"segment_id": segment_id,
					"operators": ", ".join(detail.get("operator_ids", [])) or "(none)",
					"texts_examined": texts_examined,
					"match_rows": match_rows,
					"non_match_rows": non_match_rows,
					"unique_extracted_texts": unique_extracted_texts,
					"distinct_components": distinct_components,
					"distinct_submissions": distinct_submissions,
				}
			)

		def format_share_of_texts_examined(count: int, texts_examined: int) -> str:
			if texts_examined <= 0:
				return f"{count} (0.0%)"
			return f"{count} ({(count / texts_examined) * 100:.1f}%)"

		lines.extend([
			"",
			"## Segment Metadata Overview",
			"",
			render_markdown_table(
				[
					"segment_id",
					"operators",
					"texts examined",
					"match rows",
					"non-match rows",
					"unique extracted texts",
				],
				[
					[
						format_markdown_table_cell(str(row["segment_id"])),
						format_markdown_table_cell(str(row["operators"])),
						format_markdown_table_cell(str(row["texts_examined"])),
						format_markdown_table_cell(format_share_of_texts_examined(int(row["match_rows"]), int(row["texts_examined"]))),
						format_markdown_table_cell(format_share_of_texts_examined(int(row["non_match_rows"]), int(row["texts_examined"]))),
						format_markdown_table_cell(str(row["unique_extracted_texts"])),
					]
					for row in segment_rows
				],
			),
			"",
			render_markdown_table(
				[
					"segment_id",
					"operators",
					"texts examined",
					"",
					"distinct components",
					"distinct submissions",
				],
				[
					[
						format_markdown_table_cell(str(row["segment_id"])),
						format_markdown_table_cell(str(row["operators"])),
						format_markdown_table_cell(str(row["texts_examined"])),
						"",
						format_markdown_table_cell(str(row["distinct_components"])),
						format_markdown_table_cell(str(row["distinct_submissions"])),
					]
					for row in segment_rows
				],
			),
			"",
			"## Appendix: Current Extracted Segments By Segment Type",
			"",
			"This appendix has been moved to a separate markdown file.",
			f"- Appendix file: `{payload.get('segment_appendix_report', '')}`",
		])

	if segment_match_details:
		lines.extend([
			"",
			"## Segment Detail Files",
			"",
			"Detailed match and non-match tables are emitted as separate markdown files, one per current registry `segment_id`.",
			"",
			"| Segment ID | Operators | Match Rows | Non-Match Rows | Output File |",
			"| --- | --- | ---: | ---: | --- |",
		])
		for segment_id, detail in segment_match_details.items():
			operator_text = ", ".join(detail.get("operator_ids", [])) or "(none)"
			match_rows = detail.get("matches", [])
			non_match_rows = detail.get("non_matches", [])
			output_file = payload.get("segment_detail_reports", {}).get(segment_id, "")
			lines.append(
				"| {segment_id} | {operators} | {match_count} | {non_match_count} | {output_file} |".format(
					segment_id=format_markdown_table_cell(segment_id),
					operators=format_markdown_table_cell(operator_text),
					match_count=len(match_rows),
					non_match_count=len(non_match_rows),
					output_file=format_markdown_table_cell(output_file),
				)
			)

	return "\n".join(lines).rstrip() + "\n"


def main() -> int:
	args = parse_args()
	script_path = Path(__file__).resolve()
	pipeline_paths_path = resolve_pipeline_paths_path(script_path)
	current_release, payload, current_operator_specs_path = collect_current_release_context(
		pipeline_paths_path,
		layer0_config_key=args.layer0_config_key,
	)
	_segmentation_case_type, _operator_spec_type, _execute_operator, load_operator_specs = load_pipeline_runtime(
		pipeline_paths_path
	)
	baseline_release = discover_baseline_release(
		current_operator_specs_path=current_operator_specs_path,
		current_release=current_release,
		baseline_iteration_arg=args.baseline_iteration,
		baseline_run_arg=args.baseline_run,
		allow_same_release_baseline=(args.layer0_config_key != "layer0_calibration"),
	)
	if not baseline_release.get("registry_file_version"):
		baseline_operator_specs_path = resolve_operator_specs_path_for_release(
			current_operator_specs_path,
			baseline_release,
		)
		if baseline_operator_specs_path is not None:
			baseline_release.update(parse_release_from_operator_specs_path(baseline_operator_specs_path))
	else:
		baseline_operator_specs_path = resolve_operator_specs_path_for_release(
			current_operator_specs_path,
			baseline_release,
		)
	current_runtime_dir = resolve_layer0_artifact_dir(
		pipeline_paths_path=pipeline_paths_path,
		payload=payload,
		release_config=current_release,
		config_path=[args.layer0_config_key, "layer0_run_operator_engine", "output"],
	)
	baseline_runtime_dir = resolve_layer0_artifact_dir(
		pipeline_paths_path=pipeline_paths_path,
		payload=payload,
		release_config=baseline_release,
		config_path=[args.layer0_config_key, "layer0_run_operator_engine", "output"],
	)
	current_stitched_dir = resolve_layer0_artifact_dir(
		pipeline_paths_path=pipeline_paths_path,
		payload=payload,
		release_config=current_release,
		config_path=[args.layer0_config_key, "layer0_postprocess_segments", "output"],
	)
	baseline_stitched_dir = resolve_layer0_artifact_dir(
		pipeline_paths_path=pipeline_paths_path,
		payload=payload,
		release_config=baseline_release,
		config_path=[args.layer0_config_key, "layer0_postprocess_segments", "output"],
	)
	runtime_diff = compare_artifact_dirs(
		current_dir=current_runtime_dir,
		baseline_dir=baseline_runtime_dir,
		matcher_suffix="_output.csv",
		comparator=compare_runtime_files,
	)
	stitched_diff = compare_artifact_dirs(
		current_dir=current_stitched_dir,
		baseline_dir=baseline_stitched_dir,
		matcher_suffix="_output-wide-stitched.csv",
		comparator=compare_stitched_files,
	)
	operator_spec_diff = {}
	current_operator_specs = load_operator_specs(str(current_operator_specs_path))
	if baseline_operator_specs_path is not None and baseline_operator_specs_path.is_file():
		baseline_operator_specs = load_operator_specs(str(baseline_operator_specs_path))
		operator_spec_diff = build_operator_spec_diff(
			current_specs=current_operator_specs,
			baseline_specs=baseline_operator_specs,
		)
	staleness = build_staleness_summary(
		current_operator_specs_path,
		runtime_diff.get("current_files", []) + stitched_diff.get("current_files", []),
	)
	output_md_path, output_json_path = resolve_report_output_paths(
		payload=payload,
		layer0_config_key=args.layer0_config_key,
		pipeline_paths_path=pipeline_paths_path,
		current_release=current_release,
		baseline_release=baseline_release,
		output_md_arg=args.output_md,
		output_json_arg=args.output_json,
	)
	assignment_id = resolve_assignment_prefix_from_output(output_md_path)
	segment_match_details = build_current_segment_match_details(
		current_runtime_files=runtime_diff.get("current_files", []),
		current_stitched_files=stitched_diff.get("current_files", []),
		current_operator_specs=current_operator_specs,
	)
	segment_detail_output_paths = build_segment_match_detail_output_paths(
		main_output_md_path=output_md_path,
		current_release=current_release,
		segment_match_details=segment_match_details,
	)
	segment_appendix_output_path = build_segment_appendix_output_path(main_output_md_path=output_md_path)
	report_payload = {
		"current_release": current_release,
		"baseline_release": baseline_release,
		"runtime_diff": runtime_diff,
		"stitched_diff": stitched_diff,
		"operator_spec_diff": operator_spec_diff,
		"staleness": staleness,
		"assignment_id": assignment_id,
		"current_segment_match_details": segment_match_details,
		"segment_detail_reports": {
			segment_id: str(path)
			for segment_id, path in segment_detail_output_paths.items()
		},
		"segment_appendix_report": str(segment_appendix_output_path),
	}
	output_json_path.parent.mkdir(parents=True, exist_ok=True)
	output_json_path.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")
	output_md_path.parent.mkdir(parents=True, exist_ok=True)
	output_md_path.write_text(build_markdown_report(report_payload), encoding="utf-8")
	segment_appendix_output_path.write_text(
		build_segment_appendix_markdown_report(report_payload, main_report_path=output_md_path),
		encoding="utf-8",
	)
	for segment_id, detail in segment_match_details.items():
		segment_output_path = segment_detail_output_paths[segment_id]
		segment_output_path.write_text(
			build_segment_match_detail_report(
				assignment_id=assignment_id,
				segment_id=segment_id,
				detail=detail,
				current_release=current_release,
				main_report_path=output_md_path,
			),
			encoding="utf-8",
		)
	print(f"report_md={output_md_path}")
	print(f"report_json={output_json_path}")
	print(f"segment_appendix_report={segment_appendix_output_path}")
	for segment_id, segment_output_path in sorted(segment_detail_output_paths.items()):
		print(f"segment_report[{segment_id}]={segment_output_path}")
	print(f"runtime_changed_rows={runtime_diff['changed_row_count']}")
	print(f"stitched_changed_rows={stitched_diff['changed_row_count']}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())