from __future__ import annotations

import ast
import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25135_sparse_production_runtime as sparse  # noqa: E402
from deepwide_agent import v25271_validated_production_checkpoint_runtime as checkpoint  # noqa: E402
from deepwide_agent import v25342_checkpoint_exact220_adapter as adapter  # noqa: E402
from deepwide_agent import v25342_checkpoint_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25342_checkpoint_exact220 as finalizer  # noqa: E402
from scripts import run_v25342_checkpoint_exact220 as runner  # noqa: E402
import test_v25271_validated_production_checkpoint_runtime as checkpoint_tests  # noqa: E402


class V25342CheckpointExact220Tests(unittest.TestCase):
    def harness(self):
        return checkpoint_tests.V25271ValidatedProductionCheckpointRuntimeTests(
            "runTest"
        )

    def test_visible_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertEqual(
            contract.payload_sha256([task["opaque_id"] for task in tasks]),
            "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a",
        )

    def test_checkpoint_parent_authorities_are_hash_bound(self) -> None:
        parents = contract.parent_receipts(ROOT, tracked=True)
        self.assertEqual(
            parents["v25272_checkpoint_build_audit"]["sha256"],
            contract.CHECKPOINT_BUILD_AUDIT_SHA256,
        )
        self.assertEqual(
            parents["v25283_checkpoint_reliability_audit"]["sha256"],
            contract.CHECKPOINT_RELIABILITY_AUDIT_SHA256,
        )

    def test_execution_keeps_high_concurrency_and_physical_caps(self) -> None:
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 40)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(
            contract.PHYSICAL_CAPS,
            {
                "queries_per_task": 4,
                "fetches_per_task": 14,
                "model_forwards_per_task": 4,
            },
        )
        policy = contract.source_policy()
        self.assertTrue(policy["validated_production_checkpoint_precedes_auxiliary_envelope"])
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit_or_routes"])

    def test_normal_checkpoint_result_is_byte_preserving_completed_task(self) -> None:
        _inner, result, stage = self.harness()._run_target()
        wrapped_result = adapter.validate_result(adapter._wrap_result(result))
        wrapped_stage = adapter.validate_stage_receipt(
            adapter._wrap_stage(stage, runtime_returned=True)
        )
        self.assertEqual(wrapped_result["prediction"], result["prediction"])
        self.assertEqual(wrapped_result["cost"], result["cost"])
        self.assertFalse(wrapped_result["checkpoint_recovery_event_present"])
        self.assertFalse(wrapped_stage["checkpoint_recovery_event_present"])
        self.assertFalse(wrapped_stage["failure_present"])

    def test_postcheckpoint_recovery_is_completed_not_outer_failure(self) -> None:
        with mock.patch.object(
            checkpoint, "_build_result", side_effect=ValueError("hidden")
        ):
            _inner, result, stage = self.harness()._run_target()
        wrapped_result = adapter.validate_result(adapter._wrap_result(result))
        wrapped_stage = adapter.validate_stage_receipt(
            adapter._wrap_stage(stage, runtime_returned=True)
        )
        self.assertTrue(wrapped_result["checkpoint_recovery_event_present"])
        self.assertTrue(wrapped_stage["checkpoint_recovery_event_present"])
        self.assertFalse(wrapped_stage["failure_present"])
        self.assertTrue(wrapped_result["recovery_prediction_is_sealed_checkpoint_prediction"])
        self.assertNotIn("hidden", str(wrapped_result))

    def test_untrusted_checkpoint_remains_finite_outer_failure(self) -> None:
        harness = self.harness()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            _inner, budget, model, searches = harness._wiring(root)
            with mock.patch.object(
                checkpoint,
                "validate_checkpoint",
                side_effect=ValueError("hidden checkpoint"),
            ), self.assertRaises(checkpoint.ProductionCheckpointStageError) as caught:
                checkpoint.run_task(
                    checkpoint_tests.TASK,
                    model=model,
                    searches=searches,
                    limits=checkpoint_tests.limits(),
                    budget=budget,
                    monotonic=time.monotonic,
                )
        wrapped = adapter.validate_stage_receipt(
            adapter._wrap_stage(caught.exception.stage_receipt, runtime_returned=False)
        )
        self.assertTrue(wrapped["failure_present"])
        self.assertEqual(wrapped["failure_stage"], "production_checkpoint_select")
        self.assertFalse(wrapped["checkpoint_recovery_event_present"])
        self.assertNotIn("hidden checkpoint", str(wrapped))

    def test_adapter_result_and_stage_tamper_fail_closed(self) -> None:
        _inner, result, stage = self.harness()._run_target()
        wrapped_result = adapter._wrap_result(result)
        wrapped_stage = adapter._wrap_stage(stage, runtime_returned=True)
        changed_result = copy.deepcopy(wrapped_result)
        changed_result["prediction"] += "x"
        with self.assertRaises(ValueError):
            adapter.validate_result(changed_result)
        changed_stage = copy.deepcopy(wrapped_stage)
        changed_stage["checkpoint_recovery_event_present"] = True
        with self.assertRaises(ValueError):
            adapter.validate_stage_receipt(changed_stage)

    def test_runner_rejects_privileged_input_before_effect(self) -> None:
        task = dict(contract.task_vector(ROOT)[0])
        task["category"] = "forbidden"
        with self.assertRaises(ValueError):
            runner.run_one_task(task)

    def test_runtime_ast_has_no_privileged_or_evaluator_capability(self) -> None:
        privileged = {
            "category",
            "question_type",
            "task_category",
            "ground_truth",
            "answer_key",
            "split",
            "score",
            "reward",
        }
        hits: list[str] = []
        imports: list[str] = []
        for relative in (contract.CONTRACT, contract.RUNNER, contract.RUNTIME):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
                elif isinstance(node, ast.Subscript) and isinstance(
                    node.slice, ast.Constant
                ):
                    if node.slice.value in privileged:
                        hits.append(str(node.slice.value))
        self.assertEqual(hits, [])
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))

    def test_successor_surfaces_and_finalizer_are_fresh(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, contract.parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, contract.parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.RUNNER_MARKER, contract.parent.RUNNER_MARKER)
        self.assertEqual(contract.MODEL, contract.parent.MODEL)
        self.assertEqual(contract.SEARCH, contract.parent.SEARCH)
        self.assertEqual(contract.LIMITS, contract.parent.LIMITS)
        self.assertFalse((ROOT / contract.OUTPUT_ROOT).exists())
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertIs(finalizer.base.runner, runner)
        self.assertEqual(
            finalizer.base.base.EVALUATOR_PROTOCOL, contract.EVALUATOR_PROTOCOL
        )


if __name__ == "__main__":
    unittest.main()
