
# .
```
BEGIN GENERATION
```

# .
`````
## CAL_PPP_SectionA_Step00_CalibrationPayloadFormat_v01

## Purpose

Define the canonical payload structure used during calibration runs for component `SectionA`.

This artefact specifies the exact input structure that calibration scoring prompts will receive when evaluating dimensions associated with this component.

The payload format establishes the execution contract between:

- the calibration dataset
- calibration scoring prompts generated for the component’s dimensions

All calibration scoring prompts for dimensions belonging to `SectionA` must assume this payload structure exactly.

## Calibration Evidence Surface

Calibration operates over responses to the component:

```
component_id = SectionA
```

Each payload item represents the text submitted by a participant for this component.

Dimensions such as `A1`, `A2`, `A3`, etc., will be evaluated against the same `response_text`.

## Calibration Scoring Unit

Each calibration item represents one participant response to the component.

Calibration scoring unit:

```
participant_id × component_id
```

Each dimension applied during calibration evaluates the same response independently.

## Payload Fields

Each calibration item must contain exactly the following fields.

### participant_id

Type: string or integer

Description:

Unique identifier for the participant whose response appears in the calibration dataset.

Requirements:

- must be unique within the dataset
- must remain stable across calibration runs
- must not encode scoring information
- must not contain personally identifiable information unless explicitly permitted by the data governance policy

Example:

```
participant_id: P017
```

### response_text

Type: UTF-8 text string

Description:

The participant-authored response corresponding to component `SectionA`.

Requirements:

- must contain the original participant-authored text
- must not include rubric definitions
- must not include scoring annotations
- must not include additional metadata fields

Permitted wrapper artefacts:

- dataset boundary markers such as `+++`
- header lines such as `participant_id=<value>`

These wrapper artefacts must be ignored during scoring.

Example:

```
participant_id=P017
+++
I think the responsibility lies primarily with the engineering team because they designed the algorithm and understand how the data was collected...
+++
```

## Independence Rule

Each calibration item must be evaluated independently.

Scoring prompts must not:

- compare responses across participants
- infer context from neighbouring rows
- assume dataset ordering carries meaning

Only the `response_text` for that participant may be used as evidence.

## Evidence Rule

Evidence must be derived strictly from explicit textual content within `response_text`.

Calibration scoring prompts must not:

- infer unstated reasoning
- assume intent beyond the text
- incorporate external knowledge

## Dataset Constraints

The calibration dataset must satisfy the following constraints:

- all rows must include `participant_id`
- all rows must include `response_text`
- no additional fields are permitted
- encoding must be UTF-8
- whitespace normalization is permitted but content must not be altered

## Example Calibration Payload

Example dataset fragment:

```
participant_id=P012
+++
The engineers should be responsible for identifying bias in the dataset because they built the model and understand its assumptions. However, the company leadership also shares responsibility because they decide whether the system is deployed.
+++

participant_id=P013
+++
Responsibility should not rest solely with the engineers. While they create the system, regulators and company leadership must ensure safeguards exist before deployment.
+++
```

## Normative Status

This payload format defines the authoritative calibration input structure for all calibration scoring prompts associated with component:

```
SectionA
```

Calibration scoring prompts for dimensions such as:

```
CAL_PPP_A1_Step05_provisional_scoring_prompt_v01
CAL_PPP_A2_Step05_provisional_scoring_prompt_v01
CAL_PPP_A3_Step05_provisional_scoring_prompt_v01
```

must assume this payload structure exactly.

Deviation from this format invalidates the calibration run.

````
