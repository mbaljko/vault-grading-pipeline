#!/usr/bin/env python3
"""Shared deterministic runtime for generated Layer 1 indicator scorers.

The Layer 1 deterministic path compiles machine-readable indicator payloads into
small Python modules. Those generated modules delegate the matching mechanics to
this runtime so the policy implementation stays centralized and auditable.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Mapping


logger = logging.getLogger(__name__)

LABEL_LINE_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")
LEADING_ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
CONJUNCTION_SPLIT_RE = re.compile(r"\s+and\s+|\s*,\s*", re.IGNORECASE)
MATCH_PREFIX_RE = re.compile(
	r"^(?:rule\s+that|requirement\s+to|institutional\s+demand\s+for|institutional\s+demand\s+of|obligation\s+to)\s+",
	re.IGNORECASE,
)


@dataclass(frozen=True)
class AliasMatch:
	candidate: str
	canonical: str
	matched_text: str
	matched_span: str
	is_alias: bool


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


def strip_leading_match_prefix(value: str) -> str:
	stripped = strip_leading_article(value)
	return MATCH_PREFIX_RE.sub("", stripped, count=1).strip()


def singularize_token(token: str) -> str:
	if len(token) > 3 and token.endswith("ies"):
		return f"{token[:-3]}y"
	if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
		return token[:-1]
	return token


def normalize_inflectional_text(value: str) -> str:
	return " ".join(singularize_token(token) for token in value.split())


def preprocess_candidate_for_match(value: str, rule: str) -> str:
	normalized = normalize_text(value, rule)
	if not normalized:
		return ""
	return strip_leading_match_prefix(normalized)


def expand_candidates_with_suffix_coordination(candidates: list[str], rule: str) -> list[str]:
	expanded_candidates: list[str] = []
	seen_candidates: set[str] = set()
	for candidate in candidates:
		processed_candidate = preprocess_candidate_for_match(candidate, rule)
		if not processed_candidate:
			continue
		logger.debug("Matching original segment '%s' stripped to '%s'", candidate, processed_candidate)
		candidate_variants = [processed_candidate]
		parts = [part.strip() for part in CONJUNCTION_SPLIT_RE.split(processed_candidate) if part.strip()]
		candidate_variants.extend(parts)
		if re.search(r"\s+and\s+", processed_candidate, re.IGNORECASE):
			left, right = re.split(r"\s+and\s+", processed_candidate, maxsplit=1, flags=re.IGNORECASE)
			left = left.strip()
			right_tokens = right.strip().split()
			for suffix_size in range(1, min(2, len(right_tokens)) + 1):
				suffix = " ".join(right_tokens[-suffix_size:])
				synthetic = normalize_whitespace(f"{left} {suffix}").strip()
				if synthetic:
					candidate_variants.append(synthetic)
		for variant in candidate_variants:
			if variant and variant not in seen_candidates:
				seen_candidates.add(variant)
				expanded_candidates.append(variant)
	return expanded_candidates


def expand_candidates_with_conjuncts(candidates: list[str], rule: str) -> list[str]:
	return expand_candidates_with_suffix_coordination(candidates, rule)


def span_contains_excluded_term(span: str, excluded_terms: list[str], rule: str) -> bool:
	normalized_span = normalize_text(span, rule)
	for excluded_term in excluded_terms:
		if not excluded_term:
			continue
		if normalize_inflectional_text(normalized_span) == normalize_inflectional_text(excluded_term):
			return True
	return False


def build_allowed_match_entries(
	allowed_terms: list[str],
	allowed_aliases: Mapping[str, str],
	rule: str,
) -> list[tuple[str, str, bool]]:
	entries: list[tuple[str, str, bool]] = []
	seen_entries: set[tuple[str, str, bool]] = set()
	for term in allowed_terms:
		normalized_term = normalize_text(term, rule)
		if not normalized_term:
			continue
		for variant in (normalized_term, strip_leading_article(normalized_term)):
			entry = (variant, normalized_term, False)
			if variant and entry not in seen_entries:
				seen_entries.add(entry)
				entries.append(entry)
	for alias, canonical in dict(allowed_aliases).items():
		normalized_alias = normalize_text(alias, rule)
		normalized_canonical = normalize_text(canonical, rule)
		if not normalized_alias or not normalized_canonical:
			continue
		for variant in (normalized_alias, strip_leading_article(normalized_alias)):
			entry = (variant, normalized_canonical, True)
			if variant and entry not in seen_entries:
				seen_entries.add(entry)
				entries.append(entry)
	return entries


def resolve_candidate_matches(
	candidate: str,
	allowed_terms: list[str],
	allowed_aliases: Mapping[str, str],
	rule: str,
	excluded_terms: list[str] | None = None,
) -> list[AliasMatch]:
	excluded_terms = excluded_terms or []
	resolved_matches: list[AliasMatch] = []
	seen_matches: set[tuple[str, str, str]] = set()
	entries = build_allowed_match_entries(allowed_terms, allowed_aliases, rule)
	candidate_variant = preprocess_candidate_for_match(candidate, rule)
	if not candidate_variant:
		return []
	logger.debug("Matching original segment '%s' stripped to '%s'", candidate, candidate_variant)
	for candidate_variant in [candidate_variant]:
		candidate_variant_cmp = normalize_inflectional_text(candidate_variant)
		candidate_matches: list[AliasMatch] = []
		for pattern_text, canonical, is_alias in entries:
			pattern_cmp = normalize_inflectional_text(pattern_text)
			if not pattern_cmp or not candidate_variant_cmp:
				continue
			if pattern_cmp in candidate_variant_cmp:
				matched_span = pattern_text
			elif candidate_variant_cmp == pattern_cmp:
				matched_span = candidate_variant
			else:
				continue
			candidate_matches.append(
				AliasMatch(
					candidate=candidate_variant,
					canonical=canonical,
					matched_text=pattern_text,
					matched_span=matched_span,
					is_alias=is_alias,
				)
			)
		for match in sorted(candidate_matches, key=lambda item: (-len(item.matched_text), -len(item.matched_span), item.matched_text)):
			if span_contains_excluded_term(match.matched_span, excluded_terms, rule):
				logger.debug(
					"Rejected %s match for candidate '%s' because matched span '%s' contained an excluded term",
					"alias" if match.is_alias else "canonical",
					match.candidate,
					match.matched_span,
				)
				continue
			match_key = (match.canonical, match.matched_text, match.candidate)
			if match_key in seen_matches:
				continue
			seen_matches.add(match_key)
			logger.debug(
				"Matched original segment '%s' stripped to '%s' via %s '%s' -> canonical '%s'",
				candidate,
				match.candidate,
				"alias" if match.is_alias else "canonical",
				match.matched_text,
				match.canonical,
			)
			resolved_matches.append(match)
			break
	return resolved_matches


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


def resolve_segment_text_by_id(row: Mapping[str, object], component_id: str, segment_id: str) -> str:
	segment_field = f"segment_text_{component_id}__{segment_id}"
	return str(row.get(segment_field, "") or "").strip()


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
	return bool(
		resolve_candidate_matches(
			"; ".join(candidates),
			list(payload.get("allowed_terms", [])),
			dict(payload.get("allowed_aliases", {})),
			rule,
		)
	)


def exact_or_alias_article_insensitive_any_conjunct_match(
	candidates: list[str],
	payload: Mapping[str, object],
	rule: str,
) -> bool:
	return bool(
		resolve_matches_for_candidates(
			expand_candidates_with_conjuncts(candidates, rule),
			payload,
			rule,
		)
	)


def resolve_matches_for_candidates(
	candidates: list[str],
	payload: Mapping[str, object],
	rule: str,
	excluded_terms: list[str] | None = None,
) -> list[AliasMatch]:
	all_matches: list[AliasMatch] = []
	seen_canonicals: set[str] = set()
	for candidate in candidates:
		for match in resolve_candidate_matches(
			candidate,
			list(payload.get("allowed_terms", [])),
			dict(payload.get("allowed_aliases", {})),
			rule,
			excluded_terms,
		):
			if match.canonical in seen_canonicals:
				continue
			seen_canonicals.add(match.canonical)
			all_matches.append(match)
	return all_matches


def canonicalize_segment_text(
	text: str,
	allowed_terms: list[str],
	allowed_aliases: Mapping[str, str],
	rule: str,
) -> str:
	if not text.strip():
		return ""
	matches = resolve_matches_for_candidates(
		expand_candidates_with_conjuncts(extract_candidate_units(text, rule), rule),
		{
			"allowed_terms": allowed_terms,
			"allowed_aliases": dict(allowed_aliases),
		},
		rule,
	)
	if matches:
		return sorted(matches, key=lambda item: (-len(item.matched_text), item.canonical))[0].canonical
	return ""


def extract_canonical_mentions_from_text(
	text: str,
	allowed_terms: list[str],
	allowed_aliases: Mapping[str, str],
	rule: str,
) -> list[str]:
	if not normalize_text(text, rule):
		return []
	return [
		match.canonical
		for match in resolve_matches_for_candidates(
			expand_candidates_with_conjuncts(extract_candidate_units(text, rule), rule),
			{
				"allowed_terms": allowed_terms,
				"allowed_aliases": dict(allowed_aliases),
			},
			rule,
		)
	]


def canonical_inequality_match(
	row: Mapping[str, object],
	component_id: str,
	payload: Mapping[str, object],
	rule: str,
) -> bool:
	left_segment_id = str(payload.get("left_segment_id", "DemandA") or "DemandA").strip()
	right_segment_id = str(payload.get("right_segment_id", "DemandB") or "DemandB").strip()
	left_text = resolve_segment_text_by_id(row, component_id, left_segment_id)
	right_text = resolve_segment_text_by_id(row, component_id, right_segment_id)
	left_canonical = canonicalize_segment_text(
		left_text,
		list(payload.get("left_allowed_terms", [])),
		dict(payload.get("left_allowed_aliases", {})),
		rule,
	)
	right_canonical = canonicalize_segment_text(
		right_text,
		list(payload.get("right_allowed_terms", [])),
		dict(payload.get("right_allowed_aliases", {})),
		rule,
	)
	if left_canonical and right_canonical:
		return left_canonical != right_canonical
	if left_text and right_text:
		return True
	source_response_text = str(row.get("source_response_text", "") or row.get("response_text", "") or "").strip()
	if source_response_text:
		fallback_canonicals = extract_canonical_mentions_from_text(
			source_response_text,
			list(payload.get("left_allowed_terms", [])) + list(payload.get("right_allowed_terms", [])),
			{
				**dict(payload.get("left_allowed_aliases", {})),
				**dict(payload.get("right_allowed_aliases", {})),
			},
			rule,
		)
		if len(fallback_canonicals) >= 2:
			return True
	return bool(left_canonical or right_canonical)


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


def evaluate_match_policy(
	text: str,
	payload: Mapping[str, object],
	*,
	row: Mapping[str, object] | None = None,
	component_id: str = "",
) -> bool:
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
	if match_policy == "canonical_inequality":
		if row is None or not component_id:
			return False
		return canonical_inequality_match(row, component_id, payload, rule)
	raise ValueError(f"Unsupported Layer 1 match_policy: {match_policy}")


def apply_decision_rule(
	text: str,
	payload: Mapping[str, object],
	*,
	row: Mapping[str, object] | None = None,
	component_id: str = "",
) -> tuple[str, str]:
	rule = str(payload.get("normalisation_rule", "") or "").strip()
	decision_rule = str(payload.get("decision_rule", "") or "").strip()
	match_policy = str(payload.get("match_policy", "") or "").strip()
	excluded_terms = [normalize_text(term, rule) for term in payload.get("excluded_terms", []) if normalize_text(term, rule)]
	normalized_text = normalize_text(text, rule)
	has_excluded = any(term in normalized_text for term in excluded_terms)
	policy_match = evaluate_match_policy(text, payload, row=row, component_id=component_id)
	if decision_rule == "present_if_any_allowed_term_found":
		return ("present" if policy_match else "not_present", "none")
	if decision_rule == "present_if_exact_match_or_alias_and_not_excluded":
		if match_policy in {"exact_or_alias_article_insensitive", "exact_or_alias_article_insensitive_any_conjunct"}:
			matches = resolve_matches_for_candidates(
				expand_candidates_with_conjuncts(extract_candidate_units(text, rule), rule)
				if match_policy == "exact_or_alias_article_insensitive_any_conjunct"
				else extract_candidate_units(text, rule),
				payload,
				rule,
				excluded_terms,
			)
			return ("present" if matches else "not_present", "none")
		return ("present" if policy_match and not has_excluded else "not_present", "none")
	if decision_rule == "present_if_matches_stage_or_role_and_not_excluded":
		return ("present" if policy_match and not has_excluded else "not_present", "none")
	if decision_rule == "present_if_minimum_group_matches_met_and_not_excluded":
		return ("present" if policy_match and not has_excluded else "not_present", "none")
	if decision_rule == "present_if_no_excluded_terms_found":
		return ("present" if not has_excluded else "not_present", "none")
	if decision_rule == "present_if_any_allowed_term_found_and_not_only_excluded":
		return ("present" if policy_match else "not_present", "none")
	if decision_rule == "present_if_canonical_mapping_of_demand_a_not_equal_canonical_mapping_of_demand_b":
		return ("present" if policy_match and not has_excluded else "not_present", "none")
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
	match_policy = str(payload.get("match_policy", "") or "").strip()
	if match_policy == "canonical_inequality":
		left_segment_id = str(payload.get("left_segment_id", "DemandA") or "DemandA").strip()
		right_segment_id = str(payload.get("right_segment_id", "DemandB") or "DemandB").strip()
		left_text = resolve_segment_text_by_id(row, resolved_component_id, left_segment_id)
		right_text = resolve_segment_text_by_id(row, resolved_component_id, right_segment_id)
		source_response_text = str(row.get("source_response_text", "") or row.get("response_text", "") or "").strip()
		if not left_text and not right_text and not source_response_text:
			return {
				"submission_id": resolve_submission_id(row),
				"component_id": resolved_component_id,
				"indicator_id": indicator_id,
				"evidence_status": "not_present",
				"evaluation_notes": default_evaluation_notes,
				"confidence": "high",
				"flags": "missing_input_text",
			}
		evidence_status, flags = apply_decision_rule(
			"",
			payload,
			row=row,
			component_id=resolved_component_id,
		)
		return {
			"submission_id": resolve_submission_id(row),
			"component_id": resolved_component_id,
			"indicator_id": indicator_id,
			"evidence_status": evidence_status,
			"evaluation_notes": default_evaluation_notes,
			"confidence": "high",
			"flags": flags,
		}
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
	evidence_status, flags = apply_decision_rule(text, payload, row=row, component_id=resolved_component_id)
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