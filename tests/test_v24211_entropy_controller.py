from __future__ import annotations

import ast
import copy
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24211_entropy_controller import (  # noqa: E402
    CONTEXT_ACTIONS,
    FEATURE_KEYS,
    MAX_PREDICTED_SYSTEM_TOKENS,
    MODEL_ROLE,
    NO_ENTROPY_FEATURE_KEYS,
    SIGNAL_KEYS,
    decide_entropy_action,
    object_sha256,
    project_four_layer_features,
    validate_action_model,
    validate_decision_receipt,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def signals(**updates: float | None) -> dict[str, float | None]:
    value: dict[str, float | None] = {
        "anchor_risk_proxy": 0.4,
        "coverage_risk_proxy": 0.5,
        "row_eligibility_risk_proxy": 0.6,
        "cell_value_risk_proxy": 0.7,
        "anchor_normalized_entropy": 0.8,
    }
    value.update(updates)
    return value


def action_model(
    feature_keys: tuple[str, ...],
    *,
    contribution: float,
    tokens: int,
) -> dict[str, object]:
    width = len(feature_keys) + 1
    return {
        "fit_records": 5,
        "calibration_records": 3,
        "raw_coefficients": {
            "task_contribution": [0.0] * width,
            "log_action_system_tokens": [0.0] * width,
        },
        "affine_calibrators": {
            "task_contribution": [contribution, 0.0],
            "log_action_system_tokens": [math.log1p(tokens), 0.0],
        },
    }


def branch(
    feature_keys: tuple[str, ...],
    *,
    contributions: dict[str, dict[str, float]] | None = None,
    token_costs: dict[str, dict[str, int]] | None = None,
) -> dict[str, object]:
    contributions = contributions or {}
    token_costs = token_costs or {}
    return {
        "feature_keys": list(feature_keys),
        "models": {
            context: {
                action: action_model(
                    feature_keys,
                    contribution=contributions.get(context, {}).get(action, 0.1),
                    tokens=token_costs.get(context, {}).get(action, 100),
                )
                for action in actions
            }
            for context, actions in CONTEXT_ACTIONS.items()
        },
    }


def sealed_model(
    *,
    full_contributions: dict[str, dict[str, float]] | None = None,
    full_token_costs: dict[str, dict[str, int]] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "artifact_version": 1,
        "role": MODEL_ROLE,
        "job_manifest_sha256": SHA_B,
        "model_ready": True,
        "blockers": [],
        "full_model": branch(
            FEATURE_KEYS,
            contributions=full_contributions,
            token_costs=full_token_costs,
        ),
        "no_entropy_baseline": branch(NO_ENTROPY_FEATURE_KEYS),
        "fit_record_count": 45,
        "calibration_record_count": 27,
        "fit_task_clusters": 16,
        "calibration_task_clusters": 8,
        "ridge_lambda": 0.001,
        "minimum_fit_records_per_context_action": 5,
        "minimum_calibration_records_per_context_action": 3,
        "fit_calibration_aggregate_sha256": SHA_C,
        "audit_outcomes_read": False,
        "controller_or_training_authorized": False,
    }
    value["model_sha256"] = object_sha256(value)
    return value


def decide(
    model: dict[str, object],
    *,
    context: str = "anchor",
    policy_branch: str = "full_entropy",
    current_signals: dict[str, float | None] | None = None,
) -> dict[str, object]:
    return decide_entropy_action(
        model=model,
        expected_model_sha256=str(model["model_sha256"]),
        expected_job_manifest_sha256=SHA_B,
        signals=current_signals or signals(),
        context=context,
        policy_branch=policy_branch,
        opaque_task_ref_sha256=SHA_A,
        decision_index=2,
        pre_action_state_sha256=SHA_C,
        selected_parent_manifest_sha256=SHA_D,
    )


class V24211EntropyControllerTests(unittest.TestCase):
    def test_four_layer_projection_uses_canonical_zero_and_availability(self) -> None:
        value = project_four_layer_features(
            signals(
                anchor_risk_proxy=None,
                row_eligibility_risk_proxy=None,
                anchor_normalized_entropy=None,
            )
        )
        self.assertEqual(tuple(value), FEATURE_KEYS)
        self.assertEqual(value["anchor_risk_proxy"], 0.0)
        self.assertEqual(value["anchor_risk_available"], 0.0)
        self.assertEqual(value["coverage_risk_available"], 1.0)
        self.assertEqual(value["row_eligibility_risk_available"], 0.0)
        self.assertEqual(value["cell_value_risk_available"], 1.0)
        self.assertEqual(value["anchor_normalized_entropy"], 0.0)
        self.assertEqual(value["anchor_entropy_available"], 0.0)

    def test_projection_rejects_extra_reordered_and_out_of_range_signals(self) -> None:
        extra = signals()
        extra["question_type"] = 0.0
        with self.assertRaisesRegex(ValueError, "signal schema"):
            project_four_layer_features(extra)
        reordered = {key: signals()[key] for key in reversed(SIGNAL_KEYS)}
        with self.assertRaisesRegex(ValueError, "signal schema"):
            project_four_layer_features(reordered)
        with self.assertRaisesRegex(ValueError, "outside"):
            project_four_layer_features(signals(coverage_risk_proxy=1.1))

    def test_selects_positive_value_per_token_then_frozen_ties(self) -> None:
        actions = CONTEXT_ACTIONS["anchor"]
        model = sealed_model(
            full_contributions={
                "anchor": {actions[0]: 0.4, actions[1]: 0.3, actions[2]: -0.2}
            },
            full_token_costs={
                "anchor": {actions[0]: 400, actions[1]: 100, actions[2]: 1}
            },
        )
        receipt = decide(model)
        self.assertEqual(receipt["decision_kind"], "action")
        self.assertEqual(receipt["selected_action"], actions[1])
        self.assertEqual(
            receipt["decision_reason"],
            "maximum_strictly_positive_predicted_contribution_per_token",
        )
        self.assertEqual(receipt, validate_decision_receipt(receipt))

        tied = sealed_model(
            full_contributions={"anchor": {action: 0.2 for action in actions}},
            full_token_costs={"anchor": {action: 100 for action in actions}},
        )
        self.assertEqual(decide(tied)["selected_action"], actions[0])

    def test_no_positive_contribution_stops(self) -> None:
        actions = CONTEXT_ACTIONS["late_0"]
        model = sealed_model(
            full_contributions={
                "late_0": {actions[0]: 0.0, actions[1]: -0.1, actions[2]: -1.0}
            }
        )
        receipt = decide(model, context="late_0")
        self.assertEqual(receipt["decision_kind"], "stop")
        self.assertIsNone(receipt["selected_action"])

    def test_missing_branch_signal_abstains_but_no_entropy_anchor_can_rank(self) -> None:
        model = sealed_model()
        missing_entropy = signals(anchor_normalized_entropy=None)
        full = decide(model, current_signals=missing_entropy)
        baseline = decide(
            model,
            policy_branch="no_entropy",
            current_signals=missing_entropy,
        )
        self.assertEqual(full["decision_kind"], "abstain")
        self.assertEqual(full["decision_reason"], "required_same_pass_signal_unavailable")
        self.assertEqual(baseline["decision_kind"], "action")
        late = decide(
            model,
            context="late_1",
            current_signals=signals(
                row_eligibility_risk_proxy=None,
                cell_value_risk_proxy=None,
            ),
        )
        self.assertEqual(late["decision_kind"], "abstain")

    def test_zero_or_overflow_predicted_cost_abstains(self) -> None:
        actions = CONTEXT_ACTIONS["anchor"]
        zero = sealed_model(
            full_token_costs={"anchor": {actions[0]: 100, actions[1]: 0, actions[2]: 100}}
        )
        self.assertEqual(decide(zero)["decision_kind"], "abstain")
        overflow = sealed_model(
            full_token_costs={
                "anchor": {
                    actions[0]: MAX_PREDICTED_SYSTEM_TOKENS + 1,
                    actions[1]: 100,
                    actions[2]: 100,
                }
            }
        )
        self.assertEqual(decide(overflow)["decision_kind"], "abstain")

    def test_model_hash_schema_support_and_provenance_fail_closed(self) -> None:
        model = sealed_model()
        self.assertEqual(
            validate_action_model(
                model,
                expected_model_sha256=str(model["model_sha256"]),
                expected_job_manifest_sha256=SHA_B,
            ),
            model,
        )
        with self.assertRaisesRegex(ValueError, "seal"):
            validate_action_model(
                model,
                expected_model_sha256=SHA_D,
                expected_job_manifest_sha256=SHA_B,
            )
        for mutation in ("audit", "authority", "features", "support"):
            broken = copy.deepcopy(model)
            if mutation == "audit":
                broken["audit_outcomes_read"] = True
            elif mutation == "authority":
                broken["controller_or_training_authorized"] = True
            elif mutation == "features":
                broken["full_model"]["feature_keys"] = list(reversed(FEATURE_KEYS))
            else:
                broken["full_model"]["models"]["anchor"][
                    "resolve_anchor"
                ]["fit_records"] = 4
            unsigned = copy.deepcopy(broken)
            unsigned.pop("model_sha256", None)
            broken["model_sha256"] = object_sha256(unsigned)
            with self.assertRaises(ValueError, msg=mutation):
                validate_action_model(
                    broken,
                    expected_model_sha256=str(broken["model_sha256"]),
                    expected_job_manifest_sha256=SHA_B,
                )

    def test_receipt_tamper_fails_even_when_attacker_reseals(self) -> None:
        receipt = decide(sealed_model())
        for field, value in (
            ("selected_action", CONTEXT_ACTIONS["anchor"][1]),
            ("question_text_read_by_controller", True),
            ("mapping_gold_category_question_type_evaluator_score_or_reward_read", True),
        ):
            broken = copy.deepcopy(receipt)
            broken[field] = value
            broken.pop("receipt_sha256")
            broken["receipt_sha256"] = object_sha256(broken)
            with self.assertRaises(ValueError, msg=field):
                validate_decision_receipt(broken)

    def test_module_ast_has_no_io_dynamic_execution_or_privileged_inputs(self) -> None:
        path = ROOT / "src/deepwide_agent/v24211_entropy_controller.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(
            imports.intersection(
                {
                    "os",
                    "pathlib",
                    "subprocess",
                    "socket",
                    "requests",
                    "urllib",
                    "httpx",
                    "clients",
                }
            )
        )
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertFalse(calls.intersection({"open", "eval", "exec", "compile", "__import__"}))
        runtime_parameters = {
            argument.arg
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        }
        self.assertFalse(
            runtime_parameters.intersection(
                {
                    "question",
                    "question_type",
                    "category",
                    "split",
                    "gold",
                    "answer",
                    "mapping",
                    "evaluator",
                    "score",
                    "reward",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
