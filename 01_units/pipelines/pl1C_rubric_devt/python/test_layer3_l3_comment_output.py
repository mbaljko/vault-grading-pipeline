from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
import unittest

from generate_rubric_and_manifest_from_indicator_registry import parse_layer3_scoring_payloads


_EXECUTOR_PATH = Path(__file__).with_name("execute-layer3-component-scoring-modules.py")
_EXECUTOR_SPEC = importlib.util.spec_from_file_location("execute_layer3_component_scoring_modules", _EXECUTOR_PATH)
if _EXECUTOR_SPEC is None or _EXECUTOR_SPEC.loader is None:
    raise RuntimeError(f"Unable to load Layer 3 executor module from {_EXECUTOR_PATH}")
_EXECUTOR_MODULE = importlib.util.module_from_spec(_EXECUTOR_SPEC)
_EXECUTOR_SPEC.loader.exec_module(_EXECUTOR_MODULE)
score_submission_rows = _EXECUTOR_MODULE.score_submission_rows


class Layer3CommentParsingTests(unittest.TestCase):
    def test_parse_layer3_payload_extracts_l3_comment_not_as_condition(self) -> None:
        registry_text = """
## Example_Layer3

#### Component scoring rule

| resultant scale value | D01 | L3_Comment |
| --- | --- | --- |
| meets_expectations | demonstrated | Core evidence is present. |
| below_expectations | little_to_no_demonstration | Core evidence is missing. |

#### dimension bindings

| component_id | D01 |
| --- | --- |
| D23Response | D01 |
""".strip()

        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.md"
            registry_path.write_text(registry_text, encoding="utf-8")
            payloads = parse_layer3_scoring_payloads(registry_path)

        self.assertIn("D23Response", payloads)
        payload = json.loads(payloads["D23Response"]["component_scoring_payload_json"])
        self.assertEqual(payload["input_dimension_tokens"], ["d01"])
        self.assertEqual(payload["bound_dimension_ids"], ["D01"])
        self.assertEqual(payload["derivation_rules"][0]["conditions"], {"d01": "demonstrated"})
        self.assertNotIn("L3_Comment", payload["derivation_rules"][0]["conditions"])
        self.assertEqual(payload["derivation_rules"][0]["l3_comment"], "Core evidence is present.")


class Layer3CommentOutputTests(unittest.TestCase):
    def test_score_submission_rows_includes_l3_comment(self) -> None:
        class DummyModule:
            COMPONENT_ID = "D23Response"
            SBO_IDENTIFIER = "C_PPS1D23_SecD23"
            SBO_SHORT_DESCRIPTION = "within-type comparison"
            COMPONENT_PERFORMANCE_SCALE = ["below_expectations", "meets_expectations"]
            BOUND_DIMENSION_IDS = ["D01"]

            @staticmethod
            def score_component_with_comment(dimension_values: dict[str, str], dimension_scale_lookup=None) -> tuple[str, str]:
                if dimension_values.get("D01") == "demonstrated":
                    return "meets_expectations", "Core evidence is present."
                return "below_expectations", "Core evidence is missing."

        submission_rows = [
            {
                "submission_id": "8203104",
                "component_id": "D23Response",
                "dimension_id": "D01",
                "evidence_status": "demonstrated",
                "min_confidence_indicator": "high",
                "flags_any_indicator": "none",
            }
        ]

        output_row = score_submission_rows(
            DummyModule,
            submission_rows,
            dimension_id_field="dimension_id",
            value_field="evidence_status",
            dimension_scale_lookup={"D01": {"little_to_no_demonstration": 0, "demonstrated": 1}},
            confidence_field="min_confidence_indicator",
            flags_field="flags_any_indicator",
        )

        self.assertEqual(output_row["component_score"], "meets_expectations")
        self.assertEqual(output_row["L3_Comment"], "Core evidence is present.")


if __name__ == "__main__":
    unittest.main()
