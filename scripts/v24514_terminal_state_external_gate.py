#!/usr/bin/env python3
"""Fresh one-wave gate for proof-derived absolute terminal decision state.

V2.45.12 measured record-stage deltas and therefore could not distinguish a
complete failure from an earlier targeted/reserve success that the record
stage merely preserved.  This successor keeps the frozen V2.45.11 worker and
all source-credit thresholds, but aggregates V2.45.13 absolute terminal state.

The new 64-entity population is literal/canonical disjoint from all 340 prior
external questions and 2,720 entities.  No prior population is rerun.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from deepwide_agent import (  # noqa: E402
    v24513_terminal_record_bound_projection as terminal,
)
from scripts import v24512_proposal_seeded_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24514_fresh_terminal_state_proposal_seeded_external_gate_v1"
PROTOCOL = Path(f"results/v24514_terminal_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(
    f"results/v24514_terminal_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(f"results/v24514_terminal_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24514_terminal_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24514_terminal_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24514_terminal_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24514_terminal_external_postresult_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24513_terminal_projection_build_audit_v1_{DATE}.json"
)
RUNNER_MARKER = "scripts/v24514_terminal_state_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_terminal_state_proposal_seeded_external_gate"
PRIOR_QUESTION_COUNT = 340
PRIOR_ENTITY_COUNT = 2720
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS
PREVIOUS_RESULT = predecessor.RESULT
PREVIOUS_DECISION = predecessor.DECISION
PREVIOUS_POSTAUDIT = predecessor.POSTAUDIT
PREVIOUS_PROTOCOL_ID = predecessor.PROTOCOL_ID
ENTITY_GROUPS = (
    (
        "College of Wooster",
        "Knox College",
        "Beloit College",
        "Grinnell College",
        "Coe College",
        "Cornell College",
        "Luther College",
        "Wartburg College",
    ),
    (
        "Whitman College",
        "Willamette University",
        "University of Puget Sound",
        "Lewis & Clark College",
        "Reed College",
        "Linfield University",
        "Pacific University",
        "George Fox University",
    ),
    (
        "Agnes Scott College",
        "Spelman College",
        "Morehouse College",
        "Oglethorpe University",
        "Berry College",
        "Mercer University",
        "Furman University",
        "Wofford College",
    ),
    (
        "Allegheny College",
        "Juniata College",
        "Gettysburg College",
        "Dickinson College",
        "Franklin & Marshall College",
        "Ursinus College",
        "Muhlenberg College",
        "Lafayette College",
    ),
    (
        "Hobart and William Smith Colleges",
        "St. Lawrence University",
        "Clarkson University",
        "Siena College",
        "Skidmore College",
        "Union College",
        "Hartwick College",
        "Ithaca College",
    ),
    (
        "Lake Forest College",
        "Illinois College",
        "Monmouth College",
        "Augustana College",
        "North Central College",
        "Wheaton College",
        "Elmhurst University",
        "Millikin University",
    ),
    (
        "Hólar University College",
        "University of Eastern Finland",
        "University of Liechtenstein",
        "University of Andorra",
        "University of the Faroe Islands",
        "Ilisimatusarfik",
        "University of Antsiranana",
        "University of Cape Verde",
    ),
    (
        "Royal University of Bhutan",
        "Sherubtse College",
        "Jigme Namgyel Engineering College",
        "University of the Ryukyus",
        "Ochanomizu University",
        "Tokyo University of Foreign Studies",
        "Hitotsubashi University",
        "Nara Women's University",
    ),
)


def _question(group: tuple[str, ...]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.14 entity group drifted")
    return (
        "Use public web sources to return one Markdown table about "
        + ", ".join(group[:-1])
        + ", and "
        + group[-1]
        + ". The column names are: University, Founding year. Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)
GATES = {
    "minimum_worker_success_tasks": 8,
    "maximum_worker_hard_timeout_tasks": 0,
    "maximum_worker_nonzero_tasks": 0,
    "minimum_complete_validation_returned_tasks": 8,
    "minimum_target_plan_tasks": 1,
    "minimum_reserve_engaged_tasks": 1,
    "minimum_reserve_usable_page_tasks": 1,
    "minimum_terminal_safe_change_tasks": 1,
    "minimum_terminal_positive_decision_credit_tasks": 1,
    "minimum_total_terminal_decision_credit_nats": 1e-12,
    "maximum_safe_change_regression_tasks": 0,
    "maximum_total_safe_change_regression_count": 0,
    "maximum_decision_credit_regression_tasks": 0,
    "maximum_total_decision_credit_regression_nats": 0.0,
    "maximum_additional_external_effects": 0,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 3,
    "maximum_fetch_helper_failures": 3,
    "maximum_parent_validation_p95_seconds": 1.0,
}
SOURCE_FILES = (
    *predecessor.SOURCE_FILES,
    "src/deepwide_agent/v24513_terminal_record_bound_projection.py",
    "tests/test_v24513_terminal_record_bound_projection.py",
    "scripts/audit_v24513_terminal_projection_build.py",
    "tests/test_audit_v24513_terminal_projection_build.py",
    str(PARENT),
    str(PREVIOUS_RESULT),
    str(PREVIOUS_DECISION),
    str(PREVIOUS_POSTAUDIT),
    RUNNER_MARKER,
    "tests/test_v24514_terminal_state_external_gate.py",
)
TEST_SUITES = (
    ("tests/test_v24511_proposal_seeded_record_bound_worker.py", 4, 180),
    ("tests/test_v24513_terminal_record_bound_projection.py", 7, 180),
    ("tests/test_v24506_record_bound_external_gate.py", 9, 240),
    ("tests/test_v24512_proposal_seeded_external_gate.py", 9, 240),
    ("tests/test_v24514_terminal_state_external_gate.py", 11, 240),
)
EXPECTED_TEST_COUNT = 40


_ORIGINAL_PATCHED_CORE = predecessor._patched_core
_ORIGINAL_VALIDATE_PROTOCOL = predecessor.validate_protocol
_ORIGINAL_VALIDATE_PREAUDIT = predecessor.validate_preaudit
_ORIGINAL_VALIDATE_ACTIVATION = predecessor.validate_activation
_ORIGINAL_VALIDATE_EXECUTION_START = predecessor.validate_execution_start


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.14 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _prior_questions() -> tuple[str, ...]:
    return PRIOR_QUESTIONS


def _fresh_entity_vector_valid() -> bool:
    parser = (
        predecessor.predecessor.reserve_history.base.history.history.previous_gate.history.history.history.parent
    )
    current = {
        entity
        for question in QUESTIONS
        for entity in parser._question_entity_vector(question)
    }
    prior = {
        entity
        for question in _prior_questions()
        for entity in parser._question_entity_vector(question)
    }
    current_canonical = {parser._canonical_entity(item) for item in current}
    prior_canonical = {parser._canonical_entity(item) for item in prior}
    return (
        len(QUESTIONS) == 8
        and len(current) == 64
        and len(current_canonical) == 64
        and len(_prior_questions()) == PRIOR_QUESTION_COUNT
        and len(prior) == PRIOR_ENTITY_COUNT
        and len(prior_canonical) == PRIOR_ENTITY_COUNT
        and current.isdisjoint(prior)
        and current_canonical.isdisjoint(prior_canonical)
    )


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24513_terminal_projection_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or authorization.get(
            "fresh_terminal_observability_external_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or value.get("label_blind_audit", {}).get("passed") is not True
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.14 build parent drifted")
    return value


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_340_prior_external_questions": _fresh_entity_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_prior_external_populations_rerun": False,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _previous_closed() -> bool:
    result = _read(PREVIOUS_RESULT)
    decision = _read(PREVIOUS_DECISION)
    postaudit = _read(PREVIOUS_POSTAUDIT)
    return (
        result.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and decision.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and postaudit.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and decision.get("status") == "fresh_targeted_external_no_go"
        and postaudit.get("audit_valid") is True
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("findings") == []
        and _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
    )


def _record_bound_binding() -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.14 V2.45.12 closure drifted")
    record = predecessor.predecessor
    return {
        "proof_policy": record.RECORD_PROOF_POLICY_ID,
        "bounded_parent_policy": record.RECORD_PARENT_POLICY_ID,
        "stage_delta_projection_policy": record.total.POLICY_ID,
        "terminal_projection_policy": terminal.POLICY_ID,
        "proposal_seeded_planner_policy": predecessor.PLANNER_POLICY_ID,
        "proposal_seeded_worker_policy": predecessor.WORKER_POLICY_ID,
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "new_population_reuses_prior_question_or_entity": False,
        "v24512_population_rerun": False,
        "v24512_result_sha256": sha256(ROOT / PREVIOUS_RESULT),
        "v24512_decision_sha256": sha256(ROOT / PREVIOUS_DECISION),
        "v24512_postaudit_sha256": sha256(ROOT / PREVIOUS_POSTAUDIT),
        "proposal_seed_is_query_only": True,
        "proposal_votes_promoted_to_active_credit": False,
        "source_count_posterior_margin_and_credit_thresholds_relaxed": False,
        "same_frozen_page_vector_replayed": True,
        "record_stage_gain_required_for_go": False,
        "absolute_terminal_safe_change_and_decision_credit_required": True,
        "safe_change_or_decision_credit_regression_allowed": False,
        "additional_query_search_batch_model_request_or_fetch": False,
        "failure_rows_claim_zero_private_effects": False,
    }


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return (
        value.get("success_tasks") == 8
        and value.get("failure_as_zero_tasks") == 0
        and value.get("passed_success_tasks") == 8
        and value.get("target_plan_tasks", 0) >= GATES["minimum_target_plan_tasks"]
        and value.get("reserve_engaged_tasks", 0)
        >= GATES["minimum_reserve_engaged_tasks"]
        and value.get("reserve_usable_page_tasks", 0)
        >= GATES["minimum_reserve_usable_page_tasks"]
        and value.get("terminal_safe_change_tasks", 0)
        >= GATES["minimum_terminal_safe_change_tasks"]
        and value.get("terminal_positive_decision_credit_tasks", 0)
        >= GATES["minimum_terminal_positive_decision_credit_tasks"]
        and float(value.get("total_terminal_decision_credit_nats", 0.0))
        >= GATES["minimum_total_terminal_decision_credit_nats"]
        and value.get("safe_change_regression_tasks", 0)
        <= GATES["maximum_safe_change_regression_tasks"]
        and value.get("total_safe_change_regression_count", 0)
        <= GATES["maximum_total_safe_change_regression_count"]
        and value.get("decision_credit_regression_tasks", 0)
        <= GATES["maximum_decision_credit_regression_tasks"]
        and float(value.get("total_decision_credit_regression_nats", 0.0))
        <= GATES["maximum_total_decision_credit_regression_nats"]
        and value.get("total_additional_external_effects_success_rows")
        == GATES["maximum_additional_external_effects"]
        and value.get("total_validation_memo_misses") == 64
        and value.get("total_validation_memo_mismatches") == 0
        and value.get("all_success_rows_consumed_validated_capabilities") is True
        and value.get("all_terminal_states_consumed_validated_capabilities")
        is True
        and value.get("all_failure_rows_are_content_free_zero_projections")
        is True
        and value.get("failure_rows_claim_zero_private_effects") is False
        and value.get("private_task_content_emitted") is False
        and value.get("privileged_evaluator_content_read") is False
    )


def diagnostic_route(
    mechanism: Mapping[str, Any],
    supervision: Mapping[str, Any],
    *,
    diagnostic: bool,
    reliability: bool,
    parent_validation: bool,
    latency: bool,
) -> str:
    if int(supervision.get("worker_hard_timeout_tasks", 0)) > 0:
        return "bounded_worker_stage_successor"
    if int(supervision.get("worker_nonzero_tasks", 0)) > 0:
        return "worker_exception_successor"
    if not diagnostic:
        return "proof_or_observability_successor"
    if int(mechanism.get("target_plan_tasks", 0)) == 0:
        return "target_plan_coverage_successor"
    if int(mechanism.get("reserve_engaged_tasks", 0)) == 0:
        return "reserve_engagement_successor"
    if int(mechanism.get("reserve_usable_page_tasks", 0)) == 0:
        return "reserve_fetch_yield_successor"
    if int(mechanism.get("safe_change_regression_tasks", 0)) > 0:
        return "safe_change_regression_successor"
    if int(mechanism.get("decision_credit_regression_tasks", 0)) > 0:
        return "decision_credit_regression_successor"
    if int(mechanism.get("terminal_safe_change_tasks", 0)) == 0:
        return "terminal_support_posterior_margin_successor"
    if float(mechanism.get("total_terminal_decision_credit_nats", 0.0)) <= 0:
        return "terminal_decision_credit_successor"
    if not reliability:
        return "provider_or_fetch_reliability_successor"
    if not parent_validation:
        return "parent_validation_successor"
    if not latency:
        return "latency_capacity_successor"
    return "fresh_paired_dev64_design"


def _patched_core() -> dict[str, Any]:
    value = dict(_ORIGINAL_PATCHED_CORE())
    value.update(
        {
            "PROTOCOL_ID": PROTOCOL_ID,
            "PROTOCOL": PROTOCOL,
            "PREAUDIT": PREAUDIT,
            "ACTIVATION": ACTIVATION,
            "EXECUTION_START": EXECUTION_START,
            "RESULT": RESULT,
            "DECISION": DECISION,
            "POSTAUDIT": POSTAUDIT,
            "PARENT": PARENT,
            "LEASE_OWNER": LEASE_OWNER,
            "LEASE_PURPOSE": LEASE_PURPOSE,
            "RUNNER_MARKER": RUNNER_MARKER,
            "SOURCE_FILES": SOURCE_FILES,
            "TEST_SUITES": TEST_SUITES,
            "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
            "ENTITY_GROUPS": ENTITY_GROUPS,
            "QUESTIONS": QUESTIONS,
            "GATES": GATES,
            "_prior_questions": _prior_questions,
            "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
            "_parent": _parent,
            "_task_contract": _task_contract,
            "aggregate_projections": terminal.aggregate_projections,
            "validate_targeted_aggregate": terminal.validate_aggregate,
            "_mechanism_passed": mechanism_passed,
            "_diagnostic_route": diagnostic_route,
        }
    )
    return value


@contextmanager
def configured_predecessor(*, validators: bool = False) -> Iterator[None]:
    patches: dict[str, Any] = {
        "PROTOCOL_ID": PROTOCOL_ID,
        "PROTOCOL": PROTOCOL,
        "PREAUDIT": PREAUDIT,
        "ACTIVATION": ACTIVATION,
        "EXECUTION_START": EXECUTION_START,
        "RESULT": RESULT,
        "DECISION": DECISION,
        "POSTAUDIT": POSTAUDIT,
        "PARENT": PARENT,
        "RUNNER_MARKER": RUNNER_MARKER,
        "LEASE_OWNER": LEASE_OWNER,
        "LEASE_PURPOSE": LEASE_PURPOSE,
        "PRIOR_QUESTION_COUNT": PRIOR_QUESTION_COUNT,
        "PRIOR_ENTITY_COUNT": PRIOR_ENTITY_COUNT,
        "PRIOR_QUESTIONS": PRIOR_QUESTIONS,
        "PREVIOUS_RESULT": PREVIOUS_RESULT,
        "PREVIOUS_DECISION": PREVIOUS_DECISION,
        "PREVIOUS_POSTAUDIT": PREVIOUS_POSTAUDIT,
        "PREVIOUS_PROTOCOL_ID": PREVIOUS_PROTOCOL_ID,
        "ENTITY_GROUPS": ENTITY_GROUPS,
        "QUESTIONS": QUESTIONS,
        "GATES": GATES,
        "SOURCE_FILES": SOURCE_FILES,
        "TEST_SUITES": TEST_SUITES,
        "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
        "_prior_questions": _prior_questions,
        "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
        "_parent": _parent,
        "_task_contract": _task_contract,
        "_previous_closed": _previous_closed,
        "_record_bound_binding": _record_bound_binding,
        "_patched_core": _patched_core,
    }
    if validators:
        patches.update(
            {
                "validate_protocol": validate_protocol,
                "validate_preaudit": validate_preaudit,
                "validate_activation": validate_activation,
                "validate_execution_start": validate_execution_start,
            }
        )
    missing = object()
    originals = {name: getattr(predecessor, name, missing) for name in patches}
    try:
        for name, value in patches.items():
            setattr(predecessor, name, value)
        yield
    finally:
        for name, value in originals.items():
            if value is missing:
                delattr(predecessor, name)
            else:
                setattr(predecessor, name, value)


@contextmanager
def _with_protocol_validator_bridge() -> Iterator[None]:
    """Let nested frozen preaudit builders validate the terminal protocol.

    V2.45.12 transforms its own preaudit after V2.45.06 returns.  Patching all
    validators here would skip that intermediate schema check.  Only protocol
    validation is bridged; both predecessor preaudit validators still run.
    """

    lower = predecessor.predecessor
    originals = {
        (predecessor, "validate_protocol"): predecessor.validate_protocol,
        (lower, "validate_protocol"): lower.validate_protocol,
    }

    def bridge(*_args: object, value: Mapping[str, Any] | None = None, **_kwargs: object):
        return validate_protocol(value=value)

    try:
        predecessor.validate_protocol = bridge
        lower.validate_protocol = bridge
        yield
    finally:
        for (module, name), value in originals.items():
            setattr(module, name, value)


def build_protocol(
    *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.14 predecessor is not closed")
    with configured_predecessor(validators=True):
        value = predecessor.build_protocol(
            now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["scope"] = "fresh_nonbenchmark_absolute_terminal_entropy_credit_gate"
    value["mechanism"].update(
        {
            "terminal_projection_policy": terminal.POLICY_ID,
            "record_stage_increment_required_for_go": False,
            "absolute_terminal_safe_change_and_credit_required": True,
            "terminal_regression_allowed": False,
        }
    )
    value["protocol_payload_sha256"] = payload_sha256(
        {
            key: item
            for key, item in value.items()
            if key != "protocol_payload_sha256"
        }
    )
    return validate_protocol(value=value)


def validate_protocol(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core["scope"] = "fresh_nonbenchmark_record_bound_entropy_credit_gate"
    for name in (
        "terminal_projection_policy",
        "record_stage_increment_required_for_go",
        "absolute_terminal_safe_change_and_credit_required",
        "terminal_regression_allowed",
    ):
        core.get("mechanism", {}).pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PROTOCOL(value=core)
    mechanism = copied.get("mechanism", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "fresh_nonbenchmark_absolute_terminal_entropy_credit_gate"
        or copied.get("record_bound_binding") != _record_bound_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or mechanism.get("terminal_projection_policy") != terminal.POLICY_ID
        or mechanism.get("record_stage_increment_required_for_go") is not False
        or mechanism.get("absolute_terminal_safe_change_and_credit_required")
        is not True
        or mechanism.get("terminal_regression_allowed") is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.14 terminal protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor(), _with_protocol_validator_bridge():
        value = predecessor.build_preaudit(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_332_prior_external_questions",
        None,
    )
    checks.pop("prior_external_questions_and_entities_exactly_332_and_2656", None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_340_prior_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_340_and_2720"] = True
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks")
    if not isinstance(checks, Mapping):
        raise RuntimeError("V2.45.14 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    core_checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_340_prior_external_questions",
        None,
    )
    core_checks.pop("prior_external_questions_and_entities_exactly_340_and_2720", None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_332_prior_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_332_and_2656"] = True
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_predecessor(), _with_protocol_validator_bridge():
        _ORIGINAL_VALIDATE_PREAUDIT(value=core)
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("launch_authorized") is not True
        or checks.get(
            "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_340_prior_external_questions"
        )
        is not True
        or checks.get("prior_external_questions_and_entities_exactly_340_and_2720")
        is not True
        or checks.get("focused_tests", {}).get("test_count")
        != EXPECTED_TEST_COUNT
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.14 preactivation audit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    validate_preaudit()
    with configured_predecessor(validators=True):
        return predecessor.build_activation(now=now)


def validate_activation() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_predecessor(validators=True):
        return predecessor.build_execution_start(now=now)


def validate_execution_start() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return predecessor.validate_public_result(value)


def run_probe() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return predecessor.run_probe()


def build_decision(*, now: int | None = None) -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return predecessor.build_decision(now=now)


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return predecessor.build_postaudit(now=now)


def run_process_subcommand(args: argparse.Namespace) -> None:
    with configured_predecessor(validators=True):
        predecessor.run_process_subcommand(args)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "protocol",
            "preaudit",
            "activation",
            "start",
            "run",
            "finalize",
            "supervisor",
            "worker",
        ),
    )
    parser.add_argument("--ordinal")
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--checkpoint-directory")
    parser.add_argument("--slots")
    parser.add_argument(
        predecessor.predecessor.base.worker_budget.DEADLINE_ORIGIN_ARGUMENT
    )
    args = parser.parse_args()
    if args.command == "protocol":
        predecessor.predecessor.base.publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit":
        predecessor.predecessor.base.publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        predecessor.predecessor.base.publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        predecessor.predecessor.base.publish(
            ROOT / EXECUTION_START, build_execution_start()
        )
    elif args.command == "run":
        run_probe()
    elif args.command == "finalize":
        predecessor.predecessor.base.publish(ROOT / DECISION, build_decision())
        predecessor.predecessor.base.publish(ROOT / POSTAUDIT, build_postaudit())
    else:
        run_process_subcommand(args)


if __name__ == "__main__":
    main()
