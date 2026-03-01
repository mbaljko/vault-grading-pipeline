### The architectural problem to solve
You have two classes of things that must not be tangled:
1. **Reusable grading infrastructure** (pipeline engine, scoring stages, calibration machinery, run logging, schemas, validators, report generators). This should live in vault-grading-pipeline as the canonical home.
2. **Course-specific assets and policies** (rubrics, dimensions, “needs review” rules, assignment mappings, roster joins, sampling strategies, exemplar sets, TA workflow, any local privacy constraints). These must live in each course vault (e.g., your eecs3000 vault).
The right mental model is: **pipeline core + course adapter**.
- The pipeline core provides stable commands and data contracts.
- Each course vault provides a thin “adapter package” that supplies configuration, rubric content, and any local logic.
### Proposed architecture
#### 1) Keep vault-grading-pipeline  as a monorepo of reusable units
In vault-grading-pipeline, treat calibration as a reusable pipeline (or library) rather than something embedded in the course vault.
Example units you will likely want:
- units/pipelines/calibration/
    Reusable calibration workflow: sampling, anchor selection scaffolds, rubric freeze artefacts, calibration drift checks, “needs_review” rule evaluation harness.
- units/pipelines/scoring/
    Production scoring workflow (dimension-first scoring, output schema, confidence/flags, review queue emission).
- libs/common/
    Shared utilities: config loading, path resolution, run logging, manifest writing, schema validation, CLI helpers.
- libs/grading/ (optional)
    Shared domain library: rubric model, dimension model, scoring record schema, review queue schema, consistency check primitives.
This keeps calibration “in the pipeline”, but makes it parametrised by a course adapter.
#### 2) In each course vault, create a small “course adapter” package
Inside the eecs3000 vault (and similarly for other courses), add a minimal Python package whose only job is to define:
- course identifiers and paths
- assignment definitions
- rubric dimensions
- calibration sampling parameters
- “needs_review” rules and flags
- course-specific transforms for preamble steps (preparing student work files)
Suggested location in the course vault:
```
`<course-vault>/grading/`
  `README.md`
  `course_config/`
    `configs/`
    `rubrics/`
    `schemas/` (only if course extends)
    `templates/` (optional course overrides)
  `src/eecs3000_grading/`
    `__init__.py`
    `course.py`           # course metadata + path mapping
    `assignments.py`      # assignment registry
    `rubric.py`           # rubric and dimensions (or loader)
    `rules.py`            # needs_review rules, flags, disqualifiers
    `prep/`               # preamble transforms (prepare student work)
      `__init__.py`
      `prepare_inputs.py`
```
This course adapter should remain thin. Anything generalisable gets promoted into vault-grading-pipeline.
#### 3) Define an explicit contract between pipeline and course adapter
The pipeline should not import arbitrary course code ad hoc. It should load a **course adapter** that implements a small, explicit interface.
A practical “contract” (conceptual, not Eclipse/VS Code parlance):
- The course adapter exports a function like:
    - get_course_spec() -> CourseSpec
- CourseSpec includes:
    - course_id
    - paths (where inputs live in that vault, where outputs should go)
    - assignments registry
    - rubric (dimensions + scoring scale)
    - calibration_plan (dimension-first sampling sizes, anchor expectations)
    - rules (non-negotiables/disqualifiers/flags/needs_review conditions)
    - preprocessors (preamble steps to normalize student work into canonical input tables)
Then the pipeline runs:
- calibration using CourseSpec.calibration_plan, CourseSpec.rubric, CourseSpec.rules
- scoring using CourseSpec.rubric and CourseSpec.rules
- consistency_check using CourseSpec.consistency_checks (optional)
This is what prevents drift into “vibe architecture”.
#### 4) Use configuration layering, not code duplication
Keep rubric text and dimension definitions in course vault files (because they are course-specific), but process them through reusable loaders and validators in the pipeline.
Layering:
- Pipeline defaults (generic)
- Course config (required)
- Run config (optional overrides per run)
Concretely:
- Course vault stores: `course_config/configs/<assignment>.yml` and `course_config/rubrics/<assignment>.yml`
- Pipeline provides: schema + loader + validation + normalisation to RubricSpec
#### 5) Make preamble steps first-class pipeline stages
You mentioned “preamble steps to prepare the files containing the student work”.
Treat those as a formal stage, not informal scripts.
Pattern:
- Stage 0: prepare_inputs (course-specific, but invoked through pipeline)
- Stage 1: calibrate_dimension (pipeline logic, parametrised)
- Stage 2: score_dimension (pipeline logic, parametrised)
- Stage 3: consistency_check (pipeline logic, parametrised)
- Stage 4: emit_review_queue and emit_reports (pipeline logic)
The only course-specific part of Stage 0 is _how to extract/normalise student work_ from the course vault’s artefacts.
Everything else should be pipeline-reusable.
### How to connect the two repos in practice (Option A friendly)
Since you prefer Option A (one environment per repo), the simplest operational approach is:
- Keep the pipeline repo as its own Python environment
- Run pipeline commands from the pipeline repo, pointing at the course vault via paths/config
Two workable connection styles:
#### Style A: Pipeline reads course vault config files, no Python package in course vault
- Course vault contains only YAML/rubric files and raw student artefacts.
- Pipeline loads those files by path.
- This is the lowest friction, but course-specific “rules” must be expressible declaratively (YAML), not arbitrary Python.
#### Style B: Course vault provides a small Python adapter package (recommended for your case)
- Course-specific rules and preamble transforms are Python (because they often are).
- Pipeline installs the course adapter in editable mode when you’re working with that course, or loads it via PYTHONPATH.
- This is still compatible with Option A because the environment lives in the pipeline repo; you just add the course adapter to it.
If you anticipate nontrivial “needs_review” logic and file-prep transforms, Style B will feel much better.
### What this looks like as a daily workflow
From vault-grading-pipeline:
- Prepare canonical inputs (calls course adapter prep):
    - `bin/run pipeline scoring prepare --course eecs3000 --assignment <A1>
- Calibrate Dimension 1:
    - `bin/run pipeline calibration calibrate-dimension --course eecs3000 --assignment <A1> --dimension 1
- Score Dimension 1 across all cells:
    - `bin/run pipeline scoring score-dimension --course eecs3000 --assignment <A1> --dimension 1
- Run cross-dimension checks:
    - `bin/run pipeline scoring consistency-check --course eecs3000 --assignment <A1>
Course vault remains the authoritative home for:
- the rubric text and any course policy
- the raw student work artefacts
- any course-specific reports you want to keep with the course record
Pipeline remains the authoritative home for:
- the calibration machinery
- scoring machinery and schemas
- run logging and reproducibility patterns
- shared libraries and validators
### A concrete next step
If you paste the current eecs3000 grading-related directory tree (just ls of the relevant folders), I’ll propose:
- the exact grading/ adapter skeleton for that vault
- the exact CourseSpec interface surface
- the minimal set of config files you should keep in the course vault versus the pipeline repo
