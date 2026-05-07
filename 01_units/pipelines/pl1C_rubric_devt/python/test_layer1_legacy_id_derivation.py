from __future__ import annotations

import unittest

from generate_rubric_and_manifest_from_indicator_registry import derive_legacy_layer1_indicator_id
from generate_rubric_and_manifest_from_indicator_registry_non_Layer0_consuming import (
    derive_legacy_layer1_indicator_id as derive_legacy_layer1_indicator_id_non_layer0,
)


class Layer1LegacyIdDerivationTests(unittest.TestCase):
    def test_primary_generator_preserves_section_letter_and_number(self) -> None:
        self.assertEqual(derive_legacy_layer1_indicator_id("SectionA1Response", "01"), "IA11")
        self.assertEqual(derive_legacy_layer1_indicator_id("SectionB21Response", "09"), "IB219")

    def test_non_layer0_generator_preserves_section_letter_and_number(self) -> None:
        self.assertEqual(derive_legacy_layer1_indicator_id_non_layer0("SectionA1Response", "01"), "IA11")
        self.assertEqual(derive_legacy_layer1_indicator_id_non_layer0("SectionB21Response", "09"), "IB219")


if __name__ == "__main__":
    unittest.main()
