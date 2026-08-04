#!/usr/bin/env python3
"""Append-only total-aggregate successor to the unlaunched V2.44.92 gate.

V2.44.92's successful capability path is frozen and reused byte-for-byte, but
its public aggregate accepted only successful V2.44.91 rows.  This successor
binds the V2.44.92 invalidation and installs V2.44.93's total projection so a
failed task becomes an explicit failure-as-zero mechanism row while partial
effect lower bounds remain in the independent observation aggregate.

The inherited artifact ``role`` strings intentionally identify the frozen
V2.44.92 schema; ``protocol_id`` and paths identify this V2.44.93 successor.
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
from deepwide_agent import v24493_total_targeted_projection as total  # noqa: E402
from scripts import v24492_targeted_external_gate as base  # noqa: E402


DATE = "20260804"
PROTOCOL_ID = "v24493_fresh_total_targeted_support_external_gate_v1"
PROTOCOL = Path(f"results/v24493_total_targeted_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24493_total_targeted_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24493_total_targeted_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24493_total_targeted_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24493_total_targeted_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24493_total_targeted_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24493_total_targeted_external_postresult_audit_v1_{DATE}.json")
INVALIDATION = Path("results/v24492_targeted_external_protocol_invalidation_v1_20260804.json")
RUNNER_MARKER = "scripts/v24493_total_targeted_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_total_targeted_support_external_gate"
SOURCE_FILES = (
    "src/deepwide_agent/v24490_entropy_targeted_support_search.py",
    "src/deepwide_agent/v24491_proof_carrying_targeted_support.py",
    "src/deepwide_agent/v24492_targeted_timed_parent.py",
    "src/deepwide_agent/v24493_total_targeted_projection.py",
    "tests/test_v24491_proof_carrying_targeted_support.py",
    "tests/test_v24492_targeted_timed_parent.py",
    "tests/test_v24493_total_targeted_projection.py",
    "scripts/v24492_targeted_external_gate.py",
    "tests/test_v24492_targeted_external_gate.py",
    str(INVALIDATION),
    RUNNER_MARKER,
    "tests/test_v24493_total_targeted_external_gate.py",
    str(base.PARENT),
)
TEST_SUITES = (
    ("tests/test_v24491_proof_carrying_targeted_support.py", 10, 180),
    ("tests/test_v24492_targeted_timed_parent.py", 4, 120),
    ("tests/test_v24493_total_targeted_projection.py", 4, 120),
    ("tests/test_v24493_total_targeted_external_gate.py", 7, 120),
)
EXPECTED_TEST_COUNT = 25


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.93 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def validate_invalidation() -> dict[str, Any]:
    value = _read(INVALIDATION)
    if (
        value.get("role") != "v24492_targeted_external_protocol_invalidation"
        or value.get("protocol_id") != base.PROTOCOL_ID
        or value.get("reason")
        != "failure_as_zero_projection_schema_is_not_accepted_by_success_only_targeted_aggregate"
        or value.get("external_probe_launched") is not False
        or value.get("network_model_search_fetch_or_evaluator_called") is not False
        or value.get("same_population_consumed") is not False
        or value.get("authorization", {}).get(
            "append_only_failure_aggregate_successor_design"
        )
        is not True
        or value.get("authorization", {}).get("v24492_activation_or_launch")
        is not False
        or not _sealed(value, "invalidation_payload_sha256")
    ):
        raise RuntimeError("V2.44.93 predecessor invalidation drifted")
    return value


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return (
        value.get("success_tasks") == base.SELECTED
        and value.get("failure_as_zero_tasks") == 0
        and value.get("passed_success_tasks") == base.SELECTED
        and value.get("target_plan_tasks", 0)
        >= base.GATES["minimum_target_plan_tasks"]
        and value.get("safe_change_improvement_tasks", 0)
        >= base.GATES["minimum_safe_change_improvement_tasks"]
        and value.get("positive_decision_credit_tasks", 0)
        >= base.GATES["minimum_positive_decision_credit_tasks"]
        and float(value.get("total_decision_credit_nats", 0.0))
        >= base.GATES["minimum_total_decision_credit_nats"]
        and value.get("total_additional_model_acquisitions_success_rows")
        <= base.GATES["maximum_additional_model_acquisitions"]
        and value.get("total_validation_memo_misses") == base.SELECTED * 8
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
        mechanism.get("selected") == base.SELECTED
        and mechanism.get("exact_ordinal_vector") is True
        and mechanism.get("success_tasks") == base.SELECTED
        and mechanism.get("failure_as_zero_tasks") == 0
        and observation.get("selected") == base.SELECTED
        and observation.get("success_tasks") == base.SELECTED
        and observation.get("failure_tasks") == 0
        and observation.get("fully_observed_effect_tasks") == base.SELECTED
        and timing.get("selected") == base.SELECTED
        and timing.get("parent_success_tasks") == base.SELECTED
        and timing.get("certificate_validation_invocations") == base.SELECTED
        and timing.get("adaptive_projection_invocations") == base.SELECTED
        and timing.get("recursive_historical_semantic_replay_tasks") == 0
        and supervision.get("selected") == base.SELECTED
        and supervision.get("worker_success_tasks") == base.SELECTED
        and supervision.get("worker_hard_timeout_tasks") == 0
        and supervision.get("worker_nonzero_tasks") == 0
        and supervision.get("checkpoint_chain_valid_tasks") == base.SELECTED
        and supervision.get("complete_validation_returned_tasks") == base.SELECTED
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
        return "targeted_plan_coverage_successor"
    if int(mechanism.get("safe_change_improvement_tasks", 0)) == 0:
        return "targeted_support_conversion_successor"
    if float(mechanism.get("total_decision_credit_nats", 0.0)) <= 0:
        return "entropy_to_decision_alignment_successor"
    if not reliability:
        return "provider_or_fetch_reliability_successor"
    if not parent_validation:
        return "parent_validation_successor"
    if not latency:
        return "latency_capacity_successor"
    return "fresh_paired_dev64_design"


_PATCHED = {
    "PROTOCOL_ID": PROTOCOL_ID,
    "PROTOCOL": PROTOCOL,
    "PREAUDIT": PREAUDIT,
    "ACTIVATION": ACTIVATION,
    "EXECUTION_START": EXECUTION_START,
    "RESULT": RESULT,
    "DECISION": DECISION,
    "POSTAUDIT": POSTAUDIT,
    "LEASE_OWNER": LEASE_OWNER,
    "LEASE_PURPOSE": LEASE_PURPOSE,
    "RUNNER_MARKER": RUNNER_MARKER,
    "SOURCE_FILES": SOURCE_FILES,
    "TEST_SUITES": TEST_SUITES,
    "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
    "aggregate_projections": total.aggregate_projections,
    "validate_targeted_aggregate": total.validate_aggregate,
    "_mechanism_passed": mechanism_passed,
    "_diagnostic_complete": diagnostic_complete,
    "_diagnostic_route": diagnostic_route,
}


@contextmanager
def configured_base() -> Iterator[None]:
    missing = object()
    originals = {name: getattr(base, name, missing) for name in _PATCHED}
    try:
        for name, value in _PATCHED.items():
            setattr(base, name, value)
        yield
    finally:
        for name, value in originals.items():
            if value is missing:
                delattr(base, name)
            else:
                setattr(base, name, value)


def _successor_binding() -> dict[str, Any]:
    invalidation = validate_invalidation()
    return {
        "invalidated_protocol_id": invalidation["protocol_id"],
        "invalidation_path": str(INVALIDATION),
        "invalidation_sha256": sha256(ROOT / INVALIDATION),
        "total_projection_policy": total.POLICY_ID,
        "same_unconsumed_population_reused": True,
        "successful_execution_path_unchanged": True,
        "failure_as_zero_projection_is_total": True,
        "failure_rows_claim_zero_private_effects": False,
    }


def build_protocol(*, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    validate_invalidation()
    with configured_base():
        value = base.build_protocol(now=now, require_pristine=require_pristine)
    value = copy.deepcopy(value)
    value["successor_binding"] = _successor_binding()
    value["mechanism"]["total_projection_policy"] = total.POLICY_ID
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(value=value)


def validate_protocol(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PROTOCOL)
    with configured_base():
        base.validate_protocol(value=copied)
    if (
        copied.get("successor_binding") != _successor_binding()
        or copied.get("mechanism", {}).get("total_projection_policy")
        != total.POLICY_ID
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.44.93 successor protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_base():
        value = base.build_preaudit(now=now)
    return value


def validate_preaudit() -> dict[str, Any]:
    with configured_base():
        return base.validate_preaudit()


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    with configured_base():
        return base.build_activation(now=now)


def validate_activation() -> dict[str, Any]:
    with configured_base():
        return base.validate_activation()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    with configured_base():
        return base.build_execution_start(now=now)


def validate_execution_start() -> dict[str, Any]:
    with configured_base():
        return base.validate_execution_start()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_base():
        return base.validate_public_result(value)


def run_probe() -> dict[str, Any]:
    with configured_base():
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
