from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class OperatorSpec:
	assessment_id: str
	component_id: str
	cid: str
	template_id: str
	local_slot: str
	operator_id: str
	operator_identifier: str
	operator_identifier_shortid: str
	operator_short_description: str
	segment_id: str
	output_mode: Literal["span", "status_only"]
	family: str
	anchor_patterns: list[str]
	direction: str | None
	start_rule: str | None
	end_rule: str | None
	stop_markers: list[str]
	target_type: str
	allow_coordination: bool
	skip_later_candidates: bool
	operator_definition: str
	operator_guidance: str
	failure_mode_guidance: str
	decision_procedure: str
	missing_status: str
	ambiguous_status: str
	malformed_status: str
	instance_status: str


@dataclass(frozen=True)
class ExtractionResult:
	submission_id: str
	component_id: str
	operator_id: str
	segment_id: str
	segment_text: str
	extraction_status: Literal["ok", "missing", "ambiguous", "malformed"]
	extraction_notes: str
	confidence: Literal["high", "medium", "low"]
	flags: Literal["none", "needs_review"]


@dataclass(frozen=True)
class RuntimeDiagnostic:
	submission_id: str
	component_id: str
	operator_id: str
	event_type: str
	message: str


@dataclass(frozen=True)
class FamilyExecution:
	segment_text: str
	extraction_status: Literal["ok", "missing", "ambiguous", "malformed"]
	extraction_notes: str
	confidence: Literal["high", "medium", "low"]
	flags: Literal["none", "needs_review"]