---
prompt_id: pl1B_stage13_layer1_indicator_scoring_prompt_wrapper_v01
version: v01
stage: pipeline_pl1B_stage13
purpose: generate a bounded Layer 1 SBO scoring prompt that performs indicator evidence detection for a single target component using the Layer1_ScoringManifest
status: active
owner: EECS3000W26
generation_parameters:
  temperature: 0
  top_p: 1
input_contract:
  - target_component_parameter (`PARAM_TARGET_COMPONENT_ID = <INSERT HERE>`)
  - assignment_payload_specification (<ASSESSMENT_ID>_AssignmentPayloadSpec_v*)
  - layer1_scoring_manifest (Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION>)
input_structure:
  delimiter: §§§
  parameter_block:
    required_format: PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>
  artefacts:
    - name: assignment_payload_specification
      expected_elements:
        - assessment_id
        - submission_id
        - component_id
        - response_text
      canonical_scoring_unit: submission_id_x_component_id
      evidence_rule: explicit_textual_evidence_only
    - name: layer1_scoring_manifest
      expected_elements:
        - component_id
        - sbo_identifier
        - indicator_id
        - sbo_short_description
        - indicator_definition
        - assessment_guidance
        - evaluation_notes
  artefact_order:
    - parameter_block
    - assignment_payload_specification
    - layer1_scoring_manifest
    - generation_trigger
manifest_processing:
  filtering_rule: filter_rows_where_component_id_equals_PARAM_TARGET_COMPONENT_ID
  validation_rules:
    - filtered_manifest_must_not_be_empty
    - indicator_id_values_must_be_unique_within_filtered_rows
output_contract: generated_scoring_prompt
output_structure:
  artefact_name_pattern: RUN_<ASSESSMENT_ID>_<PARAM_TARGET_COMPONENT_ID>_Layer1_SBO_scoring_prompt_v*
  output_container: fenced_markdown_block
  outer_fence: "````"
  required_sections:
    - Prompt title and restrictions
    - Authoritative scoring materials
    - Input format
    - Evaluation discipline
    - Evidence interpretation rules
    - Confidence assignment rule
    - Output schema
    - Constraints
    - Content rules
    - Failure mode handling
runtime_semantics:
  input_definition:
    - runtime_input_dataset_contains_one_or_more_rows
    - each_runtime_row_represents_submission_id_x_component_id
    - evaluate_rows_where_component_id_equals_target_component
    - do_not_stop_after_first_runtime_row
  batch_output_definition:
    - emit_one_csv_header_row_once
    - for_each_runtime_row_emit_one_row_per_indicator
    - group_output_rows_by_runtime_row
    - maintain_indicator_order_within_each_group
    - total_rows_equals_runtime_rows_times_indicator_count
evaluation_pipeline:
  sequence:
    - construct_internal_runtime_dataset_representation
    - identify_valid_runtime_rows_matching_target_component
    - apply_wrapper_handling_rules_per_runtime_row_if_required
    - construct_ordered_indicator_id_list_from_manifest
    - build_evidence_index_from_response_text
    - perform_single_analytic_signal_pass
    - group_candidate_fragments_by_indicator_relevance
    - evaluate_indicators_using_indexed_fragments
indicator_evidence_scale:
  values:
    - present
    - not_present
  definitions:
    present: explicit_textual_evidence_fully_and_clearly_satisfies_indicator_definition
    not_present: indicator_absent_or_supported_only_by_partial_weak_implicit_incomplete_vague_or_ambiguous_evidence
confidence_scale:
  values:
    - high
    - medium
    - low
  interpretation:
    high: decision_clearly_supported_by_explicit_evidence_or_clear_absence_of_qualifying_evidence
    medium: decision_boundary_is_close_and_may_require_review
    low: use_only_when_binary_decision_is_required_but_text_is_highly_unclear_or_malformed
output_schema:
  format: csv
  header: submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
  fields:
    - submission_id
    - component_id
    - indicator_id
    - evidence_status
    - evaluation_notes
    - confidence
    - flags
  allowed_flag_values:
    - none
    - needs_review
evaluation_rules:
  - each_indicator_evaluated_once_per_runtime_row
  - present_requires_explicit_fragment_that_fully_satisfies_indicator_definition
  - partial_or_weak_or_implicit_evidence_must_be_classified_as_not_present
  - indicators_must_be_evaluated_independently
  - dimension_logic_must_not_be_used
  - mapping_rules_must_not_be_used
  - component_performance_logic_must_not_be_used
  - no_inferential_reconstruction_of_missing_structure
content_rules:
  - output_must_be_csv_only
  - header_must_appear_once
  - evaluation_notes_must_be_double_quoted
  - empty_notes_must_be_emitted_as_double_quotes
  - component_id_must_equal_target_component
  - one_output_row_per_indicator_per_runtime_row
constraints:
  - do_not_modify_scoring_manifest
  - do_not_invent_indicators
  - do_not_perform_dimension_scoring
  - do_not_assign_component_or_submission_scores
  - evaluator_must_use_only_runtime_dataset_and_embedded_manifest
failure_conditions:
  - missing_required_parameter
  - malformed_delimiter_structure
  - missing_assignment_payload_specification
  - missing_layer1_scoring_manifest
  - filtered_manifest_empty
  - duplicate_indicator_ids_detected
  - runtime_dataset_contains_no_valid_rows
  - csv_header_cannot_be_emitted_exactly
notes: |
  This prompt performs Stage 1.3 of Pipeline PL1B. It generates a reusable
  Layer 1 SBO scoring prompt that evaluates indicator evidence using the
  Layer1_ScoringManifest. The wrapper filters indicators by the target
  component and embeds their definitions and detection guidance into a
  standalone scoring prompt capable of processing runtime datasets and
  producing indicator-level evidence status outputs for downstream
  Layer 2–4 rubric evaluation stages.
---
### **revised canonical output scaffold source for single-indicator scoring**

  

Use this as the new scaffold source for a prompt that scores exactly one indicator per run.

````
#### RUN_[[ASSESSMENT_ID]]_[[TARGET_COMPONENT_ID]]_[[TARGET_INDICATOR_ID]]_Layer1_SBO_scoring_prompt_v01

#### Prompt title and restrictions

This prompt performs **Layer 1 SBO scoring** for target component `[[TARGET_COMPONENT_ID]]` and target indicator `[[TARGET_INDICATOR_ID]]`.

It determines the `evidence_status` value for the embedded indicator SBO instance belonging to this component.

This prompt does **not**:

- evaluate dimensions
- evaluate indicator combinations
- apply indicator→dimension mappings
- assign component performance levels
- assign submission scores
- evaluate indicators belonging to other components
- evaluate any indicator other than `[[TARGET_INDICATOR_ID]]`

Layer 1 SBO scoring performs only:

```text
binary indicator presence detection
```

#### Authoritative scoring materials

Assessment identifier:

```text
[[ASSESSMENT_ID]]
```

Target component:

```text
[[TARGET_COMPONENT_ID]]
```

Target indicator:

```text
[[TARGET_INDICATOR_ID]]
```

Canonical scoring unit:

```text
submission_id × component_id × indicator_id
```

Runtime row identifier rule:

- The canonical submission-level identifier field is `[[SUBMISSION_IDENTIFIER_FIELD]]`.
- In output, copy the runtime row value from `[[SUBMISSION_IDENTIFIER_FIELD]]` into the CSV field named `submission_id`.

Evidence rule:

```text
explicit textual evidence only
```

Wrapper-handling rule for response text:

[[WRAPPER_HANDLING_RULE_BULLETS]]

Embedded indicator specification:

| indicator_id | sbo_short_description | indicator_definition | assessment_guidance | embedded evaluator guidance |
|---|---|---|---|---|
| [[INDICATOR_ID]] | [[SBO_SHORT_DESCRIPTION]] | [[INDICATOR_DEFINITION]] | [[ASSESSMENT_GUIDANCE]] | [[EMBEDDED_EVALUATOR_GUIDANCE]] |

Indicator evidence status scale:

| value | meaning |
|---|---|
| `present` | clear, sufficient, explicit textual evidence fully satisfies the indicator definition |
| `not_present` | the indicator is absent or supported only by partial, weak, implicit, incomplete, vague, or ambiguous evidence |

Field rules:

- `evaluation_notes` enclosed in double quotes
- empty notes represented as `""`

Use only:

- the runtime dataset rows
- canonical `response_text`
- the embedded indicator definition
- the embedded assessment guidance
- the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- the embedded evidence scale

Do not use:

- external knowledge
- dimension reasoning
- performance-level reasoning
- assumptions about intended meaning
- other indicators
- indicator combinations

Require all of the following:

- one CSV row for the embedded indicator **for each valid runtime row**
- complete coverage of all valid runtime rows in the runtime dataset
- `component_id = [[TARGET_COMPONENT_ID]]` in every emitted row
- `indicator_id = [[TARGET_INDICATOR_ID]]` in every emitted row
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

Produce no output if:

- the runtime dataset contains no valid runtime rows for the target component
- the CSV header cannot be emitted exactly as specified
- complete row coverage cannot be achieved for all valid runtime rows
- any contradiction prevents deterministic evaluation

#### Input format

Runtime input will contain a dataset with one or more runtime rows.  
Each runtime row represents one submission-level evaluation unit:
[[SUBMISSION_IDENTIFIER_FIELD]] × component_id
Evaluate every runtime row whose component_id equals the target component.  
Do not stop after the first runtime row.

Each runtime row must contain:

- a submission identifier field
- `component_id`
- the response text field `response_text`

For all later instructions in this prompt, the selected field must be treated as the canonical `response_text` for that runtime row.

Wrapper handling is applied per runtime row.

#### Evaluation discipline

For each runtime row, evaluate the embedded indicator exactly once.  
For each runtime row, emit one CSV data row.  
Emit rows grouped by runtime row order.  
Emit the CSV header exactly once, before all data rows.

```text
total data row count = number of valid runtime rows
```

##### Runtime Row Coverage Rule

Before writing any output rows, construct the ordered list of valid runtime rows from the runtime dataset.

A valid runtime row is a row whose:

- submission identifier field is present
- `component_id` is present
- the response text field `response_text` is present
- `component_id` equals `[[TARGET_COMPONENT_ID]]`

Do not stop after the first valid runtime row.  
Do not emit output for only a prefix of the runtime dataset.

##### Evaluation Sequence

Layer 1 SBO scoring must follow this exact sequence:

1. Construct a single internal representation of the runtime input dataset.
2. Identify the valid runtime rows whose `component_id = [[TARGET_COMPONENT_ID]]`.
3. For each valid runtime row, treat the field `response_text` as the row’s canonical response text.
4. Apply wrapper-handling rules to each valid runtime row before evaluation.
5. For each valid runtime row:
   - construct a single internal representation of that row’s canonical `response_text`
   - identify candidate supporting fragments for the embedded indicator without inferring unstated meaning
   - evaluate the indicator against the explicit threshold stated in the embedded indicator specification
   - treat partial, weak, implicit, incomplete, vague, or ambiguous matches as `not_present`
   - evaluate using explicit fragment comparison rather than holistic interpretation

##### Indicator Evaluation

For each valid runtime row:

- internally identify whether a supporting textual fragment exists
- evaluate the fragment using the embedded `indicator_definition`
- evaluate the fragment using the embedded `assessment_guidance`
- use the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- assign `evidence_status`
- assign `confidence`
- assign `flags`

##### Evidence Gate Rule

Do **not** assign `present` unless a supporting textual fragment is explicitly present and fully satisfies the embedded indicator threshold.

If no such fragment exists, assign:

```text
not_present
```

If the response contains only partial, weak, implicit, incomplete, vague, or ambiguous evidence, assign:

```text
not_present
```

##### Output Row Count Rule

Before emitting CSV rows, verify that:

```text
number of data rows to be written
=
number of valid runtime rows
```

If counts differ, complete the missing evaluations before emitting output.  
Do not emit partial output.

##### Output Emission Rule

Emit output in this exact structure:

- one CSV header row
- then, for runtime row 1, one data row
- then, for runtime row 2, one data row
- continue until all valid runtime rows are exhausted

#### Evidence interpretation rules

##### Evidence Fragment Output Mode

Default behaviour:

- supporting fragments are identified internally
- fragments are **not printed**
- `evaluation_notes` should normally be empty and emitted as `""`

Optional runtime mode:

```text
FRAGMENT_OUTPUT_MODE = on
```

If enabled, `evaluation_notes` may briefly reference the supporting fragment used to assign the evidence status.

##### Binary Threshold Rule

Presence requires a complete, explicit textual match to the embedded indicator specification.

Do not assign `present` for:

- partial matches
- implied structure
- incomplete structure
- vague mention
- keyword mention without required analytic structure

All such cases must be assigned:

```text
not_present
```

##### Independence Rule

This indicator must be evaluated independently.

Do not use:

- other indicators
- dimension logic
- indicator combinations
- mapping rules
- component expectations

to influence the judgement.

#### Confidence assignment rule

Confidence reflects clarity of the basis for the binary decision, not degree of evidence.

```text
high
the assigned status is clearly supported by explicit textual evidence or by a clear absence of qualifying evidence

medium
the assigned status is determinable, but the boundary is close and should be flagged for review if needed

low
use only when a binary decision is still required but the evidence surface is unusually difficult to parse because of malformed or highly unclear text
```

```text
If evidence_status = not_present because no qualifying fragment exists, assign confidence = high.
If a decision is boundary-close, assign flags = needs_review.
Do not use confidence to introduce partial credit or graded evidence.
```

#### Output schema

Output must be CSV.  
Emit the header row exactly once:

```text
submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
```

In output, `evaluation_notes` refers only to the CSV output field.  
It does not rename or reproduce the manifest `evaluation_notes` field, which serves as embedded evaluator guidance inside the scoring prompt.

Field rules:

- `submission_id` must be copied from the runtime row
- `component_id` must equal `[[TARGET_COMPONENT_ID]]` in every emitted row
- `indicator_id` must equal `[[TARGET_INDICATOR_ID]]` in every emitted row
- `evaluation_notes` must always be enclosed in double quotes
- if `evaluation_notes` is empty, emit `""`
- `confidence` must be one of: `low`, `medium`, `high`
- `flags` must be one of: `none`, `needs_review`
- no additional columns may appear
- no explanatory text may appear before or after the CSV

#### Constraints

Use only:

- the runtime dataset rows
- canonical `response_text`
- the embedded indicator definition
- the embedded assessment guidance
- the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- the embedded evidence scale

Do not use:

- external knowledge
- dimension reasoning
- performance-level reasoning
- assumptions about intended meaning
- inferential reconstruction of missing structure

#### Content rules

Require all of the following:

- one CSV row for the embedded indicator **for each valid runtime row**
- complete coverage of all valid runtime rows in the runtime dataset
- `component_id = [[TARGET_COMPONENT_ID]]` in every emitted row
- `indicator_id = [[TARGET_INDICATOR_ID]]` in every emitted row
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

#### Failure mode handling

If any artefact or parameter is missing, inconsistent, or contradictory:

- produce **no output**
- wait silently for corrected inputs

If the selected manifest row is:

- missing
- duplicated
- missing evaluation fields

the wrapper prompt must **produce no output**.

Produce no output if:

- the runtime dataset contains no valid runtime rows for the target component
- the CSV header cannot be emitted exactly as specified
- complete row coverage cannot be achieved for all valid runtime rows
- any contradiction prevents deterministic evaluation
````

### **insertion tokens you will need in Python**

  

Your single-indicator scaffold needs these tokens in addition to the old shared ones:

```
[[TARGET_INDICATOR_ID]]
[[INDICATOR_ID]]
[[SBO_SHORT_DESCRIPTION]]
[[INDICATOR_DEFINITION]]
[[ASSESSMENT_GUIDANCE]]
[[EMBEDDED_EVALUATOR_GUIDANCE]]
```

### **key structural changes from the bundled version**

- singular throughout: indicator instead of indicators
    
- canonical scoring unit becomes:
    

```
submission_id × component_id × indicator_id
```

-   
    
- the embedded indicator section becomes a **single-row table**
    
- row-count rule becomes:
    

```
number of valid runtime rows
```

- rather than:
    

```
number of valid runtime rows × number of embedded indicators
```

-   
    
- output emission becomes **one data row per valid runtime row**
    
- independence language now refers to avoiding use of **other indicators**
    

  

If you want, I can next give you the exact Python-side insertion mapping and validation rules for this single-indicator version.


======

# NEW VERSION


### **recommendation**

  

Plug the optional embedded decision procedure into the scaffold as a new subsection inside:

  

### **Authoritative scoring materials**

  

That is the cleanest location because it keeps all indicator-specific authoritative material together:

- indicator definition
    
- assessment guidance
    
- embedded evaluator guidance
    
- optional embedded decision procedure
    

  

This also avoids mixing registry-derived content with global runtime instructions.

  

### **revised scaffold with optional embedded decision procedure**


## scaffold with optional embedded decision procedure

````
#### RUN_[[ASSESSMENT_ID]]_[[TARGET_COMPONENT_ID]]_[[TARGET_INDICATOR_ID]]_Layer1_SBO_scoring_prompt_v01

#### Prompt title and restrictions

This prompt performs **Layer 1 SBO scoring** for target component `[[TARGET_COMPONENT_ID]]` and target indicator `[[TARGET_INDICATOR_ID]]`.

It determines the `evidence_status` value for the embedded indicator SBO instance belonging to this component.

This prompt does **not**:

- evaluate dimensions
- evaluate indicator combinations
- apply indicator→dimension mappings
- assign component performance levels
- assign submission scores
- evaluate indicators belonging to other components
- evaluate any indicator other than `[[TARGET_INDICATOR_ID]]`

Layer 1 SBO scoring performs only:

```text
binary indicator presence detection
```

#### Authoritative scoring materials

Assessment identifier:

```text
[[ASSESSMENT_ID]]
```

Target component:

```text
[[TARGET_COMPONENT_ID]]
```

Target indicator:

```text
[[TARGET_INDICATOR_ID]]
```

Canonical scoring unit:

```text
submission_id × component_id × indicator_id
```

Runtime row identifier rule:

- The canonical submission-level identifier field is `[[SUBMISSION_IDENTIFIER_FIELD]]`.
- In output, copy the runtime row value from `[[SUBMISSION_IDENTIFIER_FIELD]]` into the CSV field named `submission_id`.

Evidence rule:

```text
explicit textual evidence only
```

Wrapper-handling rule for response text:

[[WRAPPER_HANDLING_RULE_BULLETS]]

Embedded indicator specification:

| indicator_id | sbo_short_description | indicator_definition | assessment_guidance | embedded evaluator guidance |
|---|---|---|---|---|
| [[INDICATOR_ID]] | [[SBO_SHORT_DESCRIPTION]] | [[INDICATOR_DEFINITION]] | [[ASSESSMENT_GUIDANCE]] | [[EMBEDDED_EVALUATOR_GUIDANCE]] |

Embedded decision procedure for `[[TARGET_INDICATOR_ID]]`:

[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]

Indicator evidence status scale:

| value | meaning |
|---|---|
| `present` | clear, sufficient, explicit textual evidence fully satisfies the indicator definition |
| `not_present` | the indicator is absent or supported only by partial, weak, implicit, incomplete, vague, or ambiguous evidence |

Field rules:

- `evaluation_notes` enclosed in double quotes
- empty notes represented as `""`

Use only:

- the runtime dataset rows
- canonical `response_text`
- the embedded indicator definition
- the embedded assessment guidance
- the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- the embedded decision procedure, if present
- the embedded evidence scale

Do not use:

- external knowledge
- dimension reasoning
- performance-level reasoning
- assumptions about intended meaning
- other indicators
- indicator combinations

Require all of the following:

- one CSV row for the embedded indicator **for each valid runtime row**
- complete coverage of all valid runtime rows in the runtime dataset
- `component_id = [[TARGET_COMPONENT_ID]]` in every emitted row
- `indicator_id = [[TARGET_INDICATOR_ID]]` in every emitted row
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

Produce no output if:

- the runtime dataset contains no valid runtime rows for the target component
- the CSV header cannot be emitted exactly as specified
- complete row coverage cannot be achieved for all valid runtime rows
- any contradiction prevents deterministic evaluation

#### Input format

Runtime input will contain a dataset with one or more runtime rows.  
Each runtime row represents one submission-level evaluation unit:
[[SUBMISSION_IDENTIFIER_FIELD]] × component_id
Evaluate every runtime row whose component_id equals the target component.  
Do not stop after the first runtime row.

Each runtime row must contain:

- a submission identifier field
- `component_id`
- the response text field `response_text`

For all later instructions in this prompt, the selected field must be treated as the canonical `response_text` for that runtime row.

Wrapper handling is applied per runtime row.

#### Evaluation discipline

For each runtime row, evaluate the embedded indicator exactly once.  
For each runtime row, emit one CSV data row.  
Emit rows grouped by runtime row order.  
Emit the CSV header exactly once, before all data rows.

```text
total data row count = number of valid runtime rows
```

##### Runtime Row Coverage Rule

Before writing any output rows, construct the ordered list of valid runtime rows from the runtime dataset.

A valid runtime row is a row whose:

- submission identifier field is present
- `component_id` is present
- the response text field `response_text` is present
- `component_id` equals `[[TARGET_COMPONENT_ID]]`

Do not stop after the first valid runtime row.  
Do not emit output for only a prefix of the runtime dataset.

##### Evaluation Sequence

Layer 1 SBO scoring must follow this exact sequence:

1. Construct a single internal representation of the runtime input dataset.
2. Identify the valid runtime rows whose `component_id = [[TARGET_COMPONENT_ID]]`.
3. For each valid runtime row, treat the field `response_text` as the row’s canonical response text.
4. Apply wrapper-handling rules to each valid runtime row before evaluation.
5. For each valid runtime row:
   - construct a single internal representation of that row’s canonical `response_text`
   - identify candidate supporting fragments for the embedded indicator without inferring unstated meaning
   - if an embedded decision procedure is present, apply it exactly as written
   - evaluate the indicator against the explicit threshold stated in the embedded indicator specification
   - treat partial, weak, implicit, incomplete, vague, or ambiguous matches as `not_present`
   - evaluate using explicit fragment comparison rather than holistic interpretation

##### Indicator Evaluation

For each valid runtime row:

- internally identify whether a supporting textual fragment exists
- evaluate the fragment using the embedded `indicator_definition`
- evaluate the fragment using the embedded `assessment_guidance`
- use the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- if present, apply the embedded decision procedure exactly as written
- assign `evidence_status`
- assign `confidence`
- assign `flags`

##### Evidence Gate Rule

Do **not** assign `present` unless a supporting textual fragment is explicitly present and fully satisfies the embedded indicator threshold.

If no such fragment exists, assign:

```text
not_present
```

If the response contains only partial, weak, implicit, incomplete, vague, or ambiguous evidence, assign:

```text
not_present
```

##### Output Row Count Rule

Before emitting CSV rows, verify that:

```text
number of data rows to be written
=
number of valid runtime rows
```

If counts differ, complete the missing evaluations before emitting output.  
Do not emit partial output.

##### Output Emission Rule

Emit output in this exact structure:

- one CSV header row
- then, for runtime row 1, one data row
- then, for runtime row 2, one data row
- continue until all valid runtime rows are exhausted

#### Evidence interpretation rules

##### Evidence Fragment Output Mode

Default behaviour:

- supporting fragments are identified internally
- fragments are **not printed**
- `evaluation_notes` should normally be empty and emitted as `""`

Optional runtime mode:

```text
FRAGMENT_OUTPUT_MODE = on
```

If enabled, `evaluation_notes` may briefly reference the supporting fragment used to assign the evidence status.

##### Binary Threshold Rule

Presence requires a complete, explicit textual match to the embedded indicator specification.

Do not assign `present` for:

- partial matches
- implied structure
- incomplete structure
- vague mention
- keyword mention without required analytic structure

All such cases must be assigned:

```text
not_present
```

##### Independence Rule

This indicator must be evaluated independently.

Do not use:

- other indicators
- dimension logic
- indicator combinations
- mapping rules
- component expectations

to influence the judgement.

#### Confidence assignment rule

Confidence reflects clarity of the basis for the binary decision, not degree of evidence.

```text
high
the assigned status is clearly supported by explicit textual evidence or by a clear absence of qualifying evidence

medium
the assigned status is determinable, but the boundary is close and should be flagged for review if needed

low
use only when a binary decision is still required but the evidence surface is unusually difficult to parse because of malformed or highly unclear text
```

```text
If evidence_status = not_present because no qualifying fragment exists, assign confidence = high.
If a decision is boundary-close, assign flags = needs_review.
Do not use confidence to introduce partial credit or graded evidence.
```

#### Output schema

Output must be CSV.  
Emit the header row exactly once:

```text
submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
```

In output, `evaluation_notes` refers only to the CSV output field.  
It does not rename or reproduce the manifest `evaluation_notes` field, which serves as embedded evaluator guidance inside the scoring prompt.

Field rules:

- `submission_id` must be copied from the runtime row
- `component_id` must equal `[[TARGET_COMPONENT_ID]]` in every emitted row
- `indicator_id` must equal `[[TARGET_INDICATOR_ID]]` in every emitted row
- `evaluation_notes` must always be enclosed in double quotes
- if `evaluation_notes` is empty, emit `""`
- `confidence` must be one of: `low`, `medium`, `high`
- `flags` must be one of: `none`, `needs_review`
- no additional columns may appear
- no explanatory text may appear before or after the CSV

#### Constraints

Use only:

- the runtime dataset rows
- canonical `response_text`
- the embedded indicator definition
- the embedded assessment guidance
- the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- the embedded decision procedure, if present
- the embedded evidence scale

Do not use:

- external knowledge
- dimension reasoning
- performance-level reasoning
- assumptions about intended meaning
- inferential reconstruction of missing structure

#### Content rules

Require all of the following:

- one CSV row for the embedded indicator **for each valid runtime row**
- complete coverage of all valid runtime rows in the runtime dataset
- `component_id = [[TARGET_COMPONENT_ID]]` in every emitted row
- `indicator_id = [[TARGET_INDICATOR_ID]]` in every emitted row
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

#### Failure mode handling

If any artefact or parameter is missing, inconsistent, or contradictory:

- produce **no output**
- wait silently for corrected inputs

If the selected manifest row is:

- missing
- duplicated
- missing evaluation fields

the wrapper prompt must **produce no output**.

Produce no output if:

- the runtime dataset contains no valid runtime rows for the target component
- the CSV header cannot be emitted exactly as specified
- complete row coverage cannot be achieved for all valid runtime rows
- any contradiction prevents deterministic evaluation
````

### **token list**

  

Keep the existing single-indicator tokens and add one optional decision-procedure token.

```
[[ASSESSMENT_ID]]
[[TARGET_COMPONENT_ID]]
[[TARGET_INDICATOR_ID]]
[[SUBMISSION_IDENTIFIER_FIELD]]
[[WRAPPER_HANDLING_RULE_BULLETS]]

[[INDICATOR_ID]]
[[SBO_SHORT_DESCRIPTION]]
[[INDICATOR_DEFINITION]]
[[ASSESSMENT_GUIDANCE]]
[[EMBEDDED_EVALUATOR_GUIDANCE]]

[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]
```

### **recommended rendering rule for the optional block**

  

Use deterministic fallback text rather than making the section disappear. That keeps the scaffold canonical.

  

#### **when a decision procedure exists**

Render [[EMBEDDED_DECISION_PROCEDURE_BLOCK]] as a verbatim bullet list copied from the registry, for example:

```
- Step 1: locate candidate mechanism phrases following `through`, `via`, or `using`.
- Step 2: reject generic phrases such as `system` or `process` unless qualified.
- Step 3: assign `present` only if a concrete operative mechanism is explicitly named.
```

#### **when no decision procedure exists**

Render [[EMBEDDED_DECISION_PROCEDURE_BLOCK]] as:

```
- No embedded decision procedure is provided for this indicator.
```

### **why this is the right insertion point**

  

This keeps the decision procedure:

- authoritative and indicator-specific
    
- visible before evaluation begins
    
- separate from global runtime rules
    
- easy to render deterministically from Python
    

  

If you want, I can next give you a compact insertion-mapping spec for the Python builder, including exact fallback behaviour for [[EMBEDDED_DECISION_PROCEDURE_BLOCK]].