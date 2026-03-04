
# .
```
BEGIN GENERATION
```


append at the end
\===
component_id = \<value from AssignmentPayloadSpec\>
\===
contents of `<ASSESSMENT_ID>_Step00_AssignmentPayloadSpec_v01`

# .
````
## Wrapper Prompt — Generate `CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step00_CalibrationPayloadFormat_v01`

## Purpose

This wrapper prompt generates the artefact:

```
CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step00_CalibrationPayloadFormat_v01
```

The artefact defines the canonical payload structure used during calibration runs for a specific component of an assessment.

The generated document establishes the execution contract between:

- the calibration dataset produced from the canonical population
- the calibration scoring prompts used to evaluate rubric dimensions belonging to the component

The wrapper prompt derives all structural information from the authoritative input:

```
<ASSESSMENT_ID>_Step00_AssignmentPayloadSpec_v01
```

The user supplies the `component_id` first and then appends the assignment payload specification.

This wrapper prompt generates documentation only.  
It does not generate calibration datasets or scoring prompts.

## Task Classification

This wrapper prompt performs:

- payload schema extraction
- component-level evidence surface specification
- calibration execution contract definition

This wrapper prompt does not perform:

- rubric construction
- dimension definition
- indicator generation
- boundary rule definition
- scoring or grading

## Authoritative Inputs (Required)

The model may rely only on the following inputs, supplied verbatim by the user and delimited by `===`.

### Input 1 — Target Component

The user must provide:

```
component_id = <value from AssignmentPayloadSpec>
```

Example:

```
component_id = SectionA
```

The component must exist in the authoritative component list defined in the assignment payload specification.

### Input 2 — Assignment Payload Specification

The user must append the full contents of:

```
<ASSESSMENT_ID>_Step00_AssignmentPayloadSpec_v01
```

This document defines:

- the assessment identity
- canonical identifier fields
- canonical response fields
- the set of valid `component_id` values
- wrapper handling rules
- structural dataset invariants

The wrapper prompt must treat this document as normative.

All payload fields must be derived from this specification.

## Generation Rules

The generated artefact must:

- reference the selected `component_id`
- inherit identifier and evidence field definitions from the assignment payload specification
- preserve canonical field names
- preserve wrapper handling rules
- preserve dataset constraints

The wrapper prompt must not invent additional payload fields.

## Stage Discipline

### Stage 1 — Input

The user supplies the authoritative inputs between `===` delimiters.

Input order must be:

```
===
component_id = <value>
===

===
contents of <ASSESSMENT_ID>_Step00_AssignmentPayloadSpec_v01
===
```

The model reads silently.

No output is produced.

### Stage 2 — Execution

The model generates output only after the command:

```
BEGIN GENERATION
```

Silence is the correct behaviour until this command appears.

## Output Artefact Requirements

The model must generate exactly one artefact.

The artefact must be emitted inside a fenced Markdown block.

If the generated artefact contains fenced code blocks, the outer fence must use four backticks:

```
===
component_id = XX
===
````
