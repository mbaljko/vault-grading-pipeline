This is the right moment to pause before over-engineering.
You are not asking “what is theoretically clean?”
You are asking:
> Given real grading pressure, do I stabilise this Excel/MCode workflow or migrate now?

Here is the clear answer:
### Do not migrate the workflow right now. Stabilise it.
You have:
- A working process.
- It has already been executed successfully once.
- You are mid-course.
- You still have 4 components × multiple dimensions left.
Migrating to a new infrastructure mid-stream will introduce:
- implementation bugs
- schema mismatches
- sampling inconsistencies
- TA confusion
- subtle row-misalignment errors
That risk is much higher than the architectural impurity of staying in Excel temporarily.
## The correct move now
**Freeze the workflow as Version 1.0 and document it precisely.**
Then:
- Finish this grading cycle using it.
- After the term, abstract it into the pipeline repo.
You are still in “live operations mode,” not “infrastructure refactor mode.”
# What you actually have (and why it’s not wrong)
Your current workflow is:
1. LMS export (wide CSV)
2. Convert to Excel workbook
3. Add grading sheet worksheet
4. Use MCode to:
    - join validation (__join_status)
    - clean HTML/emojibake
    - compute word counts
    - prepend anonymised +++row_id=YYY+++
5. Create sampled worksheet
6. Use interior-uniform sampling
7. Copy calibration rows for TA review
This is:
- Deterministic
- Reproducible (if the MCode is stable)
- Already partially validated
- Dimension-first compatible
That is not a fragile ad hoc system. It is a proto-pipeline implemented in Excel.
# The real architectural question
The question is not “Excel vs Python.”
The question is:
> Where does canonicalisation live?

Right now it lives in:
- an Excel workbook
- MCode scripts
- manual operations
That is acceptable for this term.
What you need now is not migration.
What you need is:
1. Explicit specification of what Stage 0 guarantees.
2. Versioned MCode.
3. A stable worksheet contract.
# When you should migrate
Migrate when:
- You have completed grading for this assessment.
- You are not under deadline pressure.
- You want cross-course reuse.
- You want batch automation.
- You want deterministic non-interactive processing.
Do not migrate mid-stream.
# What I recommend you do immediately
Instead of migrating, do this:
## 1. Formalise your Excel Stage 0 contract
Write a document:
stage0_excel_contract.md
Define:
- Input worksheet names
- Output worksheet names
- Required columns
- Join logic
- Sampling logic
- Word count logic
- ID anonymisation rule
You already wrote the spec. Now bind it to this implementation.
## 2. Version your MCode
Store:
- The exact MCode scripts in the pipeline repo.
- Treat them as code, not as embedded workbook logic.
This gives you:
- Version control
- Future migration path
- Reproducibility
## 3. Freeze the workbook structure
Define canonical worksheet names:
- raw_export
- grading_sheet
- validation
- cleaned_entries
- sampled_entries
Do not rename them mid-cycle.
# What NOT to do right now
Do not:
- Rewrite in pandas
- Introduce Parquet
- Change file formats
- Redesign the sampling logic
- Replace row_id mechanism
You are in production mode.
# The strategic timeline
Now (during grading):
- Stabilise Excel workflow.
- Document it.
After term:
- Re-implement Stage 0 in pipeline repo.
- Replicate identical output schema.
- Validate equivalence against Excel outputs.
Only migrate when you can do output diffing.
# The real decision rule
Ask:
> Is the current workflow failing or blocking scaling?

If no — do not migrate.
Your current pain point is not technical debt.
It is architectural clarity.
Those are different problems.
# My recommendation in one sentence
Keep the Excel/MCode workflow for this term, formalise it as a Version 1 Stage 0 implementation, and migrate only after grading is complete.
If you want, I can now:
- Map your exact Excel workflow to the canonical Stage 0 spec you wrote
- Or outline a zero-risk migration plan that guarantees output equivalence when you eventually switch to Python.
