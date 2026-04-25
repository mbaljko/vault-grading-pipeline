# Layer 1 Registry Supported Values

This reference lists machine-supported values that are validated and/or interpreted by the Layer 1 deterministic registry parser and runtime.

## How to Read This Document

- Use this file as the practical contract between Layer 1 registry authoring and deterministic runtime behavior.
- If a value is listed as supported, it is validated and/or has executable meaning.
- If a value is not listed here, assume it is not supported unless code says otherwise.
- This document covers the `indicator_scoring_payload_json` contract used by generated Layer 1 Python scorers.

## Quick Start (Most Common Layer 1 Pattern)

For a typical grouped co-occurrence indicator:

1. Set `normalisation_rule=lowercase_trim` (or `lowercase_lemma_effect_terms` if effect-term lemmatization is needed).
2. Set `match_policy=co_occurrence_lemma`.
3. Set `decision_rule=present_if_minimum_group_matches_met_and_not_excluded`.
4. Provide `required_term_groups` with at least `minimum_match_count_per_group=1`.
5. Keep `bound_segment_resolution_policy=hard_stay` unless explicit fallback to broader text is required.

For windowed group matching, use `match_policy=co_occurrence_window_N` where `N` is a positive integer.

## Registry Payload Fields and Supported Values

| Field | Supported values | Notes |
| --- | --- | --- |
| `scoring_mode` | Required, open-ended string | Required by parser; no strict value enumeration in current code. |
| `dependency_type` | Required, open-ended string | Required by parser; no strict value enumeration in current code. |
| `bound_segment_id` | Required, open-ended string | Required by parser; used for segment-field resolution. |
| `normalisation_rule` | `""`, `lowercase`, `lowercase_trim`, `lowercase_trim_strip_stage_suffix`, `lowercase_trim_strip_leading_determiner`, `lowercase_lemma_effect_terms` | Any other value is rejected. |
| `match_policy` | `substring_any`, `exact_or_alias`, `exact_or_alias_article_insensitive`, `exact_or_alias_article_insensitive_any_conjunct`, `exact_or_alias_or_role`, `co_occurrence`, `co_occurrence_lemma`, `absence_check`, `canonical_inequality`, `co_occurrence_window_N` | `co_occurrence_window_N` is supported when `N` is a positive integer. |
| `decision_rule` | `present_if_any_allowed_term_found`, `present_if_exact_match_or_alias_and_not_excluded`, `present_if_matches_stage_or_role_and_not_excluded`, `present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded`, `present_if_minimum_group_matches_met_and_not_excluded`, `present_if_minimum_group_matches_met_or_fallback_and_not_excluded`, `present_if_no_excluded_terms_found`, `present_if_any_allowed_term_found_and_not_only_excluded`, `present_if_canonical_mappings_are_distinct` | Decision-rule aliases are normalized (see alias table below). |
| `bound_segment_resolution_policy` | `hard_stay`, `fallback_to_evidence_text` | Defaults to `hard_stay` when omitted/blank. |
| `required_term_groups` | Mapping of `group_name -> list[str]` | Used by co-occurrence policies. |
| `minimum_match_count_per_group` | Integer (`>= 0` accepted; effective minimum is 1 during matching) | Used with grouped-term matching. |
| `allowed_terms` | List of strings | Used by exact/substring/stage matching families. |
| `allowed_aliases` | Mapping `alias -> canonical` | Alias keys and canonical values are normalized under selected normalisation rule. |
| `allowed_roles` | List of strings | Used with `match_policy=exact_or_alias_or_role`. |
| `excluded_terms` | List of strings | Evaluated after normalization; may veto positive matches by decision-rule semantics. |
| `left_segment_id`, `right_segment_id` | Strings | Used with `match_policy=canonical_inequality`; defaults are `DemandA` and `DemandB` when omitted. |
| `left_allowed_terms`, `right_allowed_terms` | Lists of strings | Used with `canonical_inequality`. |
| `left_allowed_aliases`, `right_allowed_aliases` | Mapping `alias -> canonical` | Used with `canonical_inequality`. |
| `derived_structural_feature_rule` | Mapping or semicolon `key: value` rule string | Optional augmentation field; normalized to config with `enabled` default `false`. |
| `implicit_feature_recovery` | Mapping or semicolon `key: value` rule string | Optional augmentation field; normalized to config with `enabled` default `false`. |
| `fallback_rule` | Mapping or semicolon `key: value` rule string | Optional augmentation field; normalized to config with `enabled` default `false`. |
| `domain_artifact_tokens` | Comma-delimited string or list of strings | Optional augmentation tokens; normalized to list. |

## Decision Rule Aliases

The parser/runtime normalize these legacy names:

| Alias input | Canonical decision_rule |
| --- | --- |
| `present_if_canonical_mapping_of_demand_a_not_equal_canonical_mapping_of_demand_b` | `present_if_canonical_mappings_are_distinct` |
| `present_if_any_stage_token_matches_after_normalisation_and_not_excluded` | `present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded` |

## Optional Rule-String Syntax

Optional augmentation rule objects can be encoded as semicolon-delimited key-value strings, for example:

`enabled: true; condition: effect_form_present AND direct_object_present; action: treat_object_as_structural_feature`

Supported parsing behavior:

- `enabled` accepts booleans: `true/false`, `yes/no`, `1/0`, `on/off`.
- Numeric values are parsed as integers when they are digit-only.
- Unknown keys are preserved but ignored unless consumed by runtime logic.
- Malformed optional rule strings fail safe to `enabled=false`.

Condition expressions support:

- identifiers (for example `effect_form_present`, `direct_object_present`, `domain_artifact_present`)
- logical operators `AND`, `OR`, `NOT`
- parentheses.

## Diagnostics Flags (Output)

The Layer 1 scorer emits comma-separated flags in output rows.

Supported flag values:

- `none`
- `missing_input_text`
- `derived_feature_recovered`
- `implicit_feature_recovery_used`
- `fallback_rule_used`
- `windowed_co_occurrence_match`
- `excluded_term_override`

Diagnostics are non-breaking metadata; they do not override decision-rule outcomes by themselves.

## Operational Defaults and Derived Behavior

| Context | Value |
| --- | --- |
| Default `bound_segment_resolution_policy` | `hard_stay` |
| Default optional-rule enablement | `enabled=false` when missing/malformed |
| `co_occurrence_window_N` validity | Supported only when `N > 0` |
| Grouped matching minimum | `minimum_match_count_per_group` values below `1` behave as `1` at match time |
| Domain artifact token input forms | Comma-delimited string or list |

## Registry-Declared but Open-Ended Fields

These are required/consumed but not strictly enumerated in current validation:

- `scoring_mode`
- `dependency_type`
- `bound_segment_id` (string value itself is open-ended)
- textual content of `allowed_terms`, `allowed_aliases`, `required_term_groups`, and related lexical lists.

## What This File Does Not Guarantee

- It does not promise perfect linguistic or semantic inference.
- It does not encode assignment-specific semantics.
- It does not replace tests; it documents supported machine contracts.

## Canonical Source Files

- `01_units/pipelines/pl1C_rubric_devt/python/layer1_indicator_scoring_runtime.py`
- `01_units/pipelines/pl1C_rubric_devt/python/generate-layer1-indicator-scoring-module.py`
- `01_units/pipelines/pl1C_rubric_devt/python/test_layer1_indicator_scoring_runtime.py`
