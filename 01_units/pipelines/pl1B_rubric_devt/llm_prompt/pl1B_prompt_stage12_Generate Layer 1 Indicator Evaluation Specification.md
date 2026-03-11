---


---



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
## Wrapper Prompt — Generate Layer 1 Indicator Evaluation Specification (Stage 1.2)

### Prompt title and purpose

This wrapper prompt generates the **Layer 1 Indicator Evaluation Specification** for an assessment rubric.

The generated output corresponds to:

Rubric Template: 6.1 Layer 1 SBO Value Derivation (Draft)

This stage converts the **Layer 1 indicator registry** into an **operational evaluation specification** describing how each indicator is detected in student responses.

This prompt does **not modify the indicator registry** and does **not perform scoring**.

---

## Required input artefacts

All artefacts must be supplied verbatim and delimited using:

===
<content>
===

Artefacts must appear in the following order:

===
Rubric_SpecificationGuide_v01
===
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
===
Rubric_Template: 5.4 Layer 1 SBO Instances
===

If any artefact is missing, malformed, or inconsistent, the prompt must produce **no output**.

---

# Output schema (authoritative)

The evaluation specification must be produced as **structured tabular data**.

Each indicator SBO instance corresponds to **exactly one row** in the evaluation specification table.

The table schema is:

| sbo_identifier | sbo_short_description | indicator_definition | assessment_guidance | evaluation_notes |
|---|---|---|---|---|

Column meanings:

| column | purpose |
|---|---|
| sbo_identifier | canonical identifier of the indicator SBO instance |
| sbo_short_description | indicator label copied from Section 5.4 |
| indicator_definition | conceptual definition of the analytic signal |
| assessment_guidance | operational guidance for detecting the signal |
| evaluation_notes | clarifications, exclusions, or interpretive boundaries |

### Schema invariants

The generated tables must obey the following rules:

1. Column names must appear **exactly as specified above**.
2. Column order must **not change**.
3. Each row must correspond to **exactly one indicator SBO instance**.
4. Every indicator from **Section 5.4 must appear exactly once**.
5. No additional columns may be added.
6. No columns may be omitted.

---

# Table generation rules

Evaluation specifications must be emitted as **Markdown tables**.

Indicators must be grouped by `component_id`.

For each component:

1. Emit a section heading:

##### Component: `<component_id>`

2. Immediately after the heading, emit a Markdown table with the schema defined above.

3. Populate one row for each indicator belonging to that component.

Indicators must appear in **increasing `indicator_id` order**.

---

# Indicator specification guidance

### indicator_definition

A concise conceptual description of the analytic signal.

The definition should:

- restate the meaning of the indicator
- describe the analytic concept being detected
- avoid referencing scoring thresholds
- avoid referencing performance levels

The definition must remain **conceptual rather than procedural**.

Example:

Detects statements that attribute responsibility across multiple actors such as individuals, teams, institutions, or tools.

---

### assessment_guidance

Operational guidance describing **how the signal may appear in response text**.

This section should:

- describe the kinds of language that express the signal
- reference typical phrasing patterns where helpful
- remain general rather than enumerating exhaustive keyword lists

Example:

Look for language indicating that responsibility is shared across people, teams, institutions, or systems involved in computing work.

---

### evaluation_notes

Clarifications or edge-case guidance.

These may include:

- distinctions between similar indicators
- cases where evidence should not be assigned
- reminders about interpretive boundaries

Example:

Do not assign evidence when the response mentions teamwork without describing shared responsibility.

---

# Generation procedure

The generator must perform the following steps:

1. Read the **Layer 1 SBO instance registry (Section 5.4)**.
2. Identify each indicator SBO instance.
3. Locate the corresponding analytic signals in the analytic brief.
4. Translate those signals into evaluation specifications.
5. Populate one row per indicator in the appropriate component table.

---

# Output format

The output must be emitted as a **single fenced Markdown block**.

The outer fence must use **four backticks**.

Inside that block, emit exactly:

#### 6.1 Layer 1 SBO Value Derivation (Draft)

followed by the component sections and their tables.

No commentary or text may appear outside the tables except the component headings.

---

# Output restrictions

The generated output must contain **only one fenced block**.

Inside that block it must contain:

- the section heading
- component headings
- Markdown tables following the defined schema

Narrative indicator blocks must **not** be used.
===
````