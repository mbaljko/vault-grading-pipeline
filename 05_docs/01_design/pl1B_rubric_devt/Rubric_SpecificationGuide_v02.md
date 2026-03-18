## Rubric_SpecificationGuide_v02

### 0. Purpose

This document defines the authoring conventions and normative rules for creating rubric payloads under the four-layer grading ontology.  
It serves as the companion to the `Rubric_Template`.  
The `Rubric_Template` defines the schema of the rubric payload.  
This guide defines how that schema must be populated and interpreted.

This guide is intended for rubric authors, calibration designers, and pipeline maintainers.  
It defines:

- ontological conventions
- identifier conventions
- scale conventions
- SBO instance authoring rules
- value-derivation section conventions
- mapping table semantics
- stability and invariance rules

This guide is human-readable and normative.  
It is not itself the machine-readable rubric payload.

### 0.0 Identifier and Ontology Layers

The rubric system operates across three distinct identifier domains.  
Each domain corresponds to a different level of the grading architecture.

```text
DATASET DOMAIN
────────────────────────────────────────────────────────

participant_id
      │
      └── identifies a participant-authored assignment artefact
          in the canonical dataset


ONTOLOGY DOMAIN (Assessment Artefact and scoring layers)
────────────────────────────────────────────────────────

Assessment Artefact (AA)

Layer 1–3 AA:
participant_id × component_id
        │
        │ evidence examined
        ▼

indicator SBO
        │
        ▼
dimension SBO
        │
        ▼
component SBO
        │
        ▼
submission SBO   (Layer 4 aggregation object)


RUBRIC PAYLOAD DOMAIN (rubric specification)
────────────────────────────────────────────────────────

assessment_id
      │
      ▼
sid  (short identifier derived from assessment_id)

      │
      ▼
SBO identifiers constructed from RP identifiers

I_<sid>_<cid>_<iid>    indicator SBO
D_<sid>_<cid>_<did>    dimension SBO
C_<sid>_<cid>          component SBO
S_<sid>                submission SBO
```

### 0.1 Interpretation

| layer | identifier | role |
|---|---|---|
| dataset | `participant_id` | identifies a participant's assignment artefact |
| ontology | `participant_id × component_id` | defines the Assessment Artefact examined for evidence |
| rubric payload | `assessment_id` / `sid` | identifies the assessment for which the rubric is authored |

The submission SBO refers to the Layer-4 scoring object representing the assessment-level aggregation, not to an individual participant submission.

### 1. Relationship to Related Artefacts

#### 1.1 Artefact Roles

| artefact | role |
|---|---|
| `Rubric_Template` | schema document defining the structure of the rubric payload |
| `Rubric_SpecificationGuide_v01` | normative guide defining how the template is to be authored |
| `Pipeline_1B_Layered_Rubric_Construction_Pipeline` | procedural guide describing how rubric structures are developed and stabilised |
| `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01` | canonical data architecture and evidence surface specification |

#### 1.2 Interpretive boundary

The rubric payload must be interpretable without external design commentary, but the conventions by which it is authored are defined here.  
This guide therefore governs:

- how identifiers are formed
- how scales are registered
- how mapping tables are written
- how sections of the rubric template are populated

### 1.3 Rubric Payload Identifier Convention

Rubric payload instances generated from the `Rubric_Template` must follow the naming pattern:

```text
RUBRIC_<ASSESSMENT_ID>_<STATUS>_payload_v<VERSION>.md
```

#### Identifier Element Registry

| element | meaning |
|---|---|
| `ASSESSMENT_ID` | identifier of the assessment defined in the Assignment Payload Specification |
| `STATUS` | lifecycle state of the rubric payload |
| `VERSION` | sequential version number of the rubric payload |

#### Valid Status Values

| status | meaning |
|---|---|
| `CAL` | calibration rubric; the rubric structure may still be revised |
| `PROD` | frozen production rubric used for scoring |

#### Example Filenames

```text
RUBRIC_PPP_CAL_payload_v01.md
RUBRIC_PPP_CAL_payload_v02.md
RUBRIC_PPP_PROD_payload_v01.md
```

#### Versioning Rule

A rubric payload with status `PROD` must be treated as structurally frozen.  
If any structural change is required, including changes to SBO instances, scale definitions, or mapping tables, a new version of the rubric payload must be created rather than modifying the existing production rubric.

### 2. Ontological Conventions

#### 2.1 Core terms

| term | definition |
|---|---|
| Assessment Artefact (AA) | the participant-authored artefact from which evidence is examined during a scoring pass |
| Score-Bearing Object (SBO) | an analytic entity that receives a score or value derived from evidence found in an AA |
| scoring layer | a stage of evaluation that assigns scores or values to one class of SBO |

#### 2.2 Assessment Artefact by layer

| layer | AA |
|---|---|
| Layer 1 | `participant_id × component_id` |
| Layer 2 | `participant_id × component_id` |
| Layer 3 | `participant_id × component_id` |
| Layer 4 | `participant_id` |

#### 2.3 Score-Bearing Objects by layer

| layer | SBO class | score_name |
|---|---|---|
| Layer 1 | indicator | `indicator_value` |
| Layer 2 | dimension | `dimension_score` |
| Layer 3 | component | `component_score` |
| Layer 4 | submission | `submission_score` |

The submission SBO class represents the top-level scoring object for the assessment, not an individual participant submission.  
Participant artefacts are identified using `participant_id` in the canonical dataset.

#### 2.4 Score derivation invariant

When multiple layers are used, score derivation follows the invariant:

```text
AA → indicator SBO values → dimension SBO scores → component SBO scores → submission SBO score
```

Higher-layer SBO scores may be derived from lower-layer SBO values only through explicit value-derivation rules or mapping tables defined in the rubric payload.

#### 2.5 Evidence boundary rule

Evidence used during scoring must be drawn only from the AA defined for that layer.  
No evidence outside the AA may be used when assigning scores or values.

### 3. Identifier Conventions

This section defines the identifier primitives and naming rules used when constructing SBO identifiers across all four scoring layers.

#### 3.1 Intended outcomes of the identifier conventions

Identifier conventions ensure that rubric payloads remain:

- readable
- structurally predictable
- stable across rubric revisions
- unambiguous when referencing indicators and dimensions across components

Consistent identifiers allow rubric authors, calibration designers, and grading pipelines to reference SBOs, indicators, and dimensions unambiguously across scoring layers, components, and rubric versions.

#### 3.2 Identifier systems in the rubric payload

Two distinct identifier systems operate in the rubric payload.

1. SBO identifiers  
   Structured identifiers constructed from rubric primitive identifiers that uniquely identify Score-Bearing Objects across the four scoring layers.

2. rubric primitive identifiers (RP identifiers)  
   Compact tokens that identify analytic entities used in rubric construction.  
   These include identifiers such as `sid`, `cid`, `iid`, and `did`.

Rubric primitive identifiers provide the building blocks of the identifier system.  
SBO identifiers combine those primitives into fully qualified identifiers that correspond to concrete scoring entities in the rubric payload.

#### 3.3 SBO identifiers

##### 3.3.1 SBO identifier structure

SBO identifiers are structured identifiers constructed from Rubric Primitive identifiers.  
They uniquely identify rubric scoring entities across the four scoring layers.

The prefix of the SBO identifier indicates the SBO class, which corresponds directly to the scoring layer.

| layer | SBO class | identifier pattern |
|---|---|---|
| Layer 1 | indicator | `I_<sid>_<cid>_<iid>` |
| Layer 2 | dimension | `D_<sid>_<cid>_<did>` |
| Layer 3 | component | `C_<sid>_<cid>` |
| Layer 4 | submission | `S_<sid>` |

Examples:

| SBO identifier | expansion |
|---|---|
| `S_PPP` | Layer-4 submission SBO for assessment `PPP` |
| `C_PPP_SecA` | component SBO for component `SecA` |
| `D_PPP_SecA_D01` | dimension SBO `D01` evaluating component `SecA` |
| `I_PPP_SecA_I01` | indicator SBO `I01` detecting evidence in component `SecA` |

The values of `<sid>`, `<cid>`, `<iid>`, and `<did>` are described below under rubric primitive identifiers.

##### 3.3.2 `sbo_identifier_shortid`

In addition to the full `sbo_identifier`, each SBO instance may define a compact identifier named `sbo_identifier_shortid`.  
This value provides a short reference token used in mapping tables and rule descriptions.

For indicator and dimension SBO instances, `sbo_identifier_shortid` is normally set equal to the RP identifier.

| SBO class | RP identifier | typical shortid |
|---|---|---|
| indicator | `iid` | `I01`, `P01` |
| dimension | `did` | `D01`, `Q01` |

Because the RP identifier conventions ensure that `iid` and `did` values are unique within the rubric payload, these short identifiers remain unambiguous even when used without the component identifier.

#### 3.4 Rubric Primitive identifiers

The rubric payload uses four rubric primitive identifiers.

| primitive | meaning |
|---|---|
| `sid` | short identifier derived from `assessment_id` |
| `cid` | short identifier representing a component |
| `iid` | indicator identifier |
| `did` | dimension identifier |

These primitives form the building blocks used to construct SBO identifiers.  
The values of `sid` and `cid` originate from the Assignment Payload Specification, while `iid` and `did` are defined within the rubric payload.

##### 3.4.1 General construction rules

All RP identifiers should follow the following conventions.

| rule | description |
|---|---|
| compact | typically 2–6 characters |
| recognisable | clearly reference the entity being identified |
| stable | must remain constant across rubric revisions |
| alphanumeric | avoid spaces and punctuation |

##### 3.4.2 RP identifier registry

| RP identifier | associated SBO class | value source | example | notes |
|---|---|---|---|---|
| `sid` | submission | Assignment Payload Specification | `PPP` | short identifier derived from `assessment_id` and used in construction of submission-layer SBO identifiers |
| `cid` | component | derived from canonical `component_id` | `SecA` | compact identifier used inside SBO identifiers |
| `iid` | indicator | rubric-defined | `I01` | may use subtype prefixes `I` or `P` |
| `did` | dimension | rubric-defined | `D01` | may use subtype prefixes `D` or `Q` |

##### 3.4.3 Indicator RP identifier format

Indicator identifiers follow a fixed two-digit numbering scheme.

Format:

```text
I00 – I99
```

| rule | description |
|---|---|
| prefix | must begin with `I` or `P` |
| numbering | two-digit numeric suffix |
| padding | single-digit numbers must be zero-padded |
| range | `00–99` |
| uniqueness | each `iid` value must be unique within the rubric payload |

Examples:

| iid |
|---|
| `I01` |
| `I02` |
| `P01` |

##### 3.4.4 Dimension RP identifier format

Dimension identifiers follow the same two-digit numbering scheme.

Format:

```text
D00 – D99
```

| rule | description |
|---|---|
| prefix | must begin with `D` or `Q` |
| numbering | two-digit numeric suffix |
| padding | single-digit numbers must be zero-padded |
| range | `00–99` |
| uniqueness | each `did` value must be unique within the rubric payload |

Examples:

| did |
|---|
| `D01` |
| `D02` |
| `Q01` |

##### 3.4.5 Component RP identifier derivation

The `cid` is a short identifier representing a component.  
It is derived from the canonical `component_id` defined in the Assignment Payload Specification.

Example:

| field | value |
|---|---|
| `component_id` | `SectionAResponse` |
| `cid` | `SecA` |

The `component_id` remains the canonical dataset identifier.  
The `cid` exists only to make SBO identifiers compact and readable.

Typical transformations:

| component_id | cid |
|---|---|
| `SectionAResponse` | `SecA` |
| `SectionBResponse` | `SecB` |
| `SectionCResponse` | `SecC` |

##### 3.4.6 Identifier stability rule

RP identifiers must remain stable across rubric revisions unless the corresponding entity is removed or fundamentally redefined.  
Changes to identifier values should be treated as rubric-version changes, not editorial revisions.

##### 3.4.7 RP identifier subtype prefixes

The RP identifiers `iid` and `did` may contain semantic subtype prefixes that signal the analytic scope of the indicator or dimension.  
These subtype prefixes are part of the RP identifier value, not part of the SBO identifier prefix.

| RP identifier | subtype prefixes | meaning |
|---|---|---|
| `iid` | `I`, `P` | component-local indicator (`I`) or pan-component indicator (`P`) |
| `did` | `D`, `Q` | component-local dimension (`D`) or pan-component dimension (`Q`) |

Examples:

| RP identifier value | meaning |
|---|---|
| `I01` | component-local indicator |
| `P01` | pan-component indicator |
| `D01` | component-local dimension |
| `Q01` | pan-component dimension |

##### 3.4.8 RP identifier uniqueness domains

Within a rubric payload, the RP identifiers `iid` and `did` define two unique identifier domains.

| domain | definition |
|---|---|
| `IID` | the set of all indicator RP identifier values used in the rubric payload |
| `DID` | the set of all dimension RP identifier values used in the rubric payload |

These domains must satisfy the following rules.

| rule | description |
|---|---|
| uniqueness of `IID` | no two indicator SBO instances may share the same `iid` value |
| uniqueness of `DID` | no two dimension SBO instances may share the same `did` value |
| disambiguation | each `iid` or `did` value must identify exactly one RP identifier within its domain |

### 4. Scale Conventions

#### 4.1 Registered scales

The standard rubric payload defines four scales.

| scale_name | scale_type | ordered |
|---|---|---|
| `indicator_verification_scale` | verification | true |
| `dimension_evidence_scale` | evidence | true |
| `component_performance_scale` | performance | true |
| `submission_performance_scale` | performance | true |

#### 4.2 Standard scale values

##### 4.2.1 `indicator_verification_scale`

| ordered rank | scale_value |
|---|---|
| 1 | `present` |
| 2 | `not_present` |

Interpretation:

- `present` = clear, sufficient, explicit textual evidence of the indicator is present in the Assessment Artefact
- `not_present` = the indicator is absent, weak, vague, implied, ambiguous, partial, or otherwise insufficient for positive verification

Layer 1 does not assign partial credit.  
Borderline, incomplete, or weakly grounded forms must be treated as `not_present`.

##### 4.2.2 `dimension_evidence_scale`

| ordered rank | scale_value |
|---|---|
| 1 | `demonstrated` |
| 2 | `partially_demonstrated` |
| 3 | `little_to_no_demonstration` |

##### 4.2.3 `component_performance_scale`

| ordered rank | scale_value |
|---|---|
| 1 | `exceeds_expectations` |
| 2 | `meets_expectations` |
| 3 | `approaching_expectations` |
| 4 | `below_expectations` |
| 5 | `not_demonstrated` |

##### 4.2.4 `submission_performance_scale`

| ordered rank | scale_value |
|---|---|
| 1 | `exceeds_expectations` |
| 2 | `meets_expectations` |
| 3 | `approaching_expectations` |
| 4 | `below_expectations` |
| 5 | `not_demonstrated` |

#### 4.3 Scale ordering rule

For ordered scales, row order in the scale definition table determines the ranking from strongest to weakest.  
The first row is the strongest value.  
Subsequent rows represent progressively weaker values.  
Mapping-table comparisons rely on this ordering.

For `indicator_verification_scale`, ordered comparison exists only to support downstream use of Layer 1 values.  
It does not imply graded evidence within Layer 1 itself.

#### 4.4 Scale discipline rule

All input values used in mapping tables must come from the scale associated with the input SBOs.  
All output values must come from the scale associated with the target SBO.

### 5. Short Identifier Conventions

#### 5.1 `sbo_identifier_shortid`

`sbo_identifier_shortid` is a compact token used to reference a specific SBO instance within mapping tables.

#### 5.2 Required properties

`sbo_identifier_shortid` values must be:

- unique within the rubric payload
- stable across rubric revisions unless the SBO is removed
- suitable for use as a column header
- composed only of alphanumeric characters and underscores

#### 5.3 Typical forms

| SBO class | typical shortid forms |
|---|---|
| indicator | `I01`, `I02`, `P01` |
| dimension | `D01`, `D02`, `Q01` |
| component | `C1`, `C2` or component shorthand such as `SECA` |
| submission | `S1` or assessment-specific singleton shortid |

#### 5.4 Shortid usage rule

Short identifiers are used only as compact references inside:

- mapping tables
- registry summaries
- rule descriptions

They do not replace `sbo_identifier` as the canonical identifier of an SBO instance.

### 6. SBO Instance Authoring Conventions

#### 6.1 General rule

Every SBO instance registry must define instances, not merely SBO classes.  
An instance must include all fields required by the schema for that layer.

#### 6.2 Layer 4 SBO instances

Layer 4 defines the submission-level SBO.  
This SBO represents the assessment-level aggregation object for scoring, not an individual participant artefact.

Required fields:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `assessment_id` |
| `sbo_short_description` |

#### 6.3 Layer 3 SBO instances

Layer 3 defines component SBO instances.

Required fields:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `assessment_id` |
| `component_id` |
| `sbo_short_description` |

Constraints:

- `component_id` must match the Assignment Payload Specification
- each `component_id` must correspond to a valid component defined in the Assignment Payload Specification

#### 6.4 Layer 2 SBO instances

Layer 2 defines dimension SBO instances.

Required fields:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `assessment_id` |
| `component_id` |
| `dimension_id` |
| `sbo_short_description` |

Constraints:

- `(component_id, dimension_id)` pairs must be unique
- `dimension_id` values must remain stable across rubric versions

#### 6.5 Layer 1 SBO instances

Layer 1 defines indicator SBO instances.

Required fields:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `assessment_id` |
| `component_id` |
| `indicator_id` |
| `sbo_short_description` |

Constraints:

- indicator SBO instances are defined independently of dimensions
- an indicator may contribute evidence to one or more dimensions
- `indicator_id` values must remain stable within a rubric version
- each Layer 1 indicator SBO instance must represent one atomic analytic signal suitable for binary human verification
- Layer 1 indicators must be directly verifiable from explicit response text
- Layer 1 indicators must not require holistic judgement or comparative evaluation
- Layer 1 indicators must not encode degree, quality, strength, maturity, or completeness
- Layer 1 indicators must not represent engagement, effort, fluency, writing quality, or generic reasoning quality

#### 6.6 `sbo_short_description` authoring rule

`sbo_short_description` should provide a concise human-readable label for the SBO instance.  
It should:

- be short enough to scan in tables
- distinguish the SBO from neighbouring instances
- avoid embedding scoring thresholds
- avoid embedding downstream outcomes

For Layer 1 SBO instances, `sbo_short_description` must denote a signal that can be verified through a binary `present` / `not_present` judgement based on explicit text alone.  
Descriptions should avoid labels that imply degree, maturity, strength, sufficiency, or quality.

Examples:

- `explicit accountability attribution`
- `component coherence`
- `role boundary articulation`

### 7. Layer Value-Derivation Section Conventions

Each Layer N value-derivation section defines how scores or values for that layer are derived.

#### 7.1 Standard subsection grammar

Every value-derivation section should include the following subsections.

| subsection | purpose |
|---|---|
| Target SBO class | names the SBOs receiving the output score or value |
| Input SBO class | names the SBOs or evidence source used as input |
| Registry summary | lists or summarises the relevant SBO instances |
| Mapping tables | defines deterministic derivation rules, if applicable |
| Fallback rule | defines default behaviour when no stronger rule applies |
| Optional interpretation notes | human-readable clarifications |

#### 7.2 Layer 1 special case

Layer 1 value derivation is implemented through procedural evaluation rather than mapping tables.

Layer 1 value derivation operates as binary human verification.

A Layer 1 value records whether clear, sufficient, explicit textual evidence of the indicator is present in the Assessment Artefact.

Accordingly:

- the Mapping Tables subsection may be omitted
- evaluation guidance must still be supplied
- the derivation method must still be explicit and reproducible
- vague mention, implication, partial performance, weak execution, ambiguous wording, or borderline evidence must be treated as `not_present`

Layer 1 thresholding concerns indicator presence detection and is part of procedural value derivation.  
It is distinct from hard boundary rules operating on `dimension_score` or `component_score`.

#### 7.3 Evaluation guidance for Layer 1

Layer 1 value derivation typically uses fields such as:

| field | role |
|---|---|
| `indicator_definition` | defines what the indicator is checking for |
| `assessment_guidance` | tells the evaluator how to identify the signal |
| `evaluation_notes` | clarifies edge cases or exclusions |

For Layer 1, evaluation guidance must support a binary `present` / `not_present` decision.

`indicator_definition` must:

- define the conceptual signal being checked
- remain conceptual rather than procedural
- avoid performance language and score-level terminology

`assessment_guidance` must:

- describe how the signal may appear in explicit response text
- support fast human verification
- clarify what kinds of wording or structure count as recognisable evidence
- distinguish explicit structure from vague mention where needed

`evaluation_notes` must:

- identify false-positive forms that should not be counted
- identify borderline forms that must be treated as `not_present`
- clarify distinctions from neighbouring indicators
- reinforce that mere keyword mention is insufficient unless the required analytic structure is present

### 8. Hard Boundary Rule Conventions

#### 8.1 Purpose

Hard boundary rules constrain score eligibility.  
They do not replace mapping tables; they supplement them.

#### 8.2 Valid scope

Hard boundary rules may operate only on:

- `dimension_score`
- `component_score`

They must not introduce evidence from outside the defined AA.

#### 8.3 Example form

Example rule statement:

```text
Eligibility for meets_expectations requires two dimensions at partially_demonstrated or higher.
```

Such rules should be represented in a way that is explicit, deterministic, and compatible with the value-derivation sections.

### 9. Mapping Table Specification

#### 9.1 Purpose

Mapping tables define how scores for one class of SBO are derived from the scores of other SBOs.  
A mapping table must be deterministic: for any combination of input values there must be exactly one resulting output value.

Ordered threshold comparison semantics in this section apply to mapping tables used for Layers 2–4.  
Layer 1 does not use ordered threshold mapping tables.

#### 9.2 General structure

Each mapping table has the structure:

| resultant scale value | `<input_sbo_shortid_1>` | `<input_sbo_shortid_2>` | ... |
|---|---|---|---|

Interpretation:

- columns represent input SBOs
- rows represent threshold conditions
- `resultant scale value` specifies the output score for the target SBO

#### 9.3 Column requirements

Each mapping table must contain:

1. `resultant scale value`
2. one column for each input SBO

Column names for input SBOs must match `sbo_identifier_shortid` values defined in the relevant SBO registry.

#### 9.4 Cell semantics

Cells in input columns represent minimum threshold values.  
A row condition is satisfied when the actual input value is greater than or equal to the threshold value in the cell.

Example:  
If the input scale ordering is `demonstrated > partially_demonstrated > little_to_no_demonstration` and the cell contains `partially_demonstrated`, then the row condition is satisfied when the input value is either `partially_demonstrated` or `demonstrated`.

#### 9.5 Wildcard semantics

The symbol `*` may be used as a wildcard.  
A wildcard means that the value of that input does not affect the row condition.

Example:

| resultant scale value | I1 | I2 |
|---|---|---|
| `partially_demonstrated` | `present` | `*` |

Interpretation:  
If `I1 ≥ present`, then the row condition is satisfied regardless of the value of `I2`.

#### 9.6 Row precedence

Rows are evaluated from top to bottom.  
Rows must be ordered from strongest threshold condition at the top to weakest threshold condition at the bottom.  
The first row whose threshold condition is satisfied determines the output.  
Once a row is satisfied, later rows are ignored.  
No two rows may define identical threshold conditions for the same set of input SBOs.

#### 9.7 Coverage requirement

Mapping tables must guarantee that every possible combination of input values yields a result.  
Coverage may be achieved by:

1. explicitly enumerating all combinations, or
2. ensuring that the bottom row defines the weakest possible threshold condition

In practice, the bottom row usually uses the weakest values of the input scales so that every input configuration satisfies at least that row.

#### 9.8 Validity constraints

A valid mapping table must satisfy all of the following:

1. `resultant scale value` contains only values from the target SBO scale
2. input columns contain only values from the corresponding input SBO scales or the wildcard `*`
3. rows are ordered from strongest to weakest threshold condition
4. evaluation yields exactly one output value for every possible input combination

#### 9.9 Evaluation procedure

Mapping-table evaluation follows this procedure:

```text
for each row in the table (top to bottom):
    if all input values meet or exceed the row thresholds:
        return resultant_scale_value
```

Because rows are ordered from strongest to weakest, the returned value is the strongest satisfied threshold condition.

### 10. Structural Invariants

The following invariants must hold for any rubric authored under this guide.

1. All mapping tables must use input values drawn from the scale associated with the input SBOs and output values drawn from the scale associated with the target SBO.
2. Every component must define its dimensions.
3. Every `(component_id, dimension_id)` pair must be unique.
4. Every `(assessment_id, component_id, indicator_id)` combination must correspond to a valid Layer 1 SBO instance.
5. Mapping tables must produce exactly one score outcome.
6. Evidence evaluation must operate only within the defined AA.
7. Indicator SBO instances may contribute evidence to multiple dimension SBOs; dimension membership is defined exclusively by the Layer 2 mapping rules.
8. Layer 1 value derivation must use binary human verification based on explicit text only.
9. For Layer 1, `present` requires clear, sufficient, explicit textual evidence of the target signal.
10. For Layer 1, ambiguous, partial, vague, implied, or weakly structured forms must be treated as `not_present`.

### 11. Normative Status

This document defines the normative authoring conventions for rubric payloads created under the four-layer grading ontology.  
All rubric templates and populated rubric payloads should conform to these conventions unless an explicitly documented exception is adopted at the assessment level.