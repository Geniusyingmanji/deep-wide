from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24822_population_publication as target  # noqa: E402


class V24822PublicationAuditTests(unittest.TestCase):
    def test_build_recomputes_disjointness_and_binding(self) -> None:
        value = target.build(now=1)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(value["counts"]["tasks"], 32)
        self.assertEqual(value["counts"]["selected_entities"], 128)
        self.assertEqual(value["counts"]["selected_gold_cells"], 256)
        self.assertEqual(value["counts"]["selected_gold_cell_overlap"], 0)
        self.assertEqual(value["counts"]["selected_target_pair_overlap"], 0)
        self.assertEqual(value["counts"]["selected_entity_overlap"], 119)

    def test_entity_overlap_is_disclosed_not_hidden(self) -> None:
        value = target.build(now=1)
        self.assertTrue(value["checks"]["entity_overlap_disclosed_exactly"])
        self.assertGreater(value["counts"]["selected_entity_overlap"], 0)
        self.assertGreater(value["counts"]["selected_entity_novel"], 0)

    def test_audit_grants_protocol_design_only(self) -> None:
        value = target.build(now=1)
        self.assertTrue(value["authorization"]["fresh_external_protocol_design"])
        self.assertFalse(value["authorization"]["external_launch"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertFalse(value["authorization"]["public_dev64_or_exact220"])

    def test_resealed_public_authority_tamper_is_detectable(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("publication audit has not been published")
        value = json.loads(path.read_text(encoding="utf-8"))
        changed = copy.deepcopy(value)
        changed["authorization"]["public_dev64_or_exact220"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.design.payload_sha256(changed)
        self.assertNotEqual(
            changed["authorization"], value["authorization"]
        )
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["authorization"]["public_dev64_or_exact220"])


if __name__ == "__main__":
    unittest.main()
