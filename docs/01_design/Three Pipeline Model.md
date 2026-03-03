Yes. That’s the cleanest decomposition, and it matches the ontological layers you’re already enforcing.
Here’s the separation that will stay stable over time.
### Pipeline 1: canonical_population_prep
Purpose: define the grading population and its canonical representation.
Outputs (course-specific, per assessment, per run snapshot):
- Stage 0A canonical grading targets snapshot (rubric-agnostic)
- Stage 0A manifest (pinned to pipeline_commit)
- join/eligibility audit artefacts as needed
This pipeline answers: what exists and is eligible to be graded?
### Pipeline 2: calibration_runs
Purpose: construct and stabilise rubric interpretation (rules, anchors, triggers).
Inputs:
- a Stage 0A snapshot (or a copy of one component slice of it)
- rubric definition artefacts under construction
Outputs:
- calibration sets (sample IDs per component)
- boundary rules revisions
- anchor banks
- stability checks
- production scoring protocol
- a rubric definition artefact that is now “locked” for use (this is the handoff)
This pipeline answers: how should we interpret/scorify the population?
### Pipeline 3: grading_runs
Purpose: apply the locked rubric to the canonical population deterministically.
Inputs:
- frozen Stage 0A snapshot (canonical population)
- locked rubric definition (versioned)
- locked scoring protocol (including needs_review triggers)
Outputs:
- Stage 0B canonical grading units (expanded targets × rubric dimensions)
- scoring outputs (full population)
- QA outputs (coverage checks, duplicates, drift flags)
- export artefacts for LMS upload and internal reporting
This pipeline answers: what scores does the population receive under the locked interpretation?
### Key discipline
The handoff from Pipeline 2 to Pipeline 3 is a “rubric lock” event.
After rubric lock:
- calibration may continue as a future revision cycle, but it produces a new rubric version
- grading runs must not mutate rubric structure for that run
### Directory implications with your naming
With your renames, this maps cleanly to:
- 01_rubric_devt_runs/ for Pipeline 2 outputs (calibration artefacts + rubric versions)
- 02_calibration_runs/ if you still want to treat calibration as distinct from rubric construction; otherwise merge into 01_rubric_devt_runs/
- 03_grading_runs/ for Pipeline 1 + Pipeline 3 run artefacts, or split:
    - 03_grading_runs/00_population/ (Stage 0A)
    - 03_grading_runs/01_scoring/ (Stage 0B + scoring)
If you want one decisive rule: Stage 0A snapshots live with grading runs, even if calibration borrows them.


If you want, I can propose a minimal directory tree under 06_grading/<ASSESSMENT>/ that makes these three pipelines explicit without creating too many folders.
