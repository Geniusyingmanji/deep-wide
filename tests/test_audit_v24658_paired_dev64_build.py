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

from scripts import audit_v24658_paired_dev64_build as audit  # noqa: E402


class V24658BuildAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "a" * 40,
        remote: str = "a" * 40,
        clean: bool = True,
        fields: list[str] | None = None,
        imports: list[str] | None = None,
        finalizer_findings: list[str] | None = None,
        lease_active: bool = False,
    ) -> dict:
        expected_watchers = [
            {"pid": 795336, "marker": audit.PROTECTED_WATCHERS[0][1], "start_ticks": 713986317},
            {"pid": 3061652, "marker": audit.PROTECTED_WATCHERS[1][1], "start_ticks": 747569004},
        ]
        tests = iter((True, count) for _path, count, _timeout in audit.TEST_SUITES)
        with patch.object(audit, "_ordinary", side_effect=lambda path: ROOT / path), patch.object(
            audit, "sha256", return_value="b" * 64
        ), patch.object(audit, "_run_test", side_effect=lambda *_args: next(tests)), patch.object(
            audit, "_git", side_effect=[head, remote, "" if clean else " M plan.md"]
        ), patch.object(audit, "_tracked", return_value=True), patch.object(
            audit.control, "_field_accesses", return_value=list(fields or [])
        ), patch.object(
            audit.control, "_import_hits", return_value=list(imports or [])
        ), patch.object(
            audit, "_finalizer_findings", return_value=list(finalizer_findings or [])
        ), patch.object(audit, "_implementation_valid", return_value=True), patch.object(
            audit, "protected_watcher_snapshot", return_value=expected_watchers
        ), patch.object(
            audit, "lease_observation", return_value={"active": lease_active}
        ), patch.object(audit, "SECRET", audit.re.compile(r"a^")):
            return audit.build_audit(now=0)

    def test_source_and_test_counts_are_frozen(self) -> None:
        self.assertEqual(len(audit.SOURCES), audit.EXPECTED_SOURCES)
        self.assertEqual(
            sum(count for _path, count, _timeout in audit.TEST_SUITES),
            audit.EXPECTED_TEST_COUNT,
        )

    def test_synthetic_go_authorizes_design_only(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["authorization"]["protocol_design"])
        self.assertFalse(value["authorization"]["activation_or_forward_launch"])
        self.assertFalse(value["authorization"]["evaluator_access"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_dirty_or_unpushed_fails_closed(self) -> None:
        dirty = self.synthetic(clean=False)
        unpushed = self.synthetic(remote="c" * 40)
        self.assertIn("v24658_source_worktree_not_clean", dirty["findings"])
        self.assertIn("v24658_source_commit_not_pushed", unpushed["findings"])

    def test_privileged_access_or_evaluator_import_fails_closed(self) -> None:
        fields = self.synthetic(fields=["runtime.py:1:gold"])
        imports = self.synthetic(imports=["runtime.py:evaluator"])
        self.assertIn("privileged_forward_field_access", fields["findings"])
        self.assertIn("evaluator_import_in_forward_surface", imports["findings"])

    def test_finalizer_validator_or_live_lease_drift_fails_closed(self) -> None:
        validator = self.synthetic(finalizer_findings=["missing:validate_postaudit"])
        lease = self.synthetic(lease_active=True)
        self.assertIn(
            "finalizer_freeze_or_observation_validator_drifted",
            validator["findings"],
        )
        self.assertIn("shared_api_lease_active", lease["findings"])

    def test_resealed_launch_authorization_tamper_fails_closed(self) -> None:
        value = self.synthetic()
        tampered = copy.deepcopy(value)
        tampered["authorization"]["activation_or_forward_launch"] = True
        tampered.pop("audit_payload_sha256")
        tampered["audit_payload_sha256"] = audit.payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(tampered)

    def test_finalizer_ast_rejects_hardcoded_false_lease(self) -> None:
        source = """
def validate_evaluator_gate(): pass
def validate_evaluator_start(): pass
def validate_final_result(): pass
def validate_postaudit(): pass
def build_postaudit():
    return {\"shared_api_lease_active\": False}
"""
        with patch.object(
            audit.Path, "read_text", return_value=source
        ):
            self.assertIn(
                "postaudit_shared_lease_hardcoded_false",
                audit._finalizer_findings(),
            )


if __name__ == "__main__":
    unittest.main()
