"""Runtime diagnostic mapping for Layer 0 extraction results.

Extraction results are converted into JSONL-friendly diagnostic events. The
event type preserves explicit boundary_misparse flags so boundary recovery
issues can be audited separately from missing/ambiguous/malformed outcomes.
"""

from __future__ import annotations

from .models import ExtractionResult, RuntimeDiagnostic


def diagnostic_from_result(result: ExtractionResult) -> RuntimeDiagnostic | None:
	if result.extraction_status == "ok" and result.flags == "none":
		return None
	event_type = result.extraction_status
	if result.flags == "boundary_misparse":
		event_type = "boundary_misparse"
	if result.flags == "needs_review" and result.extraction_status == "ok":
		event_type = "needs_review"
	message = result.extraction_notes or f"status={result.extraction_status}; confidence={result.confidence}"
	return RuntimeDiagnostic(
		submission_id=result.submission_id,
		component_id=result.component_id,
		operator_id=result.operator_id,
		event_type=event_type,
		message=message,
	)


def disagreement_note(message: str) -> str:
	return message.strip()