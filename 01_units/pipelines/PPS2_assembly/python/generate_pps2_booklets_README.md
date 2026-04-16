# PPS2 Booklet Generator

This directory contains a single-script generator for individualized PPS2 exam booklets.

## What it does

- Reads all JSON files from a student data directory.
- Loads the master Markdown template.
- Replaces brace-style placeholders such as `{participant_id}` and `{claims.CLM_01_text}`.
- Renders one PDF per student with `pandoc` into the output directory.

## Required dependencies

- Python 3.10+
- `pandoc`
- A LaTeX engine on `PATH`, preferably `xelatex`

## Run

```bash
python /Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/generate_pps2_booklets.py \
  --template /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/master_PPS2_activity/PPS2_template.md \
  --latex-template /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/master_PPS2_activity/PPS2_pdf_template.tex \
  --input-dir /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/student_data \
  --output-dir /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/generated_individualized_PPS2 \
  --keep-tex
```

## Useful flags

- `--keep-md`: also save the filled Markdown file for each student.
- `--keep-tex`: also save the pandoc-generated LaTeX file for each student.
- `--allow-missing`: render even if some placeholders remain unresolved.
- `--verbose`: print dependency and pandoc command details.
- `--latex-template`: pass a custom LaTeX template to pandoc for PDF styling.

## Custom PDF styling

This workflow can use a custom LaTeX template to control PDF appearance without changing the student JSON or the Markdown content template.

Starter template location:

```text
/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/master_PPS2_activity/PPS2_pdf_template.tex
```

That template currently provides a basic article layout with readable spacing and narrower margins than the Pandoc default.

## Placeholder behavior

The script extracts placeholders automatically from the template using regex. Nested JSON is flattened using dot notation, so this data:

```json
{
  "participant_id": "S042",
  "claims": {
    "CLM_01_text": "Claim text"
  }
}
```

can resolve both `{participant_id}` and `{claims.CLM_01_text}`.

Top-level scalar keys also remain directly addressable, so `{CLM_01_text}` works when the JSON includes that exact key.

## Output filenames

Each rendered booklet is named:

```text
<participant_id>_PPS2.pdf
```

If `participant_id` is missing, the JSON filename stem is used.