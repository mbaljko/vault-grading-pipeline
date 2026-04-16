import unittest
from types import SimpleNamespace
from unittest.mock import patch

from layer0_runtime.boundaries import find_anchor_occurrences
from layer0_runtime.families import run_right_np_after_anchor_before_marker, run_span_after_marker_before_marker
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


if __name__ == "__main__":
	unittest.main()