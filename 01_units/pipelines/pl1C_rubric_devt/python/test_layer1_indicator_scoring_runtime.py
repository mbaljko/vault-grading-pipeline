import importlib.util
from pathlib import Path
import unittest

from layer1_indicator_scoring_runtime import apply_decision_rule, score_indicator_from_row


_GENERATOR_PATH = Path(__file__).with_name("generate-layer1-indicator-scoring-module.py")
_GENERATOR_SPEC = importlib.util.spec_from_file_location("generate_layer1_indicator_scoring_module", _GENERATOR_PATH)
if _GENERATOR_SPEC is None or _GENERATOR_SPEC.loader is None:
	raise RuntimeError(f"Unable to load generator module from {_GENERATOR_PATH}")
_GENERATOR_MODULE = importlib.util.module_from_spec(_GENERATOR_SPEC)
_GENERATOR_SPEC.loader.exec_module(_GENERATOR_MODULE)
parse_scoring_payload = _GENERATOR_MODULE.parse_scoring_payload


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
		"bound_segment_resolution_policy": "hard_stay",
}

CANONICAL_INEQUALITY_PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "canonical_inequality",
	"decision_rule": "present_if_canonical_mappings_are_distinct",
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

STAGE_TOKEN_PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "exact_or_alias_article_insensitive_any_conjunct",
	"decision_rule": "present_if_any_stage_token_matches_after_normalisation_and_not_excluded",
	"allowed_terms": [
		"preliminary screening",
		"individual reviewer assessment",
		"reviewer assignment",
		"committee deliberation",
		"documentation",
		"categorisation",
	],
	"allowed_aliases": {
		"categorization": "categorisation",
		"pre screening": "preliminary screening",
		"deliberation": "committee deliberation",
		"reviewer assessment": "individual reviewer assessment",
	},
	"excluded_terms": [
		"reviewer preparation",
		"file preparation",
		"individual reviewers examining",
	],
	"bound_segment_resolution_policy": "hard_stay",
}

BOUND_SEGMENT_POLICY_PAYLOAD = {
	"normalisation_rule": "lowercase_trim_strip_stage_suffix",
	"match_policy": "exact_or_alias",
	"decision_rule": "present_if_any_stage_token_matches_after_normalisation_and_not_excluded",
	"allowed_terms": [
		"preliminary screening",
		"reviewer assignment",
		"committee deliberation",
	],
	"allowed_aliases": {
		"assignment": "reviewer assignment",
		"screening": "preliminary screening",
	},
	"excluded_terms": [],
	"bound_segment_id": "04_WorkflowOrRole",
	"bound_segment_resolution_policy": "hard_stay",
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

	def test_canonical_distinct_rule_accepts_legacy_decision_rule_alias(self) -> None:
		status, _ = apply_decision_rule(
			"",
			{
				**CANONICAL_INEQUALITY_PAYLOAD,
				"decision_rule": "present_if_canonical_mapping_of_demand_a_not_equal_canonical_mapping_of_demand_b",
			},
			row={
				"component_id": "SectionB2Response",
				"segment_text_SectionB2Response__DemandA": "published evaluation criteria",
				"segment_text_SectionB2Response__DemandB": "balanced workload distribution",
			},
			component_id="SectionB2Response",
		)
		self.assertEqual(status, "present")

	def test_stage_token_rule_matches_stage_inside_longer_span(self) -> None:
		status, _ = apply_decision_rule(
			"the preliminary screening and assignment stage",
			STAGE_TOKEN_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_stage_token_rule_matches_alias_inside_longer_span(self) -> None:
		status, _ = apply_decision_rule(
			"the pre screening stage",
			STAGE_TOKEN_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_stage_token_rule_matches_multiple_canonical_stages_in_coordinated_span(self) -> None:
		status, _ = apply_decision_rule(
			"the preliminary screening, categorization, and reviewer assignment stage",
			STAGE_TOKEN_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_stage_token_rule_rejects_role_only_string(self) -> None:
		status, _ = apply_decision_rule(
			"the reviewer preparation stage",
			STAGE_TOKEN_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_stage_token_rule_rejects_non_stage_phrase(self) -> None:
		status, _ = apply_decision_rule(
			"individual reviewers examining stage",
			STAGE_TOKEN_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_stage_token_rule_respects_excluded_terms_even_when_other_stage_text_exists(self) -> None:
		status, _ = apply_decision_rule(
			"the reviewer preparation and documentation stage",
			STAGE_TOKEN_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_stage_token_rule_logs_raw_normalized_alias_and_excluded_diagnostics(self) -> None:
		with self.assertLogs("layer1_indicator_scoring_runtime", level="DEBUG") as captured:
			status, _ = apply_decision_rule("the pre screening and documentation stage", STAGE_TOKEN_PAYLOAD)
		self.assertEqual(status, "present")
		joined_logs = "\n".join(captured.output)
		self.assertIn("raw_segment='the pre screening and documentation stage'", joined_logs)
		self.assertIn("normalized_segment='the pre screening and documentation stage'", joined_logs)
		self.assertIn("matched_canonical_terms=", joined_logs)
		self.assertIn("preliminary screening", joined_logs)
		self.assertIn("documentation", joined_logs)
		self.assertIn("matched_excluded_terms=[]", joined_logs)
		self.assertIn("final_status=present", joined_logs)

	def test_apply_decision_rule_raises_for_unsupported_decision_rule(self) -> None:
		with self.assertRaisesRegex(ValueError, "Unsupported Layer 1 decision_rule: unsupported_rule"):
			apply_decision_rule(
				"documentation stage",
				{
					"normalisation_rule": "lowercase_trim",
					"match_policy": "substring_any",
					"decision_rule": "unsupported_rule",
					"allowed_terms": ["documentation"],
					"allowed_aliases": {},
					"excluded_terms": [],
				},
			)

	def test_score_indicator_from_row_hard_stays_on_blank_bound_segment_by_default(self) -> None:
		result = score_indicator_from_row(
			{
				"participant_id": "8156972",
				"component_id": "SectionB1Response",
				"segment_text_SectionB1Response__04_WorkflowOrRole": "",
				"evidence_text": "[SectionB1Response__03_Mechanism]\nscheduling and reviewer assignment",
			},
			component_id="SectionB1Response",
			indicator_id="I14",
			payload=BOUND_SEGMENT_POLICY_PAYLOAD,
		)
		self.assertEqual(result["evidence_status"], "not_present")

	def test_score_indicator_from_row_can_fallback_when_policy_overrides_default(self) -> None:
		result = score_indicator_from_row(
			{
				"participant_id": "8156972",
				"component_id": "SectionB1Response",
				"segment_text_SectionB1Response__04_WorkflowOrRole": "",
				"evidence_text": "[SectionB1Response__03_Mechanism]\nscheduling and reviewer assignment",
			},
			component_id="SectionB1Response",
			indicator_id="I14",
			payload={
				**BOUND_SEGMENT_POLICY_PAYLOAD,
				"bound_segment_resolution_policy": "fallback_to_evidence_text",
			},
		)
		self.assertEqual(result["evidence_status"], "present")

	def test_parse_scoring_payload_defaults_bound_segment_resolution_policy_to_hard_stay(self) -> None:
		payload = parse_scoring_payload(
			'{'
			'"scoring_mode":"deterministic",'
			'"dependency_type":"segment",'
			'"bound_segment_id":"04_WorkflowOrRole",'
			'"normalisation_rule":"lowercase_trim",'
			'"match_policy":"exact_or_alias",'
			'"decision_rule":"present_if_exact_match_or_alias_and_not_excluded",'
			'"allowed_terms":["documentation"],'
			'"allowed_aliases":{},'
			'"excluded_terms":[]'
			'}'
		)
		self.assertEqual(payload["bound_segment_resolution_policy"], "hard_stay")

	def test_parse_scoring_payload_raises_for_unsupported_bound_segment_resolution_policy(self) -> None:
		with self.assertRaisesRegex(
			ValueError,
			"Unsupported Layer 1 bound_segment_resolution_policy: unsupported_policy",
		):
			parse_scoring_payload(
				'{'
				'"scoring_mode":"deterministic",'
				'"dependency_type":"segment",'
				'"bound_segment_id":"04_WorkflowOrRole",'
				'"normalisation_rule":"lowercase_trim",'
				'"match_policy":"exact_or_alias",'
				'"decision_rule":"present_if_exact_match_or_alias_and_not_excluded",'
				'"allowed_terms":["documentation"],'
				'"allowed_aliases":{},'
				'"excluded_terms":[],'
				'"bound_segment_resolution_policy":"unsupported_policy"'
				'}'
			)

	def test_parse_scoring_payload_raises_for_unsupported_decision_rule(self) -> None:
		with self.assertRaisesRegex(ValueError, "Unsupported Layer 1 decision_rule: unsupported_rule"):
			parse_scoring_payload(
				'{'
				'"scoring_mode":"deterministic",'
				'"dependency_type":"segment",'
				'"bound_segment_id":"01_DemandA",'
				'"normalisation_rule":"lowercase_trim",'
				'"match_policy":"substring_any",'
				'"decision_rule":"unsupported_rule",'
				'"allowed_terms":["documentation"],'
				'"allowed_aliases":{},'
				'"excluded_terms":[]'
				'}'
			)

	def test_parse_scoring_payload_normalizes_legacy_canonical_distinct_rule_name(self) -> None:
		payload = parse_scoring_payload(
			'{'
			'"scoring_mode":"deterministic",'
			'"dependency_type":"segment",'
			'"bound_segment_id":"01_DemandA",'
			'"normalisation_rule":"lowercase_trim",'
			'"match_policy":"canonical_inequality",'
			'"decision_rule":"present_if_canonical_mapping_of_demand_a_not_equal_canonical_mapping_of_demand_b",'
			'"left_segment_id":"DemandA",'
			'"right_segment_id":"DemandB",'
			'"left_allowed_terms":["published evaluation criteria"],'
			'"right_allowed_terms":["published evaluation criteria"],'
			'"left_allowed_aliases":{},'
			'"right_allowed_aliases":{},'
			'"excluded_terms":[]'
			'}'
		)
		self.assertEqual(payload["decision_rule"], "present_if_canonical_mappings_are_distinct")


if __name__ == "__main__":
	unittest.main()
