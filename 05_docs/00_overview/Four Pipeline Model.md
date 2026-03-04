## Design Note
### Four-Pipeline Architecture for Course Grading Infrastructure
## 1. Purpose
This design note defines a four-pipeline architecture for grading work that separates:
- population preparation,
- rubric construction,
- calibration runs, and
- production grading runs.
The goal is to enforce clear handoffs, stable artefacts, and reproducible runs, while keeping rubric work and scoring work decoupled.
## 2. Pipeline List
The architecture contains four pipelines:
### 2.1 `pl1A_canonical_population_prep`
### 2.2 `pl1B_rubric_devt`
### 2.3 `pl2_calibration`
### 2.4 `pl3_grading_core`
## 3. Global Entity Model and Terms
### 3.1 Canonical Population
The canonical population is the set of eligible submissions, expressed as canonical grading targets.
Stage 0A output unit:
`submission_id × component_id`
### 3.2 Rubric
The rubric is a deterministic specification defining dimensions per component, including:
- stable identifiers,
- ordering,
- and version traceability.
Stage 0B expansion unit:
`submission_id × component_id × dimension_id`
### 3.3 Calibration Artefacts
Calibration artefacts are the interpretation and stabilisation layer:
- boundary rules,
- anchor banks,
- stability checks,
- and production scoring protocol.
Calibration produces a rubric interpretation regime, not grades.
### 3.4 Production Scoring Artefacts
Production artefacts include grading units and scoring outputs for the canonical population, plus QA and exports.
## 4. Pipeline Definitions
## 4.1 `pl1A_canonical_population_prep`
### 4.1.1 Purpose
Prepare a rubric-agnostic canonical dataset of grading targets for an assessment.
### 4.1.2 Inputs
- LMS submission export(s)
- grading worksheet export (eligibility / roster)
- optional institutional database export(s)
### 4.1.3 Core Transformations
- deterministic joins for eligibility filtering
- stable `submission_id` derivation
- component identification and long-format canonicalisation
- text cleaning and normalisation
- schema validation and deterministic ordering
### 4.1.4 Required Outputs
- frozen canonical grading target snapshot (Stage 0A)
- Stage 0A manifest pinned to `pipeline_commit`
- join / exclusion audit artefacts (as needed)
### 4.1.5 Completion Gate
Stage 0A is complete only when:
- canonical unit is `submission_id × component_id`
- primary key uniqueness holds
- scope coverage holds
- a frozen snapshot exists
- the manifest is fully static and snapshot-derived where required
## 4.2 `pl1B_rubric_devt`
### 4.2.1 Purpose
Construct and version a deterministic rubric definition suitable for Stage 0B expansion and downstream scoring.
This pipeline is responsible for producing a rubric artefact that is stable enough to be locked for grading runs.
### 4.2.2 Inputs
- course assessment design intent (rubric goals, dimensions, scale)
- prior rubric versions (if any)
- constraints from delivery (TA workflow, grading platform limits)
### 4.2.3 Core Transformations
- define `component_id` set for the assessment
- define `dimension_id` set per component
- define dimension ordering per component
- define scale labels and level meanings
- define versioning and change control mechanism
### 4.2.4 Required Outputs
- rubric definition dataset (`rubric_definition`) with stable IDs
- rubric version identifier (human-readable) and commit pin
- rubric schema documentation (field meanings, invariants)
### 4.2.5 Completion Gate
Rubric development is complete for a given version only when:
- all dimensions have stable identifiers
- component → dimension mapping is deterministic
- ordering is explicit
- the rubric artefact is versioned and reproducible
## 4.3 `pl2_calibration`
### 4.3.1 Purpose
Stabilise rubric interpretation by producing decision rules and anchors that make scoring repeatable.
Calibration does not grade the full population. It produces a locked interpretation regime that can be applied later.
### 4.3.2 Inputs
- a frozen Stage 0A snapshot (or component slice)
- a rubric definition version from `pl1B_rubric_devt`
### 4.3.3 Core Transformations
- build calibration sets (sampling)
- define or refine boundary rules
- create anchor banks (clean + borderline)
- run stability checks
- define production scoring protocol (`needs_review` triggers, pace, escalation rules)
### 4.3.4 Required Outputs
Per calibrated `component_id` and (if applicable) `dimension_id`:
- calibration set artefact(s)
- boundary rules artefact(s) with explicit hardest boundary
- anchor bank artefact(s)
- stability check note(s)
- production scoring protocol artefact
### 4.3.5 Completion Gate
Calibration is complete for a given rubric version only when:
- calibration sets are frozen and traceable
- boundary rules are explicit and operational
- anchors exist for each score level (minimum standard enforced by policy)
- stability check indicates acceptable repeatability
- the production protocol is written and frozen
### 4.3.6 Rubric Lock Event
Calibration culminates in a rubric lock event:
- the rubric definition version is declared locked for a grading run
- calibration artefacts are associated to that rubric version
- any further changes create a new rubric version and a new calibration cycle
## 4.4 `pl3_grading_core`
### 4.4.1 Purpose
Apply a locked rubric interpretation regime to the canonical population to produce grades deterministically.
### 4.4.2 Inputs
- frozen Stage 0A snapshot from `pl1A_canonical_population_prep`
- locked rubric definition version from `pl1B_rubric_devt`
- locked calibration artefacts and production protocol from `pl2_calibration`
### 4.4.3 Core Transformations
- Stage 0B expansion: targets → grading units
  - `submission_id × component_id × dimension_id`
- scoring over the full population using locked rules
- `needs_review` handling and escalation workflow
- QA checks (coverage, duplicates, missingness, ordering)
- export formatting for LMS grade upload and internal reporting
### 4.4.4 Required Outputs
- Stage 0B canonical grading unit dataset
- scoring outputs for the population
- QA and coverage reports
- export-ready grade upload artefacts
### 4.4.5 Completion Gate
A grading run is complete only when:
- Stage 0B coverage checks pass
- scoring outputs are complete and aligned to grading units
- QA checks pass or are documented exceptions
- exports are reproducible from the frozen run state
## 5. Handoff Contracts Between Pipelines
### 5.1 Handoff: `pl1A_canonical_population_prep` → `pl2_calibration`
Contract:
- calibration must use a frozen Stage 0A snapshot, not live query outputs
- calibration sets must reference stable identifiers from the snapshot
### 5.2 Handoff: `pl1B_rubric_devt` → `pl2_calibration`
Contract:
- calibration assumes a specific rubric version
- dimension identifiers and ordering must be stable
### 5.3 Handoff: `pl2_calibration` → `pl3_grading_core`
Contract:
- grading core uses only locked calibration artefacts
- any changes to rules or dimension structure require a new rubric version and new calibration cycle
### 5.4 Handoff: `pl1A_canonical_population_prep` + `pl1B_rubric_devt` → `pl3_grading_core`
Contract:
- Stage 0B requires both:
  - canonical targets snapshot (Stage 0A)
  - rubric definition dataset (locked version)
- grading units must be reproducible from these inputs
## 6. Run Identity and Version Pinning
Each run must pin:
- course + assessment identifiers
- run date (or run ID)
- canonical snapshot identity
- rubric version identity
- pipeline commit hash for logic used
The goal is that any downstream artefact can be traced back to:
- a population snapshot,
- a rubric version,
- and a specific logic revision.
## 7. Storage and Placement Model (Revised)
This architecture distinguishes **inputs** from **run outputs** and mirrors the four-pipeline structure in both layers.
All course-specific artefacts live under:
```
06_grading/<ASSESSMENT>/
```
Within that directory, storage is divided into two top-level zones:
- `00_inputs/`
- `02_runs_outputs/`
### 7.1 Input Zone
```
00_inputs/
  pl1A_canonical_population_prep_input/
  pl1B_rubric_devt_input/
  pl2_calibration_input/
  pl3_grading_core_input/
```
Purpose:
- Store raw and upstream artefacts required to execute each pipeline.
- Inputs may be replaced or versioned over time.
- Inputs are not considered frozen runs.
Pipeline-specific intent:
- `pl1A_canonical_population_prep_input/`
  - LMS exports
  - grading worksheets
  - database extracts
- `pl1B_rubric_devt_input/`
  - assessment design notes
  - draft rubric structures
  - prior rubric versions (if reused)
- `pl2_calibration_input/`
  - Stage 0A snapshot copy (for sampling)
  - selected calibration sets
  - rubric definition version under test
- `pl3_grading_core_input/`
  - frozen Stage 0A snapshot
  - locked rubric definition version
  - locked calibration artefacts
  - production protocol
Inputs may evolve. They are not authoritative historical artefacts.
### 7.2 Runs / Outputs Zone
```
02_runs_outputs/
  pl1A_canonical_population_prep_runs/
  pl1B_rubric_devt_runs/
  pl2_calibration_runs/
  pl3_grading_core_runs/
```
Purpose:
- Store frozen, versioned, reproducible outputs of each pipeline.
- Each subdirectory contains bounded runs.
- Each run must be self-contained and traceable.
#### 7.2.1 `pl1A_canonical_population_prep_runs/`
Contains:
- Stage 0A canonical dataset snapshot
- Stage 0A manifest
- join validation audit artefacts
Each run represents a frozen canonical population state.
#### 7.2.2 `pl1B_rubric_devt_runs/`
Contains:
- rubric definition datasets
- dimension specifications
- scale definitions
- rubric version declarations
Each run represents a versioned rubric artefact suitable for calibration.
#### 7.2.3 `pl2_calibration_runs/`
Contains:
- calibration set artefacts
- boundary rule revisions
- anchor banks
- stability check notes
- provisional scoring outputs
Each run represents a diagnostic execution of rubric interpretation tied to a specific rubric version and canonical snapshot.
Calibration runs do not produce grades.
#### 7.2.4 `pl3_grading_core_runs/`
Contains:
- Stage 0B grading unit dataset
- scoring outputs (full population)
- QA artefacts
- export-ready grade files
- grading manifests
Each run represents an authoritative grading execution tied to:
- a specific canonical population snapshot,
- a specific rubric version,
- a specific pipeline commit state.
## 7.3 Run Identity Discipline
Every run directory must encode or record:
- course and assessment identifier
- run timestamp or run ID
- canonical population reference
- rubric version reference
- pipeline commit hash (where applicable)
No artefact in `02_runs_outputs/` may be modified after freeze.
If logic or rubric changes, a new run directory must be created.
## 7.4 Architectural Principle
Inputs are mutable working artefacts.  
Runs are immutable historical records.
The separation between `00_inputs/` and `02_runs_outputs/` enforces:
- reproducibility,
- auditability,
- and clear handoffs between pipelines.
This model supports longitudinal comparison across rubric versions and grading cycles without ambiguity.
## 8. Summary
The four-pipeline architecture enforces:
- separation of population definition from rubric definition,
- separation of rubric definition from calibration,
- separation of calibration from production grading,
- and deterministic, pinned, reproducible artefacts at each boundary.
This supports long-term reuse across assessments while keeping course-specific runs auditable and comparable.
