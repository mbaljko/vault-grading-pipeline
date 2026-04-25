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
import ast
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
	"present_if_minimum_group_matches_met_or_fallback_and_not_excluded",
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

MATCH_POLICY_WINDOW_RE = re.compile(r"^co_occurrence_window_(\d+)$")
RULE_BOOL_TRUE_VALUES = {"1", "true", "yes", "y", "on"}
RULE_BOOL_FALSE_VALUES = {"0", "false", "no", "n", "off"}
RULE_EXPR_TOKEN_RE = re.compile(r"\(|\)|AND|OR|NOT|[A-Za-z_][A-Za-z0-9_]*", re.IGNORECASE)
OBJECT_PHRASE_SKIP_TOKENS = {
	"the",
	"a",
	"an",
	"to",
	"of",
	"for",
	"in",
	"on",
	"with",
	"and",
	"or",
	"that",
	"this",
	"these",
	"those",
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


def parse_rule_bool(value: object, default: bool = False) -> bool:
	if isinstance(value, bool):
		return value
	if value is None:
		return default
	normalized = str(value).strip().lower()
	if normalized in RULE_BOOL_TRUE_VALUES:
		return True
	if normalized in RULE_BOOL_FALSE_VALUES:
		return False
	return default


def parse_semicolon_rule_config(value: object) -> dict[str, object]:
	if isinstance(value, Mapping):
		config = {str(key).strip(): inner for key, inner in value.items() if str(key).strip()}
		config["enabled"] = parse_rule_bool(config.get("enabled"), default=False)
		return config
	if not isinstance(value, str) or not value.strip():
		return {"enabled": False}
	config: dict[str, object] = {}
	for part in value.split(";"):
		chunk = part.strip()
		if not chunk or ":" not in chunk:
			continue
		key, raw_value = chunk.split(":", 1)
		normalized_key = key.strip()
		normalized_value = raw_value.strip()
		if not normalized_key:
			continue
		if normalized_key == "enabled":
			config[normalized_key] = parse_rule_bool(normalized_value, default=False)
		elif normalized_value.isdigit():
			config[normalized_key] = int(normalized_value)
		else:
			config[normalized_key] = normalized_value
	config.setdefault("enabled", False)
	return config


def parse_comma_delimited_tokens(value: object) -> list[str]:
	if isinstance(value, str):
		return [token for token in (part.strip() for part in value.split(",")) if token]
	if isinstance(value, list):
		return [str(token).strip() for token in value if str(token).strip()]
	return []


def parse_rule_sequence(value: object) -> list[str]:
	if isinstance(value, (list, tuple, set)):
		return [str(item).strip() for item in value if str(item).strip()]
	if not isinstance(value, str) or not value.strip():
		return []
	raw_value = value.strip()
	if raw_value.startswith("[") or raw_value.startswith("("):
		try:
			parsed = ast.literal_eval(raw_value)
		except (ValueError, SyntaxError):
			parsed = None
		if isinstance(parsed, (list, tuple, set)):
			return [str(item).strip() for item in parsed if str(item).strip()]
	trimmed = raw_value.strip("[]()")
	return [item for item in (part.strip().strip("\"'") for part in trimmed.split(",")) if item]


def pattern_matches_normalized_text(pattern: str, normalized_text: str, rule: str) -> bool:
	if not pattern:
		return False
	raw_pattern = str(pattern).strip()
	if raw_pattern.startswith("re:"):
		try:
			return bool(re.search(raw_pattern[3:], normalized_text, flags=re.IGNORECASE))
		except re.error:
			return False
	if len(raw_pattern) >= 2 and raw_pattern.startswith("/") and raw_pattern.endswith("/"):
		try:
			return bool(re.search(raw_pattern[1:-1], normalized_text, flags=re.IGNORECASE))
		except re.error:
			return False
	normalized_pattern = normalize_text(raw_pattern, rule)
	if not normalized_pattern:
		return False
	return normalized_pattern.lower() in normalized_text.lower()


def has_matching_derived_pattern(patterns: list[str], normalized_text: str, rule: str) -> bool:
	return any(pattern_matches_normalized_text(pattern, normalized_text, rule) for pattern in patterns)


def has_matching_restricted_effect_form(restricted_effect_forms: list[str], normalized_text: str, rule: str) -> bool:
	for effect_form in restricted_effect_forms:
		normalized_effect_form = normalize_text(effect_form, rule)
		if normalized_effect_form and phrase_appears_in_text(normalized_text, normalized_effect_form):
			return True
	return False


def normalize_payload_optional_fields(payload: Mapping[str, object]) -> dict[str, object]:
	normalized = dict(payload)
	normalized["derived_structural_feature_rule"] = parse_semicolon_rule_config(
		normalized.get("derived_structural_feature_rule")
	)
	normalized["implicit_feature_recovery"] = parse_semicolon_rule_config(
		normalized.get("implicit_feature_recovery")
	)
	normalized["fallback_rule"] = parse_semicolon_rule_config(normalized.get("fallback_rule"))
	normalized["domain_artifact_tokens"] = parse_comma_delimited_tokens(normalized.get("domain_artifact_tokens"))
	return normalized


def parse_co_occurrence_window_size(match_policy: str) -> int | None:
	match = MATCH_POLICY_WINDOW_RE.fullmatch(match_policy)
	if match is None:
		return None
	window_size = int(match.group(1))
	return window_size if window_size > 0 else None


def is_supported_match_policy(match_policy: str) -> bool:
	if match_policy in SUPPORTED_MATCH_POLICIES:
		return True
	return parse_co_occurrence_window_size(match_policy) is not None


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
	if left_canonical and right_canonical:
		return left_canonical != right_canonical
	if left_text and right_text:
		return normalize_text(left_text, rule) != normalize_text(right_text, rule)
	fallback_source_text = (
		str(row.get("source_response_text", "") or "").strip()
		or str(row.get("evidence_text", "") or "").strip()
		or str(row.get("response_text", "") or "").strip()
	)
	if fallback_source_text:
		return True
	return False


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


def tokenize_rule_expression(expression: str) -> list[str]:
	return [token.upper() for token in RULE_EXPR_TOKEN_RE.findall(expression or "")]


def evaluate_rule_condition(expression: str, context: Mapping[str, bool]) -> bool:
	tokens = tokenize_rule_expression(expression)
	if not tokens:
		return True
	index = 0

	def parse_expression() -> bool:
		nonlocal index
		value = parse_term()
		while index < len(tokens) and tokens[index] == "OR":
			index += 1
			value = value or parse_term()
		return value

	def parse_term() -> bool:
		nonlocal index
		value = parse_factor()
		while index < len(tokens) and tokens[index] == "AND":
			index += 1
			value = value and parse_factor()
		return value

	def parse_factor() -> bool:
		nonlocal index
		if index >= len(tokens):
			return False
		token = tokens[index]
		if token == "NOT":
			index += 1
			return not parse_factor()
		if token == "(":
			index += 1
			value = parse_expression()
			if index < len(tokens) and tokens[index] == ")":
				index += 1
			return value
		if token == ")":
			index += 1
			return False
		index += 1
		return bool(context.get(token.lower(), False))

	result = parse_expression()
	return result and index >= len(tokens)


def normalize_required_term_groups(payload: Mapping[str, object], rule: str) -> dict[str, list[str]]:
	required_term_groups = {
		str(group_name): [str(term) for term in group_terms]
		for group_name, group_terms in dict(payload.get("required_term_groups", {})).items()
	}
	normalized_required_term_groups: dict[str, list[str]] = {}
	for group_name, group_terms in required_term_groups.items():
		normalized_required_term_groups[group_name] = sorted(
			{normalize_text(term, rule) for term in group_terms if normalize_text(term, rule)}
		)
	return normalized_required_term_groups


def tokenize_normalized_text(text: str) -> list[str]:
	return [token for token in normalize_whitespace(text).split(" ") if token]


def find_phrase_token_spans(tokens: list[str], phrase_tokens: list[str]) -> list[tuple[int, int]]:
	if not tokens or not phrase_tokens:
		return []
	spans: list[tuple[int, int]] = []
	length = len(phrase_tokens)
	for start in range(0, len(tokens) - length + 1):
		if tokens[start : start + length] == phrase_tokens:
			spans.append((start, start + length - 1))
	return spans


def has_windowed_group_alignment(group_spans: dict[str, list[tuple[int, int]]], window_size: int) -> bool:
	groups = [group_name for group_name, spans in group_spans.items() if spans]
	if not groups:
		return False

	def dfs(group_index: int, current_min: int, current_max: int) -> bool:
		if group_index >= len(groups):
			return (current_max - current_min) <= window_size
		for start, end in group_spans[groups[group_index]]:
			next_min = min(current_min, start)
			next_max = max(current_max, end)
			if (next_max - next_min) > window_size:
				continue
			if dfs(group_index + 1, next_min, next_max):
				return True
		return False

	for start, end in group_spans[groups[0]]:
		if dfs(1, start, end):
			return True
	return False


def evaluate_co_occurrence_phrase_groups_with_window(
	text: str,
	payload: Mapping[str, object],
	rule: str,
	window_size: int,
) -> tuple[bool, str, dict[str, list[str]], dict[str, list[str]], int, bool]:
	base_status, normalized_text, normalized_required_term_groups, matched_terms_by_group, minimum_match_count = (
		evaluate_co_occurrence_phrase_groups(text, payload, rule)
	)
	if not base_status:
		return (
			False,
			normalized_text,
			normalized_required_term_groups,
			matched_terms_by_group,
			minimum_match_count,
			False,
		)
	tokens = tokenize_normalized_text(normalized_text)
	group_spans: dict[str, list[tuple[int, int]]] = {}
	for group_name, terms in matched_terms_by_group.items():
		spans: list[tuple[int, int]] = []
		for term in terms:
			phrase_tokens = tokenize_normalized_text(term)
			spans.extend(find_phrase_token_spans(tokens, phrase_tokens))
		group_spans[group_name] = spans
	window_match = has_windowed_group_alignment(group_spans, window_size)
	return (
		window_match,
		normalized_text,
		normalized_required_term_groups,
		matched_terms_by_group,
		minimum_match_count,
		window_match,
	)


def resolve_domain_artifact_tokens(payload: Mapping[str, object], rule: str) -> list[str]:
	tokens: list[str] = []
	for token in parse_comma_delimited_tokens(payload.get("domain_artifact_tokens")):
		normalized = normalize_text(token, rule)
		if not normalized:
			continue
		if normalized not in tokens:
			tokens.append(normalized)
		inflectional = normalize_inflectional_text(normalized)
		if inflectional and inflectional not in tokens:
			tokens.append(inflectional)
	return tokens


def infer_effect_and_structural_groups(
	normalized_required_term_groups: Mapping[str, list[str]],
) -> tuple[list[str], list[str]]:
	effect_groups: list[str] = []
	structural_groups: list[str] = []
	for group_name in normalized_required_term_groups:
		normalized_name = group_name.lower()
		if "effect" in normalized_name or "action" in normalized_name:
			effect_groups.append(group_name)
		if "structural" in normalized_name or "feature" in normalized_name or "object" in normalized_name:
			structural_groups.append(group_name)
	return effect_groups, structural_groups


def extract_direct_object_phrases(
	normalized_text: str,
	effect_terms: list[str],
) -> list[str]:
	tokens = tokenize_normalized_text(normalized_text)
	if not tokens or not effect_terms:
		return []
	phrases: list[str] = []
	seen: set[str] = set()
	for effect_term in effect_terms:
		phrase_tokens = tokenize_normalized_text(effect_term)
		for _, end in find_phrase_token_spans(tokens, phrase_tokens):
			cursor = end + 1
			while cursor < len(tokens) and tokens[cursor] in OBJECT_PHRASE_SKIP_TOKENS:
				cursor += 1
			if cursor >= len(tokens):
				continue
			for size in (1, 2):
				phrase = " ".join(tokens[cursor : min(cursor + size, len(tokens))]).strip()
				if phrase and phrase not in seen:
					seen.add(phrase)
					phrases.append(phrase)
	return phrases


def evaluate_group_match_with_augmentations(
	text: str,
	payload: Mapping[str, object],
	rule: str,
	match_policy: str,
	allow_fallback: bool,
) -> dict[str, object]:
	normalized_payload = normalize_payload_optional_fields(payload)
	window_size = parse_co_occurrence_window_size(match_policy)
	if window_size is not None:
		policy_match, normalized_text, normalized_required_term_groups, matched_terms_by_group, minimum_match_count, windowed_match = (
			evaluate_co_occurrence_phrase_groups_with_window(text, normalized_payload, rule, window_size)
		)
	elif match_policy == "co_occurrence_lemma":
		policy_match, normalized_text, normalized_required_term_groups, matched_terms_by_group, minimum_match_count = (
			evaluate_co_occurrence_phrase_groups(text, normalized_payload, rule)
		)
		windowed_match = False
	else:
		policy_match = co_occurrence_match(text, normalized_payload, rule)
		normalized_text = normalize_text(text, rule)
		normalized_required_term_groups = normalize_required_term_groups(normalized_payload, rule)
		minimum_match_count = int(normalized_payload.get("minimum_match_count_per_group", 0) or 0)
		matched_terms_by_group = {
			group_name: [term for term in terms if term and term in normalized_text]
			for group_name, terms in normalized_required_term_groups.items()
		}
		windowed_match = False

	effect_groups, structural_groups = infer_effect_and_structural_groups(normalized_required_term_groups)
	effect_terms = [term for group_name in effect_groups for term in matched_terms_by_group.get(group_name, [])]
	direct_object_phrases = extract_direct_object_phrases(normalized_text, effect_terms)
	domain_artifact_tokens = resolve_domain_artifact_tokens(normalized_payload, rule)
	domain_artifact_present = any(token and phrase_appears_in_text(normalized_text, token) for token in domain_artifact_tokens)
	direct_object_present = bool(direct_object_phrases)
	effect_form_present = bool(effect_terms)

	missing_groups = [
		group_name
		for group_name, terms in matched_terms_by_group.items()
		if len(terms) < max(minimum_match_count, 1)
	]

	derived_rule = dict(normalized_payload.get("derived_structural_feature_rule", {}))
	implicit_rule = dict(normalized_payload.get("implicit_feature_recovery", {}))
	derived_feature_recovered = False
	derived_structural_feature_matched = False
	derived_structural_feature_pattern_not_matched = False
	implicit_feature_recovery_used = False
	if missing_groups and (
		parse_rule_bool(derived_rule.get("enabled"), default=False)
		or parse_rule_bool(implicit_rule.get("enabled"), default=False)
	):
		context = {
			"effect_form_present": effect_form_present,
			"direct_object_present": direct_object_present,
			"domain_artifact_present": domain_artifact_present,
		}
		rules_to_evaluate = [
			("derived", derived_rule),
			("implicit", implicit_rule),
		]
		for rule_label, recovery_rule in rules_to_evaluate:
			if not parse_rule_bool(recovery_rule.get("enabled"), default=False):
				continue
			condition = str(recovery_rule.get("condition", "") or "").strip()
			action = str(recovery_rule.get("action", "treat_object_as_structural_feature") or "").strip()
			if action != "treat_object_as_structural_feature":
				continue
			if not evaluate_rule_condition(condition, context):
				continue
			if rule_label == "derived":
				declared_patterns = parse_rule_sequence(recovery_rule.get("patterns"))
				if declared_patterns and not has_matching_derived_pattern(declared_patterns, normalized_text, rule):
					derived_structural_feature_pattern_not_matched = True
					continue
				if declared_patterns:
					derived_structural_feature_matched = True
			target_missing_group = next((group for group in missing_groups if group in structural_groups), "")
			if not target_missing_group and missing_groups:
				target_missing_group = missing_groups[0]
			if not target_missing_group:
				continue
			recovered_phrase = direct_object_phrases[0] if direct_object_phrases else "(recovered_object)"
			matched_terms_by_group[target_missing_group] = [recovered_phrase]
			missing_groups = [group for group in missing_groups if group != target_missing_group]
			derived_feature_recovered = True
			if rule_label == "implicit":
				implicit_feature_recovery_used = True
			break

	fallback_rule = dict(normalized_payload.get("fallback_rule", {}))
	fallback_rule_used = False
	fallback_restricted_effect_form_matched = False
	fallback_restricted_effect_form_not_matched = False
	present_via_fallback = False
	fallback_unknown_action = False
	if allow_fallback and missing_groups and parse_rule_bool(fallback_rule.get("enabled"), default=False):
		condition_context = {
			"effect_form_present": effect_form_present,
			"direct_object_present": direct_object_present,
			"domain_artifact_present": domain_artifact_present,
		}
		condition = str(
			fallback_rule.get(
				"condition",
				"effect_form_present AND (direct_object_present OR domain_artifact_present)",
			)
		)
		if evaluate_rule_condition(condition, condition_context):
			restricted_effect_forms = parse_rule_sequence(fallback_rule.get("restricted_effect_forms"))
			if restricted_effect_forms:
				if has_matching_restricted_effect_form(restricted_effect_forms, normalized_text, rule):
					fallback_restricted_effect_form_matched = True
				else:
					fallback_restricted_effect_form_not_matched = True
					restricted_effect_forms = []
			if not fallback_restricted_effect_form_not_matched:
				fallback_action = str(fallback_rule.get("action", "") or "").strip()
				if fallback_action and fallback_action not in {"accept_as_present_with_flag"}:
					fallback_unknown_action = True
				else:
					target_missing_group = next((group for group in missing_groups if group in structural_groups), "")
					if not target_missing_group and missing_groups:
						target_missing_group = missing_groups[0]
					if target_missing_group:
						recovered_phrase = direct_object_phrases[0] if direct_object_phrases else "(fallback_object)"
						matched_terms_by_group[target_missing_group] = [recovered_phrase]
						missing_groups = [group for group in missing_groups if group != target_missing_group]
						fallback_rule_used = True
						if fallback_action == "accept_as_present_with_flag":
							present_via_fallback = True

	policy_or_fallback_match = policy_match and not missing_groups
	if derived_feature_recovered and not missing_groups:
		policy_or_fallback_match = True
	if fallback_rule_used and not missing_groups:
		policy_or_fallback_match = True
	return {
		"policy_match": policy_match,
		"policy_or_fallback_match": policy_or_fallback_match,
		"normalized_text": normalized_text,
		"normalized_required_term_groups": normalized_required_term_groups,
		"matched_terms_by_group": matched_terms_by_group,
		"minimum_match_count": minimum_match_count,
		"derived_feature_recovered": derived_feature_recovered,
		"derived_structural_feature_matched": derived_structural_feature_matched,
		"derived_structural_feature_pattern_not_matched": derived_structural_feature_pattern_not_matched,
		"implicit_feature_recovery_used": implicit_feature_recovery_used,
		"fallback_rule_used": fallback_rule_used,
		"fallback_restricted_effect_form_matched": fallback_restricted_effect_form_matched,
		"fallback_restricted_effect_form_not_matched": fallback_restricted_effect_form_not_matched,
		"present_via_fallback": present_via_fallback,
		"fallback_unknown_action": fallback_unknown_action,
		"windowed_co_occurrence_match": windowed_match,
	}


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
	window_size = parse_co_occurrence_window_size(match_policy)
	if window_size is not None:
		window_match, _, _, _, _, _ = evaluate_co_occurrence_phrase_groups_with_window(
			text,
			normalize_payload_optional_fields(payload),
			rule,
			window_size,
		)
		return window_match
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
	normalized_payload = normalize_payload_optional_fields(payload)
	rule = str(normalized_payload.get("normalisation_rule", "") or "").strip()
	decision_rule = normalize_decision_rule_name(str(payload.get("decision_rule", "") or "").strip())
	match_policy = str(normalized_payload.get("match_policy", "") or "").strip()
	if decision_rule not in SUPPORTED_DECISION_RULES:
		raise ValueError(f"Unsupported Layer 1 decision_rule: {decision_rule}")
	excluded_terms = [
		normalize_text(term, rule)
		for term in normalized_payload.get("excluded_terms", [])
		if normalize_text(term, rule)
	]
	normalized_text = normalize_text(text, rule)
	has_excluded = any(term in normalized_text for term in excluded_terms)
	policy_match = evaluate_match_policy(text, normalized_payload, row=row, component_id=component_id)
	diagnostic_flags: list[str] = []

	def finalize(evidence_status: str, candidate_was_positive: bool = False) -> tuple[str, str]:
		if has_excluded and candidate_was_positive:
			diagnostic_flags.append("excluded_term_veto")
			diagnostic_flags.append("excluded_term_override")
		unique_flags = [flag for index, flag in enumerate(diagnostic_flags) if flag and flag not in diagnostic_flags[:index]]
		return (evidence_status, ",".join(unique_flags) if unique_flags else "none")

	def evaluate_group_rule(allow_fallback: bool) -> tuple[bool, dict[str, object]]:
		context = evaluate_group_match_with_augmentations(
			text,
			normalized_payload,
			rule,
			match_policy,
			allow_fallback=allow_fallback,
		)
		if context.get("derived_feature_recovered"):
			diagnostic_flags.append("derived_feature_recovered")
		if context.get("derived_structural_feature_matched"):
			diagnostic_flags.append("derived_structural_feature_matched")
		if context.get("derived_structural_feature_pattern_not_matched"):
			diagnostic_flags.append("derived_structural_feature_pattern_not_matched")
		if context.get("implicit_feature_recovery_used"):
			diagnostic_flags.append("implicit_feature_recovery_used")
		if context.get("fallback_rule_used"):
			diagnostic_flags.append("fallback_rule_used")
		if context.get("fallback_restricted_effect_form_matched"):
			diagnostic_flags.append("fallback_restricted_effect_form_matched")
		if context.get("fallback_restricted_effect_form_not_matched"):
			diagnostic_flags.append("fallback_restricted_effect_form_not_matched")
		if context.get("present_via_fallback"):
			diagnostic_flags.append("present_via_fallback")
		if context.get("fallback_unknown_action"):
			diagnostic_flags.append("fallback_unknown_action")
		if context.get("windowed_co_occurrence_match"):
			diagnostic_flags.append("windowed_co_occurrence_match")
		return (bool(context.get("policy_or_fallback_match", False)), context)

	if decision_rule == "present_if_any_allowed_term_found":
		candidate = policy_match
		return finalize("present" if candidate else "not_present", candidate_was_positive=candidate)
	if decision_rule == "present_if_exact_match_or_alias_and_not_excluded":
		if match_policy in {"exact_or_alias_article_insensitive", "exact_or_alias_article_insensitive_any_conjunct"}:
			matches = resolve_matches_for_candidates(
				expand_candidates_with_conjuncts(extract_candidate_units(text, rule), rule)
				if match_policy == "exact_or_alias_article_insensitive_any_conjunct"
				else extract_candidate_units(text, rule),
				normalized_payload,
				rule,
				excluded_terms,
			)
			candidate = bool(matches)
			return finalize("present" if candidate else "not_present", candidate_was_positive=candidate)
		candidate = policy_match
		return finalize("present" if candidate and not has_excluded else "not_present", candidate_was_positive=candidate)
	if decision_rule == "present_if_matches_stage_or_role_and_not_excluded":
		candidate = policy_match
		return finalize("present" if candidate and not has_excluded else "not_present", candidate_was_positive=candidate)
	if decision_rule == "present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded":
		matches = extract_stage_phrase_matches_after_normalisation(text, normalized_payload, rule, excluded_terms)
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
		return finalize(evidence_status, candidate_was_positive=bool(matches))
	if decision_rule == "present_if_minimum_group_matches_met_and_not_excluded":
		if match_policy == "co_occurrence_lemma" or parse_co_occurrence_window_size(match_policy) is not None:
			candidate, context = evaluate_group_rule(allow_fallback=False)
			matched_excluded_terms = find_matched_excluded_terms(text, excluded_terms, rule)
			evidence_status = "present" if candidate and not matched_excluded_terms else "not_present"
			logger.debug(
				"Decision rule %s match_policy=%s normalisation_rule=%s final_status=%s raw_segment=%r normalized_segment=%r required_term_groups=%s minimum_match_count_per_group=%s matched_terms_by_group=%s matched_excluded_terms=%s",
				decision_rule,
				match_policy,
				rule,
				evidence_status,
				text,
				context.get("normalized_text", normalized_text),
				context.get("normalized_required_term_groups", {}),
				context.get("minimum_match_count", 0),
				context.get("matched_terms_by_group", {}),
				matched_excluded_terms,
			)
			return finalize(evidence_status, candidate_was_positive=candidate)
		candidate = policy_match
		return finalize("present" if candidate and not has_excluded else "not_present", candidate_was_positive=candidate)
	if decision_rule == "present_if_minimum_group_matches_met_or_fallback_and_not_excluded":
		candidate, context = evaluate_group_rule(allow_fallback=True)
		matched_excluded_terms = find_matched_excluded_terms(text, excluded_terms, rule)
		evidence_status = "present" if candidate and not matched_excluded_terms else "not_present"
		logger.debug(
			"Decision rule %s match_policy=%s normalisation_rule=%s final_status=%s raw_segment=%r normalized_segment=%r required_term_groups=%s minimum_match_count_per_group=%s matched_terms_by_group=%s matched_excluded_terms=%s",
			decision_rule,
			match_policy,
			rule,
			evidence_status,
			text,
			context.get("normalized_text", normalized_text),
			context.get("normalized_required_term_groups", {}),
			context.get("minimum_match_count", 0),
			context.get("matched_terms_by_group", {}),
			matched_excluded_terms,
		)
		return finalize(evidence_status, candidate_was_positive=candidate)
	if decision_rule == "present_if_no_excluded_terms_found":
		return finalize("present" if not has_excluded else "not_present", candidate_was_positive=not has_excluded)
	if decision_rule == "present_if_any_allowed_term_found_and_not_only_excluded":
		candidate = policy_match
		return finalize("present" if candidate else "not_present", candidate_was_positive=candidate)
	if decision_rule == "present_if_canonical_mappings_are_distinct":
		candidate = policy_match
		return finalize("present" if candidate and not has_excluded else "not_present", candidate_was_positive=candidate)
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
		if not left_text and not right_text:
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