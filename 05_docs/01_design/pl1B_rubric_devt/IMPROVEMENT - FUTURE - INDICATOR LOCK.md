### Design Document — Optional Indicator Lock Mechanism for Layer 1 SBO Scoring
#### Purpose
This document describes an **optional stabilisation mechanism** for Layer 1 SBO scoring called the **Indicator Lock Mechanism** (or **Indicator Lock Table**).
The mechanism is designed to improve reliability and determinism in rubric pipelines where a large number of indicators must be evaluated in a single scoring pass.
The mechanism is **not required** for the current PPP scoring configuration but is documented here so that it can be introduced later if the scoring architecture evolves.
### Context
Layer 1 SBO scoring evaluates indicator evidence for the canonical scoring unit:
```
AA = submission_id × component_id
```
The evaluator must assign an `evidence_status` for each indicator SBO instance defined in the Layer 1 scoring manifest.
Current pipeline behaviour:
```
component-level scoring
≈ 8 indicators evaluated per run
```
Because the scoring task is small and tightly constrained, reliability is already high.
However, as indicator sets grow larger, LLM evaluators can exhibit several failure modes.
### Failure Modes Addressed
The Indicator Lock Mechanism mitigates the following issues:
#### 1. Indicator Skipping
The model silently omits one or more indicators from evaluation.
Typical cause:
```
large indicator registry
+ sequential reasoning
+ attention drift
```
Symptom:
```
fewer output rows than expected
```
#### 2. Indicator Duplication
The model accidentally evaluates an indicator twice and omits another.
Symptom:
```
duplicate indicator_id rows
missing indicator_id rows
```
#### 3. Indicator Definition Drift
Indicator definitions subtly shift as the evaluator progresses through the prompt.
Example:
```
I01 interpreted strictly
I06 interpreted loosely
```
This occurs when the evaluator reinterprets indicator definitions while writing output rows.
#### 4. Sequential Output Bias
When the evaluator writes rows sequentially, earlier reasoning may influence later indicators.
Example:
```
indicator I01 reasoning implicitly influences I02
```
This reduces indicator independence.
### Design Principle
The Indicator Lock Mechanism separates **indicator enumeration** from **indicator evaluation**.
The evaluator must first **commit to the complete indicator set** before any scoring decisions are emitted.
This ensures:
```
indicator completeness
indicator ordering stability
evaluation independence
```
### Indicator Lock Table Concept
Before evaluating any indicators, the evaluator constructs an **internal table** containing the complete indicator set.
Example internal structure:
```
indicator_id | evaluation_state
--------------------------------
I01 | pending
I02 | pending
I03 | pending
I04 | pending
I05 | pending
I06 | pending
I07 | pending
I08 | pending
```
The evaluator then updates this table as indicators are evaluated.
Example after evaluation:
```
indicator_id | evidence_status
--------------------------------
I01 | evidence
I02 | little_to_no_evidence
I03 | partial_evidence
I04 | evidence
I05 | little_to_no_evidence
I06 | evidence
I07 | partial_evidence
I08 | little_to_no_evidence
```
Only **after the table is complete** may the evaluator emit output rows.
### Operational Workflow
The scoring procedure becomes:
```
1  read scoring manifest
2  construct indicator lock table
3  initialise all indicators with state = pending
4  evaluate each indicator
5  update table with evidence_status
6  verify table completeness
7  emit output rows in manifest order
```
Output rows are generated **after all indicators have been evaluated**.
### Indicator Lock Rule (Prompt Instruction)
If the mechanism is activated, the scoring prompt should include a rule similar to the following.
```
Indicator Lock Rule
Before evaluating any indicators, construct an internal Indicator Lock Table
containing one row for each indicator_id embedded in the prompt.
Each row must initially contain:
indicator_id
evaluation_state = pending
The evaluator must then evaluate indicators and update the table.
No output rows may be written until all indicators have been evaluated.
After the table is complete, emit CSV rows in manifest order.
```
### Relationship to the Manifest Architecture
The mechanism integrates naturally with the existing manifest system.
Indicator set source:
```
Layer1_ScoringManifest_<ASSESSMENT_ID>
```
The lock table simply mirrors the manifest rows.
Example mapping:

| Manifest Field | Lock Table Field |
|---|---|
| indicator_id | indicator_id |
| sbo_identifier | reference metadata |
| evaluation_state | internal scoring state |
The lock table does not modify the manifest.
### Expected Benefits
The mechanism improves scoring behaviour in the following ways:

| Benefit | Description |
|---|---|
| Indicator completeness | prevents skipped indicators |
| Output stability | ensures correct row counts |
| Reduced reasoning drift | fixes the indicator inventory before reasoning |
| Better calibration reproducibility | indicator interpretation stabilises across runs |
### Computational Cost
The mechanism adds a small reasoning overhead because the evaluator must maintain an internal table.
Estimated impact:
```
+ small prompt complexity
+ minor additional reasoning steps
```
However, it does **not increase output size** because the table is not emitted.
### When to Activate
The mechanism becomes beneficial when:
```
indicator_count ≥ 20
```
or when any of the following occur:
```
multi-component scoring in a single prompt
indicator registries > 15 indicators
observed skipped indicator rows
observed duplicated indicators
```
### When It Is Not Necessary
The mechanism is usually unnecessary when:
```
indicator_count ≤ 10
component-scoped scoring
strict row-count validation exists
```
This is the case for the current PPP configuration.
### Compatibility With Existing Pipeline
The mechanism is fully compatible with the current architecture:
```
AssignmentPayloadSpec
Layer1_ScoringManifest
Layer1 scoring prompt
CSV output schema
```
No structural changes are required.
Only the **scoring prompt instructions** change.
### Optional Extension — Evidence Index
The lock mechanism can optionally be extended with an **Evidence Index**.
Example internal structure:
```
indicator_id | evidence_fragment
--------------------------------
I01 | "... engineers share responsibility ..."
I02 | null
I03 | "... responsibility moves from developer to management ..."
```
This allows:
```
audit trails
quality review
scoring traceability
```
The pipeline already supports this through:
```
FRAGMENT_OUTPUT_MODE = on
```
### Summary
The Indicator Lock Mechanism is an optional stabilisation technique that ensures:
```
complete indicator evaluation
stable indicator interpretation
deterministic scoring behaviour
```
For the current PPP configuration:
```
5 components
8 indicators per component
```
the mechanism is **not required**, but documenting it now allows easy activation if the rubric or scoring architecture expands in the future.
