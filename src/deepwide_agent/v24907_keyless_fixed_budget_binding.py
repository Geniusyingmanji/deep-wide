"""Static child-process binding for the frozen no-entropy full-budget policy.

The binding changes only the two-wave policy supplied to the already validated
keyless task runtime.  Model, prompt, search transport, hard budgets, deadline,
and output contracts remain caller-owned and are checked before assignment.
"""

from __future__ import annotations

import copy
import dataclasses
from types import ModuleType
from typing import Any, Mapping

from .v24799_fixed_full_budget_control import (
    POLICY_VALUES,
    fixed_full_budget_policy,
)


POLICY_ID = "v24907_keyless_fixed_full_budget_child_binding_v1"
REQUIRED_LIMITS = {
    "wall_seconds": 240,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
}


def fixed_policy_values() -> dict[str, Any]:
    value = dataclasses.asdict(fixed_full_budget_policy())
    if value != POLICY_VALUES:
        raise RuntimeError("V2.49.07 fixed policy drifted")
    return copy.deepcopy(value)


def validate_binding_contract(
    *, limits: Mapping[str, Any], model_slot_cap: int, executor_concurrency: int
) -> None:
    if (
        any(limits.get(name) != expected for name, expected in REQUIRED_LIMITS.items())
        or isinstance(model_slot_cap, bool)
        or model_slot_cap != 8
        or isinstance(executor_concurrency, bool)
        or executor_concurrency != 20
    ):
        raise ValueError("V2.49.07 production budget or capacity drifted")


def bind_child_algorithm(algorithm: ModuleType, contract: ModuleType) -> None:
    """Bind a child-local module namespace; no shared parent process is mutated."""

    validate_binding_contract(
        limits=contract.LIMITS,
        model_slot_cap=contract.MODEL_SLOT_CAP,
        executor_concurrency=contract.EXECUTOR_CONCURRENCY,
    )
    bindings = {
        "OUTPUT_ROOT": contract.OUTPUT_ROOT,
        "TASK_ROOT": contract.TASK_ROOT,
        "MODEL_SLOT_DIRECTORY": contract.MODEL_SLOT_DIRECTORY,
        "LIMITS": copy.deepcopy(contract.LIMITS),
        "MODEL": copy.deepcopy(contract.MODEL),
        "SEARCH": copy.deepcopy(contract.SEARCH),
        "TWO_WAVE_POLICY": fixed_policy_values(),
    }
    for name, value in bindings.items():
        setattr(algorithm, name, value)


__all__ = [
    "POLICY_ID",
    "REQUIRED_LIMITS",
    "bind_child_algorithm",
    "fixed_policy_values",
    "validate_binding_contract",
]
