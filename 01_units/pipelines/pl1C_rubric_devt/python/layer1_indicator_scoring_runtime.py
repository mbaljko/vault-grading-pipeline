#!/usr/bin/env python3
"""Shared deterministic runtime for generated Layer 1 indicator scorers.

The Layer 1 deterministic path compiles machine-readable indicator payloads into
small Python modules. Those generated modules delegate the matching mechanics to
this runtime so the policy implementation stays centralized and auditable.
"""

from __future__ import annotations

import re
from typing import Mapping


LABEL_LINE_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")
LEADING_ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
CONJUNCTION_SPLIT_RE = re.compile(r"\s+(?:and|or|&)\s+", re.IGNORECASE)


def normalize_whitespace(value: str) -> str:
	return " ".join(value.split())


def normalize_text(value: object, rule: str) -> str:
	text = str(value or "")
	if not text.strip():
		return ""
	normalized = text.replace("\r\n", "\n").replace("\r", "\n")
	if rule in {"lowercase", "lowercase_trim"}:
		normalized = normalized.lower()
	return normalize_whitespace(normalized).strip() if rule.endswith("trim") else normalized.strip()


def extract_candidate_units(value: object, rule: str) -> list[str]:
	text = str(value or "")
	if not text.strip():
		return []
	candidates: list[str] = []
	seen: set[str] = set()
	for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
		line = raw_line.strip()
		if not line or LABEL_LINE_RE.fullmatch(line):
			continue
		for raw_part in line.split(";"):
			normalized = normalize_text(raw_part, rule)
			if not normalized or normalized in seen:
				continue
			seen.add(normalized)
			candidates.append(normalized)
	whole_text = normalize_text(text, rule)
	if whole_text and whole_text not in seen:
		candidates.append(whole_text)
	return candidates


def strip_leading_article(value: str) -> str:
	return LEADING_ARTICLE_RE.sub("", value, count=1).strip()


def expand_candidates_with_conjuncts(candidates: list[str]) -> list[str]:
	expanded_candidates: list[str] = []
	seen_candidates: set[str] = set()
	for candidate in candidates:
		candidate_variants = [candidate]
		candidate_variants.extend(part.strip() for part in CONJUNCTION_SPLIT_RE.split(candidate))
		for variant in candidate_variants:
			if variant and variant not in seen_candidates:
				seen_candidates.add(variant)
				expanded_candidates.append(variant)
	return expanded_candidates


def resolve_submission_id(row: Mapping[str, object]) -> str:
	for field_name in ["submission_id", "participant_id"]:
		value = str(row.get(field_name, "") or "").strip()
		if value:
			return value
	return ""


def resolve_component_id(row: Mapping[str, object], component_id: str) -> str:
	value = str(row.get("component_id", "") or "").strip()
	return value or component_id


def resolve_indicator_text(row: Mapping[str, object], component_id: str, payload: Mapping[str, object]) -> str:
	bound_segment_id = str(payload.get("bound_segment_id", "") or "").strip()
	if bound_segment_id:
		segment_field = f"segment_text_{component_id}__{bound_segment_id}"
		segment_value = str(row.get(segment_field, "") or "").strip()
		if segment_value:
			return segment_value
	for field_name in ["evidence_text", "response_text"]:
		field_value = str(row.get(field_name, "") or "").strip()
		if field_value:
			return field_value
	return ""


def contains_any_substring(text: str, terms: list[str], rule: str) -> bool:
	normalized_text = normalize_text(text, rule)
	return any(normalize_text(term, rule) in normalized_text for term in terms if normalize_text(term, rule))


def exact_or_alias_match(candidates: list[str], payload: Mapping[str, object], rule: str) -> bool:
	allowed_terms = {
		normalize_text(term, rule)
		for term in payload.get("allowed_terms", [])
		if normalize_text(term, rule)
	}
	allowed_aliases = {
		normalize_text(alias, rule): normalize_text(canonical, rule)
		for alias, canonical in dict(payload.get("allowed_aliases", {})).items()
		if normalize_text(alias, rule) and normalize_text(canonical, rule)
	}
	for candidate in candidates:
		if candidate in allowed_terms:
			return True
		canonical = allowed_aliases.get(candidate)
		if canonical and canonical in allowed_terms:
			return True
	return False


def exact_or_alias_article_insensitive_match(candidates: list[str], payload: Mapping[str, object], rule: str) -> bool:
	normalized_candidates = []
	seen_candidates: set[str] = set()
	for candidate in candidates:
		for variant in (candidate, strip_leading_article(candidate)):
			if variant and variant not in seen_candidates:
				seen_candidates.add(variant)
				normalized_candidates.append(variant)
	allowed_terms = set()
	for term in payload.get("allowed_terms", []):
		normalized_term = normalize_text(term, rule)
		if not normalized_term:
			continue
		allowed_terms.add(normalized_term)
		stripped_term = strip_leading_article(normalized_term)
		if stripped_term:
			allowed_terms.add(stripped_term)
	allowed_aliases = {}
	for alias, canonical in dict(payload.get("allowed_aliases", {})).items():
		normalized_alias = normalize_text(alias, rule)
		normalized_canonical = normalize_text(canonical, rule)
		if not normalized_alias or not normalized_canonical:
			continue
		for alias_variant in (normalized_alias, strip_leading_article(normalized_alias)):
			if alias_variant:
				allowed_aliases[alias_variant] = normalized_canonical
	for candidate in normalized_candidates:
		if candidate in allowed_terms:
			return True
		canonical = allowed_aliases.get(candidate)
		if canonical and canonical in allowed_terms:
			return True
	return False


def exact_or_alias_article_insensitive_any_conjunct_match(
	candidates: list[str],
	payload: Mapping[str, object],
	rule: str,
) -> bool:
	return exact_or_alias_article_insensitive_match(
		expand_candidates_with_conjuncts(candidates),
		payload,
		rule,
	)


def role_or_term_match(candidates: list[str], payload: Mapping[str, object], rule: str) -> bool:
	combined_payload = {
		"allowed_terms": list(payload.get("allowed_terms", [])) + list(payload.get("allowed_roles", [])),
		"allowed_aliases": dict(payload.get("allowed_aliases", {})),
	}
	return exact_or_alias_match(candidates, combined_payload, rule)


def co_occurrence_match(text: str, payload: Mapping[str, object], rule: str) -> bool:
	normalized_text = normalize_text(text, rule)
	minimum_match_count = int(payload.get("minimum_match_count_per_group", 0) or 0)
	required_term_groups = dict(payload.get("required_term_groups", {}))
	if not required_term_groups:
		return False
	for group_terms in required_term_groups.values():
		matched_terms = {
			normalize_text(term, rule)
			for term in group_terms
			if normalize_text(term, rule) and normalize_text(term, rule) in normalized_text
		}
		if len(matched_terms) < max(minimum_match_count, 1):
			return False
	return True


def evaluate_match_policy(text: str, payload: Mapping[str, object]) -> bool:
	rule = str(payload.get("normalisation_rule", "") or "").strip()
	match_policy = str(payload.get("match_policy", "") or "").strip()
	candidates = extract_candidate_units(text, rule)
	if match_policy == "substring_any":
		return contains_any_substring(text, list(payload.get("allowed_terms", [])), rule)
	if match_policy == "exact_or_alias":
		return exact_or_alias_match(candidates, payload, rule)
	if match_policy == "exact_or_alias_article_insensitive":
		return exact_or_alias_article_insensitive_match(candidates, payload, rule)
	if match_policy == "exact_or_alias_article_insensitive_any_conjunct":
		return exact_or_alias_article_insensitive_any_conjunct_match(candidates, payload, rule)
	if match_policy == "exact_or_alias_or_role":
		return role_or_term_match(candidates, payload, rule)
	if match_policy == "co_occurrence":
		return co_occurrence_match(text, payload, rule)
	if match_policy == "absence_check":
		return True
	raise ValueError(f"Unsupported Layer 1 match_policy: {match_policy}")


def apply_decision_rule(text: str, payload: Mapping[str, object]) -> tuple[str, str]:
	rule = str(payload.get("normalisation_rule", "") or "").strip()
	decision_rule = str(payload.get("decision_rule", "") or "").strip()
	excluded_terms = [normalize_text(term, rule) for term in payload.get("excluded_terms", []) if normalize_text(term, rule)]
	normalized_text = normalize_text(text, rule)
	has_excluded = any(term in normalized_text for term in excluded_terms)
	policy_match = evaluate_match_policy(text, payload)
	if decision_rule == "present_if_any_allowed_term_found":
		return ("present" if policy_match else "not_present", "none")
	if decision_rule == "present_if_exact_match_or_alias_and_not_excluded":
		return ("present" if policy_match and not has_excluded else "not_present", "none")
	if decision_rule == "present_if_matches_stage_or_role_and_not_excluded":
		return ("present" if policy_match and not has_excluded else "not_present", "none")
	if decision_rule == "present_if_minimum_group_matches_met_and_not_excluded":
		return ("present" if policy_match and not has_excluded else "not_present", "none")
	if decision_rule == "present_if_no_excluded_terms_found":
		return ("present" if not has_excluded else "not_present", "none")
	if decision_rule == "present_if_any_allowed_term_found_and_not_only_excluded":
		return ("present" if policy_match else "not_present", "none")
	return ("present" if policy_match else "not_present", "none")


def score_indicator_from_row(
	row: Mapping[str, object],
	*,
	component_id: str,
	indicator_id: str,
	payload: Mapping[str, object],
	default_evaluation_notes: str = "",
) -> dict[str, str]:
	resolved_component_id = resolve_component_id(row, component_id)
	text = resolve_indicator_text(row, resolved_component_id, payload)
	if not text:
		return {
			"submission_id": resolve_submission_id(row),
			"component_id": resolved_component_id,
			"indicator_id": indicator_id,
			"evidence_status": "not_present",
			"evaluation_notes": default_evaluation_notes,
			"confidence": "high",
			"flags": "missing_input_text",
		}
	evidence_status, flags = apply_decision_rule(text, payload)
	return {
		"submission_id": resolve_submission_id(row),
		"component_id": resolved_component_id,
		"indicator_id": indicator_id,
		"evidence_status": evidence_status,
		"evaluation_notes": default_evaluation_notes,
		"confidence": "high",
		"flags": flags,
	}


__all__ = [
	"score_indicator_from_row",
]