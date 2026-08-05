#!/usr/bin/env python3
"""Validator-bound successor to the unlaunched V2.44.99 reserve gate.

V2.44.99 froze a fresh population and reserve protocol, but its independent
``worker`` and ``supervisor`` CLI branches entered only the base configuration
context.  They therefore called the frozen V2.44.92 protocol validator before
any effect and rejected the reserve extension.  This successor reuses the
same unconsumed population and changes no mechanism, budget, gate, or source
selection.  It binds the reserve validator context at every CLI/process layer.
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
from scripts import v24499_reserve_external_gate as predecessor  # noqa: E402


DATE = "20260804"
PROTOCOL_ID = "v24500_fresh_validator_bound_reserve_external_gate_v1"
PROTOCOL = Path(f"results/v24500_reserve_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24500_reserve_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24500_reserve_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24500_reserve_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24500_reserve_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24500_reserve_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24500_reserve_external_postresult_audit_v1_{DATE}.json")
INVALIDATION = Path(
    "results/v24499_reserve_external_protocol_invalidation_v1_20260804.json"
)
RUNNER_MARKER = "scripts/v24500_reserve_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_validator_bound_reserve_external_gate"
SOURCE_FILES = (
    *(
        value
        for value in predecessor.SOURCE_FILES
        if value
        not in {
            predecessor.RUNNER_MARKER,
            "tests/test_v24499_reserve_external_gate.py",
        }
    ),
    predecessor.RUNNER_MARKER,
    "tests/test_v24499_reserve_external_gate.py",
    str(predecessor.PROTOCOL),
    str(predecessor.PREAUDIT),
    str(INVALIDATION),
    RUNNER_MARKER,
    "tests/test_v24500_reserve_external_gate.py",
)
TEST_SUITES = (
    ("tests/test_v24497_proof_carrying_targeted_reserve.py", 12, 180),
    ("tests/test_v24498_reserve_timed_parent.py", 4, 120),
    ("tests/test_v24498_total_reserve_projection.py", 4, 120),
    ("tests/test_v24499_reserve_external_gate.py", 7, 120),
    ("tests/test_v24500_reserve_external_gate.py", 6, 180),
)
EXPECTED_TEST_COUNT = 33


_ORIGINAL_VALIDATE_PROTOCOL = predecessor.validate_protocol
_ORIGINAL_VALIDATE_PREAUDIT = predecessor.validate_preaudit
_ORIGINAL_VALIDATE_ACTIVATION = predecessor.validate_activation
_ORIGINAL_VALIDATE_EXECUTION_START = predecessor.validate_execution_start
PREDECESSOR_PROTOCOL_ID = predecessor.PROTOCOL_ID


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.00 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def validate_invalidation() -> dict[str, Any]:
    value = _read(INVALIDATION)
    if (
        value.get("role") != "v24499_reserve_external_protocol_invalidation"
        or value.get("protocol_id") != PREDECESSOR_PROTOCOL_ID
        or value.get("reason")
        != "supervisor_worker_subcommands_do_not_bind_the_reserve_protocol_validator"
        or value.get("detected_before_activation") is not True
        or value.get("activation_created") is not False
        or value.get("execution_start_created") is not False
        or value.get("external_probe_launched") is not False
        or value.get("network_model_search_fetch_or_evaluator_called") is not False
        or value.get("same_population_consumed") is not False
        or value.get("authorization", {}).get(
            "append_only_validator_binding_successor_design"
        )
        is not True
        or value.get("authorization", {}).get("v24499_activation_or_launch")
        is not False
        or not _sealed(value, "invalidation_payload_sha256")
    ):
        raise RuntimeError("V2.45.00 predecessor invalidation drifted")
    return value


def _patched_core() -> dict[str, Any]:
    value = dict(predecessor._CORE_PATCHED)
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
            "LEASE_OWNER": LEASE_OWNER,
            "LEASE_PURPOSE": LEASE_PURPOSE,
            "RUNNER_MARKER": RUNNER_MARKER,
            "SOURCE_FILES": SOURCE_FILES,
            "TEST_SUITES": TEST_SUITES,
            "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
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
        "RUNNER_MARKER": RUNNER_MARKER,
        "LEASE_OWNER": LEASE_OWNER,
        "LEASE_PURPOSE": LEASE_PURPOSE,
        "SOURCE_FILES": SOURCE_FILES,
        "TEST_SUITES": TEST_SUITES,
        "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
        "_CORE_PATCHED": _patched_core(),
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


def _successor_binding() -> dict[str, Any]:
    invalidation = validate_invalidation()
    return {
        "invalidated_protocol_id": invalidation["protocol_id"],
        "invalidation_path": str(INVALIDATION),
        "invalidation_sha256": sha256(ROOT / INVALIDATION),
        "same_unconsumed_population_reused": True,
        "mechanism_budget_gates_and_population_unchanged": True,
        "parent_run_validator_context_bound": True,
        "supervisor_validator_context_bound": True,
        "worker_validator_context_bound": True,
        "all_validator_and_configuration_bindings_restored_on_exit": True,
        "additional_network_model_search_fetch_or_evaluator_effect": False,
    }


def build_protocol(*, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    validate_invalidation()
    with configured_predecessor():
        value = predecessor.build_protocol(
            now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["validator_binding_successor"] = _successor_binding()
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(value=value)


def validate_protocol(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core.pop("validator_binding_successor", None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PROTOCOL(value=core)
    if (
        copied.get("validator_binding_successor") != _successor_binding()
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.00 validator-bound protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor(validators=True):
        value = predecessor.build_preaudit(now=now)
    value = copy.deepcopy(value)
    value["validator_binding_successor"] = _successor_binding()
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PREAUDIT)
    core = copy.deepcopy(copied)
    core.pop("validator_binding_successor", None)
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_predecessor(validators=True):
        _ORIGINAL_VALIDATE_PREAUDIT(value=core)
    if (
        copied.get("validator_binding_successor") != _successor_binding()
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.00 validator-bound preaudit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol(); validate_preaudit()
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
    """Bind both configuration and validators for worker/supervisor CLI."""

    with configured_predecessor(validators=True):
        with predecessor.configured_base(), predecessor._with_validator_patches():
            predecessor.base._worker(args) if args.command == "worker" else predecessor.base._supervisor(args)


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
    parser.add_argument(predecessor.base.worker_budget.DEADLINE_ORIGIN_ARGUMENT)
    args = parser.parse_args()
    if args.command == "protocol":
        predecessor.base.publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit":
        predecessor.base.publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        predecessor.base.publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        predecessor.base.publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_probe()
    elif args.command == "finalize":
        predecessor.base.publish(ROOT / DECISION, build_decision())
        predecessor.base.publish(ROOT / POSTAUDIT, build_postaudit())
    else:
        run_process_subcommand(args)


if __name__ == "__main__":
    main()
