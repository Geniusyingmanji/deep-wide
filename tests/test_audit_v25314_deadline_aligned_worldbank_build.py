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

from scripts import audit_v25314_deadline_aligned_worldbank_build as target  # noqa: E402


REAL_GIT = target.base._git


class V25314DeadlineAlignedWorldBankBuildAuditTests(unittest.TestCase):
    @staticmethod
    def _fake_tests() -> dict:
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
                    "output_sha256": "a" * 64,
                }
                for pattern, expected in target.TEST_SUITES
            ],
        }

    @staticmethod
    def _clean_git(*args: str) -> str:
        if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
            return target.IMPLEMENTATION_COMMIT
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    def _audit(self) -> dict:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            return target.build_audit(now=1, tracked=False)

    def test_fixed_diagnosis_sources_commit_and_closure_are_exact(self) -> None:
        self.assertTrue(target._diagnosis_barrier())
        self.assertEqual(
            {str(path): target.base.sha256(path) for path in target.FIXED},
            {str(path): digest for path, digest in target.FIXED.items()},
        )
        self.assertEqual(
            target._changed_paths(target.IMPLEMENTATION_COMMIT),
            target.IMPLEMENTATION_PATHS,
        )
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.runtime.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        self.assertEqual(
            target.runtime.payload_sha256([row["path"] for row in vector]),
            target.EXPECTED_CLOSURE_PATH_SHA256,
        )

    def test_closure_is_label_blind_without_evaluator_or_credentials(self) -> None:
        closure, _vector = target._closure()
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(
            semantic["allowed_provider_rank_access"],
            ["src/deepwide_agent/clients.py:565:score"],
        )

    def test_deadline_parity_witness_is_true_and_effect_free(self) -> None:
        self.assertEqual(target._deadline_parity_witness(), target._expected_witness())

    def test_source_invariants_and_parent_caps_are_exact(self) -> None:
        self.assertTrue(all(target._source_invariants().values()))
        self.assertEqual(target.runtime.PARENT_LIMITS["search_queries"], 4)
        self.assertEqual(target.runtime.PARENT_LIMITS["fetch_targets"], 10)
        self.assertEqual(target.runtime.PARENT_LIMITS["model_calls"], 3)
        self.assertEqual(target.runtime.PARENT_LIMITS["wall_seconds"], 240)

    def test_build_audit_authorizes_only_fresh_population_design(self) -> None:
        value = self._audit()
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        authorization = value["authorization"]
        self.assertTrue(
            authorization["fresh_disjoint_worldbank_population_and_protocol_design"]
        )
        self.assertFalse(authorization["external_activation_or_launch"])
        self.assertFalse(authorization["postfreeze_evaluator"])
        self.assertFalse(
            authorization["deepwidebench_dev64_exact220_forward_or_evaluator"]
        )

    def test_resealed_nested_tamper_fails_closed(self) -> None:
        value = self._audit()
        for kind in (
            "diagnosis",
            "commit",
            "deadline",
            "population",
            "launch",
            "credit",
            "dependency",
            "check",
        ):
            changed = copy.deepcopy(value)
            if kind == "diagnosis":
                changed["fixed_inputs"][str(target.PARENT_DIAGNOSIS)] = "0" * 64
            elif kind == "commit":
                changed["implementation_commit"]["commit"] = "0" * 40
            elif kind == "deadline":
                changed["deadline_parity_witness"]["aligned_deadlines"] = False
            elif kind == "population":
                changed["future_protocol_requirements"][
                    "reuse_old_target_entity_page_response_or_prediction"
                ] = True
            elif kind == "launch":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "dependency":
                changed["runtime_dependency_vector"][0]["sha256"] = "0" * 64
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.runtime.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_live_provider_or_evaluator_constructor(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "HardTotalWallResponsesClient(",
            "AzureNativeSearchClient(",
            "requests.",
            "urlopen(",
            "run_official_eval_local",
            ".complete(system",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
