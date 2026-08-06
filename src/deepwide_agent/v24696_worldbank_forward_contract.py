"""Append-only execution constants for the frozen V2.46.94 surface."""

from __future__ import annotations


CHILD_TERMINAL_NAME = "child_terminal_receipt.json"
PARENT_EXIT_NAME = "parent_exit_receipt.json"
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
TASK_WALL_SECONDS = 240.0
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_ATTEMPT_SECONDS = 0.05


__all__ = [
    "CHILD_TERMINAL_NAME",
    "CLEANUP_RESERVE_SECONDS",
    "MINIMUM_ATTEMPT_SECONDS",
    "MODEL_SLOT_POOL_ID",
    "PARENT_EXIT_NAME",
    "TASK_WALL_SECONDS",
]
