#!/usr/bin/env python3
"""Post-freeze evaluator control for the V2.46.94 World Bank gate.

Only this control may open the evaluator-only gold and provenance after the
12-task, three-arm predictions and the repaired content-free forward audit are
frozen.  It performs no model, search, fetch, network, benchmark, or official
DeepWideBench evaluator call and cannot feed evaluator information back into
the completed forward pass.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24694_worldbank_external_contract import (  # noqa: E402
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
from deepwide_agent.v24694_worldbank_external_evaluator import (  # noqa: E402
    ARMS,
    GOLD,
    PROVENANCE,
    evaluate_frozen_rows,
    gold_rows,
)


EVALUATOR_PROTOCOL = Path(
    f"results/v24700_v24694_worldbank_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v24700_v24694_worldbank_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24700_v24694_worldbank_postresult_audit_v1_{DATE}.json"
)
SOURCE_FILES = (
    Path("src/deepwide_agent/v24694_worldbank_external_evaluator.py"),
    Path("scripts/evaluate_v24700_v24694_worldbank_target_value.py"),
    Path("tests/test_evaluate_v24700_v24694_worldbank_target_value.py"),
)


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.47.00 evaluator expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.00 evaluator expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
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
        raise RuntimeError("V2.47.00 evaluator requires clean HEAD == target/main")


def absent(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise RuntimeError("V2.47.00 evaluator output is not pristine")


def source_manifest() -> dict[str, str]:
    return {str(path): sha256(ROOT / path) for path in SOURCE_FILES}


def _validate_parent() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    forward, audit, freeze = (
        read(ROOT / path)
        for path in (FORWARD_RESULT, FORWARD_AUDIT, PREDICTION_FREEZE)
    )
    checks = audit.get("checks", {})
    repair = audit.get("repair", {})
    if (
        forward.get("role") != "v24694_worldbank_forward_result"
        or forward.get("protocol_id") != PROTOCOL_ID
        or not sealed(forward, "result_sha256")
        or audit.get("role") != "v24699_v24694_worldbank_forward_audit"
        or not sealed(audit, "audit_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or checks.get("mechanism_triggered") is not True
        or checks.get("target_value_differs_from_expanded_tasks", 0) <= 0
        or checks.get("requested_target_count") != SELECTED_COUNT * 8
        or repair.get("lookup_category_conservation") is not True
        or repair.get("completion_category_conservation") is not True
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_protocol_design"
        )
        is not True
        or audit.get("authorization", {}).get("evaluator_execution") is not False
        or not sealed(freeze, "freeze_sha256")
        or freeze.get("all_predictions_terminal_before_gold_or_evaluator_open")
        is not True
        or freeze.get("gold_or_provenance_path_opened_or_hashed") is not False
        or freeze.get("predictions_sha256") != sha256(ROOT / PREDICTIONS)
        or forward.get("prediction_freeze_sha256")
        != sha256(ROOT / PREDICTION_FREEZE)
        or audit.get("forward_sha256") != sha256(ROOT / FORWARD_RESULT)
    ):
        raise RuntimeError("V2.47.00 evaluator parent drifted")
    return forward, audit, freeze


def _validate_evaluator_surfaces() -> tuple[list[dict[str, str]], dict[str, Any]]:
    gold = gold_rows((ROOT / GOLD).read_text(encoding="utf-8"))
    provenance = read(ROOT / PROVENANCE)
    records = provenance.get("records")
    if (
        provenance.get("role") != "v24694_worldbank_gold_provenance"
        or not sealed(provenance, "provenance_payload_sha256")
        or not isinstance(records, list)
        or len(records) != 96
        or provenance.get("forward_import_or_runtime_read_authorized") is not False
        or provenance.get("gold_open_before_prediction_freeze_authorized") is not False
        or provenance.get("append_only_repair", {}).get("invalid_predecessor")
        != "v24691"
        or provenance.get("append_only_repair", {}).get(
            "population_gold_values_and_provenance_unchanged"
        )
        is not True
    ):
        raise RuntimeError("V2.47.00 evaluator provenance drifted")
    identities = {
        (
            str(record.get("opaque_id", "")),
            str(record.get("iso3", "")),
            str(record.get("indicator", "")),
            str(record.get("year", "")),
        )
        for record in records
        if isinstance(record, Mapping)
    }
    if len(identities) != 96:
        raise RuntimeError("V2.47.00 evaluator provenance identity drifted")
    return gold, provenance


def preregister(*, now: int | None = None) -> dict[str, Any]:
    absent(ROOT / EVALUATOR_PROTOCOL)
    _forward, audit, _freeze = _validate_parent()
    gold, provenance = _validate_evaluator_surfaces()
    manifest = source_manifest()
    value = {
        "artifact_version": 1,
        "role": "v24700_v24694_worldbank_evaluator_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "base_commit": git("rev-parse", "HEAD"),
        "selected_tasks": SELECTED_COUNT,
        "gold_rows": len(gold),
        "provenance_records": len(provenance["records"]),
        "mechanism_changed_task_count": audit["checks"][
            "target_value_differs_from_expanded_tasks"
        ],
        "valid_exact_record_count": audit["checks"]["valid_exact_record_count"],
        "missing_response_count": audit["checks"]["missing_response_count"],
        "fixed_denominator_failure_as_zero": True,
        "primary_comparison": "target_value_minus_expanded_parser",
        "primary_metric": "exact_table_successes",
        "guardrails": [
            "target_value_composite_not_lower",
            "target_value_item_f1_not_lower",
        ],
        "go_rule": "strict_target_value_exact_table_gain_nonnegative_composite_and_nonnegative_item_f1",
        "parser_comparison_diagnostic": "expanded_parser_minus_frozen_parser",
        "unknown_value_cells_diagnostic_only": True,
        "quality_cost_pareto_gate_not_equal_effect_causal_ablation": True,
        "entropy_shadow_only_not_routing_or_credit": True,
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
        "network_model_search_fetch_or_official_deepwidebench_evaluator_called": False,
        "authorization": {
            "one_external_evaluation": True,
            "fresh_deepwidebench_candidate_design": False,
            "dev64_launch": False,
            "exact220_launch": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_sha256"] = payload_sha256(value)
    return value


def _validate_evaluator_protocol() -> dict[str, Any]:
    protocol = read(ROOT / EVALUATOR_PROTOCOL)
    manifest = protocol.get("source_manifest")
    if (
        protocol.get("role")
        != "v24700_v24694_worldbank_evaluator_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or not sealed(protocol, "protocol_sha256")
        or protocol.get("authorization")
        != {
            "one_external_evaluation": True,
            "fresh_deepwidebench_candidate_design": False,
            "dev64_launch": False,
            "exact220_launch": False,
            "leaderboard_or_sota": False,
        }
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
        raise RuntimeError("V2.47.00 evaluator protocol drifted")
    return protocol


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    absent(ROOT / RESULT)
    _protocol = _validate_evaluator_protocol()
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
        "role": "v24700_v24694_worldbank_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "metrics": metrics,
        "passed": passed,
        "status": (
            "worldbank_target_value_external_go"
            if passed
            else "worldbank_target_value_external_no_go"
        ),
        "fixed_denominator_failure_as_zero": True,
        "quality_evaluation_executed_once_after_prediction_freeze": True,
        "evaluator_protocol_sha256": sha256(ROOT / EVALUATOR_PROTOCOL),
        "frozen_predictions_sha256": sha256(ROOT / PREDICTIONS),
        "evaluator_only_gold_sha256": sha256(ROOT / GOLD),
        "evaluator_only_provenance_sha256": sha256(ROOT / PROVENANCE),
        "claim_scope": {
            "fresh_worldbank_external_quality_measured": True,
            "target_value_exact_address_quality_measured": True,
            "quality_cost_pareto_gate": True,
            "equal_effect_causal_ablation": False,
            "deepwidebench_quality_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "network_model_search_fetch_or_official_deepwidebench_evaluator_called_by_evaluation": False,
        "authorization": {
            "fresh_deepwidebench_candidate_design": passed,
            "dev64_launch": False,
            "exact220_launch": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def _metrics_valid(metrics: Any) -> bool:
    if not isinstance(metrics, Mapping):
        return False
    arms = metrics.get("arms")
    parser_delta = metrics.get("expanded_minus_frozen")
    target_delta = metrics.get("target_value_minus_expanded")
    if (
        not isinstance(arms, Mapping)
        or set(arms) != set(ARMS)
        or not isinstance(parser_delta, Mapping)
        or not isinstance(target_delta, Mapping)
        or any(arms[arm].get("tasks") != SELECTED_COUNT for arm in ARMS)
    ):
        return False
    keys = (
        "exact_table_successes",
        "entity_recall",
        "row_f1",
        "item_f1",
        "column_f1",
        "composite",
    )
    try:
        expected_parser = {
            key: arms["expanded_parser"][key] - arms["frozen_parser"][key]
            for key in keys
        }
        expected_target = {
            key: arms["target_value"][key] - arms["expanded_parser"][key]
            for key in keys
        }
    except (KeyError, TypeError):
        return False
    for observed, expected in (
        (parser_delta, expected_parser),
        (target_delta, expected_target),
    ):
        if any(
            abs(float(observed.get(key, float("inf"))) - float(expected[key]))
            > 1e-12
            for key in keys
        ):
            return False
    gate = (
        expected_target["exact_table_successes"] > 0
        and expected_target["composite"] >= 0
        and expected_target["item_f1"] >= 0
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
        or not isinstance(metrics, Mapping)
        or metrics.get("gate_passed") is not result.get("passed")
    ):
        findings.append("binding_denominator_metrics_or_gate_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24700_v24694_worldbank_postresult_audit",
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
            "fresh_deepwidebench_candidate_design": not findings
            and result.get("passed") is True,
            "dev64_launch": False,
            "exact220_launch": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.47.00 postresult audit failed")
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
