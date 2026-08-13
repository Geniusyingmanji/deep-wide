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

from scripts import audit_v25363_partial_field_grounded_fact_build as target  # noqa: E402


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


class V25363PartialFieldGroundedFactBuildTests(unittest.TestCase):
    def test_fixed_hashes_closure_caps_and_semantics_are_exact(self) -> None:
        self.assertTrue(
            all(
                target.base.sha256(path) == expected
                for path, expected in target.FIXED_HASHES.items()
            )
        )
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.base.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        self.assertEqual(
            target.base.payload_sha256([row["path"] for row in vector]),
            target.EXPECTED_CLOSURE_PATH_SHA256,
        )
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(
            (target.cap.QUERY_CAP, target.cap.FETCH_CAP, target.cap.MODEL_CAP),
            (4, 14, 4),
        )

    def test_build_audit_authorizes_fresh_population_protocol_design_only(self) -> None:
        with mock.patch.object(target, "_tests", return_value=_fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        authorization = value["authorization"]
        self.assertTrue(
            authorization["fresh_disjoint_population_selection_and_protocol_design"]
        )
        self.assertFalse(authorization["network_activation_or_external_forward"])
        self.assertFalse(authorization["evaluator_or_deepwidebench_forward"])

    def test_resealed_launch_credit_hash_cap_or_estimand_tamper_fails(self) -> None:
        with mock.patch.object(
            target, "_tests", return_value=_fake_tests("b")
        ):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("launch", "credit", "hash", "cap", "estimand"):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"]["network_activation_or_external_forward"] = True
            elif kind == "credit":
                changed["paired_estimand"]["positive_signed_credit_count"] = 1
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.RUNTIME_SOURCE)] = "0" * 64
            elif kind == "cap":
                changed["physical_caps"]["model_forwards"] = 3
            else:
                changed["paired_estimand"]["candidate_additional_fact_proposal_calls"] = 1
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
