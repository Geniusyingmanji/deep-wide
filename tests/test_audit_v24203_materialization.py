from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from scripts.audit_v24203_materialization import (
    OUTPUT,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24203MaterializationTests(unittest.TestCase):
    def test_real_audit_binds_frozen_inputs_and_grants_no_execution(self) -> None:
        value = build_audit(created_at_unix=1)
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertEqual(value["role"], "v24203_successor_materialization_audit")
        self.assertTrue(value["label_blind"])
        self.assertEqual(value["identity_handoff_decision_count"], 3)
        self.assertEqual(value["blocked_nonempty_package_decision_count"], 33)
        self.assertFalse(value["any_nonempty_package_materializable_now"])
        for field in (
            "decision_receipt_or_live_status_envelope_read",
            "runtime_task_state_prediction_or_result_read",
            "benchmark_question_answer_evidence_or_url_read",
            "mapping_gold_category_question_type_evaluator_score_or_reward_read",
            "credential_value_read_persisted_hashed_or_emitted",
            "network_model_search_fetch_evaluator_or_api_called",
            "candidate_tree_or_package_materialized",
            "package_gate_evaluated_or_launched",
            "shared_api_lease_acquired",
            "process_signal_restart_resume_rerun_skip_or_selective_retry",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        ):
            self.assertFalse(value[field], field)

    def test_component_sources_preserve_authority_boundaries(self) -> None:
        value = build_audit(created_at_unix=1)
        sources = value["component_sources"]
        self.assertFalse(
            sources["search_yield_shared_query"]["historical_publication_available"]
        )
        self.assertFalse(
            sources["entropy_credit_controller"]["controller_implementation_authority_available"]
        )
        self.assertTrue(
            sources["markdown_rank_slot"]["historical_publication_available"]
        )
        self.assertFalse(
            sources["markdown_rank_slot"]["selected_baseline_rebase_publication_available"]
        )
        self.assertTrue(
            sources["markdown_branch_scope_open_fallback"][
                "mainline_scope_and_markdown_branch_scope_must_remain_namespaced"
            ]
        )

    def test_audit_source_has_no_network_process_environment_or_dynamic_code(self) -> None:
        source = (Path(__file__).parents[1] / "scripts/audit_v24203_materialization.py").read_text()
        tree = ast.parse(source)
        forbidden_imports = {
            "requests",
            "urllib",
            "httpx",
            "socket",
            "subprocess",
            "multiprocessing",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse({alias.name.split(".")[0] for alias in node.names} & forbidden_imports)
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], forbidden_imports)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"eval", "exec", "compile", "open"})
        self.assertNotIn("os.environ", source)
        self.assertNotIn("/proc", source)

    def test_publish_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / OUTPUT.name
            value = {"x": 1}
            publish_new(path, value)
            with self.assertRaises(FileExistsError):
                publish_new(path, value)


if __name__ == "__main__":
    unittest.main()
