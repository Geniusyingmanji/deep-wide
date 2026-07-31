from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from deepwide_agent.v24200_successor import payload_sha256
from scripts.audit_v24205_markdown_rebase_feasibility import (
    OUTPUT,
    build_audit,
    publish_new,
)


class AuditV24205MarkdownRebaseFeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit()

    def test_real_audit_separates_hook_feasibility_from_publication(self) -> None:
        value = self.value
        conclusion = value["conclusion"]
        self.assertTrue(conclusion["p12_schema69_schema70_bytes_repo_local_and_exact"])
        self.assertTrue(conclusion["schema76_schema77_markdown_production_hooks_compatible"])
        self.assertTrue(
            conclusion["schema76_schema77_mainline_scope_hook_already_active_once"]
        )
        self.assertTrue(
            conclusion["branch_scope_must_not_reapply_historical_v24104_patch"]
        )
        self.assertTrue(conclusion["branch_scope_namespace_alias_semantics_still_unpublished"])
        self.assertFalse(conclusion["selected_package_publication_available"])
        for field in (
            "live_status_or_decision_receipt_read",
            "runtime_task_state_prediction_or_result_read",
            "benchmark_question_answer_evidence_or_url_read",
            "mapping_gold_category_question_type_evaluator_score_or_reward_read",
            "credential_value_read_persisted_hashed_or_emitted",
            "network_model_search_fetch_evaluator_or_api_called",
            "candidate_tree_or_package_materialized",
            "component_implementation_authority_granted",
            "package_gate_evaluated_or_launched",
            "shared_api_lease_acquired",
            "process_signal_restart_resume_rerun_skip_or_selective_retry",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        ):
            self.assertFalse(value[field], field)

    def test_mainline_rebase_preserves_one_scope_hook_and_audit_rejects_duplicate(
        self,
    ) -> None:
        for row in self.value["mainline_hook_audit"].values():
            self.assertTrue(row["production_hook_compatibility"])
            self.assertTrue(row["mainline_scope_hook_preserved_exactly_once"])
            self.assertTrue(row["historical_branch_scope_patch_mechanically_succeeds"])
            self.assertTrue(
                row[
                    "historical_branch_scope_patch_reapplication_rejected_by_audit"
                ]
            )
            self.assertTrue(row["branch_scope_requires_zero_byte_namespace_alias_design"])
            self.assertFalse(row["tests_version_guards_rebased"])
            self.assertFalse(row["candidate_or_publication_built"])
            self.assertEqual(row["after_hook_counts"]["markdown_import"], 1)
            self.assertEqual(row["after_hook_counts"]["scope_import"], 1)
            self.assertEqual(row["after_hook_counts"]["scope_fallback_call"], 1)
            duplicate = row["historical_branch_scope_patch_duplicate_hook_counts"]
            self.assertEqual(duplicate["scope_import"], 2)
            self.assertEqual(duplicate["scope_fallback_call"], 2)
            self.assertEqual(duplicate["scope_audit_write"], 2)

    def test_audit_seal_and_create_exclusive_publish(self) -> None:
        unsigned = dict(self.value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / OUTPUT.name
            publish_new(path, self.value)
            with self.assertRaises(FileExistsError):
                publish_new(path, self.value)

    def test_audit_source_has_no_network_process_environment_or_dynamic_code(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24205_markdown_rebase_feasibility.py"
        ).read_text()
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
                self.assertFalse(
                    {alias.name.split(".")[0] for alias in node.names}
                    & forbidden_imports
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], forbidden_imports)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"eval", "exec", "compile", "open"})
        self.assertNotIn("os.environ", source)
        self.assertNotIn("/proc", source)


if __name__ == "__main__":
    unittest.main()
