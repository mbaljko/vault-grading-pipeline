import unittest
from types import SimpleNamespace
from unittest.mock import patch

from layer0_runtime.boundaries import find_anchor_occurrences
from layer0_runtime.families import (
	run_claim_text_passthrough_no_anchor,
	run_local_effect_phrase_after_marker,
	run_right_np_after_anchor_before_marker,
	run_span_after_marker_before_marker,
)
from layer0_runtime.loader import validate_spec
from layer0_runtime.models import OperatorSpec


def make_spec(*, operator_id: str, family: str, anchor_patterns: list[str], stop_markers: list[str], allow_coordination: bool) -> OperatorSpec:
	return OperatorSpec(
		assessment_id="AP2B",
		component_id="SectionB1Response",
		cid="SecB1",
		template_id="B_claim_seg_test",
		local_slot="02",
		operator_id=operator_id,
		operator_identifier=f"O_AP2B_TEST_{operator_id}",
		operator_identifier_shortid=operator_id,
		operator_short_description="test operator",
		segment_id="Segment",
		output_mode="span",
		family=family,
		anchor_patterns=anchor_patterns,
		direction="right",
		start_rule="immediate_post_anchor",
		end_rule="first_stop_marker",
		stop_markers=stop_markers,
		target_type="noun_phrase",
		allow_coordination=allow_coordination,
		skip_later_candidates=False,
		operator_definition="test definition",
		operator_guidance="test guidance",
		failure_mode_guidance="test failure guidance",
		decision_procedure="test decision procedure",
		missing_status="missing",
		ambiguous_status="ambiguous",
		malformed_status="malformed",
		instance_status="active",
		anchor_precondition_patterns=[],
		anchor_selection_policy="first_match",
	)


class Layer0RuntimeCoordinationTests(unittest.TestCase):
	def _fallback_doc(self, text: str) -> SimpleNamespace:
		return SimpleNamespace(text=text)

	@patch("layer0_runtime.families.parse_text")
	def test_right_np_extracts_after_connects_with_anchor(self, mock_parse_text) -> None:
		text = "Institutions connects with workload balancing requirements through reviewer assignment logic."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S102",
			family="right_np_after_anchor_before_marker",
			anchor_patterns=["connects with"],
			stop_markers=["through", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_right_np_after_anchor_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "workload balancing requirements")

	@patch("layer0_runtime.families.parse_text")
	def test_right_np_extracts_after_bare_interacts_anchor(self, mock_parse_text) -> None:
		text = "Institutions interacts human decision authority through scoring rubric shaping committee deliberation."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S102",
			family="right_np_after_anchor_before_marker",
			anchor_patterns=["interacts"],
			stop_markers=["through", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_right_np_after_anchor_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "human decision authority")

	@patch("layer0_runtime.families.parse_text")
	def test_right_np_extends_through_and_coordination(self, mock_parse_text) -> None:
		text = "Institutions interact with schools and families through mentorship."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S102",
			family="right_np_after_anchor_before_marker",
			anchor_patterns=["interact with"],
			stop_markers=["through", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_right_np_after_anchor_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "schools and families")

	@patch("layer0_runtime.families.parse_text")
	def test_right_np_keeps_first_candidate_when_coordination_disabled(self, mock_parse_text) -> None:
		text = "Institutions interact with schools and families through mentorship."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S102",
			family="right_np_after_anchor_before_marker",
			anchor_patterns=["interact with"],
			stop_markers=["through", "comma", "clause_boundary"],
			allow_coordination=False,
		)

		result = run_right_np_after_anchor_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "schools")

	@patch("layer0_runtime.families.parse_text")
	def test_right_np_extends_through_compact_comma_coordination(self, mock_parse_text) -> None:
		text = "Institutions interact with schools, families, and community groups through mentorship."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S102",
			family="right_np_after_anchor_before_marker",
			anchor_patterns=["interact with"],
			stop_markers=["through", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_right_np_after_anchor_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "schools, families, and community groups")

	@patch("layer0_runtime.families.parse_text")
	def test_span_after_marker_uses_first_local_np_with_coordination(self, mock_parse_text) -> None:
		text = "Institutions interact with communities through tutoring and mentoring shaping civic habits."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S103",
			family="span_after_marker_before_marker",
			anchor_patterns=["through"],
			stop_markers=["shaping", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_span_after_marker_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "tutoring and mentoring")

	@patch("layer0_runtime.families.parse_text")
	def test_span_after_marker_stops_before_clause_comma(self, mock_parse_text) -> None:
		text = "Institutions interact with communities through the AI generated condensed summary, directly shaping reviewer attention."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S103",
			family="span_after_marker_before_marker",
			anchor_patterns=["through"],
			stop_markers=["shaping", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_span_after_marker_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "the AI generated condensed summary")

	@patch("layer0_runtime.families.parse_text")
	def test_span_after_marker_stops_before_infinitive_extension(self, mock_parse_text) -> None:
		text = "Institutions interact with communities through the structured scoring rubric interface to influence reviewer assessment."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S103",
			family="span_after_marker_before_marker",
			anchor_patterns=["through"],
			stop_markers=["shaping", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_span_after_marker_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "the structured scoring rubric interface")

	@patch("layer0_runtime.families.parse_text")
	def test_span_after_marker_stops_before_new_ap1b_markers(self, mock_parse_text) -> None:
		mock_parse_text.side_effect = self._fallback_doc
		cases = [
			(
				"uses the online portal to submit applications",
				"to",
				"the online portal",
			),
			(
				"uses flagged case files which contain applicant details",
				"which",
				"flagged case files",
			),
			(
				"uses the dashboard that displays routing status",
				"that",
				"the dashboard",
			),
			(
				"uses reports where escalation is logged",
				"where",
				"reports",
			),
			(
				"uses the case file who is assigned manually",
				"who",
				"the case file",
			),
		]

		for text, stop_marker, expected in cases:
			with self.subTest(stop_marker=stop_marker, text=text):
				spec = make_spec(
					operator_id="S103",
					family="span_after_marker_before_marker",
					anchor_patterns=["uses"],
					stop_markers=[stop_marker],
					allow_coordination=True,
				)

				result = run_span_after_marker_before_marker(text, spec)

				self.assertEqual(result.extraction_status, "ok")
				self.assertEqual(result.segment_text, expected)

	def test_anchor_matching_does_not_fire_inside_throughput(self) -> None:
		text = "Reporting obligations interact with throughput expectations through scoring rubric."

		occurrences = find_anchor_occurrences(text, ["through"])

		self.assertEqual(len(occurrences), 1)
		self.assertEqual(text[occurrences[0][0]:occurrences[0][1]].lower(), "through")

	def test_anchor_matching_prefers_longer_anchor_at_same_position(self) -> None:
		text = "The institutional demand interacts with documentation requirements through scoring rubric."

		occurrences = find_anchor_occurrences(text, ["interacts", "interacts with"])

		self.assertGreaterEqual(len(occurrences), 2)
		self.assertEqual(text[occurrences[0][0]:occurrences[0][1]].lower(), "interacts with")

	@patch("layer0_runtime.families.parse_text")
	def test_right_np_expands_attached_pp_phrase(self, mock_parse_text) -> None:
		text = "Institutions interacts with throughput expectations tied to funding-cycle schedules through reviewer assignment logic."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S102",
			family="right_np_after_anchor_before_marker",
			anchor_patterns=["interacts with"],
			stop_markers=["through", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_right_np_after_anchor_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "throughput expectations tied to funding-cycle schedules")

	@patch("layer0_runtime.families.parse_text")
	def test_right_np_expands_coordination_and_pp(self, mock_parse_text) -> None:
		text = "Institutions interacts with documentation and record-keeping standards for audit through reviewer assignment logic."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S102",
			family="right_np_after_anchor_before_marker",
			anchor_patterns=["interacts with"],
			stop_markers=["through", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_right_np_after_anchor_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "documentation and record-keeping standards for audit")

	@patch("layer0_runtime.families.parse_text")
	def test_anchor_precondition_policy_applies_generically(self, mock_parse_text) -> None:
		text = "Demands interact with communities and shaping control text by sequencing attention by surfacing excerpts."
		mock_parse_text.side_effect = self._fallback_doc
		spec = OperatorSpec(
			assessment_id="AP2B",
			component_id="SectionB1Response",
			cid="SecB1",
			template_id="B_claim_seg_05",
			local_slot="05",
			operator_id="S05",
			operator_identifier="O_AP2B_TEST_S05",
			operator_identifier_shortid="S05",
			operator_short_description="test precondition policy",
			segment_id="05_Effect",
			output_mode="span",
			family="local_effect_phrase_after_marker",
			anchor_patterns=["by"],
			direction="right",
			start_rule="immediate_post_anchor",
			end_rule="first_stop_marker",
			stop_markers=["by", "comma_new_clause", "subordinate_extension", "sentence_end"],
			target_type="local_effect_phrase",
			allow_coordination=True,
			skip_later_candidates=False,
			operator_definition="test definition",
			operator_guidance="test guidance",
			failure_mode_guidance="test failure guidance",
			decision_procedure="test decision procedure",
			missing_status="missing",
			ambiguous_status="ambiguous",
			malformed_status="malformed",
			instance_status="active",
			anchor_precondition_patterns=["shaping"],
			anchor_selection_policy="first_after_precondition",
			candidate_selection_policy="first_local_candidate",
			later_candidate_handling="ignore_later_candidates",
		)

		result = run_local_effect_phrase_after_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "sequencing attention")

	@patch("layer0_runtime.families.parse_text")
	def test_boundary_misparse_emitted_for_failed_boundary_recovery(self, mock_parse_text) -> None:
		text = "Institutions interacts with, documentation and record-keeping standards through reviewer assignment logic."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S102",
			family="right_np_after_anchor_before_marker",
			anchor_patterns=["interacts with"],
			stop_markers=["comma", "clause_boundary"],
			allow_coordination=False,
		)

		result = run_right_np_after_anchor_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "missing")
		self.assertEqual(result.flags, "boundary_misparse")

	@patch("layer0_runtime.families.parse_text")
	def test_missing_emitted_for_true_absence(self, mock_parse_text) -> None:
		text = "Institutions document policies without any interaction anchor."
		mock_parse_text.side_effect = self._fallback_doc
		spec = make_spec(
			operator_id="S102",
			family="right_np_after_anchor_before_marker",
			anchor_patterns=["interacts with"],
			stop_markers=["through", "comma", "clause_boundary"],
			allow_coordination=True,
		)

		result = run_right_np_after_anchor_before_marker(text, spec)

		self.assertEqual(result.extraction_status, "missing")
		self.assertNotEqual(result.flags, "boundary_misparse")

	def test_claim_text_passthrough_no_anchor_returns_trimmed_full_text(self) -> None:
		text = "  This is the full claim text for downstream evaluation.  "
		spec = OperatorSpec(
			assessment_id="AP2B",
			component_id="SectionB1Response",
			cid="SecB1",
			template_id="B_claim_seg_00",
			local_slot="00",
			operator_id="S00",
			operator_identifier="O_AP2B_TEST_S00",
			operator_identifier_shortid="S00",
			operator_short_description="test no-anchor claim passthrough",
			segment_id="00_Claim",
			output_mode="span",
			family="claim_text_passthrough_no_anchor",
			anchor_patterns=[],
			direction="none",
			start_rule="full_text_without_anchor",
			end_rule="full_text",
			stop_markers=[],
			target_type="claim_text",
			allow_coordination=False,
			skip_later_candidates=False,
			operator_definition="test definition",
			operator_guidance="test guidance",
			failure_mode_guidance="test failure guidance",
			decision_procedure="test decision procedure",
			missing_status="missing",
			ambiguous_status="ambiguous",
			malformed_status="malformed",
			instance_status="active",
			anchor_precondition_patterns=[],
			anchor_selection_policy="first_match",
			candidate_selection_policy="unspecified",
			later_candidate_handling="unspecified",
		)

		validate_spec(spec)
		result = run_claim_text_passthrough_no_anchor(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "This is the full claim text for downstream evaluation")

	def test_local_effect_uses_first_by_after_shaping_and_stops_before_second_by(self) -> None:
		text = "The mechanism shapes reviewer preparation by sequencing attention by surfacing criterion-linked excerpts."
		spec = OperatorSpec(
			assessment_id="AP2B",
			component_id="SectionB1Response",
			cid="SecB1",
			template_id="B_claim_seg_05",
			local_slot="05",
			operator_id="S05",
			operator_identifier="O_AP2B_TEST_S05",
			operator_identifier_shortid="S05",
			operator_short_description="test local effect operator",
			segment_id="05_Effect",
			output_mode="span",
			family="local_effect_phrase_after_marker",
			anchor_patterns=["by"],
			direction="right",
			start_rule="immediate_post_anchor",
			end_rule="local_effect_boundary",
			stop_markers=["by", "comma_new_clause", "subordinate_extension", "sentence_end"],
			target_type="local_effect_phrase",
			allow_coordination=True,
			skip_later_candidates=False,
			operator_definition="test definition",
			operator_guidance="test guidance",
			failure_mode_guidance="test failure guidance",
			decision_procedure="test decision procedure",
			missing_status="missing",
			ambiguous_status="ambiguous",
			malformed_status="malformed",
			instance_status="active",
			anchor_precondition_patterns=["shaping", "shapes"],
			anchor_selection_policy="first_after_precondition",
		)

		result = run_local_effect_phrase_after_marker(text, spec)

		self.assertEqual(result.extraction_status, "ok")
		self.assertEqual(result.segment_text, "sequencing attention")


if __name__ == "__main__":
	unittest.main()