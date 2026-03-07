# Rubric Template
### Purpose
Defines the scoring structure used to evaluate assessment submissions.
The rubric operates under the **four-layer scoring ontology**.

| layer | SBO |
|---|---|
| Layer 1 | indicator |
| Layer 2 | dimension |
| Layer 3 | component |
| Layer 4 | submission |
# 1. Layer 4 SBO Registry

| field |
|---|
| `submission_score` |
# 2. Layer 3 SBO Registry

| field |
|---|
| `component_score` |
# 3. Layer 2 SBO Registry

| field |
|---|
| `dimension_score` |
# 4. Layer 1 SBO Registry

| field |
|---|
| `indicator_score` |
# 5. SBO Instance Registries
### 5.4 Layer 1 SBO Instances
Registry of indicator SBO instances.
### 5.3 Layer 2 SBO Instances
Registry of dimension SBO instances.
### 5.2 Layer 3 SBO Instances
Registry of component SBO instances.
### 5.1 Layer 4 SBO Instances
Registry of submission SBO instances.
# 6. SBO Value Derivation Registries
### 6.1 Layer 1 Value Derivation
Derives `indicator_score` from `response_text`.
### 6.2 Layer 2 Value Derivation
Derives `dimension_score` from indicator evidence.
### 6.3 Layer 3 Value Derivation
Derives `component_score` from dimension evidence.
### 6.4 Layer 4 Value Derivation
Derives `submission_score` from component scores.
# 7. Scoring Ontology
Evaluation hierarchy

| entity |
|---|
| submission |
| component |
| dimension |
| indicator |
Assessment artefact:
`submission_id × component_id`
# 8. Rubric Stability States

| state            |
| ---------------- |
| Draft            |
| Under Evaluation |
| Stabilised       |
| Frozen           |
