#!/usr/bin/env python3
"""Publish the content-free V2.48.77 pre-subprocess launch failure."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24877_keyless_coverage_exact220_contract as contract  # noqa: E402


RESULT = Path("results/v24877_keyless_coverage_exact220_launch_failure_v1_20260808.json")


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.48.77 launch-failure source is absent")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.77 expected object")
    return value


def build() -> dict:
    if (ROOT / RESULT).exists() or (ROOT / RESULT).is_symlink():
        raise FileExistsError(RESULT)
    forward = _read(ROOT / contract.FORWARD_RESULT)
    summary = _read(ROOT / contract.RUN_SUMMARY)
    freeze = _read(ROOT / contract.PREDICTION_FREEZE)
    if (
        forward.get("terminal_predictions") != 220
        or forward.get("fallback_tables") != 220
        or forward.get("model_generated_tables") != 0
        or forward.get("system_total_tokens") != 0
        or forward.get("coverage_revision_totals", {}).get("valid_bundles") != 0
        or forward.get("keyless_effect_totals", {}).get("provider_attempts") != 0
        or summary.get("parent_exit_taxonomy") != {"parent_unobserved": 220}
        or summary.get("model_requests") != 0
        or summary.get("search_calls") != 0
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
    ):
        raise RuntimeError("V2.48.77 failure signature drifted")
    value = {
        "artifact_version": 1,
        "role": "v24877_keyless_coverage_exact220_launch_failure",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "invalid_for_quality_comparison_pre_subprocess_runner_failure",
        "selected": 220,
        "terminal_failure_as_zero_predictions": 220,
        "observed": {
            "forward_wall_seconds": forward["forward_wall_seconds"],
            "model_requests": 0,
            "search_response_calls": 0,
            "provider_attempts": 0,
            "fetch_calls": 0,
            "valid_bundles": 0,
            "parent_unobserved": 220,
        },
        "cause": {
            "failure_boundary": "runner_before_child_subprocess_spawn",
            "coarse_type": "recursive_child_environment_binding",
            "private_task_query_url_page_prediction_answer_or_credential_read_by_diagnosis": False,
        },
        "provenance": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        },
        "authorization": {
            "v24877_resume_retry_skip_or_selective_rerun": False,
            "v24877_evaluator": False,
            "append_only_corrected_successor_design": True,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
    }
    value["result_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    value = build()
    path = ROOT / RESULT
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"path": str(RESULT), "status": value["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
