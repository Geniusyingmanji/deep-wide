from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25067_quote_verified_build as target  # noqa: E402


class V25067QuoteVerifiedBuildAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        closure = target._dependency_closure(
            (target.BINDING_SOURCE, target.RUNTIME_SOURCE)
        )
        cls.closure = closure
        cls.semantic = target._semantic_findings(closure)

    def test_dependency_closure_contains_candidate_and_injected_parents(self) -> None:
        self.assertIn(target.BINDING_SOURCE, self.closure)
        self.assertIn(target.RUNTIME_SOURCE, self.closure)
        self.assertIn(
            Path("src/deepwide_agent/v24996_shared_first_wave_paired_runtime.py"),
            self.closure,
        )
        self.assertIn(Path("src/deepwide_agent/clients.py"), self.closure)

    def test_semantic_findings_and_direct_capabilities_are_empty(self) -> None:
        self.assertEqual(self.semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(self.semantic["evaluator_capabilities"], [])
        self.assertEqual(self.semantic["credential_literal_hits"], [])
        self.assertEqual(target._direct_forbidden_imports(target.BINDING_SOURCE), [])
        self.assertEqual(target._direct_forbidden_imports(target.RUNTIME_SOURCE), [])

    def test_parent_hashes_and_authority_are_build_design_only(self) -> None:
        self.assertEqual(target._parent_barrier(), target.EXPECTED_PARENT_HASHES)

    def synthetic_audit(self) -> dict:
        tests = {
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
                    "output_sha256": "0" * 64,
                }
                for pattern, expected in target.TEST_SUITES
            ],
        }
        watchers = {
            str(pid): {
                "present": True,
                "start_ticks": ticks,
                "matches_frozen_identity": True,
            }
            for pid, ticks in target.PROTECTED_WATCHERS.items()
        }
        with mock.patch.object(target, "_git") as git, mock.patch.object(
            target, "_tests", return_value=tests
        ), mock.patch.object(target, "_tracked", return_value=True), mock.patch.object(
            target, "_watchers", return_value=watchers
        ), mock.patch.object(target, "_lease_inactive", return_value=True):
            git.side_effect = lambda *args: (
                "frozen-head"
                if args in (("rev-parse", "HEAD"), ("rev-parse", "target/main"))
                else ""
            )
            return target.build_audit(now=1, tracked=True)

    def test_clean_synthetic_audit_authorizes_only_protocol_design(self) -> None:
        value = self.synthetic_audit()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["authorization"]["fresh_external_protocol_design"])
        self.assertFalse(
            value["authorization"]["fresh_external_protocol_publication"]
        )
        self.assertFalse(
            value["authorization"]["fresh_external_activation_or_launch"]
        )
        self.assertFalse(value["authorization"]["paired_dev_or_public_exact220"])

    def test_resealed_launch_watcher_or_credit_tamper_fails(self) -> None:
        for mutation in ("launch", "watcher", "finding", "effect"):
            changed = copy.deepcopy(self.synthetic_audit())
            if mutation == "launch":
                changed["authorization"]["fresh_external_activation_or_launch"] = True
            elif mutation == "watcher":
                changed["runtime_state"]["protected_watchers"]["795336"][
                    "matches_frozen_identity"
                ] = False
            elif mutation == "finding":
                changed["findings"] = ["tampered"]
            else:
                changed["network_model_search_fetch_evaluator_benchmark_or_api_called"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_publication_is_create_exclusive(self) -> None:
        value = self.synthetic_audit()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audit.json"
            target.publish_exclusive(path, value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, value)


if __name__ == "__main__":
    unittest.main()
