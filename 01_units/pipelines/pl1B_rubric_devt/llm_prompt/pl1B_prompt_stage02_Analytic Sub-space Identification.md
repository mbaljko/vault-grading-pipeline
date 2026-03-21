# .
```
BEGIN GENERATION
```


the inputs
`<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
`<ASSESSMENT_ID>_SubmissionAnalyticBrief_v00.md`
Calibration Sample
# . 
````
## PROMPT: Stage 0.2 Analytic Sub-space Identification

You are assisting with rubric design for an assessment.

This prompt performs **Stage 0.2 — Analytic Sub-space Identification**.

The task is to derive **analytic sub-spaces** from the component instructions in the assignment specification and output the section that will be inserted into the Submission Analytic Brief.

This prompt is strictly limited to **task decomposition**.  
It does **not** design indicators, dimensions, score labels, scoring logic, or rubric payload fields.

---

## Required Input Artefacts

Two artefacts must be supplied verbatim using the delimiter `===`.

They must appear in the following order:

```text
===
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01

===
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
```

If either artefact is missing, incomplete, malformed, or inconsistent, produce **no output**.

---

## Stage Purpose

Some assignment components ask students to perform **multiple distinct analytic moves** within a single response.

Each such move defines an **analytic sub-space**.

An analytic sub-space is:

- a **task-defined conceptual area within one component-level response surface**
- derived directly from the **component instructions**
- used as an **analytic scaffold** for later rubric construction
- **not part of the scoring ontology**
- **not included in the Rubric Payload**

Analytic sub-spaces support:

- Stage 0.3 **contrastive pattern discovery**
- Stage 1 **indicator discovery**
- later **dimension formation**

---

## Core Definition

A valid analytic sub-space must satisfy **all** of the following:

1. It corresponds to **one distinct conceptual task** explicitly asked for in the component instructions.
2. It is specific enough that a later analyst could use it as a bounded area for **contrastive pattern discovery**.
3. It is broad enough that it does **not** merely restate a surface wording variant of another sub-space from the same component.
4. It is derived from the **student task**, not from later scoring ideas, inferred constructs, or hidden analytic preferences.

---

## Strict Derivation Rules

### Rule 1 — Use only the component instructions

Derive analytic sub-spaces **only** from the wording of the component instructions in:

```text
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```

Do not use:

- later rubric language
- inferred scoring dimensions
- candidate indicators
- hidden assumptions about what “should” matter
- any content from the Submission Analytic Brief except for consistency of naming and document context

### Rule 2 — One prompt task = one sub-space unless the task is truly indivisible

If a component prompt contains multiple distinct “Address:” bullets, clauses, or task phrases, treat them as **separate candidate sub-spaces**.

Do **not** collapse multiple prompt tasks into a single sub-space merely because they are thematically related.

Only merge tasks if the prompt wording clearly shows that they are **one indivisible analytic move** rather than multiple parallel ones.

### Rule 3 — Do not invent hidden tasks

Do not create sub-spaces for concepts that are merely implied, backgrounded, or analytically convenient unless the component instructions explicitly ask the student to address them.

Examples of invalid invention:

- splitting one prompt bullet into several sub-spaces because it seems analytically rich
- adding a sub-space for “examples” or “justification” when the prompt does not independently require that
- adding a sub-space for “writing quality,” “clarity,” or “professionalism”

### Rule 4 — Do not collapse distinct moves into umbrella wording

Avoid vague umbrella sub-spaces such as:

- “professional responsibility”
- “institutional context”
- “justice issues”
- “AI responsibility”

when the instructions actually specify multiple distinct moves inside those domains.

If the prompt differentiates tasks, the registry must differentiate them.

### Rule 5 — Preserve component-local task structure

Sub-spaces must be defined **within the logic of each component**.

Do not harmonise or normalise across components at the cost of losing the local prompt structure.

### Rule 6 — Single-task components may have one sub-space

If a component genuinely asks for one integrated analytic move, represent it as a **single analytic sub-space**.

Do not force three sub-spaces merely for symmetry.

### Rule 7 — Section E or synthesis components

If a synthesis component is defined as a single reflective or diagnostic synthesis task, it may be represented as **one analytic sub-space**, even if several examples of synthesis content are listed in the instructions.

Use the prompt structure itself to decide this.

---

## Anti-Failure Checks

Before producing output, silently verify all of the following.

### Check A — Coverage check

Every `component_id` in the **Component Registry** of:

```text
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```

must appear in the registry.

### Check B — Instruction-to-sub-space traceability check

Every analytic sub-space must be traceable to a specific component instruction.

If you cannot point to the exact instruction wording that motivates a proposed sub-space, do not include it.

### Check C — No-collapse check

If two or more instruction bullets ask students to address different questions, they must not be collapsed into one sub-space unless the wording makes them inseparable.

### Check D — No-invention check

If a proposed sub-space introduces wording that cannot be grounded in the instructions, remove it.

### Check E — Granularity check

Each sub-space should be:

- narrower than the full component
- broader than an indicator
- conceptually usable as a bounded area for later pattern discovery

### Check F — Registry completeness check

The registry must contain one row for **each analytic sub-space** and no extra rows.

---

## Identifier Rules

Each analytic sub-space must use the identifier format:

```text
<SECTION_LETTER><INTEGER>
```

Examples:

```text
A1
A2
A3
B1
B2
C1
```

Rules:

- `SECTION_LETTER` must correspond to the section letter encoded in the relevant `component_id`.
- numbering must begin at `1` within each component
- numbering must be consecutive
- identifiers must be unique within the registry

---

## Analytic Focus Rules

The `analytic focus` field must be a concise phrase naming the conceptual task.

It must:

- describe the task the student is being asked to perform
- be short and precise
- avoid rubric language
- avoid score language
- avoid full-sentence prose where a concise phrase will do

Good examples:

- accountability locus
- role boundary and responsibility hand-off
- institutional authority and constraint
- criteria for recognising harm or exclusion
- diagnostic synthesis across prior sections

Bad examples:

- whether the student correctly understands accountability
- sophisticated thinking about institutional justice
- strong reasoning about professional obligations
- broad reflection on the whole assignment

---

## Deliverable

Produce the section to be inserted into:

```text
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```

The section must be titled:

```markdown
### 4. Analytic Sub-space Identification
```

This section must contain:

1. a short explanatory introduction
2. an analytic sub-space registry table
3. brief notes explaining how this registry will be used in later stages

---

## Required Output Structure

Output exactly the following structure and nothing else.

### Required heading

```markdown
### 4. Analytic Sub-space Identification
```

### Required explanatory content

State that analytic sub-spaces:

- are task-defined conceptual areas within a component response
- are derived directly from component instructions
- are used only as a design scaffold for later rubric-construction stages
- are not part of the scoring ontology
- do not appear in the Rubric Payload

### Required registry heading

```markdown
### Analytic Sub-space Registry
```

### Required table schema

| component | sub-space_id | analytic focus |
|---|---|---|

Requirements:

- one row per analytic sub-space
- include all components
- component names must exactly match the `component_id` values in the Assignment Payload Spec

### Required closing notes heading

```markdown
### Notes for Later Stages
```

Include concise notes stating that:

- these sub-spaces guide Stage 0.3 contrastive pattern discovery
- multiple indicators may later arise within one sub-space
- later dimensions may merge signals across multiple sub-spaces
- sub-spaces are analytic scaffolds only, not scoring ontology entities

---

## Output Constraints

Do not:

- reproduce the full Submission Analytic Brief
- reproduce the full Assignment Payload Spec
- include chain-of-thought
- include a mapping commentary outside the required section
- include justification paragraphs for each row
- include rubric dimensions, indicators, score labels, or scoring language

Do:

- output only the completed Section 4 content
- ensure exact structural compliance
- ensure that each row is directly grounded in component instructions

---

## Final Silent Validation

Before outputting, silently confirm:

- every registry row is instruction-grounded
- no distinct prompt task has been collapsed without justification from the prompt wording
- no analytic sub-space has been invented
- every component is represented
- identifiers are valid and consecutive
- analytic focus phrases are concise and non-evaluative

If any of these checks fail, revise internally before producing output.
===
````
