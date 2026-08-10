"""Append-only, zero-network recovery of the V2.50.27 quality evaluation."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25027_clue_resolved_external_contract as parent


DATE = "20260810"
PROTOCOL_ID = "v25028_read_only_clue_quality_recovery_v1"
PROTOCOL = Path(f"results/v25028_clue_quality_recovery_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25028_clue_quality_recovery_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25028_clue_quality_recovery_postresult_audit_v1_{DATE}.json")
FAILURE = Path(f"results/v25027_clue_resolved_external_evaluation_failure_v1_{DATE}.json")
PARENT_PROTOCOL = parent.PROTOCOL
PARENT_FORWARD = parent.FORWARD_RESULT
PARENT_AUDIT = parent.FORWARD_AUDIT
PARENT_EVALUATOR_PROTOCOL = parent.EVALUATOR_PROTOCOL
FROZEN_ROWS = parent.TASK_RESULTS
PREDICTION_FREEZE = parent.PREDICTION_FREEZE
FROZEN_GOLD = parent.POSTFREEZE_GOLD
SOURCE = Path("src/deepwide_agent/v25028_clue_evaluation_recovery_contract.py")
RUNNER = Path("scripts/recover_v25028_clue_evaluation.py")
TEST = Path("tests/test_recover_v25028_clue_evaluation.py")
EVALUATOR = parent.EVALUATOR
LOCAL_SOURCES = (SOURCE, RUNNER, TEST, EVALUATOR)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
seal = parent.seal
sealed = parent.sealed
git = parent.git


def source_policy() -> dict[str, Any]:
    return {
        "read_only_inputs": [
            str(FROZEN_ROWS), str(PREDICTION_FREEZE), str(FROZEN_GOLD),
            str(FAILURE), str(PARENT_FORWARD), str(PARENT_AUDIT),
            str(PARENT_EVALUATOR_PROTOCOL),
        ],
        "network_model_search_fetch_or_forward_effect": False,
        "gold_refetch": False,
        "prediction_retry_resume_skip_or_selective_revaluation": False,
        "all_twenty_tasks_and_both_arms_evaluated_once": True,
        "fixed_denominator_failure_as_zero": True,
        "original_failed_attempt_evaluated_prediction_rows": 0,
        "public_exact220_or_sota_authorized": False,
    }


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in LOCAL_SOURCES:
        path = root / relative
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.50.28 source path drifted")
        if tracked:
            parent.git(root, "ls-files", "--error-unmatch", str(relative))
        output[str(relative)] = sha256(path)
    return output


def build_protocol(root: Path, *, now: int, tracked: bool = True) -> dict[str, Any]:
    manifest = dependency_manifest(root, tracked=tracked)
    inputs = {
        str(FROZEN_ROWS): sha256(root / FROZEN_ROWS),
        str(PREDICTION_FREEZE): sha256(root / PREDICTION_FREEZE),
        str(FROZEN_GOLD): sha256(root / FROZEN_GOLD),
        str(FAILURE): sha256(root / FAILURE),
        str(PARENT_FORWARD): sha256(root / PARENT_FORWARD),
        str(PARENT_AUDIT): sha256(root / PARENT_AUDIT),
        str(PARENT_EVALUATOR_PROTOCOL): sha256(root / PARENT_EVALUATOR_PROTOCOL),
    }
    value = {
        "artifact_version": 1,
        "role": "v25028_clue_quality_recovery_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD"),
        "fixed_denominator": parent.TASK_COUNT,
        "fixed_arm_count": len(parent.ARMS),
        "frozen_input_manifest": inputs,
        "frozen_input_manifest_sha256": payload_sha256(inputs),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "quality_gate": parent.quality_gate(),
        "source_policy": source_policy(),
        "authorization": {
            "one_read_only_recovery_evaluation": True,
            "network_or_gold_refetch": False,
            "public_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any], *, tracked: bool = True) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = build_protocol(root, now=int(copied.get("created_at_unix", -1)), tracked=tracked)
    expected["git_head"] = copied.get("git_head")
    expected = seal(expected, "protocol_payload_sha256")
    if (
        copied != expected
        or not isinstance(copied.get("git_head"), str)
        or len(copied["git_head"]) != 40
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.50.28 recovery protocol drifted")
    return copied


def read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.50.28 expected ordinary JSON")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.28 expected JSON object")
    return value


__all__ = [
    "FAILURE", "FROZEN_GOLD", "FROZEN_ROWS", "LOCAL_SOURCES", "PARENT_AUDIT",
    "PARENT_EVALUATOR_PROTOCOL", "PARENT_FORWARD", "POSTAUDIT", "PREDICTION_FREEZE",
    "PROTOCOL", "PROTOCOL_ID", "RESULT", "RUNNER", "SOURCE", "TEST",
    "build_protocol", "dependency_manifest", "git", "payload_sha256", "read_json",
    "seal", "sealed", "sha256", "source_policy", "validate_protocol",
]
