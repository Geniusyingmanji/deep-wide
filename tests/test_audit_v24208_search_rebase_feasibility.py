from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from deepwide_agent.v24200_successor import payload_sha256
from scripts.audit_v24208_search_rebase_feasibility import (
    OUTPUT,
    RUNTIME_MODULE,
    RUNTIME_TEST,
    build_audit,
    patch_search_production,
    publish_new,
)
from scripts.replay_v24201_repo_local_candidate_dag import build_replay


class AuditV24208SearchRebaseFeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit()

    def test_six_parent_variants_have_one_exact_delta(self) -> None:
        rows = self.value["rebase_feasibility"]
        self.assertEqual(len(rows), 6)
        self.assertEqual(
            {row["baseline_name"] for row in rows.values()},
            {"p12", "schema76", "schema77"},
        )
        self.assertEqual(
            {row["parent_variant"] for row in rows.values()},
            {"selected_baseline", "selected_markdown_candidate"},
        )
        expected = {
            "src/deepwide_agent/runtime.py",
            "scripts/preflight_deepwide.py",
            RUNTIME_MODULE,
            RUNTIME_TEST,
        }
        for row in rows.values():
            self.assertEqual(set(row["delta_files"]), expected)
            self.assertEqual(
                row["feasibility_regular_file_count"],
                row["parent_regular_file_count"] + 2,
            )
            self.assertFalse(row["candidate_or_publication_materialized"])

    def test_audit_grants_no_publication_or_execution(self) -> None:
        conclusion = self.value["conclusion"]
        self.assertTrue(
            conclusion["six_selected_parent_variants_rebase_deterministically"]
        )
        self.assertTrue(conclusion["same_query_budget_and_no_new_api_budget"])
        self.assertTrue(
            conclusion["v24180_quality_go_still_required_before_publication"]
        )
        self.assertFalse(
            conclusion["selected_search_component_publication_available"]
        )
        for field in (
            "live_status_gate_result_or_decision_receipt_read",
            "runtime_task_state_prediction_or_result_read",
            "benchmark_question_answer_evidence_or_url_read",
            "mapping_gold_category_question_type_evaluator_score_or_reward_read",
            "credential_value_read_persisted_hashed_or_emitted",
            "network_model_search_fetch_evaluator_or_api_called",
            "candidate_tree_or_package_materialized",
            "component_publication_or_implementation_authority_granted",
            "package_gate_evaluated_or_launched",
            "shared_api_lease_acquired",
            "process_signal_restart_resume_rerun_skip_or_selective_retry",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        ):
            self.assertFalse(self.value[field], field)

    def test_patch_is_deterministic_and_refuses_double_application(self) -> None:
        _value, maps = build_replay()
        first = patch_search_production(maps["schema76"], target_schema=82)
        second = patch_search_production(maps["schema76"], target_schema=82)
        self.assertEqual(first, second)
        with self.assertRaisesRegex(RuntimeError, "expected one"):
            patch_search_production(first, target_schema=86)

    def test_seal_create_exclusive_and_static_capability_boundary(self) -> None:
        unsigned = dict(self.value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / OUTPUT.name
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(path, self.value)

        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24208_search_rebase_feasibility.py"
        ).read_text()
        tree = ast.parse(source)
        forbidden_imports = {
            "requests", "urllib", "httpx", "socket", "subprocess", "multiprocessing"
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
