> so if I implement the Recommended Minimal Alignment Actions, will I then regenerate the document "Stage 0 (Excel/MCode) — Implementation Mapping to Specification"?
and I'd also like to build documentation for replicability in the future

Short answer: **yes — but in a specific way.**
You do not “regenerate” the mapping document from scratch.
You **promote it from diagnostic mapping → normative implementation spec**.
Right now the document reads like:
> “Here is how the current Excel workflow approximates the spec.”

After you implement the Minimal Alignment Actions, it should become:
> “This is the authoritative Excel Stage 0 implementation, and it satisfies the Stage 0 specification.”

That is a different document state.
## What should happen after you implement the Minimal Alignment Actions
Once you:
- Add explicit identifier columns
- Add stage0_manifest worksheet
- Explicitly declare cleaned_entries as canonical dataset
- Decide Mode A vs Mode B
You should:
### 1. Revise the mapping document into an Implementation Standard
Rename it something like:
```
Stage0_Excel_Implementation_Standard.md
```
Change tone from descriptive to prescriptive:
Instead of:
> “Currently partially satisfied…”

It should say:
> “The Excel Stage 0 implementation SHALL…”

That converts it into an operational contract.
### 2. Add a Replicability Section
You are correct — replicability needs its own layer.
You want future-you (or a TA) to be able to:
- Re-run Stage 0 on a new export
- Validate correctness
- Produce identical outputs
That requires a second document:
```
Stage0_Excel_Runbook.md
```
This is different from the spec.
The spec defines _what must be true_.
The runbook defines _how to do it_.
# Recommended Documentation Architecture
Inside your pipeline repo (or course vault if you prefer for now):
```
docs/
  stage0/
    Stage0_Specification.md
    Stage0_Excel_Implementation_Standard.md
    Stage0_Excel_Runbook.md
    Stage0_Validation_Checklist.md
```

==I'm adding the design notes under /docs/01_design/ in vault-grading-pipeline since it is reusable tooling, why are you suggesting to put it in course repo?==

Each document has a distinct role:
### 1. Stage0_Specification.md
Normative, platform-agnostic spec.
Never mentions Excel or Python.
### 2. Stage0_Excel_Implementation_Standard.md
Defines:
- Worksheet names
- Required columns
- Required manifest contents
- Required validation checks
- Required sampling determinism
This says:
> If you use Excel, this is what “correct” means.

### 3. Stage0_Excel_Runbook.md
Step-by-step operator instructions:
1. Export LMS CSV
2. Save as workbook
3. Paste grading worksheet
4. Refresh Power Query
5. Verify validation
6. Confirm row counts
7. Review stage0_manifest
8. Export canonical dataset (optional)
This is operational replication documentation.
### 4. Stage0_Validation_Checklist.md
One-page checklist:
- No no_match rows in canonical dataset
- Row count matches expected
- No duplicate keys
- Word counts computed
- Sampling parameters recorded
This is what prevents drift over time.
# The Key Conceptual Shift
Right now you are thinking:
> “Should I regenerate the mapping doc?”

The better move is:
> “I will convert the mapping doc into a formal implementation standard and separate the runbook.”

That gives you:
- Conceptual clarity
- Replicability
- Auditability
- Migration readiness later
# Why this matters strategically
When you later migrate to Python:
- You keep Stage0_Specification.md unchanged.
- You write Stage0_Python_Implementation_Standard.md.
- You validate equivalence between Excel and Python outputs.
Because you separated:
- specification
- implementation
- runbook
You avoid architectural confusion.
# Direct Answer
Yes, revise the document — but:
- Convert it into an implementation standard.
- Add a separate runbook for replicability.
- Add a checklist for operational validation.
Do not leave it as a mapping document long-term.
If you want, I can next:
- Draft the structure of Stage0_Excel_Implementation_Standard.md, or
- Draft a clean, operator-focused Stage0_Excel_Runbook.md.
