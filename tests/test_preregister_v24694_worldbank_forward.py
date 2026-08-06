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

from scripts import preregister_v24694_worldbank_forward as target  # noqa: E402


class V24694WorldBankProtocolTests(unittest.TestCase):
    def synthetic(self):
        population = {
            "selected_count": 48,
            "selected_region_count": 6,
            "selected_region_max": 9,
            "excluded_iso3_count": 23,
            "selected_visible_vector_sha256": "b" * 64,
        }
        with patch.object(target, "_parents", return_value=({}, {}, population)), patch.object(
            target, "sha256", return_value="a" * 64
        ), patch.object(
            target, "protected_watcher_snapshot", return_value=[]
        ):
            return target.build_protocol(now=0, require_clean=False, require_pristine=False)

    def test_protocol_is_inert_and_label_blind(self) -> None:
        value = self.synthetic()
        self.assertEqual(value["task_contract"]["runtime_input_keys"], ["opaque_id", "question"])
        self.assertFalse(value["authorization"]["preactivation_audit_generation"])
        self.assertFalse(value["authorization"]["activation_or_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_execution_and_effect_caps_are_fixed(self) -> None:
        value = self.synthetic()
        self.assertEqual(value["execution"]["executor_concurrency"], 12)
        self.assertEqual(value["execution"]["model_slot_cap"], 8)
        self.assertEqual(value["execution"]["task_wall_seconds"], 240.0)
        self.assertEqual(value["execution"]["hard_fetch_deadline_seconds"], 40.0)
        self.assertEqual(value["mechanism"]["fixed_generic_plus_exact_fetch_cap"], [2, 8, 10])

    def test_entropy_cannot_route_or_receive_credit(self) -> None:
        mechanism = self.synthetic()["mechanism"]
        self.assertTrue(mechanism["entropy_shadow_only"])
        self.assertFalse(mechanism["positive_task_credit_assigned"])

    def test_forward_manifest_excludes_evaluator_surfaces(self) -> None:
        for path in target.DEPENDENCIES:
            for marker in target.FORBIDDEN_MARKERS:
                self.assertNotIn(marker, path)

    def test_protocol_seal_detects_tamper(self) -> None:
        value = self.synthetic()
        unsigned = copy.deepcopy(value)
        seal = unsigned.pop("protocol_sha256")
        self.assertEqual(seal, target.payload_sha256(unsigned))
        unsigned["authorization"]["activation_or_launch"] = True
        self.assertNotEqual(seal, target.payload_sha256(unsigned))


if __name__ == "__main__":
    unittest.main()
