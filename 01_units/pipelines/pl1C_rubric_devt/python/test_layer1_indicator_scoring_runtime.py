import unittest

from layer1_indicator_scoring_runtime import apply_decision_rule


PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "exact_or_alias_article_insensitive_any_conjunct",
	"decision_rule": "present_if_exact_match_or_alias_and_not_excluded",
	"allowed_terms": [
		"administrative workload distribution requirements",
		"documentation and record-keeping standards",
		"human scoring authority",
	],
	"allowed_aliases": {
		"reviewers must score applications independently": "human scoring authority",
		"documented accountability": "documentation and record-keeping standards",
		"distribute administrative workloads among reviewers": "administrative workload distribution requirements",
	},
	"excluded_terms": [
		"system",
		"tool",
		"process",
		"workflow",
		"stage",
		"reviewer",
		"committee",
		"model",
		"algorithm",
		"platform",
		"outcome",
		"fairness",
		"efficiency",
	],
}

CANONICAL_INEQUALITY_PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "canonical_inequality",
	"decision_rule": "present_if_canonical_mapping_of_demand_a_not_equal_canonical_mapping_of_demand_b",
	"left_segment_id": "DemandA",
	"right_segment_id": "DemandB",
	"left_allowed_terms": [
		"published evaluation criteria",
		"administrative workload distribution requirements",
		"human decision authority",
	],
	"right_allowed_terms": [
		"published evaluation criteria",
		"administrative workload distribution requirements",
		"human decision authority",
	],
	"left_allowed_aliases": {
		"balanced workload distribution": "administrative workload distribution requirements",
	},
	"right_allowed_aliases": {
		"balanced workload distribution": "administrative workload distribution requirements",
	},
	"excluded_terms": [],
}


class Layer1IndicatorScoringRuntimeTests(unittest.TestCase):
	def test_prefix_stripping_rule_that_logs_original_and_stripped_segment(self) -> None:
		with self.assertLogs("layer1_indicator_scoring_runtime", level="DEBUG") as captured:
			status, _ = apply_decision_rule("the rule that reviewers must score applications independently", PAYLOAD)
		self.assertEqual(status, "present")
		joined_logs = "\n".join(captured.output)
		self.assertIn("original segment 'the rule that reviewers must score applications independently'", joined_logs)
		self.assertIn("stripped to 'reviewers must score applications independently'", joined_logs)
		self.assertIn("alias 'reviewers must score applications independently'", joined_logs)

	def test_prefix_stripping_institutional_demand_for(self) -> None:
		status, _ = apply_decision_rule("the institutional demand for documented accountability", PAYLOAD)
		self.assertEqual(status, "present")

	def test_prefix_stripping_requirement_to(self) -> None:
		status, _ = apply_decision_rule("the requirement to distribute administrative workloads among reviewers", PAYLOAD)
		self.assertEqual(status, "present")

	def test_canonical_inequality_present_when_slots_are_noncanonical(self) -> None:
		status, _ = apply_decision_rule(
			"",
			CANONICAL_INEQUALITY_PAYLOAD,
			row={
				"component_id": "SectionB2Response",
				"segment_text_SectionB2Response__DemandA": "transparent justification",
				"segment_text_SectionB2Response__DemandB": "fair reviewer preparation",
			},
			component_id="SectionB2Response",
		)
		self.assertEqual(status, "present")

	def test_canonical_inequality_present_when_slots_blank_but_source_text_exists(self) -> None:
		status, _ = apply_decision_rule(
			"",
			CANONICAL_INEQUALITY_PAYLOAD,
			row={
				"component_id": "SectionB3Response",
				"segment_text_SectionB3Response__DemandA": "",
				"segment_text_SectionB3Response__DemandB": "",
				"source_response_text": (
					"In this system, the institutional demand for transparent justification "
					"interacts human decision authority through coring rubric shaping committee deliberation."
				),
			},
			component_id="SectionB3Response",
		)
		self.assertEqual(status, "present")


if __name__ == "__main__":
	unittest.main()
