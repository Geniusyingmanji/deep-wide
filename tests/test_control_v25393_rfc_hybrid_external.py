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

from scripts import control_v25393_rfc_hybrid_external as target  # noqa: E402


def _fake_tests(fill: str = "a"):
    return {
        "expected": target.EXPECTED_TESTS,
        "observed": target.EXPECTED_TESTS,
        "passed": True,
        "suites": [
            {
                "pattern": pattern,
                "expected": expected,
                "observed": expected,
                "returncode": 0,
                "passed": True,
                "output_sha256": fill * 64,
            }
            for pattern, expected in target.TEST_SUITES
        ],
    }


class V25393RfcHybridControlTests(unittest.TestCase):
    def test_contract_protocol_validates_without_launch_authority(self) -> None:
        value = target.contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="a" * 64,
        )
        self.assertEqual(
            target.contract.validate_protocol(ROOT, value, tracked=False), value
        )
        self.assertFalse(value["authorization"]["one_external_forward"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertTrue(value["execution"]["one_final_joint_table_record_synthesis"])
        self.assertTrue(value["execution"]["persist_prediction_hashes_not_prediction_text"])
        self.assertEqual(value["execution"]["candidate_model_forward_count"], 0)

    def test_build_audit_authorizes_protocol_generation_only(self) -> None:
        with (
            mock.patch.object(target, "_tests", return_value=_fake_tests()),
            mock.patch.object(target, "_future_pristine", return_value=True),
        ):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build(value), value)
        self.assertTrue(
            value["authorization"]["protocol_generation_after_build_commit_push"]
        )
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_resealed_launch_credit_parent_or_persistence_tamper_fails(self) -> None:
        with (
            mock.patch.object(target, "_tests", return_value=_fake_tests("b")),
            mock.patch.object(target, "_future_pristine", return_value=True),
        ):
            value = target.build_audit(now=1, require_clean=False)
        for kind in ("launch", "credit", "parent", "persistence"):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"]["external_forward"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "parent":
                changed["checks"]["runtime_and_population_parent_barriers_exact"] = False
            else:
                changed["checks"]["prediction_text_not_persisted"] = False
            changed.pop("audit_payload_sha256")
            changed = target.contract.seal(changed, "audit_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_build(changed)

    def test_control_source_has_no_evaluator_or_benchmark_entrypoint(self) -> None:
        source = (ROOT / target.contract.CONTROL).read_text(encoding="utf-8")
        for forbidden in (
            "run_official_eval_local(",
            "leaderboard_submit(",
            "run_exact220(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
