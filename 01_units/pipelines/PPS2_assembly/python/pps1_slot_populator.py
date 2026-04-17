"""Populate PPS1 section-slot and claim fields from dimension-level source fields.

This module isolates the slot-selection heuristic used by the PPS1 importer.
It expects a schema-like object that exposes:

- `dimensions`: ordered short dimension keys such as `B-1`
- `short_to_dotted_dimension`: mapping such as `B-1 -> B.2.1`
- `section1_slots`, `section2_slots`, `section3_slots`: ordered slot definitions

The source record is the already-assembled flat record containing direct LMS
fields plus the derived `*-devt` and `*-status` fields. The target mapping is
typically the importer's `sectionDerived` block.

Selection heuristic:

1. Prefer dimensions with a non-empty `-status` value.
2. Then prefer dimensions with a non-empty `-devt` value.
3. Fall back to schema dimension order.
4. Section 1 takes the first three dimensions from that priority list.
5. Section 2 takes the next three remaining dimensions.
6. Section 3/4 tensions prefer dimensions whose `-status` is `in tension`,
   then reuse the Section 2/remaining order to fill any open slots.

Claim fields are tied to Section 2. `CLM_01_dimension` is the first Section 2
dimension, and `CLM_01_text` through `CLM_03_text` are populated from the
matching Section 2 PPS1 values in slot order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


CLAIM_DIMENSION_FIELD = "CLM_01_dimension"
CLAIM_TEXT_FIELDS = ("CLM_01_text", "CLM_02_text", "CLM_03_text")


@dataclass(frozen=True)
class SectionSlot:
    dim_field: str
    ppp_field: str | None = None
    pps1_field: str | None = None


class SlotPopulationSchema(Protocol):
    dimensions: list[str]
    short_to_dotted_dimension: dict[str, str]
    section1_slots: list[SectionSlot]
    section2_slots: list[SectionSlot]
    section3_slots: list[SectionSlot]


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def select_section_dimensions(
    schema: SlotPopulationSchema,
    record: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    priority = ordered_unique(
        [dimension for dimension in schema.dimensions if record.get(f"{dimension}-status")]
        + [dimension for dimension in schema.dimensions if record.get(f"{dimension}-devt")]
        + schema.dimensions
    )
    section1 = priority[:3]
    remaining = [dimension for dimension in priority if dimension not in section1]
    section2 = remaining[:3]
    tension_dims = [
        dimension for dimension in schema.dimensions if record.get(f"{dimension}-status") == "in tension"
    ]
    tension_priority = ordered_unique(tension_dims + section2 + remaining)
    section3 = tension_priority[:2]
    return section1, section2, section3


def populate_section_fields(
    schema: SlotPopulationSchema,
    target: dict[str, str],
    source_record: dict[str, str],
) -> None:
    section1_dims, section2_dims, section3_dims = select_section_dimensions(schema, source_record)

    for dimension, slot in zip(section1_dims, schema.section1_slots, strict=False):
        target[slot.dim_field] = schema.short_to_dotted_dimension[dimension]
        if slot.ppp_field:
            target[slot.ppp_field] = source_record.get(f"{dimension}-PPP", "")
        if slot.pps1_field:
            target[slot.pps1_field] = source_record.get(f"{dimension}-PPS1", "")

    for dimension, slot in zip(section2_dims, schema.section2_slots, strict=False):
        target[slot.dim_field] = schema.short_to_dotted_dimension[dimension]
        if slot.ppp_field:
            target[slot.ppp_field] = source_record.get(f"{dimension}-PPP", "")
        if slot.pps1_field:
            target[slot.pps1_field] = source_record.get(f"{dimension}-PPS1", "")

    for dimension, slot in zip(section3_dims, schema.section3_slots, strict=False):
        target[slot.dim_field] = schema.short_to_dotted_dimension[dimension]
        if slot.pps1_field:
            target[slot.pps1_field] = source_record.get(f"{dimension}-PPS1", "")

    if section2_dims:
        target[CLAIM_DIMENSION_FIELD] = schema.short_to_dotted_dimension[section2_dims[0]]

    for dimension, claim_field in zip(section2_dims, CLAIM_TEXT_FIELDS, strict=False):
        target[claim_field] = source_record.get(f"{dimension}-PPS1", "")