from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24529_alias_seeded_target_acquisition import (  # noqa: E402
    AliasSeededTargetAcquisition,
)
from deepwide_agent.v24530_alias_seeded_bounded_worker import (  # noqa: E402
    budget_vector_seconds,
    run_alias_seeded_worker,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24524_alias_title_integration import TASK, clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24530-test-validator-manifest").hexdigest()


class V24530AliasSeededBoundedWorkerTests(unittest.TestCase):
    def test_real_worker_executes_alias_policy_and_preserves_proof_surface(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary)
            directory = root / "task"
            checkpoint = root / "checkpoint"
            fixture = root / "fixture"
            directory.mkdir()
            checkpoint.mkdir()
            fixture.mkdir()
            clock = AdvancingClock()
            model, search = clients(fixture, clock, mode="support")
            with patch(
                "deepwide_agent.v24469_bounded_worker_supervisor.bind_worker_to_parent"
            ):
                result = run_alias_seeded_worker(
                    TASK,
                    ordinal=1,
                    expected_supervisor_pid=os.getpid(),
                    checkpoint_directory=checkpoint,
                    output_root=root,
                    directory=directory,
                    model_factory=lambda _callback: model,
                    search_factory=lambda _callback: search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                    expected_model_cap=2,
                    writer=lambda name, value: _new_json(directory / name, value),
                    validator_manifest_sha256=MANIFEST,
                )
        self.assertGreater(result["alias_title_receipt"]["decision_credit_gain_nats"], 0)
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.request_invocations, 4)
        self.assertEqual(search.fetch_invocations, 5)

    def test_missing_acquisition_activity_fails_closed(self) -> None:
        fake = {
            "policy_id": "v24529_visible_row_alias_seeded_target_acquisition_v1",
            "binding_count": 3,
            "targeted_query_vector_calls": 0,
            "discovery_query_vector_calls": 0,
            "lead_selection_calls": 0,
            "alias_seeded_query_vector_calls": 0,
            "row_without_safe_alias_query_vector_calls": 0,
            "visible_lead_count": 0,
            "alias_title_hit_lead_count": 0,
            "selected_lead_count": 0,
            "selected_alias_title_hit_lead_count": 0,
            "logical_queries_per_plan_unchanged": True,
            "search_batches_per_plan_unchanged": True,
            "maximum_fetches_per_plan_unchanged": True,
            "alias_derived_only_from_visible_row_text": True,
            "lead_priority_uses_visible_title_only": True,
            "alias_hint_receives_vote_or_source_entropy_or_decision_credit": False,
            "final_cross_row_identity_relation_year_source_posterior_margin_leave_one_out_and_safe_change_rules_unchanged": True,
            "cache_or_cross_task_state_used": False,
            "bindings_restored": True,
            "task_question_opaque_id_query_url_page_prediction_value_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        with (
            patch(
                "deepwide_agent.v24530_alias_seeded_bounded_worker.parent.run_alias_title_worker",
                return_value={},
            ),
            patch.object(AliasSeededTargetAcquisition, "content_free_receipt", return_value=fake),
            self.assertRaisesRegex(RuntimeError, "did not execute"),
        ):
            run_alias_seeded_worker()

    def test_budget_and_runtime_source_remain_label_blind(self) -> None:
        self.assertEqual(budget_vector_seconds(), (150.0, 220.0, 245.0, 255.0))
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24530_alias_seeded_bounded_worker.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
