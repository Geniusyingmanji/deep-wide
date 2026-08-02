#!/usr/bin/env python3
"""Narrow post-forward validator erratum for V2.42.71.

The frozen runner emitted an execution-start field named
``mapping_control_prediction_...`` but its validator expected the shorter
``mapping_gold_...`` name.  Both fields mean the same strict-false claim.  This
module accepts exactly that one key alias on the already sealed execution
start and otherwise replays the frozen activation, prediction-freeze,
summary, forward-result, and model-slot receipt checks without modifying any
artifact or opening historical control/evaluator resources.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24271_forward_contract import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_PROTOCOL,
    FORWARD_RESULT,
    MODEL_SLOT_CAP,
    PREDICTION_FREEZE,
    RUNNER_MARKER,
    RUN_SUMMARY,
    SELECTED_COUNT,
    validate_protocol,
)
from scripts import run_v24271_keyless_dev64 as frozen  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


EXPECTED_RUNNER_SHA256 = (
    "fb7fa3f0a0ed5849841295aa7e481137e09611cc9b639d9b196aa2873f45997f"
)
EXPECTED_FORWARD_PROTOCOL_SHA256 = (
    "6c16a135eb466dd2cc383c3826bac7ea941ef42b15accd015d9c5986533978c3"
)
EXPECTED_EXECUTION_START_SHA256 = (
    "7ff7c3dc5383f7c4dc2d4a38ba6779e8ecbd788b410847fd208c69143e1cc46b"
)
EXPECTED_PREDICTION_FREEZE_SHA256 = (
    "67bcef768e939213bfd700da934d0901f0207dd00f26124b602e7f8e94823fd7"
)
EXPECTED_FORWARD_RESULT_SHA256 = (
    "c83b53222bff57399e5043218fe786c6633d12a3fe105f97aeca7755b3a60679"
)
EXPECTED_KEY = (
    "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read"
)
ERRATUM_OUTPUT = Path(
    "results/v24271_forward_validator_field_alias_erratum_v1_20260802.json"
)
FROZEN_VALIDATOR_KEY = (
    "mapping_gold_category_question_type_split_evaluator_score_read"
)
ERRATUM_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "status",
        "runner_sha256",
        "forward_protocol_sha256",
        "execution_start_sha256",
        "prediction_freeze_sha256",
        "forward_result_sha256",
        "accepted_alias",
        "accepted_alias_value",
        "selected",
        "terminal_predictions",
        "model_generated_tables",
        "fallback_tables",
        "shared_model_receipts",
        "control_prediction_mapping_gold_or_evaluator_opened_or_hashed",
        "evaluator_side_resource_opened_or_hashed",
        "network_or_api_called",
        "valid",
        "erratum_payload_sha256",
    }
)


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def validate_execution_start_erratum(
    root: Path, protocol: dict[str, Any], activation: dict[str, Any]
) -> dict[str, Any]:
    value = read_object(root / EXECUTION_START)
    runner = value.get("runner")
    expected_keys = set(frozen.EXECUTION_START_KEYS)
    expected_keys.remove(FROZEN_VALIDATOR_KEY)
    expected_keys.add(EXPECTED_KEY)
    if (
        sha256(root / "scripts/run_v24271_keyless_dev64.py")
        != EXPECTED_RUNNER_SHA256
        or sha256(root / FORWARD_PROTOCOL) != EXPECTED_FORWARD_PROTOCOL_SHA256
        or sha256(root / EXECUTION_START) != EXPECTED_EXECUTION_START_SHA256
        or set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role") != "v24271_keyless_dev64_execution_start"
        or value.get("protocol_sha256") != sha256(root / FORWARD_PROTOCOL)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("selected_opaque_ids_sha256")
        != protocol["task_contract"]["selected_opaque_ids_sha256"]
        or not isinstance(runner, dict)
        or set(runner) != {"pid", "start_ticks", "marker"}
        or frozen._nonnegative_int(runner.get("pid"), "runner pid") <= 0
        or frozen._nonnegative_int(runner.get("start_ticks"), "runner start ticks")
        < 0
        or runner.get("marker") != RUNNER_MARKER
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get("label_blind") is not True
        or value.get(EXPECTED_KEY) is not False
        or FROZEN_VALIDATOR_KEY in value
        or value.get("api_called_before_execution_start") is not False
        or not _sealed(value, "execution_start_payload_sha256")
        or activation.get("activation_payload_sha256")
        != read_object(root / ACTIVATION).get("activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.71 execution-start erratum rejected")
    return value


def validate_forward_barrier(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, FORWARD_PROTOCOL)
    activation = frozen.validate_activation(root, protocol)
    execution = validate_execution_start_erratum(root, protocol, activation)
    if sha256(root / PREDICTION_FREEZE) != EXPECTED_PREDICTION_FREEZE_SHA256:
        raise RuntimeError("V2.42.71 prediction freeze is not the attested freeze")
    freeze = read_object(root / PREDICTION_FREEZE)
    rows = frozen.validate_prediction_freeze(root, protocol, freeze)
    if sha256(root / FORWARD_RESULT) != EXPECTED_FORWARD_RESULT_SHA256:
        raise RuntimeError("V2.42.71 forward result is not the attested result")
    forward = read_object(root / FORWARD_RESULT)
    if (
        set(forward) != frozen.FORWARD_KEYS
        or forward.get("artifact_version") != 1
        or forward.get("role") != "v24271_keyless_dev64_forward_result"
        or forward.get("protocol_id") != protocol["protocol_id"]
        or forward.get("selected") != SELECTED_COUNT
        or forward.get("terminal_predictions") != SELECTED_COUNT
        or forward.get("model_generated_tables", -1)
        + forward.get("fallback_tables", -1)
        != SELECTED_COUNT
        or forward.get("prediction_freeze_sha256") != sha256(root / PREDICTION_FREEZE)
        or forward.get("candidate_exact64_before_control_or_evaluator_open") is not True
        or forward.get("control_prediction_mapping_gold_or_evaluator_opened_or_hashed")
        is not False
        or forward.get("label_blind") is not True
        or forward.get("official_evaluator_called") is not False
        or forward.get("new_exact220_or_sota_launched") is not False
        or forward.get("execution_start_sha256") != sha256(root / EXECUTION_START)
        or forward.get("activation_payload_sha256")
        != activation["activation_payload_sha256"]
        or not _sealed(forward, "result_payload_sha256")
    ):
        raise RuntimeError("V2.42.71 forward result erratum rejected")
    summary = read_object(root / RUN_SUMMARY)
    frozen.validate_summary(summary)
    for name in (
        "model_generated_tables",
        "fallback_tables",
        "cost_totals",
        "stage_seconds_sum",
        "wall_seconds_sum",
    ):
        if forward.get(name) != summary.get(name):
            raise RuntimeError(f"V2.42.71 erratum summary binding drifted: {name}")
    receipts = forward.get("shared_model_receipts")
    if not isinstance(receipts, dict) or set(receipts) != frozen.RECEIPT_KEYS:
        raise RuntimeError("V2.42.71 erratum receipt schema drifted")
    for key in frozen.RECEIPT_KEYS - {"all_acquisitions_match_actual_requests"}:
        frozen._nonnegative_int(receipts.get(key), f"receipt.{key}")
    healthy = (
        receipts["children"] == SELECTED_COUNT
        and receipts["present"] == SELECTED_COUNT
        and receipts["valid"] == SELECTED_COUNT
        and receipts["invalid"] == 0
        and receipts["slot_acquisitions"] == receipts["actual_model_requests"]
    )
    if receipts.get("all_acquisitions_match_actual_requests") is not healthy:
        raise RuntimeError("V2.42.71 erratum receipt accounting drifted")
    return {
        "protocol": protocol,
        "activation": activation,
        "execution": execution,
        "freeze": freeze,
        "rows": rows,
        "summary": summary,
        "forward": forward,
    }


def build_erratum(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    barrier = validate_forward_barrier(root)
    forward = barrier["forward"]
    value = {
        "artifact_version": 1,
        "role": "v24271_forward_validator_field_alias_erratum",
        "created_at_unix": int(__import__("time").time()) if now is None else int(now),
        "status": "valid_exact64_forward_with_single_validator_field_alias",
        "runner_sha256": EXPECTED_RUNNER_SHA256,
        "forward_protocol_sha256": EXPECTED_FORWARD_PROTOCOL_SHA256,
        "execution_start_sha256": EXPECTED_EXECUTION_START_SHA256,
        "prediction_freeze_sha256": EXPECTED_PREDICTION_FREEZE_SHA256,
        "forward_result_sha256": EXPECTED_FORWARD_RESULT_SHA256,
        "accepted_alias": {"frozen_validator": FROZEN_VALIDATOR_KEY, "emitted": EXPECTED_KEY},
        "accepted_alias_value": False,
        "selected": SELECTED_COUNT,
        "terminal_predictions": len(barrier["rows"]),
        "model_generated_tables": forward["model_generated_tables"],
        "fallback_tables": forward["fallback_tables"],
        "shared_model_receipts": forward["shared_model_receipts"],
        "control_prediction_mapping_gold_or_evaluator_opened_or_hashed": False,
        "evaluator_side_resource_opened_or_hashed": False,
        "network_or_api_called": False,
        "valid": True,
    }
    value["erratum_payload_sha256"] = payload_sha256(value)
    validate_erratum(value)
    return value


def validate_erratum(value: dict[str, Any]) -> None:
    if (
        set(value) != ERRATUM_KEYS
        or value.get("role") != "v24271_forward_validator_field_alias_erratum"
        or value.get("status")
        != "valid_exact64_forward_with_single_validator_field_alias"
        or value.get("accepted_alias")
        != {"frozen_validator": FROZEN_VALIDATOR_KEY, "emitted": EXPECTED_KEY}
        or value.get("accepted_alias_value") is not False
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal_predictions") != SELECTED_COUNT
        or value.get("model_generated_tables", -1) + value.get("fallback_tables", -1)
        != SELECTED_COUNT
        or value.get("control_prediction_mapping_gold_or_evaluator_opened_or_hashed")
        is not False
        or value.get("evaluator_side_resource_opened_or_hashed") is not False
        or value.get("network_or_api_called") is not False
        or value.get("valid") is not True
        or not _sealed(value, "erratum_payload_sha256")
    ):
        raise RuntimeError("V2.42.71 erratum receipt drifted")


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def validate_committed_erratum(root: Path = ROOT) -> dict[str, Any]:
    value = read_object(root / ERRATUM_OUTPUT)
    validate_erratum(value)
    barrier = validate_forward_barrier(root)
    forward = barrier["forward"]
    if (
        value.get("runner_sha256")
        != sha256(root / "scripts/run_v24271_keyless_dev64.py")
        or value.get("forward_protocol_sha256") != sha256(root / FORWARD_PROTOCOL)
        or value.get("execution_start_sha256") != sha256(root / EXECUTION_START)
        or value.get("prediction_freeze_sha256") != sha256(root / PREDICTION_FREEZE)
        or value.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or value.get("terminal_predictions") != len(barrier["rows"])
        or value.get("model_generated_tables")
        != forward["model_generated_tables"]
        or value.get("fallback_tables") != forward["fallback_tables"]
        or value.get("shared_model_receipts")
        != forward["shared_model_receipts"]
    ):
        raise RuntimeError("V2.42.71 committed erratum is not barrier-bound")
    return value


if __name__ == "__main__":
    value = build_erratum()
    publish_new(ROOT / ERRATUM_OUTPUT, value)
    print(
        json.dumps(
            {"path": str(ERRATUM_OUTPUT), "sha256": sha256(ROOT / ERRATUM_OUTPUT)},
            sort_keys=True,
        )
    )
