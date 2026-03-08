# .
```
BEGIN GENERATION
```


three inputs
`Rubric_SpecificationGuide_v01`
`<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md`
`Rubric_Template: 5.4 Layer 1 SBO Instances`
# . 
````
## Wrapper Prompt — Generate Layer 1 Indicator Evaluation Specification (Stage 1.1.5)

### Prompt title and purpose

This wrapper prompt generates the **Layer 1 Indicator Evaluation Specification** for an assessment rubric.

The generated output corresponds to:

```text
Rubric Template: 6.1 Layer 1 SBO Value Derivation (Draft)
```

This stage converts the **Layer 1 indicator registry** into an **operational evaluation specification** describing how each indicator is detected in student responses.

The purpose is to define **how indicator evidence is derived from the Layer 1 Assessment Artefact**.

This prompt does **not modify the indicator registry** and does **not perform scoring**.

---

### Required input artefacts

The following artefacts must be supplied verbatim and delimited using:

```text
===
<content>
===
```

Artefacts must appear in the following order:

```text
===
Rubric_SpecificationGuide_v01
===
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
===
Rubric_Template: 5.4 Layer 1 SBO Instances
===
```

If any artefact is missing, malformed, or inconsistent, the prompt must produce **no output**.

---

### Objective

Using the **indicator SBO instances defined in Section 5.4**, generate the **evaluation specification used to detect those indicators in student responses**.

Each indicator must receive a corresponding **evaluation specification block** defining how its evidence is identified in response text.

The specification must be grounded in:

- analytic sub-spaces
- contrastive response observations
- candidate indicator signals
- candidate indicator sets

from the analytic brief.

The generator must **not introduce analytic concepts that do not appear in the analytic brief**.

---

### Layer 1 scoring context

Indicator evaluation operates on the **Layer 1 Assessment Artefact**:

```text
AA = submission_id × component_id
```

The evidence surface available to the evaluator is:

```text
response_text
```

Indicators are evaluated using the **indicator evidence scale**:

```text
evidence
partial_evidence
little_to_no_evidence
```

Section 6.1 therefore defines **how evaluators should interpret response text when assigning indicator scores**.

---

### Evaluation specification structure

For each indicator SBO instance, generate an evaluation specification row containing the following fields:

```text
sbo_identifier  
sbo_short_description  
indicator_definition  
assessment_guidance  
evaluation_notes
```

These fields provide the operational interpretation used during scoring.

---

### Field definitions

#### indicator_definition

A concise conceptual description of the analytic signal being detected.

The definition should:

- restate the meaning of the indicator
- describe the analytic concept being detected
- avoid referencing performance levels
- avoid referencing scoring thresholds

The definition should be **conceptual**, not procedural.

Example format:

```text
Detects statements that attribute responsibility across multiple actors such as individuals, teams, institutions, or tools.
```

---

#### assessment_guidance

Operational guidance describing **how the signal may appear in response text**.

This section should:

- describe the kinds of language that express the signal
- reference typical phrasing patterns where appropriate
- remain general rather than enumerating exhaustive keyword lists
- help the evaluator recognise the signal in varied wording

Example format:

```text
Look for explicit language indicating that responsibility is shared or distributed across multiple actors, such as individuals, teams, institutions, or technological systems.
```

---

#### evaluation_notes

Clarifications, exclusions, or edge-case guidance.

These notes may include:

- distinctions between similar indicators
- cases where evidence should **not** be assigned
- reminders about interpretive boundaries

Example format:

```text
Do not assign evidence when the response only mentions collaboration without attributing responsibility across actors.
```

---

### Authoring rules

Evaluation specifications must:

- align with the analytic signals defined in the indicator registry
- remain grounded in the analytic brief
- avoid embedding scoring thresholds
- avoid referencing performance levels
- avoid introducing new analytic categories
- avoid rewriting or modifying the indicator descriptions from Section 5.4

Descriptions must remain **clear, concise, and operationally interpretable**.

---

### Evaluation specification generation procedure

The generator must perform the following steps:

1. Read the **Layer 1 SBO instance registry**.
2. Identify each indicator SBO instance.
3. Locate the corresponding analytic signals in the analytic brief.
4. Translate those signals into an evaluation specification.
5. Produce one evaluation block per indicator.

Each evaluation block must correspond exactly to one indicator instance.

No indicators may be omitted.

---

### Output format

The output must be emitted as a **single fenced Markdown block**.

The **outer fence must use four backticks**.

Inside that fenced block, emit exactly:

```text
#### 6.1 Layer 1 SBO Value Derivation (Draft)
```

followed by the evaluation specification blocks.

Evaluation specifications must be presented as Markdown tables whenever possible.

Indicators must be grouped by `component_id`.

For each component, generate a Markdown table with the following columns:

| sbo_identifier | sbo_short_description | indicator_definition | assessment_guidance | evaluation_notes |
|---|---|---|---|---|

Each row of the table must correspond to one indicator SBO instance.

Indicators must appear in increasing `indicator_id` order within each component table.


Tabular output is mandatory when multiple indicators are present for a component.

Free-form blocks must not be used unless a table is structurally impossible.

---

### Output restrictions

The generated output must contain **only a single fenced Markdown block**.

Inside that block it must contain:

```text
#### 6.1 Layer 1 SBO Value Derivation (Draft)
```

followed by the component tables containing the evaluation specifications.

No commentary, explanation, or additional text may appear outside the block.
===
````