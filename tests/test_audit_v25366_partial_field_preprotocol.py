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

from scripts import audit_v25366_partial_field_preprotocol as target  # noqa: E402


def fake_tests():
    return {
        "expected": target.EXPECTED_TESTS,
        "observed": target.EXPECTED_TESTS,
        "passed": True,
        "suites": [],
    }


class V25366PartialFieldPreprotocolTests(unittest.TestCase):
    def test_build_and_population_barriers_are_exact(self) -> None:
        self.assertTrue(target._build_barrier())
        self.assertTrue(target._population_barrier())
        self.assertEqual(target.EXPECTED_TESTS, 20)

    def test_success_authorizes_protocol_design_only(self) -> None:
        with mock.patch.object(target, "_tests", return_value=fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        authorization = value["authorization"]
        self.assertTrue(
            authorization["third_fresh_partial_field_protocol_design"]
        )
        self.assertFalse(authorization["external_activation_or_launch"])
        self.assertFalse(authorization["evaluator_or_deepwidebench_or_sota"])

    def test_resealed_activation_evaluator_reuse_credit_or_hash_tamper_fails(self) -> None:
        with mock.patch.object(target, "_tests", return_value=fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("activation", "evaluator", "reuse", "credit", "hash"):
            changed = copy.deepcopy(value)
            if kind == "activation":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "evaluator":
                changed["authorization"]["evaluator_or_deepwidebench_or_sota"] = True
            elif kind == "reuse":
                changed["authorization"]["first_or_second_fresh_population_reuse"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["population_audit"]["sha256"] = "0" * 64
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_external_effect_entrypoint(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "run_official_eval_local",
            "HardTotalWallResponsesClient(",
            "acquire_deepwide_api_lease(",
            "fetch_urls(",
            ".complete(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
