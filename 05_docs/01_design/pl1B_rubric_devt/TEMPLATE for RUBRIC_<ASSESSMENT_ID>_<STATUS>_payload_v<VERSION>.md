## Rubric_Template
### Purpose
Defines the **structural schema of a rubric payload** used to evaluate assessment submissions.
The rubric operates under the **four-layer scoring ontology**.
Authoring conventions, identifier rules, and mapping semantics are defined in `Rubric_SpecificationGuide_v01`.

| layer | SBO |
|---|---|
| Layer 1 | indicator |
| Layer 2 | dimension |
| Layer 3 | component |
| Layer 4 | submission |
### 1. Layer 4 SBO Registry

| field |
|---|
| `submission_score` |
### 2. Layer 3 SBO Registry

| field |
|---|
| `component_score` |
### 3. Layer 2 SBO Registry

| field |
|---|
| `dimension_score` |
### 4. Layer 1 SBO Registry

| field |
|---|
| `indicator_score` |
### 5. SBO Instance Registries
Instance registries define the specific **Score-Bearing Object (SBO) instances** used by the rubric.
Each instance must include:
- `sbo_identifier`
- `sbo_identifier_shortid`
- any layer-specific identifier fields (for example `component_id`, `dimension_id`, or `indicator_id`)
- `sbo_short_description`
`sbo_identifier_shortid` is a compact token used in mapping tables and rule definitions.
#### 5.4 Layer 1 SBO Instances
Registry of **indicator SBO instances**.
Required fields typically include:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `submission_id` |
| `component_id` |
| `indicator_id` |
| `sbo_short_description` |
#### 5.3 Layer 2 SBO Instances
Registry of **dimension SBO instances**.
Required fields typically include:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `submission_id` |
| `component_id` |
| `dimension_id` |
| `sbo_short_description` |
#### 5.2 Layer 3 SBO Instances
Registry of **component SBO instances**.
Required fields typically include:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `submission_id` |
| `component_id` |
| `sbo_short_description` |
#### 5.1 Layer 4 SBO Instances
Registry of **submission SBO instances**.
Required fields typically include:

| field |
|---|
| `sbo_identifier` |
| `sbo_identifier_shortid` |
| `submission_id` |
| `sbo_short_description` |
### 6. SBO Value Derivation Registries
Value-derivation sections define how scores for each SBO layer are computed.
These sections may contain:
- registry summaries
- evaluation guidance
- mapping tables
- fallback rules
- interpretation notes
#### 6.1 Layer 1 Value Derivation
Derives `indicator_score` from `response_text`.
Layer 1 scoring may be implemented through procedural evaluation rather than mapping tables.
Typical contents:
- indicator definitions
- assessment guidance
- evaluation notes
#### 6.2 Layer 2 Value Derivation
Derives `dimension_score` from indicator evidence.
Typical contents:
- indicator → dimension mapping tables
- optional fallback rules
- interpretation notes
#### 6.3 Layer 3 Value Derivation
Derives `component_score` from dimension evidence.
Typical contents:
- dimension → component mapping tables
- optional boundary rules
- interpretation notes
#### 6.4 Layer 4 Value Derivation
Derives `submission_score` from component scores.
Typical contents:
- component aggregation rules
- optional fallback rules
- interpretation notes
### 7. Scoring Ontology
Evaluation hierarchy.

| entity |
|---|
| submission |
| component |
| dimension |
| indicator |
Assessment artefact for Layers 1–3: `submission_id × component_id`.
Assessment artefact for Layer 4: `submission_id`.
### 8. Rubric Stability States

| state |
|---|
| Draft |
| Under Evaluation |
| Stabilised |
| Frozen |
### 9. Scale Registry
Defines the scoring scales used by the rubric.

| scale_name | scale_type |
|---|---|
| `indicator_evidence_scale` | evidence |
| `dimension_evidence_scale` | evidence |
| `component_performance_scale` | performance |
| `submission_performance_scale` | performance |
