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

from scripts import audit_v25291_monotone_unknown_fill_build as target  # noqa: E402


REAL_GIT = target.base._git


class V25291MonotoneUnknownFillBuildAuditTests(unittest.TestCase):
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
            return target.V25290_COMMIT
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    def _audit(self) -> dict:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            return target.build_audit(now=1, tracked=False)

    def test_fixed_parent_sources_commit_and_dependency_closure_are_exact(self) -> None:
        self.assertEqual(
            target._fixed_parents(),
            {str(path): digest for path, digest in target.FIXED_PARENTS.items()},
        )
        self.assertEqual(
            target._fixed_sources(),
            {str(path): digest for path, digest in target.FIXED_SOURCES.items()},
        )
        self.assertTrue(target._parent_barrier())
        self.assertEqual(
            target._changed_paths(target.V25290_COMMIT),
            target.V25290_COMMIT_PATHS,
        )
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.seal.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        self.assertEqual(
            target.seal.payload_sha256([row["path"] for row in vector]),
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

    def test_runtime_invariants_and_parent_caps_are_exact(self) -> None:
        self.assertTrue(all(target._source_invariants().values()))
        self.assertEqual(target.legacy_contract.LIMITS["search_queries"], 4)
        self.assertEqual(target.legacy_contract.LIMITS["fetch_targets"], 10)
        self.assertEqual(target.legacy_contract.LIMITS["model_calls"], 3)
        self.assertEqual(target.legacy_contract.LIMITS["wall_seconds"], 240)

    def test_build_audit_authorizes_fresh_protocol_design_only(self) -> None:
        value = self._audit()
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        authorization = value["authorization"]
        self.assertTrue(
            authorization[
                "fresh_disjoint_shared_prefix_external_population_and_protocol_design"
            ]
        )
        self.assertFalse(authorization["external_activation_or_launch"])
        self.assertFalse(authorization["postfreeze_evaluator"])
        self.assertFalse(
            authorization["deepwidebench_dev64_exact220_forward_or_evaluator"]
        )
        self.assertTrue(target._watchers_exact(value["protected_watchers"]))

    def test_resealed_source_protocol_launch_credit_nested_or_check_tamper_fails(self) -> None:
        value = self._audit()
        for kind in (
            "source",
            "protocol",
            "launch",
            "credit",
            "suite_hidden",
            "watcher_hidden",
            "dependency_hidden",
            "invariant_hidden",
            "check_hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "source":
                changed["fixed_sources"][str(target.INTEGRATION)] = "0" * 64
            elif kind == "protocol":
                changed["future_protocol_requirements"][
                    "direct_deepwidebench_220_after_build"
                ] = True
            elif kind == "launch":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            elif kind == "suite_hidden":
                changed["tests"]["suites"][0]["hidden"] = True
            elif kind == "watcher_hidden":
                changed["protected_watchers"]["795336"]["hidden"] = True
            elif kind == "dependency_hidden":
                changed["runtime_dependency_vector"][0]["hidden"] = True
            elif kind == "invariant_hidden":
                changed["runtime_invariants"]["hidden"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.seal.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_does_not_call_network_model_search_or_evaluator(self) -> None:
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
