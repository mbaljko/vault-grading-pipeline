from __future__ import annotations

import csv
import tempfile
from pathlib import Path
import unittest

from populate_gradebook_from_inputs import populate_gradebook


class PopulateGradebookL3CommentTests(unittest.TestCase):
    def test_feedback_comments_appends_l3_comment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            gradebook_input = temp_path / "gradebook.csv"
            canonical_input = temp_path / "canonical.csv"
            scored_input = temp_path / "scored.csv"
            output_file = temp_path / "output.csv"

            with gradebook_input.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "Identifier",
                        "Full name",
                        "Email address",
                        "Grade",
                        "Feedback comments",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "Identifier": "stu-01",
                        "Full name": "A Student",
                        "Email address": "a.student@example.edu",
                        "Grade": "",
                        "Feedback comments": "",
                    }
                )

            with canonical_input.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["submission_id", "GW.Identifier", "GW.Full name", "User", "Username"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "submission_id": "1001",
                        "GW.Identifier": "stu-01",
                        "GW.Full name": "A Student",
                        "User": "A Student",
                        "Username": "a.student",
                    }
                )

            with scored_input.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "submission_id",
                        "submission_numeric_score",
                        "Feedback comments",
                        "L3_comment",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "submission_id": "1001",
                        "submission_numeric_score": "0.75",
                        "Feedback comments": "Primary feedback summary.",
                        "L3_comment": "Developmental interpretation present.",
                    }
                )

            populate_gradebook(
                gradebook_input=gradebook_input,
                canonical_input=canonical_input,
                scored_input=scored_input,
                output_file=output_file,
                grade_column="Grade",
            )

            with output_file.open("r", encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))

            self.assertEqual(row["Grade"], "0.75")
            self.assertEqual(
                row["Feedback comments"],
                "Primary feedback summary.\nDevelopmental interpretation present.",
            )

    def test_feedback_comments_does_not_append_pipe_joined_l3_comment_when_grouped_feedback_already_contains_segments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            gradebook_input = temp_path / "gradebook.csv"
            canonical_input = temp_path / "canonical.csv"
            scored_input = temp_path / "scored.csv"
            output_file = temp_path / "output.csv"

            grouped_feedback = "\n".join(
                [
                    "Overall result for SectionB: meets expectations (13 / 15). 12 dimensions.",
                    "SectionB1",
                    "  D11: demonstrated",
                    "Claim is structurally complete and clearly identifies an actor, tool or artefact, mediation action, workflow stage, and valid action-object relationship within the required template structure.",
                    "SectionB2",
                    "  D21: demonstrated",
                    "Claim identifies an actor, tool or artefact, mediation action, and workflow stage, but the action-object relationship is structurally incomplete or insufficiently specified.",
                ]
            )
            legacy_flat_comment = (
                "Claim is structurally complete and clearly identifies an actor, tool or artefact, mediation action, "
                "workflow stage, and valid action-object relationship within the required template structure. | "
                "Claim identifies an actor, tool or artefact, mediation action, and workflow stage, but the "
                "action-object relationship is structurally incomplete or insufficiently specified."
            )

            with gradebook_input.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "Identifier",
                        "Full name",
                        "Email address",
                        "Grade",
                        "Feedback comments",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "Identifier": "stu-01",
                        "Full name": "A Student",
                        "Email address": "a.student@example.edu",
                        "Grade": "",
                        "Feedback comments": "",
                    }
                )

            with canonical_input.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["submission_id", "GW.Identifier", "GW.Full name", "User", "Username"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "submission_id": "1001",
                        "GW.Identifier": "stu-01",
                        "GW.Full name": "A Student",
                        "User": "A Student",
                        "Username": "a.student",
                    }
                )

            with scored_input.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "submission_id",
                        "submission_numeric_score",
                        "Feedback comments",
                        "L3_comment",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "submission_id": "1001",
                        "submission_numeric_score": "13",
                        "Feedback comments": grouped_feedback,
                        "L3_comment": legacy_flat_comment,
                    }
                )

            populate_gradebook(
                gradebook_input=gradebook_input,
                canonical_input=canonical_input,
                scored_input=scored_input,
                output_file=output_file,
                grade_column="Grade",
            )

            with output_file.open("r", encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))

            self.assertEqual(row["Feedback comments"], grouped_feedback)


if __name__ == "__main__":
    unittest.main()
