### `Layer1_ScoringManifest_v01` Schema
#### Purpose
This artefact defines the **component-specific scoring job contract** for **Layer 1 SBO scoring**.
It identifies:
- the assessment and component in scope
- the canonical assessment artefacts and evidence surface
- the exact Layer 1 SBO instances to be scored
- the exact Layer 1 value-derivation rows to be used
- the expected runtime dataset contract
- the expected output dataset contract
This manifest is designed to let a **Layer 1 SBO scoring-prompt wrapper** generate a component-specific scoring prompt **without inferring component scope from the global rubric payload**.
#### Recommended filename pattern
```text
RUN_<ASSESSMENT_ID>_<COMPONENT_ID>_Layer1_ScoringManifest_v01.md
```
Example:
```text
RUN_PPP_SectionAResponse_Layer1_ScoringManifest_v01.md
```
#### Required top-level sections
The manifest must contain these sections in this order:
```text
1. Manifest Metadata
2. Scoring Job Scope
3. Runtime Input Contract
4. Layer 1 SBO Instances in Scope
5. Layer 1 Value-Derivation Rows in Scope
6. Runtime Output Contract
7. Validation Rules
```
### 1. Manifest Metadata
This section identifies the manifest artefact and its role.
Required table schema:

| field | value |
|---|---|
| `manifest_id` | unique manifest identifier |
| `manifest_version` | manifest version token |
| `assessment_id` | assessment identifier |
| `component_id` | canonical component identifier |
| `layer` | fixed value `Layer1` |
| `manifest_role` | fixed value `component_scoring_job_contract` |
| `status` | lifecycle status such as `draft`, `stabilised`, or `frozen` |
Example:

| field | value |
|---|---|
| `manifest_id` | `RUN_PPP_SectionAResponse_Layer1_ScoringManifest_v01` |
| `manifest_version` | `v01` |
| `assessment_id` | `PPP` |
| `component_id` | `SectionAResponse` |
| `layer` | `Layer1` |
| `manifest_role` | `component_scoring_job_contract` |
| `status` | `draft` |
### 2. Scoring Job Scope
This section defines the scoring scope and authoritative sources.
Required table schema:

| field | value |
|---|---|
| `aa_scope` | assessment artefact definition |
| `evidence_surface` | canonical evidence field |
| `target_score_name` | fixed value `indicator_score` |
| `target_scale_name` | fixed value `indicator_evidence_scale` |
| `allowed_scale_values` | ordered allowed values |
| `assignment_payload_source` | authoritative payload artefact |
| `rubric_instances_source` | authoritative Layer 1 instance source |
| `rubric_value_derivation_source` | authoritative Layer 1 value-derivation source |
Example:

| field | value |
|---|---|
| `aa_scope` | `submission_id × component_id` |
| `evidence_surface` | `response_text` |
| `target_score_name` | `indicator_score` |
| `target_scale_name` | `indicator_evidence_scale` |
| `allowed_scale_values` | `evidence, partial_evidence, little_to_no_evidence` |
| `assignment_payload_source` | `PPP_AssignmentPayloadSpec_v01` |
| `rubric_instances_source` | `Rubric Template: 5.4 Layer 1 SBO Instances` |
| `rubric_value_derivation_source` | `Rubric Template: 6.1 Layer 1 SBO Value Derivation` |
### 3. Runtime Input Contract
This section defines the dataset the scoring prompt will consume.
Required table schema:

| field | value |
|---|---|
| `runtime_input_dataset_id` | identifier of the scoring dataset |
| `expected_component_id` | canonical component identifier |
| `required_input_columns` | exact required columns |
| `response_field` | fixed response field |
| `component_filter_rule` | component restriction rule |
| `wrapper_handling_rule` | wrapper interpretation rule |
| `row_unit` | runtime row unit |
Example:

| field | value |
|---|---|
| `runtime_input_dataset_id` | `CAL_PPP_SectionAResponse_Layer1_dataset_v01` |
| `expected_component_id` | `SectionAResponse` |
| `required_input_columns` | `submission_id, component_id, response_text` |
| `response_field` | `response_text` |
| `component_filter_rule` | `all input rows must satisfy component_id = SectionAResponse` |
| `wrapper_handling_rule` | `apply wrapper-handling rules from PPP_AssignmentPayloadSpec_v01 before evaluation` |
| `row_unit` | `one row = one submission_id × component_id instance` |
Optional additional table for input column registry:

| column_name | role | required |
|---|---|---|
| `submission_id` | row identifier | `true` |
| `component_id` | component scope identifier | `true` |
| `response_text` | evidence surface | `true` |
### 4. Layer 1 SBO Instances in Scope
This section enumerates the exact Layer 1 SBOs that the generated scoring prompt must score.
Required table schema:

| sbo_identifier | sbo_identifier_shortid | submission_id | component_id | indicator_id | sbo_short_description |
|---|---|---|---|---|---|
Rules:
- include only rows for the manifest’s `component_id`
- include every in-scope Layer 1 SBO exactly once
- row order must be increasing by `indicator_id`
- this table is the authoritative in-scope indicator registry for the scoring job
Example:

| sbo_identifier | sbo_identifier_shortid | submission_id | component_id | indicator_id | sbo_short_description |
|---|---|---|---|---|---|
| `I_PPP_SecA_I01` | `I01` | `PPP` | `SectionAResponse` | `I01` | `distributed responsibility attribution` |
| `I_PPP_SecA_I02` | `I02` | `PPP` | `SectionAResponse` | `I02` | `individual responsibility attribution` |
| `I_PPP_SecA_I03` | `I03` | `PPP` | `SectionAResponse` | `I03` | `responsibility hand-off articulation` |
### 5. Layer 1 Value-Derivation Rows in Scope
This section enumerates the exact evaluation-specification rows corresponding to the in-scope Layer 1 SBOs.
Required table schema:

| sbo_identifier | indicator_id | sbo_short_description | indicator_definition | assessment_guidance | evaluation_notes |
|---|---|---|---|---|---|
Rules:
- include exactly one row for each `sbo_identifier` listed in Section 4
- `sbo_identifier` values must match Section 4 exactly
- `indicator_id` values must match Section 4 exactly
- `sbo_short_description` values must match Section 4 exactly
- row order must match Section 4
- this table is the authoritative evaluation-specification slice for the scoring job
Example:

| sbo_identifier | indicator_id | sbo_short_description | indicator_definition | assessment_guidance | evaluation_notes |
|---|---|---|---|---|---|
| `I_PPP_SecA_I01` | `I01` | `distributed responsibility attribution` | `Detects statements that assign responsibility across multiple actors such as individuals, teams, institutions, or tools.` | `Look for language indicating that responsibility is shared, layered, or distributed across different actors involved in the work.` | `Do not assign evidence when the response mentions teamwork without attributing responsibility across actors.` |
| `I_PPP_SecA_I02` | `I02` | `individual responsibility attribution` | `Detects statements that place accountability primarily on the individual professional.` | `Look for explicit claims that responsibility rests mainly with the individual, especially for one’s own actions, tasks, or code.` | `Do not assign evidence merely because a response uses first-person language; the response must explicitly attribute responsibility to the individual.` |
### 6. Runtime Output Contract
This section defines the exact output schema the generated scoring prompt must produce.
Required table schema:

| field | value |
|---|---|
| `output_format` | output serialization |
| `output_header_required` | whether header row is required |
| `output_row_unit` | evaluation row unit |
| `required_output_columns` | exact ordered columns |
| `confidence_mode` | confidence policy |
| `flags_mode` | flags policy |
| `evidence_quote_mode` | quoted-fragment output policy |
Example:

| field | value |
|---|---|
| `output_format` | `csv` |
| `output_header_required` | `true` |
| `output_row_unit` | `one row per submission_id × component_id × indicator_id` |
| `required_output_columns` | `submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags` |
| `confidence_mode` | `enabled` |
| `flags_mode` | `enabled` |
| `evidence_quote_mode` | `disabled_by_default` |
Optional output column registry:

| column_name | role | required |
|---|---|---|
| `submission_id` | submission identifier | `true` |
| `component_id` | component identifier | `true` |
| `indicator_id` | indicator identifier | `true` |
| `evidence_status` | Layer 1 score | `true` |
| `evaluation_notes` | brief diagnostic note | `true` |
| `confidence` | optional confidence value | `true` |
| `flags` | review flag | `true` |
### 7. Validation Rules
This section defines machine-checkable consistency rules for the manifest.
Required table schema:

| rule_id | validation_rule |
|---|---|
Recommended rules:

| rule_id | validation_rule |
|---|---|
| `V01` | `assessment_id` must match the assessment referenced in all cited artefacts |
| `V02` | `component_id` must match the component value in every row of Section 4 |
| `V03` | every row in Section 4 must have a unique `sbo_identifier` |
| `V04` | every row in Section 4 must have a unique `indicator_id` |
| `V05` | Section 5 must contain exactly one row for every `sbo_identifier` in Section 4 |
| `V06` | `sbo_identifier`, `indicator_id`, and `sbo_short_description` must match between Sections 4 and 5 |
| `V07` | `required_input_columns` must include `submission_id`, `component_id`, and `response_text` |
| `V08` | `required_output_columns` must exactly match the scoring prompt output contract |
| `V09` | all allowed scale values must belong to `indicator_evidence_scale` |
| `V10` | no Layer 1 SBO outside the target `component_id` may appear in Sections 4 or 5 |
### Complete manifest template
```md
### 1. Manifest Metadata

| field | value |
|---|---|
| `manifest_id` | `RUN_<ASSESSMENT_ID>_<COMPONENT_ID>_Layer1_ScoringManifest_v01` |
| `manifest_version` | `v01` |
| `assessment_id` | `<ASSESSMENT_ID>` |
| `component_id` | `<COMPONENT_ID>` |
| `layer` | `Layer1` |
| `manifest_role` | `component_scoring_job_contract` |
| `status` | `draft` |
### 2. Scoring Job Scope

| field | value |
|---|---|
| `aa_scope` | `submission_id × component_id` |
| `evidence_surface` | `response_text` |
| `target_score_name` | `indicator_score` |
| `target_scale_name` | `indicator_evidence_scale` |
| `allowed_scale_values` | `evidence, partial_evidence, little_to_no_evidence` |
| `assignment_payload_source` | `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01` |
| `rubric_instances_source` | `Rubric Template: 5.4 Layer 1 SBO Instances` |
| `rubric_value_derivation_source` | `Rubric Template: 6.1 Layer 1 SBO Value Derivation` |
### 3. Runtime Input Contract

| field | value |
|---|---|
| `runtime_input_dataset_id` | `CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Layer1_dataset_v01` |
| `expected_component_id` | `<COMPONENT_ID>` |
| `required_input_columns` | `submission_id, component_id, response_text` |
| `response_field` | `response_text` |
| `component_filter_rule` | `all input rows must satisfy component_id = <COMPONENT_ID>` |
| `wrapper_handling_rule` | `apply wrapper-handling rules from <ASSESSMENT_ID>_AssignmentPayloadSpec_v01 before evaluation` |
| `row_unit` | `one row = one submission_id × component_id instance` |

| column_name | role | required |
|---|---|---|
| `submission_id` | row identifier | `true` |
| `component_id` | component scope identifier | `true` |
| `response_text` | evidence surface | `true` |
### 4. Layer 1 SBO Instances in Scope

| sbo_identifier | sbo_identifier_shortid | submission_id | component_id | indicator_id | sbo_short_description |
|---|---|---|---|---|---|
| `<I_sid_cid_iid_01>` | `<iid_01>` | `<ASSESSMENT_ID>` | `<COMPONENT_ID>` | `<iid_01>` | `<short_description_01>` |
| `<I_sid_cid_iid_02>` | `<iid_02>` | `<ASSESSMENT_ID>` | `<COMPONENT_ID>` | `<iid_02>` | `<short_description_02>` |
### 5. Layer 1 Value-Derivation Rows in Scope

| sbo_identifier | indicator_id | sbo_short_description | indicator_definition | assessment_guidance | evaluation_notes |
|---|---|---|---|---|---|
| `<I_sid_cid_iid_01>` | `<iid_01>` | `<short_description_01>` | `<indicator_definition_01>` | `<assessment_guidance_01>` | `<evaluation_notes_01>` |
| `<I_sid_cid_iid_02>` | `<iid_02>` | `<short_description_02>` | `<indicator_definition_02>` | `<assessment_guidance_02>` | `<evaluation_notes_02>` |
### 6. Runtime Output Contract

| field | value |
|---|---|
| `output_format` | `csv` |
| `output_header_required` | `true` |
| `output_row_unit` | `one row per submission_id × component_id × indicator_id` |
| `required_output_columns` | `submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags` |
| `confidence_mode` | `enabled` |
| `flags_mode` | `enabled` |
| `evidence_quote_mode` | `disabled_by_default` |

| column_name | role | required |
|---|---|---|
| `submission_id` | submission identifier | `true` |
| `component_id` | component identifier | `true` |
| `indicator_id` | indicator identifier | `true` |
| `evidence_status` | Layer 1 score | `true` |
| `evaluation_notes` | brief diagnostic note | `true` |
| `confidence` | confidence value | `true` |
| `flags` | review flag | `true` |
### 7. Validation Rules

| rule_id | validation_rule |
|---|---|
| `V01` | `assessment_id` must match the assessment referenced in all cited artefacts |
| `V02` | `component_id` must match the component value in every row of Section 4 |
| `V03` | every row in Section 4 must have a unique `sbo_identifier` |
| `V04` | every row in Section 4 must have a unique `indicator_id` |
| `V05` | Section 5 must contain exactly one row for every `sbo_identifier` in Section 4 |
| `V06` | `sbo_identifier`, `indicator_id`, and `sbo_short_description` must match between Sections 4 and 5 |
| `V07` | `required_input_columns` must include `submission_id`, `component_id`, and `response_text` |
| `V08` | `required_output_columns` must exactly match the scoring prompt output contract |
| `V09` | all allowed scale values must belong to `indicator_evidence_scale` |
| `V10` | no Layer 1 SBO outside the target `component_id` may appear in Sections 4 or 5 |
```
### Recommendation for your pipeline
For your setup, I would make this manifest a required upstream input to the **Stage 1.3 / Layer 1 SBO scoring prompt wrapper** and stop giving that wrapper the full global `5.4` and `6.1` sections directly.
