## Pipeline_1B_Layered_Rubric_Construction_Pipeline
### 0. Purpose
Pipeline 1B defines the process for constructing and stabilising a rubric for an assessment submission under the **four-layer scoring ontology**.

| layer | score-bearing object (SBO) |
|---|---|
| Layer 1 | indicator SBO |
| Layer 2 | dimension SBO |
| Layer 3 | component SBO |
| Layer 4 | submission SBO |
Rubric construction proceeds **layer by layer**, using empirical evidence from real student responses.
The pipeline produces a rubric specification stored in the **Rubric Template**.
Calibration pipelines operate only **after the rubric is stabilised and frozen**.
### 1. Upstream Inputs
#### Required Artefact Registry

| artefact | description |
|---|---|
| `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01` | canonical dataset and payload structure |
Rubric construction must remain fully compatible with this specification.
#### Canonical Identifier Registry

| field | type |
|---|---|
| `submission_id` | integer |
| `component_id` | string |
#### Evidence Surface Registry

| field | evidentiary_status |
|---|---|
| `response_text` | evidence |
#### Canonical Scoring Unit
`submission_id × component_id`
### 2. Layer Construction Pattern
Each rubric layer is constructed using the same pattern.
#### Layer Construction Structure

| block | purpose |
|---|---|
| Purpose | define what the layer represents |
| Inputs | information used to build the layer |
| Rubric Sections | template sections modified |
| Process | iterative empirical development |
| Exit Condition | stability criteria |
| Deliverables | stabilised rubric sections |
### 3. Layer 1 — Indicator Construction
#### Purpose
Detect observable textual signals in student responses.
#### Inputs
- Submission analytic brief  
- analytic sub-spaces  
- calibration dataset  
Assessment artefact: `AA = submission_id × component_id`
#### Rubric Sections

| section |
|---|
| `5.4 Layer 1 SBO Instances` |
| `6.1 Layer 1 SBO Value Derivation` |
#### Process

| step | operation |
|---|---|
| 1 | instantiate indicator SBOs |
| 2 | define evaluation guidance |
| 3 | generate indicator scoring prompts |
| 4 | test on calibration sample |
| 5 | revise indicators or evaluation guidance |
#### Exit Condition
Indicator behaviour is stable and produces consistent `indicator_score`.
#### Deliverables

| artefact |
|---|
| stabilised indicator registry |
| stabilised indicator value derivation rules |
### 4. Layer 2 — Dimension Construction
#### Purpose
Translate indicator evidence into conceptual evaluation criteria.
#### Inputs
- indicator scoring dataset  
- analytic sub-spaces  
- candidate dimensions  
#### Rubric Sections

| section |
|---|
| `5.3 Layer 2 SBO Instances` |
| `6.2 Layer 2 SBO Value Derivation` |
#### Process

| step | operation |
|---|---|
| 1 | define dimension SBO instances |
| 2 | define indicator→dimension mappings |
| 3 | compute dimension scores |
| 4 | examine score distributions |
| 5 | revise mappings or dimensions |
#### Exit Condition
Dimension scores correspond to meaningful conceptual distinctions.
#### Deliverables

| artefact |
|---|
| stabilised dimension registry |
| stabilised dimension mapping rules |
### 5. Layer 3 — Component Scoring
#### Purpose
Translate dimension evidence into component performance levels.
#### Inputs
- dimension scoring dataset  
- component performance model  
#### Rubric Sections

| section |
|---|
| `5.2 Layer 3 SBO Instances` |
| `6.3 Layer 3 SBO Value Derivation` |
#### Process

| step | operation |
|---|---|
| 1 | apply dimension→component mapping |
| 2 | compute component scores |
| 3 | compare with human judgement |
| 4 | revise mapping rules |
#### Exit Condition
Component scores correspond to holistic judgement of response quality.
#### Deliverables

| artefact |
|---|
| stabilised component SBO registry |
| stabilised component mapping rules |
### 6. Layer 4 — Submission Scoring
#### Purpose
Combine component scores into a final submission score.
#### Inputs
- component scoring dataset  
#### Rubric Sections

| section |
|---|
| `5.1 Layer 4 SBO Instances` |
| `6.4 Layer 4 SBO Value Derivation` |
#### Process

| step | operation |
|---|---|
| 1 | apply component aggregation rules |
| 2 | compute submission scores |
| 3 | examine distribution |
#### Exit Condition
Submission scores behave consistently across the dataset.
#### Deliverables

| artefact |
|---|
| stabilised submission SBO registry |
| stabilised submission aggregation rules |
### 7. Rubric Freeze
When all layers are stabilised, the rubric becomes production-ready.
#### Frozen Sections

| rubric section |
|---|
| `5.4 Layer 1 SBO Instances` |
| `6.1 Layer 1 SBO Value Derivation` |
| `5.3 Layer 2 SBO Instances` |
| `6.2 Layer 2 SBO Value Derivation` |
| `5.2 Layer 3 SBO Instances` |
| `6.3 Layer 3 SBO Value Derivation` |
| `5.1 Layer 4 SBO Instances` |
| `6.4 Layer 4 SBO Value Derivation` |
#### Output Artefacts

| artefact |
|---|
| Rubric Design Document |
| `RUBRIC_<ASSESSMENT_ID>_PROD_payload_v01` |
