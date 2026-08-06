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

from scripts import audit_v24710_sparse_worldbank_build as audit  # noqa: E402


def valid_probe() -> dict:
    return {
        "population": "benchmark_external_synthetic",
        "synthetic_tasks": 1,
        "route_eligible_tasks": 1,
        "applied_tasks": 1,
        "official_target_value_count": 212,
        "changed_numeric_cell_count": 212,
        "adapter_bulk_callback_invocations": 1,
        "caller_supplied_archive_count": 4,
        "network_bulk_download_count": 0,
        "task_question_opaque_id_country_capital_value_prediction_or_candidate_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_benchmark_forward_evaluator_or_azure_called": False,
    }


class V24710SparseWorldBankBuildAuditTests(unittest.TestCase):
    def test_probe_gate_requires_full_denominator_and_one_change(self) -> None:
        self.assertTrue(audit.probe_valid(valid_probe()))
        for field, value in (
            ("synthetic_tasks", 2),
            ("applied_tasks", 0),
            ("official_target_value_count", 211),
            ("adapter_bulk_callback_invocations", 2),
        ):
            tampered = valid_probe()
            tampered[field] = value
            self.assertFalse(audit.probe_valid(tampered), field)

    def test_runtime_ast_and_secret_scan_are_clean(self) -> None:
        self.assertEqual(audit.ast_findings(), ([], []))
        self.assertFalse(audit.SECRET.search(audit._ordinary(audit.RUNTIME_SOURCE).read_text()))

    def test_parent_chain_is_valid(self) -> None:
        self.assertTrue(audit._parents_valid())

    def test_validate_resealed_authorization_tamper_fails(self) -> None:
        value = {
            "role": "v24710_sparse_worldbank_build_audit",
            "audit_valid": True,
            "findings": [],
            "parents": {"valid": True},
            "mechanism": {
                "synthetic_probe_valid": True,
                "synthetic_probe": valid_probe(),
            },
            "tests": {"passed": True, "observed": audit.EXPECTED_TEST_COUNT},
            "label_blind_audit": {"passed": True},
            "runtime_state": {
                "protected_watchers_unchanged": True,
                "shared_api_lease_inactive": True,
                "v247_forward_process_active": False,
            },
            "authorization": {
                "sparse_full220_forward_contract_and_protocol_design": True,
                "activation_or_forward_launch": False,
                "evaluator": False,
                "avg_at_4": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = audit.runtime.payload_sha256(value)
        audit.validate_audit(value)
        tampered = copy.deepcopy(value)
        tampered["authorization"]["activation_or_forward_launch"] = True
        tampered.pop("audit_payload_sha256")
        tampered["audit_payload_sha256"] = audit.runtime.payload_sha256(tampered)
        with self.assertRaisesRegex(RuntimeError, "drifted"):
            audit.validate_audit(tampered)

    def test_build_failure_keeps_launch_unauthorized(self) -> None:
        fake_git = lambda *args: "a" * 40 if args[0] == "rev-parse" else ""
        with (
            patch.object(audit, "_git", side_effect=fake_git),
            patch.object(audit, "_tracked", return_value=True),
            patch.object(audit, "_parents_valid", return_value=True),
            patch.object(
                audit,
                "_run_tests",
                return_value=(True, audit.EXPECTED_TEST_COUNT),
            ),
            patch.object(audit, "ast_findings", return_value=([], [])),
            patch.object(audit, "_watcher", return_value=True),
            patch.object(audit, "_lease_inactive", return_value=True),
            patch.object(audit, "_active", return_value=False),
        ):
            value = audit.build_audit(now=0, probe_fn=lambda: {"probe_failed": True})
        self.assertFalse(value["audit_valid"])
        self.assertIn("synthetic_mechanism_probe_failed", value["findings"])
        self.assertFalse(
            value["authorization"]["sparse_full220_forward_contract_and_protocol_design"]
        )
        self.assertFalse(value["authorization"]["activation_or_forward_launch"])


if __name__ == "__main__":
    unittest.main()
