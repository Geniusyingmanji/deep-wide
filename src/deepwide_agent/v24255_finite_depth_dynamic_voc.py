"""Build-only finite-depth dynamic value-of-computation kernel.

The kernel compares three policies over the same preregistered finite action
graph:

* pure expected information gain;
* one-step terminal-loss value of computation; and
* finite-depth Bellman value of computation.

States and actions are represented only by SHA-256 references and bounded
scalars.  The graph contains the loss incurred by stopping in each state, a
belief-entropy diagnostic, heterogeneous action costs, and calibrated
observation probabilities.  It contains no question, observation text,
benchmark label, answer, evaluator payload, or score.

This module has no file, environment, network, model-client, search-client,
evaluator, subprocess, or runtime surface.  It is not imported by the active
DeepWide forward path and grants no benchmark, training, or publication
authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Mapping


POLICY_ID = "v24255_finite_depth_dynamic_terminal_loss_voc_v1"
MODEL_ROLE = "v24255_calibrated_finite_action_graph"
RECEIPT_ROLE = "v24255_finite_depth_dynamic_voc_receipt"

MAX_STATES = 128
MAX_ACTIONS_PER_STATE = 32
MAX_OUTCOMES_PER_ACTION = 32
MAX_DEPTH = 8
MAX_BUDGET = 1_000_000
PROBABILITY_TOLERANCE = 1e-9
VALUE_PRECISION = 12

FIT_SCOPE = "preregistered_training_or_calibration_only"
TERMINAL_LOSS_DEFINITION = (
    "bounded_four_layer_deepwide_terminal_task_loss_if_stopped_now"
)
ENTROPY_ROLE = (
    "diagnostic_expected_posterior_entropy_not_terminal_utility"
)
TRANSITION_SEMANTICS = (
    "calibrated_probability_of_content_free_successor_state_given_action"
)
COST_TREATMENT = "hard_budget_then_positive_value_per_cost_ranking"
TIE_BREAK = (
    "value_per_cost_desc_gross_value_desc_cost_asc_preregistered_order"
)

PRODUCTION_PACKAGE_AUTHORIZED = False
RUNTIME_FORWARD_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False
BENCHMARK_EVALUATOR_AUTHORIZED = False
LEADERBOARD_OR_SOTA_CLAIM_AUTHORIZED = False

FORBIDDEN_RUNTIME_METADATA_KEYS = frozenset(
    {
        "answer",
        "answerkey",
        "benchmarkcategory",
        "benchmarklabel",
        "benchmarksubset",
        "category",
        "correctness",
        "evaluator",
        "evaluatoroutput",
        "evaluatorpayload",
        "evaluatorscore",
        "finaloutcome",
        "gold",
        "groundtruth",
        "mapping",
        "officialmetrics",
        "prediction",
        "questiontype",
        "resultscsv",
        "reward",
        "score",
        "split",
        "taskcategory",
        "taskid",
        "verifieroutcome",
    }
)

MODEL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "model_fit_manifest_sha256",
        "calibration_protocol_sha256",
        "root_state_ref_sha256",
        "max_depth",
        "max_budget",
        "state_order",
        "states",
        "transition_calibration_complete",
        "missing_calibration_count",
        "terminal_loss_definition",
        "entropy_role",
        "transition_probability_semantics",
        "fit_scope",
        "benchmark_evaluator_gold_mapping_category_question_type_or_score_used",
        "raw_state_action_observation_question_or_id_embedded",
        "production_package_authorized",
        "runtime_forward_authorized",
        "credit_training_authorized",
        "transition_model_sha256",
    }
)
STATE_KEYS = frozenset(
    {
        "state_ref_sha256",
        "stop_terminal_loss",
        "belief_entropy",
        "actions",
    }
)
ACTION_KEYS = frozenset(
    {
        "action_ref_sha256",
        "cost",
        "outcomes",
    }
)
OUTCOME_KEYS = frozenset(
    {
        "next_state_ref_sha256",
        "probability",
        "calibration_ready",
        "calibration_ref_sha256",
    }
)
ACTION_VALUE_KEYS = frozenset(
    {
        "action_ref_sha256",
        "cost",
        "affordable",
        "transition_calibration_complete",
        "expected_entropy_after",
        "pure_information_gain",
        "pure_information_gain_per_cost",
        "expected_stop_terminal_loss_after",
        "myopic_terminal_loss_voc",
        "myopic_terminal_loss_voc_per_cost",
        "expected_dynamic_terminal_loss_after",
        "finite_depth_dynamic_voc",
        "finite_depth_dynamic_voc_per_cost",
        "descendant_option_value",
    }
)
POLICY_RESULT_KEYS = frozenset(
    {
        "objective",
        "decision_kind",
        "selected_action_ref_sha256",
        "decision_reason",
        "selected_gross_value",
        "selected_value_per_cost",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind",
        "build_only",
        "transition_model_sha256",
        "root_state_ref_sha256",
        "requested_depth",
        "available_budget",
        "root_stop_terminal_loss",
        "root_belief_entropy",
        "action_order",
        "action_values",
        "policies",
        "transition_calibration_complete",
        "missing_calibration_count",
        "requested_depth_one_myopic_equivalence",
        "dynamic_voc_includes_descendant_option_value",
        "stop_action_available",
        "cost_treatment",
        "deterministic_tie_break",
        "entropy_is_terminal_utility",
        "raw_state_action_observation_question_or_id_embedded",
        "benchmark_evaluator_gold_mapping_category_question_type_split_score_or_reward_used",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "runtime_forward_training_evaluator_or_leaderboard_authorized",
        "receipt_sha256",
    }
)

POLICY_SPECS = {
    "pure_information_gain": (
        "expected_posterior_entropy_reduction_per_cost",
        "pure_information_gain",
        "pure_information_gain_per_cost",
        "no_strictly_positive_information_gain",
    ),
    "myopic_terminal_loss_voc": (
        "one_step_expected_terminal_loss_reduction_per_cost",
        "myopic_terminal_loss_voc",
        "myopic_terminal_loss_voc_per_cost",
        "no_strictly_positive_myopic_terminal_loss_voc",
    ),
    "finite_depth_dynamic_voc": (
        "bellman_expected_terminal_loss_reduction_per_cost",
        "finite_depth_dynamic_voc",
        "finite_depth_dynamic_voc_per_cost",
        "no_strictly_positive_finite_depth_dynamic_voc",
    ),
}


def object_sha256(value: object) -> str:
    """Return the canonical JSON SHA-256 used by sealed objects."""

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.55 {label} schema is not exact")
    return value


def _integer(
    value: object, *, label: str, minimum: int, maximum: int
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.55 {label} is outside the frozen range")
    return value


def _number(
    value: object, *, label: str, minimum: float, maximum: float
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"V2.42.55 {label} is not finite")
    number = float(value)
    if number < minimum or number > maximum:
        raise ValueError(f"V2.42.55 {label} is outside the frozen range")
    return 0.0 if number == 0.0 else number


def _quantize(value: float) -> float:
    rounded = round(float(value), VALUE_PRECISION)
    return 0.0 if rounded == 0.0 else rounded


def _normalized_metadata_key(value: object) -> str:
    return "".join(
        character for character in str(value).casefold() if character.isalnum()
    )


def reject_privileged_runtime_metadata(value: object) -> None:
    """Recursively reject evaluator-only keys from any proposed graph."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalized_metadata_key(key) in FORBIDDEN_RUNTIME_METADATA_KEYS:
                raise ValueError("V2.42.55 privileged runtime metadata rejected")
            reject_privileged_runtime_metadata(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            reject_privileged_runtime_metadata(nested)


def _normalize_states(
    states: object, *, max_budget: int
) -> tuple[list[dict[str, Any]], dict[str, int | bool]]:
    if not isinstance(states, list) or not 1 <= len(states) <= MAX_STATES:
        raise ValueError("V2.42.55 state count is outside the frozen range")
    reject_privileged_runtime_metadata(states)
    normalized: list[dict[str, Any]] = []
    state_refs: set[str] = set()
    action_refs: set[str] = set()
    missing_calibration_count = 0
    transition_count = 0

    for state_index, raw_state in enumerate(states):
        state = _exact_mapping(
            raw_state, keys=STATE_KEYS, label=f"state {state_index}"
        )
        state_ref = state["state_ref_sha256"]
        if not _is_sha256(state_ref) or state_ref in state_refs:
            raise ValueError("V2.42.55 state reference is invalid or duplicated")
        state_refs.add(str(state_ref))
        loss = _number(
            state["stop_terminal_loss"],
            label="stop terminal loss",
            minimum=0.0,
            maximum=1.0,
        )
        entropy = _number(
            state["belief_entropy"],
            label="belief entropy",
            minimum=0.0,
            maximum=1.0,
        )
        raw_actions = state["actions"]
        if (
            not isinstance(raw_actions, list)
            or len(raw_actions) > MAX_ACTIONS_PER_STATE
        ):
            raise ValueError("V2.42.55 action count is outside the frozen range")
        actions: list[dict[str, Any]] = []
        for action_index, raw_action in enumerate(raw_actions):
            action = _exact_mapping(
                raw_action,
                keys=ACTION_KEYS,
                label=f"action {state_index}/{action_index}",
            )
            action_ref = action["action_ref_sha256"]
            if not _is_sha256(action_ref) or action_ref in action_refs:
                raise ValueError(
                    "V2.42.55 action reference is invalid or duplicated"
                )
            action_refs.add(str(action_ref))
            cost = _integer(
                action["cost"],
                label="action cost",
                minimum=1,
                maximum=max_budget,
            )
            raw_outcomes = action["outcomes"]
            if (
                not isinstance(raw_outcomes, list)
                or not 1 <= len(raw_outcomes) <= MAX_OUTCOMES_PER_ACTION
            ):
                raise ValueError(
                    "V2.42.55 outcome count is outside the frozen range"
                )
            outcomes: list[dict[str, Any]] = []
            next_refs: set[str] = set()
            probabilities: list[float] = []
            for outcome_index, raw_outcome in enumerate(raw_outcomes):
                outcome = _exact_mapping(
                    raw_outcome,
                    keys=OUTCOME_KEYS,
                    label=(
                        f"outcome {state_index}/{action_index}/{outcome_index}"
                    ),
                )
                next_ref = outcome["next_state_ref_sha256"]
                if not _is_sha256(next_ref) or next_ref in next_refs:
                    raise ValueError(
                        "V2.42.55 successor reference is invalid or duplicated"
                    )
                next_refs.add(str(next_ref))
                probability = _number(
                    outcome["probability"],
                    label="transition probability",
                    minimum=0.0,
                    maximum=1.0,
                )
                if probability <= 0.0:
                    raise ValueError(
                        "V2.42.55 transition probability must be positive"
                    )
                calibration_ready = outcome["calibration_ready"]
                calibration_ref = outcome["calibration_ref_sha256"]
                if not isinstance(calibration_ready, bool):
                    raise ValueError(
                        "V2.42.55 calibration readiness is not boolean"
                    )
                if calibration_ready:
                    if not _is_sha256(calibration_ref):
                        raise ValueError(
                            "V2.42.55 calibrated transition lacks a reference"
                        )
                elif calibration_ref is not None:
                    raise ValueError(
                        "V2.42.55 uncalibrated transition has a reference"
                    )
                else:
                    missing_calibration_count += 1
                probabilities.append(probability)
                outcomes.append(
                    {
                        "next_state_ref_sha256": str(next_ref),
                        "probability": probability,
                        "calibration_ready": calibration_ready,
                        "calibration_ref_sha256": calibration_ref,
                    }
                )
                transition_count += 1
            if (
                abs(math.fsum(probabilities) - 1.0)
                > PROBABILITY_TOLERANCE
            ):
                raise ValueError(
                    "V2.42.55 transition probabilities are not normalized"
                )
            actions.append(
                {
                    "action_ref_sha256": str(action_ref),
                    "cost": cost,
                    "outcomes": outcomes,
                }
            )
        normalized.append(
            {
                "state_ref_sha256": str(state_ref),
                "stop_terminal_loss": loss,
                "belief_entropy": entropy,
                "actions": actions,
            }
        )
    return normalized, {
        "missing_calibration_count": missing_calibration_count,
        "transition_calibration_complete": missing_calibration_count == 0,
        "transition_count": transition_count,
    }


def _validate_graph(
    states: list[dict[str, Any]], *, root_state_ref_sha256: str
) -> None:
    state_order = [state["state_ref_sha256"] for state in states]
    state_set = set(state_order)
    if root_state_ref_sha256 not in state_set:
        raise ValueError("V2.42.55 root state is absent")
    edges: dict[str, list[str]] = {state_ref: [] for state_ref in state_order}
    indegree = {state_ref: 0 for state_ref in state_order}
    for state in states:
        source = state["state_ref_sha256"]
        for action in state["actions"]:
            for outcome in action["outcomes"]:
                target = outcome["next_state_ref_sha256"]
                if target not in state_set:
                    raise ValueError("V2.42.55 successor state is absent")
                edges[source].append(target)
                indegree[target] += 1

    reachable = {root_state_ref_sha256}
    frontier = [root_state_ref_sha256]
    while frontier:
        source = frontier.pop()
        for target in edges[source]:
            if target not in reachable:
                reachable.add(target)
                frontier.append(target)
    if reachable != state_set:
        raise ValueError("V2.42.55 graph contains an unreachable state")

    queue = [state_ref for state_ref in state_order if indegree[state_ref] == 0]
    processed = 0
    while queue:
        source = queue.pop(0)
        processed += 1
        for target in edges[source]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if processed != len(state_order):
        raise ValueError("V2.42.55 action graph contains a cycle")


def build_transition_model(
    *,
    model_fit_manifest_sha256: str,
    calibration_protocol_sha256: str,
    root_state_ref_sha256: str,
    max_depth: int,
    max_budget: int,
    states: object,
) -> dict[str, Any]:
    """Build and seal one content-free finite action graph."""

    if (
        not _is_sha256(model_fit_manifest_sha256)
        or not _is_sha256(calibration_protocol_sha256)
        or not _is_sha256(root_state_ref_sha256)
    ):
        raise ValueError("V2.42.55 model identity is not SHA-256 bound")
    depth = _integer(
        max_depth, label="maximum depth", minimum=1, maximum=MAX_DEPTH
    )
    budget = _integer(
        max_budget, label="maximum budget", minimum=1, maximum=MAX_BUDGET
    )
    normalized_states, summary = _normalize_states(states, max_budget=budget)
    _validate_graph(
        normalized_states, root_state_ref_sha256=root_state_ref_sha256
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": MODEL_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "model_fit_manifest_sha256": model_fit_manifest_sha256,
        "calibration_protocol_sha256": calibration_protocol_sha256,
        "root_state_ref_sha256": root_state_ref_sha256,
        "max_depth": depth,
        "max_budget": budget,
        "state_order": [
            state["state_ref_sha256"] for state in normalized_states
        ],
        "states": normalized_states,
        "transition_calibration_complete": summary[
            "transition_calibration_complete"
        ],
        "missing_calibration_count": summary["missing_calibration_count"],
        "terminal_loss_definition": TERMINAL_LOSS_DEFINITION,
        "entropy_role": ENTROPY_ROLE,
        "transition_probability_semantics": TRANSITION_SEMANTICS,
        "fit_scope": FIT_SCOPE,
        "benchmark_evaluator_gold_mapping_category_question_type_or_score_used": False,
        "raw_state_action_observation_question_or_id_embedded": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "runtime_forward_authorized": RUNTIME_FORWARD_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
    }
    value["transition_model_sha256"] = object_sha256(value)
    return validate_transition_model(
        value,
        expected_transition_model_sha256=value["transition_model_sha256"],
    )


def validate_transition_model(
    value: object, *, expected_transition_model_sha256: str
) -> dict[str, Any]:
    """Validate a graph, its outer binding, topology, and calibration flags."""

    if not _is_sha256(expected_transition_model_sha256):
        raise ValueError("V2.42.55 expected model binding is invalid")
    model = _exact_mapping(value, keys=MODEL_KEYS, label="transition model")
    reject_privileged_runtime_metadata(model["states"])
    unsigned = dict(model)
    seal = unsigned.pop("transition_model_sha256", None)
    if (
        _integer(
            model["artifact_version"],
            label="artifact version",
            minimum=1,
            maximum=1,
        )
        != 1
        or model["role"] != MODEL_ROLE
        or model["policy_id"] != POLICY_ID
        or model["build_only"] is not True
        or seal != expected_transition_model_sha256
        or seal != object_sha256(unsigned)
        or not _is_sha256(model["model_fit_manifest_sha256"])
        or not _is_sha256(model["calibration_protocol_sha256"])
        or not _is_sha256(model["root_state_ref_sha256"])
        or model["terminal_loss_definition"] != TERMINAL_LOSS_DEFINITION
        or model["entropy_role"] != ENTROPY_ROLE
        or model["transition_probability_semantics"] != TRANSITION_SEMANTICS
        or model["fit_scope"] != FIT_SCOPE
        or model[
            "benchmark_evaluator_gold_mapping_category_question_type_or_score_used"
        ]
        is not False
        or model["raw_state_action_observation_question_or_id_embedded"]
        is not False
        or model["production_package_authorized"] is not False
        or model["runtime_forward_authorized"] is not False
        or model["credit_training_authorized"] is not False
    ):
        raise ValueError("V2.42.55 model seal or safety contract drifted")
    depth = _integer(
        model["max_depth"],
        label="maximum depth",
        minimum=1,
        maximum=MAX_DEPTH,
    )
    budget = _integer(
        model["max_budget"],
        label="maximum budget",
        minimum=1,
        maximum=MAX_BUDGET,
    )
    normalized_states, summary = _normalize_states(
        model["states"], max_budget=budget
    )
    missing_calibration_count = _integer(
        model["missing_calibration_count"],
        label="missing calibration count",
        minimum=0,
        maximum=int(summary["transition_count"]),
    )
    _validate_graph(
        normalized_states,
        root_state_ref_sha256=str(model["root_state_ref_sha256"]),
    )
    if (
        depth != model["max_depth"]
        or budget != model["max_budget"]
        or object_sha256(model["states"]) != object_sha256(normalized_states)
        or model["state_order"]
        != [state["state_ref_sha256"] for state in normalized_states]
        or not isinstance(model["transition_calibration_complete"], bool)
        or model["transition_calibration_complete"]
        is not summary["transition_calibration_complete"]
        or missing_calibration_count
        != summary["missing_calibration_count"]
    ):
        raise ValueError("V2.42.55 model graph summary drifted")
    return copy.deepcopy(dict(model))


def _state_map(model: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        state["state_ref_sha256"]: state
        for state in model["states"]
    }


def _action_is_calibrated(action: Mapping[str, Any]) -> bool:
    return all(
        outcome["calibration_ready"] is True
        and _is_sha256(outcome["calibration_ref_sha256"])
        for outcome in action["outcomes"]
    )


def _bellman_terminal_loss(
    *,
    states: Mapping[str, Mapping[str, Any]],
    state_ref_sha256: str,
    depth: int,
    budget: int,
    memo: dict[tuple[str, int, int], float],
) -> float:
    key = (state_ref_sha256, depth, budget)
    if key in memo:
        return memo[key]
    state = states[state_ref_sha256]
    best_loss = _quantize(state["stop_terminal_loss"])
    if depth > 0:
        for action in state["actions"]:
            cost = action["cost"]
            if cost > budget:
                continue
            expected = _quantize(
                math.fsum(
                    outcome["probability"]
                    * _bellman_terminal_loss(
                        states=states,
                        state_ref_sha256=outcome[
                            "next_state_ref_sha256"
                        ],
                        depth=depth - 1,
                        budget=budget - cost,
                        memo=memo,
                    )
                    for outcome in action["outcomes"]
                )
            )
            if expected < best_loss:
                best_loss = expected
    memo[key] = best_loss
    return best_loss


def _policy_result(
    *,
    policy_name: str,
    action_order: list[str],
    action_values: Mapping[str, Mapping[str, Any]],
    calibration_complete: bool,
) -> dict[str, Any]:
    objective, gross_key, ratio_key, no_positive_reason = POLICY_SPECS[
        policy_name
    ]
    if not calibration_complete:
        return {
            "objective": objective,
            "decision_kind": "abstain",
            "selected_action_ref_sha256": None,
            "decision_reason": "transition_probability_calibration_incomplete",
            "selected_gross_value": None,
            "selected_value_per_cost": None,
        }
    affordable = [
        action_ref
        for action_ref in action_order
        if action_values[action_ref]["affordable"] is True
    ]
    if not action_order:
        return {
            "objective": objective,
            "decision_kind": "stop",
            "selected_action_ref_sha256": None,
            "decision_reason": "no_registered_action",
            "selected_gross_value": None,
            "selected_value_per_cost": None,
        }
    if not affordable:
        return {
            "objective": objective,
            "decision_kind": "stop",
            "selected_action_ref_sha256": None,
            "decision_reason": "no_affordable_action_within_budget",
            "selected_gross_value": None,
            "selected_value_per_cost": None,
        }
    beneficial = [
        action_ref
        for action_ref in affordable
        if action_values[action_ref][gross_key] is not None
        and action_values[action_ref][gross_key] > 0.0
    ]
    if not beneficial:
        return {
            "objective": objective,
            "decision_kind": "stop",
            "selected_action_ref_sha256": None,
            "decision_reason": no_positive_reason,
            "selected_gross_value": None,
            "selected_value_per_cost": None,
        }
    rank = {
        action_ref: index for index, action_ref in enumerate(action_order)
    }
    selected = min(
        beneficial,
        key=lambda action_ref: (
            -float(action_values[action_ref][ratio_key]),
            -float(action_values[action_ref][gross_key]),
            int(action_values[action_ref]["cost"]),
            rank[action_ref],
        ),
    )
    return {
        "objective": objective,
        "decision_kind": "action",
        "selected_action_ref_sha256": selected,
        "decision_reason": "maximum_strictly_positive_value_per_cost",
        "selected_gross_value": action_values[selected][gross_key],
        "selected_value_per_cost": action_values[selected][ratio_key],
    }


def _evaluate_clean(
    *,
    model: Mapping[str, Any],
    requested_depth: int,
    available_budget: int,
) -> dict[str, Any]:
    states = _state_map(model)
    root = states[model["root_state_ref_sha256"]]
    action_order = [
        action["action_ref_sha256"] for action in root["actions"]
    ]
    calibration_complete = model["transition_calibration_complete"] is True
    values: dict[str, dict[str, Any]] = {}
    memo: dict[tuple[str, int, int], float] = {}

    for action in root["actions"]:
        action_ref = action["action_ref_sha256"]
        cost = action["cost"]
        affordable = cost <= available_budget
        action_calibrated = _action_is_calibrated(action)
        row: dict[str, Any] = {
            "action_ref_sha256": action_ref,
            "cost": cost,
            "affordable": affordable,
            "transition_calibration_complete": action_calibrated,
            "expected_entropy_after": None,
            "pure_information_gain": None,
            "pure_information_gain_per_cost": None,
            "expected_stop_terminal_loss_after": None,
            "myopic_terminal_loss_voc": None,
            "myopic_terminal_loss_voc_per_cost": None,
            "expected_dynamic_terminal_loss_after": None,
            "finite_depth_dynamic_voc": None,
            "finite_depth_dynamic_voc_per_cost": None,
            "descendant_option_value": None,
        }
        if calibration_complete:
            expected_entropy = _quantize(
                math.fsum(
                    outcome["probability"]
                    * states[outcome["next_state_ref_sha256"]][
                        "belief_entropy"
                    ]
                    for outcome in action["outcomes"]
                )
            )
            expected_stop_loss = _quantize(
                math.fsum(
                    outcome["probability"]
                    * states[outcome["next_state_ref_sha256"]][
                        "stop_terminal_loss"
                    ]
                    for outcome in action["outcomes"]
                )
            )
            information_gain = _quantize(
                root["belief_entropy"] - expected_entropy
            )
            myopic_voc = _quantize(
                root["stop_terminal_loss"] - expected_stop_loss
            )
            row.update(
                {
                    "expected_entropy_after": expected_entropy,
                    "pure_information_gain": information_gain,
                    "pure_information_gain_per_cost": _quantize(
                        information_gain / cost
                    ),
                    "expected_stop_terminal_loss_after": expected_stop_loss,
                    "myopic_terminal_loss_voc": myopic_voc,
                    "myopic_terminal_loss_voc_per_cost": _quantize(
                        myopic_voc / cost
                    ),
                }
            )
            if affordable:
                expected_dynamic_loss = _quantize(
                    math.fsum(
                        outcome["probability"]
                        * _bellman_terminal_loss(
                            states=states,
                            state_ref_sha256=outcome[
                                "next_state_ref_sha256"
                            ],
                            depth=requested_depth - 1,
                            budget=available_budget - cost,
                            memo=memo,
                        )
                        for outcome in action["outcomes"]
                    )
                )
                dynamic_voc = _quantize(
                    root["stop_terminal_loss"] - expected_dynamic_loss
                )
                option_value = _quantize(dynamic_voc - myopic_voc)
                if option_value < 0.0 and abs(option_value) <= 10 ** (
                    -VALUE_PRECISION
                ):
                    option_value = 0.0
                row.update(
                    {
                        "expected_dynamic_terminal_loss_after": (
                            expected_dynamic_loss
                        ),
                        "finite_depth_dynamic_voc": dynamic_voc,
                        "finite_depth_dynamic_voc_per_cost": _quantize(
                            dynamic_voc / cost
                        ),
                        "descendant_option_value": option_value,
                    }
                )
        values[action_ref] = row

    policies = {
        policy_name: _policy_result(
            policy_name=policy_name,
            action_order=action_order,
            action_values=values,
            calibration_complete=calibration_complete,
        )
        for policy_name in POLICY_SPECS
    }
    depth_one_equivalence: bool | None = None
    if requested_depth == 1 and calibration_complete:
        depth_one_equivalence = all(
            (
                values[action_ref]["finite_depth_dynamic_voc"]
                == values[action_ref]["myopic_terminal_loss_voc"]
                if values[action_ref]["affordable"]
                else values[action_ref]["finite_depth_dynamic_voc"] is None
            )
            for action_ref in action_order
        ) and (
            policies["finite_depth_dynamic_voc"][
                "selected_action_ref_sha256"
            ]
            == policies["myopic_terminal_loss_voc"][
                "selected_action_ref_sha256"
            ]
        )

    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "label_blind": True,
        "build_only": True,
        "transition_model_sha256": model["transition_model_sha256"],
        "root_state_ref_sha256": model["root_state_ref_sha256"],
        "requested_depth": requested_depth,
        "available_budget": available_budget,
        "root_stop_terminal_loss": root["stop_terminal_loss"],
        "root_belief_entropy": root["belief_entropy"],
        "action_order": action_order,
        "action_values": values,
        "policies": policies,
        "transition_calibration_complete": calibration_complete,
        "missing_calibration_count": model["missing_calibration_count"],
        "requested_depth_one_myopic_equivalence": depth_one_equivalence,
        "dynamic_voc_includes_descendant_option_value": True,
        "stop_action_available": True,
        "cost_treatment": COST_TREATMENT,
        "deterministic_tie_break": TIE_BREAK,
        "entropy_is_terminal_utility": False,
        "raw_state_action_observation_question_or_id_embedded": False,
        "benchmark_evaluator_gold_mapping_category_question_type_split_score_or_reward_used": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "runtime_forward_training_evaluator_or_leaderboard_authorized": False,
    }
    receipt["receipt_sha256"] = object_sha256(receipt)
    return receipt


def evaluate_voc_policies(
    *,
    model: object,
    expected_transition_model_sha256: str,
    requested_depth: int,
    available_budget: int,
) -> dict[str, Any]:
    """Evaluate the three policies and return one sealed content-free receipt."""

    clean = validate_transition_model(
        model,
        expected_transition_model_sha256=expected_transition_model_sha256,
    )
    depth = _integer(
        requested_depth,
        label="requested depth",
        minimum=1,
        maximum=clean["max_depth"],
    )
    budget = _integer(
        available_budget,
        label="available budget",
        minimum=0,
        maximum=clean["max_budget"],
    )
    receipt = _evaluate_clean(
        model=clean,
        requested_depth=depth,
        available_budget=budget,
    )
    return validate_planning_receipt(
        receipt,
        model=clean,
        expected_transition_model_sha256=expected_transition_model_sha256,
    )


def validate_planning_receipt(
    receipt: object,
    *,
    model: object,
    expected_transition_model_sha256: str,
) -> dict[str, Any]:
    """Replay a receipt from its exact sealed transition model."""

    clean = validate_transition_model(
        model,
        expected_transition_model_sha256=expected_transition_model_sha256,
    )
    value = _exact_mapping(receipt, keys=RECEIPT_KEYS, label="receipt")
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    if (
        seal != object_sha256(unsigned)
        or value["artifact_version"] != 1
        or value["role"] != RECEIPT_ROLE
        or value["policy_id"] != POLICY_ID
        or value["label_blind"] is not True
        or value["build_only"] is not True
        or value["transition_model_sha256"]
        != expected_transition_model_sha256
        or value["root_state_ref_sha256"]
        != clean["root_state_ref_sha256"]
        or value["entropy_is_terminal_utility"] is not False
        or value["raw_state_action_observation_question_or_id_embedded"]
        is not False
        or value[
            "benchmark_evaluator_gold_mapping_category_question_type_split_score_or_reward_used"
        ]
        is not False
        or value[
            "file_environment_network_model_search_fetch_or_process_accessed"
        ]
        is not False
        or value[
            "runtime_forward_training_evaluator_or_leaderboard_authorized"
        ]
        is not False
    ):
        raise ValueError("V2.42.55 receipt seal or safety contract drifted")
    depth = _integer(
        value["requested_depth"],
        label="receipt depth",
        minimum=1,
        maximum=clean["max_depth"],
    )
    budget = _integer(
        value["available_budget"],
        label="receipt budget",
        minimum=0,
        maximum=clean["max_budget"],
    )
    expected = _evaluate_clean(
        model=clean,
        requested_depth=depth,
        available_budget=budget,
    )
    if object_sha256(dict(value)) != object_sha256(expected):
        raise ValueError("V2.42.55 receipt replay drifted")
    if (
        set(value["action_values"]) != set(value["action_order"])
        or any(
            set(row) != ACTION_VALUE_KEYS
            for row in value["action_values"].values()
        )
        or set(value["policies"]) != set(POLICY_SPECS)
        or any(
            set(row) != POLICY_RESULT_KEYS
            for row in value["policies"].values()
        )
    ):
        raise ValueError("V2.42.55 receipt nested schema drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "BENCHMARK_EVALUATOR_AUTHORIZED",
    "COST_TREATMENT",
    "CREDIT_TRAINING_AUTHORIZED",
    "LEADERBOARD_OR_SOTA_CLAIM_AUTHORIZED",
    "MAX_BUDGET",
    "MAX_DEPTH",
    "MODEL_ROLE",
    "POLICY_ID",
    "PRODUCTION_PACKAGE_AUTHORIZED",
    "RECEIPT_ROLE",
    "RUNTIME_FORWARD_AUTHORIZED",
    "TIE_BREAK",
    "build_transition_model",
    "evaluate_voc_policies",
    "object_sha256",
    "reject_privileged_runtime_metadata",
    "validate_planning_receipt",
    "validate_transition_model",
]
