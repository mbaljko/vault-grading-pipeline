## RUBRIC_EXAMPLE_CAL_payload_v01
### Purpose
Illustrates a **rubric payload instance** conforming to `Rubric_Template` and `Rubric_SpecificationGuide_v01`.
This rubric is for the assessment `EXAMPLE` and demonstrates both:
- **component-local evaluation** (`I`, `D`)
- **cross-component evaluation** (`P`, `Q`)
The rubric follows the **four-layer scoring ontology**.

| layer | SBO |
|---|---|
| Layer 1 | indicator |
| Layer 2 | dimension |
| Layer 3 | component |
| Layer 4 | submission |
Assessment artefact for Layers 1–3: `submission_id × component_id`  
Assessment artefact for Layer 4: `submission_id`
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
#### 5.4 Layer 1 SBO Instances

| sbo_identifier | sbo_identifier_shortid | submission_id | component_id | indicator_id | sbo_short_description |
|---|---|---|---|---|---|
| `I_PPP_SectionAResponse_I1` | `I1` | `PPP` | `SectionAResponse` | `I1` | explicit assignment of responsibility |
| `I_PPP_SectionAResponse_I2` | `I2` | `PPP` | `SectionAResponse` | `I2` | recognition of distributed responsibility |
| `I_PPP_SectionAResponse_I3` | `I3` | `PPP` | `SectionAResponse` | `I3` | articulation of role boundary |
| `I_PPP_SectionAResponse_I4` | `I4` | `PPP` | `SectionAResponse` | `I4` | reference to institutional oversight |
| `P_PPP_Global_P1` | `P1` | `PPP` | `Global` | `P1` | cross-component consistency of responsibility reasoning |
| `P_PPP_Global_P2` | `P2` | `PPP` | `Global` | `P2` | coherence of professional obligation claims across components |
#### 5.3 Layer 2 SBO Instances

| sbo_identifier | sbo_identifier_shortid | submission_id | component_id | dimension_id | sbo_short_description |
|---|---|---|---|---|---|
| `D_PPP_SectionAResponse_D1` | `D1` | `PPP` | `SectionAResponse` | `D1` | clarity of responsibility attribution |
| `D_PPP_SectionAResponse_D2` | `D2` | `PPP` | `SectionAResponse` | `D2` | recognition of distributed accountability |
| `D_PPP_SectionAResponse_D3` | `D3` | `PPP` | `SectionAResponse` | `D3` | articulation of professional obligations |
| `Q_PPP_Global_Q1` | `Q1` | `PPP` | `Global` | `Q1` | cross-component conceptual coherence |
| `Q_PPP_Global_Q2` | `Q2` | `PPP` | `Global` | `Q2` | consistency of responsibility reasoning across responses |
#### 5.2 Layer 3 SBO Instances

| sbo_identifier           | sbo_identifier_shortid | submission_id | component_id       | sbo_short_description               |
| ------------------------ | ---------------------- | ------------- | ------------------ | ----------------------------------- |
| `C_PPP_SectionAResponse` | `C1`                   | `PPP`         | `SectionAResponse` | component performance for Section A |
#### 5.1 Layer 4 SBO Instances

| sbo_identifier | sbo_identifier_shortid | submission_id | sbo_short_description |
|---|---|---|---|
| `S_PPP` | `S1` | `PPP` | overall submission performance |
### 6. SBO Value Derivation Registries
#### 6.1 Layer 1 Value Derivation
Derives `indicator_score` from `response_text`.
##### Indicator Evaluation Guidance

| indicator_id | indicator_definition | assessment_guidance |
|---|---|---|
| `I1` | response explicitly assigns responsibility for an outcome | language such as “the engineer is responsible for…” |
| `I2` | response identifies actors beyond the individual professional | references to institutions, teams, regulators, or systems |
| `I3` | response describes where responsibility legitimately ends or transfers | statements describing responsibility hand-off |
| `I4` | response references formal oversight structures | mention of regulation, governance, or review processes |
| `P1` | reasoning about responsibility remains consistent across components | evaluate conceptual consistency |
| `P2` | claims about professional obligation remain coherent across responses | compare reasoning across sections |
#### 6.2 Layer 2 Value Derivation
Derives `dimension_score` from indicator evidence.
##### Indicator → Dimension Mapping Table

| resultant scale value | I1 | I2 | I3 | I4 |
|---|---|---|---|---|
| demonstrated | evidence | evidence | partial_evidence | partial_evidence |
| partially_demonstrated | partial_evidence | partial_evidence | little_to_no_evidence | * |
| little_to_no_demonstration | little_to_no_evidence | little_to_no_evidence | little_to_no_evidence | little_to_no_evidence |
##### Cross-component Indicator → Dimension Mapping

| resultant scale value | P1 | P2 |
|---|---|---|
| demonstrated | evidence | evidence |
| partially_demonstrated | partial_evidence | partial_evidence |
| little_to_no_demonstration | little_to_no_evidence | little_to_no_evidence |
#### 6.3 Layer 3 Value Derivation
Derives `component_score` from dimension evidence.
##### Dimension → Component Mapping Table

| resultant scale value | D1 | D2 | D3 |
|---|---|---|---|
| exceeds_expectations | demonstrated | demonstrated | demonstrated |
| meets_expectations | partially_demonstrated | partially_demonstrated | partially_demonstrated |
| approaching_expectations | partially_demonstrated | little_to_no_demonstration | little_to_no_demonstration |
| below_expectations | little_to_no_demonstration | little_to_no_demonstration | little_to_no_demonstration |
| not_demonstrated | * | * | * |
#### 6.4 Layer 4 Value Derivation
Derives `submission_score` from component scores and cross-component dimensions.
##### Component + Global Dimension Mapping

| resultant scale value | C1 | Q1 | Q2 |
|---|---|---|---|
| exceeds_expectations | exceeds_expectations | demonstrated | demonstrated |
| meets_expectations | meets_expectations | partially_demonstrated | partially_demonstrated |
| approaching_expectations | approaching_expectations | * | * |
| below_expectations | below_expectations | * | * |
| not_demonstrated | not_demonstrated | * | * |
### 7. Scoring Ontology

| entity |
|---|
| submission |
| component |
| dimension |
| indicator |
Assessment artefact for Layers 1–3: `submission_id × component_id`  
Assessment artefact for Layer 4: `submission_id`
### 8. Rubric Stability States

| state |
|---|
| Draft |
| Under Evaluation |
| Stabilised |
| Frozen |
### 9. Scale Registry

| scale_name | scale_type |
|---|---|
| `indicator_evidence_scale` | evidence |
| `dimension_evidence_scale` | evidence |
| `component_performance_scale` | performance |
| `submission_performance_scale` | performance |
### 10. Example Evaluation Row

| submission_id | component_id | I1 | I2 | I3 | I4 | P1 | P2 | D1 | D2 | D3 | Q1 | Q2 | C1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 108234 | SectionAResponse | evidence | evidence | partial_evidence | partial_evidence | evidence | partial_evidence | demonstrated | demonstrated | partially_demonstrated | demonstrated | partially_demonstrated | meets_expectations |
