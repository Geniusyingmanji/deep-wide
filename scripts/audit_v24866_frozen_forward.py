#!/usr/bin/env python3
"""Read-only pre-evaluator audit for the frozen V2.48.66 forward."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24866_coverage_revision_exact220_contract as contract  # noqa: E402
from scripts import run_v24866_coverage_revision_exact220 as runner  # noqa: E402


OUTPUT = contract.FORWARD_AUDIT


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def main() -> None:
    protocol = runner._read(ROOT / contract.PROTOCOL)
    forward = runner._read(ROOT / contract.FORWARD_RESULT)
    summary = runner._read(ROOT / contract.RUN_SUMMARY)
    freeze = runner._read(ROOT / contract.PREDICTION_FREEZE)
    rows = [
        json.loads(line)
        for line in (ROOT / contract.RUNTIME_PREDICTIONS)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    tasks = contract.task_vector(ROOT, protocol)
    hashes = [row.get("prediction_sha256") for row in rows]
    checks = {
        "head_equals_target_main": _git("rev-parse", "HEAD")
        == _git("rev-parse", "target/main"),
        "worktree_clean": _git("status", "--porcelain") == "",
        "forward_result_tracked": subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(contract.FORWARD_RESULT)],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0,
        "selected_terminal_exact220": forward.get("selected") == 220
        and forward.get("terminal_predictions") == 220
        and summary.get("selected") == 220
        and summary.get("completed") == 220
        and freeze.get("selected") == 220
        and freeze.get("terminal") == 220
        and len(rows) == 220,
        "prediction_order_bound": [row.get("opaque_id") for row in rows]
        == [task["opaque_id"] for task in tasks],
        "prediction_hash_vector_bound": freeze.get("prediction_hashes_sha256")
        == contract.payload_sha256(hashes),
        "runtime_and_summary_hashes_bound": freeze.get(
            "runtime_predictions_sha256"
        )
        == contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS)
        and freeze.get("run_summary_sha256")
        == contract.sha256(ROOT / contract.RUN_SUMMARY),
        "all_predictions_label_blind": all(
            row.get("status") == "completed"
            and row.get("label_blind") is True
            and row.get(
                "mapping_gold_category_question_type_split_evaluator_score_read"
            )
            is False
            for row in rows
        ),
        "mapping_and_evaluator_closed_during_forward": freeze.get(
            "mapping_gold_or_evaluator_opened_or_hashed"
        )
        is False
        and forward.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is False
        and forward.get("official_evaluator_called") is False,
        "fixed_denominator_counts": int(summary.get("model_generated_tables", -1))
        + int(summary.get("fallback_tables", -1))
        == 220,
        "coverage_bundle_accounting": summary.get(
            "coverage_revision_totals"
        )
        == forward.get("coverage_revision_totals")
        and summary.get("coverage_revision_totals", {}).get("valid_bundles")
        + summary.get("coverage_revision_totals", {}).get(
            "invalid_or_missing_bundles"
        )
        == 220,
        "entropy_shadow_only": summary.get(
            "coverage_revision_totals", {}
        ).get("entropy_or_information_gain_used_for_admission_or_routing")
        is False,
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
        "forward_processes_absent": not any(
            marker in line
            for line in subprocess.run(
                ["ps", "-eo", "args="], stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, timeout=20, check=False,
            ).stdout.splitlines()
            if "ps -eo" not in line
            for marker in (contract.RUNNER_MARKER, contract.CHILD_MARKER)
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24866_coverage_revision_exact220_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "runtime_predictions_sha256": contract.sha256(
            ROOT / contract.RUNTIME_PREDICTIONS
        ),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "selected": 220,
        "terminal_predictions": 220,
        "model_generated_tables": summary["model_generated_tables"],
        "fallback_tables": summary["fallback_tables"],
        "coverage_revision_totals": summary["coverage_revision_totals"],
        "forward_wall_seconds": summary["forward_wall_seconds"],
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "postfreeze_exact220_evaluator_protocol": not findings,
            "forward_retry_resume_skip_or_rerun": False,
            "selective_evaluation_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_audit": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    descriptor = os.open(
        ROOT / OUTPUT,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"audit_valid": not findings, "findings": findings}))


if __name__ == "__main__":
    main()
