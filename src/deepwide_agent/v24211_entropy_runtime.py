"""Runtime bridge for the V2.42.11 entropy decision kernel.

This module closes the policy-to-action boundary without reading files,
environment variables, benchmark labels, or evaluator artifacts.  At one of
the three frozen same-pass decision stages it:

1. projects the current four-layer shadow snapshot;
2. obtains a sealed action/stop/abstain decision from the pure kernel;
3. for an action, executes exactly the historical two-query retrieval
   observation and applies the V2.41.22 provenance-preserving state adapter;
4. restarts the ordinary idempotent stage runner from its top so every
   invalidated suffix is recomputed before downstream use.

The bridge consumes its model and immutable parent bindings as constructor
objects.  Candidate publishers and launch freezes remain responsible for
loading and hash-binding those objects.  The historical projection-only arm is
never called.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .v24121_continuation import execute_retrieval_observation
from .v24122_execution import (
    V24122TrueContinuationRuntime,
    prepare_v24122_matched_branch_states,
)
from .v24211_entropy_controller import (
    POLICY_ID,
    decide_entropy_action,
    object_sha256,
    validate_action_model,
    validate_decision_receipt,
)


RUNTIME_POLICY_ID = "v24211_entropy_runtime_bridge_v1"
RUNTIME_RECEIPT_ROLE = "v24211_entropy_runtime_transition_receipt"
# This implementation is deliberately not a launch grant.  A future sealed
# package publisher must replace this source-level negative assertion with an
# immutable package receipt that binds the selected parent, model, runner and
# preflight bytes before any benchmark process can instantiate the runtime.
PRODUCTION_PACKAGE_AUTHORIZED = False
DECISION_STAGES = {
    "after_initial_belief": "anchor",
    "bridge_after_initial_belief": "anchor",
    "downstream_after_initial_belief": "anchor",
    "after_candidate_discovery": "late_0",
    "after_row_enrichment": "late_1",
}
CONTEXT_ORDER = ("anchor", "late_0", "late_1")
RUNTIME_TRANSITION_KEYS = {
    "artifact_version",
    "role",
    "runtime_policy_id",
    "context",
    "decision_kind",
    "selected_action",
    "decision_receipt",
    "decision_receipt_sha256",
    "pre_action_state_sha256",
    "action_observation_sha256",
    "action_observation_receipt_sha256",
    "action_adapter_receipt_sha256",
    "post_action_state_before_controller_ledger_sha256",
    "state_mutated_by_action",
    "projection_only_action_arm_called",
    "mapping_gold_category_question_type_evaluator_score_or_reward_read",
    "runtime_transition_sha256",
}


class EntropyControllerRestart(RuntimeError):
    """Internal control-flow marker after a real action changes runtime state."""


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value).issubset(set("0123456789abcdef"))
    )


def _signals(snapshot: dict[str, Any]) -> dict[str, float | None]:
    raw = snapshot.get("raw_risk_vector")
    anchor = snapshot.get("anchor")
    if not isinstance(raw, dict) or not isinstance(anchor, dict):
        raise ValueError("V2.42.11 shadow snapshot lacks controller signals")
    return {
        "anchor_risk_proxy": raw.get("anchor_other_mass"),
        "coverage_risk_proxy": raw.get("coverage_unseen_mass_proxy"),
        "row_eligibility_risk_proxy": raw.get("row_unresolved_rate"),
        "cell_value_risk_proxy": raw.get("cell_uncertain_rate"),
        "anchor_normalized_entropy": anchor.get("normalized_entropy"),
    }


class V24211EntropyRuntime(V24122TrueContinuationRuntime):
    """Ordinary DeepWide runtime plus at most one action per frozen context."""

    def __init__(
        self,
        *args: Any,
        entropy_action_model: dict[str, Any],
        entropy_action_model_sha256: str,
        entropy_action_model_job_manifest_sha256: str,
        entropy_selected_parent_manifest_sha256: str,
        entropy_policy_branch: str = "full_entropy",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if (
            entropy_policy_branch not in {"full_entropy", "no_entropy"}
            or not _is_sha256(entropy_action_model_sha256)
            or not _is_sha256(entropy_action_model_job_manifest_sha256)
            or not _is_sha256(entropy_selected_parent_manifest_sha256)
        ):
            raise ValueError("V2.42.11 runtime controller binding is invalid")
        # Validate once before any forward state can be observed.  The pure
        # kernel validates again at each decision, so both constructor-time
        # substitution and later in-memory mutation fail closed.
        self._v24211_model = validate_action_model(
            entropy_action_model,
            expected_model_sha256=entropy_action_model_sha256,
            expected_job_manifest_sha256=(
                entropy_action_model_job_manifest_sha256
            ),
        )
        self._v24211_model_sha256 = entropy_action_model_sha256
        self._v24211_job_manifest_sha256 = (
            entropy_action_model_job_manifest_sha256
        )
        self._v24211_parent_manifest_sha256 = (
            entropy_selected_parent_manifest_sha256
        )
        self._v24211_policy_branch = entropy_policy_branch
        self._v24211_active_question: str | None = None
        self._v24211_in_controller_retrieval = False

    def _v24211_attempted_contexts(self, state: dict[str, Any]) -> set[str]:
        rows = state.get("v24211_entropy_decisions")
        if rows is None:
            return set()
        if not isinstance(rows, list):
            raise ValueError("V2.42.11 decision ledger is invalid")
        task_ref = hashlib.sha256(
            f"{POLICY_ID}|task|{state.get('opaque_id', '')}".encode("utf-8")
        ).hexdigest()
        for index, row in enumerate(rows):
            if (
                not isinstance(row, dict)
                or set(row) != RUNTIME_TRANSITION_KEYS
                or row.get("artifact_version") != 1
                or row.get("role") != RUNTIME_RECEIPT_ROLE
                or row.get("runtime_policy_id") != RUNTIME_POLICY_ID
                or row.get("projection_only_action_arm_called") is not False
                or row.get(
                    "mapping_gold_category_question_type_evaluator_score_or_reward_read"
                )
                is not False
                or row.get("runtime_transition_sha256")
                != object_sha256(
                    {
                        key: value
                        for key, value in row.items()
                        if key != "runtime_transition_sha256"
                    }
                )
            ):
                raise ValueError("V2.42.11 transition receipt seal drifted")
            try:
                receipt = validate_decision_receipt(row.get("decision_receipt"))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "V2.42.11 nested decision receipt drifted"
                ) from exc
            if (
                row.get("decision_receipt_sha256")
                != receipt["receipt_sha256"]
                or row.get("context") != receipt["context"]
                or row.get("decision_kind") != receipt["decision_kind"]
                or row.get("selected_action") != receipt["selected_action"]
                or row.get("pre_action_state_sha256")
                != receipt["pre_action_state_sha256"]
                or receipt["decision_index"] != index
                or receipt["opaque_task_ref_sha256"] != task_ref
                or receipt["policy_branch"] != self._v24211_policy_branch
                or receipt["action_model_sha256"] != self._v24211_model_sha256
                or receipt["action_model_job_manifest_sha256"]
                != self._v24211_job_manifest_sha256
                or receipt["selected_parent_manifest_sha256"]
                != self._v24211_parent_manifest_sha256
            ):
                raise ValueError("V2.42.11 transition/decision binding drifted")
            action_taken = receipt["decision_kind"] == "action"
            action_hashes = (
                row.get("action_observation_sha256"),
                row.get("action_observation_receipt_sha256"),
                row.get("action_adapter_receipt_sha256"),
            )
            if action_taken:
                if (
                    row.get("state_mutated_by_action") is not True
                    or not all(_is_sha256(value) for value in action_hashes)
                    or not _is_sha256(
                        row.get(
                            "post_action_state_before_controller_ledger_sha256"
                        )
                    )
                ):
                    raise ValueError("V2.42.11 action transition is incomplete")
            elif (
                row.get("state_mutated_by_action") is not False
                or any(value is not None for value in action_hashes)
                or row.get("post_action_state_before_controller_ledger_sha256")
                != row.get("pre_action_state_sha256")
            ):
                raise ValueError("V2.42.11 no-action transition drifted")
        contexts = [str(row.get("context", "")) for row in rows]
        if any(context not in CONTEXT_ORDER for context in contexts):
            raise ValueError("V2.42.11 decision ledger context drifted")
        if len(contexts) != len(set(contexts)):
            raise ValueError("V2.42.11 context was decided more than once")
        indices = [CONTEXT_ORDER.index(context) for context in contexts]
        if indices != sorted(indices):
            raise ValueError("V2.42.11 decision ledger order drifted")
        return set(contexts)

    def _v24211_apply_decision(
        self,
        state: dict[str, Any],
        snapshot: dict[str, Any],
        *,
        context: str,
    ) -> bool:
        attempted = self._v24211_attempted_contexts(state)
        if context in attempted:
            return False
        question = self._v24211_active_question
        if not isinstance(question, str) or not question:
            raise RuntimeError("V2.42.11 active visible question is unavailable")
        ledger = state.setdefault("v24211_entropy_decisions", [])
        pre_action_state_sha256 = object_sha256(state)
        task_ref = hashlib.sha256(
            f"{POLICY_ID}|task|{state.get('opaque_id', '')}".encode("utf-8")
        ).hexdigest()
        receipt = decide_entropy_action(
            model=self._v24211_model,
            expected_model_sha256=self._v24211_model_sha256,
            expected_job_manifest_sha256=self._v24211_job_manifest_sha256,
            signals=_signals(snapshot),
            context=context,
            policy_branch=self._v24211_policy_branch,
            opaque_task_ref_sha256=task_ref,
            decision_index=len(ledger),
            pre_action_state_sha256=pre_action_state_sha256,
            selected_parent_manifest_sha256=self._v24211_parent_manifest_sha256,
        )
        transition: dict[str, Any] = {
            "artifact_version": 1,
            "role": RUNTIME_RECEIPT_ROLE,
            "runtime_policy_id": RUNTIME_POLICY_ID,
            "context": context,
            "decision_kind": receipt["decision_kind"],
            "selected_action": receipt["selected_action"],
            "decision_receipt": receipt,
            "decision_receipt_sha256": receipt["receipt_sha256"],
            "pre_action_state_sha256": pre_action_state_sha256,
            "action_observation_sha256": None,
            "action_observation_receipt_sha256": None,
            "action_adapter_receipt_sha256": None,
            "post_action_state_before_controller_ledger_sha256": (
                pre_action_state_sha256
            ),
            "state_mutated_by_action": False,
            "projection_only_action_arm_called": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        }
        if receipt["decision_kind"] != "action":
            transition["runtime_transition_sha256"] = object_sha256(transition)
            ledger.append(transition)
            self._save(state)
            return False

        action = str(receipt["selected_action"])
        self._v24211_in_controller_retrieval = True
        try:
            observation, observation_receipt = execute_retrieval_observation(
                search=self.search,
                source_state=state,
                source_checkpoint_sha256=pre_action_state_sha256,
                snapshot=snapshot,
                context=context,
                action=action,
            )
        finally:
            self._v24211_in_controller_retrieval = False
        prepared = prepare_v24122_matched_branch_states(
            source_state=state,
            source_checkpoint_sha256=pre_action_state_sha256,
            observation_artifact=observation,
            observation_receipt=observation_receipt,
            replicate_id=0,
            continuation_policy_sha256=self._v24211_parent_manifest_sha256,
        )
        action_state = prepared["action"]
        if action_state.get("opaque_id") != state.get("opaque_id"):
            raise RuntimeError("V2.42.11 action adapter changed opaque identity")
        transition["action_observation_sha256"] = observation[
            "artifact_payload_sha256"
        ]
        transition["action_observation_receipt_sha256"] = observation_receipt[
            "receipt_payload_sha256"
        ]
        transition["action_adapter_receipt_sha256"] = prepared["receipt"][
            "receipt_payload_sha256"
        ]
        transition["post_action_state_before_controller_ledger_sha256"] = (
            object_sha256(action_state)
        )
        transition["state_mutated_by_action"] = True
        transition["runtime_transition_sha256"] = object_sha256(transition)
        action_state["v24211_entropy_decisions"] = [*ledger, transition]
        action_state["v24211_runtime_policy_id"] = RUNTIME_POLICY_ID
        state.clear()
        state.update(action_state)
        self._save(state)
        return True

    def _record_shadow(self, state: dict[str, Any], stage: str) -> None:
        super()._record_shadow(state, stage)
        context = DECISION_STAGES.get(stage)
        if context is None or self._v24211_in_controller_retrieval:
            return
        snapshots = [
            row
            for row in state.get("shadow_risk_snapshots", [])
            if isinstance(row, dict) and row.get("stage") == stage
        ]
        if len(snapshots) != 1:
            raise RuntimeError("V2.42.11 cannot bind the persisted shadow stage")
        if self._v24211_apply_decision(state, snapshots[0], context=context):
            raise EntropyControllerRestart(context)

    def _run_task_stages(
        self,
        state: dict[str, Any],
        question: str,
        checkpoint_wall_time: Any,
    ) -> dict[str, Any]:
        if self._v24211_active_question is not None:
            raise RuntimeError("V2.42.11 runtime is not reentrant across tasks")
        self._v24211_active_question = question
        try:
            # Three contexts are the absolute maximum, so four restarts imply
            # duplicate or unregistered control flow and fail closed.
            for _ in range(len(CONTEXT_ORDER) + 1):
                try:
                    return super()._run_task_stages(
                        state, question, checkpoint_wall_time
                    )
                except EntropyControllerRestart:
                    continue
            raise RuntimeError("V2.42.11 controller restart bound exceeded")
        finally:
            self._v24211_active_question = None


__all__ = [
    "CONTEXT_ORDER",
    "DECISION_STAGES",
    "EntropyControllerRestart",
    "PRODUCTION_PACKAGE_AUTHORIZED",
    "RUNTIME_POLICY_ID",
    "RUNTIME_RECEIPT_ROLE",
    "V24211EntropyRuntime",
]
