# PPS1 CSV Importer

This workflow converts the exported PPS1 LMS CSV into one JSON file per student for PPS2 booklet generation.

## Files

- Script: `/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/import_pps1_csv_to_json.py`
- Schema/config: `/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/pps1_import_schema.json`

## What it does

- Reads the PPS1 LMS export CSV.
- Maps LMS columns into the JSON fields used by the PPS2 workflow.
- Derives `*-devt` fields from the `*_shift`, `*_cont`, and `*_intro` columns.
- Derives `*-status` fields from the `E2_*_GridResponse` columns.
- Populates the `Sec1_*`, `Sec2_*`, `Sec3Sec4_*`, and `CLM_*` fields heuristically from the available dimension data.
- Writes one JSON per row into `student_data_all`.
- Writes an audit CSV with one row per imported LMS row.
- Writes a Markdown sidecar summary report next to the audit CSV.
- Copies a random sample into `student_data`.
- Augments that sample with three coverage cases: one random `_DOT` family-name file, the file with the longest family name, and the file with the longest given-name string.

## Configuration

Default importer inputs are centralized in `pps1_import_schema.json` under `importDefaults`:

- `csvPath`
- `participantsCsvPath`
- `allOutputDir`
- `sampleOutputDir`
- `auditPath`
- `sampleSize`

The same schema file also defines:

- field order and default values for output JSON
- direct CSV-to-JSON field mapping
- dimension mappings like `B-1 -> B.2.1`
- section slot mappings for Section 1, Section 2, and Section 3/4 tension fields

CLI arguments still work as overrides when needed.

## Name Join Logic

`GIVEN_NAME` and `FAMILY_NAME` are resolved using the participants export CSV first.

Primary join key:

- `Email address`

Secondary fallback join key:

- LMS `Username` matched against the email local-part from the participants CSV

If no participant match is found, the importer falls back to parsing the LMS `User` field heuristically.

This matters because the LMS `User` field is not always a reliable given-name/family-name split, while the participants CSV usually is.

Special handling:

- If the authoritative participant last name is `.`, the JSON `FAMILY_NAME` is kept as `.`.
- Filenames are built as `FAMILY_NAME` first, then `GIVEN_NAME`, with the family-name portion uppercased.
- For filenames only, a family name of `.` is rendered as `_DOT` so the generated filename remains explicit and filesystem-safe.

## Typical Run

```bash
/opt/homebrew/bin/python3 /Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/import_pps1_csv_to_json.py --sample-seed 3000
```

This also writes the audit CSV configured at `auditPath` and a Markdown sidecar summary report next to it.

## Notes

- The importer cleans mapped LMS response fields and the rich-text concept interpretation/use and attestation fields before writing JSON.
- The audit CSV currently contains one row per imported LMS row with the source CSV path, row index, user identifiers, resolved participant identity, output JSON path, per-dimension development-type checks, and Position-State Matrix audit fields.
- For each dimension `B-1` through `D-3`, the audit includes `*-shift`, `*-cont-reinf`, `*-intro`, `*-check`, and `*-err` columns. `*-check` is `true` only when exactly one development-type box is selected; otherwise `*-err` is `none selected` or `multiple selected`.
- The audit also records the four Position-State Matrix columns `E2_00_GridResponse`, `E2_10_GridResponse`, `E2_01_GridResponse`, and `E2_11_GridResponse`, plus a per-row `Position-State Matrix Saturation Rate` showing what percentage of those four fields are specified.
- The Markdown sidecar summary report counts, for each dimension, how many rows passed the check, had no development type selected, or had multiple development types selected, and it also summarizes Position-State Matrix coverage and saturation distribution with both counts and percentages.
- Section-selection logic is heuristic. If the PPS2 booklet structure changes, update the schema first and only change Python when selection logic itself must change.
- The sampled set can therefore be larger than `sampleSize`, because the three coverage cases are added on top of the random sample when they are not already included.