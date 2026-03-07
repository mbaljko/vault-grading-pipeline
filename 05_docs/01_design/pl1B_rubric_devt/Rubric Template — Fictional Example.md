## Rubric_Template_FictionalExample_PPP
### Purpose
Illustrates how the **Rubric Template** appears once populated with exemplar structures for the assessment `PPP` (Professional Practice Portfolio).
The example shows rubric structures for the component `SectionAResponse`.
The rubric follows the **four-layer scoring ontology**.

| layer | score-bearing object |
|---|---|
| Layer 1 | indicator SBO |
| Layer 2 | dimension SBO |
| Layer 3 | component SBO |
| Layer 4 | submission SBO |
Assessment artefact for Layers 1–3: `submission_id × component_id`  
Assessment artefact for Layer 4: `submission_id`
### 1. Layer 4 SBO Instance Registry

| sbo_identifier | sbo_short_description |
|---|---|
| `S_sid` | overall submission performance score |
### 2. Layer 3 SBO Instance Registry

| sbo_identifier | component_id | sbo_short_description |
|---|---|---|
| `C_sid_SectionAResponse` | `SectionAResponse` | component performance for Section A |
### 3. Layer 2 SBO Instance Registry

| sbo_identifier | component_id | dimension_id | sbo_short_description |
|---|---|---|---|
| `D_sid_SectionAResponse_D1` | `SectionAResponse` | D1 | clarity of responsibility attribution |
| `D_sid_SectionAResponse_D2` | `SectionAResponse` | D2 | recognition of distributed accountability |
| `D_sid_SectionAResponse_D3` | `SectionAResponse` | D3 | articulation of professional obligations |
### 4. Layer 1 SBO Instance Registry

| sbo_identifier | component_id | indicator_id | sbo_short_description |
|---|---|---|---|
| `I_sid_SectionAResponse_I1` | `SectionAResponse` | I1 | explicit assignment of responsibility |
| `I_sid_SectionAResponse_I2` | `SectionAResponse` | I2 | identification of responsibility outside the individual |
| `I_sid_SectionAResponse_I3` | `SectionAResponse` | I3 | description of responsibility hand-off |
| `I_sid_SectionAResponse_I4` | `SectionAResponse` | I4 | explicit reference to regulatory or institutional oversight |
### 5. Layer 1 SBO Value Derivation
Derives `indicator_score` from `response_text`.
#### Indicator Scoring Scale

| indicator_score | interpretation |
|---|---|
| 0 | signal not present |
| 1 | signal weakly present |
| 2 | signal clearly present |
#### Indicator Evaluation Guidance

| indicator_id | indicator_definition | assessment_guidance |
|---|---|---|
| I1 | response explicitly assigns responsibility for an outcome | look for language such as “the engineer is responsible for…” |
| I2 | response identifies actors beyond the individual professional | references to institutions, teams, regulators, or systems |
| I3 | response describes where responsibility legitimately ends or transfers | phrases indicating responsibility hand-off |
| I4 | response references formal oversight structures | mention of regulation, governance, or review processes |
### 6. Layer 2 SBO Value Derivation
Derives `dimension_score` from indicator evidence.
#### Dimension Scoring Scale

| dimension_score | interpretation |
|---|---|
| 0 | weak conceptual evidence |
| 1 | partial conceptual articulation |
| 2 | strong conceptual articulation |
#### Indicator → Dimension Mapping

| dimension_id | contributing_indicators | rule |
|---|---|---|
| D1 | I1 | `dimension_score = max(I1)` |
| D2 | I2, I3 | `dimension_score = max(I2, I3)` |
| D3 | I4 | `dimension_score = max(I4)` |
### 7. Layer 3 SBO Value Derivation
Derives `component_score` from dimension evidence.
#### Component Performance Scale

| component_score | interpretation |
|---|---|
| exceeds_expectations | sophisticated analytic reasoning |
| meets_expectations | competent response |
| approaching_expectations | partially developed reasoning |
| below_expectations | weak or inconsistent reasoning |
| not_demonstrated | minimal or no relevant evidence |
#### Dimension → Component Mapping

| rule_id | condition | component_score |
|---|---|---|
| R1 | all `dimension_score ≥ 2` | exceeds_expectations |
| R2 | all `dimension_score ≥ 1` | meets_expectations |
| R3 | at least one `dimension_score = 1` | approaching_expectations |
| R4 | all `dimension_score = 0` | below_expectations |
| R5 | response missing or blank | not_demonstrated |
### 8. Layer 4 SBO Value Derivation
Derives `submission_score` from component scores.
#### Submission Performance Scale

| submission_score | interpretation |
|---|---|
| exceeds_expectations | exceptional submission |
| meets_expectations | overall competent submission |
| approaching_expectations | partially satisfactory submission |
| below_expectations | insufficient submission |
| not_demonstrated | no submission evidence |
#### Component Aggregation Rule

| rule_id | condition | submission_score |
|---|---|---|
| S1 | all `component_score ≥ meets_expectations` | meets_expectations |
| S2 | any `component_score = exceeds_expectations` and none below approaching | exceeds_expectations |
| S3 | any `component_score = approaching_expectations` | approaching_expectations |
| S4 | any `component_score = below_expectations` | below_expectations |
| S5 | all `component_score = not_demonstrated` | not_demonstrated |
### 9. Rubric Stability State

| rubric_section | state |
|---|---|
| Layer 1 SBO Instances | Stabilised |
| Layer 1 Value Derivation | Stabilised |
| Layer 2 SBO Instances | Stabilised |
| Layer 2 Value Derivation | Stabilised |
| Layer 3 SBO Instances | Stabilised |
| Layer 3 Value Derivation | Stabilised |
| Layer 4 SBO Instances | Stabilised |
| Layer 4 Value Derivation | Stabilised |
### 10. Example Evaluation Row
Example scoring output for one response.

| submission_id | component_id | I1 | I2 | I3 | I4 | D1 | D2 | D3 | component_score |
|---|---|---|---|---|---|---|---|---|---|
| 108234 | SectionAResponse | 2 | 2 | 1 | 1 | 2 | 2 | 1 | meets_expectations |
