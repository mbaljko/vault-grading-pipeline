#!/usr/bin/env python3
"""Shared deterministic runtime for generated Layer 1 indicator scorers.

The Layer 1 deterministic path compiles machine-readable indicator payloads into
small Python modules. Those generated modules delegate the matching mechanics to
this runtime so the policy implementation stays centralized and auditable.

This file is the authoritative implementation surface for Layer 1 registry
`normalisation_rule`, `decision_rule`, `match_policy`, and bound-segment
text-resolution semantics.

The explicitly implemented `normalisation_rule` values are:
- `lowercase`: lowercases the input text but otherwise preserves internal spacing and trailing stage labels.
- `lowercase_trim`: lowercases the input text, collapses repeated whitespace, and strips leading and trailing whitespace.
- `lowercase_trim_strip_stage_suffix`: applies `lowercase_trim`, then removes a trailing `stage` suffix so labels like `documentation stage` normalize to `documentation`.
- `lowercase_trim_strip_leading_determiner`: applies `lowercase_trim`, then removes a leading determiner so labels like `the committee` normalize to `committee`.
- `lowercase_lemma_effect_terms`: applies `lowercase_trim`, then rewrites only configured effect-term inflections like `sequencing` -> `sequence` while preserving surrounding structural-feature text.


The explicitly recognized `decision_rule` values are:
- `present_if_any_allowed_term_found`: returns `present` when the configured `match_policy` finds any allowed term in the segment, without applying excluded-term veto logic.
- `present_if_exact_match_or_alias_and_not_excluded`: returns `present` when an allowed term or alias resolves successfully under the exact-match family of policies and no excluded term is present.
- `present_if_matches_stage_or_role_and_not_excluded`: returns `present` when the configured policy finds an allowed stage, role, or equivalent mapped term and the segment is not vetoed by excluded terms.
- `present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded`: returns `present` only when the normalized segment contains a full registered stage phrase or full approved alias phrase, and no excluded term is present.
- `present_if_minimum_group_matches_met_and_not_excluded`: returns `present` when the co-occurrence/group matcher finds the required minimum number of terms per configured group and no excluded term is present.
- `present_if_no_excluded_terms_found`: returns `present` whenever the segment contains none of the configured excluded terms, regardless of allowed-term matching.
- `present_if_any_allowed_term_found_and_not_only_excluded`: returns `present` when the configured policy finds an allowed term match; this rule does not independently veto on excluded-term presence.
- `present_if_canonical_mappings_are_distinct`: returns `present` when the left and right slots resolve to different canonical values, with excluded terms still able to veto the result.

Legacy compatibility note:
- `present_if_canonical_mapping_of_demand_a_not_equal_canonical_mapping_of_demand_b`
	is normalized to `present_if_canonical_mappings_are_distinct`

The explicitly recognized `match_policy` values are:
- `substring_any`: normalizes the segment and returns a match when any normalized allowed term appears as a substring within it.
- `exact_or_alias`: splits the segment into candidate units and matches those units exactly against normalized allowed terms or aliases.
- `exact_or_alias_article_insensitive`: matches exact normalized allowed terms or aliases while tolerating leading-article differences such as `the committee` vs `committee`.
- `exact_or_alias_article_insensitive_any_conjunct`: extends the article-insensitive exact matcher by also testing conjunct-level candidates extracted from coordinated phrases.
- `exact_or_alias_or_role`: evaluates the exact-or-alias matcher over the union of `allowed_terms` and `allowed_roles`.
- `co_occurrence`: normalizes the segment and requires each configured term group in `required_term_groups` to meet `minimum_match_count_per_group`.
- `co_occurrence_lemma`: normalizes both the segment and each registered group term using the configured `normalisation_rule`, then requires full phrase matches per group using boundary-safe phrase matching.
- `absence_check`: reports a policy match unconditionally and leaves the final decision to the decision rule's excluded-term logic.
- `canonical_inequality`: resolves left and right bound slots to canonical values and reports a match when those canonical mappings are distinct under the configured payload.

Any other `match_policy` value hard-fails as unsupported.

Any other `decision_rule` value hard-fails as unsupported.

Bound-segment text resolution note:
- indicators may declare `bound_segment_resolution_policy`
- `hard_stay` is the default and keeps scoring pinned to the declared
	`bound_segment_id`; if that segment is blank, the indicator scores from blank
	rather than falling through to broader text fields
- `fallback_to_evidence_text` explicitly allows a blank bound segment to fall
	through to `evidence_text` and then `response_text`
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Mapping


logger = logging.getLogger(__name__)

SUPPORTED_NORMALISATION_RULES = {
	"",
	"lowercase",
	"lowercase_trim",
	"lowercase_trim_strip_stage_suffix",
	"lowercase_trim_strip_leading_determiner",
	"lowercase_lemma_effect_terms",
}

DECISION_RULE_ALIASES = {
	"present_if_canonical_mapping_of_demand_a_not_equal_canonical_mapping_of_demand_b": "present_if_canonical_mappings_are_distinct",
	"present_if_any_stage_token_matches_after_normalisation_and_not_excluded": "present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded",
}

SUPPORTED_DECISION_RULES = {
	"present_if_any_allowed_term_found",
	"present_if_exact_match_or_alias_and_not_excluded",
	"present_if_matches_stage_or_role_and_not_excluded",
	"present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded",
	"present_if_minimum_group_matches_met_and_not_excluded",
	"present_if_no_excluded_terms_found",
	"present_if_any_allowed_term_found_and_not_only_excluded",
	"present_if_canonical_mappings_are_distinct",
}

SUPPORTED_BOUND_SEGMENT_RESOLUTION_POLICIES = {
	"hard_stay",
	"fallback_to_evidence_text",
}

SUPPORTED_MATCH_POLICIES = {
	"substring_any",
	"exact_or_alias",
	"exact_or_alias_article_insensitive",
	"exact_or_alias_article_insensitive_any_conjunct",
	"exact_or_alias_or_role",
	"co_occurrence",
	"co_occurrence_lemma",
	"absence_check",
	"canonical_inequality",
}

LABEL_LINE_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")
LEADING_ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
CONJUNCTION_SPLIT_RE = re.compile(r"\s+and\s+|\s*,\s*", re.IGNORECASE)
TRAILING_STAGE_SUFFIX_RE = re.compile(r"\s+stage$", re.IGNORECASE)
MATCH_PREFIX_RE = re.compile(
	r"^(?:rule\s+that|requirement\s+to|institutional\s+demand\s+for|institutional\s+demand\s+of|obligation\s+to)\s+",
	re.IGNORECASE,
)
EFFECT_TERM_PHRASE_LEMMA_MAP = {
	"putting into words": "put into words",
	"puts into words": "put into words",
	"put into words": "put into words",
}
EFFECT_TERM_PHRASE_LEMMA_RE = re.compile(
	r"\b(?:" + "|".join(sorted((re.escape(term) for term in EFFECT_TERM_PHRASE_LEMMA_MAP), key=len, reverse=True)) + r")\b"
)
EFFECT_TERM_LEMMA_MAP = {
	"sequencing": "sequence",
	"sequences": "sequence",
	"sequenced": "sequence",
	"structuring": "structure",
	"structures": "structure",
	"structured": "structure",
	"allocating": "allocate",
	"allocates": "allocate",
	"allocation": "allocate",
	"distributing": "distribute",
	"distributes": "distribute",
	"distribution": "distribute",
	"redistributing": "redistribute",
	"redistributes": "redistribute",
	"redistribution": "redistribute",
	"formalising": "formalise",
	"formalises": "formalise",
	"formalisation": "formalise",
	"formalizing": "formalize",
	"formalizes": "formalize",
	"formalization": "formalize",
	"organising": "organise",
	"organises": "organise",
	"organisation": "organise",
	"organizing": "organize",
	"organizes": "organize",
	"organization": "organize",
	"recording": "record",
	"records": "record",
	"recorded": "record",
	"requiring": "require",
	"requires": "require",
	"requirement": "require",
	"guiding": "guide",
	"guides": "guide",
	"guidance": "guide",
	"ordering": "order",
	"orders": "order",
	"ordered": "order",
	"orienting": "orient",
	"orients": "orient",
	"orientation": "orient",
	"narrowing": "narrow",
	"narrows": "narrow",
	"narrowed": "narrow",
	"focusing": "focus",
	"focuses": "focus",
	"focused": "focus",
	"compiling": "compile",
	"compiles": "compile",
	"compilation": "compile",
	"aligning": "align",
	"aligns": "align",
	"alignment": "align",
	"expanding": "expand",
	"expands": "expand",
	"expansion": "expand",
	"influencing": "influence",
	"influences": "influence",
	"imposing": "impose",
	"imposes": "impose",
	"pairing": "pair",
	"pairs": "pair",
	"shifting": "shift",
	"shifts": "shift",
	"reorganising": "reorganise",
	"reorganises": "reorganise",
	"reorganisation": "reorganise",
	"reorganizing": "reorganize",
	"reorganizes": "reorganize",
	"reorganization": "reorganize",
}
EFFECT_TERM_LEMMA_RE = re.compile(
	r"\b(?:" + "|".join(sorted((re.escape(term) for term in EFFECT_TERM_LEMMA_MAP), key=len, reverse=True)) + r")\b"
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


def apply_effect_term_phrase_lemma_map(value: str) -> str:
	return EFFECT_TERM_PHRASE_LEMMA_RE.sub(lambda match: EFFECT_TERM_PHRASE_LEMMA_MAP[match.group(0)], value)


def apply_effect_term_lemma_map(value: str) -> str:
	return EFFECT_TERM_LEMMA_RE.sub(lambda match: EFFECT_TERM_LEMMA_MAP[match.group(0)], value)


def normalize_decision_rule_name(decision_rule: str) -> str:
	return DECISION_RULE_ALIASES.get(decision_rule, decision_rule)


def validate_normalisation_rule_name(rule: str) -> str:
	if rule not in SUPPORTED_NORMALISATION_RULES:
		raise ValueError(f"Unsupported Layer 1 normalisation_rule: {rule}")
	return rule


def normalize_text(value: object, rule: str) -> str:
	rule = validate_normalisation_rule_name(str(rule or "").strip())
	text = str(value or "")
	if not text.strip():
		return ""
	trim_rules = {
		"lowercase_trim",
		"lowercase_trim_strip_stage_suffix",
		"lowercase_trim_strip_leading_determiner",
		"lowercase_lemma_effect_terms",
	}
	normalized = text.replace("\r\n", "\n").replace("\r", "\n")
	if rule in {
		"lowercase",
		"lowercase_trim",
		"lowercase_trim_strip_stage_suffix",
		"lowercase_trim_strip_leading_determiner",
		"lowercase_lemma_effect_terms",
	}:
		normalized = normalized.lower()
	if rule in trim_rules:
		normalized = normalize_whitespace(normalized).strip()
	if rule == "lowercase_trim_strip_stage_suffix":
		normalized = TRAILING_STAGE_SUFFIX_RE.sub("", normalized)
	if rule == "lowercase_trim_strip_leading_determiner":
		normalized = LEADING_ARTICLE_RE.sub("", normalized, count=1)
	if rule == "lowercase_lemma_effect_terms":
		normalized = apply_effect_term_phrase_lemma_map(normalized)
		normalized = apply_effect_term_lemma_map(normalized)
	return normalize_whitespace(normalized).strip() if rule in trim_rules else normalized.strip()


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


def normalize_bound_segment_resolution_policy(payload: Mapping[str, object]) -> str:
	policy = str(payload.get("bound_segment_resolution_policy", "") or "").strip()
	if not policy:
		return "hard_stay"
	if policy not in SUPPORTED_BOUND_SEGMENT_RESOLUTION_POLICIES:
		raise ValueError(f"Unsupported Layer 1 bound_segment_resolution_policy: {policy}")
	return policy


def resolve_indicator_text(row: Mapping[str, object], component_id: str, payload: Mapping[str, object]) -> str:
	bound_segment_id = str(payload.get("bound_segment_id", "") or "").strip()
	bound_segment_resolution_policy = normalize_bound_segment_resolution_policy(payload)
	if bound_segment_id:
		segment_field = f"segment_text_{component_id}__{bound_segment_id}"
		segment_value = str(row.get(segment_field, "") or "").strip()
		if segment_value:
			return segment_value
		if bound_segment_resolution_policy == "hard_stay":
			return ""
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


def find_matched_excluded_terms(text: str, excluded_terms: list[str], rule: str) -> list[str]:
	normalized_text = normalize_text(text, rule)
	return [excluded_term for excluded_term in excluded_terms if excluded_term and excluded_term in normalized_text]


def phrase_appears_in_text(text: str, phrase: str) -> bool:
	if not text or not phrase:
		return False
	return bool(re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text))


def extract_stage_phrase_matches_after_normalisation(
	text: str,
	payload: Mapping[str, object],
	rule: str,
	excluded_terms: list[str] | None = None,
) -> list[AliasMatch]:
	excluded_terms = excluded_terms or []
	normalized_text = normalize_text(text, rule)
	if not normalized_text:
		logger.debug(
			"Stage-phrase evaluation raw_segment=%r normalized_segment=%r matched_excluded_terms=%s matched_canonical_terms=%s",
			text,
			normalized_text,
			[],
			[],
		)
		return []
	entries = build_allowed_match_entries(
		list(payload.get("allowed_terms", [])),
		dict(payload.get("allowed_aliases", {})),
		rule,
	)
	matches: list[AliasMatch] = []
	seen_canonicals: set[str] = set()
	for pattern_text, canonical, is_alias in sorted(entries, key=lambda item: (-len(item[0]), item[0])):
		if canonical in seen_canonicals or not phrase_appears_in_text(normalized_text, pattern_text):
			continue
		matches.append(
			AliasMatch(
				candidate=normalized_text,
				canonical=canonical,
				matched_text=pattern_text,
				matched_span=pattern_text,
				is_alias=is_alias,
			)
		)
		seen_canonicals.add(canonical)
	matched_excluded_terms = find_matched_excluded_terms(text, excluded_terms, rule)
	matched_canonical_terms = sorted({match.canonical for match in matches})
	logger.debug(
		"Stage-phrase evaluation raw_segment=%r normalized_segment=%r matched_excluded_terms=%s matched_canonical_terms=%s",
		text,
		normalized_text,
		matched_excluded_terms,
		matched_canonical_terms,
	)
	return matches


def stage_phrase_match_after_normalisation(text: str, payload: Mapping[str, object], rule: str) -> bool:
	excluded_terms = [normalize_text(term, rule) for term in payload.get("excluded_terms", []) if normalize_text(term, rule)]
	return bool(extract_stage_phrase_matches_after_normalisation(text, payload, rule, excluded_terms))


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
	source_response_text = str(row.get("source_response_text", "") or row.get("response_text", "") or "").strip()
	if left_canonical and right_canonical:
		return left_canonical != right_canonical
	if not left_canonical and not right_canonical:
		return bool(left_text or right_text or source_response_text)
	if left_text and right_text:
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
	matched_terms_by_group: dict[str, list[str]] = {}
	if not required_term_groups:
		logger.debug(
			"Grouped-term evaluation raw_segment=%r normalized_segment=%r required_term_groups=%s minimum_match_count_per_group=%s matched_terms_by_group=%s final_status=%s",
			text,
			normalized_text,
			required_term_groups,
			minimum_match_count,
			matched_terms_by_group,
			False,
		)
		return False
	for group_terms in required_term_groups.values():
		matched_terms = {
			normalize_text(term, rule)
			for term in group_terms
			if normalize_text(term, rule) and normalize_text(term, rule) in normalized_text
		}
		group_name = next(
			(name for name, terms in required_term_groups.items() if terms is group_terms),
			"",
		)
		matched_terms_by_group[group_name] = sorted(matched_terms)
		if len(matched_terms) < max(minimum_match_count, 1):
			logger.debug(
				"Grouped-term evaluation raw_segment=%r normalized_segment=%r required_term_groups=%s minimum_match_count_per_group=%s matched_terms_by_group=%s final_status=%s",
				text,
				normalized_text,
				required_term_groups,
				minimum_match_count,
				matched_terms_by_group,
				False,
			)
			return False
	logger.debug(
		"Grouped-term evaluation raw_segment=%r normalized_segment=%r required_term_groups=%s minimum_match_count_per_group=%s matched_terms_by_group=%s final_status=%s",
		text,
		normalized_text,
		required_term_groups,
		minimum_match_count,
		matched_terms_by_group,
		True,
	)
	return True


def evaluate_co_occurrence_phrase_groups(
	text: str,
	payload: Mapping[str, object],
	rule: str,
) -> tuple[bool, str, dict[str, list[str]], dict[str, list[str]], int]:
	normalized_text = normalize_text(text, rule)
	minimum_match_count = int(payload.get("minimum_match_count_per_group", 0) or 0)
	required_term_groups = {
		str(group_name): [str(term) for term in group_terms]
		for group_name, group_terms in dict(payload.get("required_term_groups", {})).items()
	}
	matched_terms_by_group: dict[str, list[str]] = {}
	normalized_required_term_groups: dict[str, list[str]] = {}
	if not required_term_groups:
		return (False, normalized_text, normalized_required_term_groups, matched_terms_by_group, minimum_match_count)
	for group_name, group_terms in required_term_groups.items():
		normalized_terms = sorted({normalize_text(term, rule) for term in group_terms if normalize_text(term, rule)})
		normalized_required_term_groups[group_name] = normalized_terms
		matched_terms = [term for term in normalized_terms if phrase_appears_in_text(normalized_text, term)]
		matched_terms_by_group[group_name] = matched_terms
		if len(matched_terms) < max(minimum_match_count, 1):
			return (
				False,
				normalized_text,
				normalized_required_term_groups,
				matched_terms_by_group,
				minimum_match_count,
			)
	return (True, normalized_text, normalized_required_term_groups, matched_terms_by_group, minimum_match_count)


def co_occurrence_lemma_match(text: str, payload: Mapping[str, object], rule: str) -> bool:
	final_status, normalized_text, normalized_required_term_groups, matched_terms_by_group, minimum_match_count = (
		evaluate_co_occurrence_phrase_groups(text, payload, rule)
	)
	logger.debug(
		"Grouped-lemma evaluation match_policy=%s normalisation_rule=%s raw_segment=%r normalized_segment=%r required_term_groups=%s minimum_match_count_per_group=%s matched_terms_by_group=%s final_status=%s",
		"co_occurrence_lemma",
		rule,
		text,
		normalized_text,
		normalized_required_term_groups,
		minimum_match_count,
		matched_terms_by_group,
		final_status,
	)
	return final_status


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
	if match_policy == "co_occurrence_lemma":
		return co_occurrence_lemma_match(text, payload, rule)
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
	decision_rule = normalize_decision_rule_name(str(payload.get("decision_rule", "") or "").strip())
	match_policy = str(payload.get("match_policy", "") or "").strip()
	if decision_rule not in SUPPORTED_DECISION_RULES:
		raise ValueError(f"Unsupported Layer 1 decision_rule: {decision_rule}")
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
	if decision_rule == "present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded":
		matches = extract_stage_phrase_matches_after_normalisation(text, payload, rule, excluded_terms)
		matched_excluded_terms = find_matched_excluded_terms(text, excluded_terms, rule)
		matched_canonical_terms = sorted({match.canonical for match in matches})
		evidence_status = "present" if matches and not matched_excluded_terms else "not_present"
		logger.debug(
			"Decision rule %s final_status=%s raw_segment=%r normalized_segment=%r matched_canonical_terms=%s matched_excluded_terms=%s",
			decision_rule,
			evidence_status,
			text,
			normalized_text,
			matched_canonical_terms,
			matched_excluded_terms,
		)
		return (evidence_status, "none")
	if decision_rule == "present_if_minimum_group_matches_met_and_not_excluded":
		if match_policy == "co_occurrence_lemma":
			matched_excluded_terms = find_matched_excluded_terms(text, excluded_terms, rule)
			policy_match, normalized_co_occurrence_text, normalized_required_term_groups, matched_terms_by_group, minimum_match_count = (
				evaluate_co_occurrence_phrase_groups(text, payload, rule)
			)
			evidence_status = "present" if policy_match and not matched_excluded_terms else "not_present"
			logger.debug(
				"Decision rule %s match_policy=%s normalisation_rule=%s final_status=%s raw_segment=%r normalized_segment=%r required_term_groups=%s minimum_match_count_per_group=%s matched_terms_by_group=%s matched_excluded_terms=%s",
				decision_rule,
				match_policy,
				rule,
				evidence_status,
				text,
				normalized_co_occurrence_text,
				normalized_required_term_groups,
				minimum_match_count,
				matched_terms_by_group,
				matched_excluded_terms,
			)
			return (evidence_status, "none")
		return ("present" if policy_match and not has_excluded else "not_present", "none")
	if decision_rule == "present_if_no_excluded_terms_found":
		return ("present" if not has_excluded else "not_present", "none")
	if decision_rule == "present_if_any_allowed_term_found_and_not_only_excluded":
		return ("present" if policy_match else "not_present", "none")
	if decision_rule == "present_if_canonical_mappings_are_distinct":
		return ("present" if policy_match and not has_excluded else "not_present", "none")
	raise ValueError(f"Unsupported Layer 1 decision_rule: {decision_rule}")


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
	"DECISION_RULE_ALIASES",
	"SUPPORTED_DECISION_RULES",
	"score_indicator_from_row",
]