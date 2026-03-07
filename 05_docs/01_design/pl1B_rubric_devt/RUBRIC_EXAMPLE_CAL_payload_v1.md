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
# 5. SBO Instance Registries
## 5.4 Layer 1 SBO Instances

| sbo_identifier | sbo_identifier_shortid | submission_id | component_id | indicator_id | sbo_short_description |
|---|---|---|---|---|---|
| `I_PPP_SectionAResponse_I01` | `I01` | `PPP` | `SectionAResponse` | `I01` | explicit assignment of responsibility |
| `I_PPP_SectionAResponse_I02` | `I02` | `PPP` | `SectionAResponse` | `I02` | recognition of distributed responsibility |
| `I_PPP_SectionAResponse_I03` | `I03` | `PPP` | `SectionAResponse` | `I03` | articulation of role boundary |
| `I_PPP_SectionAResponse_I04` | `I04` | `PPP` | `SectionAResponse` | `I04` | reference to institutional oversight |
| `P_PPP_Global_I05` | `P01` | `PPP` | `Global` | `I05` | cross-component consistency of responsibility reasoning |
| `P_PPP_Global_I06` | `P02` | `PPP` | `Global` | `I06` | coherence of professional obligation claims across components |
## 5.3 Layer 2 SBO Instances

| sbo_identifier | sbo_identifier_shortid | submission_id | component_id | dimension_id | sbo_short_description |
|---|---|---|---|---|---|
| `D_PPP_SectionAResponse_D01` | `D01` | `PPP` | `SectionAResponse` | `D01` | clarity of responsibility attribution |
| `D_PPP_SectionAResponse_D02` | `D02` | `PPP` | `SectionAResponse` | `D02` | recognition of distributed accountability |
| `D_PPP_SectionAResponse_D03` | `D03` | `PPP` | `SectionAResponse` | `D03` | articulation of professional obligations |
| `Q_PPP_Global_D04` | `Q01` | `PPP` | `Global` | `D04` | cross-component conceptual coherence |
| `Q_PPP_Global_D05` | `Q02` | `PPP` | `Global` | `D05` | consistency of responsibility reasoning across responses |
## 5.2 Layer 3 SBO Instances

| sbo_identifier | sbo_identifier_shortid | submission_id | component_id | sbo_short_description |
|---|---|---|---|---|
| `C_PPP_SecA` | `C01` | `PPP` | `SectionAResponse` | component performance for Section A |
## 5.1 Layer 4 SBO Instances

| sbo_identifier | sbo_identifier_shortid | submission_id | sbo_short_description          |
| -------------- | ---------------------- | ------------- | ------------------------------ |
| `S_PPP`        | `S01`                  | `PPP`         | overall submission performance |
# 6. SBO Value Derivation Registries
## 6.1 Layer 1 Value Derivation
Derives `indicator_score` from `response_text`.
### Indicator Evaluation Guidance

| indicator_id | indicator_definition | assessment_guidance |
|---|---|---|
| `I01` | response explicitly assigns responsibility for an outcome | language such as “the engineer is responsible for…” |
| `I02` | response identifies actors beyond the individual professional | references to institutions, teams, regulators, or systems |
| `I03` | response describes where responsibility legitimately ends or transfers | statements describing responsibility hand-off |
| `I04` | response references formal oversight structures | mention of regulation, governance, or review processes |
| `I05` | reasoning about responsibility remains consistent across components | evaluate conceptual consistency |
| `I06` | claims about professional obligation remain coherent across responses | compare reasoning across sections |
## 6.2 Layer 2 Value Derivation
Derives `dimension_score` from indicator evidence.
### Indicator → Dimension Mapping Table

| resultant scale value | I01 | I02 | I03 | I04 |
|---|---|---|---|---|
| demonstrated | evidence | evidence | partial_evidence | partial_evidence |
| partially_demonstrated | partial_evidence | partial_evidence | little_to_no_evidence | * |
| little_to_no_demonstration | little_to_no_evidence | little_to_no_evidence | little_to_no_evidence | little_to_no_evidence |
### Cross-component Indicator → Dimension Mapping

| resultant scale value | P01 | P02 |
|---|---|---|
| demonstrated | evidence | evidence |
| partially_demonstrated | partial_evidence | partial_evidence |
| little_to_no_demonstration | little_to_no_evidence | little_to_no_evidence |
## 6.3 Layer 3 Value Derivation
Derives `component_score` from dimension evidence.
### Dimension → Component Mapping Table

| resultant scale value    | D01                        | D02                        | D03                        |
| ------------------------ | -------------------------- | -------------------------- | -------------------------- |
| exceeds_expectations     | demonstrated               | demonstrated               | demonstrated               |
| meets_expectations       | partially_demonstrated     | partially_demonstrated     | partially_demonstrated     |
| approaching_expectations | partially_demonstrated     | little_to_no_demonstration | little_to_no_demonstration |
| below_expectations       | little_to_no_demonstration | little_to_no_demonstration | little_to_no_demonstration |
