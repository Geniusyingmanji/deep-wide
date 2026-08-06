#!/usr/bin/env python3
"""Post-freeze evaluator control for the V2.46.51 structured-lookup gate.

Only this post-freeze control may open evaluator-only gold and provenance.  It
never feeds evaluator information back into the frozen forward and never calls
the official DeepWideBench evaluator, a model, search, fetch, or network
service.  The single evaluation is bound to immutable frozen predictions and a
separately published evaluator preregistration.
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

from deepwide_agent.v24651_ror_external_contract import (  # noqa: E402
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
from deepwide_agent.v24651_ror_external_evaluator import (  # noqa: E402
    ARMS,
    GOLD,
    PROVENANCE,
    evaluate_frozen_rows,
    gold_rows,
)


EVALUATOR_PROTOCOL = Path(
    f"results/v24654_v24651_unknown_target_structured_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24654_v24651_unknown_target_structured_result_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24654_v24651_unknown_target_structured_postresult_audit_v1_{DATE}.json"
)
SOURCE_FILES = (
    Path("src/deepwide_agent/v24651_ror_external_evaluator.py"),
    Path("scripts/evaluate_v24654_v24651_unknown_target_structured.py"),
    Path("tests/test_evaluate_v24654_v24651_unknown_target_structured.py"),
)


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.54 evaluator expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.54 evaluator expected object")
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


def clean() -> None:
    if git("status", "--porcelain") or git("rev-parse", "HEAD") != git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.54 evaluator requires clean HEAD == target/main")


def absent(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise RuntimeError("V2.46.54 evaluator output is not pristine")


def source_manifest() -> dict[str, str]:
    return {str(path): sha256(ROOT / path) for path in SOURCE_FILES}


def _validate_parent() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    forward, audit, freeze = (
        read(ROOT / path)
        for path in (FORWARD_RESULT, FORWARD_AUDIT, PREDICTION_FREEZE)
    )
    discovery = audit.get("checks", {}).get("discovery", {})
    if (
        forward.get("role") != "v24651_unknown_target_structured_forward_result"
        or forward.get("protocol_id") != PROTOCOL_ID
        or not sealed(forward, "result_sha256")
        or audit.get("role") != "v24651_unknown_target_structured_forward_audit"
        or not sealed(audit, "audit_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("checks", {}).get("mechanism_triggered") is not True
        or not isinstance(discovery.get("admitted_replacement_count"), int)
        or discovery.get("admitted_replacement_count", 0) <= 0
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_protocol_design"
        )
        is not True
        or not sealed(freeze, "freeze_sha256")
        or freeze.get("all_predictions_terminal_before_gold_or_evaluator_open")
        is not True
        or freeze.get("gold_path_opened_or_hashed") is not False
        or freeze.get("predictions_sha256") != sha256(ROOT / PREDICTIONS)
        or forward.get("prediction_freeze_sha256") != sha256(ROOT / PREDICTION_FREEZE)
        or audit.get("forward_sha256") != sha256(ROOT / FORWARD_RESULT)
    ):
        raise RuntimeError("V2.46.54 evaluator parent drifted")
    return forward, audit, freeze


def _validate_evaluator_surfaces() -> tuple[list[dict[str, str]], dict[str, Any]]:
    gold = gold_rows((ROOT / GOLD).read_text(encoding="utf-8"))
    provenance = read(ROOT / PROVENANCE)
    if (
        provenance.get("role") != "v24651_ror_gold_provenance"
        or not sealed(provenance, "provenance_payload_sha256")
        or provenance.get("commit")
        != "aab1443afefefa8460e69ab01bccceff0a8544d4"
        or provenance.get("directory_tree_sha1")
        != "473b00391664ad5a782605516ba0bea5b4d14e6b"
        or provenance.get("slice_start_inclusive") != 3_000
        or provenance.get("slice_stop_exclusive") != 3_482
        or len(provenance.get("records", [])) != 48
        or provenance.get("forward_import_or_runtime_read_authorized") is not False
        or provenance.get("gold_open_before_prediction_freeze_authorized") is not False
    ):
        raise RuntimeError("V2.46.54 provenance drifted")
    return gold, provenance


def preregister(*, now: int | None = None) -> dict[str, Any]:
    absent(ROOT / EVALUATOR_PROTOCOL)
    _forward, audit, _freeze = _validate_parent()
    gold, _provenance = _validate_evaluator_surfaces()
    manifest = source_manifest()
    value = {
        "artifact_version": 1,
        "role": "v24654_v24651_ror_evaluator_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "base_commit": git("rev-parse", "HEAD"),
        "selected_tasks": SELECTED_COUNT,
        "gold_rows": len(gold),
        "mechanism_admitted_replacement_count": audit["checks"]["discovery"][
            "admitted_replacement_count"
        ],
        "fixed_denominator_failure_as_zero": True,
        "primary_metric": "exact_table_successes",
        "guardrails": [
            "candidate_composite_not_lower",
            "candidate_item_f1_not_lower",
        ],
        "go_rule": "strict_candidate_exact_table_gain_nonnegative_composite_and_nonnegative_item_f1",
        "unknown_value_cells_diagnostic_only": True,
        "quality_cost_pareto_gate_not_equal_effect_causal_ablation": True,
        "baseline_and_candidate_share_one_frozen_prediction_prefix": True,
        "ror_full_url_and_9_character_suffix_semantically_equivalent": True,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "frozen_predictions_sha256": sha256(ROOT / PREDICTIONS),
        "evaluator_only_gold_sha256": sha256(ROOT / GOLD),
        "evaluator_only_provenance_sha256": sha256(ROOT / PROVENANCE),
        "gold_and_provenance_opened_by_this_control_only_after_prediction_freeze": True,
        "forward_activation_execution_and_forward_audit_opened_or_hashed_gold": False,
        "external_quality_evaluation_authorized_only_after_prediction_freeze": True,
        "network_model_search_fetch_or_official_deepwidebench_evaluator_called": False,
        "authorization": {
            "one_external_evaluation": True,
            "dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_sha256"] = payload_sha256(value)
    return value


def _validate_evaluator_protocol() -> dict[str, Any]:
    protocol = read(ROOT / EVALUATOR_PROTOCOL)
    manifest = protocol.get("source_manifest")
    if (
        protocol.get("role") != "v24654_v24651_ror_evaluator_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or not sealed(protocol, "protocol_sha256")
        or protocol.get("authorization", {}).get("one_external_evaluation")
        is not True
        or not isinstance(manifest, dict)
        or protocol.get("source_manifest_sha256") != payload_sha256(manifest)
        or manifest != source_manifest()
        or protocol.get("forward_result_sha256") != sha256(ROOT / FORWARD_RESULT)
        or protocol.get("forward_audit_sha256") != sha256(ROOT / FORWARD_AUDIT)
        or protocol.get("prediction_freeze_sha256")
        != sha256(ROOT / PREDICTION_FREEZE)
        or protocol.get("frozen_predictions_sha256") != sha256(ROOT / PREDICTIONS)
        or protocol.get("evaluator_only_gold_sha256") != sha256(ROOT / GOLD)
        or protocol.get("evaluator_only_provenance_sha256")
        != sha256(ROOT / PROVENANCE)
    ):
        raise RuntimeError("V2.46.54 evaluator protocol drifted")
    return protocol


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    absent(ROOT / RESULT)
    protocol = _validate_evaluator_protocol()
    predictions = [
        json.loads(line)
        for line in (ROOT / PREDICTIONS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gold, _provenance = _validate_evaluator_surfaces()
    metrics = evaluate_frozen_rows(predictions, gold)
    passed = metrics["gate_passed"]
    value = {
        "artifact_version": 1,
        "role": "v24654_v24651_unknown_target_structured_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "metrics": metrics,
        "passed": passed,
        "status": "unknown_target_structured_external_go"
        if passed
        else "unknown_target_structured_external_no_go",
        "fixed_denominator_failure_as_zero": True,
        "quality_evaluation_executed_once_after_prediction_freeze": True,
        "evaluator_protocol_sha256": sha256(ROOT / EVALUATOR_PROTOCOL),
        "frozen_predictions_sha256": sha256(ROOT / PREDICTIONS),
        "evaluator_only_gold_sha256": sha256(ROOT / GOLD),
        "evaluator_only_provenance_sha256": sha256(ROOT / PROVENANCE),
        "claim_scope": {
            "fresh_harder_external_ror_quality_measured": True,
            "unknown_target_official_structured_lookup_quality_measured": True,
            "quality_cost_pareto_gate": True,
            "equal_effect_causal_ablation": False,
            "deepwidebench_quality_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "network_model_search_fetch_or_official_deepwidebench_evaluator_called_by_evaluation": False,
        "authorization": {
            "fresh_dev64_design": passed,
            "fresh_dev64_launch": False,
            "new_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def _metrics_valid(metrics: Any) -> bool:
    if not isinstance(metrics, dict):
        return False
    arms = metrics.get("arms")
    delta = metrics.get("candidate_minus_baseline")
    if not isinstance(arms, dict) or set(arms) != set(ARMS) or not isinstance(delta, dict):
        return False
    if any(arms[arm].get("tasks") != SELECTED_COUNT for arm in ARMS):
        return False
    baseline = arms["baseline"]
    candidate = arms["unknown_target_structured"]
    keys = (
        "exact_table_successes",
        "entity_recall",
        "row_f1",
        "item_f1",
        "column_f1",
        "composite",
    )
    try:
        exact_deltas = {
            key: candidate[key] - baseline[key]
            for key in keys
        }
    except (KeyError, TypeError):
        return False
    if any(abs(float(delta.get(key, float("inf"))) - float(exact_deltas[key])) > 1e-12 for key in keys):
        return False
    gate = (
        exact_deltas["exact_table_successes"] > 0
        and exact_deltas["composite"] >= 0
        and exact_deltas["item_f1"] >= 0
    )
    return metrics.get("gate_passed") is gate


def postaudit(*, now: int | None = None) -> dict[str, Any]:
    absent(ROOT / POSTAUDIT)
    result = read(ROOT / RESULT)
    protocol = read(ROOT / EVALUATOR_PROTOCOL)
    findings: list[str] = []
    if not sealed(result, "result_sha256") or not sealed(
        protocol, "protocol_sha256"
    ):
        findings.append("result_or_protocol_invalid")
    metrics = result.get("metrics")
    if (
        result.get("evaluator_protocol_sha256") != sha256(ROOT / EVALUATOR_PROTOCOL)
        or result.get("frozen_predictions_sha256") != sha256(ROOT / PREDICTIONS)
        or result.get("fixed_denominator_failure_as_zero") is not True
        or not _metrics_valid(metrics)
        or not isinstance(metrics, dict)
        or metrics.get("gate_passed") is not result.get("passed")
    ):
        findings.append("binding_denominator_metrics_or_gate_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24654_v24651_unknown_target_structured_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "evaluator_protocol_sha256": sha256(ROOT / EVALUATOR_PROTOCOL),
        "protected_watchers": protected_watcher_snapshot(),
        "findings": findings,
        "audit_valid": not findings,
        "gold_or_provenance_opened_or_hashed_by_postresult_audit": False,
        "network_model_search_fetch_or_official_benchmark_evaluator_called_by_audit": False,
        "authorization": {
            "fresh_dev64_design": not findings and result.get("passed") is True,
            "fresh_dev64_launch": False,
            "new_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.54 postresult audit failed")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preregister", "evaluate", "postaudit"))
    args = parser.parse_args()
    clean()
    if args.command == "preregister":
        value, path = preregister(), EVALUATOR_PROTOCOL
    elif args.command == "evaluate":
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
