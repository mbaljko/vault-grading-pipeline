## rubric_definition.md
#### `rubric_definition`

The `rubric_definition` worksheet defines the authoritative dimension structure used in Stage 0B expansion.

The worksheet must be structured as a flat table with one row per:

`component_id × dimension_id`

### Required Columns

| column_name     | type   | description                                                |
|-----------------|--------|------------------------------------------------------------|
| component_id    | string | Must match `component_id` values in Stage 0A snapshot     |
| dimension_id    | string | Stable, short rubric identifier (e.g., D1, D2, D3)        |

### Recommended Columns

| column_name     | type   | description                                                |
|-----------------|--------|------------------------------------------------------------|
| dimension_order | int    | Determines deterministic ordering within component        |
| dimension_label | string | Human-readable rubric label (not used for identity)      |
| rubric_version  | string | Optional version tag (e.g., `PPP_v1_2026W`)              |

### Starter Template (Example)

| component_id     | dimension_id | dimension_order | dimension_label        |
| ---------------- | ------------ | --------------- | ---------------------- |
| SectionAResponse | D1           | 1               | Structural Positioning |
| SectionAResponse | D2           | 2               | Governance Analysis    |
| SectionAResponse | D3           | 3               | Residual Uncertainty   |
| SectionAResponse | D4           | 4               | Justice Framing        |
SectionBResponse | D1 | 1 | Structural Positioning
SectionBResponse | D2 | 2 | Governance Analysis
SectionBResponse | D3 | 3 | Residual Uncertainty
SectionBResponse | D4 | 4 | Justice Framing

### Deterministic Requirements

1. Every `component_id` present in the Stage 0A snapshot must appear in this table.
2. Every component must list all intended `dimension_id` values explicitly.
3. `dimension_id` values must be stable and not change across runs unless the rubric itself changes.
4. `dimension_order` must define deterministic ordering for Stage 0B output.
5. There must be no duplicate `(component_id, dimension_id)` pairs.

Stage 0B will perform a deterministic expansion:

`submission_id × component_id`  
→  
`submission_id × component_id × dimension_id`

This worksheet is the sole authoritative source for dimension expansion.