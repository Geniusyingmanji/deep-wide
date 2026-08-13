from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25325_low_concurrency_worldbank_population_preactivation as target  # noqa: E402


REAL_GIT = target.base._git


class V25325LowConcurrencyWorldBankPopulationPreactivationTests(unittest.TestCase):
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
            return target.HARDENING_COMMITS[-1][0]
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    def _audit(self) -> dict:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()), mock.patch.object(
            target, "_future_pristine", return_value=True
        ), mock.patch.object(target, "_active_conflicts", return_value=[]):
            return target.build_audit(now=1, tracked=False)

    def test_fixed_build_commit_closure_and_semantics_are_exact(self) -> None:
        self.assertTrue(target._build_barrier())
        self.assertEqual(
            {str(path): target.base.sha256(path) for path in target.FIXED},
            {str(path): digest for path, digest in target.FIXED.items()},
        )
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.runner.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_source_invariants_bind_claim_lease_all48_and_concurrency6(self) -> None:
        value = target._source_invariants()
        self.assertTrue(all(value.values()))
        self.assertTrue(value["target_concurrency_exact6"])

    def test_preactivation_authorizes_only_execution_start_generation(self) -> None:
        value = self._audit()
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["execution_start_generation"])
        self.assertFalse(
            value["authorization"]["single_low_concurrency_population_freeze"]
        )
        self.assertFalse(value["authorization"]["external_forward_or_evaluator"])

    def test_execution_start_roundtrip_binds_parent_and_single_authority(self) -> None:
        audit = self._audit()
        parent = "c" * 40

        def lifecycle_git(*args: str) -> str:
            if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
                return parent
            if args == ("status", "--porcelain"):
                return ""
            if args == ("rev-parse", f"{parent}^"):
                return audit["git"]["head"]
            if args == (
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                parent,
            ):
                return str(target.runner.PREACTIVATION)
            return REAL_GIT(*args)

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            fake = Path(directory) / "preactivation.json"
            fake.write_text("{}\n", encoding="utf-8")
            with mock.patch.object(
                target.base, "_git", side_effect=lifecycle_git
            ), mock.patch.object(
                target.runner, "PREACTIVATION", fake.relative_to(ROOT)
            ), mock.patch.object(
                target.runner, "_preactivation_authority", return_value=True
            ):
                value = target.build_execution_start(audit, now=1)
        self.assertEqual(value["transport_contract"]["target_concurrency"], 6)
        self.assertEqual(value["consumed_manifest_contract"]["response_count"], 84)
        self.assertEqual(
            value["authorization"],
            {
                "single_low_concurrency_population_freeze": True,
                "external_forward_or_evaluator": False,
                "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            },
        )

    def test_resealed_nested_or_authority_tamper_fails_closed(self) -> None:
        value = self._audit()
        for kind in ("source", "closure", "manifest", "conflict", "launch", "credit", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "source":
                changed["source_manifest"][str(target.runner.SOURCE)] = "0" * 64
            elif kind == "closure":
                changed["runtime_dependency_vector"][0]["sha256"] = "0" * 64
            elif kind == "manifest":
                changed["consumed_manifest_contract"]["response_count"] = 83
            elif kind == "conflict":
                changed["active_conflicts"] = [123]
            elif kind == "launch":
                changed["authorization"]["single_low_concurrency_population_freeze"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.runner.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_future_surfaces_and_runtime_state_are_currently_safe(self) -> None:
        self.assertTrue(target._future_pristine())
        self.assertEqual(target._active_conflicts(), [])
        self.assertTrue(target.base._lease_inactive())

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
