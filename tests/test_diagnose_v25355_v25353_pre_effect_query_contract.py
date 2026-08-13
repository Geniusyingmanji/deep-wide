from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25355_v25353_pre_effect_query_contract as target  # noqa: E402


class V25355DiagnosisTests(unittest.TestCase):
    def test_build_is_content_free_valid_and_authorizes_only_new_population_design(self) -> None:
        fake_tests = {
            "expected": 36,
            "observed": 36,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=fake_tests):
            value = target.build(now=1)
        self.assertEqual(target.validate(value), value)
        self.assertEqual(
            value["root_cause"]["class"], "pre_effect_query_contract_mismatch"
        )
        self.assertEqual(
            value["observations"]["raw_fallback_downstream_rejection_tasks"],
            20,
        )
        self.assertEqual(
            value["observations"][
                "projected_fallback_downstream_acceptance_tasks"
            ],
            20,
        )
        self.assertTrue(value["authorization"]["fresh_disjoint_population_design"])
        self.assertFalse(
            value["authorization"][
                "same_population_retry_resume_replay_backfill_or_replacement"
            ]
        )

    def test_resealed_rerun_or_effect_authority_tamper_fails(self) -> None:
        fake_tests = {
            "expected": 36,
            "observed": 36,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=fake_tests):
            value = target.build(now=1)
        for kind in ("rerun", "effect"):
            changed = copy.deepcopy(value)
            if kind == "rerun":
                changed["repair"]["rerun_same_twenty_tasks_authorized"] = True
            else:
                changed["authorization"]["external_forward_or_evaluator"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate(changed)


if __name__ == "__main__":
    unittest.main()
