from __future__ import annotations

from collections.abc import Iterable, Mapping

from .diagnostics import diagnostic_from_result
from .families import FAMILY_EXECUTORS
from .loader import index_specs_by_component, load_operator_specs, validate_spec, validate_specs
from .models import ExtractionResult, OperatorSpec, RuntimeDiagnostic


def _resolve_submission_id(row: Mapping[str, object]) -> str:
	for field_name in ["submission_id", "source_submission_id", "participant_id", "canonical_submission_id"]:
		value = str(row.get(field_name, "")).strip()
		if value:
			return value
	raise ValueError(f"Runtime row is missing submission_id or equivalent canonical identifier field: {dict(row)!r}")


def validate_runtime_row(row: Mapping[str, object]) -> None:
	_ = _resolve_submission_id(row)
	component_id = str(row.get("component_id", "")).strip()
	response_text = str(row.get("response_text", "")).strip()
	if not component_id:
		raise ValueError(f"Runtime row is missing component_id: {dict(row)!r}")
	if not response_text:
		raise ValueError(f"Runtime row is missing response_text: {dict(row)!r}")


def execute_operator(text: str, spec: OperatorSpec, submission_id: str) -> ExtractionResult:
	validate_spec(spec)
	if spec.family not in FAMILY_EXECUTORS:
		raise ValueError(f"Unknown family encountered during execution: {spec.family!r}")
	executor = FAMILY_EXECUTORS[spec.family]
	family_execution = executor(text, spec)
	return ExtractionResult(
		submission_id=submission_id,
		component_id=spec.component_id,
		operator_id=spec.operator_id,
		segment_id=spec.segment_id,
		segment_text=family_execution.segment_text,
		extraction_status=family_execution.extraction_status,
		extraction_notes=family_execution.extraction_notes,
		confidence=family_execution.confidence,
		flags=family_execution.flags,
	)


def execute_row(row: dict, specs_for_component: list[OperatorSpec]) -> list[ExtractionResult]:
	validate_runtime_row(row)
	submission_id = _resolve_submission_id(row)
	component_id = str(row.get("component_id", "")).strip()
	response_text = str(row.get("response_text", ""))
	if not specs_for_component:
		raise ValueError(f"Unknown component with no matching specs: {component_id!r}")
	results: list[ExtractionResult] = []
	for spec in specs_for_component:
		if spec.component_id != component_id:
			continue
		results.append(execute_operator(response_text, spec, submission_id))
	return results


def execute_batch(rows: list[dict], specs: list[OperatorSpec]) -> tuple[list[ExtractionResult], list[RuntimeDiagnostic]]:
	validate_specs(specs)
	indexed_specs = index_specs_by_component(specs)
	results: list[ExtractionResult] = []
	diagnostics: list[RuntimeDiagnostic] = []
	for row in rows:
		validate_runtime_row(row)
		component_id = str(row.get("component_id", "")).strip()
		if component_id not in indexed_specs:
			raise ValueError(f"Unknown component with no matching specs: {component_id!r}")
		row_results = execute_row(row, indexed_specs[component_id])
		results.extend(row_results)
		for result in row_results:
			diagnostic = diagnostic_from_result(result)
			if diagnostic is not None:
				diagnostics.append(diagnostic)
	return results, diagnostics


def execute_batch_from_spec_path(rows: list[dict], spec_path: str) -> tuple[list[ExtractionResult], list[RuntimeDiagnostic]]:
	specs = load_operator_specs(spec_path)
	return execute_batch(rows, specs)