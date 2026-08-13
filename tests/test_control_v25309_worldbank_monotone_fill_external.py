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

from deepwide_agent import v25309_worldbank_monotone_fill_external_contract as contract  # noqa: E402
from scripts import control_v25309_worldbank_monotone_fill_external as target  # noqa: E402


class V25309WorldBankMonotoneFillControlTests(unittest.TestCase):
    def test_dependency_closure_and_semantic_scan_are_exact(self) -> None:
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(contract.payload_sha256(vector), target.EXPECTED_CLOSURE_VECTOR_SHA256)
        self.assertEqual(
            contract.payload_sha256([row["path"] for row in vector]),
            target.EXPECTED_CLOSURE_PATH_SHA256,
        )

    def test_fixed_parents_and_frozen_population_validate(self) -> None:
        self.assertTrue(target._parent_barrier())
        self.assertTrue(
            all(target.audit.sha256(path) == digest for path, digest in target.FIXED_PARENTS.items())
        )
        self.assertEqual(len(contract.task_vector(ROOT)), 12)
        self.assertEqual(len(contract.page_vector(ROOT)), 8)

    def test_protocol_roundtrip_binds_manifest_and_gate(self) -> None:
        _closure, vector = target._closure()
        protocol = contract.build_protocol(
            source_manifest=target._source_manifest(vector), now=1
        )
        self.assertEqual(contract.validate_protocol(ROOT, protocol), protocol)
        self.assertEqual(protocol["mechanism_gate"], contract.mechanism_gate())
        changed = copy.deepcopy(protocol)
        changed["mechanism_gate"]["minimum_supported_unknown_fill_tasks"] = 1
        changed.pop("protocol_payload_sha256")
        changed["protocol_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            contract.validate_protocol(ROOT, changed)

    def test_audit_roundtrip_with_mocked_runtime_state(self) -> None:
        # Exercise the full audit schema without performing test subprocesses.
        suites = [
            {
                "pattern": pattern, "expected": expected, "observed": expected,
                "returncode": 0, "passed": True, "output_sha256": "a" * 64,
            }
            for pattern, expected in target.TEST_SUITES
        ]
        tests = {
            "expected": target.EXPECTED_TESTS, "observed": target.EXPECTED_TESTS,
            "passed": True, "suites": suites,
        }
        with mock.patch.object(target, "_tests", return_value=tests), mock.patch.object(
            target, "_future_pristine", return_value=True
        ), mock.patch.object(target, "_lease_inactive", return_value=True), mock.patch.object(
            target, "_endpoint_reachable", return_value=True
        ), mock.patch.object(target.runner, "_active_conflicts", return_value=[]):
            value = target.build_audit(now=1, tracked=False)
        # tracked=False intentionally permits untracked control/test sources but does not
        # make a publishable audit valid; all other evidence remains explicit.
        self.assertEqual(value["role"], target.ROLE)
        self.assertFalse(value["network_model_search_fetch_evaluator_benchmark_or_api_called"])
        self.assertFalse(value["authorization"]["external_forward"])

    def test_build_protocol_requires_valid_audit(self) -> None:
        with mock.patch.object(target, "validate_audit", side_effect=ValueError("bad")):
            with self.assertRaises(ValueError):
                target.build_protocol({})


if __name__ == "__main__":
    unittest.main()
