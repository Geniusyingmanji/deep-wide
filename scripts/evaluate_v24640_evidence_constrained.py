#!/usr/bin/env python3
"""Post-freeze evaluator and audit for the V2.46.40 external gate."""

from __future__ import annotations

import argparse
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

from deepwide_agent.v24640_ror_external_contract import (  # noqa: E402
    EVALUATOR_PROTOCOL,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    POSTAUDIT,
    PREDICTION_FREEZE,
    PREDICTIONS,
    PROTOCOL_ID,
    RESULT,
    SELECTED_COUNT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24640_ror_external_evaluator import (  # noqa: E402
    GOLD,
    PROVENANCE,
    evaluate_frozen_rows,
    gold_rows,
)


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.40 evaluator expected object")
    return value


def sealed(value: dict, field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def publish(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def clean() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "rev-parse", "target/main"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    if head != remote or dirty:
        raise RuntimeError("V2.46.40 evaluator requires clean HEAD == target/main")


def preregister() -> dict:
    forward, audit, freeze = (
        read(ROOT / path) for path in (FORWARD_RESULT, FORWARD_AUDIT, PREDICTION_FREEZE)
    )
    if (
        forward.get("protocol_id") != PROTOCOL_ID
        or audit.get("audit_valid") is not True
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_protocol_design"
        )
        is not True
        or freeze.get("all_predictions_terminal_before_gold_or_evaluator_open")
        is not True
    ):
        raise RuntimeError("V2.46.40 evaluator parent drifted")
    gold = gold_rows((ROOT / GOLD).read_text(encoding="utf-8"))
    provenance = read(ROOT / PROVENANCE)
    if (
        provenance.get("commit")
        != "aab1443afefefa8460e69ab01bccceff0a8544d4"
        or len(provenance.get("records", [])) != 48
    ):
        raise RuntimeError("V2.46.40 provenance drifted")
    value = {
        "artifact_version": 1,
        "role": "v24640_ror_evaluator_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected_tasks": SELECTED_COUNT,
        "fixed_denominator_failure_as_zero": True,
        "primary_metric": "exact_table_successes",
        "guardrails": ["candidate_composite_not_lower", "candidate_item_f1_not_lower"],
        "go_rule": "strict_candidate_exact_table_gain_nonnegative_composite_and_nonnegative_item_f1",
        "unknown_value_cells_diagnostic_only": True,
        "ror_full_url_and_9_character_suffix_semantically_equivalent": True,
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "frozen_predictions_sha256": sha256(ROOT / PREDICTIONS),
        "evaluator_only_gold_sha256": sha256(ROOT / GOLD),
        "evaluator_only_provenance_sha256": sha256(ROOT / PROVENANCE),
        "gold_rows": len(gold),
        "predictions_frozen_before_gold_open": True,
        "official_deepwidebench_evaluator_called": False,
        "authorization": {
            "one_external_evaluation": True,
            "dev64": False,
            "exact220": False,
        },
    }
    value["protocol_sha256"] = payload_sha256(value)
    return value


def evaluate() -> dict:
    protocol = read(ROOT / EVALUATOR_PROTOCOL)
    if (
        not sealed(protocol, "protocol_sha256")
        or protocol.get("frozen_predictions_sha256") != sha256(ROOT / PREDICTIONS)
        or protocol.get("evaluator_only_gold_sha256") != sha256(ROOT / GOLD)
        or protocol.get("evaluator_only_provenance_sha256") != sha256(ROOT / PROVENANCE)
    ):
        raise RuntimeError("V2.46.40 evaluator protocol drifted")
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
        "role": "v24640_evidence_constrained_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "metrics": metrics,
        "passed": metrics["gate_passed"],
        "status": "evidence_constrained_external_go"
        if metrics["gate_passed"]
        else "evidence_constrained_external_no_go",
        "fixed_denominator_failure_as_zero": True,
        "evaluator_protocol_sha256": sha256(ROOT / EVALUATOR_PROTOCOL),
        "frozen_predictions_sha256": sha256(ROOT / PREDICTIONS),
        "evaluator_only_gold_sha256": sha256(ROOT / GOLD),
        "claim_scope": {
            "harder_benchmark_external_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "entropy_causal_credit_validated": False,
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


def postaudit() -> dict:
    result = read(ROOT / RESULT)
    protocol = read(ROOT / EVALUATOR_PROTOCOL)
    findings = []
    if not sealed(result, "result_sha256") or not sealed(protocol, "protocol_sha256"):
        findings.append("result_or_protocol_invalid")
    if (
        result.get("evaluator_protocol_sha256") != sha256(ROOT / EVALUATOR_PROTOCOL)
        or result.get("fixed_denominator_failure_as_zero") is not True
    ):
        findings.append("binding_or_denominator_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24640_evidence_constrained_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
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
        raise RuntimeError("V2.46.40 postresult audit failed")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preregister", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "preregister":
        value, path = preregister(), EVALUATOR_PROTOCOL
    elif args.command == "evaluate":
        clean()
        value, path = evaluate(), RESULT
    else:
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
