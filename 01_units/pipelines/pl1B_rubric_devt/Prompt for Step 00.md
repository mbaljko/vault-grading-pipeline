
# .
```
BEGIN GENERATION
```

# .
````
## Wrapper Prompt — Generate `CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step00_CalibrationPayloadFormat_v01`

## Purpose

This wrapper prompt generates the artefact:

```
CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step00_CalibrationPayloadFormat_v01
```

The artefact defines the **canonical payload structure used during calibration runs** for a specific component of an assessment.

The generated document establishes the **execution contract** between:

- the calibration dataset produced from the canonical population, and  
- the calibration scoring prompts used to evaluate rubric **dimensions** belonging to the component.

The wrapper prompt derives all structural information from the authoritative input:

```
<ASSESSMENT_ID>_Step00_AssignmentPayloadSpec_v01
```

The user must then specify:

```
component_id = <value from AssignmentPayloadSpec>
```

The generated payload format must **exactly match the structure defined in the assignment payload specification**.

This wrapper prompt generates documentation only.  
It does **not** generate calibration datasets or scoring prompts.

---

## Task Classification

This wrapper prompt performs:

- payload schema extraction
- component-level evidence surface specification
- calibration execution contract definition

This wrapper prompt does **not** perform:

- rubric construction
- dimension definition
- indicator generation
- boundary rule definition
- scoring or grading.

---

## Authoritative Inputs (Required)

The model may rely **only** on the following inputs, supplied verbatim by the user and delimited by `===`.

### Input 1 — Assignment Payload Specification

```
<ASSESSMENT_ID>_Step00_AssignmentPayloadSpec_v01
```

This document defines:

- the assessment identity
- canonical identifier fields
- canonical response fields
- the set of valid `component_id` values
- wrapper handling rules
- structural dataset invariants.

The wrapper prompt must treat this document as **normative**.

All payload fields must be derived from this specification.

---

### Input 2 — Target Component

The user must provide:

```
component_id = <value from AssignmentPayloadSpec>
```

The component must exist in the authoritative component list defined in the assignment payload specification.

Example:

```
component_id = SectionA
```

---

## Generation Rules

The generated artefact must:

- reference the selected `component_id`
- inherit identifier and evidence field definitions from the assignment payload specification
- preserve canonical field names
- preserve wrapper handling rules
- preserve dataset constraints.

The wrapper prompt must **not invent additional payload fields**.

---

## Stage Discipline

### Stage 1 — Input

The user supplies the authoritative inputs between `===` delimiters.

The model reads silently.

No output is produced.

### Stage 2 — Execution

The model generates output **only after the command**:

```
BEGIN GENERATION
```

Silence is the correct behaviour until this command appears.

---

## Output Artefact Requirements

The model must generate **exactly one artefact**.

Title:

```
CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step00_CalibrationPayloadFormat_v01
```

The artefact must:

- describe the canonical calibration payload structure
- define the calibration scoring unit
- define the payload fields
- define wrapper handling rules
- define evidence rules
- define dataset constraints
- include an example payload.

The document must assume that **multiple rubric dimensions will evaluate the same payload structure**.

---

## Output Structure (Strict)

The generated document must contain the following sections **in this order**.

### Purpose

Explain that the document defines the canonical payload structure used during calibration runs for the specified component.

Describe the role of the payload format as the execution contract between the calibration dataset and calibration scoring prompts.

---

### Calibration Evidence Surface

State:

```
component_id = <value>
```

Explain that each calibration item represents a participant response to this component.

Clarify that all rubric dimensions associated with the component evaluate the same response text.

---

### Calibration Scoring Unit

Define the scoring unit:

```
participant_id × component_id
```

Explain that dimensions applied during calibration evaluate the same response independently.

---

### Payload Fields

List each canonical payload field inherited from the assignment payload specification.

For each field:

- field name
- field type
- field description
- constraints
- example value

The wrapper prompt must reproduce the identifier field and response field exactly as defined in the assignment payload specification.

---

### Independence Rule

State that calibration items must be evaluated independently.

Calibration prompts must not:

- compare participants
- infer context from dataset order
- use neighbouring responses as evidence.

---

### Evidence Rule

State that evidence must be derived strictly from explicit textual content within the response field.

External inference is prohibited.

---

### Dataset Constraints

Specify dataset requirements inherited from the assignment payload specification.

Constraints typically include:

- required fields
- encoding
- wrapper handling rules
- prohibition of scoring annotations.

---

### Example Calibration Payload

Provide an example dataset fragment demonstrating the payload format.

Examples must contain only the canonical fields.

Wrapper artefacts may be illustrated but must be declared ignorable.

---

### Normative Status

State that the payload format defines the authoritative calibration input structure for the specified component.

List example calibration scoring prompts that will consume this payload.

Example:

```
CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step05_provisional_scoring_prompt_v01
```

Explain that deviation from the defined payload structure invalidates calibration runs.

---

## Content Rules

The model must:

- use only the assignment payload specification and provided component_id
- preserve canonical field names
- preserve structural terminology.

The model must not:

- introduce new fields
- introduce rubric terminology
- modify the assignment payload schema.

---

## Failure Handling

If:

- the assignment payload specification is missing
- the provided component_id does not exist in the specification

the model must produce **no output** and wait for corrected inputs.

===
````
