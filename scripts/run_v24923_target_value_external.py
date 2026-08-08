#!/usr/bin/env python3
"""Freeze sources and run the V2.49.23 shared-prefix forward exactly once."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24923_target_value_external_contract as contract  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.49.23 runner expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.23 runner expected JSON object")
    return value


def _new_json(path: Path, value: Any) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _new_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _new_bytes(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.49.23 runner expected ordinary JSONL")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _fetch_once(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "deepwide-v24923/1.0"}
    )
    with urllib.request.urlopen(
        request, timeout=contract.FETCH_TIMEOUT_SECONDS
    ) as response:
        if response.status != 200:
            raise RuntimeError("V2.49.23 official snapshot fetch failed")
        data = response.read(contract.FETCH_MAX_BYTES + 1)
    if not data or len(data) > contract.FETCH_MAX_BYTES:
        raise RuntimeError("V2.49.23 official snapshot size drifted")
    return data


def parse_catalog(blob: bytes) -> dict[str, dict[str, str]]:
    value = json.loads(blob)
    records = value[1] if isinstance(value, list) and len(value) == 2 else None
    if not isinstance(records, list):
        raise RuntimeError("V2.49.23 country catalog schema drifted")
    output: dict[str, dict[str, str]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        iso3 = str(record.get("id", "")).strip().upper()
        name = str(record.get("name", "")).strip()
        region = record.get("region") or {}
        region_id = str(region.get("id", "")).strip()
        if len(iso3) == 3 and name and region_id:
            output[iso3] = {"name": name, "region_id": region_id}
    if len(output) < 180:
        raise RuntimeError("V2.49.23 country catalog capacity drifted")
    return output


def parse_target(
    blob: bytes, target: dict[str, str], url: str
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    value = json.loads(blob)
    records = value[1] if isinstance(value, list) and len(value) == 2 else None
    if not isinstance(records, list):
        raise RuntimeError("V2.49.23 target response schema drifted")
    lines = [
        f"| Country | ISO3 | {target['label']} [{target['indicator']}] @{target['year']} |",
        "|---|---|---:|",
    ]
    values: dict[str, dict[str, str]] = {}
    for record in records:
        if not isinstance(record, dict) or record.get("value") is None:
            continue
        country = record.get("country") or {}
        name = str(country.get("value", "")).strip()
        iso3 = str(record.get("countryiso3code", "")).strip().upper()
        if not name or len(iso3) != 3 or iso3 in values:
            continue
        rendered = str(record["value"])
        lines.append(f"| {name} | {iso3} | {rendered} |")
        values[iso3] = {"name": name, "value": rendered}
    content = "\n".join(lines)
    if len(values) < 170 or not 5_000 < len(content) <= 12_000:
        raise RuntimeError("V2.49.23 rendered page capacity drifted")
    return {
        "title": f"World Bank official indicator {target['indicator']} {target['year']}",
        "url": url,
        "content": content,
    }, values


def _rank(iso3: str) -> str:
    return hashlib.sha256(
        f"{contract.SELECTION_SEED}:{iso3}".encode("utf-8")
    ).hexdigest()


def build_visible_tasks(
    catalog: dict[str, dict[str, str]],
    values: list[dict[str, dict[str, str]]],
) -> list[dict[str, str]]:
    common = set(catalog).intersection(*(set(value) for value in values))
    eligible = sorted(
        (
            iso3
            for iso3 in common
            if catalog[iso3]["region_id"] not in {"NA", ""}
        ),
        key=lambda iso3: (_rank(iso3), iso3),
    )
    if len(eligible) < contract.SELECTED_ENTITY_COUNT:
        raise RuntimeError("V2.49.23 complete entity capacity drifted")
    selected = eligible[: contract.SELECTED_ENTITY_COUNT]
    columns = contract.visible_columns()
    tasks = []
    for index in range(contract.SELECTED_COUNT):
        group = selected[
            index * contract.ROWS_PER_TASK : (index + 1) * contract.ROWS_PER_TASK
        ]
        countries = "\n".join(
            f"{ordinal}. {catalog[iso3]['name']} [{iso3}]"
            for ordinal, iso3 in enumerate(group, 1)
        )
        question = (
            "Return exactly one Markdown table and no prose. Column names: "
            + " | ".join(columns)
            + ". Include exactly the requested country rows in the visible order. "
            "Preserve numeric decimal spelling shown in supplied official pages; "
            "use Unknown only if absent.\n<COUNTRIES>\n"
            + countries
            + "\n</COUNTRIES>"
        )
        opaque = "task_" + hashlib.sha256(
            f"v24923:{','.join(group)}".encode("utf-8")
        ).hexdigest()[:24]
        tasks.append({"opaque_id": opaque, "question": question})
    return contract.validate_task_vector(tasks)


def build_snapshot(
    catalog_blob: bytes, target_blobs: list[bytes]
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    catalog = parse_catalog(catalog_blob)
    pages = []
    values = []
    for blob, target, url in zip(
        target_blobs, contract.TARGETS, contract.TARGET_URLS, strict=True
    ):
        page, target_values = parse_target(blob, dict(target), url)
        pages.append(page)
        values.append(target_values)
    tasks = build_visible_tasks(catalog, values)
    bundle: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24923_frozen_shared_public_pages",
        "pages": pages,
        "target_keys": list(contract.TARGET_KEYS),
        "same_page_vector_for_both_arms": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    bundle["bundle_payload_sha256"] = contract.payload_sha256(bundle)
    freeze: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24923_snapshot_freeze",
        "catalog_response_sha256": hashlib.sha256(catalog_blob).hexdigest(),
        "target_response_sha256": [
            hashlib.sha256(blob).hexdigest() for blob in target_blobs
        ],
        "rendered_page_character_counts": [len(page["content"]) for page in pages],
        "complete_entity_intersection": len(
            set(catalog).intersection(*(set(value) for value in values))
        ),
        "selected_tasks": contract.SELECTED_COUNT,
        "selected_entities": contract.SELECTED_ENTITY_COUNT,
        "selection_seed_sha256": hashlib.sha256(
            contract.SELECTION_SEED.encode("utf-8")
        ).hexdigest(),
        "official_responses_fetched_once_before_arm_branch": True,
        "same_frozen_pages_required_for_both_arms": True,
        "gold_mapping_or_evaluator_created_or_opened": False,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    return bundle, tasks, freeze


def _fallback(task: dict[str, str], pages_path: Path) -> dict[str, Any]:
    table = "| Country | Value |\n|---|---|\n| Unknown | Unknown |"
    return {
        "artifact_version": 1,
        "role": "v24923_target_value_external_task_result",
        "opaque_id": task["opaque_id"],
        "status": "failure_as_zero_projection",
        "runtime_input_keys": ["opaque_id", "question"],
        "frozen_pages_sha256": contract.sha256(pages_path),
        "predictions": {arm: table for arm in contract.ARMS},
        "prediction_sha256": {
            arm: contract.payload_sha256(table) for arm in contract.ARMS
        },
        "projection_sha256": {},
        "projection_equal": True,
        "projection_receipts": {},
        "model_usage": {},
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "same_frozen_pages_model_prompt_output_cap_and_attempt_count": True,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "retry_resume_skip_or_selective_rerun": False,
        "result_payload_sha256": "failure-as-zero",
    }


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / contract.PROTOCOL)
    forward = _read(ROOT / contract.FORWARD_RESULT)
    freeze = _read(ROOT / contract.PREDICTION_FREEZE)
    summary = _read(ROOT / contract.RUN_SUMMARY)
    predictions = _read_jsonl(ROOT / contract.PREDICTIONS)
    projections = _read_jsonl(ROOT / contract.PROJECTIONS)
    prediction_ids = [str(row.get("opaque_id", "")) for row in predictions]
    projection_ids = [str(row.get("opaque_id", "")) for row in projections]
    candidate_receipts = [
        row.get("projection_receipts", {}).get("target_value_30k", {})
        for row in projections
    ]
    parent_receipts = [
        row.get("projection_receipts", {}).get("parent_30k", {})
        for row in projections
    ]
    checks = {
        "forward_result_sealed": contract.sealed(
            forward, "result_payload_sha256"
        ),
        "prediction_freeze_sealed": contract.sealed(
            freeze, "freeze_payload_sha256"
        ),
        "run_summary_sealed": contract.sealed(
            summary, "summary_payload_sha256"
        ),
        "prediction_denominator_12x2": len(predictions) == contract.SELECTED_COUNT
        and all(
            isinstance(row.get("predictions"), dict)
            and set(row["predictions"]) == set(contract.ARMS)
            for row in predictions
        ),
        "projection_denominator_12x2": len(projections) == contract.SELECTED_COUNT
        and all(
            isinstance(row.get("projection_receipts"), dict)
            and set(row["projection_receipts"]) == set(contract.ARMS)
            for row in projections
        ),
        "opaque_id_join_exact": prediction_ids == projection_ids
        and len(set(prediction_ids)) == contract.SELECTED_COUNT,
        "prediction_hashes_valid": all(
            row.get("prediction_sha256", {}).get(arm)
            == contract.payload_sha256(row["predictions"][arm])
            for row in predictions
            for arm in contract.ARMS
        ),
        "candidate_receipts_valid": all(
            isinstance(receipt, dict)
            and receipt.get("role")
            == "v24921_content_free_target_value_coverage_receipt"
            and receipt.get("policy", {}).get("total_character_cap") == 30_000
            and receipt.get("policy", {}).get("maximum_page_chars") == 5_000
            and receipt.get("orphan_selected_table_continuation_block_count") == 0
            and receipt.get("entropy_or_information_gain_assigns_credit") is False
            for receipt in candidate_receipts
        ),
        "parent_receipts_valid": all(
            isinstance(receipt, dict)
            and receipt.get("role") == "v24846_content_free_projection_receipt"
            and receipt.get("policy", {}).get("total_character_cap") == 30_000
            and receipt.get("policy", {}).get("maximum_page_chars") == 5_000
            and receipt.get("orphan_selected_table_continuation_block_count") == 0
            and receipt.get("entropy_or_information_gain_assigns_credit") is False
            for receipt in parent_receipts
        ),
        "all_predictions_terminal_before_evaluator_open": forward.get(
            "all_predictions_terminal_before_evaluator_open"
        )
        is True,
        "no_retry_resume_or_selective_rerun": all(
            row.get("retry_resume_skip_or_selective_rerun") is False
            for row in predictions
        ),
        "shared_snapshot_bound": freeze.get("snapshot_freeze_sha256")
        == contract.sha256(ROOT / contract.SNAPSHOT_FREEZE),
        "mechanism_exposure_totals_consistent": sum(
            int(receipt.get("supported_target_value_pair_count", 0))
            for receipt in candidate_receipts
        )
        == forward.get("candidate_supported_target_value_pairs")
        and sum(
            int(receipt.get("retained_target_value_pair_count", 0))
            for receipt in candidate_receipts
        )
        == forward.get("candidate_retained_target_value_pairs")
        and sum(row.get("projection_equal") is False for row in projections)
        == forward.get("projection_unequal_tasks"),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
    }
    mechanism_go = (
        checks["mechanism_exposure_totals_consistent"]
        and forward.get("projection_unequal_tasks", 0)
        >= protocol["execution"]["mechanism_gate_before_evaluator"][
            "minimum_projection_unequal_tasks"
        ]
        and forward.get("candidate_retained_target_value_pairs", 0)
        >= protocol["execution"]["mechanism_gate_before_evaluator"][
            "minimum_retained_target_value_pairs"
        ]
        and forward.get("failure_as_zero_tasks")
        == protocol["execution"]["mechanism_gate_before_evaluator"][
            "failure_as_zero_tasks"
        ]
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24923_target_value_external_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
        "projections_sha256": contract.sha256(ROOT / contract.PROJECTIONS),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "mechanism_gate": {
            "minimum_projection_unequal_tasks": protocol["execution"][
                "mechanism_gate_before_evaluator"
            ]["minimum_projection_unequal_tasks"],
            "observed_projection_unequal_tasks": forward.get(
                "projection_unequal_tasks"
            ),
            "observed_supported_target_value_pairs": forward.get(
                "candidate_supported_target_value_pairs"
            ),
            "observed_retained_target_value_pairs": forward.get(
                "candidate_retained_target_value_pairs"
            ),
            "failure_as_zero_tasks": forward.get("failure_as_zero_tasks"),
            "passed": mechanism_go,
        },
        "private_gold_mapping_or_evaluator_opened_or_hashed": False,
        "network_model_fetch_or_evaluator_called_by_audit": False,
        "authorization": {
            "postfreeze_external_evaluator_protocol": all(checks.values())
            and mechanism_go,
            "same_population_retry_resume_or_rerun": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "audit":
        value = build_forward_audit()
        if not value["audit_valid"]:
            raise RuntimeError(
                f"V2.49.23 forward audit failed: {value['findings']}"
            )
        _new_json(ROOT / contract.FORWARD_AUDIT, value)
        print(
            json.dumps(
                {
                    "path": str(contract.FORWARD_AUDIT),
                    "audit_valid": value["audit_valid"],
                    "mechanism_gate": value["mechanism_gate"],
                    "authorization": value["authorization"],
                },
                sort_keys=True,
            )
        )
        return
    protocol = _read(ROOT / contract.PROTOCOL)
    start = _read(ROOT / contract.EXECUTION_START)
    if (
        start.get("status") != "authorized_not_started"
        or start.get("authorization", {}).get("single_external_forward") is not True
        or protocol.get("protocol_id") != contract.PROTOCOL_ID
        or protocol.get("source_policy", {}).get(
            "deepwidebench_mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
    ):
        raise RuntimeError("V2.49.23 execution authorization drifted")
    if subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout.strip():
        raise RuntimeError("V2.49.23 forward requires clean worktree")
    if (ROOT / contract.OUTPUT_ROOT).exists():
        raise RuntimeError("V2.49.23 output root not pristine")
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v24923_target_value_external_v1",
        purpose="fresh_shared_prefix_target_value_gate",
        path=ROOT / contract.LEASE_PATH,
    ):
        if contract.protected_watcher_snapshot() != protocol["execution"][
            "protected_watchers"
        ]:
            raise RuntimeError("V2.49.23 protected watcher drifted")
        (ROOT / contract.OUTPUT_ROOT).mkdir(parents=True, mode=0o700)
        (ROOT / contract.SNAPSHOT_ROOT).mkdir(mode=0o700)
        (ROOT / contract.TARGET_RESPONSE_ROOT).mkdir(mode=0o700)
        (ROOT / contract.TASK_ROOT).mkdir(mode=0o700)
        (ROOT / contract.MODEL_SLOT_DIRECTORY).mkdir(mode=0o700)
        started = time.monotonic()
        urls = [contract.CATALOG_URL, *contract.TARGET_URLS]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls)) as pool:
            blobs = list(pool.map(_fetch_once, urls))
        catalog_blob, target_blobs = blobs[0], blobs[1:]
        _new_bytes(ROOT / contract.CATALOG_RESPONSE, catalog_blob)
        for index, blob in enumerate(target_blobs, 1):
            _new_bytes(
                ROOT / contract.TARGET_RESPONSE_ROOT / f"response_{index:02d}.bin",
                blob,
            )
        bundle, tasks, freeze = build_snapshot(catalog_blob, target_blobs)
        _new_json(ROOT / contract.FROZEN_PAGES, bundle)
        _new_json(ROOT / contract.SNAPSHOT_FREEZE, freeze)
        _new_jsonl(ROOT / contract.VISIBLE_TASKS, tasks)
        outcomes: dict[int, dict[str, Any]] = {}

        def run(index: int, task: dict[str, str]) -> tuple[int, dict[str, Any]]:
            directory = ROOT / contract.TASK_ROOT / f"task_{index:04d}"
            directory.mkdir(mode=0o700)
            task_path = directory / "visible_task.json"
            result_path = directory / "result.json"
            _new_json(task_path, task)
            completed = subprocess.run(
                [
                    str(ROOT / ".venv-eval/bin/python"),
                    "-I",
                    "-B",
                    str(ROOT / contract.CHILD),
                    "--task",
                    str(task_path),
                    "--pages",
                    str(ROOT / contract.FROZEN_PAGES),
                    "--result",
                    str(result_path),
                ],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=contract.TASK_WALL_SECONDS,
                check=False,
            )
            if completed.returncode == 0 and result_path.is_file():
                return index, _read(result_path)
            return index, _fallback(task, ROOT / contract.FROZEN_PAGES)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=contract.EXECUTOR_CONCURRENCY
        ) as pool:
            futures = [
                pool.submit(run, index, task)
                for index, task in enumerate(tasks, 1)
            ]
            for future in concurrent.futures.as_completed(futures):
                index, result = future.result()
                outcomes[index] = result
                _atomic_json(
                    ROOT / contract.SAFE_PROGRESS,
                    {
                        "artifact_version": 1,
                        "role": "v24923_safe_forward_progress",
                        "terminal_tasks": len(outcomes),
                        "selected_tasks": contract.SELECTED_COUNT,
                    },
                )
        ordered = [outcomes[index] for index in range(1, contract.SELECTED_COUNT + 1)]
        predictions = [
            {
                "opaque_id": row["opaque_id"],
                "predictions": row["predictions"],
                "prediction_sha256": row["prediction_sha256"],
                "retry_resume_skip_or_selective_rerun": False,
            }
            for row in ordered
        ]
        projections = [
            {
                "opaque_id": row["opaque_id"],
                "projection_sha256": row["projection_sha256"],
                "projection_equal": row["projection_equal"],
                "projection_receipts": row["projection_receipts"],
            }
            for row in ordered
        ]
        _new_jsonl(ROOT / contract.PREDICTIONS, predictions)
        _new_jsonl(ROOT / contract.PROJECTIONS, projections)
        failures = sum(row["status"] != "completed" for row in ordered)
        unequal = sum(row["projection_equal"] is False for row in ordered)
        retained_pairs = sum(
            int(
                row.get("projection_receipts", {})
                .get("target_value_30k", {})
                .get("retained_target_value_pair_count", 0)
            )
            for row in ordered
        )
        supported_pairs = sum(
            int(
                row.get("projection_receipts", {})
                .get("target_value_30k", {})
                .get("supported_target_value_pair_count", 0)
            )
            for row in ordered
        )
        summary: dict[str, Any] = {
            "artifact_version": 1,
            "role": "v24923_target_value_external_run_summary",
            "selected_tasks": contract.SELECTED_COUNT,
            "terminal_tasks": len(ordered),
            "failure_as_zero_tasks": failures,
            "model_generated_tasks": len(ordered) - failures,
            "projection_unequal_tasks": unequal,
            "candidate_supported_target_value_pairs": supported_pairs,
            "candidate_retained_target_value_pairs": retained_pairs,
            "candidate_mechanism_engaged": unequal > 0 and retained_pairs > 0,
            "forward_wall_seconds": round(time.monotonic() - started, 6),
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        }
        summary["summary_payload_sha256"] = contract.payload_sha256(summary)
        _new_json(ROOT / contract.RUN_SUMMARY, summary)
        freeze_value: dict[str, Any] = {
            "artifact_version": 1,
            "role": "v24923_prediction_freeze",
            "selected_tasks": contract.SELECTED_COUNT,
            "selected_arm_predictions": contract.SELECTED_COUNT * len(contract.ARMS),
            "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
            "projections_sha256": contract.sha256(ROOT / contract.PROJECTIONS),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "snapshot_freeze_sha256": contract.sha256(ROOT / contract.SNAPSHOT_FREEZE),
            "all_predictions_terminal_before_evaluator_open": True,
        }
        freeze_value["freeze_payload_sha256"] = contract.payload_sha256(freeze_value)
        _new_json(ROOT / contract.PREDICTION_FREEZE, freeze_value)
        result: dict[str, Any] = {
            "artifact_version": 1,
            "role": "v24923_target_value_external_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "selected": contract.SELECTED_COUNT,
            "terminal_predictions": contract.SELECTED_COUNT,
            "failure_as_zero_tasks": failures,
            "model_generated_tasks": len(ordered) - failures,
            "projection_unequal_tasks": unequal,
            "candidate_supported_target_value_pairs": supported_pairs,
            "candidate_retained_target_value_pairs": retained_pairs,
            "candidate_mechanism_engaged": summary["candidate_mechanism_engaged"],
            "all_predictions_terminal_before_evaluator_open": True,
            "retry_resume_skip_or_selective_rerun_launched": False,
            "forward_wall_seconds": summary["forward_wall_seconds"],
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "snapshot_freeze_sha256": contract.sha256(ROOT / contract.SNAPSHOT_FREEZE),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        }
        result["result_payload_sha256"] = contract.payload_sha256(result)
        _new_json(ROOT / contract.FORWARD_RESULT, result)
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
