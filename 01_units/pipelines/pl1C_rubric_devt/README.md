# pl1C_rubric_devt

This pipeline directory is organized around Layer 1 rubric development.

## Conceptual Model

- `iteration`: a rubric-development episode.
- `registry version`: a checkpoint of the indicator registry within an iteration.
- `run`: one repeated scoring execution against a fixed registry version and fixed scoring prompts.

Use these distinctions consistently:

- Start a new `iteration` when the rubric-development episode changes.
- Create a new `registry version` when the indicator registry changes during stage13 refinement.
- Create a new `run` when repeating scoring with the same registry and same prompts.

## Workflow Meaning

- `iter00` is typically the bootstrap iteration.
- Early stages such as `stage01`, `stage02`, `stage03`, and `stage11+12-merged` produce the initial indicator registry.
- `stage13` is the registry refinement loop.
- Later iterations may begin directly at `stage13` if upstream stages do not need to be rerun.

## Practical Implication

Do not use new iterations merely to repeat scoring.

Instead:

- keep the same iteration while the registry is unchanged,
- keep the same registry version while prompts are unchanged,
- store repeated scoring passes as separate runs,
- reserve new iterations for actual registry-development changes.

## Directory Intent

- `llm_prompt/`: prompt assets used by the LLM-based path.
- `python/`: deterministic orchestration and reporting scripts.
- `scaffold/`: scaffold templates used by the Python prompt-generation path.

## Layer 1 Deterministic Registry Augmentation

The deterministic Layer 1 scorer now supports optional, registry-declared augmentation fields for Python-scored indicators.

These fields are optional and backward compatible:

- `match_policy`
	- Existing values continue to work (for example `exact_or_alias`, `co_occurrence_lemma`).
	- Also supports `co_occurrence_window_N` where `N` is a positive integer.
- `derived_structural_feature_rule`
- `implicit_feature_recovery`
- `domain_artifact_tokens`
- `fallback_rule`
- `decision_rule`
	- Includes `present_if_minimum_group_matches_met_or_fallback_and_not_excluded`.

### Rule String Syntax

Optional rule objects may be encoded as semicolon-delimited key-value strings:

`enabled: true; condition: effect_form_present AND direct_object_present; action: treat_object_as_structural_feature`

Notes:

- Boolean values accepted for `enabled`: `true/false`, `yes/no`, `1/0`, `on/off`.
- Condition expressions support `AND`, `OR`, `NOT`, and parentheses.
- Unknown keys are ignored unless consumed by runtime logic.
- Malformed optional rule strings fail safe to disabled behavior.

`domain_artifact_tokens` accepts comma-delimited lists (or JSON arrays in payload JSON).

### Windowed Co-Occurrence

`co_occurrence_window_N` applies group matching only when required group terms occur within a normalized token window of size `N`.

- Normalization is applied before token window checks.
- Multiword phrase terms are supported.
- Existing `co_occurrence_lemma` behavior remains unchanged when a windowed policy is not configured.

### Derived Feature Recovery and Fallback

Recovery and fallback are generic, registry-driven behaviors:

- Derived or implicit feature recovery can satisfy one missing required group when enabled and condition checks pass.
- Fallback is applied only after normal matching fails and only when `fallback_rule.enabled` is true.
- Excluded-term checks still veto final `present` status.
- For slot-bound indicators, scoring resolves only from the bound Layer 0 segment unless `bound_segment_resolution_policy` explicitly allows fallback.

### Diagnostics Flags

The scorer may emit non-breaking diagnostic flags in `flags`:

- `derived_feature_recovered`
- `implicit_feature_recovery_used`
- `fallback_rule_used`
- `windowed_co_occurrence_match`
- `excluded_term_override`

Diagnostics are informational and do not override the configured decision rule outcome.
