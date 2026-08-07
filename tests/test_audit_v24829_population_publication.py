from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24829_population_publication as target  # noqa: E402


class V24829PopulationPublicationAuditTests(unittest.TestCase):
    def test_current_publication_is_valid_and_design_only(self) -> None:
        with patch.object(target.design, "_git", side_effect=lambda *args: "" if args == ("status", "--porcelain") else "same"):
            value = target.build(now=0)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(value["counts"]["selected_gold_cells"], 256)
        self.assertEqual(value["counts"]["selected_gold_cell_overlap"], 0)
        self.assertEqual(value["counts"]["selected_target_pair_overlap"], 0)
        self.assertEqual(value["counts"]["selected_entity_overlap"], 128)
        self.assertTrue(value["authorization"]["fresh_external_protocol_design"])
        self.assertFalse(value["authorization"]["external_launch"])

    def test_resealed_authority_tamper_fails_closed(self) -> None:
        with patch.object(target.design, "_git", side_effect=lambda *args: "" if args == ("status", "--porcelain") else "same"):
            value = target.build(now=0)
        changed = copy.deepcopy(value)
        changed["authorization"]["external_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.design.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate(changed)

    def test_private_surface_is_not_forward_authorized(self) -> None:
        private = target._read(target.design.PRIVATE)
        self.assertFalse(private["forward_import_or_runtime_read_authorized"])
        self.assertFalse(
            private["gold_provenance_or_evaluator_read_before_prediction_freeze_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
