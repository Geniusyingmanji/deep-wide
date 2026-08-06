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

from scripts import audit_v24731_dual_namespace_surface_build as target  # noqa: E402


class V24731SurfaceBuildAuditTests(unittest.TestCase):
    def test_ast_scan_and_manifest_are_clean(self) -> None:
        accesses, imports = target.ast_findings()
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        manifest = target._manifest()
        self.assertEqual(set(manifest), {str(path) for path in target.SOURCES})

    def test_resealed_authorization_tamper_fails_closed(self) -> None:
        value = {
            "role": "v24731_dual_namespace_surface_build_audit",
            "population_design_sha256": "a" * 64,
            "dependency_manifest": {"x": "b" * 64},
            "dependency_manifest_sha256": target.payload_sha256({"x": "b" * 64}),
            "tests": {"passed": True, "observed": 5, "expected": 5},
            "label_blind_audit": {"accesses": [], "evaluator_imports": [], "passed": True},
            "source_policy": {"forbidden": False},
            "findings": [],
            "audit_valid": True,
            "authorization": {
                "one_surface_publication": True,
                "reachability_protocol_design": True,
                "forward_launch": False,
                "evaluator_execution": False,
                "benchmark_dev64_or_exact220": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        with (
            patch.object(target, "sha256", return_value="a" * 64),
            patch.object(target, "_manifest", return_value={"x": "b" * 64}),
        ):
            target.validate_audit(value)
            tampered = copy.deepcopy(value)
            tampered["authorization"]["forward_launch"] = True
            tampered.pop("audit_payload_sha256")
            tampered["audit_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_audit(tampered)

    def test_surface_publication_is_not_forward_authority(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 5)
        self.assertNotIn(target.builder.CONTRACT, target.SOURCES)
        self.assertFalse((ROOT / target.builder.CONTRACT).exists())


if __name__ == "__main__":
    unittest.main()
