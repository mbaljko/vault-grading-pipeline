from __future__ import annotations

import csv
import importlib.util
import tempfile
from pathlib import Path
import unittest


_L3_SUBMISSION_PAYLOAD_PATH = Path(__file__).with_name("generate-layer3-submission-payload.py")
_L3_SUBMISSION_PAYLOAD_SPEC = importlib.util.spec_from_file_location(
    "generate_layer3_submission_payload",
    _L3_SUBMISSION_PAYLOAD_PATH,
)
if _L3_SUBMISSION_PAYLOAD_SPEC is None or _L3_SUBMISSION_PAYLOAD_SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {_L3_SUBMISSION_PAYLOAD_PATH}")
_L3_SUBMISSION_PAYLOAD_MODULE = importlib.util.module_from_spec(_L3_SUBMISSION_PAYLOAD_SPEC)
_L3_SUBMISSION_PAYLOAD_SPEC.loader.exec_module(_L3_SUBMISSION_PAYLOAD_MODULE)
build_output_rows = _L3_SUBMISSION_PAYLOAD_MODULE.build_output_rows


_L4_EXECUTOR_PATH = Path(__file__).with_name("execute-layer4-submission-scoring-modules.py")
_L4_EXECUTOR_SPEC = importlib.util.spec_from_file_location(
    "execute_layer4_submission_scoring_modules",
    _L4_EXECUTOR_PATH,
)
if _L4_EXECUTOR_SPEC is None or _L4_EXECUTOR_SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {_L4_EXECUTOR_PATH}")
_L4_EXECUTOR_MODULE = importlib.util.module_from_spec(_L4_EXECUTOR_SPEC)
_L4_EXECUTOR_SPEC.loader.exec_module(_L4_EXECUTOR_MODULE)
score_submission_row = _L4_EXECUTOR_MODULE.score_submission_row
build_l3_comment_lookup = _L4_EXECUTOR_MODULE.build_l3_comment_lookup
build_wide_output_rows = _L4_EXECUTOR_MODULE.build_wide_output_rows


_PREPARE_WORKSHEET_PATH = Path(__file__).parents[2] / "pl3_production_scoring/python/prepare_scored_worksheet_with_comment_columns.py"
_PREPARE_WORKSHEET_SPEC = importlib.util.spec_from_file_location(
    "prepare_scored_worksheet_with_comment_columns",
    _PREPARE_WORKSHEET_PATH,
)
if _PREPARE_WORKSHEET_SPEC is None or _PREPARE_WORKSHEET_SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {_PREPARE_WORKSHEET_PATH}")
_PREPARE_WORKSHEET_MODULE = importlib.util.module_from_spec(_PREPARE_WORKSHEET_SPEC)
_PREPARE_WORKSHEET_SPEC.loader.exec_module(_PREPARE_WORKSHEET_MODULE)
build_grouped_feedback = _PREPARE_WORKSHEET_MODULE._build_grouped_feedback
derive_grouped_component_layout = _PREPARE_WORKSHEET_MODULE._derive_grouped_component_layout


class Layer3SubmissionPayloadL3CommentTests(unittest.TestCase):
    def test_payload_includes_l3_comment_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "layer3_component_output.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "submission_id",
                        "component_id",
                        "sbo_identifier",
                        "component_score",
                        "L3_Comment",
                        "flags_any_dimension",
                        "min_confidence_dimension",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "submission_id": "1001",
                        "component_id": "B1Response",
                        "sbo_identifier": "C_AP2B_SecB1",
                        "component_score": "meets_expectations",
                        "L3_Comment": "Clear developmental interpretation.",
                        "flags_any_dimension": "none",
                        "min_confidence_dimension": "high",
                    }
                )
                writer.writerow(
                    {
                        "submission_id": "1001",
                        "component_id": "C1Response",
                        "sbo_identifier": "C_AP2B_SecC1",
                        "component_score": "approaching_expectations",
                        "L3_Comment": "Analytical grounding partially present.",
                        "flags_any_dimension": "none",
                        "min_confidence_dimension": "medium",
                    }
                )

            rows = build_output_rows(
                input_files=[input_path],
                submission_id_field="submission_id",
                component_id_field="component_id",
                sbo_identifier_field="sbo_identifier",
                score_field="component_score",
                comment_field="L3_Comment",
                flags_field="flags_any_dimension",
                confidence_field="min_confidence_dimension",
            )

        self.assertEqual(len(rows), 1)
        output_row = rows[0]
        self.assertEqual(output_row["L3_comment__B1Response"], "Clear developmental interpretation.")
        self.assertEqual(output_row["L3_comment__C_AP2B_SecB1"], "Clear developmental interpretation.")
        self.assertEqual(output_row["L3_comment__C1Response"], "Analytical grounding partially present.")
        self.assertEqual(output_row["L3_comment__C_AP2B_SecC1"], "Analytical grounding partially present.")
        self.assertEqual(
            output_row["L3_comment"],
            "Clear developmental interpretation. | Analytical grounding partially present.",
        )


class Layer4ExecutionL3CommentPropagationTests(unittest.TestCase):
    def test_layer4_output_row_preserves_l3_comment(self) -> None:
        class DummyLayer4Module:
            SBO_IDENTIFIER = "S_AP2B"
            SBO_SHORT_DESCRIPTION = "submission aggregate"
            SUBMISSION_PERFORMANCE_SCALE = ["not_demonstrated", "meets_expectations"]
            BOUND_COMPONENT_IDS = ["B1Response", "C1Response"]

            @staticmethod
            def score_submission(component_scores: dict[str, str]) -> dict[str, object]:
                self_scores = {
                    "B1Response": 2.0,
                    "C1Response": 1.0,
                }
                return {
                    "submission_numeric_score": 3.0,
                    "submission_score": "meets_expectations",
                    "source_component_numeric_values": self_scores,
                }

        input_row = {
            "submission_id": "1001",
            "component_score__B1Response": "meets_expectations",
            "component_score__C1Response": "approaching_expectations",
            "L3_comment": "Clear developmental interpretation. | Analytical grounding partially present.",
            "L3_comment__B1Response": "Clear developmental interpretation.",
            "L3_comment__C1Response": "Analytical grounding partially present.",
            "flags_any_component": "none",
            "min_confidence_component": "medium",
        }

        output_row = score_submission_row(
            DummyLayer4Module,
            input_row,
            submission_max_numeric_score="4.00",
            submission_id_field="submission_id",
            flags_field="flags_any_component",
            confidence_field="min_confidence_component",
        )

        self.assertEqual(
            output_row["L3_comment"],
            "Clear developmental interpretation. | Analytical grounding partially present.",
        )
        self.assertEqual(output_row["L3_comment__B1Response"], "Clear developmental interpretation.")
        self.assertEqual(output_row["L3_comment__C1Response"], "Analytical grounding partially present.")

    def test_wide_output_preserves_component_l3_comment_columns(self) -> None:
        output_rows = [
            {
                "submission_id": "1001",
                "submission_score": "meets_expectations",
                "submission_numeric_score": "3.00",
                "submission_max_numeric_score": "3.00",
                "L3_comment": "Clear developmental interpretation. | Analytical grounding partially present.",
                "L3_comment__B1Response": "Clear developmental interpretation.",
                "L3_comment__C1Response": "Analytical grounding partially present.",
                "component_score__B1Response": "meets_expectations",
                "component_score__C1Response": "approaching_expectations",
                "source_component_numeric_values_json": '{"B1Response":"2.00","C1Response":"1.00"}',
                "flags_any_component": "none",
                "min_confidence_component": "medium",
            }
        ]

        headers, wide_rows = build_wide_output_rows(
            output_rows,
            bound_component_ids=["B1Response", "C1Response"],
            layer3_wide_blocks=[],
            response_component_ids=["B1Response", "C1Response"],
            response_text_lookup={"1001": {"B1Response": "Claim 1", "C1Response": "Claim 2"}},
        )

        self.assertIn("L3_comment__B1Response", headers)
        self.assertIn("L3_comment__C1Response", headers)
        wide_row = dict(zip(headers, wide_rows[0]))
        self.assertEqual(wide_row["L3_comment__B1Response"], "Clear developmental interpretation.")
        self.assertEqual(wide_row["L3_comment__C1Response"], "Analytical grounding partially present.")


class PrepareWorksheetGroupedFeedbackTests(unittest.TestCase):
    def test_grouped_feedback_uses_component_blocks_for_multi_claim_section(self) -> None:
        header = [
            "submission_numeric_score",
            "submission_max_numeric_score",
            "submission_score",
            "SectionB1Response_response_text",
            "SectionB2Response_response_text",
            "SectionB3Response_response_text",
            "D11",
            "D12",
            "D13",
            "D14",
            "D21",
            "D22",
            "D23",
            "D24",
            "D31",
            "D32",
            "D33",
            "D34",
            "L3_comment__SectionB1Response",
            "L3_comment__SectionB2Response",
            "L3_comment__SectionB3Response",
        ]
        grouped_section_label, grouped_component_layout = derive_grouped_component_layout(
            header,
            r"^(.*)_response_text$",
            "Response",
            ["D11", "D12", "D13", "D14", "D21", "D22", "D23", "D24", "D31", "D32", "D33", "D34"],
        )
        self.assertEqual(grouped_section_label, "SectionB")

        row = {
            "D11": "1-demonstrated",
            "D12": "1-demonstrated",
            "D13": "1-demonstrated",
            "D14": "1-demonstrated",
            "D21": "1-demonstrated",
            "D22": "1-demonstrated",
            "D23": "1-demonstrated",
            "D24": "0-little_to_no_demonstration",
            "D31": "1-demonstrated",
            "D32": "1-demonstrated",
            "D33": "1-demonstrated",
            "D34": "0-little_to_no_demonstration",
            "L3_comment__SectionB1Response": "Claim is structurally complete and clearly identifies an actor, tool or artefact, mediation action, workflow stage, and valid action-object relationship within the required template structure.",
            "L3_comment__SectionB2Response": "Claim identifies an actor, tool or artefact, mediation action, and workflow stage, but the action-object relationship is structurally incomplete or insufficiently specified.",
            "L3_comment__SectionB3Response": "Claim identifies an actor, tool or artefact, mediation action, and workflow stage, but the action-object relationship is structurally incomplete or insufficiently specified.",
        }

        feedback = build_grouped_feedback(
            row,
            "Overall result for {section_label}: {grade} ({score} / {max_score}). {dimension_count} {dimension_word}.",
            "  {dimension}: {value}",
            grouped_section_label,
            "meets_expectations",
            "13",
            "15",
            grouped_component_layout,
            r"^\d+-",
        )

        expected = "\n".join(
            [
                "Overall result for SectionB: meets expectations (13 / 15). 12 dimensions.",
                "SectionB1",
                "  D11: demonstrated",
                "  D12: demonstrated",
                "  D13: demonstrated",
                "  D14: demonstrated",
                "Claim is structurally complete and clearly identifies an actor, tool or artefact, mediation action, workflow stage, and valid action-object relationship within the required template structure.",
                "SectionB2",
                "  D21: demonstrated",
                "  D22: demonstrated",
                "  D23: demonstrated",
                "  D24: little_to_no_demonstration",
                "Claim identifies an actor, tool or artefact, mediation action, and workflow stage, but the action-object relationship is structurally incomplete or insufficiently specified.",
                "SectionB3",
                "  D31: demonstrated",
                "  D32: demonstrated",
                "  D33: demonstrated",
                "  D34: little_to_no_demonstration",
                "Claim identifies an actor, tool or artefact, mediation action, and workflow stage, but the action-object relationship is structurally incomplete or insufficiently specified.",
            ]
        )
        self.assertEqual(feedback, expected)

    def test_layer4_output_row_can_backfill_l3_comment_from_component_outputs(self) -> None:
        class DummyLayer4Module:
            SBO_IDENTIFIER = "S_AP2B"
            SBO_SHORT_DESCRIPTION = "submission aggregate"
            SUBMISSION_PERFORMANCE_SCALE = ["not_demonstrated", "meets_expectations"]
            BOUND_COMPONENT_IDS = ["B1Response", "C1Response"]

            @staticmethod
            def score_submission(component_scores: dict[str, str]) -> dict[str, object]:
                self_scores = {
                    "B1Response": 2.0,
                    "C1Response": 1.0,
                }
                return {
                    "submission_numeric_score": 3.0,
                    "submission_score": "meets_expectations",
                    "source_component_numeric_values": self_scores,
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "RUN_PPS1D23_Layer3_submission_payload_v01.csv"
            payload_path.write_text(
                "submission_id,component_score__B1Response,component_score__C1Response\n"
                "1001,meets_expectations,approaching_expectations\n",
                encoding="utf-8",
            )
            component_output_path = Path(temp_dir) / "RUN_PPS1D23_D23Response_Layer3_component_scoring_v01_output.csv"
            with component_output_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["submission_id", "component_id", "sbo_identifier", "L3_Comment"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "submission_id": "1001",
                        "component_id": "B1Response",
                        "sbo_identifier": "C_AP2B_SecB1",
                        "L3_Comment": "Clear developmental interpretation.",
                    }
                )
                writer.writerow(
                    {
                        "submission_id": "1001",
                        "component_id": "C1Response",
                        "sbo_identifier": "C_AP2B_SecC1",
                        "L3_Comment": "Analytical grounding partially present.",
                    }
                )

            lookup = build_l3_comment_lookup(payload_path)
            input_row = {
                "submission_id": "1001",
                "component_score__B1Response": "meets_expectations",
                "component_score__C1Response": "approaching_expectations",
                "flags_any_component": "none",
                "min_confidence_component": "medium",
            }
            output_row = score_submission_row(
                DummyLayer4Module,
                input_row,
                submission_max_numeric_score="4.00",
                submission_id_field="submission_id",
                flags_field="flags_any_component",
                confidence_field="min_confidence_component",
                l3_comment_lookup=lookup,
            )

        self.assertEqual(
            output_row["L3_comment"],
            "Clear developmental interpretation. | Analytical grounding partially present.",
        )
        self.assertEqual(output_row["L3_comment__B1Response"], "Clear developmental interpretation.")
        self.assertEqual(output_row["L3_comment__C1Response"], "Analytical grounding partially present.")


if __name__ == "__main__":
    unittest.main()
