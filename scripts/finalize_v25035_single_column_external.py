#!/usr/bin/env python3
"""Post-freeze evaluator for the V2.50.35 single-column external gate."""

from __future__ import annotations

import copy
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as score  # noqa: E402
from deepwide_agent import v25035_single_column_external_contract as contract  # noqa: E402
from deepwide_agent.clients import canonicalize_url  # noqa: E402
from scripts import run_v25035_single_column_external as runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


EVALUATOR_LEASE_OWNER = "v25035_single_column_external_evaluator_v1"
EVALUATOR_LEASE_PURPOSE = "postfreeze_exact_pypi_version_evaluator"


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.35 evaluator expected JSON object")
    return value


def _jsonl(relative: Path) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.50.35 evaluator expected JSONL objects")
    return rows


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            )
        handle.flush()
        os.fsync(handle.fileno())


def build_evaluator_protocol(*, now: int | None = None) -> dict[str, Any]:
    protocol = contract.validate_protocol(
        ROOT, _read(contract.PROTOCOL), tracked=True
    )
    forward = _read(contract.FORWARD_RESULT)
    audit = _read(contract.FORWARD_AUDIT)
    freeze = _read(contract.PREDICTION_FREEZE)
    mechanism = forward.get("mechanism_decision") or {}
    if (
        forward.get("role") != "v25035_single_column_external_forward_result"
        or not contract.sealed(forward, "result_payload_sha256")
        or audit.get("role") != "v25035_single_column_external_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or mechanism.get("mechanism_gate_passed") is not True
        or mechanism.get("postfreeze_external_evaluator_protocol") is not True
        or freeze.get("all_predictions_terminal_before_evaluator_or_gold_refetch")
        is not True
        or not contract.sealed(freeze, "freeze_payload_sha256")
        or protocol["authorization"]["postfreeze_evaluator"] is not False
    ):
        raise RuntimeError("V2.50.35 evaluator protocol barrier failed")
    value = {
        "artifact_version": 1,
        "role": "v25035_single_column_external_evaluator_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "forward_result_sha256": contract.sha256(
                ROOT / contract.FORWARD_RESULT
            ),
            "forward_audit_sha256": contract.sha256(
                ROOT / contract.FORWARD_AUDIT
            ),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        },
        "evaluation": {
            "fixed_denominator": contract.TASK_COUNT,
            "exact_endpoint_fetches": contract.TASK_COUNT,
            "fetch_attempts_per_endpoint": 1,
            "fetch_retries": 0,
            "fetch_concurrency": contract.EXECUTOR_CONCURRENCY,
            "failure_as_zero": True,
            "metrics": [
                "exact_table_accuracy",
                "cell_accuracy",
                "schema_validity",
                "evaluator_invalid_or_not_run",
            ],
            "quality_gate": contract.gates()["quality"],
        },
        "source_policy": {
            "prediction_rows_frozen_before_gold_fetch": True,
            "one_postfreeze_exact_pypi_fetch_per_task": True,
            "same_gold_version_for_both_arms": True,
            "deepwidebench_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "same_run_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "one_postfreeze_external_evaluation": True,
            "retry_refetch_or_selective_revaluation": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "evaluator_protocol_payload_sha256")


def validate_evaluator_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    parents = copied.get("parents") or {}
    evaluation = copied.get("evaluation") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25035_single_column_external_evaluator_preregistration"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(copied, "evaluator_protocol_payload_sha256")
        or parents.get("protocol_sha256")
        != contract.sha256(ROOT / contract.PROTOCOL)
        or parents.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or parents.get("forward_audit_sha256")
        != contract.sha256(ROOT / contract.FORWARD_AUDIT)
        or parents.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or parents.get("task_rows_sha256")
        != contract.sha256(ROOT / contract.TASK_ROWS)
        or evaluation.get("fixed_denominator") != contract.TASK_COUNT
        or evaluation.get("exact_endpoint_fetches") != contract.TASK_COUNT
        or evaluation.get("fetch_attempts_per_endpoint") != 1
        or evaluation.get("fetch_retries") != 0
        or evaluation.get("failure_as_zero") is not True
        or evaluation.get("quality_gate") != contract.gates()["quality"]
        or copied.get("authorization")
        != {
            "one_postfreeze_external_evaluation": True,
            "retry_refetch_or_selective_revaluation": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        }
    ):
        raise ValueError("V2.50.35 evaluator protocol drifted")
    return copied


def _fetch_gold(index: int) -> dict[str, Any]:
    project = contract.PROJECTS[index]
    url = contract.endpoint_vector()[index]
    try:
        with requests.get(
            url,
            headers={
                "User-Agent": "DeepWideResearch/1.0 (+postfreeze-version-evaluator)"
            },
            timeout=(
                contract.FETCH_CONNECT_TIMEOUT_SECONDS,
                contract.FETCH_READ_TIMEOUT_SECONDS,
            ),
            allow_redirects=False,
            stream=True,
        ) as response:
            status = int(response.status_code)
            response.raise_for_status()
            if canonicalize_url(str(response.url)) != canonicalize_url(url):
                raise ValueError("V2.50.35 gold endpoint drifted")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                size += len(chunk)
                if size > contract.MAX_RESPONSE_BYTES:
                    raise ValueError("V2.50.35 gold response exceeds cap")
                chunks.append(bytes(chunk))
            raw = b"".join(chunks)
        value = json.loads(raw.decode("utf-8"))
        info = value.get("info") if isinstance(value, Mapping) else None
        if not isinstance(info, Mapping):
            raise ValueError("V2.50.35 gold info object absent")
        name = str(info.get("name") or "").strip()
        version = str(info.get("version") or "").strip()
        canonical = lambda item: "-".join(
            part for part in re.split(r"[-_.]+", item.casefold()) if part
        )
        if (
            canonical(name) != canonical(project)
            or not version
            or len(version) > 200
            or any(character in version for character in "\r\n\x00|")
        ):
            raise ValueError("V2.50.35 gold identity/version drifted")
        return {
            "index": index,
            "opaque_id": contract.task_vector()[index]["opaque_id"],
            "project": project,
            "version": version,
            "fetch_attempts": 1,
            "fetch_successes": 1,
            "fetch_status": status,
            "response_bytes": len(raw),
            "evaluator_valid": True,
        }
    except Exception:
        return {
            "index": index,
            "opaque_id": contract.task_vector()[index]["opaque_id"],
            "project": project,
            "version": "",
            "fetch_attempts": 1,
            "fetch_successes": 0,
            "fetch_status": 0,
            "response_bytes": 0,
            "evaluator_valid": False,
        }


def evaluate_prediction(
    prediction: str, *, column: str, gold_version: str, evaluator_valid: bool
) -> dict[str, Any]:
    canonical, _errors = score.extract_valid_markdown_table(prediction, [column])
    lines = [
        line.strip()
        for line in str(canonical or "").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    one_row = len(lines) == 3
    cells = score._split_table_row(lines[2]) if one_row else []
    schema_valid = bool(canonical is not None and one_row and len(cells) == 1)
    cell_correct = bool(
        evaluator_valid
        and schema_valid
        and gold_version
        and cells[0] == gold_version
    )
    return {
        "evaluator_valid": bool(evaluator_valid),
        "schema_valid": schema_valid,
        "cell_correct": cell_correct,
        "exact_table_success": cell_correct,
    }


def aggregate_metrics(
    rows: Sequence[Mapping[str, Any]], gold: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    checked = [runner.validate_task_row(row) for row in rows]
    gold_by_id = {str(row["opaque_id"]): dict(row) for row in gold}
    if (
        len(checked) != contract.TASK_COUNT
        or len(gold_by_id) != contract.TASK_COUNT
        or set(gold_by_id) != {str(row["opaque_id"]) for row in checked}
    ):
        raise ValueError("V2.50.35 evaluator denominator drifted")
    arm_rows: dict[str, list[dict[str, Any]]] = {
        arm: [] for arm in contract.ARMS
    }
    for row in checked:
        gold_row = gold_by_id[str(row["opaque_id"])]
        for arm in contract.ARMS:
            arm_rows[arm].append(
                evaluate_prediction(
                    str(row["predictions"][arm]),
                    column=contract.column_for_index(int(row["index"])),
                    gold_version=str(gold_row.get("version") or ""),
                    evaluator_valid=gold_row.get("evaluator_valid") is True,
                )
            )
    forward = _read(contract.FORWARD_RESULT)
    output: dict[str, Any] = {"arms": {}}
    for arm, values in arm_rows.items():
        output["arms"][arm] = {
            "selected": contract.TASK_COUNT,
            "evaluator_valid": sum(item["evaluator_valid"] for item in values),
            "evaluator_invalid_or_not_run": sum(
                not item["evaluator_valid"] for item in values
            ),
            "exact_table_successes": sum(
                item["exact_table_success"] for item in values
            ),
            "exact_table_accuracy": sum(
                item["exact_table_success"] for item in values
            )
            / contract.TASK_COUNT,
            "cell_accuracy": sum(item["cell_correct"] for item in values)
            / contract.TASK_COUNT,
            "schema_validity": sum(item["schema_valid"] for item in values)
            / contract.TASK_COUNT,
            "fallback_tasks": int(
                forward["aggregate"][f"{arm}_fallback_tables"]
            ),
        }
    control = output["arms"][contract.CONTROL_ARM]
    candidate = output["arms"][contract.CANDIDATE_ARM]
    output["candidate_minus_control"] = {
        name: candidate[name] - control[name]
        for name in (
            "exact_table_successes",
            "exact_table_accuracy",
            "cell_accuracy",
            "schema_validity",
            "evaluator_invalid_or_not_run",
            "fallback_tasks",
        )
    }
    return output


def quality_decision(
    metrics: Mapping[str, Any], mechanism: Mapping[str, Any]
) -> dict[str, Any]:
    arms = metrics.get("arms") or {}
    control = arms.get(contract.CONTROL_ARM) or {}
    candidate = arms.get(contract.CANDIDATE_ARM) or {}
    checks = {
        "mechanism_gate_passed": mechanism.get("mechanism_gate_passed") is True,
        "fixed_denominator": control.get("selected")
        == candidate.get("selected")
        == contract.TASK_COUNT,
        "candidate_exact_strictly_greater": candidate.get(
            "exact_table_successes", 0
        )
        > control.get("exact_table_successes", 0),
        "candidate_cell_accuracy_nonregression": candidate.get(
            "cell_accuracy", 0.0
        )
        >= control.get("cell_accuracy", 0.0),
        "candidate_schema_validity_nonregression": candidate.get(
            "schema_validity", 0.0
        )
        >= control.get("schema_validity", 0.0),
        "candidate_evaluator_invalid_nonincrease": candidate.get(
            "evaluator_invalid_or_not_run", contract.TASK_COUNT
        )
        <= control.get("evaluator_invalid_or_not_run", contract.TASK_COUNT),
        "candidate_fallback_strictly_less": candidate.get(
            "fallback_tasks", contract.TASK_COUNT
        )
        < control.get("fallback_tasks", contract.TASK_COUNT),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "single_column_external_quality_gate_go": passed,
        "new_deepwidebench_exact220_authorized": False,
        "leaderboard_or_sota": False,
    }


def run_evaluation() -> dict[str, Any]:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.35 evaluator requires clean pushed HEAD")
    evaluator = validate_evaluator_protocol(_read(contract.EVALUATOR_PROTOCOL))
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (contract.GOLD_SNAPSHOT, contract.RESULT, contract.POSTAUDIT)
    ):
        raise RuntimeError("V2.50.35 evaluator surface is not pristine")
    with acquire_deepwide_api_lease(
        ROOT,
        owner=EVALUATOR_LEASE_OWNER,
        purpose=EVALUATOR_LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        if contract.watcher_snapshot() != contract.validate_protocol(
            ROOT, _read(contract.PROTOCOL), tracked=True
        )["protected_watchers"]:
            raise RuntimeError("V2.50.35 evaluator watcher drifted")
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            gold = list(pool.map(_fetch_gold, range(contract.TASK_COUNT)))
    gold.sort(key=lambda row: int(row["index"]))
    _publish_jsonl(ROOT / contract.GOLD_SNAPSHOT, gold)
    rows = _jsonl(contract.TASK_ROWS)
    metrics = aggregate_metrics(rows, gold)
    forward = _read(contract.FORWARD_RESULT)
    decision = quality_decision(metrics, forward["mechanism_decision"])
    result = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25035_single_column_external_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "parents": evaluator["parents"],
            "evaluator_protocol_sha256": contract.sha256(
                ROOT / contract.EVALUATOR_PROTOCOL
            ),
            "gold_snapshot_sha256": contract.sha256(
                ROOT / contract.GOLD_SNAPSHOT
            ),
            "gold_fetch_attempts": sum(row["fetch_attempts"] for row in gold),
            "gold_fetch_successes": sum(row["fetch_successes"] for row in gold),
            "metrics": metrics,
            "mechanism_decision": forward["mechanism_decision"],
            "quality_decision": decision,
            "fixed_denominator_failure_as_zero": True,
            "retry_refetch_or_selective_revaluation": False,
            "claims": {
                "benchmark_external_single_column_normalizer_gate": True,
                "deepwidebench_score": False,
                "entropy_or_information_gain_credit_validated": False,
                "leaderboard_or_sota": False,
            },
            "authorization": {
                "production_integration_evidence": decision[
                    "single_column_external_quality_gate_go"
                ],
                "new_deepwidebench_exact220": False,
                "leaderboard_or_sota": False,
            },
        },
        "result_payload_sha256",
    )
    _publish(ROOT / contract.RESULT, result)
    return result


def main() -> None:
    value = run_evaluation()
    print(
        json.dumps(
            {
                "path": str(contract.RESULT),
                "metrics": value["metrics"],
                "quality_decision": value["quality_decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
