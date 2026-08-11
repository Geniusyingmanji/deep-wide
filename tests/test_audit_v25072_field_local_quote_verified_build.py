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

from scripts import audit_v25072_field_local_quote_verified_build as target  # noqa: E402


class V25072BuildAuditTests(unittest.TestCase):
    def test_dependency_closure_contains_new_components(self) -> None:
        closure = target._dependency_closure((target.BINDING_SOURCE, target.RUNTIME_SOURCE))
        self.assertIn(target.BINDING_SOURCE, closure)
        self.assertIn(target.RUNTIME_SOURCE, closure)
        self.assertIn(Path("src/deepwide_agent/v25065_quote_verified_record_binding.py"), closure)

    def test_direct_components_have_no_effect_imports(self) -> None:
        self.assertEqual(target._direct_forbidden_imports(target.BINDING_SOURCE), [])
        self.assertEqual(target._direct_forbidden_imports(target.RUNTIME_SOURCE), [])

    def test_parent_barrier_is_frozen_content_free_diagnosis(self) -> None:
        observed = target._parent_barrier()
        self.assertEqual(observed, target.sha256(target.PARENT_DIAGNOSIS))

    def test_resealed_authorization_tamper_fails(self) -> None:
        with mock.patch.object(target, "_git", side_effect=lambda *args: "same" if args[:2] == ("rev-parse", "HEAD") or args[:2] == ("rev-parse", "target/main") else ""), mock.patch.object(
            target, "_tracked", return_value=True
        ), mock.patch.object(target, "_tests", return_value={"expected": target.EXPECTED_TESTS, "observed": target.EXPECTED_TESTS, "passed": True, "suites": []}), mock.patch.object(
            target, "_semantic_findings", return_value={"privileged_runtime_field_accesses": [], "evaluator_capabilities": [], "credential_literal_hits": [], "allowed_provider_rank_access": []}
        ), mock.patch.object(target, "_watchers", return_value={str(pid): {"matches_frozen_identity": True} for pid in target.PROTECTED_WATCHERS}), mock.patch.object(
            target, "_lease_inactive", return_value=True
        ):
            value = target.build_audit(now=1, tracked=False)
        changed = copy.deepcopy(value)
        changed["authorization"]["evaluator_or_leaderboard_or_sota"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
