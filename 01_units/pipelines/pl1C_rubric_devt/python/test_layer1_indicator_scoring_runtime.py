import unittest

from layer1_indicator_scoring_runtime import apply_decision_rule


PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "exact_or_alias_article_insensitive_any_conjunct",
	"decision_rule": "present_if_exact_match_or_alias_and_not_excluded",
	"allowed_terms": [
		"administrative workload distribution requirements",
		"documentation and record-keeping standards",
		"eligibility requirements",
		"human decision authority",
		"human scoring authority",
		"program mission",
		"public reporting requirements",
		"published evaluation criteria",
		"timeliness expectations",
	],
	"allowed_aliases": {
		"rule that reviewers must score applications independently": "governance rules",
		"committee based decision authority": "human decision authority",
		"decision authority": "human decision authority",
		"documentation requirements": "documentation and record-keeping standards",
		"record-keeping standards": "documentation and record-keeping standards",
		"requirement to distribute administrative workloads among reviewers": "administrative workload distribution requirements",
		"workload distribution tied to reviewer capacity": "administrative workload distribution requirements",
		"institutional demand of throughput expectations": "throughput expectations",
		"human verification requirement": "verification requirements",
		"human verification requirements": "verification requirements",
		"obligation to verify applications": "verification requirements",
		"requirement for human verification": "verification requirements",
		"timeliness expectations tied to fixed funding cycle schedules": "timeliness expectations",
		"timeliness expectations tied to fixed funding-cycle schedules": "timeliness expectations",
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
	def assert_present(self, text: str) -> None:
		status, _ = apply_decision_rule(text, PAYLOAD)
		self.assertEqual(status, "present", msg=text)

	def assert_not_present(self, text: str) -> None:
		status, _ = apply_decision_rule(text, PAYLOAD)
		self.assertEqual(status, "not_present", msg=text)

	def test_required_positive_cases(self) -> None:
		for text in [
			"the rule that reviewers must score applications independently",
			"committee based decision authority",
			"documentation and record-keeping requirements",
			"the requirement to distribute administrative workloads among reviewers",
			"workload distribution tied to reviewer capacity",
			"institutional demand of throughput expectations",
			"human verification requirement",
			"timeliness expectations tied to fixed funding cycles",
		]:
			with self.subTest(text=text):
				self.assert_present(text)

	def test_required_negative_cases(self) -> None:
		for text in [
			"eligibility verification",
			"AI-assisted information structuring",
			"documentation",
			"committee structure",
			"each other",
		]:
			with self.subTest(text=text):
				self.assert_not_present(text)

	def test_logging_shows_alias_trigger(self) -> None:
		with self.assertLogs("layer1_indicator_scoring_runtime", level="DEBUG") as captured:
			status, _ = apply_decision_rule("human verification requirement", PAYLOAD)
		self.assertEqual(status, "present")
		joined_logs = "\n".join(captured.output)
		self.assertIn("human verification requirement", joined_logs)
		self.assertIn("canonical 'verification requirements'", joined_logs)


if __name__ == "__main__":
	unittest.main()