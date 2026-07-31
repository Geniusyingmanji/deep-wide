from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from deepwide_agent.v24209_search_environment import payload_sha256  # noqa: E402
from scripts.audit_v24209_search_environment import (  # noqa: E402
    OUTPUT,
    build_audit,
    publish_new,
)


class AuditV24209SearchEnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit()

    def test_current_r1_diagnostic_is_config_only_and_not_a_score(self) -> None:
        row = self.value["current_r1_config_only_diagnostic"]
        self.assertEqual(row["selected_total"], 220)
        self.assertEqual(row["provider_runtime_identity"], "anthropic-server-web-search")
        self.assertEqual(row["environment_code_file_count"], 6)
        self.assertTrue(row["one_environment_across_all_shards"])
        self.assertFalse(row["provider_index_snapshot_pinned"])
        self.assertTrue(row["not_a_fresh_candidate_or_quality_result"])

    def test_mechanism_binds_environment_and_all220_invariants(self) -> None:
        contract = self.value["mechanism_contract"]
        self.assertTrue(all(contract.values()))
        self.assertTrue(contract["all_four_shards_require_one_environment"])
        self.assertTrue(
            contract["exact220_fixed_concurrency_no_resume_failure_as_zero_revalidated"]
        )
        self.assertTrue(
            contract["future_environment_revalidation_before_executor_activation_required"]
        )

    def test_audit_grants_no_launch_or_privileged_read(self) -> None:
        for field in (
            "runtime_task_manifest_or_selected_id_file_opened",
            "benchmark_question_answer_evidence_prediction_result_or_url_read",
            "mapping_gold_category_question_type_evaluator_score_or_reward_read",
            "credential_value_read_persisted_hashed_or_emitted",
            "network_model_search_fetch_evaluator_or_api_called",
            "active_process_signal_restart_resume_rerun_skip_or_selective_retry",
            "active_benchmark_or_watcher_modified",
            "candidate_bundle_parallel_plan_or_output_root_materialized",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        ):
            self.assertFalse(self.value[field], field)
        self.assertEqual(
            self.value["audit_payload_sha256"],
            payload_sha256(
                {
                    key: item
                    for key, item in self.value.items()
                    if key != "audit_payload_sha256"
                }
            ),
        )

    def test_static_capability_boundary_and_create_exclusive_output(self) -> None:
        source = (ROOT / "scripts/audit_v24209_search_environment.py").read_text()
        tree = ast.parse(source)
        forbidden = {"requests", "httpx", "socket", "subprocess", "multiprocessing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse(
                    {alias.name.split(".")[0] for alias in node.names} & forbidden
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], forbidden)
                self.assertNotIn(
                    node.module,
                    {"urllib.request", "urllib.error", "urllib.response"},
                )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / OUTPUT.name
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(path, self.value)

    def test_control_surface_is_exact_and_sealed(self) -> None:
        surface = self.value["control_surface"]
        self.assertEqual(surface["file_count"], 4)
        self.assertEqual(
            set(surface["manifest"]),
            {
                "src/deepwide_agent/v24209_search_environment.py",
                "scripts/audit_v24209_search_environment.py",
                "tests/test_v24209_search_environment.py",
                "tests/test_audit_v24209_search_environment.py",
            },
        )
        self.assertEqual(
            surface["manifest_sha256"], payload_sha256(surface["manifest"])
        )


if __name__ == "__main__":
    unittest.main()
