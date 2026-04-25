"""Family executors for deterministic Layer 0 span extraction.

This module turns compiled OperatorSpec fields into runtime behavior, including
anchor matching, anchor-precondition policies, stop-marker boundaries,
coordination controls, and boundary_misparse diagnostics when boundary recovery
is likely incomplete.
"""

from __future__ import annotations

from .boundaries import find_anchor_occurrences, find_first_stop_marker, find_left_boundary, trim_span
from .diagnostics import disagreement_note
from .models import FamilyExecution, OperatorSpec
from .nlp_utils import (
	first_right_noun_chunk,
	has_likely_np_continuation,
	has_plausible_nounish_candidate,
	nearest_left_noun_chunk,
	parse_text,
)


def _missing_result(note: str) -> FamilyExecution:
	return FamilyExecution(
		segment_text="",
		extraction_status="missing",
		extraction_notes=note,
		confidence="high",
		flags="needs_review" if note else "none",
	)


def _ambiguous_result(note: str) -> FamilyExecution:
	return FamilyExecution(
		segment_text="",
		extraction_status="ambiguous",
		extraction_notes=note,
		confidence="medium",
		flags="needs_review",
	)


def _malformed_result(note: str) -> FamilyExecution:
	return FamilyExecution(
		segment_text="",
		extraction_status="malformed",
		extraction_notes=note,
		confidence="low",
		flags="needs_review",
	)


def _ok_result(segment_text: str, confidence: str = "high", note: str = "", needs_review: bool = False) -> FamilyExecution:
	return FamilyExecution(
		segment_text=segment_text,
		extraction_status="ok",
		extraction_notes=note,
		confidence=confidence,
		flags="needs_review" if needs_review else "none",
	)


def _boundary_misparse_result(
	segment_text: str,
	*,
	note: str,
	confidence: str = "medium",
	status: str = "ok",
) -> FamilyExecution:
	return FamilyExecution(
		segment_text=segment_text,
		extraction_status=status,
		extraction_notes=note,
		confidence=confidence,
		flags="boundary_misparse",
	)



def _first_anchor(text: str, spec: OperatorSpec) -> tuple[int, int, str] | None:
	if spec.anchor_selection_policy == "first_after_precondition":
		if not spec.anchor_precondition_patterns:
			return None
		precondition_occurrences = find_anchor_occurrences(text, spec.anchor_precondition_patterns)
		if not precondition_occurrences:
			return None
		search_start = precondition_occurrences[0][1]
		anchor_occurrences = [
			occurrence
			for occurrence in find_anchor_occurrences(text, spec.anchor_patterns)
			if occurrence[0] >= search_start
		]
		if not anchor_occurrences:
			return None
		return anchor_occurrences[0]
	occurrences = find_anchor_occurrences(text, spec.anchor_patterns)
	if not occurrences:
		return None
	return occurrences[0]


def _right_scan_stop_index(text: str, anchor_end: int, spec: OperatorSpec) -> int | None:
	if not spec.allow_coordination:
		return find_first_stop_marker(text, anchor_end, spec.stop_markers)
	filtered_markers = [
		marker
		for marker in spec.stop_markers
		if marker not in {"comma", "clause_boundary", "comma_new_clause"}
	]
	if not filtered_markers:
		return None
	return find_first_stop_marker(text, anchor_end, filtered_markers)


def run_left_np_before_anchor(text: str, spec: OperatorSpec) -> FamilyExecution:
	anchor = _first_anchor(text, spec)
	if anchor is None:
		return _missing_result("anchor not found")
	anchor_start, _, _ = anchor
	boundary_start = find_left_boundary(text, anchor_start, spec.stop_markers)
	context = text[boundary_start:anchor_start]
	trimmed_context = trim_span(context)
	if not trimmed_context:
		return _missing_result("anchor found but no recoverable pre-anchor noun phrase")
	doc = parse_text(text)
	chunk = nearest_left_noun_chunk(doc, anchor_start, minimum_start=boundary_start)
	if chunk is not None:
		chunk_start, chunk_end, chunk_text = chunk
		segment_text = trim_span(text[chunk_start:chunk_end])
		if segment_text:
			needs_review = trimmed_context != segment_text
			note = disagreement_note("parser and boundary heuristics disagreed") if needs_review else ""
			confidence = "medium" if needs_review else "high"
			return _ok_result(segment_text, confidence=confidence, note=note, needs_review=needs_review)
	if len(trimmed_context.split()) > 8:
		return _ambiguous_result("multiple candidate noun phrase boundaries")
	return _ok_result(trimmed_context, confidence="medium", note="fallback pre-anchor span recovery", needs_review=True)


def run_right_np_after_anchor_before_marker(text: str, spec: OperatorSpec) -> FamilyExecution:
	anchor = _first_anchor(text, spec)
	if anchor is None:
		return _missing_result("anchor not found")
	_, anchor_end, _ = anchor
	stop_index = _right_scan_stop_index(text, anchor_end, spec)
	doc = parse_text(text)
	chunk = first_right_noun_chunk(
		doc,
		anchor_end,
		stop_index,
		allow_coordination=spec.allow_coordination,
		candidate_selection_policy=spec.candidate_selection_policy,
	)
	right_limit = stop_index if stop_index is not None else len(text)
	if chunk is not None:
		chunk_start, chunk_end, chunk_text = chunk
		segment_text = trim_span(text[chunk_start:chunk_end])
		if segment_text:
			if has_likely_np_continuation(
				text,
				chunk_end,
				right_limit,
				allow_coordination=spec.allow_coordination,
			):
				return _boundary_misparse_result(
					segment_text,
					note="candidate found but appears truncated before a likely local continuation",
				)
			return _ok_result(segment_text)
	span_end = right_limit
	fallback_text = trim_span(text[anchor_end:span_end])
	if not fallback_text:
		if has_plausible_nounish_candidate(text, anchor_end, len(text)):
			return _boundary_misparse_result(
				"",
				note="anchor found but boundary recovery failed despite a plausible local candidate",
				status="missing",
				confidence="low",
			)
		return _missing_result("anchor found but no recoverable post-anchor noun phrase")
	if len(fallback_text.split()) > 10:
		return _ambiguous_result("multiple candidate noun phrase boundaries")
	return _boundary_misparse_result(
		fallback_text,
		note="fallback post-anchor span recovery; boundary may be imprecise",
	)


def run_span_after_marker_before_marker(text: str, spec: OperatorSpec) -> FamilyExecution:
	anchor = _first_anchor(text, spec)
	if anchor is None:
		return _missing_result("anchor not found")
	_, anchor_end, _ = anchor
	stop_index = _right_scan_stop_index(text, anchor_end, spec)
	doc = parse_text(text)
	chunk = first_right_noun_chunk(
		doc,
		anchor_end,
		stop_index,
		allow_coordination=spec.allow_coordination,
		stop_on_infinitive=True,
		candidate_selection_policy=spec.candidate_selection_policy,
	)
	segment_text = ""
	if chunk is not None:
		chunk_start, chunk_end, chunk_text = chunk
		segment_text = trim_span(text[chunk_start:chunk_end])
	if not segment_text:
		span_end = stop_index if stop_index is not None else len(text)
		segment_text = trim_span(text[anchor_end:span_end])
	if not segment_text:
		if has_plausible_nounish_candidate(text, anchor_end, len(text)):
			return _boundary_misparse_result(
				"",
				note="anchor found but span boundary recovery failed despite a plausible local candidate",
				status="missing",
				confidence="low",
			)
		return _missing_result("anchor found but no recoverable span after marker")
	if len(segment_text.split()) > 14:
		return _ambiguous_result("marker span boundary unclear")
	return _ok_result(segment_text)


def run_local_effect_phrase_after_marker(text: str, spec: OperatorSpec) -> FamilyExecution:
	anchor = _first_anchor(text, spec)
	if anchor is None:
		if spec.anchor_selection_policy == "first_after_precondition":
			return _missing_result("workflow/effect anchor sequence not found")
		return _missing_result("anchor not found")
	_, anchor_end, _ = anchor
	stop_index = find_first_stop_marker(text, anchor_end, spec.stop_markers)
	span_end = stop_index if stop_index is not None else len(text)
	segment_text = trim_span(text[anchor_end:span_end])
	if not segment_text:
		return _missing_result("anchor found but no recoverable local effect phrase")
	if len(segment_text.split()) > 18:
		return _ambiguous_result("local effect phrase boundary unclear")
	return _ok_result(segment_text, confidence="medium" if spec.allow_coordination else "high")


def run_status_only_anchor_detector(text: str, spec: OperatorSpec) -> FamilyExecution:
	anchor = _first_anchor(text, spec)
	if anchor is None:
		return _missing_result("anchor not found")
	return _ok_result("")


def run_claim_text_passthrough_if_anchor(text: str, spec: OperatorSpec) -> FamilyExecution:
	anchor = _first_anchor(text, spec)
	if anchor is None:
		return _missing_result("anchor not found")
	segment_text = trim_span(text)
	if not segment_text:
		return _missing_result("anchor found but claim text is empty")
	return _ok_result(segment_text)


def run_claim_text_passthrough_no_anchor(text: str, spec: OperatorSpec) -> FamilyExecution:
	segment_text = trim_span(text)
	if not segment_text:
		return _missing_result("claim text is empty")
	return _ok_result(segment_text)


FAMILY_EXECUTORS = {
	"left_np_before_anchor": run_left_np_before_anchor,
	"right_np_after_anchor_before_marker": run_right_np_after_anchor_before_marker,
	"span_after_marker_before_marker": run_span_after_marker_before_marker,
	"local_effect_phrase_after_marker": run_local_effect_phrase_after_marker,
	"status_only_anchor_detector": run_status_only_anchor_detector,
	"claim_text_passthrough_if_anchor": run_claim_text_passthrough_if_anchor,
	"claim_text_passthrough_no_anchor": run_claim_text_passthrough_no_anchor,
}