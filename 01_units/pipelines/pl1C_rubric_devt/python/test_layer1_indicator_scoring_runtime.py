import importlib.util
from pathlib import Path
import unittest

from layer1_indicator_scoring_runtime import apply_decision_rule, normalize_text, score_indicator_from_row


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

STAGE_PHRASE_PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "exact_or_alias_article_insensitive_any_conjunct",
	"decision_rule": "present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded",
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

B_CLAIM_CORE_05_PAYLOAD = {
	"normalisation_rule": "lowercase_trim_strip_leading_determiner_strip_possessive",
	"match_policy": "exact_or_alias",
	"decision_rule": "present_if_exact_match_or_alias_and_not_excluded",
	"allowed_terms": ["reviewer", "committee"],
	"allowed_aliases": {},
	"excluded_terms": [
		"system",
		"tool",
		"model",
		"algorithm",
		"process",
		"workflow",
		"platform",
		"stage",
		"screening",
		"assessment",
		"scoring",
		"deliberation",
		"documentation",
		"reporting",
		"preparation",
		"assignment",
	],
	"bound_segment_resolution_policy": "hard_stay",
}

BOUND_SEGMENT_POLICY_PAYLOAD = {
	"normalisation_rule": "lowercase_trim_strip_stage_suffix",
	"match_policy": "exact_or_alias",
	"decision_rule": "present_if_any_stage_phrase_matches_after_normalisation_and_not_excluded",
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

EFFECT_TERM_LEMMA_PAYLOAD = {
	"normalisation_rule": "lowercase_lemma_effect_terms",
	"match_policy": "co_occurrence_lemma",
	"decision_rule": "present_if_minimum_group_matches_met_and_not_excluded",
	"required_term_groups": {
		"effect_forms": [
			"sequence",
			"structure",
			"allocate",
			"distribute",
			"redistribute",
			"formalise",
			"formalize",
			"organise",
			"organize",
			"record",
			"require",
			"guide",
		],
		"structural_features": [
			"reviewer preparation",
			"applications",
			"capacity",
			"visibility",
			"scores",
			"written justifications",
			"categories",
			"assignment",
			"scheduling",
		],
	},
	"minimum_match_count_per_group": 1,
	"excluded_terms": [],
	"bound_segment_resolution_policy": "hard_stay",
}

EFFECT_TERM_LEMMA_EXCLUDED_PAYLOAD = {
	**EFFECT_TERM_LEMMA_PAYLOAD,
	"excluded_terms": ["visibility"],
}

PUT_INTO_WORDS_PAYLOAD = {
	**EFFECT_TERM_LEMMA_PAYLOAD,
	"required_term_groups": {
		"effect_forms": ["put into words"],
		"structural_features": ["justification"],
	},
}

WINDOWED_COOCCURRENCE_PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "co_occurrence_window_5",
	"decision_rule": "present_if_minimum_group_matches_met_and_not_excluded",
	"required_term_groups": {
		"effect_forms": ["allocate"],
		"structural_features": ["applications"],
	},
	"minimum_match_count_per_group": 1,
	"excluded_terms": [],
	"bound_segment_resolution_policy": "hard_stay",
}

DERIVED_RECOVERY_PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "co_occurrence_lemma",
	"decision_rule": "present_if_minimum_group_matches_met_and_not_excluded",
	"required_term_groups": {
		"effect_forms": ["allocate", "distribute"],
		"structural_features": ["applications"],
	},
	"minimum_match_count_per_group": 1,
	"excluded_terms": [],
	"derived_structural_feature_rule": "enabled: true; condition: effect_form_present AND direct_object_present; action: treat_object_as_structural_feature",
	"domain_artifact_tokens": "application,applications",
	"bound_segment_resolution_policy": "hard_stay",
}

FALLBACK_PAYLOAD_ENABLED = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "co_occurrence_lemma",
	"decision_rule": "present_if_minimum_group_matches_met_or_fallback_and_not_excluded",
	"required_term_groups": {
		"effect_forms": ["allocate"],
		"structural_features": ["applications"],
	},
	"minimum_match_count_per_group": 1,
	"excluded_terms": [],
	"fallback_rule": "enabled: true; condition: effect_form_present AND direct_object_present; action: accept_as_present_with_flag",
	"bound_segment_resolution_policy": "hard_stay",
}

FALLBACK_PAYLOAD_DISABLED = {
	**FALLBACK_PAYLOAD_ENABLED,
	"fallback_rule": "enabled: false; condition: effect_form_present AND direct_object_present; action: accept_as_present_with_flag",
}

DOMAIN_ARTIFACT_PASSIVE_PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "co_occurrence_lemma",
	"decision_rule": "present_if_minimum_group_matches_met_and_not_excluded",
	"required_term_groups": {
		"effect_forms": ["allocate"],
		"structural_features": ["applications"],
	},
	"minimum_match_count_per_group": 1,
	"excluded_terms": [],
	"domain_artifact_tokens": "rubric,checklist",
	"bound_segment_resolution_policy": "hard_stay",
}

DERIVED_PATTERN_REQUIRED_PAYLOAD = {
	"normalisation_rule": "lowercase_trim",
	"match_policy": "co_occurrence_lemma",
	"decision_rule": "present_if_minimum_group_matches_met_and_not_excluded",
	"required_term_groups": {
		"effect_forms": ["allocate"],
		"structural_features": ["records"],
	},
	"minimum_match_count_per_group": 1,
	"excluded_terms": [],
	"derived_structural_feature_rule": "enabled: true; condition: effect_form_present AND direct_object_present; action: treat_object_as_structural_feature; patterns: application",
	"bound_segment_resolution_policy": "hard_stay",
}

FALLBACK_RESTRICTED_EFFECT_PAYLOAD = {
	"normalisation_rule": "lowercase_lemma_effect_terms",
	"match_policy": "co_occurrence_window_5",
	"decision_rule": "present_if_minimum_group_matches_met_or_fallback_and_not_excluded",
	"required_term_groups": {
		"effect_forms": ["allocate", "organize"],
		"structural_features": ["records"],
	},
	"minimum_match_count_per_group": 1,
	"excluded_terms": [],
	"fallback_rule": "enabled: true; condition: effect_form_present AND direct_object_present; restricted_effect_forms: (allocate, assign); action: accept_as_present_with_flag",
	"bound_segment_resolution_policy": "hard_stay",
}


class Layer1IndicatorScoringRuntimeTests(unittest.TestCase):
	def test_normalize_text_lemmatizes_sequence_effect_term(self) -> None:
		self.assertIn(
			"sequence reviewer preparation",
			normalize_text("sequencing reviewer preparation", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_structure_effect_term(self) -> None:
		self.assertIn(
			"structure documentation",
			normalize_text("structuring documentation", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_allocate_effect_term(self) -> None:
		self.assertIn(
			"allocate applications according to capacity",
			normalize_text("allocating applications according to capacity", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_distribution_effect_term(self) -> None:
		self.assertIn(
			"distribute of workload",
			normalize_text("distribution of workload", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_american_formalize_effect_term(self) -> None:
		self.assertIn(
			"formalize review order",
			normalize_text("formalizing review order", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_british_formalise_effect_term(self) -> None:
		self.assertIn(
			"formalise review order",
			normalize_text("formalising review order", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_record_effect_term(self) -> None:
		self.assertIn(
			"record documentation",
			normalize_text("recording documentation", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_require_effect_term(self) -> None:
		self.assertIn(
			"require reviewers to align scores",
			normalize_text("requiring reviewers to align scores", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_guide_effect_term(self) -> None:
		self.assertIn(
			"guide how reviewers explain",
			normalize_text("guiding how reviewers explain", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_american_organize_effect_term(self) -> None:
		self.assertIn(
			"organize applications",
			normalize_text("organizing applications", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_british_organise_effect_term(self) -> None:
		self.assertIn(
			"organise applications",
			normalize_text("organising applications", "lowercase_lemma_effect_terms"),
		)

	def test_normalize_text_lemmatizes_putting_into_words_phrase(self) -> None:
		self.assertEqual(
			normalize_text(
				"putting into words the formally written justification requirements",
				"lowercase_lemma_effect_terms",
			),
			"put into words the formally written justification requirements",
		)

	def test_b_claim_core_06_effect_lemma_rule_scores_present_for_inflected_effect_terms(self) -> None:
		segments = [
			"sequencing reviewer preparation and organizing applications for efficient assignment and scheduling",
			"allocating applications according to capacity",
			"redistributing visibility",
			"structuring how scores and written justifications are recorded across defined categories",
		]
		for segment in segments:
			with self.subTest(segment=segment):
				status, _ = apply_decision_rule(segment, EFFECT_TERM_LEMMA_PAYLOAD)
				self.assertEqual(status, "present")

	def test_co_occurrence_lemma_parse_preserves_required_term_groups(self) -> None:
		payload = parse_scoring_payload(
			'{'
			'"scoring_mode":"deterministic",'
			'"dependency_type":"segment",'
			'"bound_segment_id":"05_Effect",'
			'"normalisation_rule":"lowercase_lemma_effect_terms",'
			'"match_policy":"co_occurrence_lemma",'
			'"decision_rule":"present_if_minimum_group_matches_met_and_not_excluded",'
			'"required_term_groups":{"effect_forms":["sequence"],"structural_features":["reviewer preparation","written justifications"]},'
			'"minimum_match_count_per_group":1,'
			'"excluded_terms":[]'
			'}'
		)
		self.assertEqual(payload["match_policy"], "co_occurrence_lemma")
		self.assertEqual(payload["required_term_groups"]["effect_forms"], ["sequence"])
		self.assertEqual(
			payload["required_term_groups"]["structural_features"],
			["reviewer preparation", "written justifications"],
		)

	def test_co_occurrence_lemma_normalizes_segment_and_registry_terms(self) -> None:
		status, _ = apply_decision_rule(
			"recording documentation",
			{
				**EFFECT_TERM_LEMMA_PAYLOAD,
				"required_term_groups": {
					"effect_forms": ["record"],
					"structural_features": ["documentation"],
				},
			},
		)
		self.assertEqual(status, "present")

	def test_co_occurrence_lemma_uses_word_boundary_safe_phrase_matching(self) -> None:
		status, _ = apply_decision_rule(
			"review ordering only",
			{
				**EFFECT_TERM_LEMMA_PAYLOAD,
				"required_term_groups": {
					"effect_forms": ["order"],
					"structural_features": ["view order"],
				},
			},
		)
		self.assertEqual(status, "not_present")

	def test_co_occurrence_lemma_requires_minimum_count_per_group(self) -> None:
		status, _ = apply_decision_rule(
			"sequencing reviewer preparation for assignment",
			{
				**EFFECT_TERM_LEMMA_PAYLOAD,
				"minimum_match_count_per_group": 2,
				"required_term_groups": {
					"effect_forms": ["sequence", "organize"],
					"structural_features": ["reviewer preparation", "assignment"],
				},
			},
		)
		self.assertEqual(status, "not_present")

	def test_co_occurrence_lemma_respects_excluded_terms_after_normalisation(self) -> None:
		status, _ = apply_decision_rule(
			"redistributing visibility",
			EFFECT_TERM_LEMMA_EXCLUDED_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_co_occurrence_lemma_positive_example_sequence_and_organize(self) -> None:
		status, _ = apply_decision_rule(
			"sequencing reviewer preparation and organizing applications for efficient assignment and scheduling",
			EFFECT_TERM_LEMMA_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_co_occurrence_lemma_positive_example_redistribute_visibility(self) -> None:
		status, _ = apply_decision_rule(
			"redistributing visibility",
			EFFECT_TERM_LEMMA_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_co_occurrence_lemma_positive_example_allocate_capacity(self) -> None:
		status, _ = apply_decision_rule(
			"allocating applications according to capacity",
			EFFECT_TERM_LEMMA_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_b_claim_core_06_put_into_words_segment_scores_present(self) -> None:
		status, _ = apply_decision_rule(
			"putting into words the formally written justification requirements",
			PUT_INTO_WORDS_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_co_occurrence_lemma_negative_example_deciding(self) -> None:
		status, _ = apply_decision_rule(
			"deciding",
			EFFECT_TERM_LEMMA_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_co_occurrence_lemma_negative_example_justification_without_effect_form(self) -> None:
		status, _ = apply_decision_rule(
			"the justification with both accountability obligations and community outcomes",
			{
				**EFFECT_TERM_LEMMA_PAYLOAD,
				"required_term_groups": {
					"effect_forms": ["guide", "require", "record"],
					"structural_features": ["justification"],
				},
			},
		)
		self.assertEqual(status, "not_present")

	def test_co_occurrence_lemma_negative_example_creating_categories(self) -> None:
		status, _ = apply_decision_rule(
			"creating categories",
			{
				**EFFECT_TERM_LEMMA_PAYLOAD,
				"required_term_groups": {
					"effect_forms": ["structure", "formalise"],
					"structural_features": ["categories"],
				},
			},
		)
		self.assertEqual(status, "not_present")

	def test_co_occurrence_lemma_logs_selected_policy_normalisation_and_matches(self) -> None:
		with self.assertLogs("layer1_indicator_scoring_runtime", level="DEBUG") as captured:
			status, _ = apply_decision_rule(
				"redistributing visibility",
				EFFECT_TERM_LEMMA_PAYLOAD,
			)
		self.assertEqual(status, "present")
		joined_logs = "\n".join(captured.output)
		self.assertIn("match_policy=co_occurrence_lemma", joined_logs)
		self.assertIn("normalisation_rule=lowercase_lemma_effect_terms", joined_logs)
		self.assertIn("normalized_segment='redistribute visibility'", joined_logs)
		self.assertIn("matched_terms_by_group=", joined_logs)
		self.assertIn("redistribute", joined_logs)
		self.assertIn("visibility", joined_logs)
		self.assertIn("matched_excluded_terms=[]", joined_logs)
		self.assertIn("final_status=present", joined_logs)

	def test_normalize_text_strips_leading_determiner_when_rule_requests_it(self) -> None:
		self.assertEqual(
			normalize_text("  The Committee  ", "lowercase_trim_strip_leading_determiner"),
			"committee",
		)

	def test_normalize_text_preserves_non_determiner_prefix_for_leading_determiner_rule(self) -> None:
		self.assertEqual(
			normalize_text("committee deliberation", "lowercase_trim_strip_leading_determiner"),
			"committee deliberation",
		)

	def test_normalize_text_strips_possessive_when_rule_requests_it(self) -> None:
		self.assertEqual(
			normalize_text(
				"  The Committee's obligations and reviewers' notes  ",
				"lowercase_trim_strip_leading_determiner_strip_possessive",
			),
			"committee obligations and reviewers notes",
		)

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

	def test_stage_phrase_rule_matches_preliminary_screening_stage(self) -> None:
		status, _ = apply_decision_rule(
			"the preliminary screening stage",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_stage_phrase_rule_matches_individual_reviewer_assessment_stage(self) -> None:
		status, _ = apply_decision_rule(
			"the individual reviewer assessment stage",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_stage_phrase_rule_matches_committee_deliberation_stage(self) -> None:
		status, _ = apply_decision_rule(
			"the committee deliberation stage",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_stage_phrase_rule_matches_documentation_stage(self) -> None:
		status, _ = apply_decision_rule(
			"the documentation stage",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_stage_phrase_rule_matches_reviewer_assignment_phase(self) -> None:
		status, _ = apply_decision_rule(
			"the reviewer assignment phase",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_stage_phrase_rule_matches_multiple_canonical_stages_in_coordinated_span(self) -> None:
		status, _ = apply_decision_rule(
			"the preliminary screening, categorisation, and reviewer assignment stage",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "present")

	def test_stage_phrase_rule_rejects_role_only_string(self) -> None:
		status, _ = apply_decision_rule(
			"a reviewer",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_stage_phrase_rule_rejects_reviewer_preparation(self) -> None:
		status, _ = apply_decision_rule(
			"reviewer preparation",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_stage_phrase_rule_rejects_reviewer_preparation_stage(self) -> None:
		status, _ = apply_decision_rule(
			"the reviewer preparation stage",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_stage_phrase_rule_rejects_file_preparation(self) -> None:
		status, _ = apply_decision_rule(
			"file preparation",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_stage_phrase_rule_rejects_non_stage_phrase(self) -> None:
		status, _ = apply_decision_rule(
			"individual reviewers examining stage",
			STAGE_PHRASE_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_stage_phrase_rule_logs_raw_normalized_alias_and_excluded_diagnostics(self) -> None:
		with self.assertLogs("layer1_indicator_scoring_runtime", level="DEBUG") as captured:
			status, _ = apply_decision_rule("the pre screening and documentation stage", STAGE_PHRASE_PAYLOAD)
		self.assertEqual(status, "present")
		joined_logs = "\n".join(captured.output)
		self.assertIn("raw_segment='the pre screening and documentation stage'", joined_logs)
		self.assertIn("normalized_segment='the pre screening and documentation stage'", joined_logs)
		self.assertIn("matched_canonical_terms=", joined_logs)
		self.assertIn("preliminary screening", joined_logs)
		self.assertIn("documentation", joined_logs)
		self.assertIn("matched_excluded_terms=[]", joined_logs)
		self.assertIn("final_status=present", joined_logs)

	def test_b_claim_core_05_accepts_role_only_reviewer(self) -> None:
		status, _ = apply_decision_rule("a reviewer", B_CLAIM_CORE_05_PAYLOAD)
		self.assertEqual(status, "present")

	def test_b_claim_core_05_accepts_role_only_committee(self) -> None:
		status, _ = apply_decision_rule("the committee", B_CLAIM_CORE_05_PAYLOAD)
		self.assertEqual(status, "present")

	def test_b_claim_core_05_rejects_reviewer_preparation_due_to_excluded_veto(self) -> None:
		status, _ = apply_decision_rule("reviewer preparation", B_CLAIM_CORE_05_PAYLOAD)
		self.assertEqual(status, "not_present")

	def test_b_claim_core_05_rejects_committee_deliberation_due_to_excluded_veto(self) -> None:
		status, _ = apply_decision_rule("committee deliberation", B_CLAIM_CORE_05_PAYLOAD)
		self.assertEqual(status, "not_present")

	def test_b_claim_core_05_rejects_individual_reviewer_assessment_due_to_excluded_veto(self) -> None:
		status, _ = apply_decision_rule("individual reviewer assessment", B_CLAIM_CORE_05_PAYLOAD)
		self.assertEqual(status, "not_present")

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

	def test_apply_decision_rule_raises_for_unsupported_normalisation_rule(self) -> None:
		with self.assertRaisesRegex(ValueError, "Unsupported Layer 1 normalisation_rule: unsupported_rule"):
			apply_decision_rule(
				"documentation stage",
				{
					"normalisation_rule": "unsupported_rule",
					"match_policy": "substring_any",
					"decision_rule": "present_if_any_allowed_term_found",
					"allowed_terms": ["documentation"],
					"allowed_aliases": {},
					"excluded_terms": [],
				},
			)

	def test_non_empty_match_policy_present_for_non_blank_segment(self) -> None:
		status, flags = apply_decision_rule(
			"caseworker",
			{
				"normalisation_rule": "lowercase_trim",
				"match_policy": "non_empty",
				"decision_rule": "present_if_any_allowed_term_found",
				"excluded_terms": [],
			},
		)
		self.assertEqual(status, "present")
		self.assertEqual(flags, "none")

	def test_non_empty_match_policy_empty_segment_sets_missing_input_text_flag(self) -> None:
		status, flags = apply_decision_rule(
			"   ",
			{
				"normalisation_rule": "lowercase_trim",
				"match_policy": "non_empty",
				"decision_rule": "present_if_any_allowed_term_found",
				"excluded_terms": [],
			},
		)
		self.assertEqual(status, "not_present")
		self.assertIn("missing_input_text", flags)

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

	def test_parse_scoring_payload_raises_for_unsupported_normalisation_rule(self) -> None:
		with self.assertRaisesRegex(ValueError, "Unsupported Layer 1 normalisation_rule: unsupported_rule"):
			parse_scoring_payload(
				'{'
				'"scoring_mode":"deterministic",'
				'"dependency_type":"segment",'
				'"bound_segment_id":"01_DemandA",'
				'"normalisation_rule":"unsupported_rule",'
				'"match_policy":"substring_any",'
				'"decision_rule":"present_if_any_allowed_term_found",'
				'"allowed_terms":["documentation"],'
				'"allowed_aliases":{},'
				'"excluded_terms":[]'
				'}'
			)

	def test_parse_scoring_payload_accepts_strip_leading_determiner_normalisation_rule(self) -> None:
		payload = parse_scoring_payload(
			'{'
			'"scoring_mode":"deterministic",'
			'"dependency_type":"segment",'
			'"bound_segment_id":"04_WorkflowOrRole",'
			'"normalisation_rule":"lowercase_trim_strip_leading_determiner",'
			'"match_policy":"exact_or_alias",'
			'"decision_rule":"present_if_exact_match_or_alias_and_not_excluded",'
			'"allowed_terms":["committee"],'
			'"allowed_aliases":{},'
			'"excluded_terms":[]'
			'}'
		)
		self.assertEqual(payload["normalisation_rule"], "lowercase_trim_strip_leading_determiner")

	def test_parse_scoring_payload_accepts_effect_lemma_normalisation_rule(self) -> None:
		payload = parse_scoring_payload(
			'{'
			'"scoring_mode":"deterministic",'
			'"dependency_type":"segment",'
			'"bound_segment_id":"05_Effect",'
			'"normalisation_rule":"lowercase_lemma_effect_terms",'
			'"match_policy":"co_occurrence_lemma",'
			'"decision_rule":"present_if_minimum_group_matches_met_and_not_excluded",'
			'"required_term_groups":{"effect_forms":["sequence"],"structural_features":["reviewer preparation"]},'
			'"minimum_match_count_per_group":1,'
			'"excluded_terms":[]'
			'}'
		)
		self.assertEqual(payload["normalisation_rule"], "lowercase_lemma_effect_terms")

	def test_parse_scoring_payload_non_empty_drops_allowed_terms(self) -> None:
		payload = parse_scoring_payload(
			'{'
			'"scoring_mode":"deterministic",'
			'"dependency_type":"segment",'
			'"bound_segment_id":"01_Actor",'
			'"normalisation_rule":"lowercase_trim",'
			'"match_policy":"non_empty",'
			'"decision_rule":"present_if_any_allowed_term_found",'
			'"allowed_terms":["caseworker"],'
			'"excluded_terms":[]'
			'}'
		)
		self.assertNotIn("allowed_terms", payload)

	def test_parse_scoring_payload_accepts_strip_leading_determiner_strip_possessive_rule(self) -> None:
		payload = parse_scoring_payload(
			'{'
			'"scoring_mode":"deterministic",'
			'"dependency_type":"segment",'
			'"bound_segment_id":"04_WorkflowOrRole",'
			'"normalisation_rule":"lowercase_trim_strip_leading_determiner_strip_possessive",'
			'"match_policy":"exact_or_alias",'
			'"decision_rule":"present_if_exact_match_or_alias_and_not_excluded",'
			'"allowed_terms":["committee role"],'
			'"allowed_aliases":{},'
			'"excluded_terms":[]'
			'}'
		)
		self.assertEqual(
			payload["normalisation_rule"],
			"lowercase_trim_strip_leading_determiner_strip_possessive",
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

	def test_existing_indicator_without_augmentation_fields_is_unchanged(self) -> None:
		status, flags = apply_decision_rule(
			"sequence reviewer preparation",
			{
				"normalisation_rule": "lowercase_trim",
				"match_policy": "co_occurrence_lemma",
				"decision_rule": "present_if_minimum_group_matches_met_and_not_excluded",
				"required_term_groups": {
					"effect_forms": ["sequence"],
					"structural_features": ["reviewer preparation"],
				},
				"minimum_match_count_per_group": 1,
				"excluded_terms": [],
			},
		)
		self.assertEqual(status, "present")
		self.assertEqual(flags, "none")

	def test_co_occurrence_window_5_succeeds_within_window(self) -> None:
		status, flags = apply_decision_rule(
			"allocate now the applications",
			WINDOWED_COOCCURRENCE_PAYLOAD,
		)
		self.assertEqual(status, "present")
		self.assertIn("windowed_co_occurrence_match", flags)

	def test_co_occurrence_window_5_fails_outside_window(self) -> None:
		status, _ = apply_decision_rule(
			"allocate one two three four five six applications",
			WINDOWED_COOCCURRENCE_PAYLOAD,
		)
		self.assertEqual(status, "not_present")

	def test_derived_feature_recovery_satisfies_missing_group(self) -> None:
		status, flags = apply_decision_rule(
			"allocate rubric quickly",
			DERIVED_RECOVERY_PAYLOAD,
		)
		self.assertEqual(status, "present")
		self.assertIn("derived_feature_recovered", flags)

	def test_fallback_succeeds_only_when_enabled(self) -> None:
		enabled_status, enabled_flags = apply_decision_rule(
			"allocate rubric",
			FALLBACK_PAYLOAD_ENABLED,
		)
		disabled_status, _ = apply_decision_rule(
			"allocate rubric",
			FALLBACK_PAYLOAD_DISABLED,
		)
		self.assertEqual(enabled_status, "present")
		self.assertIn("fallback_rule_used", enabled_flags)
		self.assertEqual(disabled_status, "not_present")

	def test_excluded_terms_override_normal_derived_and_fallback(self) -> None:
		status, flags = apply_decision_rule(
			"allocate applications forbidden",
			{
				**FALLBACK_PAYLOAD_ENABLED,
				"excluded_terms": ["forbidden"],
			},
		)
		self.assertEqual(status, "not_present")
		self.assertIn("excluded_term_veto", flags)
		self.assertIn("excluded_term_override", flags)

	def test_derived_pattern_required_and_matched(self) -> None:
		status, flags = apply_decision_rule(
			"allocate application quickly",
			DERIVED_PATTERN_REQUIRED_PAYLOAD,
		)
		self.assertEqual(status, "present")
		self.assertIn("derived_structural_feature_matched", flags)

	def test_derived_pattern_required_but_not_matched(self) -> None:
		status, flags = apply_decision_rule(
			"allocate application quickly",
			{
				**DERIVED_PATTERN_REQUIRED_PAYLOAD,
				"derived_structural_feature_rule": (
					"enabled: true; condition: effect_form_present AND direct_object_present; "
					"action: treat_object_as_structural_feature; patterns: committee"
				),
			},
		)
		self.assertEqual(status, "not_present")
		self.assertIn("derived_structural_feature_pattern_not_matched", flags)

	def test_fallback_restricted_effect_form_matched(self) -> None:
		status, flags = apply_decision_rule(
			"allocating applications",
			FALLBACK_RESTRICTED_EFFECT_PAYLOAD,
		)
		self.assertEqual(status, "present")
		self.assertIn("fallback_restricted_effect_form_matched", flags)
		self.assertIn("present_via_fallback", flags)

	def test_fallback_restricted_effect_form_not_matched(self) -> None:
		status, flags = apply_decision_rule(
			"organizing applications",
			FALLBACK_RESTRICTED_EFFECT_PAYLOAD,
		)
		self.assertEqual(status, "not_present")
		self.assertIn("fallback_restricted_effect_form_not_matched", flags)

	def test_excluded_term_veto_overrides_fallback(self) -> None:
		status, flags = apply_decision_rule(
			"allocating applications harmful",
			{
				**FALLBACK_RESTRICTED_EFFECT_PAYLOAD,
				"excluded_terms": ["harmful"],
			},
		)
		self.assertEqual(status, "not_present")
		self.assertIn("excluded_term_veto", flags)

	def test_unknown_fallback_action_is_non_fatal_and_not_applied(self) -> None:
		status, flags = apply_decision_rule(
			"allocating applications",
			{
				**FALLBACK_RESTRICTED_EFFECT_PAYLOAD,
				"fallback_rule": (
					"enabled: true; condition: effect_form_present AND direct_object_present; "
					"restricted_effect_forms: (allocate, assign); action: unknown_action"
				),
			},
		)
		self.assertEqual(status, "not_present")
		self.assertIn("fallback_unknown_action", flags)

	def test_focused_windowed_augmentation_row_enforces_patterns_and_restricted_fallback(self) -> None:
		payload = {
			"normalisation_rule": "lowercase_lemma_effect_terms",
			"match_policy": "co_occurrence_window_5",
			"decision_rule": "present_if_minimum_group_matches_met_or_fallback_and_not_excluded",
			"required_term_groups": {
				"effect_forms": ["allocate", "organize"],
				"structural_features": ["records"],
			},
			"minimum_match_count_per_group": 1,
			"excluded_terms": ["harmful"],
			"derived_structural_feature_rule": (
				"enabled: true; condition: effect_form_present AND direct_object_present; "
				"action: treat_object_as_structural_feature; patterns: committee"
			),
			"implicit_feature_recovery": (
				"enabled: true; condition: effect_form_present AND direct_object_present AND impossible_marker; "
				"action: treat_object_as_structural_feature"
			),
			"domain_artifact_tokens": "application,file,reviewer",
			"fallback_rule": (
				"enabled: true; condition: effect_form_present AND direct_object_present; "
				"restricted_effect_forms: (allocate, assign); action: accept_as_present_with_flag"
			),
		}

		status_a, flags_a = apply_decision_rule("allocating applications", payload)
		self.assertEqual(status_a, "present")
		self.assertIn("derived_structural_feature_pattern_not_matched", flags_a)
		self.assertIn("fallback_restricted_effect_form_matched", flags_a)
		self.assertIn("present_via_fallback", flags_a)

		status_b, flags_b = apply_decision_rule("organizing applications", payload)
		self.assertEqual(status_b, "not_present")
		self.assertIn("fallback_restricted_effect_form_not_matched", flags_b)

		status_c, flags_c = apply_decision_rule("allocating applications harmful", payload)
		self.assertEqual(status_c, "not_present")
		self.assertIn("excluded_term_veto", flags_c)

	def test_domain_artifact_tokens_not_globally_active_without_declared_rule_usage(self) -> None:
		status, flags = apply_decision_rule(
			"rubric checklist",
			DOMAIN_ARTIFACT_PASSIVE_PAYLOAD,
		)
		self.assertEqual(status, "not_present")
		self.assertEqual(flags, "none")

	def test_malformed_optional_fields_fail_safely(self) -> None:
		payload = parse_scoring_payload(
			'{'
			'"scoring_mode":"deterministic",'
			'"dependency_type":"segment",'
			'"bound_segment_id":"05_Effect",'
			'"normalisation_rule":"lowercase_trim",'
			'"match_policy":"co_occurrence_window_5",'
			'"decision_rule":"present_if_minimum_group_matches_met_or_fallback_and_not_excluded",'
			'"required_term_groups":{"effect_forms":["allocate"],"structural_features":["applications"]},'
			'"minimum_match_count_per_group":1,'
			'"excluded_terms":[],'
			'"fallback_rule":"enabled maybe; condition missing delimiter",'
			'"derived_structural_feature_rule":"this is malformed",'
			'"implicit_feature_recovery":"enabled: nope",'
			'"domain_artifact_tokens":"rubric,checklist"'
			'}'
		)
		self.assertIn("fallback_rule", payload)
		self.assertFalse(bool(payload["fallback_rule"].get("enabled", False)))
		self.assertIn("derived_structural_feature_rule", payload)
		self.assertFalse(bool(payload["derived_structural_feature_rule"].get("enabled", False)))


if __name__ == "__main__":
	unittest.main()
