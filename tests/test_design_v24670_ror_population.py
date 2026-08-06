from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24670_ror_population as design  # noqa: E402


class V24670PopulationTests(unittest.TestCase):
    def test_historical_vector_adds_all_v24664_visible_entities(self) -> None:
        visible, canonical = design.historical_entities()
        previous = {entity for group in design.V24664 for entity in group}
        self.assertEqual(len(previous), 48)
        self.assertEqual(len(visible), 4_576)
        self.assertEqual(len(canonical), 4_576)
        self.assertTrue(previous.issubset(visible))

    def test_fixed_immutable_tree_and_population_size(self) -> None:
        self.assertEqual(design.COMMIT, "aab1443afefefa8460e69ab01bccceff0a8544d4")
        self.assertEqual(design.VERSION, "v2.11")
        self.assertEqual((design.SLICE_START, design.SLICE_STOP), (0, 3_482))
        self.assertEqual(design.SELECTED_COUNT, 48)

    def test_parent_grants_design_not_launch_or_evaluator(self) -> None:
        self.assertTrue(design._parent_valid())
        parent = design._read(ROOT / design.PARENT)
        self.assertTrue(
            parent["authorization"]["fresh_nonoverlapping_external_protocol_design"]
        )
        self.assertFalse(
            parent["authorization"]["fresh_external_activation_or_launch"]
        )
        self.assertFalse(parent["authorization"]["evaluator"])
        self.assertFalse(parent["authorization"]["dev64_design_or_launch"])
        self.assertFalse(parent["authorization"]["exact220"])

    def test_parent_resealed_launch_tamper_fails_closed(self) -> None:
        value = design._read(ROOT / design.PARENT)
        value["authorization"]["fresh_external_activation_or_launch"] = True
        value.pop("audit_payload_sha256")
        value["audit_payload_sha256"] = design.payload_sha256(value)
        with patch.object(design, "_read", return_value=value):
            self.assertFalse(design._parent_valid())


if __name__ == "__main__":
    unittest.main()
