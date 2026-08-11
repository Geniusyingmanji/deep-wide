from __future__ import annotations

import ast
import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25130_causal_salience_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from scripts import control_v25130_causal_salience_exact220 as control  # noqa: E402
from scripts import finalize_v25130_causal_salience_exact220 as finalizer  # noqa: E402
from scripts import run_v25130_causal_salience_exact220 as runner  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
)


class V25130CausalSalienceExact220Tests(unittest.TestCase):
    def test_exact_v24857_visible_task_vector_and_label_blind_boundary(self) -> None:
        tasks = contract.task_vector(ROOT)
        parent = contract._parent_task_contract(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(
            contract.payload_sha256([row["opaque_id"] for row in tasks]),
            parent["opaque_id_vector_sha256"],
        )
        self.assertEqual(
            contract.payload_sha256([row["question"] for row in tasks]),
            parent["visible_question_vector_sha256"],
        )
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))

    def test_high_concurrency_and_paired_resource_caps_are_explicit(self) -> None:
        self.assertEqual(contract.SELECTED_COUNT, 220)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 40)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["fetch_targets"], 10)
        self.assertEqual(contract.LIMITS["wall_seconds"], 240)
        orders = contract.arm_order_vector()
        self.assertEqual(len(orders), 220)
        self.assertEqual(
            sum(order[0] == contract.CANDIDATE_ARM for order in orders), 110
        )

    def test_parent_quality_go_is_hash_bound_but_direct_launch_was_false(self) -> None:
        value = contract._quality_parent(ROOT)
        self.assertTrue(value["quality_gate_go"])
        self.assertTrue(value["full220_successor_build_authorized"])
        self.assertFalse(value["direct_exact220_launch_authorized_by_parent"])

    def test_protocol_freezes_causal_runtime_and_discloses_cost(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_clean=False,
            require_pristine=False,
        )
        self.assertEqual(value["execution"]["runtime_policy_id"], contract.runtime.POLICY_ID)
        self.assertEqual(value["execution"]["frozen_prediction_arm"], contract.CANDIDATE_ARM)
        self.assertTrue(
            value["treatment_scope"][
                "candidate_prediction_identity_handoff_without_retrieval_gain"
            ]
        )
        self.assertTrue(
            value["treatment_scope"][
                "matched_pair_doubles_synthesis_cost_vs_single_arm_exact220"
            ]
        )
        self.assertFalse(
            value["source_policy"][
                "entropy_or_information_gain_assigns_signed_credit_or_routes"
            ]
        )

    def test_resealed_protocol_runtime_or_budget_tamper_fails_closed(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_clean=False,
            require_pristine=False,
        )
        for kind in ("runtime", "budget"):
            changed = copy.deepcopy(value)
            if kind == "runtime":
                changed["execution"]["runtime_policy_id"] = "other"
            else:
                changed["execution"]["limits"]["fetch_targets"] = 11
            changed.pop("protocol_payload_sha256")
            changed = contract.seal(changed, "protocol_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                contract.validate_protocol(ROOT, changed, tracked=False)

    def test_real_paired_runtime_row_projects_and_revalidates(self) -> None:
        task = contract.task_vector(ROOT)[0]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            inner = CompatibleModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GroundedFrontierSearch(task["question"], phase)
                for phase in contract.runtime.PHASES
            }
            result = contract.runtime.run_paired_task(
                task,
                model=model,
                searches=searches,
                limits=runner.ScoreFirstLimits(**contract.LIMITS),
                arm_order=contract.arm_order_vector()[0],
            )
            receipt = result["content_free_receipt"]
            effect = runner.engine._actual_effect_snapshot(None, {})
            effect.update(
                {
                    "model_logical_requests": receipt["physical_model_logical_call_count"],
                    "model_provider_requests": receipt["model_provider_request_count"],
                    "model_provider_attempts": receipt["model_provider_attempt_count"],
                    "model_provider_successes": receipt["model_provider_request_count"],
                    "model_slot_acquisitions": receipt["physical_model_logical_call_count"],
                    "logical_queries": receipt["physical_query_count"],
                    "fetch_requests": receipt["physical_fetch_count"],
                    "fetch_calls": receipt["physical_fetch_count"],
                }
            )
            effect.pop("snapshot_payload_sha256")
            effect = runner.engine.contract.seal(effect, "snapshot_payload_sha256")
            parent_row = runner.engine._from_runtime(
                task,
                contract.arm_order_vector()[0],
                result,
                runner.engine._health(),
                effect,
            )
        projected = dict(parent_row)
        projected["role"] = "v25130_causal_salience_exact220_task_result"
        projected["protocol_id"] = contract.PROTOCOL_ID
        projected.pop("result_payload_sha256")
        projected = contract.seal(projected, "result_payload_sha256")
        checked = runner.validate_task_row(projected)
        self.assertEqual(checked["opaque_id"], task["opaque_id"])
        self.assertIn("causal_coupling_receipt", checked)

    def test_setup_failure_is_terminal_failure_as_zero_without_retry(self) -> None:
        task = contract.task_vector(ROOT)[0]
        original = runner.HardTotalWallResponsesClient

        class BrokenClient:
            def __init__(self, *args: object, **kwargs: object) -> None:
                raise RuntimeError("synthetic setup failure")

        runner.HardTotalWallResponsesClient = BrokenClient
        try:
            row = runner.run_one_task(task, contract.arm_order_vector()[0])
        finally:
            runner.HardTotalWallResponsesClient = original
        checked = runner.validate_task_row(row)
        self.assertTrue(checked["failure_as_zero"])
        self.assertFalse(checked["runtime_completed"])
        self.assertEqual(checked["actual_effect_snapshot"]["model_logical_requests"], 0)

    def test_summary_requires_zero_unattributable_and_exact_identity_partition(self) -> None:
        source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        self.assertIn('"unattributable_prediction_changed_tasks"', source)
        self.assertIn('"causal_identity_partition_valid_tasks"', source)
        self.assertIn('"causal_invariants_hold"', source)
        self.assertIn("identity_handoff_prediction_changed_tasks", source)

    def test_forward_dependency_closure_is_label_blind_secret_free(self) -> None:
        control.configure()
        self.assertEqual(control.parent._findings(tracked=False), ([], [], [], []))
        closure = set(contract.forward_dependency_closure(ROOT))
        self.assertIn(Path("src/deepwide_agent/clients.py"), closure)
        self.assertIn(contract.RUNTIME, closure)
        self.assertIn(contract.RUNNER, closure)

    def test_runner_does_not_import_evaluator_or_spawn_children(self) -> None:
        tree = ast.parse((ROOT / contract.RUNNER).read_text(encoding="utf-8"))
        imports: list[str] = []
        calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
        self.assertFalse(any("finalize" in item or "evaluator" in item for item in imports))
        self.assertNotIn("Popen", calls)

    def test_finalizer_reuses_fixed_32_worker_official_evaluator(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertIs(finalizer.base._forward_barrier, finalizer._forward_barrier)
        self.assertEqual(finalizer.base.EVALUATOR_WORKERS, 32)
        self.assertEqual(finalizer.base.REFERENCES["v24857_best"], contract.BASELINE_RESULT)


if __name__ == "__main__":
    unittest.main()
