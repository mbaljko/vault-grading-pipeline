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


if __name__ == "__main__":
	unittest.main()
