#!/usr/bin/env python3
"""Post-freeze evaluator and audit for the V2.46.45 external gate.

This post-freeze V2.46.45 control may open evaluator-only gold and provenance.
It never feeds evaluator information back into the frozen forward and never
calls the official DeepWideBench evaluator or any network service.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24645_ror_external_contract import (  # noqa: E402
    DATE,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    PREDICTION_FREEZE,
    PREDICTIONS,
    PROTOCOL_ID,
    SELECTED_COUNT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24645_ror_external_evaluator import (  # noqa: E402
    GOLD,
    PROVENANCE,
    evaluate_frozen_rows,
    gold_rows,
)


EVALUATOR_PROTOCOL = Path(
    f"results/v24645_primary_identity_pair_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v24645_primary_identity_pair_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24645_primary_identity_pair_postresult_audit_v1_{DATE}.json"
)


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.45 evaluator expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.45 evaluator expected object")
    return value


def sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def clean() -> None:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=20,
        ).stdout.strip()

    if git("status", "--porcelain") or git("rev-parse", "HEAD") != git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.45 evaluator requires clean HEAD == target/main")


def preregister(*, now: int | None = None) -> dict[str, Any]:
    forward, audit, freeze = (
        read(ROOT / path)
        for path in (FORWARD_RESULT, FORWARD_AUDIT, PREDICTION_FREEZE)
    )
    if (
        forward.get("role") != "v24645_primary_identity_pair_forward_result"
        or forward.get("protocol_id") != PROTOCOL_ID
        or not sealed(forward, "result_sha256")
        or audit.get("role") != "v24645_primary_identity_pair_forward_audit"
        or not sealed(audit, "audit_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_protocol_design"
        )
        is not True
        or not sealed(freeze, "freeze_sha256")
        or freeze.get("all_predictions_terminal_before_gold_or_evaluator_open")
        is not True
        or freeze.get("gold_path_opened_or_hashed") is not False
        or freeze.get("predictions_sha256") != sha256(ROOT / PREDICTIONS)
    ):
        raise RuntimeError("V2.46.45 evaluator parent drifted")
    gold = gold_rows((ROOT / GOLD).read_text(encoding="utf-8"))
    provenance = read(ROOT / PROVENANCE)
    if (
        provenance.get("role") != "v24645_ror_gold_provenance"
        or not sealed(provenance, "provenance_payload_sha256")
        or provenance.get("commit")
        != "aab1443afefefa8460e69ab01bccceff0a8544d4"
        or provenance.get("directory_tree_sha1")
        != "473b00391664ad5a782605516ba0bea5b4d14e6b"
        or provenance.get("slice_start_inclusive") != 2_000
        or provenance.get("slice_stop_exclusive") != 3_000
        or len(provenance.get("records", [])) != 48
    ):
        raise RuntimeError("V2.46.45 provenance drifted")
    value = {
        "artifact_version": 1,
        "role": "v24645_ror_evaluator_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "selected_tasks": SELECTED_COUNT,
        "gold_rows": len(gold),
        "fixed_denominator_failure_as_zero": True,
        "primary_metric": "exact_table_successes",
        "guardrails": [
            "candidate_composite_not_lower",
            "candidate_item_f1_not_lower",
        ],
        "go_rule": "strict_candidate_exact_table_gain_nonnegative_composite_and_nonnegative_item_f1",
        "unknown_value_cells_diagnostic_only": True,
        "quality_cost_pareto_gate_not_equal_effect_causal_ablation": True,
        "baseline_and_candidate_share_one_prediction_prefix": True,
        "ror_full_url_and_9_character_suffix_semantically_equivalent": True,
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "frozen_predictions_sha256": sha256(ROOT / PREDICTIONS),
        "evaluator_only_gold_sha256": sha256(ROOT / GOLD),
        "evaluator_only_provenance_sha256": sha256(ROOT / PROVENANCE),
        "forward_activation_and_execution_controls_opened_or_hashed_gold": False,
        "external_quality_evaluation_authorized_only_after_prediction_freeze": True,
        "official_deepwidebench_evaluator_called": False,
        "authorization": {
            "one_external_evaluation": True,
            "dev64": False,
            "exact220": False,
        },
    }
    value["protocol_sha256"] = payload_sha256(value)
    return value


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    protocol = read(ROOT / EVALUATOR_PROTOCOL)
    if (
        not sealed(protocol, "protocol_sha256")
        or protocol.get("authorization", {}).get("one_external_evaluation")
        is not True
        or protocol.get("frozen_predictions_sha256") != sha256(ROOT / PREDICTIONS)
        or protocol.get("evaluator_only_gold_sha256") != sha256(ROOT / GOLD)
        or protocol.get("evaluator_only_provenance_sha256")
        != sha256(ROOT / PROVENANCE)
    ):
        raise RuntimeError("V2.46.45 evaluator protocol drifted")
    predictions = [
        json.loads(line)
        for line in (ROOT / PREDICTIONS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    metrics = evaluate_frozen_rows(
        predictions, gold_rows((ROOT / GOLD).read_text(encoding="utf-8"))
    )
    value = {
        "artifact_version": 1,
        "role": "v24645_primary_identity_pair_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "metrics": metrics,
        "passed": metrics["gate_passed"],
        "status": "primary_identity_pair_external_go"
        if metrics["gate_passed"]
        else "primary_identity_pair_external_no_go",
        "fixed_denominator_failure_as_zero": True,
        "quality_evaluation_executed_after_prediction_freeze": True,
        "evaluator_protocol_sha256": sha256(ROOT / EVALUATOR_PROTOCOL),
        "frozen_predictions_sha256": sha256(ROOT / PREDICTIONS),
        "evaluator_only_gold_sha256": sha256(ROOT / GOLD),
        "claim_scope": {
            "harder_benchmark_external_quality_measured": True,
            "primary_identity_bound_missing_cell_quality_measured": True,
            "quality_cost_pareto_gate": True,
            "equal_effect_causal_ablation": False,
            "deepwidebench_quality_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "fresh_dev64_design": metrics["gate_passed"],
            "fresh_dev64_launch": False,
            "new_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def postaudit(*, now: int | None = None) -> dict[str, Any]:
    result = read(ROOT / RESULT)
    protocol = read(ROOT / EVALUATOR_PROTOCOL)
    findings: list[str] = []
    if not sealed(result, "result_sha256") or not sealed(
        protocol, "protocol_sha256"
    ):
        findings.append("result_or_protocol_invalid")
    metrics = result.get("metrics", {})
    arms = metrics.get("arms", {}) if isinstance(metrics, dict) else {}
    if (
        result.get("evaluator_protocol_sha256") != sha256(ROOT / EVALUATOR_PROTOCOL)
        or result.get("fixed_denominator_failure_as_zero") is not True
        or set(arms) != {"baseline", "deterministic_pair"}
        or any(arms[arm].get("tasks") != SELECTED_COUNT for arm in arms)
        or metrics.get("gate_passed") is not result.get("passed")
    ):
        findings.append("binding_denominator_or_gate_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24645_primary_identity_pair_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "evaluator_protocol_sha256": sha256(ROOT / EVALUATOR_PROTOCOL),
        "protected_watchers": protected_watcher_snapshot(),
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_or_official_benchmark_evaluator_called_by_audit": False,
        "authorization": {
            "fresh_dev64_design": not findings and result.get("passed") is True,
            "fresh_dev64_launch": False,
            "new_exact220": False,
        },
    }
    value["audit_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.45 postresult audit failed")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preregister", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "preregister":
        clean()
        value, path = preregister(), EVALUATOR_PROTOCOL
    elif args.command == "evaluate":
        clean()
        value, path = evaluate(), RESULT
    else:
        clean()
        value, path = postaudit(), POSTAUDIT
    publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "status": value.get("status"),
                "passed": value.get("passed"),
                "audit_valid": value.get("audit_valid"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
