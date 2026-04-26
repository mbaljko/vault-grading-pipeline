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

| Field                                           | Supported values                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Notes                                                                                                                                                                                                            |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scoring_mode`                                  | Required, open-ended string                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Required by parser; no strict value enumeration in current code.                                                                                                                                                 |
| `dependency_type`                               | Required, open-ended string                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Required by parser; no strict value enumeration in current code.                                                                                                                                                 |
| `bound_segment_id`                              | Required, open-ended string                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Required by parser; used for segment-field resolution.                                                                                                                                                           |
| `normalisation_rule`                            | `""`, `lowercase`, `lowercase_trim`, `lowercase_trim_strip_stage_suffix`, `lowercase_trim_strip_leading_determiner`, `lowercase_lemma_effect_terms`                                                                                                                                                                                                                                                                                                                                                   | Any other value is rejected.                                                                                                                                                                                     |
| `match_policy`                                  | `substring_any`, `exact_or_alias`, `exact_or_alias_article_insensitive`, `exact_or_alias_article_insensitive_any_conjunct`, `exact_or_alias_or_role`, `co_occurrence`, `co_occurrence_lemma`, `non_empty`, `absence_check`, `canonical_inequality`, `co_occurrence_window_N`                                                                                                                                                                                                                          | `co_occurrence_window_N` is supported when `N` is a positive integer. `non_empty` returns a positive match when the resolved segment text contains non-whitespace content.                                       |
| `decision_rule`                                 | `present_if_any_allowed_term_found`, `present_if_exact_match_or_alias_and_not_excluded`, `present_if_matches_stage_or_role_and_not_excluded`, `present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded`, `present_if_minimum_group_matches_met_and_not_excluded`, `present_if_minimum_group_matches_met_or_fallback_and_not_excluded`, `present_if_no_excluded_terms_found`, `present_if_any_allowed_term_found_and_not_only_excluded`, `present_if_canonical_mappings_are_distinct` | Decision-rule aliases are normalized (see alias table below).                                                                                                                                                    |
| `bound_segment_resolution_policy`               | `hard_stay`, `fallback_to_evidence_text`                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Defaults to `hard_stay` when omitted/blank.                                                                                                                                                                      |
| `required_layer0_records`                       | Semicolon-delimited predicates: `SXX:ok`, `SXX:not_ok`                                                                                                                                                                                                                                                                                                                                                                                                                                                | Evaluated as conjunction (AND) before scoring. `SXX:ok` requires an `ok` record. `SXX:not_ok` passes when `SXX` is absent or any non-`ok` status. Unsupported predicates are rejected by generator validation.   |
| `required_term_groups`                          | Mapping of `group_name -> list[str]`                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Used by co-occurrence policies.                                                                                                                                                                                  |
| `minimum_match_count_per_group`                 | Integer (`>= 0` accepted; effective minimum is 1 during matching)                                                                                                                                                                                                                                                                                                                                                                                                                                     | Used with grouped-term matching.                                                                                                                                                                                 |
| `allowed_terms`                                 | List of strings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Used by exact/substring/stage matching families. Not required for `match_policy=non_empty`.                                                                                                                      |
| `allowed_aliases`                               | Mapping `alias -> canonical`                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Alias keys and canonical values are normalized under selected normalisation rule.                                                                                                                                |
| `allowed_roles`                                 | List of strings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Used with `match_policy=exact_or_alias_or_role`.                                                                                                                                                                 |
| `excluded_terms`                                | List of strings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Evaluated after normalization; may veto positive matches by decision-rule semantics.                                                                                                                             |
| `left_segment_id`, `right_segment_id`           | Strings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Used with `match_policy=canonical_inequality`; defaults are `DemandA` and `DemandB` when omitted.                                                                                                                |
| `left_allowed_terms`, `right_allowed_terms`     | Lists of strings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Used with `canonical_inequality`.                                                                                                                                                                                |
| `left_allowed_aliases`, `right_allowed_aliases` | Mapping `alias -> canonical`                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Used with `canonical_inequality`.                                                                                                                                                                                |
| `derived_structural_feature_rule`               | Mapping or semicolon `key: value` rule string                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Optional augmentation field; normalized to config with `enabled` default `false`. If `patterns` is declared and `enabled=true`, derived recovery requires at least one pattern match on normalized segment text. |
| `implicit_feature_recovery`                     | Mapping or semicolon `key: value` rule string                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Optional augmentation field; normalized to config with `enabled` default `false`.                                                                                                                                |
| `fallback_rule`                                 | Mapping or semicolon `key: value` rule string                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Optional augmentation field; normalized to config with `enabled` default `false`. Supports `restricted_effect_forms` and `action` enforcement.                                                                   |
| `domain_artifact_tokens`                        | Comma-delimited string or list of strings                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Optional augmentation tokens; normalized to list.                                                                                                                                                                |

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

Enforced augmentation sub-keys:

- `derived_structural_feature_rule.patterns`
	- Optional list-like value.
	- When present with `enabled=true`, derived recovery succeeds only if at least one declared pattern matches normalized segment text.
	- If omitted, default derived-recovery behavior is preserved.
- `fallback_rule.restricted_effect_forms`
	- Optional list-like value.
	- When present, fallback requires at least one restricted effect form match.
	- Runtime does not silently widen to full `effect_forms` when this key is declared.
- `fallback_rule.action`
	- Supported: `accept_as_present_with_flag`.
	- If fallback succeeds with this action, scorer emits `present_via_fallback`.
	- If fallback succeeds and action is omitted, default fallback behavior is preserved.
	- Unknown actions do not crash; fallback is not applied and `fallback_unknown_action` is emitted.

List-like value forms accepted for `patterns` and `restricted_effect_forms`:

- JSON/Python-like list strings, for example `["allocate", "assign"]`.
- Tuple-like strings, for example `(allocate, assign)`.
- Native list values in payload JSON.

Pattern matching behavior for `derived_structural_feature_rule.patterns`:

- Case-insensitive matching against normalized segment text.
- Simple substring patterns are supported by default.
- Regex-style patterns are supported via `re:<pattern>` or `/pattern/` forms.

Condition expressions support:

- identifiers (for example `effect_form_present`, `direct_object_present`, `domain_artifact_present`)
- logical operators `AND`, `OR`, `NOT`
- parentheses.

## Required Layer 0 Record Predicates

`required_layer0_records` is parsed as a semicolon-delimited list of requirements.

Accepted item forms:

- `S00:ok`
- `S03:not_ok`
- `S00:ok; S03:not_ok`

Whitespace around items is ignored.

Predicate semantics:

- `SXX:ok` passes only if at least one Layer 0 record exists for `SXX` with `extraction_status=ok`.
- `SXX:not_ok` passes if no `ok` record exists for `SXX`.
	- This includes cases where `SXX` is absent.
	- This also includes cases where `SXX` exists but status is non-`ok` (for example `missing`, `ambiguous`, `malformed`, or other non-`ok` values).

Conjunction logic:

- Multiple requirements are evaluated as `AND`.
- Example: `S00:ok; S03:not_ok` passes only when `S00` is `ok` and `S03` is not `ok` (or absent).

## Diagnostics Flags (Output)

The Layer 1 scorer emits comma-separated flags in output rows.

Supported flag values:

- `none`
- `missing_input_text`
- `required_layer0_ok_missing`
- `required_layer0_not_ok_failed`
- `required_layer0_predicate_unsupported`
- `derived_feature_recovered`
- `derived_structural_feature_matched`
- `derived_structural_feature_pattern_not_matched`
- `implicit_feature_recovery_used`
- `fallback_rule_used`
- `fallback_restricted_effect_form_matched`
- `fallback_restricted_effect_form_not_matched`
- `present_via_fallback`
- `fallback_unknown_action`
- `windowed_co_occurrence_match`
- `excluded_term_veto`
- `excluded_term_override`

Diagnostics are non-breaking metadata; they do not override decision-rule outcomes by themselves.

## Non-Empty Pass-Through Pattern

Use this when you want a pure segment-presence signal with no lexical filtering.

```yaml
match_policy: non_empty
decision_rule: present_if_any_allowed_term_found
```

Behavior notes:

- If resolved segment text is non-empty after trimming whitespace, output is `present`.
- If resolved segment text is empty/whitespace, output is `not_present` and emits `missing_input_text`.
- `allowed_terms` is not required and is ignored/removed by module-generation validation for this policy.

## Operational Defaults and Derived Behavior

| Context | Value |
| --- | --- |
| Default `bound_segment_resolution_policy` | `hard_stay` |
| Default optional-rule enablement | `enabled=false` when missing/malformed |
| `co_occurrence_window_N` validity | Supported only when `N > 0` |
| Grouped matching minimum | `minimum_match_count_per_group` values below `1` behave as `1` at match time |
| Domain artifact token input forms | Comma-delimited string or list |
| Fallback unknown action handling | Non-fatal; fallback is not applied; emits `fallback_unknown_action` |
| Excluded-term behavior | Excluded terms veto primary, derived, and fallback positive paths |

## Registry-Declared but Open-Ended Fields

These are required/consumed but not strictly enumerated in current validation:

- `scoring_mode`
- `dependency_type`
- `bound_segment_id` (string value itself is open-ended)
- textual content of `allowed_terms`, `allowed_aliases`, `required_term_groups`, and related lexical lists.

## Example Registry Row (B_claim_core_06 Style)

This example shows a fully augmented Layer 1 row using windowed grouped matching, derived-pattern enforcement, restricted fallback effect forms, and fallback action semantics.

```yaml
template_id: B_claim_core_06
local_slot: "06"
sbo_short_description: structural effect expressed
status: active

scoring_mode: python
dependency_type: slot_primary
required_layer0_records: S05:ok
bound_segment_id: 05_Effect
bound_segment_resolution_policy: hard_stay

normalisation_rule: lowercase_lemma_effect_terms
match_policy: co_occurrence_window_5
minimum_match_count_per_group: 1

required_term_groups:
	structural_features:
		- applications
		- files
		- reviewers
		- records
		- written justifications
	effect_forms:
		- allocate
		- assign
		- distribute
		- organize
		- sequence
		- structure

excluded_terms:
	- better
	- worse
	- fair
	- beneficial
	- harmful

derived_structural_feature_rule:
	enabled: true
	condition: effect_form_present AND direct_object_present
	action: treat_object_as_structural_feature
	patterns:
		- "<effect_form> + applications/files/reviewers/documents/scores"
		- "NP containing review/application/score/file/document/committee"

implicit_feature_recovery:
	enabled: true
	condition: effect_form_present AND direct_object_present
	action: treat_object_as_structural_feature

domain_artifact_tokens:
	- application
	- file
	- reviewer
	- review
	- document
	- score
	- committee

fallback_rule:
	enabled: true
	condition: effect_form_present AND direct_object_present
	restricted_effect_forms: [allocate, assign, distribute, structure, organise, organize, sequence, constrain]
	action: accept_as_present_with_flag

decision_rule: present_if_minimum_group_matches_met_or_fallback_and_not_excluded
```

Runtime interpretation notes:

- `co_occurrence_window_5` enforces grouped phrase co-occurrence within a 5-token window.
- If `derived_structural_feature_rule.patterns` is present and `enabled=true`, derived recovery requires at least one pattern match.
- `fallback_rule.restricted_effect_forms` must match for fallback to succeed when the key is declared.
- `fallback_rule.action=accept_as_present_with_flag` allows fallback to score as `present` and emits `present_via_fallback`.
- `excluded_terms` still veto primary, derived, and fallback positive paths.

Gate diagnostics notes:

- `required_layer0_ok_missing`: a required `SXX:ok` predicate failed.
- `required_layer0_not_ok_failed`: a required `SXX:not_ok` predicate failed because `SXX` was `ok`.
- `required_layer0_predicate_unsupported`: an unsupported predicate was supplied.

## What This File Does Not Guarantee

- It does not promise perfect linguistic or semantic inference.
- It does not encode assignment-specific semantics.
- It does not replace tests; it documents supported machine contracts.

## Canonical Source Files

- `01_units/pipelines/pl1C_rubric_devt/python/layer1_indicator_scoring_runtime.py`
- `01_units/pipelines/pl1C_rubric_devt/python/generate-layer1-indicator-scoring-module.py`
- `01_units/pipelines/pl1C_rubric_devt/python/test_layer1_indicator_scoring_runtime.py`
