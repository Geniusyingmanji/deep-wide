#!/usr/bin/env python3
"""Ordering-safe successor to the unlaunched V2.45.00 reserve gate.

V2.45.00 correctly bound successor validators in parent, supervisor and worker
processes, but its preaudit builder exposed the outer validator before the
outer binding had been attached.  This append-only successor preserves the
unconsumed population, mechanism, budgets and process binding.  It validates
the V2.44.99 core preaudit first, then adds and validates each successor layer.
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
from scripts import v24500_reserve_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24501_fresh_ordering_safe_reserve_external_gate_v1"
PROTOCOL = Path(f"results/v24501_reserve_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24501_reserve_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24501_reserve_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24501_reserve_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24501_reserve_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24501_reserve_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24501_reserve_external_postresult_audit_v1_{DATE}.json")
INVALIDATION = Path(
    "results/v24500_reserve_external_protocol_invalidation_v1_20260805.json"
)
RUNNER_MARKER = "scripts/v24501_reserve_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_ordering_safe_reserve_external_gate"
SOURCE_FILES = (
    *predecessor.SOURCE_FILES,
    str(predecessor.PROTOCOL),
    str(INVALIDATION),
    RUNNER_MARKER,
    "tests/test_v24501_reserve_external_gate.py",
)
TEST_SUITES = (
    ("tests/test_v24497_proof_carrying_targeted_reserve.py", 12, 180),
    ("tests/test_v24498_reserve_timed_parent.py", 4, 120),
    ("tests/test_v24498_total_reserve_projection.py", 4, 120),
    ("tests/test_v24499_reserve_external_gate.py", 7, 120),
    ("tests/test_v24500_reserve_external_gate.py", 6, 180),
    ("tests/test_v24501_reserve_external_gate.py", 7, 180),
)
EXPECTED_TEST_COUNT = 40


_ORIGINAL_PATCHED_CORE = predecessor._patched_core
_ORIGINAL_VALIDATE_PROTOCOL = predecessor.validate_protocol
_ORIGINAL_VALIDATE_PREAUDIT = predecessor.validate_preaudit
_ORIGINAL_VALIDATE_ACTIVATION = predecessor.validate_activation
_ORIGINAL_VALIDATE_EXECUTION_START = predecessor.validate_execution_start
_V24499_VALIDATE_PREAUDIT = predecessor.predecessor.validate_preaudit
PREDECESSOR_PROTOCOL_ID = predecessor.PROTOCOL_ID
PREDECESSOR_PROTOCOL = predecessor.PROTOCOL


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.01 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def validate_invalidation() -> dict[str, Any]:
    value = _read(INVALIDATION)
    if (
        value.get("role") != "v24500_reserve_external_protocol_invalidation"
        or value.get("protocol_id") != PREDECESSOR_PROTOCOL_ID
        or value.get("reason")
        != "preaudit_builder_calls_successor_validator_before_successor_binding_is_attached"
        or value.get("detected_during_preactivation_build") is not True
        or value.get("local_preaudit_build_attempts") != 2
        or value.get("preaudit_created") is not False
        or value.get("activation_created") is not False
        or value.get("execution_start_created") is not False
        or value.get("external_probe_launched") is not False
        or value.get("network_model_search_fetch_or_evaluator_called") is not False
        or value.get("same_population_consumed") is not False
        or value.get("protocol_sha256") != sha256(ROOT / PREDECESSOR_PROTOCOL)
        or value.get("authorization", {}).get(
            "append_only_preaudit_builder_ordering_successor_design"
        )
        is not True
        or value.get("authorization", {}).get("v24500_activation_or_launch")
        is not False
        or not _sealed(value, "invalidation_payload_sha256")
    ):
        raise RuntimeError("V2.45.01 predecessor invalidation drifted")
    return value


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


def _validator_binding() -> dict[str, Any]:
    with configured_predecessor():
        return predecessor._successor_binding()


def _ordering_binding() -> dict[str, Any]:
    invalidation = validate_invalidation()
    return {
        "invalidated_protocol_id": invalidation["protocol_id"],
        "invalidation_path": str(INVALIDATION),
        "invalidation_sha256": sha256(ROOT / INVALIDATION),
        "same_unconsumed_population_reused": True,
        "population_mechanism_budget_gates_and_source_selection_unchanged": True,
        "v24500_parent_supervisor_worker_validator_binding_preserved": True,
        "core_preaudit_validated_before_successor_bindings_attached": True,
        "successor_bindings_attached_inner_to_outer_and_resealed": True,
        "additional_network_model_search_fetch_or_evaluator_effect": False,
    }


def build_protocol(*, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    validate_invalidation()
    with configured_predecessor():
        value = predecessor.build_protocol(
            now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["preaudit_builder_ordering_successor"] = _ordering_binding()
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(value=value)


def validate_protocol(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core.pop("preaudit_builder_ordering_successor", None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PROTOCOL(value=core)
    if (
        copied.get("validator_binding_successor") != _validator_binding()
        or copied.get("preaudit_builder_ordering_successor") != _ordering_binding()
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.01 ordering-safe protocol drifted")
    return copied


@contextmanager
def _v24499_core_preaudit_validators() -> Iterator[None]:
    module = predecessor.predecessor
    originals = {
        "validate_protocol": module.validate_protocol,
        "validate_preaudit": module.validate_preaudit,
    }
    try:
        module.validate_protocol = validate_protocol
        module.validate_preaudit = _V24499_VALIDATE_PREAUDIT
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


def _build_core_preaudit(*, now: int | None = None) -> dict[str, Any]:
    """Build and validate the V2.44.99 core before adding outer bindings."""

    with predecessor.configured_predecessor(), _v24499_core_preaudit_validators():
        return predecessor.predecessor.build_preaudit(now=now)


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor():
        value = _build_core_preaudit(now=now)
    value = copy.deepcopy(value)
    value["validator_binding_successor"] = _validator_binding()
    value["preaudit_builder_ordering_successor"] = _ordering_binding()
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PREAUDIT)
    core = copy.deepcopy(copied)
    core.pop("preaudit_builder_ordering_successor", None)
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PREAUDIT(value=core)
    if (
        copied.get("validator_binding_successor") != _validator_binding()
        or copied.get("preaudit_builder_ordering_successor") != _ordering_binding()
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.01 ordering-safe preaudit drifted")
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
    with configured_predecessor(validators=True):
        predecessor.run_process_subcommand(args)


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
    parser.add_argument(predecessor.predecessor.base.worker_budget.DEADLINE_ORIGIN_ARGUMENT)
    args = parser.parse_args()
    if args.command == "protocol":
        predecessor.predecessor.base.publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit":
        predecessor.predecessor.base.publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        predecessor.predecessor.base.publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        predecessor.predecessor.base.publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_probe()
    elif args.command == "finalize":
        predecessor.predecessor.base.publish(ROOT / DECISION, build_decision())
        predecessor.predecessor.base.publish(ROOT / POSTAUDIT, build_postaudit())
    else:
        run_process_subcommand(args)


if __name__ == "__main__":
    main()
