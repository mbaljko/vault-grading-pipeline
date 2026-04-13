import unittest

from generate_schema_from_segmentation_registry import (
	collect_coordination_text,
	default_allow_coordination_for_family,
	detect_coordination_support,
	derive_allow_coordination,
)


class AllowCoordinationDerivationTests(unittest.TestCase):
	def test_explicit_override_wins(self) -> None:
		row = {
			"template_id": "B_claim_seg_02",
			"operator_definition": "No coordination language appears here.",
		}
		self.assertTrue(derive_allow_coordination(row, "right_np_after_anchor_before_marker"))

	def test_semantic_signal_enables_coordination(self) -> None:
		row = {
			"template_id": "future_template_01",
			"operator_guidance": "Extend the span to include the full coordinated phrase when it continues through compact coordination.",
		}
		self.assertTrue(detect_coordination_support(row))
		self.assertTrue(derive_allow_coordination(row, "right_np_after_anchor_before_marker"))

	def test_family_fallback_is_conservative(self) -> None:
		row = {
			"template_id": "future_template_02",
			"operator_definition": "Extract the first local noun phrase after the anchor.",
		}
		self.assertFalse(detect_coordination_support(row))
		self.assertFalse(derive_allow_coordination(row, "right_np_after_anchor_before_marker"))

	def test_unknown_family_defaults_false(self) -> None:
		row = {
			"template_id": "future_template_03",
			"operator_definition": "Extract a slot with no span-extension guidance.",
		}
		self.assertFalse(default_allow_coordination_for_family("unknown_family"))
		self.assertFalse(derive_allow_coordination(row, "unknown_family"))

	def test_collect_coordination_text_uses_all_supported_fields(self) -> None:
		row = {
			"operator_definition": "Definition text.",
			"operator_guidance": "Guidance text.",
			"decision_procedure": "Decision text.",
		}
		collected = collect_coordination_text(row)
		self.assertIn("definition text.", collected)
		self.assertIn("guidance text.", collected)
		self.assertIn("decision text.", collected)


if __name__ == "__main__":
	unittest.main()