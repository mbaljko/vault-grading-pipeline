## Rubric_SpecificationGuide_v01
### 0. Purpose
This document defines the **authoring conventions and normative rules** for creating rubric payloads under the four-layer grading ontology.
It serves as the companion to the **Rubric Template**.
The Rubric Template defines the **schema** of the rubric payload.  
The present document defines **how that schema must be populated and interpreted**.
This guide is intended for rubric authors, calibration designers, and pipeline maintainers.
It defines:
- ontological conventions
- identifier conventions
- scale conventions
- SBO instance authoring rules
- value-derivation section conventions
- mapping table semantics
- stability and invariance rules
This guide is **human-readable and normative**.  
It is not itself the machine-readable rubric payload.
### 1. Relationship to Related Artefacts
#### 1.1 Artefact Roles

| artefact | role |
|---|---|
| `Rubric_Template` | schema document defining the structure of the rubric payload |
| `Rubric_SpecificationGuide_v01` | normative guide defining how the template is to be authored |
| `Pipeline_1B_Layered_Rubric_Construction_Pipeline` | procedural guide describing how rubric structures are developed and stabilised |
| `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01` | canonical data architecture and evidence surface specification |
#### 1.2 Interpretive boundary
The rubric payload must be interpretable **without external design commentary**, but the conventions by which it is authored are defined here.
This guide therefore governs:
- how identifiers are formed
- how scales are registered
- how mapping tables are written
- how sections of the rubric template are populated
### 1.3 Rubric Payload Identifier Convention
Rubric payload instances generated from the **Rubric Template** must follow the naming pattern:
`RUBRIC_<ASSESSMENT_ID>_<STATUS>_payload_v<VERSION>.md`
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
`RUBRIC_PPP_CAL_payload_v01.md`  
`RUBRIC_PPP_CAL_payload_v02.md`  
`RUBRIC_PPP_PROD_payload_v01.md`
#### Versioning Rule
A rubric payload with status `PROD` must be treated as **structurally frozen**.
If any structural change is required — including changes to SBO instances, scale definitions, or mapping tables — a **new version of the rubric payload must be created** rather than modifying the existing production rubric.
### 2. Ontological Conventions
#### 2.1 Core terms

| term | definition |
|---|---|
| Assessment Artefact (AA) | the portion of a student submission from which evidence is examined during a scoring pass |
| Score-Bearing Object (SBO) | an analytic entity that receives a score derived from evidence found in an AA |
| scoring layer | a stage of evaluation that assigns scores to one class of SBO |
#### 2.2 Assessment Artefact by layer

| layer | AA |
|---|---|
| Layer 1 | `submission_id × component_id` |
| Layer 2 | `submission_id × component_id` |
| Layer 3 | `submission_id × component_id` |
| Layer 4 | `submission_id` |
#### 2.3 Score-Bearing Objects by layer

| layer | SBO class | score_name |
|---|---|---|
| Layer 1 | indicator | `indicator_score` |
| Layer 2 | dimension | `dimension_score` |
| Layer 3 | component | `component_score` |
| Layer 4 | submission | `submission_score` |
#### 2.4 Score derivation invariant
When multiple layers are used, score derivation follows the invariant:
`AA → indicator SBO scores → dimension SBO scores → component SBO scores → submission SBO score`
Higher-layer SBO scores may be derived from lower-layer SBO scores only through explicit value-derivation rules or mapping tables defined in the rubric payload.
#### 2.5 Evidence boundary rule
Evidence used during scoring must be drawn **only** from the AA defined for that layer.
No evidence outside the AA may be used when assigning scores.
### 3. Identifier Conventions
#### 3.1 Canonical abbreviations
The rubric payload uses the following identifier abbreviations:

| abbreviation | meaning |
|---|---|
| `sid` | submission identifier |
| `cid` | component identifier |
| `iid` | indicator identifier |
| `did` | dimension identifier |
These abbreviations align with the assignment payload specification.
#### 3.2 SBO identifier patterns

| layer | SBO class | identifier pattern |
|---|---|---|
| Layer 1 | indicator | `[I\|P]_sid_cid_iid` |
| Layer 2 | dimension | `[D\|Q]_sid_cid_did` |
| Layer 3 | component | `C_sid_cid` |
| Layer 4 | submission | `S_sid` |
#### 3.3 Meaning of prefix variants

| prefix | typical use |
|---|---|
| `I` | standard indicator tied to analytic content |
| `P` | pan-component or holistic indicator |
| `D` | standard dimension |
| `Q` | pan-component or holistic dimension |
These prefix distinctions are **informative conventions**, not mandatory semantic categories enforced by the payload schema.
#### 3.4 Identifier stability rule
Identifiers must remain stable across rubric revisions unless the corresponding SBO is removed or fundamentally redefined.
Changes to identifier names should be treated as rubric-version changes, not editorial revisions.
### 4. Scale Conventions
#### 4.1 Registered scales
The standard rubric payload defines four scales.

| scale_name | scale_type | ordered |
|---|---|---|
| `indicator_evidence_scale` | evidence | true |
| `dimension_evidence_scale` | evidence | true |
| `component_performance_scale` | performance | true |
| `submission_performance_scale` | performance | true |
#### 4.2 Standard scale values
##### 4.2.1 `indicator_evidence_scale`

| ordered rank | scale_value |
|---|---|
| 1 | `evidence` |
| 2 | `partial_evidence` |
| 3 | `little_to_no_evidence` |
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
For ordered scales, row order in the scale definition table determines the ranking from **strongest** to **weakest**.
The first row is the strongest value.  
Subsequent rows represent progressively weaker values.
Mapping-table comparisons rely on this ordering.
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
| indicator | `I1`, `I2`, `P1` |
| dimension | `D1`, `D2`, `Q1` |
| component | `C1`, `C2` or component shorthand such as `SECA` |
| submission | `S1` or assessment-specific singleton shortid |
#### 5.4 Shortid usage rule
Short identifiers are used only as **compact references** inside:
- mapping tables
- registry summaries
- rule descriptions
They do not replace `sbo_identifier` as the canonical identifier of an SBO instance.
### 6. SBO Instance Authoring Conventions
#### 6.1 General rule
Every SBO instance registry must define **instances**, not merely SBO classes.
An instance must include all fields required by the schema for that layer.
#### 6.2 Layer 4 SBO instances
Layer 4 defines the submission-level SBO.
Required fields:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `submission_id` |
| `sbo_short_description` |
#### 6.3 Layer 3 SBO instances
Layer 3 defines component SBO instances.
Required fields:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `submission_id` |
| `component_id` |
| `sbo_short_description` |
Constraints:
- `component_id` must match the assignment payload specification
- each `(submission_id, component_id)` pair defines a Layer 3 AA
#### 6.4 Layer 2 SBO instances
Layer 2 defines dimension SBO instances.
Required fields:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `submission_id` |
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
| `submission_id` |
| `component_id` |
| `indicator_id` |
| `sbo_short_description` |
Constraints:
- indicator SBO instances are defined independently of dimensions
- an indicator may contribute evidence to one or more dimensions
- `indicator_id` values must remain stable within a rubric version
#### 6.6 `sbo_short_description` authoring rule
`sbo_short_description` should provide a concise human-readable label for the SBO instance.
It should:
- be short enough to scan in tables
- distinguish the SBO from neighbouring instances
- avoid embedding scoring thresholds
- avoid embedding downstream outcomes
Examples:
- `explicit accountability attribution`
- `component coherence`
- `role boundary articulation`
### 7. Layer Value-Derivation Section Conventions
Each Layer N value-derivation section defines **how scores for that layer are derived**.
#### 7.1 Standard subsection grammar
Every value-derivation section should include the following subsections:

| subsection | purpose |
|---|---|
| Target SBO class | names the SBOs receiving the output score |
| Input SBO class | names the SBOs or evidence source used as input |
| Registry summary | lists or summarises the relevant SBO instances |
| Mapping tables | defines deterministic derivation rules, if applicable |
| Fallback rule | defines default behaviour when no stronger rule applies |
| Optional interpretation notes | human-readable clarifications |
#### 7.2 Layer 1 special case
Layer 1 scoring may be implemented through **procedural evaluation** rather than mapping tables.
In such cases:
- the Mapping Tables subsection may be omitted
- evaluation guidance must still be supplied
- the derivation method must still be explicit and reproducible
#### 7.3 Evaluation guidance for Layer 1
Layer 1 value derivation typically uses fields such as:

| field | role |
|---|---|
| `indicator_definition` | defines what the indicator is checking for |
| `assessment_guidance` | tells the evaluator how to identify the signal |
| `evaluation_notes` | clarifies edge cases or exclusions |
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
`Eligibility for meets_expectations requires two dimensions at partially_demonstrated or higher.`
Such rules should be represented in a way that is explicit, deterministic, and compatible with the value-derivation sections.
### 9. Mapping Table Specification
#### 9.1 Purpose
Mapping tables define how scores for one class of SBO are derived from the scores of other SBOs.
A mapping table must be **deterministic**: for any combination of input values there must be exactly one resulting output value.
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
Cells in input columns represent **minimum threshold values**.
A row condition is satisfied when the actual input value is **greater than or equal to** the threshold value in the cell.
Example:
If the input scale ordering is `evidence > partial_evidence > little_to_no_evidence` and the cell contains `partial_evidence`, then the row condition is satisfied when the input value is either `partial_evidence` or `evidence`.
#### 9.5 Wildcard semantics
The symbol `*` may be used as a wildcard.
A wildcard means that the value of that input does not affect the row condition.
Example:

| resultant scale value | I1 | I2 |
|---|---|---|
| `partially_demonstrated` | `evidence` | `*` |
Interpretation:
If `I1 ≥ evidence`, then the row condition is satisfied regardless of the value of `I2`.
#### 9.6 Row precedence
Rows are evaluated from **top to bottom**.
Rows must be ordered from **strongest threshold condition** at the top to **weakest threshold condition** at the bottom.
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
4. Every `(submission_id, component_id, indicator_id)` combination must correspond to a valid Layer 1 SBO instance.
5. Mapping tables must produce exactly one score outcome.
6. Evidence evaluation must operate only within the defined AA.
7. Indicator SBO instances may contribute evidence to multiple dimension SBOs; dimension membership is defined exclusively by the Layer 2 mapping rules.
### 11. Normative Status
This document defines the normative authoring conventions for rubric payloads created under the four-layer grading ontology.
All rubric templates and populated rubric payloads should conform to these conventions unless an explicitly documented exception is adopted at the assessment level.
