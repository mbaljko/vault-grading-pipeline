# pl1C_rubric_devt

This pipeline directory is organized around Layer 1 rubric development.

## Conceptual Model

- `iteration`: a rubric-development episode.
- `registry version`: a checkpoint of the indicator registry within an iteration.
- `run`: one repeated scoring execution against a fixed registry version and fixed scoring prompts.

Use these distinctions consistently:

- Start a new `iteration` when the rubric-development episode changes.
- Create a new `registry version` when the indicator registry changes during stage13 refinement.
- Create a new `run` when repeating scoring with the same registry and same prompts.

## Workflow Meaning

- `iter00` is typically the bootstrap iteration.
- Early stages such as `stage01`, `stage02`, `stage03`, and `stage11+12-merged` produce the initial indicator registry.
- `stage13` is the registry refinement loop.
- Later iterations may begin directly at `stage13` if upstream stages do not need to be rerun.

## Practical Implication

Do not use new iterations merely to repeat scoring.

Instead:

- keep the same iteration while the registry is unchanged,
- keep the same registry version while prompts are unchanged,
- store repeated scoring passes as separate runs,
- reserve new iterations for actual registry-development changes.

## Directory Intent

- `llm_prompt/`: prompt assets used by the LLM-based path.
- `python/`: deterministic orchestration and reporting scripts.
- `scaffold/`: scaffold templates used by the Python prompt-generation path.

## Additional Docs

- Layer 1 deterministic registry augmentation reference: [docs/layer1_registry_augmentation.md](layer1_registry_supported_values.md)
