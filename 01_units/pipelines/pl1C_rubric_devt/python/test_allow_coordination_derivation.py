import unittest

from generate_schema_from_segmentation_registry import (
	audit_decision_procedure_text,
	build_operator_specs_payload,
	collect_coordination_text,
	compile_operator_spec,
	default_allow_coordination_for_family,
	derive_anchor_patterns,
	detect_coordination_support,
	derive_allow_coordination,
	derive_stop_markers,
	expand_registry_instances,
	validate_decision_procedure_encoding,
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

	def test_no_anchor_passthrough_family_derives_empty_anchor_patterns(self) -> None:
		row = {
			"template_id": "B_claim_seg_00",
			"local_slot": "00",
			"anchor_patterns": "",
		}

		self.assertEqual(
			derive_anchor_patterns(row, "claim_text_passthrough_no_anchor"),
			[],
		)

	def test_compile_operator_spec_supports_no_anchor_passthrough_family(self) -> None:
		row = {
			"assessment_id": "AP2B",
			"component_id": "SectionB1Response",
			"cid": "SecB1",
			"template_id": "B_claim_seg_00",
			"local_slot": "00",
			"operator_id": "S00",
			"operator_identifier": "O_AP2B_SecB1_S00",
			"operator_identifier_shortid": "S00",
			"operator_short_description": "extract full response claim unit",
			"operator_definition": "Return the trimmed full response text.",
			"operator_guidance": "Emit the trimmed full response text when non-empty.",
			"failure_mode_guidance": "missing when empty; malformed when unrecoverable.",
			"decision_procedure": "Trim the full response text and emit it when non-empty.",
			"output_mode": "span",
			"segment_id": "00_Claim",
			"template_group": "B_claim_seg",
			"rule_id": "RR1",
			"component_block": "S",
			"instance_status": "active",
			"source_template_id": "B_claim_seg_00",
			"source_rule_id": "RR1",
			"runtime_family": "claim_text_passthrough_no_anchor",
			"anchor_patterns": "",
		}

		spec = compile_operator_spec(row)

		self.assertEqual(spec.family, "claim_text_passthrough_no_anchor")
		self.assertEqual(spec.anchor_patterns, [])
		self.assertEqual(spec.target_type, "claim_text")

	def test_explicit_allow_coordination_override_beats_template_default(self) -> None:
		row = {
			"template_id": "B_claim_seg_02",
			"allow_coordination": "false",
			"operator_definition": "This template normally defaults true.",
		}

		self.assertFalse(derive_allow_coordination(row, "right_np_after_anchor_before_marker"))

	def test_preprocessing_rules_add_anchor_alias_and_survive_expansion(self) -> None:
		preprocessing_rules = 'Normalize "to influence" -> "shaping" for anchor detection only (non-destructive).'
		registry = {
			"registry_metadata": {
				"assessment_id": "AP2B",
				"registry_version": "04",
			},
			"identifier_construction_rules": [
				{
					"row_id": "id-1",
					"execution_fields": {"field": "operator_identifier"},
					"source_text": {
						"rule": {
							"raw": "O_{assessment_id}_{cid}_{operator_id}",
							"single_line": "O_{assessment_id}_{cid}_{operator_id}",
							"lines": ["O_{assessment_id}_{cid}_{operator_id}"],
						}
					},
				},
				{
					"row_id": "id-2",
					"execution_fields": {"field": "operator_identifier_shortid"},
					"source_text": {
						"rule": {
							"raw": "operator_id",
							"single_line": "operator_id",
							"lines": ["operator_id"],
						}
					},
				},
				{
					"row_id": "id-3",
					"execution_fields": {"field": "cid derivation rule"},
					"source_text": {
						"rule": {
							"raw": 'Start with component_id; replace "Section" with "Sec"; remove "Response"',
							"single_line": 'Start with component_id; replace "Section" with "Sec"; remove "Response"',
							"lines": ['Start with component_id; replace "Section" with "Sec"; remove "Response"'],
						}
					},
				},
			],
			"reuse_rules": [
				{
					"row_id": "reuse-1",
					"execution_fields": {
						"rule_id": "RR1",
						"template_group": "B_claim_seg",
						"applies_to_component_pattern": "SectionB1Response",
						"expansion_mode": "per_component",
						"component_block_rule": "CB1",
						"local_slot_source": "template.local_slot",
						"operator_id_format": "{component_block}{local_slot}",
						"assessment_id": "AP2B",
						"status": "active",
					},
					"source_text": {},
				},
			],
			"component_block_rules": [
				{
					"row_id": "block-1",
					"execution_fields": {
						"block_rule_id": "CB1",
						"component_id": "SectionB1Response",
						"component_block": "S",
					},
					"source_text": {},
				},
			],
			"operator_templates": [
				{
					"row_id": "template-1",
					"execution_fields": {
						"template_id": "B_claim_seg_04",
						"local_slot": "04",
						"output_mode": "span",
						"segment_id": "04_Workflow",
						"status": "active",
						"preprocessing_rules": preprocessing_rules,
					},
					"source_text": {
						"operator_short_description": {"raw": "workflow", "single_line": "workflow", "lines": ["workflow"]},
						"operator_definition": {"raw": "Extract the phrase after shaping.", "single_line": "Extract the phrase after shaping.", "lines": ["Extract the phrase after shaping."]},
						"operator_guidance": {"raw": "Use the shaping anchor.", "single_line": "Use the shaping anchor.", "lines": ["Use the shaping anchor."]},
						"failure_mode_guidance": {"raw": "Mark missing if absent.", "single_line": "Mark missing if absent.", "lines": ["Mark missing if absent."]},
						"decision_procedure": {"raw": "Find the shaping marker then capture the workflow phrase.", "single_line": "Find the shaping marker then capture the workflow phrase.", "lines": ["Find the shaping marker then capture the workflow phrase."]},
					},
				},
			],
		}

		expanded_payload = expand_registry_instances(registry)
		self.assertEqual(expanded_payload["expanded_instances"][0]["preprocessing_rules"], preprocessing_rules)

		operator_specs_payload = build_operator_specs_payload(expanded_payload)
		self.assertEqual(
			operator_specs_payload["operator_specs"][0]["anchor_patterns"],
			["shaping", "to influence"],
		)

	def test_decision_procedure_audit_warns_for_unencoded_sequencing_directives(self) -> None:
		warnings = audit_decision_procedure_text(
			{
				"operator_id": "S05",
				"decision_procedure": "Step 2: Locate the first by that follows shaping (ignore any subsequent by tokens).",
			}
		)

		self.assertEqual(len(warnings), 3)
		self.assertTrue(any("S05" in warning for warning in warnings))
		self.assertTrue(any("ignore subsequent" in warning for warning in warnings))
		self.assertTrue(any("ordinal sequencing" in warning for warning in warnings))
		self.assertTrue(any("numbered steps" in warning for warning in warnings))

	def test_decision_procedure_audit_suppresses_encoded_by_after_shaping_directives(self) -> None:
		warnings = audit_decision_procedure_text(
			{
				"operator_id": "S05",
				"decision_procedure": "Step 2: Locate the first by that follows shaping (ignore any subsequent by tokens).",
				"anchor_precondition_patterns": "shaping",
				"anchor_selection_policy": "first_after_precondition",
				"stop_markers": "by, comma_new_clause, subordinate_extension, sentence_end",
			}
		)

		self.assertEqual(warnings, [])

	def test_decision_procedure_audit_ignores_numbering_when_no_unencoded_directive_remains(self) -> None:
		warnings = audit_decision_procedure_text(
			{
				"operator_id": "S01",
				"decision_procedure": "Step 1: Locate the anchor.\n\nStep 2: Extract the span.\n\nStep 3: Return ok.",
			}
		)

		self.assertEqual(warnings, [])

	def test_decision_procedure_audit_suppresses_encoded_first_candidate_directives(self) -> None:
		warnings = audit_decision_procedure_text(
			{
				"operator_id": "S02",
				"decision_procedure": "Step 2: Identify the first local noun phrase immediately after the anchor. Step 4: Stop before through, a clause-introducing comma, or another clear clause boundary.",
				"candidate_selection_policy": "first_local_candidate",
				"later_candidate_handling": "ignore_later_candidates",
				"stop_markers": "through, comma, clause_boundary",
			}
		)

		self.assertEqual(warnings, [])

	def test_decision_procedure_encoding_requires_first_candidate_field(self) -> None:
		with self.assertRaisesRegex(ValueError, "candidate_selection_policy='first_local_candidate'"):
			validate_decision_procedure_encoding(
				{
					"operator_id": "S02",
					"decision_procedure": "Step 2: Identify the first local noun phrase immediately after the anchor.",
				}
			)

	def test_decision_procedure_encoding_requires_clause_boundary_marker(self) -> None:
		with self.assertRaisesRegex(ValueError, "stop_markers including one of"):
			validate_decision_procedure_encoding(
				{
					"operator_id": "S03",
					"decision_procedure": "Step 4: Stop before shaping, a clause-introducing comma, or another clear clause boundary.",
					"candidate_selection_policy": "first_local_candidate",
					"later_candidate_handling": "ignore_later_candidates",
					"stop_markers": "shaping",
				}
			)

	def test_decision_procedure_audit_suppresses_encoded_anchor_precondition_selection(self) -> None:
		warnings = audit_decision_procedure_text(
			{
				"operator_id": "S05",
				"decision_procedure": "Step 2: Locate the first by that follows shaping (ignore any subsequent by tokens).",
				"anchor_precondition_patterns": "shaping",
				"anchor_selection_policy": "first_after_precondition",
				"stop_markers": "by, comma_new_clause, subordinate_extension, sentence_end",
			}
		)

		self.assertEqual(warnings, [])

	def test_decision_procedure_encoding_requires_anchor_selection_policy(self) -> None:
		with self.assertRaisesRegex(ValueError, "anchor_selection_policy='first_after_precondition'"):
			validate_decision_procedure_encoding(
				{
					"operator_id": "S05",
					"decision_procedure": "Step 2: Locate the first by that follows shaping (ignore any subsequent by tokens).",
					"stop_markers": "by, comma_new_clause, subordinate_extension, sentence_end",
				}
			)


if __name__ == "__main__":
	unittest.main()