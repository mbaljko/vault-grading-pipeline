"""Populate PPS1 section-slot fields from dimension-level source fields.

This module isolates the slot-selection heuristic used by the PPS1 importer.
It expects a schema-like object that exposes:

- `dimensions`: ordered short dimension keys such as `B-1`
- `short_to_dotted_dimension`: mapping such as `B-1 -> B.2.1`
- `section1_slots`, `section2_slots`, `section3_slots`: ordered slot definitions

The source record is the already-assembled flat record containing direct LMS
fields plus the derived `*-devt` and `*-status` fields. The target mapping is
typically the importer's `sectionDerived` block.

Slots populated by this module:

- Section 1 slots:
    - `Sec1_TS1_dim`, `Sec1_TS1_PPP`, `Sec1_TS1_PPS1`, `Sec1_TS1_devt_type`, `Sec1_TS1_devt_explain_if_conflicting`
    - `Sec1_TS2_dim`, `Sec1_TS2_PPP`, `Sec1_TS2_PPS1`, `Sec1_TS2_devt_type`, `Sec1_TS2_devt_explain_if_conflicting`
    - `Sec1_TS3_dim`, `Sec1_TS3_PPP`, `Sec1_TS3_PPS1`, `Sec1_TS3_devt_type`, `Sec1_TS3_devt_explain_if_conflicting`
- Section 2 slots:
    - `Sec2_V1_dim`, `Sec2_V1_PPP`, `Sec2_V1_PPS1`, `Sec2_V1_devt_type`, `Sec2_V1_devt_explain_if_conflicting`
    - `Sec2_V2_dim`, `Sec2_V2_PPP`, `Sec2_V2_PPS1`, `Sec2_V2_devt_type`, `Sec2_V2_devt_explain_if_conflicting`
    - `Sec2_V3_dim`, `Sec2_V3_PPP`, `Sec2_V3_PPS1`, `Sec2_V3_devt_type`, `Sec2_V3_devt_explain_if_conflicting`
- Section 4 slots:
    - `Sec4_Slot1_dim`, `Sec4_Slot1_PPS1`, `Sec4_Slot1_devt_type`, `Sec4_Slot1_devt_explain_if_conflicting`
    - `Sec4_Slot2_dim`, `Sec4_Slot2_PPS1`, `Sec4_Slot2_devt_type`, `Sec4_Slot2_devt_explain_if_conflicting`
    - `Sec4_Slot3_dim`, `Sec4_Slot3_PPS1`, `Sec4_Slot3_devt_type`, `Sec4_Slot3_devt_explain_if_conflicting`

Selection heuristic:

1. Build a prioritized dimension order by preferring non-empty `-status`, then
    non-empty `-devt`, then schema dimension order.
2. Populate the Section 1 TS slots first from family-specific subsets of that
    prioritized order:
    - `TS1` takes the first `B-*` dimension.
    - `TS2` takes the first `C-*` dimension.
    - `TS3` takes the first `D-*` dimension.
3. Section 2 takes its slots from the remaining prioritized dimensions.
4. Section 4 prefers dimensions from the remaining pool whose `-status` is
    `in tension`, then falls back to the remaining Section 2 order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SectionSlot:
    dim_field: str
    ppp_field: str | None = None
    pps1_field: str | None = None
    devt_type_field: str | None = None
    devt_explain_if_conflicting_field: str | None = None


def conflict_explanation(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("conflict:"):
        return normalized.removeprefix("conflict:").strip()
    return ""
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


def first_dimension_for_family(priority: list[str], family_prefix: str) -> str | None:
    for dimension in priority:
        if dimension.startswith(f"{family_prefix}-"):
            return dimension
    return None


def select_section_dimensions(
    schema: SlotPopulationSchema,
    record: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    section1_slot_count = len(schema.section1_slots)
    section2_slot_count = len(schema.section2_slots)
    section3_slot_count = len(schema.section3_slots)
    priority = ordered_unique(
        [dimension for dimension in schema.dimensions if record.get(f"{dimension}-status")]
        + [dimension for dimension in schema.dimensions if record.get(f"{dimension}-devt")]
        + schema.dimensions
    )

    section1: list[str] = []
    for family_prefix in ["B", "C", "D"][:section1_slot_count]:
        selected_dimension = first_dimension_for_family(priority, family_prefix)
        if selected_dimension:
            section1.append(selected_dimension)

    remaining = [dimension for dimension in priority if dimension not in section1]

    if len(section1) < section1_slot_count:
        section1.extend(remaining[: section1_slot_count - len(section1)])
        remaining = [dimension for dimension in priority if dimension not in section1]

    section2 = remaining[:section2_slot_count]
    remaining_after_section2 = [dimension for dimension in remaining if dimension not in section2]
    tension_dims = [
        dimension
        for dimension in section2 + remaining_after_section2
        if record.get(f"{dimension}-status") == "in tension"
    ]
    tension_priority = ordered_unique(tension_dims + section2 + remaining_after_section2)
    section3 = tension_priority[:section3_slot_count]
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
        if slot.devt_type_field:
            target[slot.devt_type_field] = source_record.get(f"{dimension}-devt_converged", "")
        if slot.devt_explain_if_conflicting_field:
            target[slot.devt_explain_if_conflicting_field] = conflict_explanation(
                source_record.get(f"{dimension}-devt_converged_health", "")
            )

    for dimension, slot in zip(section2_dims, schema.section2_slots, strict=False):
        target[slot.dim_field] = schema.short_to_dotted_dimension[dimension]
        if slot.ppp_field:
            target[slot.ppp_field] = source_record.get(f"{dimension}-PPP", "")
        if slot.pps1_field:
            target[slot.pps1_field] = source_record.get(f"{dimension}-PPS1", "")
        if slot.devt_type_field:
            target[slot.devt_type_field] = source_record.get(f"{dimension}-devt_converged", "")
        if slot.devt_explain_if_conflicting_field:
            target[slot.devt_explain_if_conflicting_field] = conflict_explanation(
                source_record.get(f"{dimension}-devt_converged_health", "")
            )

    for dimension, slot in zip(section3_dims, schema.section3_slots, strict=False):
        target[slot.dim_field] = schema.short_to_dotted_dimension[dimension]
        if slot.pps1_field:
            target[slot.pps1_field] = source_record.get(f"{dimension}-PPS1", "")
        if slot.devt_type_field:
            target[slot.devt_type_field] = source_record.get(f"{dimension}-devt_converged", "")
        if slot.devt_explain_if_conflicting_field:
            target[slot.devt_explain_if_conflicting_field] = conflict_explanation(
                source_record.get(f"{dimension}-devt_converged_health", "")
            )
