"""Datamodels used by the deterministic Layer 0 operator runtime.

These contracts define registry-derived operator specs, extraction outputs, and
diagnostic payloads. Extraction flags include boundary_misparse to represent
boundary-recovery failures distinct from pure absence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import asdict
from dataclasses import field
from typing import Any, Literal


StopMarker = Literal[
	"comma",
	"sentence_start",
	"conjunction_boundary",
	"through",
	"to",
	"which",
	"that",
	"who",
	"where",
	"within",
	"during",
	"at",
	"before",
	"clause_boundary",
	"shaping",
	"by",
	"comma_new_clause",
	"subordinate_extension",
	"sentence_end",
]


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
	stop_markers: list[StopMarker]
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
	anchor_precondition_patterns: list[str] = field(default_factory=list)
	anchor_selection_policy: str = "first_match"
	candidate_selection_policy: str = "unspecified"
	later_candidate_handling: str = "unspecified"
	requires_prior_segment: str | None = None


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
	flags: Literal["none", "needs_review", "boundary_misparse"]


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
	flags: Literal["none", "needs_review", "boundary_misparse"]


def _validate_optional_choice(field_name: str, value: str | None, allowed_values: set[str]) -> None:
	if value is None:
		return
	if value not in allowed_values:
		raise ValueError(
			f"{field_name} must be one of {sorted(allowed_values)!r} when provided; got {value!r}"
		)


@dataclass(frozen=True)
class SegmentationCase:
	case_id: str
	submission_id: str
	component_id: str
	operator_id: str
	segment_id: str
	input_text: str
	expected_segment_text: str
	expected_extraction_status: str
	expected_confidence: str | None
	expected_flags: str | None
	label: str
	review_note: str | None

	def __post_init__(self) -> None:
		_validate_optional_choice(
			"expected_extraction_status",
			self.expected_extraction_status,
			{"ok", "missing", "ambiguous", "malformed"},
		)
		_validate_optional_choice(
			"expected_confidence",
			self.expected_confidence,
			{"high", "medium", "low"},
		)
		_validate_optional_choice(
			"expected_flags",
			self.expected_flags,
			{"none", "needs_review", "boundary_misparse"},
		)

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)

	def to_json(self, *, indent: int | None = None) -> str:
		return json.dumps(self.to_dict(), indent=indent, sort_keys=False)

	@classmethod
	def from_dict(cls, payload: dict[str, Any]) -> "SegmentationCase":
		return cls(**payload)

	@classmethod
	def from_json(cls, payload: str) -> "SegmentationCase":
		data = json.loads(payload)
		if not isinstance(data, dict):
			raise ValueError("SegmentationCase JSON must decode to an object.")
		return cls.from_dict(data)