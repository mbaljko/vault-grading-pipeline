import unittest

from generate_schema_from_segmentation_registry import (
	collect_coordination_text,
	default_allow_coordination_for_family,
	derive_anchor_patterns,
	detect_coordination_support,
	derive_allow_coordination,
	derive_stop_markers,
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

	def test_explicit_anchor_patterns_override_prose_inference(self) -> None:
		row = {
			"template_id": "B_claim_seg_01",
			"local_slot": "01",
			"anchor_patterns": "custom anchor, fallback anchor",
			"operator_definition": "This prose no longer needs to carry the runtime anchor text.",
		}

		self.assertEqual(
			derive_anchor_patterns(row, "left_np_before_anchor"),
			["custom anchor", "fallback anchor"],
		)

	def test_explicit_stop_markers_override_slot_defaults(self) -> None:
		row = {
			"template_id": "B_claim_seg_03",
			"local_slot": "03",
			"stop_markers": "sentence_end, comma",
		}

		self.assertEqual(
			derive_stop_markers(row, "span_after_marker_before_marker"),
			["sentence_end", "comma"],
		)

	def test_explicit_allow_coordination_override_beats_template_default(self) -> None:
		row = {
			"template_id": "B_claim_seg_02",
			"allow_coordination": "false",
			"operator_definition": "This template normally defaults true.",
		}

		self.assertFalse(derive_allow_coordination(row, "right_np_after_anchor_before_marker"))


if __name__ == "__main__":
	unittest.main()