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

from deepwide_agent import v25401_grounded_record_membership_runtime as parent  # noqa: E402
from deepwide_agent import v25545_deterministic_visible_constraint_runtime as strict  # noqa: E402
from deepwide_agent import v25569_constraint_totality_safe_handoff_runtime as target  # noqa: E402
from deepwide_agent import v25568_constraint_exact220_contract as exact220  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import QUESTION  # noqa: E402
from test_v25395_visible_membership_synthesis_runtime import MEMBERSHIP_QUESTION  # noqa: E402
from test_v25401_grounded_record_membership_runtime import (  # noqa: E402
    GroundedMembershipModel,
    run_runtime,
)


ORDER_QUESTION = MEMBERSHIP_QUESTION.replace(
    "Preserve row order.", "Sort by TLD Manager in ascending order."
)
PARENT_ROWS = ROOT / (
    "outputs/v25406_grounded_membership_exact220_v1_20260813/"
    "frozen_task_results.jsonl"
)


def historical_parent_rows():
    tasks = {row["opaque_id"]: row for row in exact220.task_vector(ROOT)}
    with PARENT_ROWS.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["runtime_completed"]:
                yield tasks[row["opaque_id"]], row


class V25569ConstraintTotalitySafeHandoffTests(unittest.TestCase):
    def test_canonical_projection_preserves_v25545_behavior(self) -> None:
        candidate_model = GroundedMembershipModel()
        strict_model = GroundedMembershipModel()
        result, stage, budget = run_runtime(
            target, candidate_model, question=ORDER_QUESTION
        )
        strict_result, _strict_stage, _ = run_runtime(
            strict, strict_model, question=ORDER_QUESTION
        )
        checked = target.validate_result(result)
        target.validate_stage_receipt(stage)
        self.assertEqual(checked["mode"], target.CANONICAL_PROJECTION)
        self.assertTrue(checked["projection_admitted"])
        self.assertFalse(checked["byte_exact_parent_handoff"])
        self.assertEqual(checked["prediction"], strict_result["prediction"])
        self.assertEqual(candidate_model.systems, strict_model.systems)
        self.assertEqual(candidate_model.users, strict_model.users)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertEqual(
            checked["constraint_totality_receipt"]["positive_signed_credit_count"],
            0,
        )

    def test_no_constraint_is_still_parent_prediction_byte_exact(self) -> None:
        candidate_model = GroundedMembershipModel()
        parent_model = GroundedMembershipModel()
        result, _stage, _budget = run_runtime(
            target, candidate_model, question=QUESTION
        )
        parent_result, _parent_stage, _ = run_runtime(
            parent, parent_model, question=QUESTION
        )
        checked = target.validate_result(result)
        self.assertEqual(checked["mode"], target.CANONICAL_PROJECTION)
        self.assertFalse(checked["candidate_prediction_changed"])
        self.assertEqual(checked["prediction"], parent_result["prediction"])

    def test_historical_parent_replay_keeps_all_209_terminal_predictions(self) -> None:
        counts = {"canonical_projection": 0, "byte_exact_parent_handoff": 0}
        for task, row in historical_parent_rows():
            result = target.build_result(row["runtime_result"], task["question"])
            checked = target.validate_result(result)
            counts[checked["mode"]] += 1
            if checked["byte_exact_parent_handoff"]:
                self.assertEqual(
                    checked["prediction"], row["runtime_result"]["prediction"]
                )
                self.assertFalse(checked["candidate_prediction_changed"])
        self.assertEqual(
            counts,
            {"canonical_projection": 204, "byte_exact_parent_handoff": 5},
        )

    def test_noncanonical_run_task_invokes_parent_once_and_returns_success(self) -> None:
        selected = None
        for task, row in historical_parent_rows():
            try:
                strict._visible_columns(row["runtime_result"]["prediction"])
            except ValueError:
                selected = (task, row)
                break
        self.assertIsNotNone(selected)
        task, row = selected
        with mock.patch.object(
            target.parent,
            "run_task",
            return_value=(row["runtime_result"], row["content_free_stage_receipt"]),
        ) as delegated:
            result, stage = target.run_task(
                task,
                model=object(),
                searches={},
                limits=object(),
                budget=object(),
                monotonic=lambda: 0.0,
            )
        delegated.assert_called_once()
        checked = target.validate_result(result)
        target.validate_stage_receipt(stage)
        self.assertEqual(checked["mode"], target.BYTE_EXACT_PARENT_HANDOFF)
        self.assertEqual(checked["prediction"], row["runtime_result"]["prediction"])
        self.assertFalse(stage["failure_present"])
        self.assertIsNone(stage["constrained_stage_receipt"])

    def test_resealed_mode_parent_or_prediction_tamper_fails(self) -> None:
        task, row = next(
            (task, row)
            for task, row in historical_parent_rows()
            if self._is_noncanonical(row["runtime_result"]["prediction"])
        )
        result = target.build_result(row["runtime_result"], task["question"])
        for kind in ("mode", "parent", "prediction"):
            changed = copy.deepcopy(result)
            if kind == "mode":
                changed["mode"] = target.CANONICAL_PROJECTION
                changed["projection_admitted"] = True
                changed["byte_exact_parent_handoff"] = False
            elif kind == "parent":
                changed["private_parent_result_payload_sha256"] = "a" * 64
            else:
                changed["prediction"] += "\n"
                changed["prediction_sha256"] = __import__("hashlib").sha256(
                    changed["prediction"].encode()
                ).hexdigest()
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    @staticmethod
    def _is_noncanonical(prediction: str) -> bool:
        try:
            strict._visible_columns(prediction)
            return False
        except ValueError:
            return True

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        path = ROOT / (
            "src/deepwide_agent/"
            "v25569_constraint_totality_safe_handoff_runtime.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden_fields
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "httpx",
            "socket",
            "urllib",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden_call in ("open(", "getenv(", "run_official_eval_local("):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
