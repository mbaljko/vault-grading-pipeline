# PPS1 Slot Populator

This module contains the PPS1 importer logic that chooses which dimension rows populate the booklet slot fields.

## Files

- Module: `/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/pps1_slot_populator.py`
- Importer caller: `/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/import_pps1_csv_to_json.py`

## Scope

The module is intentionally narrow. It does not import LMS CSV rows, build base records, or derive `*-devt` and `*-status` values. It only:

- defines the `SectionSlot` dataclass used by the schema loader
- selects Section 1, Section 2, and Section 4 dimensions from an assembled record
- writes the `Sec1_*`, `Sec2_*`, and `Sec4_Slot*` fields into a target mapping

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

1. Build a prioritized dimension order by preferring non-empty `-status`, then non-empty `-devt`, then schema order.
2. Populate the Section 1 TS slots first from family-specific subsets of that prioritized order:
  - `TS1` takes the first `B-*` dimension.
  - `TS2` takes the first `C-*` dimension.
  - `TS3` takes the first `D-*` dimension.
3. Section 2 takes as many dimensions as there are configured Section 2 slots from the remaining prioritized pool.
4. Section 4 prefers `in tension` dimensions from the remaining pool, then falls back to the remaining Section 2 order.

This is why a slot such as `Sec1_TS1_dim` will always be a `B.*` dimension: the module selects the highest-priority remaining `B-*` dimension for `TS1`, then does the same for `C-*` and `D-*` for `TS2` and `TS3`.

## Maintenance Notes

- Change the schema if slot names or slot counts change.
- Change this module only if the slot-selection heuristic itself changes.
- Keep the source record flat and fully populated before calling the module; it is not responsible for deriving missing upstream fields.