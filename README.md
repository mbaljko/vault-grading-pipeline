# README.md
# vault-grading-pipeline
## Overview
This repository is the canonical workspace for developing and running grading-related pipelines, operational data workflows, and small supporting tools used in course delivery.
It is designed as a **multi-pipeline, multi-tool monorepo** that supports:
- autograding and rubric evaluation pipelines  
- LMS data workflows (imports, exports, roster ETL)  
- feedback artefact generation  
- release and packaging workflows  
- stand-alone CLI tools and lightweight apps  
The architecture prioritises:
- a stable execution interface  
- consistent configuration and schema conventions  
- traceable, reproducible runs  
- easy extensibility across semesters  
- independence from IDE-specific project structures  
This repository works equally well with VS Code, terminal workflows, and automated execution.
## Core Concepts
### Monorepo with Modular Units
All runnable components are organised into **units**, which come in two types:
#### Pipelines
Repeatable workflows with defined inputs, transformations, and outputs.
Examples:
- grading workflows  
- roster ETL  
- release packaging  
#### Apps / Tools
Stand-alone utilities that support course operations.
Examples:
- report viewers  
- CLI utilities  
- local web dashboards  
Each unit is independently understandable and runnable while sharing:
- a common Python environment  
- shared utility libraries  
- consistent run logging conventions  
## Repository Structure
```
vault-grading-pipeline/
  README.md
  .gitignore
  .obsidian/                 # vault metadata
  docs/                      # design and operational documentation
    00_overview/
    01_design/
    02_specs/
    03_operations/
  bin/                       # stable execution interface
    run                      # dispatcher entrypoint
  env/                       # shared virtual environment (ignored)
  configs/                   # repo-wide non-secret configs
  secrets/                   # local secrets (ignored)
  units/
    pipelines/               # all pipeline modules
    apps/                    # stand-alone tools and apps
  libs/                      # shared reusable code
    common/
  runs/                      # execution artefacts (ignored)
  examples/                  # small sample inputs
  schemas/                   # shared data schemas
  templates/                 # shared templates
  scripts/                   # short-lived maintenance scripts
```
## Execution Model
All workflows are executed through a **stable dispatcher** in `bin/`.
This provides a consistent interface regardless of internal structure.
### Core Pattern
```
bin/run pipeline <name> <command> [args...]
bin/run app <name> <command> [args...]
```
### Examples
```
bin/run pipeline grading_core grade --config configs/dev.yml
bin/run pipeline roster_etl import --config configs/roster.yml
bin/run app grade_report_viewer serve --port 8000
```
The dispatcher handles:
- environment activation  
- run directory creation  
- logging conventions  
- argument forwarding  
## Run Artefact Conventions
Each execution produces a traceable run directory:
```
runs/<unit>/<YYYY-MM-DD>/<HHMMSS>/
  logs/
  inputs_manifest.json
  config_resolved.yml
  outputs/
  checks/
```
Key principles:
- every run is reproducible  
- inputs and resolved configuration are recorded  
- logs are co-located with outputs  
- run artefacts are never committed  
## Configuration Model
Configuration is layered:
- **Repository-wide defaults** → `configs/`
- **Unit-specific configuration** → `units/.../<name>/config/`
- **Secrets (never committed)** → `secrets/`
## Development Model
Durable code must live in one of two places:
- `units/.../src/<name>/` — unit-specific code  
- `libs/.../src/<libname>/` — shared utilities  
Top-level `scripts/` is reserved only for:
- temporary maintenance tasks  
- migrations  
- one-off operations  
If a script becomes durable, it must be promoted into a unit.
## Environment Strategy
The repository initially uses a **single shared Python environment** located at:
```
env/
```
This simplifies setup and coordination across multiple pipelines.
The architecture supports future migration to per-unit environments if needed.
## Git and Ignore Policy
This repository uses an **explicit blacklist model**:
- all durable artefacts are tracked by default  
- only ephemeral, local, or sensitive items are ignored  
Never commit:
- environments  
- run artefacts  
- secrets  
- caches  
Always commit:
- source code  
- schemas and templates  
- documentation  
- non-secret configuration  
## Adding a New Pipeline
1. Create a directory:
```
units/pipelines/<name>/
```
2. Add a standard skeleton:
```
config/
schemas/
templates/
src/<name>/
tests/
README.md
```
3. Implement commands and register them with the dispatcher.
## Adding a New Tool or App
1. Create:
```
units/apps/<name>/
```
2. Keep it CLI-first unless a UI is required.
3. Use shared libraries via `libs/`.
## Documentation Organisation
Repository documentation is structured as:
- **Overview** — what exists and how to run it  
- **Design** — architecture decisions  
- **Specs** — schemas and invariants  
- **Operations** — SOPs and troubleshooting  
Each unit also includes its own local README.
## Design Philosophy
This repository enforces clarity through **directory architecture**, not through IDE configuration or restrictive ignore rules.
It is intended to be:
- extensible across academic terms  
- reproducible across machines  
- maintainable by future collaborators  
- independent of specific development tools  
## Initial Setup Status
The repository is considered properly initialised when:
- `units/pipelines/` and `units/apps/` exist  
- `libs/common/` exists  
- `bin/run` is operational  
- `env/`, `runs/`, and `secrets/` are ignored  
- documentation directories are established  
## Next Steps
Typical next actions after cloning:
1. Create the shared environment in `env/`
2. Implement the first pipeline under `units/pipelines/`
3. Add shared utilities to `libs/common/`
4. Populate `docs/` with design and operational notes
This repository serves as a long-term operational foundation for grading infrastructure and related academic workflow automation.
