from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25557_v25555_pool_no_go as target  # noqa: E402


class V25557PoolNoGoDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.diagnose(now=1)

    def test_diagnosis_binds_fixed_twenty_zero_effect_no_go(self) -> None:
        value = self.value
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["aggregate"]["task_count"], 20)
        self.assertEqual(value["aggregate"]["failure_as_zero_tasks"], 20)
        self.assertEqual(value["aggregate"]["physical_queries"], 0)
        self.assertEqual(value["aggregate"]["physical_fetches"], 0)
        self.assertEqual(value["aggregate"]["physical_model_forwards"], 0)
        self.assertFalse(value["mechanism_gate_passed"])

    def test_source_contract_identifies_pool_id_mismatch(self) -> None:
        root = self.value["root_cause"]
        self.assertEqual(
            root["runner_custom_pool_id"],
            "v25555_fresh_date_external_model_pool_v1",
        )
        self.assertEqual(
            root["deadline_limiter_required_pool_id"], target.limiter.POOL_ID
        )
        self.assertFalse(root["pool_id_equal"])
        self.assertIn("before_any_query", root["failure_boundary"])

    def test_authority_is_fix_build_only_and_forbids_same_population_retry(self) -> None:
        authority = self.value["authorization"]
        self.assertTrue(authority["successor_pool_contract_fix_build"])
        self.assertFalse(authority["same_population_retry_resume_replay_or_replacement"])
        self.assertFalse(authority["postfreeze_quality"])
        self.assertFalse(authority["deepwidebench_forward_or_evaluator"])
        self.assertEqual(self.value["positive_signed_credit_count"], 0)

    def test_resealed_root_cause_effect_credit_or_authority_tamper_fails(self) -> None:
        for kind in ("root", "effect", "credit", "authority"):
            changed = copy.deepcopy(self.value)
            if kind == "root":
                changed["root_cause"]["pool_id_equal"] = True
            elif kind == "effect":
                changed["aggregate"]["physical_model_forwards"] = 1
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["authorization"]["postfreeze_quality"] = True
            changed.pop("diagnosis_payload_sha256")
            changed = target.contract.seal(changed, "diagnosis_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate(changed)


if __name__ == "__main__":
    unittest.main()
