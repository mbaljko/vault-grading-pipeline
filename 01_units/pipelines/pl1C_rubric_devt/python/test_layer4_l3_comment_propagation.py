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
        self.assertEqual(output_row["submission_score"], "meets_expectations")

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
