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


if __name__ == "__main__":
    unittest.main()
