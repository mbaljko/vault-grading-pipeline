#!/usr/bin/env python3
"""Generate a Layer 1 rubric payload and scoring manifest from an indicator registry.

This script reads a markdown indicator registry table, extracts the Layer 1
indicator rows, and writes two markdown outputs in the same directory by
default:

- RUBRIC_<ASSESSMENT>_CAL_payload_<VERSION>.md
- <ASSESSMENT>_Layer1_ScoringManifest_<VERSION>.md

The generated documents follow the same structural conventions as the existing
pl1C_rubric_devt rubric payload and scoring manifest examples.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


REQUIRED_REGISTRY_COLUMNS = {
    "indicator_id",
    "sbo_identifier",
    "sbo_identifier_shortid",
    "assessment_id",
    "component_id",
    "sbo_short_description",
    "indicator_definition",
    "assessment_guidance",
    "evaluation_notes",
}
VERSION_TOKEN_RE = re.compile(r"_(v(?:_i)?\d+)\.md$", re.IGNORECASE)
SHORTID_NUMBER_RE = re.compile(r"(\d+)")


@dataclass(frozen=True)
class IndicatorRow:
    indicator_id: str
    sbo_identifier: str
    sbo_identifier_shortid: str
    assessment_id: str
    component_id: str
    sbo_short_description: str
    indicator_definition: str
    assessment_guidance: str
    evaluation_notes: str
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate rubric and scoring manifest markdown from an indicator registry."
    )
    parser.add_argument(
        "--indicator-registry",
        type=Path,
        required=True,
        help="Path to the markdown indicator registry file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for generated outputs. Defaults to the registry file directory.",
    )
    parser.add_argument(
        "--rubric-output",
        type=Path,
        help="Explicit rubric output file path. Overrides --output-dir naming.",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        help="Explicit manifest output file path. Overrides --output-dir naming.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include rows whose status is not 'active'.",
    )
    return parser.parse_args()


def normalize_markdown_cell(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1].strip()
    return stripped


def parse_markdown_row(line: str) -> list[str]:
    parts = [part.strip() for part in line.strip().split("|")]
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [normalize_markdown_cell(part) for part in parts]


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    compact = [cell.replace(" ", "") for cell in cells]
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in compact)


def load_indicator_rows(registry_path: Path, include_inactive: bool) -> list[IndicatorRow]:
    lines = registry_path.read_text(encoding="utf-8").splitlines()

    header_cells: list[str] | None = None
    rows: list[IndicatorRow] = []

    for line in lines:
        if "|" not in line:
            continue
        cells = parse_markdown_row(line)
        if not cells:
            continue

        if header_cells is None:
            lowered = {cell.strip().lower() for cell in cells}
            if REQUIRED_REGISTRY_COLUMNS.issubset(lowered):
                header_cells = [cell.strip().lower() for cell in cells]
            continue

        if is_separator_row(cells):
            continue
        if len(cells) != len(header_cells):
            continue

        record = dict(zip(header_cells, cells, strict=True))
        status = record.get("status", "").strip().lower()
        if not include_inactive and status and status != "active":
            continue

        rows.append(
            IndicatorRow(
                indicator_id=record["indicator_id"],
                sbo_identifier=record["sbo_identifier"],
                sbo_identifier_shortid=record["sbo_identifier_shortid"],
                assessment_id=record["assessment_id"],
                component_id=record["component_id"],
                sbo_short_description=record["sbo_short_description"],
                indicator_definition=record["indicator_definition"],
                assessment_guidance=record["assessment_guidance"],
                evaluation_notes=record["evaluation_notes"],
                status=record.get("status", ""),
            )
        )

    if header_cells is None:
        raise ValueError(f"Could not locate a valid indicator registry table in: {registry_path}")
    if not rows:
        raise ValueError(f"No indicator rows were loaded from registry: {registry_path}")

    assessment_ids = {row.assessment_id for row in rows}
    if len(assessment_ids) != 1:
        raise ValueError(f"Expected one assessment_id in registry, found: {sorted(assessment_ids)}")

    return sorted(rows, key=indicator_sort_key)


def indicator_sort_key(row: IndicatorRow) -> tuple[str, int, str]:
    match = SHORTID_NUMBER_RE.search(row.sbo_identifier_shortid)
    shortid_number = int(match.group(1)) if match else 0
    return row.component_id, shortid_number, row.sbo_identifier


def extract_version_token(registry_path: Path) -> str:
    match = VERSION_TOKEN_RE.search(registry_path.name)
    if match:
        return match.group(1)
    return "v01"


def resolve_output_paths(
    registry_path: Path,
    assessment_id: str,
    version_token: str,
    output_dir: Path | None,
    rubric_output: Path | None,
    manifest_output: Path | None,
) -> tuple[Path, Path]:
    resolved_output_dir = output_dir.resolve() if output_dir else registry_path.parent.resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    rubric_path = (
        with_registry_version_suffix(rubric_output.resolve(), version_token)
        if rubric_output
        else resolved_output_dir / f"RUBRIC_{assessment_id}_CAL_payload_{version_token}.md"
    )
    manifest_path = (
        with_registry_version_suffix(manifest_output.resolve(), version_token)
        if manifest_output
        else resolved_output_dir / f"{assessment_id}_Layer1_ScoringManifest_{version_token}.md"
    )
    rubric_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    return rubric_path, manifest_path


def with_registry_version_suffix(output_path: Path, version_token: str) -> Path:
    match = VERSION_TOKEN_RE.search(output_path.name)
    if match:
        updated_name = VERSION_TOKEN_RE.sub(f"_{version_token}.md", output_path.name)
        return output_path.with_name(updated_name)
    return output_path


def group_rows_by_component(rows: list[IndicatorRow]) -> dict[str, list[IndicatorRow]]:
    grouped: dict[str, list[IndicatorRow]] = defaultdict(list)
    for row in rows:
        grouped[row.component_id].append(row)
    return dict(sorted(grouped.items()))


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    body_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator_line, *body_lines])


def render_rubric_document(title_stem: str, assessment_id: str, rows: list[IndicatorRow]) -> str:
    component_rows = group_rows_by_component(rows)

    layer_1_instance_rows = [
        [
            row.sbo_identifier,
            row.sbo_identifier_shortid,
            row.assessment_id,
            row.component_id,
            row.indicator_id,
            row.sbo_short_description,
        ]
        for row in rows
    ]

    parts: list[str] = [
        f"## {title_stem}",
        "### 0A. Purpose",
        "Defines the **structural schema of a rubric payload** used to evaluate **participant assignment artefacts**.",
        "",
        "The rubric operates under the **four-layer scoring ontology**.",
        "Authoring conventions, identifier rules, and mapping semantics are defined in `Rubric_SpecificationGuide_v02`.",
        "",
        render_markdown_table(
            ["layer", "SBO class"],
            [
                ["Layer 1", "indicator"],
                ["Layer 2", "dimension"],
                ["Layer 3", "component"],
                ["Layer 4", "submission-level aggregate"],
            ],
        ),
        "### 0B. Identifier Registry",
        "",
        render_markdown_table(
            ["identifier", "level", "meaning", "used in"],
            [
                ["`assessment_id`", "rubric specification", "identifies the assessment for which the rubric payload is authored", "rubric payload, SBO instance registries"],
                ["`participant_id`", "dataset / scoring input", "identifies one participant artefact in the canonical dataset and scoring inputs", "canonical datasets, runtime assessment artefacts"],
                ["`submission_id`", "scoring output schema", "standardised output field name used when participant identifiers are emitted by scoring pipelines", "runtime scoring outputs, scoring prompt output schemas"],
                ["`component_id`", "component", "identifies a component or response surface within the assessment", "datasets, rubric payload, scoring pipelines"],
                ["`dimension_id`", "rubric dimension", "identifies a dimension SBO within a component", "rubric payload"],
                ["`indicator_id`", "rubric indicator", "identifies an indicator SBO within a component", "rubric payload"],
            ],
        ),
        "",
        "### 1. Layer 4 SBO Registry",
        "",
        render_markdown_table(["field"], [["`submission_score`"]]),
        "### 2. Layer 3 SBO Registry",
        "",
        render_markdown_table(["field"], [["`component_score`"]]),
        "### 3. Layer 2 SBO Registry",
        "",
        render_markdown_table(["field"], [["`dimension_score`"]]),
        "### 4. Layer 1 SBO Registry",
        "",
        render_markdown_table(["field"], [["`indicator_score`"]]),
        "",
        "### 4A. Score Registry Summary",
        "",
        render_markdown_table(
            ["layer", "SBO class", "score field", "score meaning"],
            [
                ["Layer 1", "indicator", "`indicator_score`", "evidence status assigned to an indicator SBO"],
                ["Layer 2", "dimension", "`dimension_score`", "dimension-level evidence judgement derived from indicator evidence"],
                ["Layer 3", "component", "`component_score`", "component-level performance judgement derived from dimension evidence"],
                ["Layer 4", "submission-level aggregate", "`submission_score`", "assignment-level performance judgement derived from component scores"],
            ],
        ),
        "### 5. SBO Instance Registries",
        "Instance registries define the specific **Score-Bearing Object (SBO) instances** used by the rubric.",
        "Each instance must include:",
        "- `sbo_identifier`",
        "- `sbo_identifier_shortid`",
        "- any layer-specific identifier fields (for example `component_id`, `dimension_id`, or `indicator_id`)",
        "- `sbo_short_description`",
        "`sbo_identifier_shortid` is a compact token used in mapping tables and rule definitions.",
        "",
        "",
        "#### 5.4 Layer 1 SBO Instances (Draft)",
        "",
        render_markdown_table(
            [
                "sbo_identifier",
                "sbo_identifier_shortid",
                "assessment_id",
                "component_id",
                "indicator_id",
                "sbo_short_description",
            ],
            layer_1_instance_rows,
        ),
        "",
        "#### 5.3 Layer 2 SBO Instances",
        "Registry of **dimension SBO instances**.",
        "Required fields typically include:",
        "",
        render_markdown_table(
            ["field"],
            [
                ["`sbo_identifier`"],
                ["`sbo_identifier_shortid`"],
                ["`assessment_id`"],
                ["`component_id`"],
                ["`dimension_id`"],
                ["`sbo_short_description`"],
            ],
        ),
        "#### 5.2 Layer 3 SBO Instances",
        "Registry of **component SBO instances**.",
        "Required fields typically include:",
        "",
        render_markdown_table(
            ["field"],
            [
                ["`sbo_identifier`"],
                ["`sbo_identifier_shortid`"],
                ["`assessment_id`"],
                ["`component_id`"],
                ["`sbo_short_description`"],
            ],
        ),
        "#### 5.1 Layer 4 SBO Instances",
        "Registry of **submission SBO instances**.",
        "Required fields typically include:",
        "",
        render_markdown_table(
            ["field"],
            [
                ["`sbo_identifier`"],
                ["`sbo_identifier_shortid`"],
                ["`assessment_id`"],
                ["`sbo_short_description`"],
            ],
        ),
        "### 6. SBO Value Derivation Registries",
        "Value-derivation sections define how scores for each SBO layer are computed.",
        "These sections may contain:",
        "- registry summaries",
        "- evaluation guidance",
        "- mapping tables",
        "- fallback rules",
        "- interpretation notes",
        "",
        "",
        "#### 6.1 Layer 1 SBO Value Derivation (Draft)",
        "",
    ]

    for component_id, component_indicator_rows in component_rows.items():
        parts.extend(
            [
                f"##### Component: `{component_id}`",
                "",
                render_markdown_table(
                    [
                        "sbo_identifier",
                        "sbo_short_description",
                        "indicator_definition",
                        "assessment_guidance",
                        "evaluation_notes",
                    ],
                    [
                        [
                            row.sbo_identifier,
                            row.sbo_short_description,
                            row.indicator_definition,
                            row.assessment_guidance,
                            row.evaluation_notes,
                        ]
                        for row in component_indicator_rows
                    ],
                ),
                "",
            ]
        )

    parts.extend(
        [
            "#### 6.2 Layer 2 Value Derivation",
            "Derives `dimension_score` from indicator evidence.",
            "Typical contents:",
            "- indicator → dimension mapping tables",
            "- optional fallback rules",
            "- interpretation notes",
            "#### 6.3 Layer 3 Value Derivation",
            "Derives `component_score` from dimension evidence.",
            "Typical contents:",
            "- dimension → component mapping tables",
            "- optional boundary rules",
            "- interpretation notes",
            "#### 6.4 Layer 4 Value Derivation",
            "Derives `submission_score` from component scores.",
            "Typical contents:",
            "- component aggregation rules",
            "- optional fallback rules",
            "- interpretation notes",
            "### 7. Scoring Ontology and Identifier Context",
            "Evaluation hierarchy.",
            "",
            render_markdown_table(
                ["SBO class"],
                [
                    ["submission-level aggregate"],
                    ["component"],
                    ["dimension"],
                    ["indicator"],
                ],
            ),
            "",
            "Assessment artefact for Layers 1–3: `participant_id × component_id`.",
            "Assessment artefact for Layer 4: `participant_id`.",
            "",
            "The rubric payload itself is authored at the **assessment level**, using the identifier:",
            "",
            "`assessment_id`",
            "",
            "During scoring, participant artefacts identified by `participant_id` are evaluated using this rubric specification.",
            "### 8. Rubric Stability States",
            "",
            render_markdown_table(
                ["state"],
                [["Draft"], ["Under Evaluation"], ["Stabilised"], ["Frozen"]],
            ),
            "### 9. Scale Registry",
            "Defines the scoring scales used by the rubric.",
            "",
            render_markdown_table(
                ["scale_name", "scale_type"],
                [
                    ["`indicator_evidence_scale`", "evidence"],
                    ["`dimension_evidence_scale`", "evidence"],
                    ["`component_performance_scale`", "performance"],
                    ["`submission_performance_scale`", "performance"],
                ],
            ),
            "",
        ]
    )

    return "\n".join(parts)


def render_manifest_document(title_stem: str, assessment_id: str, rows: list[IndicatorRow]) -> str:
    component_rows = group_rows_by_component(rows)
    manifest_rows = [
        [
            row.component_id,
            f"`{row.sbo_identifier}`",
            f"`{row.indicator_id}`",
            f"`{row.sbo_short_description}`",
            row.indicator_definition,
            row.assessment_guidance,
            row.evaluation_notes,
        ]
        for row in rows
    ]

    parts = [
        f"## {title_stem}",
        "",
        "### 1. Manifest metadata",
        "",
        render_markdown_table(
            ["field", "value"],
            [
                ["assessment_id", assessment_id],
                ["scoring_layer", "Layer1"],
                ["scoring_scope", "participant_id × component_id"],
                ["ontology_reference", "Rubric_SpecificationGuide_v*"],
                ["expected_input_identifier", "participant_id"],
                ["runtime_output_identifier", "submission_id"],
                ["component_registry_count", str(len(component_rows))],
                ["total_indicator_count", str(len(rows))],
            ],
        ),
        "",
        "### 2. Identifier context",
        "",
        "Scoring unit:",
        "",
        "```text",
        "participant_id × component_id",
        "```",
        "",
        "Identifier relationship:",
        "",
        "```text",
        "submission_id ↔ participant_id",
        "```",
        "",
        "### 3. Layer 1 Indicator Scoring Manifest",
        "",
        render_markdown_table(
            [
                "component_id",
                "sbo_identifier",
                "indicator_id",
                "sbo_short_description",
                "indicator_definition",
                "assessment_guidance",
                "evaluation_notes",
            ],
            manifest_rows,
        ),
        "",
    ]
    return "\n".join(parts)


def main() -> int:
    args = parse_args()

    registry_path = args.indicator_registry.resolve()
    if not registry_path.exists():
        raise FileNotFoundError(f"Indicator registry not found: {registry_path}")

    rows = load_indicator_rows(registry_path, include_inactive=args.include_inactive)
    assessment_id = rows[0].assessment_id
    version_token = extract_version_token(registry_path)

    rubric_path, manifest_path = resolve_output_paths(
        registry_path=registry_path,
        assessment_id=assessment_id,
        version_token=version_token,
        output_dir=args.output_dir,
        rubric_output=args.rubric_output,
        manifest_output=args.manifest_output,
    )

    rubric_text = render_rubric_document(rubric_path.stem, assessment_id, rows)
    manifest_text = render_manifest_document(manifest_path.stem, assessment_id, rows)

    rubric_path.write_text(rubric_text, encoding="utf-8")
    manifest_path.write_text(manifest_text, encoding="utf-8")

    print(f"Indicator registry: {registry_path}")
    print(f"Rubric output: {rubric_path}")
    print(f"Manifest output: {manifest_path}")
    print(f"Assessment: {assessment_id}")
    print(f"Indicators written: {len(rows)}")
    print(f"Components written: {len(group_rows_by_component(rows))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())