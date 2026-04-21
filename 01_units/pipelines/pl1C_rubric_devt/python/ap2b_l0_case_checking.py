from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


_RUN_RELEASE_PATH_PATTERN = re.compile(r"/02_runs/iter(?P<iteration>\d+)/stage13/registry_v(?P<registry_version>\d+)/")
_OPERATOR_SPECS_FILENAME_PATTERN = re.compile(r"^(?P<prefix>.+)_v(?P<registry_file_version>\d+)\.json$")


def resolve_pipeline_paths_path(script_path: Path) -> Path:
	raw_path = os.environ.get("AP2B_PIPELINE_PATHS")
	if raw_path:
		resolved = Path(raw_path).resolve()
		if not resolved.exists():
			raise FileNotFoundError(f"AP2B pipeline_paths.json not found: {resolved}")
		return resolved
	for candidate in [script_path.resolve().parent] + list(script_path.resolve().parents):
		pipeline_paths = candidate / "pipeline_paths.json"
		if pipeline_paths.is_file():
			return pipeline_paths.resolve()
	raise FileNotFoundError(f"Could not locate pipeline_paths.json from {script_path.resolve()}")


def load_json(path: Path) -> dict[str, Any]:
	resolved = path.resolve()
	if not resolved.exists():
		raise FileNotFoundError(f"Required JSON file not found: {resolved}")
	payload = json.loads(resolved.read_text(encoding="utf-8"))
	if not isinstance(payload, dict):
		raise ValueError(f"JSON payload must decode to an object: {resolved}")
	return payload


def load_pipeline_runtime(pipeline_paths_path: Path) -> tuple[type[Any], type[Any], Any, Any]:
	pipeline_paths_payload = load_json(pipeline_paths_path)
	pipeline_repo = str(pipeline_paths_payload.get("paths", {}).get("pipeline_repo", "")).strip()
	if not pipeline_repo:
		raise ValueError(f"pipeline_repo not configured in {pipeline_paths_path}")
	python_dir = Path(pipeline_repo) / "01_units/pipelines/pl1C_rubric_devt/python"
	if not python_dir.is_dir():
		raise FileNotFoundError(f"Pipeline python directory not found: {python_dir}")
	if str(python_dir) not in sys.path:
		sys.path.insert(0, str(python_dir))
	from layer0_runtime import SegmentationCase, execute_operator, load_operator_specs
	from layer0_runtime.models import OperatorSpec

	return SegmentationCase, OperatorSpec, execute_operator, load_operator_specs


def expand_template(value: str, release_config: dict[str, str]) -> str:
	expanded = value
	for placeholder, replacement in release_config.items():
		expanded = expanded.replace(f"{{{placeholder}}}", replacement)
	return expanded


def first_non_empty(*values: Any) -> str:
	for value in values:
		if value is None:
			continue
		text = str(value).strip()
		if text:
			return text
	return ""


def build_release_config(payload: dict[str, Any]) -> dict[str, str]:
	shared_releases = payload.get("shared_releases_l1_l2_l3_l4", {})
	iteration = first_non_empty(
		shared_releases.get("calibration", {}).get("iteration"),
	)
	registry_version = first_non_empty(
		shared_releases.get("registry_dir_version"),
		shared_releases.get("calibration", {}).get("iteration"),
	)
	registry_file_version = first_non_empty(
		shared_releases.get("registry_l0_file_version"),
		shared_releases.get("registry_dir_version"),
		shared_releases.get("calibration", {}).get("iteration"),
	)
	scoring_run = first_non_empty(
		shared_releases.get("calibration", {}).get("scoring_run"),
	)
	return {
		"iteration": iteration,
		"registry_file_version": registry_file_version,
		"registry_version": registry_version,
		"scoring_run": scoring_run,
	}


def build_assignment_relative_path(path_config: dict[str, Any], release_config: dict[str, str]) -> str:
	return "".join(
		[
			str(path_config.get("base", "")),
			str(path_config.get("dir", "")),
			str(path_config.get("run", "")),
			expand_template(str(path_config.get("run_relative_subdir", "")), release_config),
			expand_template(str(path_config.get("filename", "")), release_config),
		]
	)


def resolve_operator_specs_path(pipeline_paths_path: Path) -> Path:
	payload = load_json(pipeline_paths_path)
	assignment_pipelines_root = pipeline_paths_path.parent / "01_pipelines"
	release_config = build_release_config(payload)
	operator_specs_input = payload["layer0_calibration"]["layer0_run_operator_engine"]["operator_specs_input"]
	relative_path = build_assignment_relative_path(operator_specs_input, release_config)
	return (assignment_pipelines_root / relative_path).resolve()


def resolve_harness_reports_dir(pipeline_paths_path: Path) -> Path:
	payload = load_json(pipeline_paths_path)
	assignment_pipelines_root = pipeline_paths_path.parent / "01_pipelines"
	release_config = build_release_config(payload)
	diagnostics_output = payload["layer0_calibration"]["layer0_test_harness"]["diagnostics_output"]
	relative_path = build_assignment_relative_path(diagnostics_output, release_config)
	return (assignment_pipelines_root / relative_path).resolve()


def resolve_cases_dir(script_path: Path) -> Path:
	raw_path = os.environ.get("AP2B_L0_CASES_DIR")
	if raw_path:
		return Path(raw_path).resolve()
	return (script_path.resolve().parent / "layer0_test_assets").resolve()


def resolve_case_path(script_path: Path, env_var: str, filename: str) -> Path:
	raw_path = os.environ.get(env_var)
	if raw_path:
		return Path(raw_path).resolve()
	return resolve_cases_dir(script_path) / filename


def load_segmentation_cases(path: Path, segmentation_case_type: type[Any]) -> list[Any]:
	payload = load_json(path)
	rows = payload.get("cases", [])
	if not isinstance(rows, list):
		raise ValueError(f"Case payload must contain a list under 'cases': {path}")
	return [segmentation_case_type.from_dict(row) for row in rows]


def normalize_case_operator_id(component_id: str, operator_id: str) -> str:
	text = str(operator_id).strip()
	if not text:
		return text
	legacy_match = re.fullmatch(r"S\d(\d{2})", text)
	if legacy_match is not None:
		return f"S{legacy_match.group(1)}"
	return text


def make_spec_lookup_key(component_id: str, operator_id: str) -> tuple[str, str]:
	return (str(component_id).strip(), str(operator_id).strip())


def index_specs_by_operator_id(specs: list[Any]) -> dict[tuple[str, str], Any]:
	indexed: dict[tuple[str, str], Any] = {}
	for spec in specs:
		lookup_key = make_spec_lookup_key(spec.component_id, spec.operator_id)
		existing = indexed.get(lookup_key)
		if existing is not None:
			raise ValueError(
				"Duplicate scoped operator_id in AP2B operator specs: "
				f"operator_id={spec.operator_id!r}; component_id={spec.component_id!r}"
			)
		indexed[lookup_key] = spec
	return indexed


def compare_case(case: Any, specs_by_operator_id: dict[tuple[str, str], Any], execute_operator: Any) -> dict[str, Any]:
	normalized_operator_id = normalize_case_operator_id(case.component_id, case.operator_id)
	operator_spec = specs_by_operator_id.get(make_spec_lookup_key(case.component_id, case.operator_id))
	if operator_spec is None:
		operator_spec = specs_by_operator_id.get(make_spec_lookup_key(case.component_id, normalized_operator_id))
	if operator_spec is None:
		return {
			"case_id": case.case_id,
			"status": "failed",
			"mismatches": [
				{
					"field": "operator_id",
					"expected": case.operator_id,
					"observed": None,
					"message": (
						"Missing OperatorSpec for component_id={component_id!r}, operator_id={operator_id!r} "
						"(normalized={normalized!r})"
					).format(
						component_id=case.component_id,
						operator_id=case.operator_id,
						normalized=normalized_operator_id,
					),
				}
			],
		}

	result = execute_operator(case.input_text, operator_spec, case.submission_id)
	mismatches: list[dict[str, Any]] = []

	if operator_spec.component_id != case.component_id:
		mismatches.append(
			{
				"field": "component_id",
				"expected": case.component_id,
				"observed": operator_spec.component_id,
			}
		)
	if operator_spec.segment_id != case.segment_id:
		mismatches.append(
			{
				"field": "segment_id",
				"expected": case.segment_id,
				"observed": operator_spec.segment_id,
			}
		)
	if result.segment_text != case.expected_segment_text:
		mismatches.append(
			{
				"field": "segment_text",
				"expected": case.expected_segment_text,
				"observed": result.segment_text,
			}
		)
	if result.extraction_status != case.expected_extraction_status:
		mismatches.append(
			{
				"field": "extraction_status",
				"expected": case.expected_extraction_status,
				"observed": result.extraction_status,
			}
		)
	if case.expected_confidence is not None and result.confidence != case.expected_confidence:
		mismatches.append(
			{
				"field": "confidence",
				"expected": case.expected_confidence,
				"observed": result.confidence,
			}
		)
	if case.expected_flags is not None and result.flags != case.expected_flags:
		mismatches.append(
			{
				"field": "flags",
				"expected": case.expected_flags,
				"observed": result.flags,
			}
		)

	return {
		"case_id": case.case_id,
		"status": "passed" if not mismatches else "failed",
		"operator_id": case.operator_id,
		"resolved_operator_id": operator_spec.operator_id,
		"group": None,
		"mismatches": mismatches,
		"expected": asdict(case),
		"observed": asdict(result),
	}


def run_case_group(
	*,
	group_name: str,
	cases: list[Any],
	specs_by_operator_id: dict[tuple[str, str], Any],
	execute_operator: Any,
) -> list[dict[str, Any]]:
	results: list[dict[str, Any]] = []
	for case in cases:
		outcome = compare_case(case, specs_by_operator_id, execute_operator)
		outcome["group"] = group_name
		results.append(outcome)
	return results


def run_case_groups(
	*,
	case_groups: list[tuple[str, list[Any]]],
	specs_by_operator_id: dict[tuple[str, str], Any],
	execute_operator: Any,
) -> list[dict[str, Any]]:
	results: list[dict[str, Any]] = []
	for group_name, cases in case_groups:
		results.extend(
			run_case_group(
				group_name=group_name,
				cases=cases,
				specs_by_operator_id=specs_by_operator_id,
				execute_operator=execute_operator,
			)
		)
	return results


def summarize_results(group_results: list[dict[str, Any]]) -> dict[str, Any]:
	total_case_count = len(group_results)
	pass_count = sum(1 for result in group_results if result["status"] == "passed")
	failures = [result for result in group_results if result["status"] == "failed"]
	return {
		"total_case_count": total_case_count,
		"pass_count": pass_count,
		"fail_count": len(failures),
		"failing_case_ids": [result["case_id"] for result in failures],
		"failures": failures,
	}


def print_summary(summary: dict[str, Any]) -> None:
	print(f"total_case_count={summary['total_case_count']}")
	print(f"pass_count={summary['pass_count']}")
	print(f"fail_count={summary['fail_count']}")
	print("failing_case_ids")
	for case_id in summary["failing_case_ids"]:
		print(f"  {case_id}")


def write_json_report(path: Path, payload: dict[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown_summary_report(
	path: Path,
	payload: dict[str, Any],
	*,
	title: str,
	preamble_lines: list[str] | None = None,
) -> None:
	summary = payload["summary"]
	release = payload.get("release", {})
	results = payload.get("results", [])
	case_paths = payload.get("case_paths", {})
	comparison = payload.get("comparison")
	status = "PASS" if summary.get("fail_count", 0) == 0 else "FAIL"
	group_counts: dict[str, dict[str, int]] = {}
	for result in results:
		group_name = str(result.get("group") or "ungrouped")
		counts = group_counts.setdefault(group_name, {"total": 0, "passed": 0, "failed": 0})
		counts["total"] += 1
		if result.get("status") == "passed":
			counts["passed"] += 1
		else:
			counts["failed"] += 1

	lines = [
		f"# {title}",
		"",
		f"Status: **{status}**",
	]

	if preamble_lines:
		lines.extend(["", *preamble_lines])

	lines.extend([
		"",
		"## Summary",
		"",
		f"- Total cases: {summary.get('total_case_count', 0)}",
		f"- Passed: {summary.get('pass_count', 0)}",
		f"- Failed: {summary.get('fail_count', 0)}",
	])

	if group_counts:
		lines.extend([
			"",
			"## Group Breakdown",
			"",
			"| Group | Total | Passed | Failed |",
			"| --- | ---: | ---: | ---: |",
		])
		for group_name in sorted(group_counts):
			counts = group_counts[group_name]
			lines.append(
				f"| {group_name} | {counts['total']} | {counts['passed']} | {counts['failed']} |"
			)

	lines.extend([
		"",
		"## Release",
		"",
		f"- Iteration: {release.get('iteration', '') or 'n/a'}",
		f"- Registry version: {release.get('registry_version', '') or 'n/a'}",
		f"- Registry file version: {release.get('registry_file_version', '') or 'n/a'}",
		f"- Scoring run: {release.get('scoring_run', '') or 'n/a'}",
		f"- Operator specs: `{payload.get('operator_specs_path', '')}`",
	])

	if case_paths:
		lines.extend([
			"",
			"## Case Assets",
			"",
		])
		for case_name in sorted(case_paths):
			lines.append(f"- {case_name}: `{case_paths[case_name]}`")

	if comparison:
		baseline = comparison.get("baseline", {})
		result_diff = comparison.get("result_diff", {})
		spec_diff = comparison.get("spec_diff", {})
		lines.extend([
			"",
			"## Comparison With Previous Release",
			"",
			f"- Baseline iteration: {baseline.get('iteration', '') or 'n/a'}",
			f"- Baseline registry version: {baseline.get('registry_version', '') or 'n/a'}",
			f"- Baseline registry file version: {baseline.get('registry_file_version', '') or 'n/a'}",
			f"- Baseline operator specs: `{baseline.get('operator_specs_path', '') or 'n/a'}`",
			f"- Changed case outputs on this harness set: {result_diff.get('changed_case_count', 0)}",
			f"- Added cases relative to baseline: {result_diff.get('added_case_count', 0)}",
			f"- Removed cases relative to baseline: {result_diff.get('removed_case_count', 0)}",
			f"- Changed operator specs: {spec_diff.get('changed_operator_count', 0)}",
			f"- Added operators: {spec_diff.get('added_operator_count', 0)}",
			f"- Removed operators: {spec_diff.get('removed_operator_count', 0)}",
		])

		changed_cases = result_diff.get("changed_cases", [])
		if changed_cases:
			lines.extend([
				"",
				"### Changed Case Outputs",
				"",
				"| Case ID | Group | Fields Changed | Baseline Segment | Current Segment |",
				"| --- | --- | --- | --- | --- |",
			])
			for changed_case in changed_cases:
				fields_changed = ", ".join(change["field"] for change in changed_case.get("changes", []))
				baseline_observed = changed_case.get("baseline", {}).get("observed", {})
				current_observed = changed_case.get("current", {}).get("observed", {})
				lines.append(
					"| {case_id} | {group} | {fields_changed} | `{baseline_segment}` | `{current_segment}` |".format(
						case_id=changed_case.get("case_id", ""),
						group=changed_case.get("group", "") or "",
						fields_changed=fields_changed or "n/a",
						baseline_segment=str(baseline_observed.get("segment_text", "")),
						current_segment=str(current_observed.get("segment_text", "")),
					)
				)
		else:
			lines.extend([
				"",
				"### Changed Case Outputs",
				"",
				"None.",
			])

		changed_operators = spec_diff.get("changed_operators", [])
		if changed_operators:
			lines.extend([
				"",
				"### Changed Operator Specs",
				"",
				"| Operator ID | Fields Changed |",
				"| --- | --- |",
			])
			for changed_operator in changed_operators:
				field_names = ", ".join(change["field"] for change in changed_operator.get("changes", []))
				lines.append(f"| {changed_operator.get('operator_id', '')} | {field_names or 'n/a'} |")

			for changed_operator in changed_operators:
				lines.extend([
					"",
					f"#### {changed_operator.get('operator_id', '')}",
					"",
				])
				for change in changed_operator.get("changes", []):
					lines.append(
						"- {field}: baseline `{baseline}` current `{current}`".format(
							field=change.get("field", "unknown"),
							baseline=change.get("baseline"),
							current=change.get("current"),
						)
					)
		else:
			lines.extend([
				"",
				"### Changed Operator Specs",
				"",
				"None.",
			])

	failures = summary.get("failures", [])
	if failures:
		lines.extend([
			"",
			"## Failures",
			"",
			"| Case ID | Group | Operator | Mismatch Count |",
			"| --- | --- | --- | ---: |",
		])
		for failure in failures:
			lines.append(
				"| {case_id} | {group} | {operator_id} | {mismatch_count} |".format(
					case_id=failure.get("case_id", ""),
					group=failure.get("group", "") or "",
					operator_id=failure.get("operator_id", "") or "",
					mismatch_count=len(failure.get("mismatches", [])),
				)
			)

		for failure in failures:
			lines.extend([
				"",
				f"### {failure.get('case_id', '')}",
				"",
				f"- Group: {failure.get('group', '') or 'n/a'}",
				f"- Operator ID: {failure.get('operator_id', '') or 'n/a'}",
			])
			for mismatch in failure.get("mismatches", []):
				lines.append(
					"- {field}: expected `{expected}` observed `{observed}`".format(
						field=mismatch.get("field", "unknown"),
						expected=mismatch.get("expected"),
						observed=mismatch.get("observed"),
					)
				)
	else:
		lines.extend([
			"",
			"## Failures",
			"",
			"None.",
		])

	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report_payload(
	*,
	summary: dict[str, Any],
	release_config: dict[str, str],
	operator_specs_path: Path,
	case_paths: dict[str, Path],
	results: list[dict[str, Any]],
) -> dict[str, Any]:
	return {
		"summary": summary,
		"release": release_config,
		"operator_specs_path": str(operator_specs_path),
		"case_paths": {name: str(path) for name, path in case_paths.items()},
		"results": results,
	}


def parse_release_from_operator_specs_path(path: Path) -> dict[str, str]:
	path_text = path.resolve().as_posix()
	path_match = _RUN_RELEASE_PATH_PATTERN.search(path_text)
	filename_match = _OPERATOR_SPECS_FILENAME_PATTERN.match(path.name)
	if path_match is None or filename_match is None:
		return {}
	return {
		"iteration": path_match.group("iteration"),
		"registry_version": path_match.group("registry_version"),
		"registry_file_version": filename_match.group("registry_file_version"),
	}


def discover_previous_operator_specs_path(current_operator_specs_path: Path) -> Path | None:
	current_path = current_operator_specs_path.resolve()
	current_release = parse_release_from_operator_specs_path(current_path)
	if not current_release:
		return None
	runs_root = current_path.parents[4]
	filename_match = _OPERATOR_SPECS_FILENAME_PATTERN.match(current_path.name)
	if filename_match is None:
		return None
	filename_glob = f"{filename_match.group('prefix')}_v*.json"
	current_sort_key = (
		int(current_release["iteration"]),
		int(current_release["registry_version"]),
		int(current_release["registry_file_version"]),
	)
	best_candidate: tuple[tuple[int, int, int], Path] | None = None
	for candidate in runs_root.glob(f"iter*/stage13/registry_v*/00_rubric_sibling_files/{filename_glob}"):
		candidate_path = candidate.resolve()
		if candidate_path == current_path:
			continue
		candidate_release = parse_release_from_operator_specs_path(candidate_path)
		if not candidate_release:
			continue
		candidate_sort_key = (
			int(candidate_release["iteration"]),
			int(candidate_release["registry_version"]),
			int(candidate_release["registry_file_version"]),
		)
		if candidate_sort_key >= current_sort_key:
			continue
		if best_candidate is None or candidate_sort_key > best_candidate[0]:
			best_candidate = (candidate_sort_key, candidate_path)
	if best_candidate is None:
		return None
	return best_candidate[1]


def build_result_diff(
	*,
	current_results: list[dict[str, Any]],
	baseline_results: list[dict[str, Any]],
) -> dict[str, Any]:
	baseline_by_case_id = {result["case_id"]: result for result in baseline_results}
	current_by_case_id = {result["case_id"]: result for result in current_results}
	changed_cases: list[dict[str, Any]] = []
	for case_id in sorted(set(current_by_case_id) & set(baseline_by_case_id)):
		current_result = current_by_case_id[case_id]
		baseline_result = baseline_by_case_id[case_id]
		changes: list[dict[str, Any]] = []
		for field_name in ["status", "mismatches"]:
			if current_result.get(field_name) != baseline_result.get(field_name):
				changes.append(
					{
						"field": field_name,
						"baseline": baseline_result.get(field_name),
						"current": current_result.get(field_name),
					}
				)
		current_observed = current_result.get("observed", {})
		baseline_observed = baseline_result.get("observed", {})
		for field_name in ["segment_text", "extraction_status", "confidence", "flags"]:
			if current_observed.get(field_name) != baseline_observed.get(field_name):
				changes.append(
					{
						"field": field_name,
						"baseline": baseline_observed.get(field_name),
						"current": current_observed.get(field_name),
					}
				)
		if changes:
			changed_cases.append(
				{
					"case_id": case_id,
					"group": current_result.get("group"),
					"changes": changes,
					"baseline": baseline_result,
					"current": current_result,
				}
			)
	added_case_ids = sorted(set(current_by_case_id) - set(baseline_by_case_id))
	removed_case_ids = sorted(set(baseline_by_case_id) - set(current_by_case_id))
	return {
		"changed_case_count": len(changed_cases),
		"changed_cases": changed_cases,
		"added_case_count": len(added_case_ids),
		"added_case_ids": added_case_ids,
		"removed_case_count": len(removed_case_ids),
		"removed_case_ids": removed_case_ids,
	}


def build_operator_spec_diff(
	*,
	current_specs: list[Any],
	baseline_specs: list[Any],
) -> dict[str, Any]:
	def spec_diff_key(spec: Any) -> str:
		operator_identifier = str(getattr(spec, "operator_identifier", "")).strip()
		if operator_identifier:
			return operator_identifier
		return f"{getattr(spec, 'component_id', '')}::{getattr(spec, 'operator_id', '')}"

	current_by_operator_id = {spec_diff_key(spec): asdict(spec) for spec in current_specs}
	baseline_by_operator_id = {spec_diff_key(spec): asdict(spec) for spec in baseline_specs}
	shared_operator_ids = sorted(set(current_by_operator_id) & set(baseline_by_operator_id))
	changed_operators: list[dict[str, Any]] = []
	for operator_id in shared_operator_ids:
		current_spec = current_by_operator_id[operator_id]
		baseline_spec = baseline_by_operator_id[operator_id]
		changes: list[dict[str, Any]] = []
		for field_name in sorted(set(current_spec) | set(baseline_spec)):
			if current_spec.get(field_name) != baseline_spec.get(field_name):
				changes.append(
					{
						"field": field_name,
						"baseline": baseline_spec.get(field_name),
						"current": current_spec.get(field_name),
					}
				)
		if changes:
			changed_operators.append({"operator_id": operator_id, "changes": changes})
	added_operator_ids = sorted(set(current_by_operator_id) - set(baseline_by_operator_id))
	removed_operator_ids = sorted(set(baseline_by_operator_id) - set(current_by_operator_id))
	return {
		"changed_operator_count": len(changed_operators),
		"changed_operators": changed_operators,
		"added_operator_count": len(added_operator_ids),
		"added_operator_ids": added_operator_ids,
		"removed_operator_count": len(removed_operator_ids),
		"removed_operator_ids": removed_operator_ids,
	}


def build_previous_release_comparison(
	*,
	current_operator_specs_path: Path,
	current_operator_specs: list[Any],
	case_groups: list[tuple[str, list[Any]]],
	execute_operator: Any,
	load_operator_specs: Any,
) -> dict[str, Any] | None:
	baseline_operator_specs_path = discover_previous_operator_specs_path(current_operator_specs_path)
	if baseline_operator_specs_path is None:
		return None
	baseline_operator_specs = load_operator_specs(str(baseline_operator_specs_path))
	baseline_specs_by_operator_id = index_specs_by_operator_id(baseline_operator_specs)
	baseline_results = run_case_groups(
		case_groups=case_groups,
		specs_by_operator_id=baseline_specs_by_operator_id,
		execute_operator=execute_operator,
	)
	baseline_release = parse_release_from_operator_specs_path(baseline_operator_specs_path)
	baseline_release["operator_specs_path"] = str(baseline_operator_specs_path)
	return {
		"baseline": baseline_release,
		"result_diff": build_result_diff(
			current_results=run_case_groups(
				case_groups=case_groups,
				specs_by_operator_id=index_specs_by_operator_id(current_operator_specs),
				execute_operator=execute_operator,
			),
			baseline_results=baseline_results,
		),
		"spec_diff": build_operator_spec_diff(
			current_specs=current_operator_specs,
			baseline_specs=baseline_operator_specs,
		),
	}