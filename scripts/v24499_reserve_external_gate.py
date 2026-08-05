#!/usr/bin/env python3
"""Protocol and runner for one fresh proof-carrying reserve external gate.

The execution orchestration is the frozen V2.44.92 one-wave runner.  This
successor replaces only the population, proof-capability parent/worker,
failure-total projection, parent build audit, and reserve-specific mechanism
gates.  Protocol and preactivation publication perform no remote effect.
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
from deepwide_agent.v24497_proof_carrying_targeted_reserve import (  # noqa: E402
    POLICY_ID as RESERVE_PROOF_POLICY_ID,
)
from deepwide_agent.v24498_reserve_timed_parent import (  # noqa: E402
    POLICY_ID as RESERVE_PARENT_POLICY_ID,
    run_reserve_parent_with_separated_budget,
    run_reserve_worker,
    supervise_reserve_worker_with_separated_budget,
)
from deepwide_agent import v24498_total_reserve_projection as total  # noqa: E402
from scripts import audit_v24498_reserve_parent_build as parent_build  # noqa: E402
from scripts import v24492_targeted_external_gate as base  # noqa: E402


DATE = "20260804"
PROTOCOL_ID = "v24499_fresh_proof_carrying_reserve_external_gate_v1"
PROTOCOL = Path(f"results/v24499_reserve_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24499_reserve_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24499_reserve_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24499_reserve_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24499_reserve_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24499_reserve_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24499_reserve_external_postresult_audit_v1_{DATE}.json")
PARENT = parent_build.AUDIT
RUNNER_MARKER = "scripts/v24499_reserve_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_proof_carrying_reserve_external_gate"
PRIOR_QUESTION_COUNT = 316
PRIOR_ENTITY_COUNT = 2528
PRIOR_QUESTIONS = (
    base.history._prior_questions() + base.history.QUESTIONS + base.QUESTIONS
)
ENTITY_GROUPS = (
    (
        "Rhode Island School of Design", "Pratt Institute",
        "School of the Art Institute of Chicago", "California Institute of the Arts",
        "ArtCenter College of Design", "Savannah College of Art and Design",
        "Otis College of Art and Design", "Minneapolis College of Art and Design",
    ),
    (
        "Juilliard School", "Curtis Institute of Music", "Berklee College of Music",
        "New England Conservatory", "Manhattan School of Music",
        "Cleveland Institute of Music", "San Francisco Conservatory of Music",
        "Colburn School",
    ),
    (
        "Architectural Association School of Architecture", "Cooper Union",
        "Cranbrook Academy of Art", "Graz University of Technology",
        "Vienna University of Technology", "Brno University of Technology",
        "Czech Technical University in Prague", "Warsaw University of Technology",
    ),
    (
        "Pohang University of Science and Technology",
        "Gwangju Institute of Science and Technology",
        "Ulsan National Institute of Science and Technology",
        "Daegu Gyeongbuk Institute of Science and Technology",
        "Okinawa Institute of Science and Technology",
        "Japan Advanced Institute of Science and Technology",
        "Nara Institute of Science and Technology",
        "King Abdullah University of Science and Technology",
    ),
    (
        "INSEAD", "IMD Business School", "HEC Paris", "ESSEC Business School",
        "ESCP Business School", "EMLYON Business School",
        "SDA Bocconi School of Management",
        "Rotterdam School of Management Erasmus University",
    ),
    (
        "Ashesi University", "University of Development Studies",
        "Ghana Communication Technology University", "Pentecost University",
        "Methodist University Ghana", "Accra Technical University",
        "Ho Technical University", "Koforidua Technical University",
    ),
    (
        "Torcuato Di Tella University", "Austral University Argentina",
        "Universidad de San Andrés", "Universidad del CEMA",
        "Adolfo Ibáñez University", "Diego Portales University",
        "Andrés Bello University", "Alberto Hurtado University",
    ),
    (
        "Bond University", "University of the Sunshine Coast",
        "Southern Cross University", "Charles Darwin University",
        "Federation University Australia", "Torrens University Australia",
        "University of Notre Dame Australia", "Avondale University",
    ),
)


def _question(group: tuple[str, ...]) -> str:
    if len(group) != 8:
        raise ValueError("V2.44.99 entity group drifted")
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
    "minimum_reserve_new_observation_tasks": 1,
    "minimum_reserve_supporting_observation_tasks": 1,
    "minimum_safe_change_improvement_tasks": 1,
    "minimum_positive_decision_credit_gain_tasks": 1,
    "minimum_total_decision_credit_gain_nats": 1e-12,
    "maximum_safe_change_regression_tasks": 0,
    "maximum_decision_credit_regression_tasks": 0,
    "maximum_total_decision_credit_regression_nats": 0.0,
    "maximum_additional_model_acquisitions": 0,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 3,
    "maximum_fetch_helper_failures": 3,
    "maximum_parent_validation_p95_seconds": 1.0,
}
SOURCE_FILES = (
    "src/deepwide_agent/v24496_targeted_reserve_contradiction.py",
    "src/deepwide_agent/v24497_proof_carrying_targeted_reserve.py",
    "src/deepwide_agent/v24498_reserve_timed_parent.py",
    "src/deepwide_agent/v24498_total_reserve_projection.py",
    "tests/test_v24497_proof_carrying_targeted_reserve.py",
    "tests/test_v24498_reserve_timed_parent.py",
    "tests/test_v24498_total_reserve_projection.py",
    str(PARENT),
    "scripts/v24492_targeted_external_gate.py",
    RUNNER_MARKER,
    "tests/test_v24499_reserve_external_gate.py",
)
TEST_SUITES = (
    ("tests/test_v24497_proof_carrying_targeted_reserve.py", 12, 180),
    ("tests/test_v24498_reserve_timed_parent.py", 4, 120),
    ("tests/test_v24498_total_reserve_projection.py", 4, 120),
    ("tests/test_v24499_reserve_external_gate.py", 7, 120),
)
EXPECTED_TEST_COUNT = 27


_ORIGINAL_VALIDATE_PROTOCOL = base.validate_protocol
_ORIGINAL_VALIDATE_PREAUDIT = base.validate_preaudit
_ORIGINAL_VALIDATE_ACTIVATION = base.validate_activation
_ORIGINAL_VALIDATE_EXECUTION_START = base.validate_execution_start


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.99 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _prior_questions() -> tuple[str, ...]:
    return PRIOR_QUESTIONS


def _fresh_entity_vector_valid() -> bool:
    parser = base.history.history.previous_gate.history.history.history.parent
    current = {
        entity
        for question in QUESTIONS
        for entity in parser._question_entity_vector(question)
    }
    prior_questions = _prior_questions()
    prior = {
        entity
        for question in prior_questions
        for entity in parser._question_entity_vector(question)
    }
    return (
        len(current) == 64
        and len({parser._canonical_entity(entity) for entity in current}) == 64
        and len(prior_questions) == PRIOR_QUESTION_COUNT
        and len(prior) == PRIOR_ENTITY_COUNT
        and len({parser._canonical_entity(entity) for entity in prior})
        == PRIOR_ENTITY_COUNT
        and current.isdisjoint(prior)
        and {parser._canonical_entity(entity) for entity in current}.isdisjoint(
            {parser._canonical_entity(entity) for entity in prior}
        )
    )


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24498_reserve_parent_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "fresh_reserve_external_protocol_design"
        )
        is not True
        or value.get("authorization", {}).get(
            "fresh_reserve_external_activation_or_launch"
        )
        is not False
        or value.get("label_blind_audit", {}).get("passed") is not True
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.99 build parent drifted")
    return value


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_316_prior_external_questions": _fresh_entity_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_prior_external_populations_rerun": False,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return (
        value.get("success_tasks") == 8
        and value.get("failure_as_zero_tasks") == 0
        and value.get("passed_success_tasks") == 8
        and value.get("target_plan_tasks", 0) >= 1
        and value.get("reserve_engaged_tasks", 0) >= 1
        and value.get("reserve_usable_page_tasks", 0) >= 1
        and value.get("reserve_new_observation_tasks", 0) >= 1
        and value.get("reserve_supporting_observation_tasks", 0) >= 1
        and value.get("safe_change_improvement_tasks", 0) >= 1
        and value.get("positive_decision_credit_gain_tasks", 0) >= 1
        and float(value.get("total_decision_credit_gain_nats", 0.0)) >= 1e-12
        and value.get("safe_change_regression_tasks", 0) == 0
        and value.get("decision_credit_regression_tasks", 0) == 0
        and float(value.get("total_decision_credit_regression_nats", 0.0)) == 0
        and value.get("total_additional_model_acquisitions_success_rows") == 0
        and value.get("total_validation_memo_misses") == 64
        and value.get("total_validation_memo_mismatches") == 0
        and value.get("all_success_rows_consumed_validated_capabilities") is True
        and value.get("all_failure_rows_are_content_free_zero_projections") is True
        and value.get("failure_rows_claim_zero_private_effects") is False
    )


def diagnostic_complete(
    mechanism: Mapping[str, Any],
    observation: Mapping[str, Any],
    timing: Mapping[str, Any],
    supervision: Mapping[str, Any],
) -> bool:
    return (
        mechanism.get("selected") == 8
        and mechanism.get("exact_ordinal_vector") is True
        and observation.get("selected") == 8
        and timing.get("selected") == 8
        and supervision.get("selected") == 8
        and supervision.get("checkpoint_chain_valid_tasks") == 8
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
    if int(mechanism.get("reserve_new_observation_tasks", 0)) == 0:
        return "target_bound_projection_successor"
    if int(mechanism.get("safe_change_improvement_tasks", 0)) == 0:
        return "support_posterior_margin_successor"
    if float(mechanism.get("total_decision_credit_gain_nats", 0.0)) <= 0:
        return "incremental_credit_alignment_successor"
    if not reliability:
        return "provider_or_fetch_reliability_successor"
    if not parent_validation:
        return "parent_validation_successor"
    if not latency:
        return "latency_capacity_successor"
    return "fresh_paired_dev64_design"


_CORE_PATCHED = {
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
    "TARGETED_PROOF_POLICY_ID": RESERVE_PROOF_POLICY_ID,
    "TARGETED_PARENT_POLICY_ID": RESERVE_PARENT_POLICY_ID,
    "_prior_questions": _prior_questions,
    "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
    "_parent": _parent,
    "_task_contract": _task_contract,
    "run_targeted_worker": run_reserve_worker,
    "supervise_targeted_worker_with_separated_budget": supervise_reserve_worker_with_separated_budget,
    "run_targeted_parent_with_separated_budget": run_reserve_parent_with_separated_budget,
    "aggregate_projections": total.aggregate_projections,
    "validate_targeted_aggregate": total.validate_aggregate,
    "_mechanism_passed": mechanism_passed,
    "_diagnostic_complete": diagnostic_complete,
    "_diagnostic_route": diagnostic_route,
}


@contextmanager
def configured_base() -> Iterator[None]:
    missing = object()
    originals = {name: getattr(base, name, missing) for name in _CORE_PATCHED}
    try:
        for name, value in _CORE_PATCHED.items():
            setattr(base, name, value)
        yield
    finally:
        for name, value in originals.items():
            if value is missing:
                delattr(base, name)
            else:
                setattr(base, name, value)


def _reserve_binding() -> dict[str, Any]:
    return {
        "proof_policy": RESERVE_PROOF_POLICY_ID,
        "bounded_parent_policy": RESERVE_PARENT_POLICY_ID,
        "total_projection_policy": total.POLICY_ID,
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "new_population_reuses_prior_question_or_entity": False,
        "reserve_uses_only_same_targeted_discovery_union": True,
        "total_targeted_fetch_cap": 3,
        "additional_query_search_batch_or_model_request": False,
        "failure_rows_claim_zero_private_effects": False,
        "incremental_decision_credit_separate_from_parent_credit": True,
    }


def build_protocol(*, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    with configured_base():
        value = base.build_protocol(now=now, require_pristine=require_pristine)
    value = copy.deepcopy(value)
    value["scope"] = "fresh_nonbenchmark_proof_carrying_reserve_conversion_gate"
    value["reserve_binding"] = _reserve_binding()
    value["mechanism"].update(
        {
            "total_projection_policy": total.POLICY_ID,
            "reserve_reuses_same_targeted_discovery_union": True,
            "reserve_additional_query_search_batch_or_model_request": False,
            "reserve_support_conflict_and_incremental_credit_projected": True,
        }
    )
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(value=value)


def validate_protocol(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core["scope"] = "fresh_nonbenchmark_targeted_entropy_decision_credit_gate"
    core.pop("reserve_binding", None)
    for name in (
        "total_projection_policy",
        "reserve_reuses_same_targeted_discovery_union",
        "reserve_additional_query_search_batch_or_model_request",
        "reserve_support_conflict_and_incremental_credit_projected",
    ):
        core.get("mechanism", {}).pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_base():
        _ORIGINAL_VALIDATE_PROTOCOL(ROOT, value=core)
    if (
        copied.get("scope")
        != "fresh_nonbenchmark_proof_carrying_reserve_conversion_gate"
        or copied.get("reserve_binding") != _reserve_binding()
        or copied.get("mechanism", {}).get("total_projection_policy")
        != total.POLICY_ID
        or copied.get("mechanism", {}).get(
            "reserve_reuses_same_targeted_discovery_union"
        )
        is not True
        or copied.get("mechanism", {}).get(
            "reserve_additional_query_search_batch_or_model_request"
        )
        is not False
        or copied.get("mechanism", {}).get(
            "reserve_support_conflict_and_incremental_credit_projected"
        )
        is not True
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.44.99 reserve protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_base(), _with_validator_patches():
        value = base.build_preaudit(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    checks.pop("fresh_64_entity_vector_frozen", None)
    checks.pop("prior_external_questions_and_entities_exactly_308_and_2464", None)
    checks["fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_316_prior_external_questions"] = True
    checks["prior_external_questions_and_entities_exactly_316_and_2528"] = True
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks")
    provenance = copied.get("provenance")
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or copied.get("launch_authorized") is not True
        or not isinstance(checks, Mapping)
        or any(
            checks.get(name) is not True
            for name in (
                "protocol_valid_and_sealed",
                "one_wave_capacity_frozen",
                "phase_deadlines_exactly_150_220_245",
                "keyless_proxy_listening_without_api_request",
                "shared_api_lease_inactive",
                "protocol_commit_pushed",
                "worktree_clean",
                "all_protocol_sources_tracked",
                "future_surface_pristine",
                "protected_watchers_unchanged",
            )
        )
        or checks.get(
            "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_316_prior_external_questions"
        )
        is not True
        or checks.get(
            "prior_external_questions_and_entities_exactly_316_and_2528"
        )
        is not True
        or not isinstance(checks.get("focused_tests"), Mapping)
        or checks["focused_tests"].get("passed") is not True
        or checks["focused_tests"].get("test_count") != EXPECTED_TEST_COUNT
        or checks.get("benchmark_or_evaluator_surface_authorized") is not False
        or copied.get("privileged_field_accesses") != []
        or copied.get("evaluator_imports") != []
        or copied.get("protected_watchers") != base.protected_watcher_snapshot()
        or not isinstance(provenance, Mapping)
        or provenance.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or provenance.get("surface_manifest_sha256")
        != validate_protocol()["surface_manifest_sha256"]
        or provenance.get("head") != provenance.get("target_main")
        or copied.get("authorization") != base._activation_authorization()
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.99 preactivation audit drifted")
    return copied


def _with_validator_patches() -> Iterator[None]:
    @contextmanager
    def context() -> Iterator[None]:
        missing = object()
        patches = {
            "validate_protocol": lambda _root=ROOT, value=None: validate_protocol(value=value),
            "validate_preaudit": lambda _root=ROOT: validate_preaudit(),
            "validate_activation": lambda _root=ROOT: validate_activation(),
            "validate_execution_start": lambda _root=ROOT: validate_execution_start(),
        }
        originals = {name: getattr(base, name, missing) for name in patches}
        try:
            for name, item in patches.items():
                setattr(base, name, item)
            yield
        finally:
            for name, item in originals.items():
                if item is missing:
                    delattr(base, name)
                else:
                    setattr(base, name, item)
    return context()


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol(); validate_preaudit()
    with configured_base(), _with_validator_patches():
        return base.build_activation(now=now)


def validate_activation() -> dict[str, Any]:
    with configured_base(), _with_validator_patches():
        value = _ORIGINAL_VALIDATE_ACTIVATION(ROOT)
    validate_protocol(); validate_preaudit()
    return value


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_base(), _with_validator_patches():
        return base.build_execution_start(now=now)


def validate_execution_start() -> dict[str, Any]:
    with configured_base():
        return _ORIGINAL_VALIDATE_EXECUTION_START(ROOT)


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_base():
        return base.validate_public_result(value)


def run_probe() -> dict[str, Any]:
    with configured_base(), _with_validator_patches():
        return base.run_probe()


def build_decision(*, now: int | None = None) -> dict[str, Any]:
    with configured_base():
        return base.build_decision(now=now)


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    with configured_base():
        return base.build_postaudit(now=now)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "protocol", "preaudit", "activation", "start", "run", "finalize",
            "supervisor", "worker",
        ),
    )
    parser.add_argument("--ordinal")
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--checkpoint-directory")
    parser.add_argument("--slots")
    parser.add_argument(base.worker_budget.DEADLINE_ORIGIN_ARGUMENT)
    args = parser.parse_args()
    if args.command == "protocol":
        base.publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit":
        base.publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        base.publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        base.publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_probe()
    elif args.command == "finalize":
        base.publish(ROOT / DECISION, build_decision())
        base.publish(ROOT / POSTAUDIT, build_postaudit())
    else:
        with configured_base():
            base._worker(args) if args.command == "worker" else base._supervisor(args)


if __name__ == "__main__":
    main()
