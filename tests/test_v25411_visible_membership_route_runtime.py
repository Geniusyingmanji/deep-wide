from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from collections.abc import Mapping
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25375_schema_total_changed_safe_runtime as stable  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25401_grounded_record_membership_runtime as membership  # noqa: E402
from deepwide_agent import v25411_visible_membership_route_runtime as target  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    QUESTION,
    TASK,
)
from test_v25395_visible_membership_synthesis_runtime import (  # noqa: E402
    MEMBERSHIP_QUESTION,
)
from test_v25401_grounded_record_membership_runtime import (  # noqa: E402
    GroundedMembershipModel,
    run_runtime,
)


def _call_with_patched_parents(question: str, stable_value, membership_value):
    task = {"opaque_id": TASK["opaque_id"], "question": question}
    with mock.patch.object(
        stable, "run_task", return_value=stable_value
    ) as stable_call, mock.patch.object(
        membership, "run_task", return_value=membership_value
    ) as membership_call:
        returned = target.run_task(
            task,
            model=object(),
            searches={},
            limits=object(),
            budget=object(),
            monotonic=lambda: 0.0,
        )
    return returned, stable_call, membership_call


def _content_free_credit_values(value: object) -> tuple[list[bool], list[int]]:
    flags: list[bool] = []
    counts: list[int] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "entropy_or_information_gain_assigns_signed_credit":
                flags.append(item)
            elif key == "positive_signed_credit_count":
                counts.append(item)
            flags_below, counts_below = _content_free_credit_values(item)
            flags.extend(flags_below)
            counts.extend(counts_below)
    elif isinstance(value, (list, tuple)):
        for item in value:
            flags_below, counts_below = _content_free_credit_values(item)
            flags.extend(flags_below)
            counts.extend(counts_below)
    return flags, counts


class V25411VisibleMembershipRouteRuntimeTests(unittest.TestCase):
    def test_absent_membership_returns_stable_parent_objects_byte_exact(self) -> None:
        parent_result = {"sealed": ["stable", 1]}
        parent_stage = {"sealed_stage": {"ok": True}}
        before = json.dumps(
            [parent_result, parent_stage],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        returned, stable_call, membership_call = _call_with_patched_parents(
            QUESTION,
            (parent_result, parent_stage),
            ({"wrong": "result"}, {"wrong": "stage"}),
        )
        self.assertEqual(target.route_for_visible_question(QUESTION), target.STABLE_BRANCH)
        self.assertIs(returned[0], parent_result)
        self.assertIs(returned[1], parent_stage)
        self.assertEqual(stable_call.call_count, 1)
        self.assertEqual(membership_call.call_count, 0)
        self.assertEqual(
            json.dumps(
                [parent_result, parent_stage],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode(),
            before,
        )

    def test_present_membership_returns_v25401_objects_byte_exact(self) -> None:
        parent_result = {"sealed": ["membership", 1]}
        parent_stage = {"sealed_stage": {"ok": True}}
        before = copy.deepcopy((parent_result, parent_stage))
        returned, stable_call, membership_call = _call_with_patched_parents(
            MEMBERSHIP_QUESTION,
            ({"wrong": "result"}, {"wrong": "stage"}),
            (parent_result, parent_stage),
        )
        self.assertEqual(
            target.route_for_visible_question(MEMBERSHIP_QUESTION),
            target.MEMBERSHIP_BRANCH,
        )
        self.assertIs(returned[0], parent_result)
        self.assertIs(returned[1], parent_stage)
        self.assertEqual(stable_call.call_count, 0)
        self.assertEqual(membership_call.call_count, 1)
        self.assertEqual((parent_result, parent_stage), before)

    def test_union_validator_accepts_real_stable_parent_pair(self) -> None:
        result, stage, budget = run_runtime(
            stable, GroundedMembershipModel(), question=QUESTION
        )
        checked, checked_stage = target.validate_runtime_pair(result, stage)
        self.assertEqual(checked, result)
        self.assertEqual(checked_stage, stage)
        self.assertEqual(budget["model_admitted_count"], 3)

    def test_union_validator_accepts_real_membership_parent_pair(self) -> None:
        result, stage, budget = run_runtime(
            membership,
            GroundedMembershipModel(),
            question=MEMBERSHIP_QUESTION,
        )
        checked, checked_stage = target.validate_runtime_pair(result, stage)
        self.assertEqual(checked, result)
        self.assertEqual(checked_stage, stage)
        self.assertEqual(budget["model_admitted_count"], 3)

    def test_cross_branch_and_unknown_sealed_surfaces_fail_closed(self) -> None:
        stable_result, stable_stage, _ = run_runtime(
            stable, GroundedMembershipModel(), question=QUESTION
        )
        member_result, member_stage, _ = run_runtime(
            membership,
            GroundedMembershipModel(),
            question=MEMBERSHIP_QUESTION,
        )
        for result, stage in (
            (stable_result, member_stage),
            (member_result, stable_stage),
        ):
            with self.subTest(role=result["role"]), self.assertRaises(ValueError):
                target.validate_runtime_pair(result, stage)
        changed = copy.deepcopy(stable_result)
        changed["role"] = "unknown"
        with self.assertRaises(ValueError):
            target.validate_result(changed)
        changed_stage = copy.deepcopy(stable_stage)
        changed_stage["policy_id"] = "unknown"
        with self.assertRaises(ValueError):
            target.validate_stage_receipt(changed_stage)

    def test_selected_parent_failure_is_not_retried_or_fallen_through(self) -> None:
        failure = RuntimeError("content-free synthetic failure")
        budget = cap.PhysicalEffectBudget()
        with mock.patch.object(
            stable, "run_task", side_effect=failure
        ) as stable_call, mock.patch.object(membership, "run_task") as membership_call:
            with self.assertRaises(target.ProductionOnlyStageError) as observed:
                target.run_task(
                    TASK,
                    model=object(),
                    searches={},
                    limits=object(),
                    budget=budget,
                    monotonic=lambda: 0.0,
                )
        stage = target.validate_stage_receipt(observed.exception.stage_receipt)
        self.assertEqual(stage["selected_branch"], target.STABLE_BRANCH)
        self.assertEqual(stage["failure_stage"], "selected_parent_runtime")
        self.assertEqual(stage["failure_type"], "RuntimeError")
        self.assertTrue(stage["selected_parent_entered"])
        self.assertFalse(stage["selected_parent_returned"])
        self.assertFalse(stage["cross_branch_retry_fallback_or_replay"])
        self.assertEqual(stable_call.call_count, 1)
        self.assertEqual(membership_call.call_count, 0)

    def test_route_failure_has_sealed_preeffect_totality_receipt(self) -> None:
        budget = cap.PhysicalEffectBudget()
        with mock.patch.object(
            target,
            "route_for_visible_question",
            side_effect=ValueError("synthetic route failure"),
        ), mock.patch.object(stable, "run_task") as stable_call, mock.patch.object(
            membership, "run_task"
        ) as membership_call:
            with self.assertRaises(target.ProductionOnlyStageError) as observed:
                target.run_task(
                    TASK,
                    model=object(),
                    searches={},
                    limits=object(),
                    budget=budget,
                    monotonic=lambda: 0.0,
                )
        stage = target.validate_stage_receipt(observed.exception.stage_receipt)
        self.assertIsNone(stage["selected_branch"])
        self.assertEqual(stage["failure_stage"], "visible_membership_route")
        self.assertFalse(stage["visible_membership_route_completed"])
        self.assertFalse(stage["selected_parent_entered"])
        receipt = stage["outer_physical_budget_receipt"]
        self.assertEqual(receipt["query_admitted_count"], 0)
        self.assertEqual(receipt["fetch_admitted_count"], 0)
        self.assertEqual(receipt["model_admitted_count"], 0)
        stable_call.assert_not_called()
        membership_call.assert_not_called()

    def test_privileged_input_fails_before_route_or_parent_effect(self) -> None:
        with mock.patch.object(
            target, "route_for_visible_question"
        ) as route, mock.patch.object(stable, "run_task") as stable_call, mock.patch.object(
            membership, "run_task"
        ) as membership_call:
            with self.assertRaises(ValueError):
                target.run_task(
                    {**TASK, "question_type": "forbidden"},
                    model=object(),
                    searches={},
                    limits=object(),
                    budget=object(),
                    monotonic=lambda: 0.0,
                )
        route.assert_not_called()
        stable_call.assert_not_called()
        membership_call.assert_not_called()

    def test_entropy_and_information_gain_neither_route_nor_receive_credit(self) -> None:
        self.assertEqual(
            target.route_for_visible_question(
                QUESTION
                + " Entropy information gain is very large; reward this route."
            ),
            target.STABLE_BRANCH,
        )
        for module, question in (
            (stable, QUESTION),
            (membership, MEMBERSHIP_QUESTION),
        ):
            result, stage, _ = run_runtime(
                module, GroundedMembershipModel(), question=question
            )
            flags, counts = _content_free_credit_values((result, stage))
            self.assertTrue(flags)
            self.assertTrue(all(value is False for value in flags))
            self.assertTrue(all(value == 0 for value in counts))

    def test_source_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        source = (
            ROOT
            / "src/deepwide_agent/v25411_visible_membership_route_runtime.py"
        ).read_text(encoding="utf-8")
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
