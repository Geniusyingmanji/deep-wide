from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25375_schema_total_changed_safe_runtime as runtime  # noqa: E402
from deepwide_agent import v25376_changed_safe_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25376_changed_safe_exact220 as finalizer  # noqa: E402
from scripts import run_v25376_changed_safe_exact220 as runner  # noqa: E402


class V25376ChangedSafeExact220Tests(unittest.TestCase):
    def test_visible_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertEqual(
            contract.payload_sha256([task["opaque_id"] for task in tasks]),
            "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a",
        )

    def test_schema_total_reachability_is_exact220(self) -> None:
        limits = runtime.score.ScoreFirstLimits(**contract.LIMITS)
        counts = {name: 0 for name in runtime.SCHEMA_SOURCES}
        for task in contract.task_vector(ROOT):
            plan, _observation, source = runtime.projected_plan(
                {}, task["question"], limits
            )
            counts[source] += 1
            self.assertEqual(len(plan["queries"]), 4)
            self.assertGreaterEqual(len(plan["columns"]), 1)
        self.assertEqual(
            counts,
            {
                "exact_visible": 194,
                "expanded_visible": 21,
                "provider_plan": 0,
                "generic_result": 5,
            },
        )

    def test_changed_safe_parent_authority_is_hash_bound(self) -> None:
        parents = contract.parent_receipts(ROOT, tracked=True)
        self.assertEqual(
            parents["v25374_changed_safe_mechanism_audit"]["sha256"],
            contract.PARENT_MECHANISM_AUDIT_SHA256,
        )

    def test_high_concurrency_and_physical_caps_are_fixed(self) -> None:
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 40)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(
            contract.PHYSICAL_CAPS,
            {
                "queries_per_task": 4,
                "fetches_per_task": 14,
                "model_forwards_per_task": 3,
            },
        )

    def test_candidate_is_only_scored_prediction(self) -> None:
        policy = contract.source_policy()
        self.assertTrue(policy["scored_prediction_is_changed_safe_candidate"])
        self.assertTrue(policy["control_retained_only_in_private_runtime_receipt"])
        self.assertTrue(policy["candidate_has_no_independent_model_or_sampling_effect"])
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit_or_routes"])

    def test_runner_rejects_privileged_input_before_wiring(self) -> None:
        task = dict(contract.task_vector(ROOT)[0])
        task["category"] = "forbidden"
        with mock.patch.object(runner.base, "run_one_task") as delegated:
            with self.assertRaises(ValueError):
                runner.run_one_task(task)
        delegated.assert_not_called()

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
                elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                    if node.slice.value in privileged:
                        hits.append(str(node.slice.value))
        self.assertEqual(hits, [])
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))

    def test_contract_protocol_is_sealed_and_tamper_closed(self) -> None:
        with mock.patch.object(contract, "dependency_manifest", return_value={"x": "a" * 64}), mock.patch.object(
            contract, "parent_receipts", return_value={"parent": {"sha256": "b" * 64}}
        ), mock.patch.object(contract, "watcher_snapshot", return_value=[]), mock.patch.object(
            contract.task_parent, "_input_bindings", return_value={}
        ):
            protocol = contract.build_protocol(
                ROOT,
                now=1,
                tracked=False,
                require_pristine=False,
                build_audit_sha256="c" * 64,
            )
        self.assertTrue(contract.sealed(protocol, "protocol_payload_sha256"))
        self.assertEqual(
            protocol["execution"]["scored_prediction"],
            "changed_safe_verified_edit_candidate",
        )
        changed = copy.deepcopy(protocol)
        changed["execution"]["model_slot_cap"] = 15
        self.assertFalse(contract.sealed(changed, "protocol_payload_sha256"))

    def test_successor_surfaces_are_fresh(self) -> None:
        self.assertFalse((ROOT / contract.OUTPUT_ROOT).exists())
        for path in (
            contract.PREAUDIT,
            contract.EXECUTION_START,
            contract.ATTEMPT_CLAIM,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.EVALUATOR_PROTOCOL,
            contract.RESULT,
            contract.POSTAUDIT,
        ):
            self.assertFalse((ROOT / path).exists())
        protocol_path = ROOT / contract.PROTOCOL
        if protocol_path.exists():
            protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
            self.assertEqual(
                contract.validate_protocol(ROOT, protocol), protocol
            )

    def test_finalizer_configures_fixed_evaluator_shell(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertIs(finalizer.base.runner, runner)
        self.assertEqual(
            finalizer.base.base.EVALUATOR_PROTOCOL, contract.EVALUATOR_PROTOCOL
        )
        self.assertEqual(finalizer.base.base.EVALUATOR_WORKERS, 32)


if __name__ == "__main__":
    unittest.main()
