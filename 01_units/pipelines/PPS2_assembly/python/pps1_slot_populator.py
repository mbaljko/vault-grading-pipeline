"""Populate PPS1 section-slot fields from dimension-level source fields.

This module isolates the slot-selection heuristic used by the PPS1 importer.
It expects a schema-like object that exposes:

- `dimensions`: ordered short dimension keys such as `B-1`
- `short_to_dotted_dimension`: mapping such as `B-1 -> B.2.1`
- `section1_slots`, `section2_slots`, `section3_slots`: ordered slot definitions

The source record is the already-assembled flat record containing direct LMS
fields plus the derived `*-devt_converged` and `*-status` fields. The target
mapping is typically the importer's `sectionDerived` block.

Slots populated by this module:

- Section 1 slots:
    - `Sec1_TS1_dim`, `Sec1_TS1_PPP`, `Sec1_TS1_PPS1`, `Sec1_TS1_devt_type`, `Sec1_TS1_devt_explain_if_conflicting`
    - `Sec1_TS2_dim`, `Sec1_TS2_PPP`, `Sec1_TS2_PPS1`, `Sec1_TS2_devt_type`, `Sec1_TS2_devt_explain_if_conflicting`
    - `Sec1_TS3_dim`, `Sec1_TS3_PPP`, `Sec1_TS3_PPS1`, `Sec1_TS3_devt_type`, `Sec1_TS3_devt_explain_if_conflicting`
- Section 2 slots:
    - `Sec2_V1_dim`, `Sec2_V1_PPP`, `Sec2_V1_PPS1`, `Sec2_V1_devt_type`, `Sec2_V1_devt_explain_if_conflicting`
    - `Sec2_V2_dim`, `Sec2_V2_PPP`, `Sec2_V2_PPS1`, `Sec2_V2_devt_type`, `Sec2_V2_devt_explain_if_conflicting`
- Section 4 slots:
    - `Sec4_Slot1_dim`, `Sec4_Slot1_PPS1`, `Sec4_Slot1_devt_type`, `Sec4_Slot1_devt_explain_if_conflicting`
    - `Sec4_Slot2_dim`, `Sec4_Slot2_PPS1`, `Sec4_Slot2_devt_type`, `Sec4_Slot2_devt_explain_if_conflicting`
    - `Sec4_Slot3_dim`, `Sec4_Slot3_PPS1`, `Sec4_Slot3_devt_type`, `Sec4_Slot3_devt_explain_if_conflicting`

All populated `*_dim` fields use the longer human-friendly dimension labels.

Selection heuristic:

1. Build a prioritized dimension order by preferring non-empty
    `-devt_converged`, then schema dimension order.
2. Populate the Section 1 TS slots first from family-specific subsets of that
    prioritized order:
    - `TS1` takes the first non-tension `B-*` dimension when available,
        otherwise it falls back to the first remaining `B-*` dimension.
    - `TS2` takes the first non-tension `C-*` dimension when available,
        otherwise it falls back to the first remaining `C-*` dimension.
    - `TS3` takes the first non-tension `D-*` dimension when available,
        otherwise it falls back to the first remaining `D-*` dimension.
3. Section 2 takes its slots from the remaining pool while trying to avoid
    duplication with the TS selections. It prefers `B-*` and `C-*` dimensions,
    tries to include one from each of `B` and `C`, ranks development types as
    `intro`, then `cont-reinf`, then `shift`, and only falls back to `D-*`
    when needed to fill the populated V slots.
    - `V1` and `V2` participate in this selection.
4. Section 4 prefers dimensions from the remaining pool whose `-status` is
    `in tension`, then falls back to the remaining Section 2 order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


HUMAN_FRIENDLY_DIMENSIONS = {
    "B-1": "B-1 Institutional structures and organisational arrangements",
    "B-2": "B-2 Responsibility and accountability distribution",
    "B-3": "B-3 Institutional influence, constraint, and authority",
    "C-1": "C-1 Justice, accessibility, and harm",
    "C-2": "C-2 Assumptions about neutrality, efficiency, fairness, or objectivity",
    "C-3": "C-3 Criteria for identifying harm, exclusion, or accessibility barriers",
    "D-1": "D-1 Human responsibility vs AI-mediated delegation of responsibility",
    "D-2": "D-2 AI-mediated oversight, uncertainty, and verification practices",
    "D-3": "D-3 Role of tools or AI systems in shaping professional judgement",
}

SECTION2_DEVELOPMENT_PRIORITY = {
    "intro": 0,
    "cont-reinf": 1,
    "shift": 2,
}


@dataclass(frozen=True)
class SectionSlot:
    dim_field: str
    ppp_field: str | None = None
    pps1_field: str | None = None
    devt_type_field: str | None = None
    devt_explain_if_conflicting_field: str | None = None


def conflict_explanation(devt_type: str, health_value: str) -> str:
    if devt_type.strip() != "conflicting":
        return ""
    normalized = health_value.strip()
    if normalized:
        return normalized
    return ""


def display_dimension(
    schema: SlotPopulationSchema,
    dimension: str,
    *,
    human_friendly: bool,
) -> str:
    if human_friendly:
        return HUMAN_FRIENDLY_DIMENSIONS.get(
            dimension,
            schema.short_to_dotted_dimension[dimension],
        )
    return schema.short_to_dotted_dimension[dimension]


class SlotPopulationSchema(Protocol):
    dimensions: list[str]
    short_to_dotted_dimension: dict[str, str]
    section1_slots: list[SectionSlot]
    section2_slots: list[SectionSlot]
    section3_slots: list[SectionSlot]
    slot_population_audit_note_field: str | None


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


def first_non_tension_dimension_for_family(
    priority: list[str],
    record: dict[str, str],
    family_prefix: str,
) -> str | None:
    for dimension in priority:
        if not dimension.startswith(f"{family_prefix}-"):
            continue
        if record.get(f"{dimension}-status") != "in tension":
            return dimension
    return None


def normalized_section2_development_type(record: dict[str, str], dimension: str) -> str:
    return record.get(f"{dimension}-devt_converged", "").strip().lower().replace("_", "-")


def rank_section2_dimensions(priority: list[str], record: dict[str, str], dimensions: list[str]) -> list[str]:
    priority_index = {dimension: index for index, dimension in enumerate(priority)}

    def ranking_key(dimension: str) -> tuple[int, int]:
        development_type = normalized_section2_development_type(record, dimension)
        development_rank = SECTION2_DEVELOPMENT_PRIORITY.get(
            development_type,
            len(SECTION2_DEVELOPMENT_PRIORITY),
        )
        return development_rank, priority_index[dimension]

    return sorted(dimensions, key=ranking_key)


def select_section2_dimensions(
    section2_slot_count: int,
    priority: list[str],
    record: dict[str, str],
    remaining: list[str],
) -> list[str]:
    if section2_slot_count <= 0:
        return []

    ranked_remaining = rank_section2_dimensions(priority, record, remaining)
    remaining_by_family = {
        family: [dimension for dimension in ranked_remaining if dimension.startswith(f"{family}-")]
        for family in ("B", "C", "D")
    }

    section2: list[str] = []
    for family in ("B", "C"):
        family_candidates = remaining_by_family[family]
        if family_candidates and len(section2) < section2_slot_count:
            section2.append(family_candidates[0])

    ranked_fill_order = [
        dimension for dimension in ranked_remaining if dimension.startswith(("B-", "C-")) and dimension not in section2
    ]
    ranked_fill_order.extend(
        dimension for dimension in ranked_remaining if dimension.startswith("D-") and dimension not in section2
    )
    ranked_fill_order.extend(
        dimension
        for dimension in ranked_remaining
        if not dimension.startswith(("B-", "C-", "D-")) and dimension not in section2
    )

    for dimension in ranked_fill_order:
        if len(section2) >= section2_slot_count:
            break
        section2.append(dimension)

    return section2


def select_section_dimensions(
    schema: SlotPopulationSchema,
    record: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    section1_slot_count = len(schema.section1_slots)
    section2_slot_count = len(schema.section2_slots)
    section3_slot_count = len(schema.section3_slots)
    priority = ordered_unique(
        [dimension for dimension in schema.dimensions if record.get(f"{dimension}-devt_converged")]
        + schema.dimensions
    )

    section1: list[str] = []
    for family_prefix in ["B", "C", "D"][:section1_slot_count]:
        selected_dimension = first_non_tension_dimension_for_family(priority, record, family_prefix)
        if not selected_dimension:
            selected_dimension = first_dimension_for_family(priority, family_prefix)
        if selected_dimension:
            section1.append(selected_dimension)

    remaining = [dimension for dimension in priority if dimension not in section1]

    if len(section1) < section1_slot_count:
        section1.extend(remaining[: section1_slot_count - len(section1)])
        remaining = [dimension for dimension in priority if dimension not in section1]

    section2 = select_section2_dimensions(section2_slot_count, priority, record, remaining)
    remaining_after_section2 = [dimension for dimension in remaining if dimension not in section2]
    tension_dims = [
        dimension
        for dimension in section2 + remaining_after_section2
        if record.get(f"{dimension}-status") == "in tension"
    ]
    tension_priority = ordered_unique(tension_dims + section2 + remaining_after_section2)
    section3 = tension_priority[:section3_slot_count]
    return section1, section2, section3


def describe_section1_reason(record: dict[str, str], dimension: str) -> str:
    if record.get(f"{dimension}-status") != "in tension":
        return "non-tension"
    return "family-fallback"


def describe_section2_reason(record: dict[str, str], dimension: str) -> str:
    devt_type = normalized_section2_development_type(record, dimension) or "none"
    if dimension.startswith(("B-", "C-")):
        return f"BC-pref/{devt_type}"
    if dimension.startswith("D-"):
        return f"D-fallback/{devt_type}"
    return f"other/{devt_type}"


def describe_section3_reason(record: dict[str, str], dimension: str) -> str:
    if record.get(f"{dimension}-status") == "in tension":
        return "tension-first"
    return "remaining-fallback"


def build_slot_population_audit_note(
    record: dict[str, str],
    section1_dims: list[str],
    section2_dims: list[str],
    section3_dims: list[str],
) -> str:
    parts: list[str] = []

    if section1_dims:
        section1_notes = [
            f"TS{index}={dimension} {describe_section1_reason(record, dimension)}"
            for index, dimension in enumerate(section1_dims, start=1)
        ]
        parts.append("TS: " + ", ".join(section1_notes))

    if section2_dims:
        section2_notes = [
            f"V{index}={dimension} {describe_section2_reason(record, dimension)}"
            for index, dimension in enumerate(section2_dims, start=1)
        ]
        parts.append("V: " + ", ".join(section2_notes))

    if section3_dims:
        section3_notes = [
            f"Slot{index}={dimension} {describe_section3_reason(record, dimension)}"
            for index, dimension in enumerate(section3_dims, start=1)
        ]
        parts.append("Sec4: " + ", ".join(section3_notes))

    return " | ".join(parts)


def populate_section_fields(
    schema: SlotPopulationSchema,
    target: dict[str, str],
    source_record: dict[str, str],
) -> None:
    section1_dims, section2_dims, section3_dims = select_section_dimensions(schema, source_record)

    for dimension, slot in zip(section1_dims, schema.section1_slots, strict=False):
        target[slot.dim_field] = display_dimension(schema, dimension, human_friendly=True)
        if slot.ppp_field:
            target[slot.ppp_field] = source_record.get(f"{dimension}-PPP", "")
        if slot.pps1_field:
            target[slot.pps1_field] = source_record.get(f"{dimension}-PPS1", "")
        devt_type = source_record.get(f"{dimension}-devt_converged", "")
        if slot.devt_type_field:
            target[slot.devt_type_field] = devt_type
        if slot.devt_explain_if_conflicting_field:
            target[slot.devt_explain_if_conflicting_field] = conflict_explanation(
                devt_type,
                source_record.get(f"{dimension}-devt_converged_health", ""),
            )

    for dimension, slot in zip(section2_dims, schema.section2_slots, strict=False):
        target[slot.dim_field] = display_dimension(schema, dimension, human_friendly=True)
        if slot.ppp_field:
            target[slot.ppp_field] = source_record.get(f"{dimension}-PPP", "")
        if slot.pps1_field:
            target[slot.pps1_field] = source_record.get(f"{dimension}-PPS1", "")
        devt_type = source_record.get(f"{dimension}-devt_converged", "")
        if slot.devt_type_field:
            target[slot.devt_type_field] = devt_type
        if slot.devt_explain_if_conflicting_field:
            target[slot.devt_explain_if_conflicting_field] = conflict_explanation(
                devt_type,
                source_record.get(f"{dimension}-devt_converged_health", ""),
            )

    for dimension, slot in zip(section3_dims, schema.section3_slots, strict=False):
        target[slot.dim_field] = display_dimension(schema, dimension, human_friendly=True)
        if slot.pps1_field:
            target[slot.pps1_field] = source_record.get(f"{dimension}-PPS1", "")
        devt_type = source_record.get(f"{dimension}-devt_converged", "")
        if slot.devt_type_field:
            target[slot.devt_type_field] = devt_type
        if slot.devt_explain_if_conflicting_field:
            target[slot.devt_explain_if_conflicting_field] = conflict_explanation(
                devt_type,
                source_record.get(f"{dimension}-devt_converged_health", ""),
            )

    if schema.slot_population_audit_note_field:
        target[schema.slot_population_audit_note_field] = build_slot_population_audit_note(
            source_record,
            section1_dims,
            section2_dims,
            section3_dims,
        )
