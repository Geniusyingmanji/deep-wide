from __future__ import annotations

import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24270_budget_equivalent_union import (  # noqa: E402
    build_v24270_fallback_result,
)
from deepwide_agent import v24271_forward_contract as forward_contract  # noqa: E402
from scripts import activate_v24271_keyless_dev64 as activation_target  # noqa: E402
from scripts import audit_v24271_keyless_dev64 as audit_target  # noqa: E402
from scripts import finalize_v24271_keyless_dev64 as finalizer  # noqa: E402
from scripts import run_v24271_keyless_dev64 as runner  # noqa: E402
from scripts.preregister_v24271_keyless_dev64 import (  # noqa: E402
    EXECUTOR_CONCURRENCY,
    MODEL_SLOT_CAP,
    SELECTED_COUNT,
    build_protocol,
    build_forward_contract,
)
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


def visible(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return a table. Column names: Name, Value.",
    }


def fallback(position: int, limits: ScoreFirstLimits) -> dict:
    return build_v24270_fallback_result(
        visible(position),
        limits=limits,
        completion_kind="worker_failure_fallback",
        failure_stage="test_executor",
        failure_type="SyntheticFailure",
        elapsed_seconds=0.1,
    )


class V24271KeylessDev64Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = build_protocol(ROOT, now=1, require_pristine=False)
        cls.forward_protocol = build_forward_contract(cls.protocol)
        cls.limits = ScoreFirstLimits(**dict(cls.protocol["limits"]))

    def test_selection_is_frozen_opaque_allowlist_and_matches_control_order(self) -> None:
        rows = forward_contract.visible_manifest_rows(ROOT)
        ids = forward_contract.selected_ids(self.forward_protocol)
        self.assertTrue(set(ids).issubset({row["opaque_id"] for row in rows}))
        frozen_control_ids = [
            line.strip()
            for line in (ROOT / "configs/full220_v2403_r1_devval_s04.ids")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        self.assertEqual(ids, frozen_control_ids)

    def test_protocol_freezes_efficiency_and_quality_gate_without_full220(self) -> None:
        value = self.protocol
        self.assertEqual(value["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(value["forward_contract"]["executor_concurrency"], 2)
        self.assertEqual(value["model_slot_contract"]["slot_cap"], 2)
        self.assertEqual(value["decision_contract"]["maximum_search_token_ratio"], 0.35)
        self.assertEqual(value["decision_contract"]["maximum_task_wall_sum_ratio"], 0.5)
        self.assertFalse(value["authorization"]["new_exact220_launch"])
        self.assertFalse(value["authorization"]["leaderboard_submission_or_sota_claim"])

    def test_forward_import_closure_has_no_evaluator_or_control_capability(self) -> None:
        sources = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in self.protocol["forward_surface"]["manifest"]
        )
        for marker in audit_target.FORWARD_CAPABILITY_MARKERS:
            self.assertNotIn(marker, sources)
        script_imports = []
        for relative in self.protocol["forward_surface"]["dependency_manifest"]:
            script_imports.extend(audit_target._script_imports(ROOT / relative))
        script_imports.extend(
            audit_target._script_imports(ROOT / "scripts/run_v24271_keyless_dev64.py")
        )
        self.assertTrue(
            set(script_imports).issubset(audit_target.DEPENDENCY_IMPORT_ALLOWLIST)
        )

    def test_scheduler_runs_exact64_once_with_two_workers(self) -> None:
        tasks = [visible(position) for position in range(1, SELECTED_COUNT + 1)]
        active = 0
        maximum = 0
        seen: list[str] = []
        lock = threading.Lock()
        progress: list[dict] = []

        def fake(_root, _protocol, task, _task_root):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
                seen.append(task["opaque_id"])
            time.sleep(0.001)
            with lock:
                active -= 1
            return runner.TaskOutcome(
                fallback(int(task["opaque_id"][5:], 16), self.limits), True, True, 0
            )

        outcomes = runner.execute_forward(
            ROOT,
            self.forward_protocol,
            tasks,
            runner=fake,
            progress_writer=progress.append,
        )
        self.assertEqual(len(outcomes), SELECTED_COUNT)
        self.assertEqual(maximum, EXECUTOR_CONCURRENCY)
        self.assertEqual(len(seen), SELECTED_COUNT)
        self.assertEqual(len(set(seen)), SELECTED_COUNT)
        self.assertEqual(progress[-1]["completed_predictions"], SELECTED_COUNT)

    def test_scheduler_rejects_non64_input(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "task count"):
            runner.execute_forward(ROOT, self.forward_protocol, [visible(1)], runner=lambda *_: None)

    def test_forward_result_validator_rejects_resealed_extra_field_first(self) -> None:
        value = {
            "artifact_version": 1,
            "role": "v24271_keyless_dev64_forward_result",
            "protocol_id": self.protocol["protocol_id"],
            "question": "forbidden",
        }
        value["result_payload_sha256"] = payload_sha256(value)
        with mock.patch.object(
            runner,
            "validate_activation",
            return_value={"activation_payload_sha256": "a" * 64},
        ), mock.patch.object(runner, "validate_execution_start"), mock.patch.object(
            runner,
            "read_object",
            return_value={
                "role": "v24271_candidate_prediction_freeze",
            },
        ), mock.patch.object(
            runner, "validate_prediction_freeze"
        ), self.assertRaisesRegex(RuntimeError, "forward result"):
            runner.validate_forward_result(ROOT, self.forward_protocol, value)

    def test_forward_activation_rejects_unbound_preaudit(self) -> None:
        activation = {
            "artifact_version": 1,
            "role": "v24271_keyless_dev64_activation",
            "created_at_unix": 1,
            "status": "active",
            "forward_contract_sha256": "a" * 64,
            "forward_contract_payload_sha256": self.forward_protocol[
                "forward_contract_payload_sha256"
            ],
            "preactivation_audit_sha256": "b" * 64,
            "forward_manifest_sha256": self.forward_protocol["forward_surface"][
                "dependency_manifest_sha256"
            ],
            "selected_count": SELECTED_COUNT,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "global_model_slot_cap": MODEL_SLOT_CAP,
            "shared_api_lease_active_before_activation": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "new_exact220_or_sota_authorized": False,
        }
        activation["activation_payload_sha256"] = payload_sha256(activation)
        bad_audit = {
            "role": "v24271_keyless_dev64_preactivation_audit",
            "audit_valid": True,
            "launch_authorized": True,
            "forward_contract_sha256": "c" * 64,
            "forward_contract_payload_sha256": self.forward_protocol[
                "forward_contract_payload_sha256"
            ],
        }
        bad_audit["audit_payload_sha256"] = payload_sha256(bad_audit)
        with mock.patch.object(
            runner, "read_object", side_effect=[activation, bad_audit]
        ), mock.patch.object(
            runner, "sha256", return_value="a" * 64
        ), self.assertRaisesRegex(RuntimeError, "preactivation audit"):
            runner.validate_activation(ROOT, self.forward_protocol)

    def test_finalizer_barrier_order_precedes_control_and_evaluator_open(self) -> None:
        order: list[str] = []
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            root = Path(directory)
            with mock.patch.object(
                finalizer,
                "validate_candidate_barrier",
                side_effect=lambda *_: order.append("candidate_freeze") or {"rows": [{}] * SELECTED_COUNT},
            ), mock.patch.object(
                finalizer,
                "validate_protocol",
                side_effect=lambda *_: order.append("full_protocol") or self.protocol,
            ), mock.patch.object(
                finalizer, "validate_full_forward_binding"
            ), mock.patch.object(
                finalizer,
                "load_frozen_control_after_candidate",
                side_effect=lambda *_: order.append("control") or {"ids": []},
            ), mock.patch.object(
                finalizer,
                "validate_live_evaluator_identity",
                side_effect=lambda *_: order.append("evaluator") or {},
            ), self.assertRaisesRegex(RuntimeError, "recovery surface is absent"):
                finalizer.finalize(root, resume_evaluator=True)
        self.assertEqual(
            order,
            ["candidate_freeze", "full_protocol", "control", "evaluator"],
        )

    def test_decision_requires_every_frozen_gate(self) -> None:
        base = {
            "runtime_completed": 64,
            "runtime_failed": 0,
            "evaluator_valid": 64,
            "evaluator_invalid_or_not_run": 0,
            "whole_table_successes": 2,
            "entity_acc": 0.7,
            "f1_by_row": 0.2,
            "f1_by_item": 0.35,
            "column_f1": 0.42,
            "quality_composite": 0.4175,
            "score": 0.03,
            "model_generated_tables": 63,
            "fallback_tables": 1,
            "search_total_tokens": 1000,
            "task_wall_sum_seconds": 100.0,
            "unrecoverable_provider_failures": 0,
        }
        candidate = copy.deepcopy(base)
        candidate["search_total_tokens"] = 300
        candidate["task_wall_sum_seconds"] = 45.0
        value = finalizer.decision(self.protocol, base, candidate)
        self.assertTrue(value["passed"])
        candidate["unrecoverable_provider_failures"] = 1
        value = finalizer.decision(self.protocol, base, candidate)
        self.assertFalse(value["passed"])
        self.assertFalse(value["checks"]["candidate_unrecoverable_provider_failures"])

    def test_activation_blocks_active_lease_without_process_signal(self) -> None:
        preaudit = {
            "role": "v24271_keyless_dev64_preactivation_audit",
            "audit_valid": True,
            "launch_authorized": True,
            "protocol_sha256": "a" * 64,
        }
        preaudit["audit_payload_sha256"] = payload_sha256(preaudit)
        with mock.patch.object(activation_target, "validate_protocol", return_value=self.protocol), mock.patch.object(
            activation_target, "read_object", return_value=preaudit
        ), mock.patch.object(
            activation_target, "sha256", return_value="a" * 64
        ), mock.patch.object(
            activation_target, "process_snapshot", return_value=[]
        ), mock.patch.object(
            activation_target, "lease_observation", return_value={"active": True}
        ), self.assertRaisesRegex(RuntimeError, "boundary"):
            activation_target.build_activation(ROOT, now=1)


if __name__ == "__main__":
    unittest.main()
