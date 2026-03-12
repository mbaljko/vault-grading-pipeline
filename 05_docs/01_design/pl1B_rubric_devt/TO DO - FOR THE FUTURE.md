### Future Improvement — Layer 1 Registry Reconciliation

This improvement is **not required for the current rubric release**.  
It is recorded here as a structural enhancement to prevent indicator drift between rubric artefacts.

#### Problem

The Layer 1 scoring system currently relies on two related artefacts:

1. **Rubric Payload — Layer 1 SBO Instance Registry**
2. **Layer1 Scoring Manifest**

Both artefacts define the same conceptual indicator set, but they currently do so independently.  
If one artefact is edited without updating the other, the pipeline may experience **indicator drift**, including:

- missing indicators
- duplicate indicators
- renamed indicators
- indicators assigned to incorrect components
- stale manifests after rubric revisions

These errors can propagate silently into scoring prompts.

#### Proposed structural improvement

Adopt **`sbo_identifier` as the canonical cross-artefact join key** between:

```
Rubric Payload (Layer 1 SBO Instances)
Layer1_ScoringManifest
```

Every Layer 1 indicator instance should appear in **both artefacts** with the same identifier.

#### Registry ownership model

Separate the responsibilities of the two artefacts.

**Rubric Payload owns indicator identity**

| field |
|---|
| `sbo_identifier` |
| `assessment_id` |
| `component_id` |
| `indicator_id` |
| `sbo_short_description` |

**Layer1 Scoring Manifest owns indicator evaluation guidance**

| field |
|---|
| `sbo_identifier` |
| `indicator_definition` |
| `assessment_guidance` |
| `evaluation_notes` |

Both artefacts include `sbo_identifier`, which functions as the **canonical reconciliation key**.

#### Reconciliation rule

For a valid rubric specification:

1. Every Layer 1 SBO instance in the rubric payload **must have exactly one corresponding row** in the Layer1 Scoring Manifest with the same `sbo_identifier`.
2. Every Layer1 Scoring Manifest row **must correspond to exactly one Layer 1 SBO instance** in the rubric payload.
3. For each matched row, the following fields must match:

```
sbo_identifier
component_id
indicator_id
```

#### Pipeline validation step

Future versions of the rubric pipeline should perform a **pre-scoring validation step**:

```
1. Read Layer 1 SBO instance registry from rubric payload.
2. Read Layer1 Scoring Manifest.
3. Compare the sets of `sbo_identifier`.
4. Fail execution if the sets are not identical.
5. For each identifier, verify equality of:
   component_id
   indicator_id
```

If any mismatch occurs, the rubric artefacts are considered **structurally invalid**.

#### Expected benefit

Implementing this reconciliation mechanism will:

- prevent silent indicator drift
- ensure scoring prompts always match the rubric specification
- allow indicator definitions and guidance to evolve safely
- enable automated rubric integrity validation within the grading pipeline