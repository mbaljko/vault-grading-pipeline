# PPS1 Slot Populator

This module contains the PPS1 importer logic that chooses which dimension rows populate the booklet slot fields.

## Files

- Module: `/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/pps1_slot_populator.py`
- Importer caller: `/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/import_pps1_csv_to_json.py`

## Scope

The module is intentionally narrow. It does not import LMS CSV rows, build base records, or derive `*-devt` and `*-status` values. It only:

- defines the `SectionSlot` dataclass used by the schema loader
- selects Section 1, Section 2, and Section 3/4 dimensions from an assembled record
- writes the `Sec1_*`, `Sec2_*`, `Sec3Sec4_*`, and `CLM_*` fields into a target mapping

## Inputs

`populate_section_fields(...)` expects:

- a schema-like object with:
  - `dimensions`
  - `short_to_dotted_dimension`
  - `section1_slots`
  - `section2_slots`
  - `section3_slots`
- a target dictionary, usually the importer's `sectionDerived` block
- a flat source record that already contains:
  - direct `*-PPP` and `*-PPS1` fields
  - derived `*-devt` fields
  - derived `*-status` fields

## Selection Heuristic

The slot order is heuristic, not hard-coded per section.

1. Dimensions with a non-empty `-status` are prioritized first.
2. Dimensions with a non-empty `-devt` are prioritized next.
3. Remaining dimensions fall back to schema order.
4. Section 1 takes the first three prioritized dimensions.
5. Section 2 takes the next three remaining dimensions.
6. Section 3/4 tension slots prefer dimensions whose status is exactly `in tension`, then fall back to the Section 2 / remaining ordering.

This is why a slot such as `Sec1_TS1_dim` can end up as `D.2.1`: if `D-1` is the first prioritized dimension, it is mapped through `short_to_dotted_dimension` and assigned into the first Section 1 slot.

## Claim Fields

Claim fields are populated from the Section 2 selection:

- `CLM_01_dimension` is the first Section 2 dimension
- `CLM_01_text`, `CLM_02_text`, and `CLM_03_text` are the corresponding Section 2 PPS1 texts in slot order

## Maintenance Notes

- Change the schema if slot names or slot counts change.
- Change this module only if the slot-selection heuristic itself changes.
- Keep the source record flat and fully populated before calling the module; it is not responsible for deriving missing upstream fields.