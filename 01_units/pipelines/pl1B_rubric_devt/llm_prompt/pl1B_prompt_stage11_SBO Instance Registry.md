# .
```
BEGIN GENERATION
```


three inputs
`<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md`
# . 
````
## Wrapper Prompt — Generate Layer 1 SBO Instance Registry (Stage 1.1)

### Prompt title and restrictions

This wrapper prompt generates the **Layer 1 SBO Instance Registry** for an assessment rubric.

The generated output corresponds to:

```
Rubric Template: 5.4 Layer 1 SBO Instances
```

This stage defines the **set of Layer 1 Score-Bearing Object (SBO) instances** that represent **indicator-level analytic signals** for each component.

This prompt **does not perform scoring** and **does not assign performance levels**.

The purpose is to produce the **indicator registry** used by downstream scoring prompts.

---

### Required input artefacts

The following artefacts must be supplied verbatim and delimited using:

```
===
<content>
===
```

Artefacts must appear in the following order:

```
===
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
===
```

If the artefact is missing, malformed, or inconsistent, the prompt must produce **no output**.

---

### Objective

Using the **contrastive pattern discovery results** contained in the analytic brief, construct the **Layer 1 SBO Instance Registry**.

Each Layer 1 SBO instance corresponds to **one indicator that can be detected in a student response**.

Indicators must be derived from:

- analytic sub-spaces  
- contrastive response observations  
- candidate indicator signals  
- candidate indicator sets  

Indicators represent **detectable textual signals**.

They must **not encode scoring thresholds** and **must not reference performance levels**.

---

### Conceptual definition of a Layer 1 SBO instance

A Layer 1 SBO instance represents a **detectable analytic signal in the response text**.

Indicators should correspond to statements such as:

```
response identifies where responsibility resides
response describes a responsibility hand-off
response attributes responsibility to institutions
response identifies systemic accessibility barriers
```

Indicators must reflect **observable claims or framings expressed in the response**.

They must **not encode evaluative judgement**.

---

### Indicator design rules

Indicator SBO instances must:

- correspond to observable textual signals
- be grounded in signals extracted during Stage 0.3
- avoid embedding scoring thresholds
- avoid referencing performance levels
- avoid encoding dimension satisfaction
- avoid compound indicators that require multiple conditions

Indicators should capture **distinct analytic signals**, not broad conceptual categories.

---

### Indicator count expectations

Typical indicator counts:

```
4–8 indicator SBO instances per component
```

If more candidate signals exist, the generator must **select a coherent minimal set** that captures the primary analytic distinctions observed in the calibration responses.

Indicators should:

- maximise coverage of observed response variation
- minimise redundancy
- remain clearly distinguishable

---

### Identifier conventions

Each Layer 1 SBO instance must define the following fields.

```
sbo_identifier
sbo_identifier_shortid
submission_id
component_id
indicator_id
sbo_short_description
```

Field meanings:

| field | description |
|---|---|
| `sbo_identifier` | full SBO identifier constructed from rubric identifier primitives |
| `sbo_identifier_shortid` | short SBO token used internally |
| `submission_id` | submission identifier for the assessment |
| `component_id` | component identifier |
| `indicator_id` | indicator identifier within the component |
| `sbo_short_description` | concise description of the analytic signal |

---

### Identifier construction rules

The identifier must follow this structure:

```
<submission_id>.<component_id>.<indicator_id>
```

Example:

```
PPP.SectionAResponse.I01
```

Short identifier:

```
SBO_<component_short>_<indicator_id>
```

Example:

```
SBO_A_I01
```

Indicator identifiers must follow sequential numbering:

```
I01
I02
I03
...
```

Numbering resets for each component.

---

### Description requirements

`sbo_short_description` must:

- be concise  
- describe a **detectable textual signal**  
- begin with the word **"response"**

Example formats:

```
response identifies where responsibility resides
response attributes responsibility to institutions
response describes a responsibility hand-off
response recognises systemic accessibility barriers
```

Descriptions must **not contain evaluation language** such as:

```
good
strong
sufficient
appropriate
correct
```

---

### Output format

Emit the result as:

```
Rubric Template: 5.4 Layer 1 SBO Instances (Draft)
```

The registry must be presented as a table.

Columns:

| sbo_identifier | sbo_identifier_shortid | submission_id | component_id | indicator_id | sbo_short_description |

Indicators must be grouped by `component_id`.

---

### Generation procedure

The generator must:

1. Identify each component present in the analytic brief.
2. Extract candidate indicators associated with that component.
3. Consolidate overlapping signals into a minimal coherent indicator set.
4. Produce **4–8 indicators per component** where possible.
5. Construct the SBO identifiers.
6. Generate concise `sbo_short_description` values.

The generator must **not introduce concepts that are not present in the analytic brief**.

---

### Output restrictions

The generated output must contain only:

```
Rubric Template: 5.4 Layer 1 SBO Instances (Draft)
```

followed by the table.

No commentary or explanation may appear.
===
````