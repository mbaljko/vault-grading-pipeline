# Design Note — `vault-grading-pipeline` as a Multi-Pipeline and App Workspace
## 1. Purpose
This repository is the canonical workspace for building and running:
- grading pipelines (autograding, rubric evaluation, feedback artefact generation)
- adjacent operational pipelines (e.g., roster ETL, LMS exports/imports, release packaging)
- stand-alone tools and small apps that support course delivery (CLI utilities, local web apps, report generators)
The design goal is to support multiple independent pipelines and tools while maintaining:
- a stable execution interface (`bin/`)
- consistent configuration and schema conventions
- traceability of runs and reproducibility
- easy extensibility without reorganising the repository each term
This is a **folder- and package-oriented architecture** suitable for VS Code and Git, without relying on IDE-specific project constructs.
## 2. Core Architectural Model
### 2.1 Monorepo with Modular Units
The repository is a monorepo consisting of modular units of two types:
1. **Pipelines**: repeatable workflows with inputs → transforms → outputs (often staged)
2. **Apps/Tools**: stand-alone utilities (CLI-first; optionally local web apps)
Each unit should be independently understandable and runnable, while sharing:
- a common environment
- shared libraries
- consistent run logging and artefact conventions
### 2.2 Shared Environment Strategy
Initial setup uses a **single shared Python environment** for the repo.
Rationale:
- simplest operational setup
- minimal friction across multiple pipelines/tools
- appropriate while dependencies remain compatible
The directory layout and conventions are designed so that later evolution to per-unit environments remains possible without major restructuring.
## 3. Target Repository Structure
```text
`vault-grading-pipeline/`
  `README.md`
  `.gitignore`
  `.obsidian/`                    # vault metadata (gitignored or committed per preference)
  `docs/`                         # human documentation (design + operating notes)
    `00_overview/`
    `01_design/`
    `02_specs/`
    `03_operations/`
  `bin/`                          # stable entrypoints (thin wrappers)
    `run`                         # dispatcher: choose pipeline/app + command
    `pipeline`                    # convenience alias for pipeline runs
    `app`                         # convenience alias for tools/apps
    `doctor`                      # environment + dependency sanity checks
  `env/`                          # shared virtual environment (gitignored)
  `configs/`                      # shared/global configs (non-secret)
  `secrets/`                      # local-only secrets (gitignored; never committed)
  `units/`                        # all runnable modules live here
    `pipelines/`
      `grading_core/`
        `README.md`
        `config/`                 # unit-level configs
        `schemas/`                # unit-level schemas
        `templates/`              # unit-level templates
        `src/grading_core/`       # python package namespace
        `tests/`
      `roster_etl/`
        ... same pattern ...
      `release_packaging/`
        ... same pattern ...
    `apps/`
      `grade_report_viewer/`
        `README.md`
        `src/grade_report_viewer/`
        `static/`                 # if needed
        `tests/`
      `rubric_designer_cli/`
        ... same pattern ...
  `libs/`                         # shared code across units
    `common/`
      `src/common/`
      `tests/`
    `lms/`                        # optional: LMS adapters (e.g., eClass, Gradescope)
      `src/lms/`
      `tests/`
  `runs/`                         # execution artefacts, organised by unit + timestamp (gitignored)
    `grading_core/`
      `<YYYY-MM-DD>/<HHMMSS>/`
    `roster_etl/`
      `<YYYY-MM-DD>/<HHMMSS>/`
  `examples/`                     # sample inputs and minimal demo runs (small, committed)
  `schemas/`                      # shared schemas (cross-unit)
  `templates/`                    # shared templates (cross-unit)
  `scripts/`                      # one-off maintenance scripts (kept small; prefer units for durable logic)
```
## 4. Naming and Boundary Rules
### 4.1 Unit Names
Unit folder names must be:
- lowercase
- underscore-separated
- stable over time
Example:
- `grading_core`
- `roster_etl`
- `grade_report_viewer`
### 4.2 Code Location and Imports
Durable code must live in:
- `units/<type>/<name>/src/<name>/...` (unit-specific)
- `libs/<libname>/src/<libname>/...` (shared)
Top-level `scripts/` is reserved for:
- short-lived maintenance tasks
- migration helpers
- temporary one-offs
If a script becomes operationally important, it is promoted into a unit.
### 4.3 Configuration
Configuration is split into:
- repo-wide defaults: `configs/`
- unit-specific config: `units/.../<name>/config/`
Secrets are never committed and live only in:
- `secrets/`
## 5. Run and Artefact Conventions
All executions produce a run directory:
```text
`runs/<unit>/<YYYY-MM-DD>/<HHMMSS>/`
  `logs/`
  `inputs_manifest.json`
  `config_resolved.yml`
  `outputs/`
  `checks/`
```
Principles:
- every run is traceable to inputs and resolved configuration
- logs and artefacts are colocated with the run
- run folders are gitignored by default
## 6. Stable Execution Interface
### 6.1 `bin/` as the Operational Contract
`bin/` provides a stable interface that does not change even if internal structure evolves.
Core pattern:
- `bin/run pipeline <name> <command> [args...]`
- `bin/run app <name> <command> [args...]`
Examples:
- `bin/run pipeline grading_core grade --config <path>`
- `bin/run pipeline roster_etl import --config <path>`
- `bin/run app grade_report_viewer serve --port 8000`
Wrappers should:
- activate the shared environment if needed
- enforce consistent logging and run folder creation
- pass through arguments transparently
## 7. Documentation Discipline
Documentation is organised as:
- `docs/00_overview/` — what exists and how to run it
- `docs/01_design/` — architecture and design decisions
- `docs/02_specs/` — schema/spec documents and invariants
- `docs/03_operations/` — SOPs, troubleshooting, release steps
Each unit also includes a local `README.md` describing:
- its purpose
- inputs/outputs
- commands
- configuration
- typical failure modes
## 8. Git and Ignore Policy
- commit: source code, schemas, templates, configs (non-secret), documentation
- ignore: `env/`, `runs/`, `secrets/`, caches, large generated artefacts
A `.gitignore` should cover at minimum:
- `env/`
- `runs/`
- `secrets/`
- `**/__pycache__/`
- `**/*.pyc`
- `**/.pytest_cache/`
- `.DS_Store`
## 9. Extensibility Path
To add a new pipeline:
1. create `units/pipelines/<name>/` using the standard skeleton
2. implement code under `src/<name>/`
3. add unit configs under `config/`
4. register a wrapper command in `bin/run` (or maintain a discovery-based dispatcher)
To add a stand-alone tool/app:
5. create `units/apps/<name>/`
6. keep it CLI-first unless there is a clear reason for a UI
7. use shared libraries via `libs/` imports
## 10. Initial Setup Checklist
The initial setup of this repository is considered complete when:
- `units/pipelines/` and `units/apps/` exist (even if empty initially)
- `libs/common/` exists for shared utilities
- `bin/run` exists as the stable entrypoint
- `runs/` is created and gitignored
- `env/` is created and gitignored
- `docs/` replaces ad hoc top-level design/spec directories
This establishes a scalable base for multiple pipelines and tools without future structural churn.
