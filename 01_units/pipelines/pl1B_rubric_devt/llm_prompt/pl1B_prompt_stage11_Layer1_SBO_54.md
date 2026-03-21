---
prompt_id: pl1B_stage11_layer1_sbo_registry_prompt_v01
version: v01
stage: pipeline_pl1B_stage11
purpose: generate the Layer 1 SBO Instance Registry by consolidating indicator-level analytic signals from the submission analytic brief
status: active
owner: EECS3000W26

input_contract:
  - rubric_specification_guide (Rubric_SpecificationGuide_v*)
  - submission_analytic_brief (<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*)
  - trigger prompt (`BEGIN GENERATION`)
    
input_structure:
  delimiter: "==="
  artefacts:
    - name: rubric_specification_guide
      expected_elements:
        - layer1_sbo_identifier_structure
        - indicator_identifier_format
        - sbo_short_description_rules
    - name: submission_analytic_brief
      required_sections:
        - "Contrastive Pattern Discovery"
      extracted_elements:
        - analytic_sub_space_registry
        - candidate_indicator_signals
        - candidate_indicator_sets
        - component_identifiers

output_contract: fenced_markdown_table

output_structure:
  outer_fence: "````"
  heading: "#### 5.4 Layer 1 SBO Instances (Draft)"
  table_columns:
    - sbo_identifier
    - sbo_identifier_shortid
    - submission_id
    - component_id
    - indicator_id
    - sbo_short_description
  grouping_rule: group_rows_by_component_id
  ordering_rules:
    - indicator_id_must_be_globally_unique
    - indicator_id_must_be_sequential
    - rows_within_component_sorted_by_indicator_id

identifier_rules:
  submission_identifier_source: assessment_identifier
  component_identifier_source: canonical_component_id_from_analytic_brief
  component_short_identifier_mapping:
    SectionAResponse: SecA
    SectionBResponse: SecB
    SectionCResponse: SecC
    SectionDResponse: SecD
    SectionEResponse: SecE
  indicator_identifier_pattern: "I00-I99"
  sbo_identifier_pattern: "I_<sid>_<cid>_<iid>"
  sbo_identifier_shortid_rule: equals_indicator_id

indicator_generation_rules:
  expected_indicator_range_per_component: "4-8"
  indicator_source_priority:
    - candidate_indicator_set
    - candidate_indicator_signals
    - contrastive_pattern_observations
  consolidation_requirements:
    - merge_redundant_signals
    - preserve_key_analytic_distinctions
    - minimise_indicator_overlap
  indicator_properties:
    - must_be_observable_in_response_text
    - must_be_detectable_without_scoring
    - must_represent_single_signal
    - must_not_require_multiple_conditions

sbo_description_rules:
  description_type: compact_analytic_label
  allowed_forms:
    - noun_phrase
    - analytic_label
  disallowed_patterns:
    - full_sentence_descriptions
    - evaluative_language
    - scoring_threshold_language
    - performance_level_references
    - outcome_predictions
  examples:
    - distributed responsibility attribution
    - role boundary articulation
    - institutional constraint recognition
    - systemic accessibility barrier recognition
    - tension identification

constraints:
  - indicators_must_be_grounded_in_analytic_brief
  - do_not_invent_new_concepts
  - do_not_assign_scores
  - do_not_define_performance_levels
  - do_not_create_dimension_structures
  - do_not_generate_additional_sections
  - output_must_contain_only_one_fenced_block
  - table_must_follow_required_column_order

notes: |
  This prompt performs Stage 1.1 of Pipeline PL1B. It constructs the Layer 1 SBO
  Instance Registry used by downstream scoring prompts. Indicators are derived
  from the contrastive pattern discovery results in the submission analytic
  brief and represent detectable textual signals in student responses.
  The output corresponds to rubric template section 5.4 and must strictly
  follow identifier conventions defined in Rubric_SpecificationGuide_v*.
---
## Wrapper Prompt — Generate Layer 1 SBO Instance Registry (Stage 1.1)

### Prompt title and restrictions

This wrapper prompt generates the **Layer 1 SBO Instance Registry** for an assessment rubric.

The generated output corresponds to:

```text
Rubric Template: 5.4 Layer 1 SBO Instances
```

This stage defines the **set of Layer 1 Score-Bearing Object (SBO) instances** that represent **indicator-level analytic signals** for each component.

This prompt **does not perform scoring** and **does not assign performance levels**.

The purpose is to produce the **indicator registry** used by downstream scoring prompts.

The generated output must conform to the identifier and authoring conventions in:

```text
Rubric_SpecificationGuide_v*
```

If the instructions in the analytic brief conflict with the specification guide, the **specification guide takes precedence** for identifier formation, short identifiers, and `sbo_short_description` authoring.

---

### Required input artefacts

Artefacts are separated using the delimiter:

```text
===
```

Artefacts must appear in the following order:

```text
===
Rubric_SpecificationGuide_v*
===
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*
===
```

If any artefact is missing, malformed, or inconsistent, the prompt must produce **no output**.


### Artefact validation

The analytic brief must contain candidate indicator material derived during Stage 0.3.

Specifically, the analytic brief must preserve distinctions relevant to:
- **minimum plausible presence**
- **extended-structure presence**

If candidate indicators cannot be located in the analytic brief, or if the Stage 0.3 material does not preserve a usable distinction between minimum plausible presence patterns and extended-structure patterns where such patterns exist, the generator must produce no output.

---

### Objective

Using the **contrastive pattern discovery results** contained in the analytic brief, construct the **Layer 1 SBO Instance Registry**.

Each Layer 1 SBO instance corresponds to **one indicator that can be detected in a response text**.

Indicators must be derived from:

- analytic sub-spaces
- contrastive response observations
- candidate indicator signals
- candidate indicator sets
- distinctions between:
  - **minimum plausible presence patterns**
  - **extended-structure patterns**

Indicators represent **detectable textual signals**.

They must **not encode scoring thresholds** and **must not reference performance levels**.

The generated Layer 1 registry must preserve both:

1. **Core analytic structure indicators**
   - capture minimum plausible presence
   - expected to saturate around baseline competent performance

2. **Advanced structural indicators**
   - capture additional explicit structure observed in stronger responses
   - are not required for minimum plausible presence
   - remain binary-verifiable
   - must not encode degree, quality, or strength

---

### Conceptual definition of a Layer 1 SBO instance

A Layer 1 SBO instance represents a **detectable analytic signal in the response text**.

Indicators should correspond to signals such as:

```text
distributed responsibility attribution
responsibility hand-off articulation
institutional constraint recognition
systemic accessibility barrier recognition
```

Indicators must reflect **observable claims or framings expressed in the response**.

They must **not encode evaluative judgement**.

### Core vs advanced indicator classes

Layer 1 SBO instances may belong to one of two functional classes.

#### Core analytic structure indicators

These indicators capture **minimum plausible presence** of the target analytic structure.

Properties:
- detect baseline required structure
- expected to appear in most responses at or above “meets expectations”
- may saturate among stronger responses

#### Advanced structural indicators

These indicators capture **additional explicit structure** beyond minimum plausible presence.

Properties:
- detect structures not required for baseline task completion
- may appear only in stronger responses
- must remain binary-verifiable
- must detect **additional structure**, not quality, degree, or strength

Valid advanced signals may include:
- additional distinct entities of a required type
- additional distinct mechanisms
- additional workflow placements
- explicit cross-stage linkage
- explicit actor–output–action configurations beyond the minimum viable form
- explicit conditional or branching structures

Invalid advanced signals include:
- stronger explanation
- clearer reasoning
- more developed response
- more detailed discussion
- higher-quality articulation

Advanced indicators must still satisfy all Layer 1 binary verification constraints.

### Layer 1 verification constraint (critical)

All Layer 1 SBO instances must support a **binary human-verification decision**.

Each SBO must be interpretable as:

> Is there clear, sufficient, explicit textual evidence that this analytic signal is present?

Accordingly, each SBO must:

- correspond to a signal that can be **verified directly from explicit text**
- have an **implicit minimum threshold of recognisable structure**
- avoid signals that could be triggered by:
  - vague mention
  - implied meaning
  - partial or incomplete phrasing

If a signal cannot be reliably evaluated using a **present / not present decision**, it must not be included as a Layer 1 SBO.

Borderline, weak, or ambiguous forms must be assumed to fall into **not present** at Layer 1 and must instead be handled through:
- Stage 0.3 contrastive pattern distinctions
- multi-SBO aggregation downstream

For advanced structural indicators specifically:

- the signal may require **more than one identifiable textual element**
- the signal may be supported by **distributed but explicit textual evidence**
- however, it must still support a defensible binary verification decision without requiring holistic quality judgement

Advanced indicators must be rejected if they depend on:
- perceived sophistication
- explanatory strength
- interpretive richness
- comparative evaluation against other responses
---

### Indicator design rules

Indicator SBO instances must:

- correspond to observable textual signals
- be grounded in signals extracted during Stage 0.3
- avoid embedding scoring thresholds
- avoid referencing performance levels
- avoid encoding dimension satisfaction
- remain distinguishable from neighbouring indicators in the same component
- be verifiable using a **binary present / not-present decision**
- require **recognisable structural expression**, not keyword presence alone
- exclude signals that would frequently produce borderline ambiguity under binary evaluation

Indicators should capture **distinct analytic signals**, not broad conceptual categories.

Indicators must represent **conceptual analytic signals only**.

They must reflect:
- explicit identification of required analytic entities
- explicit structuring of relationships among those entities
- explicit adherence to analytic constraints

Indicators must not represent:
- engagement
- effort
- writing quality
- general reasoning quality
- degree, quality, strength, sophistication, or persuasiveness

#### Rule for core indicators

Core indicators:
- should correspond to **minimum plausible presence**
- should capture baseline analytic structure
- may saturate among stronger responses

#### Rule for advanced indicators

Advanced indicators:
- must correspond to **extended-structure patterns** identified in Stage 0.3
- must capture **additional explicit structure**, not degree or quality of the same structure
- may rely on more than one textual element where the signal itself is structurally multi-part
- must still support a defensible yes/no verification decision

#### Compoundness rule (revised)

Do not create indicators that are compound in the sense of:
- bundling unrelated signals into one indicator
- requiring multiple independent conditions that do not form a single coherent structure

However, an advanced indicator may capture a **single coherent extended structure** even when that structure is expressed through more than one textual element.

Examples of acceptable advanced structures:
- second distinct output
- second distinct mediation mechanism
- cross-stage mediation linkage
- output–actor–action configuration

Examples of unacceptable compound indicators:
- site + output + linkage all at once
- output + mechanism + workflow + human role all at once
- any indicator that merely restates an entire sub-space

---

### Indicator count expectations

Typical indicator counts:

```text
4–10 indicator SBO instances per component
```

The generator should normally aim to include both:
	•	3–6 core analytic structure indicators
	•	2–4 advanced structural indicators
where the analytic brief supports both classes

If more candidate signals exist, the generator must select a coherent minimal but non-collapsing set that captures both:
	•	minimum plausible presence
	•	extended structural variation

Indicators should:
	•	maximise coverage of observed response variation
	•	minimise redundancy
	•	remain clearly distinguishable
	•	preserve important extended-structure contrasts rather than collapsing them into core indicators

---

### Required fields

Each Layer 1 SBO instance must define the following fields:

```text
sbo_identifier
sbo_identifier_shortid
assessment_id
component_id
indicator_id
sbo_short_description
```

Field meanings:

| field                    | description                                                           |
| ------------------------ | --------------------------------------------------------------------- |
| `sbo_identifier`         | canonical Layer 1 SBO identifier                                      |
| `sbo_identifier_shortid` | compact short reference token                                         |
| `assessment_id`          | identifier of the assessment for which the rubric payload is authored |
| `component_id`           | canonical component identifier from the analytic brief                |
| `indicator_id`           | rubric primitive identifier for the indicator                         |
| `sbo_short_description`  | concise human-readable label for the analytic signal                  |

---

### Identifier conventions

The generated registry must comply with the Layer 1 conventions in `Rubric_SpecificationGuide_v*`.

#### Assessment identifier (`assessment_id`)


`assessment_id` identifies the assessment for which the rubric payload is authored.

Example:

PPP

#### Component identifier (`component_id`)

`component_id` must remain the **canonical dataset component identifier** from the analytic brief.

Examples:

```text
SectionAResponse
SectionBResponse
SectionCResponse
SectionDResponse
SectionEResponse
```

#### Component short identifier (`cid`) for identifier construction

For identifier construction only, derive a compact `cid` from `component_id` using the specification guide conventions.

Use the following mappings unless the input artefacts explicitly define different canonical `cid` values:

| component_id | cid |
|---|---|
| `SectionAResponse` | `SecA` |
| `SectionBResponse` | `SecB` |
| `SectionCResponse` | `SecC` |
| `SectionDResponse` | `SecD` |
| `SectionEResponse` | `SecE` |

`cid` is **not** an output column in the registry table.  
It is used only to construct `sbo_identifier`.

#### Indicator identifier (`indicator_id`)

`indicator_id` must follow the rubric primitive identifier format:

```text
I00 – I99
```

Rules:

- must begin with `I`
- must use a two-digit numeric suffix
- must be zero-padded
- must be unique within the rubric payload
- should be assigned sequentially in the order indicators are introduced in the registry

Examples:

```text
I01
I02
I03
```

Do **not** reset `indicator_id` numbering by component.  
`indicator_id` values must remain unique within the rubric payload.
Indicator numbering must begin with I01 and increment sequentially unless the analytic brief explicitly specifies existing indicator identifiers.

#### Canonical SBO identifier (`sbo_identifier`)

Layer 1 SBO identifiers must follow this structure:

```text
I_<sid>_<cid>_<iid>
```

Where:

- `<sid>` = assessment identifier
- `<cid>` = compact component identifier
- `<iid>` = `indicator_id`

Examples:

```text
I_PPP_SecA_I01
I_PPP_SecB_I07
I_PPP_SecE_I24
```

Do **not** use dotted identifiers such as:

```text
PPP.SectionAResponse.I01
```

#### SBO short identifier (`sbo_identifier_shortid`)

For Layer 1 SBO instances, `sbo_identifier_shortid` should normally be set equal to the `indicator_id`.

Examples:

```text
I01
I02
I03
```

Do **not** generate short identifiers such as:

```text
SBO_A_I01
SBO_SecA_I01
```

Because `indicator_id` values must be unique within the rubric payload, these short identifiers remain unambiguous.

---

### `sbo_short_description` authoring rules

`sbo_short_description` must comply with `Rubric_SpecificationGuide_v*`.

It must:

- be concise
- be a compact human-readable label
- distinguish the SBO from neighbouring instances
- describe the analytic signal without using sentence form
- avoid embedding scoring thresholds
- avoid embedding downstream outcomes
- avoid evaluative language such as `good`, `strong`, `sufficient`, `appropriate`, or `correct`

It should usually be written as a **short noun phrase** or **compact analytic label**, not as a full sentence.

Preferred forms:

```text
distributed responsibility attribution
role boundary articulation
institutional constraint recognition
systemic harm recognition
neutral-tool framing
tension identification
```

Do **not** require descriptions to begin with the word `response`.

Do **not** use sentence-style formats such as:

```text
response identifies where responsibility resides
response describes a responsibility hand-off
```

---

### Consolidation rules

When generating the Layer 1 registry:

1. Prefer candidate indicators from the analytic brief that already correspond to **detectable textual signals in response text**.
2. Consolidate overlapping indicators when they are functionally redundant.
3. Preserve important analytic contrasts that are likely to matter downstream.
4. Avoid producing indicators that are merely broad topic labels.
5. Avoid producing multiple indicators that differ only cosmetically.
6. Retain enough indicators to cover both:
   - the main minimum-plausible-presence structure
   - the main extended-structure variation for each component

Do not collapse an extended-structure pattern into a core indicator when it represents:
- an additional explicit entity
- an additional explicit mechanism
- an additional workflow position
- an additional explicit relational structure

Where several candidate indicators overlap, prefer the version that is:

- more directly observable in text
- narrower and cleaner
- more reusable for downstream dimension design
- more clearly classifiable as either:
  - core analytic structure
  - advanced structural extension

---

### Output format

The output must be emitted as a single **fenced Markdown block**.

The **outer fence must use four backticks**.

Inside that fenced block, emit exactly:

```text
#### 5.4 Layer 1 SBO Instances (Draft)
```

followed by the registry table.

The registry table must use these columns in this exact order:

| sbo_identifier | sbo_identifier_shortid | assessment_id | component_id | indicator_id | sbo_short_description |

Indicators must be grouped by `component_id`.

Indicator class (core vs advanced) is an internal generation distinction only and must not appear as an output column unless separately required by a later template revision.

Within each component group:

- rows should be ordered by `indicator_id`
- identifiers should remain stable and sequential
- descriptions should be concise and parallel where possible

---

### Generation procedure

The generator must:

1. Identify each component present in the analytic brief.
2. Extract candidate indicators associated with that component.
3. Separate candidate signals into:
   - core analytic structure candidates
   - advanced structural candidates
4. Consolidate overlapping signals within each class without collapsing advanced structural candidates into core candidates.
5. Produce approximately **4–10 indicators per component** where possible.
6. Ensure the final set includes both classes where supported by the analytic brief.
7. Assign globally unique `indicator_id` values across the full rubric payload.
8. Construct `sbo_identifier` values using `I_<sid>_<cid>_<iid>`.
9. Set `sbo_identifier_shortid = indicator_id`.
10. Generate concise `sbo_short_description` labels that comply with the specification guide.

The generator must **not introduce concepts that are not present in the analytic brief**.

---

### Registry composition check

Before emitting the registry, the generator must verify for each component:

- whether the analytic brief contains evidence of:
  - minimum plausible presence patterns
  - extended-structure patterns

If both are present in the analytic brief, the registry must preserve both classes of indicators.

A component-level registry is invalid if:
- it contains only core indicators despite clear extended-structure patterns in the analytic brief
- it represents extended structure using degree or quality language rather than additional structure
- it collapses non-saturating structural patterns into core minimum-presence indicators

---

### Output restrictions

The generated output must contain only a single fenced Markdown block.

Inside that block, it must contain only:

```text
#### 5.4 Layer 1 SBO Instances (Draft)
```

followed by the table.

No commentary, explanation, notes, or prefatory text may appear outside or below the table.

===