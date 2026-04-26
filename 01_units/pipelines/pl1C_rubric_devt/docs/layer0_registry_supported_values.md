# Layer 0 Registry Supported Values

This reference lists machine-supported values that are validated and/or interpreted by the Layer 0 registry compiler and runtime.

## How to Read This Document

- Use this file as the practical contract between registry authoring and runtime behavior.
- If a value is listed as supported, it is validated and has executable meaning.
- If a value is not listed here, assume it is not supported unless code says otherwise.
- "Expanded instances" means rows emitted after template expansion and before OperatorSpec compilation.

## Quick Start (Most Common Layer 0 Pattern)

For a typical post-anchor noun phrase extractor (for example slot `02`):

1. Set `output_mode=span`.
2. Use `runtime_family=right_np_after_anchor_before_marker` (or omit and let slot mapping derive it for `02`).
3. Provide `anchor_patterns` (for example `interacts with, connect with`).
4. Set `candidate_selection_policy=first_local_candidate`.
5. Set `stop_markers=through, comma, clause_boundary`.
6. Choose `allow_coordination=true` if you want coordinated phrases included.

If you do only those six things, you usually get predictable Layer 0 behavior.

## Registry Tables and Fields

| Table                                     | Field                        | Supported values                                                                                                                                                                                                                                                                           | Notes                                                                         |
| ----------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| `registry_metadata`                       | `layer`                      | `auto`, `layer0`                                                                                                                                                                                                                                                                           | Any other value is rejected.                                                  |
| `operator_templates`                      | `output_mode`                | `span`, `status_only`                                                                                                                                                                                                                                                                      | `status_only` is only valid with `status_only_anchor_detector` family.        |
| `operator_templates` / expanded instances | `runtime_family`             | `left_np_before_anchor`, `right_np_after_anchor_before_marker`, `span_after_marker_before_marker`, `finite_verb_after_prior_span_before_marker`, `local_effect_phrase_after_marker`, `local_action_object_span_from_anchor`, `status_only_anchor_detector`, `claim_text_passthrough_if_anchor`, `claim_text_passthrough_no_anchor` | If omitted, family is derived from `local_slot`/`output_mode`.                |
| `operator_templates` / expanded instances | `local_slot`                 | Derived families supported for `00`, `01`, `02`, `03`, `04`, `05`                                                                                                                                                                                                                          | For other slots, set an explicit supported `runtime_family`.                  |
| expanded instances                        | `instance_status`            | `active`                                                                                                                                                                                                                                                                                   | Inactive rows are not compiled/executed.                                      |
| expanded instances                        | `anchor_selection_policy`    | `first_match`, `first_after_precondition`                                                                                                                                                                                                                                                  | `first_after_precondition` requires non-empty `anchor_precondition_patterns`. |
| expanded instances                        | `candidate_selection_policy` | `unspecified`, `first_local_candidate`, `anchor_plus_first_local_candidate`                                                                                                                                                                                                                | First-candidate style policies enforce first local candidate behavior.         |
| expanded instances                        | `later_candidate_handling`   | `unspecified`, `ignore_later_candidates`                                                                                                                                                                                                                                                   | Used with first-candidate style procedures.                                   |
| expanded instances                        | `requires_prior_segment`     | any non-empty segment id (for `finite_verb_after_prior_span_before_marker`)                                                                                                                                                                                                                | Required for `finite_verb_after_prior_span_before_marker`; ignored otherwise. |
| expanded instances                        | `stop_markers`               | `comma`, `sentence_start`, `conjunction_boundary`, `through`, `to`, `which`, `that`, `who`, `where`, `within`, `during`, `at`, `before`, `clause_boundary`, `shaping`, `by`, `comma_new_clause`, `subordinate_extension`, `sentence_end`                                                   | Unknown markers are rejected.                                                 |
| expanded instances                        | `allow_coordination`         | `true`, `false`, blank                                                                                                                                                                                                                                                                     | Blank means derive from template override/text/family defaults.               |

### Field-by-Field Explanation

#### `registry_metadata.layer`
- Purpose: Guards that this registry is intended for Layer 0 parsing.
- Supported values:
	- `auto`: allow auto-detection flow.
	- `layer0`: explicitly Layer 0.
- If set incorrectly, registry loading fails early.

#### `output_mode`
- Purpose: Controls whether the operator emits a text span or only status.
- Values:
	- `span`: produce segment text.
	- `status_only`: report anchor/status only, no segment text.
- Compatibility rule: `status_only` must pair with family `status_only_anchor_detector`.

#### `runtime_family`
- Purpose: Selects extraction algorithm family.
- If omitted, family is derived from `local_slot` and `output_mode`.
- Use explicit family when you need behavior that differs from slot defaults.

#### `local_slot`
- Purpose: Encodes slot position and default behavior profile.
- Built-in mapping supports `00`-`05` out of the box.
- For non-standard slots, specify a supported explicit `runtime_family`.

#### `instance_status`
- Purpose: Controls whether an expanded row is executable.
- Current executable value is `active`.
- Non-active rows are filtered/rejected in compile/runtime validation.

#### `anchor_selection_policy`
- Purpose: Defines which matching anchor to choose.
- Values:
	- `first_match`: first anchor occurrence in text.
	- `first_after_precondition`: first anchor after first matching precondition.
- Extra requirement: `first_after_precondition` needs non-empty `anchor_precondition_patterns`.

#### `candidate_selection_policy`
- Purpose: Chooses how candidate spans are selected once anchor is found.
- Values:
	- `unspecified`: family default behavior.
	- `first_local_candidate`: choose first local candidate and do not skip to later candidates.
	- `anchor_plus_first_local_candidate`: choose first local candidate with anchor-inclusive extraction semantics in families that support it.

#### `later_candidate_handling`
- Purpose: Encodes what to do with later candidates after first candidate logic.
- Values:
	- `unspecified`
	- `ignore_later_candidates`

#### `stop_markers`
- Purpose: Defines boundaries that terminate span growth.
- Unknown marker names are rejected.
- See "Stop Marker Semantics" below for practical behavior.

#### `allow_coordination`
- Purpose: Controls whether compact coordination is included in the same slot span.
- Values:
	- `true`: include coordinated continuation when boundary-safe.
	- `false`: do not extend across coordination boundary.
	- blank: derive from overrides/text/family defaults.

#### `requires_prior_segment`
- Purpose: Declares a segment dependency for families that must start scanning after a prior successful extraction.
- Values:
	- non-empty segment id string (for example `02_ToolArtefactOutput`).
- Requirement: `finite_verb_after_prior_span_before_marker` requires this field.

## Operational Defaults and Derived Values

| Context                              | Value                                                                   |
| ------------------------------------ | ----------------------------------------------------------------------- |
| Default `anchor_selection_policy`    | `first_match`                                                           |
| Default `candidate_selection_policy` | `unspecified`                                                           |
| Default `later_candidate_handling`   | `unspecified`                                                           |
| Default target types by slot         | `01-04 -> noun_phrase`, `05 -> local_effect_phrase`, `00 -> claim_text` |
| Slot 02 default stop markers         | `through`, `comma`, `clause_boundary`                                   |
| Slot 03 default stop markers         | `shaping`, `comma`, `clause_boundary`                                   |
| Slot 04 default stop markers         | `by`, `comma`, `clause_boundary`                                        |
| Slot 05 default stop markers         | `comma_new_clause`, `subordinate_extension`, `sentence_end`             |

### Slot-Derived Family Defaults

When `runtime_family` is omitted:

| local_slot | Derived family | Typical intent |
| --- | --- | --- |
| `00` | `claim_text_passthrough_if_anchor` | Keep full claim text when anchor exists |
| `01` | `left_np_before_anchor` | Extract noun phrase before interaction anchor |
| `02` | `right_np_after_anchor_before_marker` | Extract noun phrase after interaction anchor |
| `03` | `span_after_marker_before_marker` | Extract mechanism-like phrase after marker |
| `04` | `right_np_after_anchor_before_marker` | Extract workflow/role-like noun phrase |
| `05` | `local_effect_phrase_after_marker` | Extract local effect phrase after marker |

## Registry-Declared but Open-Ended Fields

| Field | Interpretation |
| --- | --- |
| `anchor_patterns` | Case-insensitive, word-boundary-safe lexical patterns used for runtime anchor matching. |
| `anchor_precondition_patterns` | Lexical patterns used before anchor matching when policy is `first_after_precondition`. |
| `operator_definition`, `operator_guidance`, `decision_procedure`, `failure_mode_guidance` | Documentation plus partial machine encoding checks (for certain directives). |

## Stop Marker Semantics (Practical)

The runtime converts marker names into boundary checks.

| stop_marker | Practical meaning |
| --- | --- |
| `through` | Stop before lexical token `through` |
| `to` | Stop before lexical token `to` |
| `which` | Stop before lexical token `which` |
| `that` | Stop before lexical token `that` |
| `who` | Stop before lexical token `who` |
| `where` | Stop before lexical token `where` |
| `within` | Stop before lexical token `within` |
| `during` | Stop before lexical token `during` |
| `at` | Stop before lexical token `at` |
| `before` | Stop before lexical token `before` |
| `shaping` | Stop before lexical token `shaping` |
| `by` | Stop before lexical token `by` |
| `comma` | Stop at the next comma |
| `comma_new_clause` | Stop at comma patterns that look like new clause starts |
| `clause_boundary` | Stop at punctuation/conjunction/subordinate boundary signals |
| `subordinate_extension` | Stop before subordinate starters like `which`, `that`, `because`, etc. |
| `sentence_end` | Stop before `.`, `!`, `?` |
| `sentence_start` | Boundary at next sentence start position |
| `conjunction_boundary` | Left-boundary helper for pre-anchor extraction |

## Examples

### Example A: First Anchor After Precondition

- `anchor_precondition_patterns=shaping`
- `anchor_patterns=by`
- `anchor_selection_policy=first_after_precondition`

Behavior: ignore `by` before `shaping`, then use first `by` after `shaping`.

### Example B: First Local Candidate Policy

- `candidate_selection_policy=first_local_candidate`
- `later_candidate_handling=ignore_later_candidates`

Behavior: once first plausible local span is found, do not jump to a later "better sounding" span.

### Example C: Coordination Toggle

Input fragment: `documentation and record-keeping standards for audit`

- `allow_coordination=true` -> coordinated phrase can be included.
- `allow_coordination=false` -> extraction may stop at first local unit.

### Example D: Anchor-Inclusive Action-Object Span

- `runtime_family=local_action_object_span_from_anchor`
- `anchor_patterns=record, records`
- `stop_markers=within, during, at, sentence_end`

Behavior: extraction starts at the matched action anchor and includes the verb, for example `record applicant information`.

## What This File Does Not Guarantee

- It does not promise perfect linguistic parsing.
- It does not encode assignment-specific semantics.
- It does not replace tests; it documents supported machine contracts.

## Canonical Source Files

- `generate_schema_from_segmentation_registry.py`
- `layer0_runtime/loader.py`
- `layer0_runtime/models.py`
- `layer0_runtime/boundaries.py`
