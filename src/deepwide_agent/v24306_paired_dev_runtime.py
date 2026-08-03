"""Exact V2.43.03 task runtime reused by the V2.43.06 low-cap experiment.

V2.43.06 changes only the cross-task global model-slot cap in its forward
contract.  The per-task baseline/candidate behavior, receipts, budgets, and
validation therefore remain the already-audited V2.43.03 implementation.
Aliases are intentional: they make an accidental runtime fork mechanically
detectable instead of relying on two copied implementations staying equal.
"""

from __future__ import annotations

from .v24303_paired_dev_runtime import (  # noqa: F401
    ARMS,
    POLICY_ID,
    RECEIPT_FIELD,
    RECEIPT_ROLE,
    SynthesisRecoveryControlModel,
    run_v24303_task,
    validate_receipt,
    validate_v24303_result,
    zero_effect_receipt,
)


run_v24306_task = run_v24303_task
validate_v24306_result = validate_v24303_result


__all__ = [
    "ARMS",
    "POLICY_ID",
    "RECEIPT_FIELD",
    "RECEIPT_ROLE",
    "SynthesisRecoveryControlModel",
    "run_v24306_task",
    "validate_receipt",
    "validate_v24306_result",
    "zero_effect_receipt",
]
