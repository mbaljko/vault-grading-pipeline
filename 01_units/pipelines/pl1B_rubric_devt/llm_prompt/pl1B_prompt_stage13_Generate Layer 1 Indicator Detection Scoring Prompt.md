# .
```
BEGIN GENERATION
```


these inputs
```
===
PARAM_TARGET_COMPONENT_ID = SectionBResponse
===
<PPP_AssignmentPayloadSpec_v01 contents>
===
<Layer1_ScoringManifest_PPP_v01 contents>
===
```

# .  
````
## Wrapper Prompt — Generate Layer 1 Indicator Detection Scoring Prompt (Stage 1.3)

Wrapper prompt: Generate a tightly bounded **Layer 1 SBO scoring prompt** for **indicator evidence detection** using the **Layer 1 scoring manifest** under the **Rubric Template architecture**.

This wrapper prompt **generates a scoring prompt**.  
It **does not evaluate student work**.

The generated scoring prompt performs **Layer 1 SBO scoring**, which determines `evidence_status` values for the indicator SBO instances belonging to one target component.

### Target Component Parameter (Required)

The wrapper prompt requires the user to specify the component whose Layer 1 indicators will be scored.

```text
PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>
```

Example:

```text
PARAM_TARGET_COMPONENT_ID = SectionBResponse
```

This parameter determines which rows from the `Layer1_ScoringManifest` will be embedded in the generated scoring prompt.

### Required Input Artefacts

All required inputs must be supplied **verbatim** and separated using the delimiter:

```text
===
```

The wrapper prompt expects the following inputs in sequence:

```text
PARAM_TARGET_COMPONENT_ID
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION>
```

The parameter block must appear in the form:

```text
===
PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>
===
```

The remaining artefacts must appear exactly as produced by their upstream pipelines and must not be modified.

If any required artefact or parameter is missing, malformed, or inconsistent, the wrapper prompt must **produce no output**.

### Input Artefact Order (Mandatory)

Artefacts must appear **exactly in the following order**, separated by the delimiter `===`.

No additional delimiters or numbering markers may appear.

```text
===
PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>
===

<ASSESSMENT_ID>_AssignmentPayloadSpec_v01 contents
===

Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION> contents
===
```

After the final delimiter block, the user must provide:

```text
BEGIN GENERATION
```

If `BEGIN GENERATION` is absent, the wrapper prompt must **produce no output**.

### Example Invocation

```text
===
PARAM_TARGET_COMPONENT_ID = SectionBResponse
===
<PPP_AssignmentPayloadSpec_v01 contents>
===
<Layer1_ScoringManifest_PPP_v01 contents>
===
BEGIN GENERATION
```

If the artefacts appear in a different order or if the delimiter structure is violated, the wrapper prompt must **produce no output**.

### Purpose

Generate a reusable **Layer 1 SBO scoring prompt** that performs **indicator evidence detection**.

The generated prompt must:

- evaluate indicator evidence using the `Layer1_ScoringManifest`
- embed the indicator evaluation specification contained in the manifest
- assign an `evidence_status` value for each indicator SBO instance belonging to the target component
- record indicator-level diagnostic information
- remain fully executable without requiring the rubric document at scoring runtime

The generated prompt must **not**:

- evaluate dimensions
- evaluate indicator combinations
- apply indicator→dimension mappings
- assign component performance levels
- assign submission scores
- evaluate indicators belonging to other components

Layer 1 SBO scoring performs only:

```text
indicator evidence detection
```

Outputs produced by the Layer 1 scoring prompt will later be consumed by:

```text
Layer 2 — Dimension Evidence Derivation
Layer 3 — Component Performance Mapping
Layer 4 — Submission Score Derivation
```

### Task Classification

This wrapper prompt performs:

- prompt synthesis
- manifest constraint propagation
- Layer 1 scoring prompt specification

This wrapper prompt does **not** perform:

- grading
- submission scoring
- rubric modification
- indicator invention
- rule invention
- pedagogical explanation

### Authoritative Inputs

The model may rely **only** on the following artefacts supplied verbatim.

#### Input Artefact
`<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`

The wrapper must extract:

```text
assessment_id
submission_id
component_id
response_text
```

Canonical scoring unit:

```text
submission_id × component_id
```

Evidence rule:

```text
explicit textual evidence only
```

If wrapper-handling rules exist for `response_text`, they must be embedded in the generated scoring prompt.

#### Input Artefact
`Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION>`

The wrapper must extract:

```text
component_id
sbo_identifier
indicator_id
sbo_short_description
indicator_definition
assessment_guidance
evaluation_notes
```

This manifest defines both:

```text
the registry of Layer 1 indicators
the evaluation specification used to detect them
```

### Manifest Filtering Rule

Before generating the scoring prompt, the wrapper must execute:

```text
filter Layer1_ScoringManifest
where component_id = PARAM_TARGET_COMPONENT_ID
```

Validation rules:

- if the filtered table is empty → **produce no output**
- if duplicate `indicator_id` values appear → **produce no output**

Only filtered rows may be embedded in the generated scoring prompt.

### Indicator Evidence Status Scale

The generated scoring prompt must embed this scale.

| value | meaning |
|---|---|
| `evidence` | explicit textual evidence clearly satisfies the indicator definition |
| `partial_evidence` | explicit textual signal relevant to the indicator exists but is incomplete |
| `little_to_no_evidence` | no interpretable explicit textual signal supporting the indicator is present |

Evidence must rely strictly on **explicit response language**.

### Output Requirements

Allowed output fields:

```text
submission_id
component_id
indicator_id
evidence_status
evaluation_notes
confidence
flags
```

Allowed values:

```text
confidence ∈ {low, medium, high}
flags ∈ {none, needs_review}
```

#### Field Formatting Rules

The scoring prompt must require:

- `evaluation_notes` enclosed in double quotes
- empty notes represented as `""`

#### CSV Header Requirement

Output must begin with the header row:

```text
submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
```

The header appears **exactly once**.

### Wrapper Execution Discipline

#### Phase 1 — Artefact ingestion

The wrapper reads artefacts silently.

If

```text
BEGIN GENERATION
```

is absent, produce **no output**.

#### Phase 2 — Prompt generation

When

```text
BEGIN GENERATION
```

appears, generate the scoring prompt artefact.

### Output Artefact

Generate exactly one artefact:

```text
RUN_<ASSESSMENT_ID>_<PARAM_TARGET_COMPONENT_ID>_Layer1_SBO_scoring_prompt_v01
```

The artefact must:

- reference `PARAM_TARGET_COMPONENT_ID`
- embed the filtered indicator rows
- embed the evaluation specification
- assume the canonical payload structure

### Prompt Template Lock Requirement

The generated scoring prompt must follow a **fixed canonical template**.

The wrapper must **not paraphrase, compress, rename, reorder, or restyle** any of the required semantic instructions listed below.

The generated scoring prompt must use the exact section order specified in this wrapper.

The generated scoring prompt must use **batch-safe runtime language** and must never use any of the following phrases:

```text
one runtime row
evaluate only the supplied runtime row
one evaluation unit
then emit exactly 8 data rows
```

The generated scoring prompt must instead describe runtime input using the exact concepts:

```text
runtime input dataset
runtime rows
for each runtime row
for each runtime row, evaluate all embedded indicators
```

### Generated Scoring Prompt Structure

The scoring prompt must appear in **one fenced Markdown block** using an outer fence of four backticks.

Sections must appear in this exact order:

```text
Prompt title and restrictions
Authoritative scoring materials
Input format
Evaluation discipline
Evidence interpretation rules
Confidence assignment rule
Output schema
Constraints
Content rules
Failure mode handling
```

### Required Canonical Runtime Semantics

The generated scoring prompt must state all of the following explicitly and without paraphrase drift.

#### Canonical input semantics

The prompt must state:

```text
Runtime input will contain a dataset with one or more runtime rows.
Each runtime row is one submission_id × component_id evaluation unit.
Evaluate every runtime row whose component_id equals the target component.
Do not stop after the first runtime row.
```

If the assignment payload specification implies wrapper handling, the prompt must state that wrapper handling is applied **per runtime row**.

#### Canonical batch-output semantics

The prompt must state:

```text
For each runtime row, evaluate all embedded indicator_id values exactly once.
For each runtime row, emit one CSV data row per embedded indicator_id.
Emit rows grouped by runtime row.
Within each runtime row group, emit indicator_id values in embedded prompt order.
Emit the CSV header exactly once, before all data rows.
```

The prompt must **not** state or imply that the total output row count is always equal only to the number of indicators.

Instead it must state:

```text
total data row count = number of valid runtime rows × number of embedded indicators
```

### Evaluation Discipline

The generated scoring prompt must include all of the following requirements.

#### Indicator Coverage Rule

Before writing any output rows, construct the ordered list of `indicator_id` values embedded in the prompt.

Ensure that:

- each embedded `indicator_id` is evaluated exactly once **per runtime row**
- indicators are processed in the order embedded in the prompt
- every valid runtime row receives a complete indicator evaluation set

#### Runtime Row Coverage Rule

Before writing any output rows, construct the ordered list of valid runtime rows from the runtime dataset.

A valid runtime row is a row whose:

- required fields are present
- `component_id` equals `PARAM_TARGET_COMPONENT_ID`

Do not stop after the first valid runtime row.

Do not emit output for only a prefix of the runtime dataset.

#### Evaluation Sequence

Layer 1 SBO scoring must follow this exact sequence:

1. Construct a single internal representation of the runtime input dataset.
2. Identify the valid runtime rows whose `component_id = PARAM_TARGET_COMPONENT_ID`.
3. Apply any wrapper-handling rules to each valid runtime row before evaluation.
4. Construct the ordered `indicator_id` list embedded in the prompt.
5. For each valid runtime row:
   - construct a single internal representation of that row’s `response_text`
   - scan the response once and identify potentially relevant textual fragments
   - store those fragments in an internal evidence index
   - perform one internal analytic signal pass over the indexed fragments
   - organise the indexed evidence into candidate signal groupings relevant to the target component
   - evaluate all embedded `indicator_id` values using the evidence index and signal groupings rather than rescanning the full response text

#### Indicator Evaluation

For each valid runtime row and for each embedded `indicator_id` in prompt order:

- internally identify whether a relevant textual fragment exists
- evaluate the fragment using `indicator_definition` and `assessment_guidance`
- assign `evidence_status`
- assign `confidence`
- assign `flags`

#### Evidence Gate Rule

Do **not** assign `evidence` or `partial_evidence` without internally identifying a supporting textual fragment.

If no relevant fragment exists, assign:

```text
little_to_no_evidence
```

#### Output Row Count Rule

Before emitting CSV rows, verify that:

```text
number of data rows to be written
=
number of valid runtime rows × number of embedded indicators
```

If counts differ, complete the missing evaluations before emitting output.

Do not emit partial output.

#### Output Emission Rule

Emit output in this exact structure:

- one CSV header row
- then, for runtime row 1, one data row per embedded `indicator_id` in prompt order
- then, for runtime row 2, one data row per embedded `indicator_id` in prompt order
- continue until all valid runtime rows are exhausted

### Evidence Interpretation Rules

The generated scoring prompt must include all of the following.

#### Evidence Fragment Output Mode

Default behaviour:

- supporting fragments are identified internally
- fragments are **not printed**

Optional runtime mode:

```text
FRAGMENT_OUTPUT_MODE = on
```

If enabled, `evaluation_notes` may briefly reference the supporting fragment.

#### Partial Evidence Preference Rule

If explicit language partially satisfies an indicator definition but does not fully satisfy it, assign:

```text
partial_evidence
```

Do not collapse weak but relevant explicit evidence into `little_to_no_evidence`.

#### Independence Rule

Indicators must be evaluated independently.

Do not use:

- other indicators
- dimension logic
- indicator combinations
- mapping rules
- component expectations

to influence the judgement.

### Confidence Assignment Rule

The generated scoring prompt must state:

```text
Confidence reflects clarity of textual evidence, not probability.
```

It must also embed this interpretation exactly:

```text
high
clear explicit language supports the assigned status

medium
explicit language present but incomplete or ambiguous

low
weak or uncertain textual signal
```

It must also state:

```text
If evidence_status = little_to_no_evidence and no fragment exists, assign confidence = high.
If you are uncertain and cannot identify sufficient explicit support for evidence or partial_evidence, assign evidence_status = little_to_no_evidence and flags = needs_review.
```

### Output Schema

The generated scoring prompt must state:

```text
Output must be CSV.
Emit the header row exactly once:
submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
```

It must also state all of the following:

- `submission_id` must be copied from the runtime row
- `component_id` must equal `PARAM_TARGET_COMPONENT_ID` in every emitted row
- `indicator_id` values must appear in embedded prompt order within each runtime row group
- `evaluation_notes` must always be enclosed in double quotes
- if `evaluation_notes` is empty, emit `""`
- no additional columns may appear
- no explanatory text may appear before or after the CSV

### Constraints

The generated scoring prompt must require the evaluator to use only:

- the runtime dataset rows
- canonical `response_text`
- the embedded indicator definitions
- the embedded assessment guidance
- the embedded evaluation notes
- the embedded evidence scale

The evaluator must not use:

- external knowledge
- dimension reasoning
- performance-level reasoning
- assumptions about intended meaning

### Content Rules

The generated scoring prompt must require:

- one CSV row per embedded indicator **for each valid runtime row**
- complete coverage of all valid runtime rows in the runtime dataset
- `component_id = PARAM_TARGET_COMPONENT_ID` in every emitted row
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

### Failure Mode Handling

If any artefact or parameter is missing, inconsistent, or contradictory:

- produce **no output**
- wait silently for corrected inputs

If the filtered manifest contains:

- no rows
- duplicate `indicator_id`
- missing evaluation fields

the wrapper prompt must **produce no output**.

The generated scoring prompt must also state:

```text
Produce no output if the runtime dataset contains no valid runtime rows for the target component.
Produce no output if the CSV header cannot be emitted exactly as specified.
Produce no output if complete row coverage cannot be achieved for all valid runtime rows.
```
===
PARAM_TARGET_COMPONENT_ID = SectionBResponse
````