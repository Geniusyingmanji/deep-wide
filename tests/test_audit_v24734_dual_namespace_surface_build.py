from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24734_dual_namespace_surface_build as target  # noqa: E402


class V24734SurfaceAuditTests(unittest.TestCase):
    def test_manifest_and_ast_are_clean(self) -> None:
        self.assertEqual(target.ast_findings(), ([], []))
        self.assertEqual(set(target._manifest()), {str(path) for path in target.SOURCES})

    def test_resealed_forward_authority_tamper_fails(self) -> None:
        value = {
            "role": "v24734_dual_namespace_surface_build_audit",
            "failure_audit_sha256": "a" * 64,
            "dependency_manifest": {"x": "b" * 64},
            "dependency_manifest_sha256": target.payload_sha256({"x": "b" * 64}),
            "tests": {"passed": True, "observed": 6, "expected": 6},
            "runtime_contract_audit": {"all_24_visible_tasks_roundtrip": True, "both_gold_denominators_parse": True, "all_unknown_evaluator_path_executes": True, "predecessor_version_or_id_absent": True},
            "label_blind_audit": {"accesses": [], "evaluator_imports": [], "passed": True},
            "source_policy": {"forbidden": False},
            "findings": [], "audit_valid": True,
            "authorization": {"one_successor_surface_publication": True, "reachability_protocol_design": True, "forward_launch": False, "evaluator_execution": False, "benchmark_dev64_or_exact220": False, "leaderboard_or_sota": False},
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        with patch.object(target, "sha256", return_value="a" * 64), patch.object(target, "_manifest", return_value={"x": "b" * 64}):
            target.validate_audit(value)
            tampered = copy.deepcopy(value); tampered["authorization"]["forward_launch"] = True; tampered.pop("audit_payload_sha256"); tampered["audit_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(RuntimeError): target.validate_audit(tampered)

    def test_successor_is_inert_before_audit(self) -> None:
        if not (ROOT / target.OUTPUT).exists():
            self.assertFalse(target.builder._authorization_valid())


if __name__ == "__main__":
    unittest.main()
