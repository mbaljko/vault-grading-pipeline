import unittest

from layer1_recovery_overlay import (
    apply_recovery_overlay_to_l1_scores,
    build_recovery_membership_index,
    score_recovery_indicator_membership,
    validate_recovery_allowlist_rows,
    validate_recovery_registry_rows,
)


class Layer1RecoveryOverlayTests(unittest.TestCase):
    def test_validate_recovery_registry_rows_rejects_bad_mode(self) -> None:
        rows = [
            {
                "component_id": "SectionB1Response",
                "indicator_id": "I11",
                "indicator_kind": "primary",
                "status": "active",
            },
            {
                "component_id": "SectionB1Response",
                "indicator_id": "I11_RECOVERY",
                "indicator_kind": "recovery",
                "sibling_of_indicator_id": "I11",
                "recovery_mode": "unsupported_mode",
                "recovery_precedence": "force_present",
                "recovery_list_ref": "iter02/00_recovery_overrides/layer1_recovery_allowlist.csv",
                "status": "active",
            },
        ]
        errors = validate_recovery_registry_rows(rows)
        self.assertTrue(any("unsupported recovery_mode" in error for error in errors))

    def test_validate_recovery_allowlist_rows_detects_unknown_submission_and_duplicate(self) -> None:
        allowlist_rows = [
            {
                "component_id": "SectionB1Response",
                "parent_indicator_id": "I11",
                "submission_id": "SUB-404",
                "recovery_indicator_id": "I11_RECOVERY",
                "reason_code": "manual_review_override",
                "added_by": "ta",
                "added_at_utc": "2026-04-25T14:00:00Z",
                "expires_at_utc": "",
                "active": "true",
            },
            {
                "component_id": "SectionB1Response",
                "parent_indicator_id": "I11",
                "submission_id": "SUB-404",
                "recovery_indicator_id": "I11_RECOVERY",
                "reason_code": "manual_review_override",
                "added_by": "ta",
                "added_at_utc": "2026-04-25T14:05:00Z",
                "expires_at_utc": "",
                "active": "true",
            },
        ]
        errors = validate_recovery_allowlist_rows(
            allowlist_rows,
            known_submission_ids={"SUB-001"},
            known_parent_indicator_ids={"I11"},
        )
        self.assertTrue(any("unknown submission_id" in error for error in errors))
        self.assertTrue(any("duplicate active allowlist key" in error for error in errors))

    def test_score_recovery_indicator_membership_marks_expired_row(self) -> None:
        index = {
            ("SectionB1Response", "I11", "SUB-001"): {
                "component_id": "SectionB1Response",
                "parent_indicator_id": "I11",
                "submission_id": "SUB-001",
                "recovery_indicator_id": "I11_RECOVERY",
                "reason_code": "old_override",
                "added_by": "ta",
                "added_at_utc": "2026-04-20T00:00:00Z",
                "expires_at_utc": "2026-04-24T23:59:59Z",
                "active": "true",
            }
        }
        status, meta = score_recovery_indicator_membership(
            component_id="SectionB1Response",
            parent_indicator_id="I11",
            submission_id="SUB-001",
            membership_index=index,
            now_utc="2026-04-25T12:00:00Z",
        )
        self.assertEqual(status, "not_present")
        self.assertIn("recovery_row_expired", meta.get("flags", ""))

    def test_apply_recovery_overlay_promotes_present_via_recovery(self) -> None:
        scored_rows = [
            {
                "submission_id": "SUB-001",
                "component_id": "SectionB1Response",
                "indicator_id": "I11",
                "evidence_status": "not_present",
                "flags": "none",
            }
        ]
        registry_rows = [
            {
                "component_id": "SectionB1Response",
                "indicator_id": "I11",
                "indicator_kind": "primary",
                "status": "active",
            },
            {
                "component_id": "SectionB1Response",
                "indicator_id": "I11_RECOVERY",
                "indicator_kind": "recovery",
                "sibling_of_indicator_id": "I11",
                "recovery_mode": "manual_allowlist",
                "recovery_precedence": "force_present",
                "recovery_list_ref": "iter02/00_recovery_overrides/layer1_recovery_allowlist.csv",
                "status": "active",
            },
        ]
        allowlist_rows = [
            {
                "component_id": "SectionB1Response",
                "parent_indicator_id": "I11",
                "submission_id": "SUB-001",
                "recovery_indicator_id": "I11_RECOVERY",
                "reason_code": "manual_review_override",
                "added_by": "ta",
                "added_at_utc": "2026-04-25T14:00:00Z",
                "expires_at_utc": "",
                "active": "true",
            }
        ]

        overlay_rows = apply_recovery_overlay_to_l1_scores(
            scored_rows,
            recovery_registry_rows=registry_rows,
            membership_index=build_recovery_membership_index(allowlist_rows),
            now_utc="2026-04-25T15:00:00Z",
        )

        self.assertEqual(overlay_rows[0]["evidence_status_primary"], "not_present")
        self.assertEqual(overlay_rows[0]["evidence_status_recovery"], "present")
        self.assertEqual(overlay_rows[0]["evidence_status_effective"], "present")
        self.assertIn("present_via_recovery", overlay_rows[0]["flags"])

    def test_apply_recovery_overlay_preserves_primary_present(self) -> None:
        scored_rows = [
            {
                "submission_id": "SUB-001",
                "component_id": "SectionB1Response",
                "indicator_id": "I11",
                "evidence_status": "present",
                "flags": "none",
            }
        ]
        overlay_rows = apply_recovery_overlay_to_l1_scores(
            scored_rows,
            recovery_registry_rows=[],
            membership_index={},
            now_utc="2026-04-25T15:00:00Z",
        )
        self.assertEqual(overlay_rows[0]["evidence_status_effective"], "present")
        self.assertEqual(overlay_rows[0]["evidence_status_recovery"], "not_present")


if __name__ == "__main__":
    unittest.main()
