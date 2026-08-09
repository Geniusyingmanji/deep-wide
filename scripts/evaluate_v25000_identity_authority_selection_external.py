#!/usr/bin/env python3
"""Post-freeze evaluator for the V2.50.00 identity/authority selection gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import native_search  # noqa: E402
from deepwide_agent import v25000_identity_authority_selection_external_contract as contract  # noqa: E402
from deepwide_agent import v24999_shared_response_selection_runtime as runtime  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def _read(relative: Path) -> dict[str, Any]:
    path = ROOT / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT)
    ):
        raise RuntimeError("V2.50.00 evaluator expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.00 evaluator expected JSON object")
    return value


def _read_jsonl(relative: Path) -> list[dict[str, Any]]:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.50.00 evaluator expected ordinary JSONL")
    values = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.50.00 evaluator JSONL drifted")
    return values


def _publish(relative: Path, value: Mapping[str, Any]) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.00 evaluator requires clean pushed HEAD")


def _matrix(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [
        line.strip()
        for line in str(text).replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(lines) < 2:
        return [], []
    cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    columns = cells[0]
    rows = [row for row in cells[2:] if len(row) == len(columns)]
    return columns, rows


def _canonical(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def parse_iana_page(raw_html: str) -> dict[str, dict[str, str]]:
    _title, text = native_search.html_to_text(raw_html)
    output: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        cells = [" ".join(value.split()) for value in line.split(" | ")]
        if len(cells) != 3:
            continue
        domain, kind, manager = cells
        folded = domain.casefold()
        if not folded.startswith(".") or not kind or not manager:
            continue
        previous = output.get(folded)
        row = {"Domain": domain, "Type": kind, "TLD Manager": manager}
        if previous is not None and previous != row:
            raise RuntimeError("V2.50.00 IANA row conflict")
        output[folded] = row
    if any(tld.casefold() not in output for tld in contract.TLD_COHORT):
        raise RuntimeError("V2.50.00 IANA gold cohort incomplete")
    return {tld: output[tld.casefold()] for tld in contract.TLD_COHORT}


def evaluate_prediction(
    prediction: str, gold: Mapping[str, str]
) -> dict[str, float | int]:
    columns, rows = _matrix(prediction)
    valid_columns = columns == list(contract.COLUMNS)
    selected = rows if valid_columns else []
    expected_key = _canonical(gold["Domain"])
    predicted = {
        _canonical(row[0]): row for row in selected if _canonical(row[0])
    }
    entity = int(expected_key in predicted)
    item_true = 0
    if entity:
        row = predicted[expected_key]
        item_true = sum(
            _canonical(value) == _canonical(gold[column])
            for value, column in zip(row[1:], contract.COLUMNS[1:], strict=True)
        )
    predicted_items = len(predicted) * 2
    precision = item_true / predicted_items if predicted_items else 0.0
    recall = item_true / 2
    item_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    row_precision = entity / len(predicted) if predicted else 0.0
    row_recall = float(entity)
    row_f1 = (
        2 * row_precision * row_recall / (row_precision + row_recall)
        if row_precision + row_recall
        else 0.0
    )
    exact = int(len(selected) == 1 and entity == 1 and item_true == 2)
    column_f1 = 1.0 if valid_columns else 0.0
    return {
        "exact_table_success": exact,
        "entity_recall": float(entity),
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "composite": (float(entity) + row_f1 + item_f1 + column_f1) / 4,
    }


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]],
    gold: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    tasks = contract.task_vector()
    by_id = {
        task["opaque_id"]: tld
        for task, tld in zip(tasks, contract.TLD_COHORT, strict=True)
    }
    values = {arm: [] for arm in contract.ARMS}
    seen: set[str] = set()
    for raw in rows:
        row = runtime.validate_result(raw)
        opaque = row["opaque_id"]
        if opaque in seen or opaque not in by_id:
            raise RuntimeError("V2.50.00 prediction identity drifted")
        seen.add(opaque)
        tld = by_id[opaque]
        for arm in contract.ARMS:
            values[arm].append(
                evaluate_prediction(row["predictions"][arm], gold[tld])
            )
    if len(seen) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.00 evaluation denominator drifted")
    aggregate: dict[str, Any] = {}
    for arm, metrics in values.items():
        aggregate[arm] = {
            "tasks": contract.TASK_COUNT,
            "exact_table_successes": sum(
                row["exact_table_success"] for row in metrics
            ),
            **{
                key: sum(float(row[key]) for row in metrics) / contract.TASK_COUNT
                for key in (
                    "entity_recall", "row_f1", "item_f1", "column_f1", "composite"
                )
            },
        }
    delta = {
        key: aggregate[contract.CANDIDATE_ARM][key]
        - aggregate[contract.CONTROL_ARM][key]
        for key in (
            "exact_table_successes", "entity_recall", "row_f1", "item_f1",
            "column_f1", "composite",
        )
    }
    return {
        "arms": aggregate,
        f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": delta,
    }


def _parent() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    forward = _read(contract.FORWARD_RESULT)
    audit = _read(contract.FORWARD_AUDIT)
    if (
        forward.get("role") != "v25000_identity_authority_selection_external_forward_result"
        or not contract.sealed(forward, "result_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_protocol"
        ) is not True
        or audit.get("mechanism_gate", {}).get("passed") is not True
        or not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or audit.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or forward.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or forward.get("task_results_sha256")
        != contract.sha256(ROOT / contract.TASK_RESULTS)
        or forward.get(
            "all_predictions_terminal_before_gold_fetch_or_quality_decision"
        ) is not True
    ):
        raise RuntimeError("V2.50.00 evaluator parent drifted")
    return protocol, forward, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preregister", "evaluate", "postaudit"))
    args = parser.parse_args()
    _clean_pushed()
    protocol, _forward, audit = _parent()
    if args.command == "preregister":
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25000_identity_authority_selection_external_evaluator_preregistration",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": int(time.time()),
                "fixed_denominator": contract.TASK_COUNT,
                "prediction_freeze_sha256": contract.sha256(
                    ROOT / contract.PREDICTION_FREEZE
                ),
                "task_results_sha256": contract.sha256(ROOT / contract.TASK_RESULTS),
                "gold_endpoint_sha256": protocol["population"][
                    "official_gold_endpoint_sha256"
                ],
                "one_postfreeze_official_page_fetch": True,
                "no_retry_refetch_or_selective_revaluation": True,
                "quality_gate": protocol["quality_gate"],
                "authorization": {
                    "one_external_evaluation": True,
                    "public_exact220": False,
                    "sota": False,
                },
            },
            "protocol_payload_sha256",
        )
        path = contract.EVALUATOR_PROTOCOL
    elif args.command == "evaluate":
        evaluator = _read(contract.EVALUATOR_PROTOCOL)
        if (
            not contract.sealed(evaluator, "protocol_payload_sha256")
            or evaluator.get("authorization", {}).get("one_external_evaluation")
            is not True
        ):
            raise RuntimeError("V2.50.00 evaluator protocol drifted")
        if (
            (ROOT / contract.POSTFREEZE_GOLD).exists()
            or (ROOT / contract.POSTFREEZE_GOLD).is_symlink()
        ):
            raise FileExistsError(ROOT / contract.POSTFREEZE_GOLD)
        with acquire_deepwide_api_lease(
            ROOT,
            owner="v25000_identity_authority_selection_external_evaluator_v1",
            purpose="single_postfreeze_iana_gold_fetch_and_selection_arm_evaluation",
            path=ROOT / contract.LEASE_PATH,
        ):
            response = requests.get(
                contract.IANA_URL,
                headers={
                    "User-Agent": "DeepWideResearch/1.0 (+postfreeze external evaluator)"
                },
                timeout=(5.0, 45.0),
                allow_redirects=False,
            )
            response.raise_for_status()
            raw = bytes(response.content)
        if len(raw) > contract.MAX_GOLD_BYTES:
            raise RuntimeError("V2.50.00 IANA response oversized")
        gold = parse_iana_page(
            raw.decode(response.encoding or "utf-8", errors="replace")
        )
        gold_artifact = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25000_postfreeze_iana_gold",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": int(time.time()),
                "endpoint_sha256": hashlib.sha256(
                    contract.IANA_URL.encode()
                ).hexdigest(),
                "http_status": int(response.status_code),
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "records": gold,
                "prediction_freeze_preexisted": True,
                "single_fetch_no_retry_or_refetch": True,
            },
            "gold_payload_sha256",
        )
        _publish(contract.POSTFREEZE_GOLD, gold_artifact)
        metrics = evaluate_rows(_read_jsonl(contract.TASK_RESULTS), gold)
        delta = metrics[
            f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}"
        ]
        passed = (
            audit["mechanism_gate"]["passed"] is True
            and delta["exact_table_successes"] > 0
            and all(
                delta[key] >= 0
                for key in (
                    "entity_recall", "row_f1", "item_f1", "column_f1", "composite"
                )
            )
        )
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25000_identity_authority_selection_external_result",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": int(time.time()),
                "status": "identity_authority_selection_external_go" if passed else "identity_authority_selection_external_no_go",
                "passed": passed,
                "metrics": metrics,
                "mechanism": audit["mechanism_gate"],
                "gold_sha256": contract.sha256(ROOT / contract.POSTFREEZE_GOLD),
                "fixed_denominator_failure_as_zero": True,
                "claim_scope": {
                    "benchmark_external_quality_measured": True,
                    "deepwidebench_quality_measured": False,
                    "production_latency_or_throughput_measured": False,
                    "entropy_or_signed_credit_validated": False,
                    "leaderboard_or_sota_supported": False,
                },
                "authorization": {
                    "production_candidate_design": passed,
                    "public_exact220_launch": False,
                    "leaderboard_or_sota": False,
                },
            },
            "result_payload_sha256",
        )
        path = contract.RESULT
    else:
        result = _read(contract.RESULT)
        findings: list[str] = []
        if not contract.sealed(result, "result_payload_sha256"):
            findings.append("result_seal_invalid")
        if result.get("fixed_denominator_failure_as_zero") is not True:
            findings.append("failure_policy_drifted")
        if contract.watcher_snapshot() != protocol["execution"]["protected_watchers"]:
            findings.append("protected_watcher_identity_drifted")
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25000_identity_authority_selection_external_postresult_audit",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": int(time.time()),
                "result_sha256": contract.sha256(ROOT / contract.RESULT),
                "gold_sha256": contract.sha256(ROOT / contract.POSTFREEZE_GOLD),
                "findings": findings,
                "audit_valid": not findings,
                "network_model_fetch_or_deepwidebench_evaluator_called_by_audit": False,
                "authorization": {
                    "production_candidate_design": not findings
                    and result.get("passed") is True,
                    "public_exact220_launch": False,
                    "leaderboard_or_sota": False,
                },
            },
            "audit_payload_sha256",
        )
        path = contract.POSTAUDIT
    _publish(path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "status": value.get("status"),
                "passed": value.get("passed"),
                "metrics": value.get("metrics"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
