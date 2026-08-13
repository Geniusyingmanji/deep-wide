#!/usr/bin/env python3
"""One-shot supervisor for a genuinely disjoint World Bank population.

The transport is the already-audited credential-free V2.52.97 helper.  This
successor changes the selection boundary and every effect surface: all 24
V2.53.05 probed targets, 144 selected entities, and 48 target-response hashes
are consumed and mechanically excluded.  A permanent claim precedes one
catalog request and one fixed 48-response target batch.  No retry, resume,
backfill, replacement, model, benchmark, or evaluator effect is available.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25315_disjoint_worldbank_population as selector  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts import run_v25297_worldbank_population_freeze as transport  # noqa: E402


DATE = "20260813"
ROLE = "v25317_disjoint_worldbank_population_freeze"
CLAIM_ROLE = "v25317_disjoint_worldbank_population_attempt_claim"
PRIVATE_ROLE = "v25317_private_disjoint_worldbank_population"
OUTPUT_ROOT = Path(f"outputs/v25317_disjoint_worldbank_population_v1_{DATE}")
CATALOG_RESPONSE = OUTPUT_ROOT / "catalog_response.bin"
TARGET_RESPONSE_ROOT = OUTPUT_ROOT / "target_responses"
POPULATION = OUTPUT_ROOT / "population.json"
ATTEMPT_CLAIM = Path(
    f"results/v25317_disjoint_worldbank_population_attempt_claim_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v25317_disjoint_worldbank_population_freeze_v1_{DATE}.json"
)
PREACTIVATION = Path(
    f"results/v25318_disjoint_worldbank_population_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25319_disjoint_worldbank_population_execution_start_v1_{DATE}.json"
)
POSTFREEZE_AUDIT = Path(
    f"results/v25320_disjoint_worldbank_population_postfreeze_audit_v1_{DATE}.json"
)
BUILD_AUDIT = Path(
    f"results/v25316_disjoint_worldbank_population_build_audit_v1_{DATE}.json"
)
BUILD_AUDIT_SHA256 = (
    "26577a73b700bb0cb5565d2f4cfe89a74757535ec7399f76d24880699b3f14c1"
)
SOURCE = Path("scripts/run_v25317_disjoint_worldbank_population.py")
TEST = Path("tests/test_run_v25317_disjoint_worldbank_population.py")
HELPER = transport.HELPER
SELECTOR = Path("src/deepwide_agent/v25315_disjoint_worldbank_population.py")
PARENT_TRANSPORT = transport.SOURCE

CATALOG_URL = transport.CATALOG_URL
CATALOG_MAXIMUM_BYTES = transport.CATALOG_MAXIMUM_BYTES
TARGET_MAXIMUM_BYTES = transport.TARGET_MAXIMUM_BYTES
CATALOG_SOCKET_TIMEOUT_SECONDS = transport.CATALOG_SOCKET_TIMEOUT_SECONDS
TARGET_SOCKET_TIMEOUT_SECONDS = transport.TARGET_SOCKET_TIMEOUT_SECONDS
CATALOG_PHASE_HARD_WALL_SECONDS = 30.0
TARGET_PHASE_HARD_WALL_SECONDS = 110.0
WHOLE_FREEZE_HARD_WALL_SECONDS = 145.0
TARGET_CONCURRENCY = 12
EXPECTED_WATCHERS = transport.EXPECTED_WATCHERS
HISTORICAL_TARGET_KEYS = tuple(
    f"{indicator}@{selector.TARGET_YEAR}"
    for indicator in sorted(transport.EXPECTED_HISTORICAL_INDICATORS)
)


def payload_sha256(value: object) -> str:
    return transport.payload_sha256(value)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _ordinary(relative: Path, *, required: bool = True) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.resolve(strict=False).is_relative_to(ROOT.resolve())
    ):
        raise ValueError("V2.53.17 path drifted")
    if required and not path.is_file():
        raise FileNotFoundError(relative)
    return path


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def publish_exclusive(path: Path, data: bytes) -> None:
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


def publish_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    publish_exclusive(
        path,
        (
            json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode(),
    )


def _build_authority() -> dict[str, Any]:
    path = _ordinary(BUILD_AUDIT)
    if sha256(path) != BUILD_AUDIT_SHA256:
        raise RuntimeError("V2.53.17 build audit hash drifted")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError("V2.53.17 build audit schema drifted")
    unsigned = dict(value)
    signature = unsigned.pop("audit_payload_sha256", None)
    authorization = value.get("authorization") or {}
    consumed = value.get("consumed_manifest") or {}
    checks = consumed.get("checks") or {}
    targets = consumed.get("target_keys")
    entities = consumed.get("entity_codes")
    responses = consumed.get("response_sha256")
    if (
        value.get("role")
        != "v25316_disjoint_worldbank_population_clean_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or signature != payload_sha256(unsigned)
        or authorization.get(
            "fresh_disjoint_worldbank_population_supervisor_build_only"
        )
        is not True
        or authorization.get("network_population_selection_or_freeze") is not False
        or authorization.get("external_activation_or_launch") is not False
        or not isinstance(targets, list)
        or len(targets) != 24
        or len(set(item.casefold() for item in targets)) != 24
        or not isinstance(entities, list)
        or len(entities) != 144
        or len(set(entities)) != 144
        or not isinstance(responses, list)
        or len(responses) != 48
        or len(set(responses)) != 48
        or any(re.fullmatch(r"[0-9a-f]{64}", item) is None for item in responses)
        or not checks
        or any(item is not True for item in checks.values())
    ):
        raise RuntimeError("V2.53.17 build authority drifted")
    return {
        "path": str(BUILD_AUDIT),
        "sha256": BUILD_AUDIT_SHA256,
        "consumed_target_keys": list(targets),
        "consumed_entity_codes": list(entities),
        "consumed_response_sha256": list(responses),
        "consumed_target_keys_sha256": consumed["target_keys_sha256"],
        "consumed_entity_codes_sha256": consumed["entity_codes_sha256"],
        "consumed_response_vector_sha256": consumed["response_vector_sha256"],
    }


def invoke_helper(
    url: str, maximum: int, timeout_seconds: float
) -> tuple[bytes | None, dict[str, Any]]:
    return transport.invoke_helper(url, maximum, timeout_seconds)


def _request_target_pages(
    targets: Sequence[selector.TargetSpec],
    *,
    get: Callable[
        [str, int, float], tuple[bytes | None, dict[str, Any]]
    ],
) -> tuple[
    dict[selector.TargetSpec, tuple[bytes, bytes]],
    dict[tuple[int, int], bytes],
    list[dict[str, Any]],
    float,
]:
    return transport._request_target_pages(targets, get=get)


def _protected_watchers_match() -> bool:
    return transport._protected_watchers_match()


def build_attempt_claim(
    *, head: str, execution_start_sha256: str, now: int | None = None
) -> dict[str, Any]:
    if (
        re.fullmatch(r"[0-9a-f]{40}", head) is None
        or re.fullmatch(r"[0-9a-f]{64}", execution_start_sha256) is None
    ):
        raise ValueError("V2.53.17 claim authority drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CLAIM_ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "execution_start": {
            "path": str(EXECUTION_START),
            "sha256": execution_start_sha256,
        },
        "build_audit": {"path": str(BUILD_AUDIT), "sha256": BUILD_AUDIT_SHA256},
        "fixed_result_path": str(RESULT),
        "fixed_output_root": str(OUTPUT_ROOT),
        "claim_created_before_catalog_or_target_network_effect": True,
        "claim_is_permanent_even_on_crash_or_no_go": True,
        "single_catalog_and_single_48_response_batch_only": True,
        "old_24_targets_144_entities_and_48_responses_are_consumed": True,
        "retry_resume_backfill_replacement_or_second_attempt": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }
    value["claim_payload_sha256"] = payload_sha256(value)
    return validate_attempt_claim(value)


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("claim_payload_sha256", None)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git_head",
            "execution_start",
            "build_audit",
            "fixed_result_path",
            "fixed_output_root",
            "claim_created_before_catalog_or_target_network_effect",
            "claim_is_permanent_even_on_crash_or_no_go",
            "single_catalog_and_single_48_response_batch_only",
            "old_24_targets_144_entities_and_48_responses_are_consumed",
            "retry_resume_backfill_replacement_or_second_attempt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CLAIM_ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_head"))) is None
        or copied.get("execution_start")
        != {
            "path": str(EXECUTION_START),
            "sha256": copied.get("execution_start", {}).get("sha256"),
        }
        or re.fullmatch(
            r"[0-9a-f]{64}", str(copied.get("execution_start", {}).get("sha256"))
        )
        is None
        or copied.get("build_audit")
        != {"path": str(BUILD_AUDIT), "sha256": BUILD_AUDIT_SHA256}
        or copied.get("fixed_result_path") != str(RESULT)
        or copied.get("fixed_output_root") != str(OUTPUT_ROOT)
        or copied.get("claim_created_before_catalog_or_target_network_effect")
        is not True
        or copied.get("claim_is_permanent_even_on_crash_or_no_go") is not True
        or copied.get("single_catalog_and_single_48_response_batch_only") is not True
        or copied.get("old_24_targets_144_entities_and_48_responses_are_consumed")
        is not True
        or copied.get("retry_resume_backfill_replacement_or_second_attempt")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.17 attempt claim drifted")
    return copied


def execute_freeze(
    *,
    head: str,
    execution_start_sha256: str,
    attempt_claim_sha256: str,
    get: Callable[
        [str, int, float], tuple[bytes | None, dict[str, Any]]
    ] = invoke_helper,
    persist: bool = True,
    now: int | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    authority = _build_authority()
    catalog_started = time.monotonic()
    catalog_body, catalog_receipt = get(
        CATALOG_URL, CATALOG_MAXIMUM_BYTES, CATALOG_SOCKET_TIMEOUT_SECONDS
    )
    catalog_elapsed = time.monotonic() - catalog_started
    candidates: list[selector.TargetSpec] = []
    catalog_stats = {
        "catalog_total": 0,
        "historical_target_count": len(HISTORICAL_TARGET_KEYS),
        "consumed_target_count": 24,
        "runtime_compatible_fresh_count": 0,
        "selected_candidate_count": 0,
    }
    failure: str | None = None
    if catalog_body is not None and persist:
        publish_exclusive(ROOT / CATALOG_RESPONSE, catalog_body)
    if catalog_body is None:
        failure = "catalog_transport"
    elif hashlib.sha256(catalog_body).hexdigest() != str(
        catalog_receipt.get("response_sha256")
    ):
        failure = "catalog_body_receipt_mismatch"
    elif catalog_elapsed > CATALOG_PHASE_HARD_WALL_SECONDS:
        failure = "catalog_hard_wall"
    else:
        try:
            candidates, catalog_stats = selector.parse_catalog(
                catalog_body,
                historical_target_keys=HISTORICAL_TARGET_KEYS,
                consumed_target_keys=authority["consumed_target_keys"],
            )
        except (RuntimeError, ValueError):
            failure = "catalog_validation_or_capacity"
    candidate_keys = [target.key for target in candidates]
    target_rows: list[dict[str, Any]] = []
    candidate_bodies: dict[selector.TargetSpec, tuple[bytes, bytes]] = {}
    target_elapsed = 0.0
    population_value: dict[str, Any] | None = None
    response_overlap_count = 0
    response_body_receipt_mismatch_count = 0
    if failure is None:
        candidate_bodies, successful_bodies, target_rows, target_elapsed = (
            _request_target_pages(candidates, get=get)
        )
        consumed_responses = set(authority["consumed_response_sha256"])
        response_body_receipt_mismatch_count = sum(
            hashlib.sha256(successful_bodies[key]).hexdigest()
            != str(row.get("response_sha256"))
            for row in target_rows
            for key in [
                (int(row["candidate_ordinal"]), int(row["page"]))
            ]
            if key in successful_bodies
        )
        response_overlap_count = sum(
            hashlib.sha256(successful_bodies[key]).hexdigest()
            in consumed_responses
            for row in target_rows
            for key in [
                (int(row["candidate_ordinal"]), int(row["page"]))
            ]
            if key in successful_bodies
        )
        for row in target_rows:
            key = (int(row["candidate_ordinal"]), int(row["page"]))
            if key in successful_bodies:
                body = successful_bodies[key]
                relative = (
                    TARGET_RESPONSE_ROOT
                    / f"response_{key[0]:02d}_page_{key[1]}.bin"
                )
                row["response_path"] = str(relative)
                if persist:
                    publish_exclusive(ROOT / relative, body)
            else:
                row["response_path"] = None
        if (
            len(target_rows) != 48
            or len(candidate_bodies) != selector.MINIMUM_TARGET_OVERSAMPLE
            or any(row["outcome"] != "success" for row in target_rows)
            or target_elapsed > TARGET_PHASE_HARD_WALL_SECONDS
        ):
            failure = "target_transport_or_hard_wall"
        elif response_body_receipt_mismatch_count:
            failure = "response_body_receipt_mismatch"
        elif response_overlap_count:
            failure = "consumed_response_overlap"
    if failure is None:
        try:
            population_value = selector.select_and_render_population(
                candidate_bodies,
                consumed_target_keys=authority["consumed_target_keys"],
                consumed_entity_codes=authority["consumed_entity_codes"],
                consumed_response_sha256=authority["consumed_response_sha256"],
            )
        except (RuntimeError, ValueError):
            failure = "population_disjoint_capacity_or_rendering"
    elapsed = time.monotonic() - started
    if elapsed > WHOLE_FREEZE_HARD_WALL_SECONDS and failure is None:
        failure = "whole_freeze_hard_wall"
        population_value = None
    population_sha: str | None = None
    if population_value is not None and failure is None:
        envelope: dict[str, Any] = {
            "artifact_version": 1,
            "role": PRIVATE_ROLE,
            "build_audit": {
                "path": str(BUILD_AUDIT),
                "sha256": BUILD_AUDIT_SHA256,
            },
            "candidate_target_keys": candidate_keys,
            "historical_target_keys_sha256": payload_sha256(
                list(HISTORICAL_TARGET_KEYS)
            ),
            "consumed_manifest": {
                "target_count": 24,
                "target_keys_sha256": authority[
                    "consumed_target_keys_sha256"
                ],
                "entity_count": 144,
                "entity_codes_sha256": authority[
                    "consumed_entity_codes_sha256"
                ],
                "response_count": 48,
                "response_vector_sha256": authority[
                    "consumed_response_vector_sha256"
                ],
            },
            "population": population_value,
        }
        envelope["population_payload_sha256"] = payload_sha256(envelope)
        encoded = (
            json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode()
        population_sha = hashlib.sha256(encoded).hexdigest()
        if persist:
            publish_exclusive(ROOT / POPULATION, encoded)
    selected_keys = list(population_value["target_keys"]) if population_value else []
    entities = list(population_value["entities"]) if population_value else []
    tasks = list(population_value["tasks"]) if population_value else []
    rows_per_task = int(population_value["rows_per_task"]) if population_value else 0
    decision = "go" if failure is None and population_value is not None else "no_go"
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "execution_start": {
            "path": str(EXECUTION_START),
            "sha256": execution_start_sha256,
        },
        "attempt_claim": {
            "path": str(ATTEMPT_CLAIM),
            "sha256": attempt_claim_sha256,
        },
        "build_audit": {"path": str(BUILD_AUDIT), "sha256": BUILD_AUDIT_SHA256},
        "decision": decision,
        "failure_code": failure,
        "catalog": {
            **catalog_receipt,
            **catalog_stats,
            "phase_elapsed_seconds": round(catalog_elapsed, 6),
            "url": CATALOG_URL,
            "response_path": str(CATALOG_RESPONSE)
            if catalog_body is not None
            else None,
            "self_proved_one_page_complete": bool(candidates),
        },
        "historical_target_count": len(HISTORICAL_TARGET_KEYS),
        "historical_target_keys_sha256": payload_sha256(
            list(HISTORICAL_TARGET_KEYS)
        ),
        "consumed_manifest": {
            "target_count": 24,
            "target_keys_sha256": authority["consumed_target_keys_sha256"],
            "entity_count": 144,
            "entity_codes_sha256": authority["consumed_entity_codes_sha256"],
            "response_count": 48,
            "response_vector_sha256": authority[
                "consumed_response_vector_sha256"
            ],
        },
        "candidate_target_keys": candidate_keys,
        "candidate_target_count": len(candidate_keys),
        "target_transport": {
            "fixed_request_count": 48,
            "concurrency": TARGET_CONCURRENCY,
            "elapsed_seconds": round(target_elapsed, 6),
            "rows": target_rows,
            "successful_response_count": sum(
                row.get("outcome") == "success" for row in target_rows
            ),
            "provider_attempt_count": sum(
                int(row.get("provider_attempt_count") or 0) for row in target_rows
            ),
            "response_body_receipt_mismatch_count": response_body_receipt_mismatch_count,
            "consumed_response_overlap_count": response_overlap_count,
        },
        "population": {
            "private_path": str(POPULATION) if population_sha else None,
            "private_sha256": population_sha,
            "selected_target_keys": selected_keys,
            "selected_target_count": len(selected_keys),
            "entity_count": len(entities),
            "entities_sha256": payload_sha256(entities) if entities else None,
            "rows_per_task": rows_per_task,
            "task_count": len(tasks),
            "task_vector_sha256": payload_sha256(tasks) if tasks else None,
            "rendered_page_count": len(population_value["pages"])
            if population_value
            else 0,
            "selected_target_overlap_count": (
                population_value["disjointness_receipt"][
                    "selected_target_overlap_count"
                ]
                if population_value
                else 0
            ),
            "selected_entity_overlap_count": (
                population_value["disjointness_receipt"][
                    "selected_entity_overlap_count"
                ]
                if population_value
                else 0
            ),
            "selected_response_overlap_count": (
                population_value["disjointness_receipt"][
                    "selected_response_overlap_count"
                ]
                if population_value
                else 0
            ),
        },
        "effect_accounting": {
            "catalog_provider_attempt_count": int(
                catalog_receipt.get("provider_attempt_count") or 0
            ),
            "target_provider_attempt_count": sum(
                int(row.get("provider_attempt_count") or 0) for row in target_rows
            ),
            "redirect_retry_refetch_resume_backfill_replacement_count": 0,
            "model_search_evaluator_or_benchmark_effect_count": 0,
            "public_worldbank_network_or_api_called": bool(
                int(catalog_receipt.get("provider_attempt_count") or 0)
                + sum(
                    int(row.get("provider_attempt_count") or 0)
                    for row in target_rows
                )
            ),
        },
        "whole_elapsed_seconds": round(elapsed, 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "external_monotone_fill_protocol_after_valid_postfreeze_audit": decision
            == "go",
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_population_attempt": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["freeze_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def _receipt_shape(row: Mapping[str, Any]) -> bool:
    return bool(
        set(row)
        == {
            "candidate_ordinal",
            "target_key",
            "page",
            "url_sha256",
            "maximum_response_bytes",
            "provider_attempt_count",
            "outcome",
            "failure_code",
            "http_status",
            "elapsed_seconds",
            "response_bytes",
            "response_sha256",
            "redirect_retry_refetch_count",
            "response_path",
        }
        and isinstance(row.get("candidate_ordinal"), int)
        and not isinstance(row.get("candidate_ordinal"), bool)
        and row.get("page") in {1, 2}
        and row.get("provider_attempt_count") in {0, 1}
        and row.get("outcome") in {"success", "failure"}
        and row.get("maximum_response_bytes") == TARGET_MAXIMUM_BYTES
        and row.get("redirect_retry_refetch_count") == 0
        and isinstance(row.get("elapsed_seconds"), (int, float))
        and not isinstance(row.get("elapsed_seconds"), bool)
        and math.isfinite(float(row["elapsed_seconds"]))
        and 0 <= float(row["elapsed_seconds"]) <= transport.HELPER_HARD_TIMEOUT_SECONDS + 2
    )


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("freeze_payload_sha256", None)
    decision = copied.get("decision")
    go = decision == "go"
    catalog = copied.get("catalog") or {}
    target = copied.get("target_transport") or {}
    rows = target.get("rows")
    population = copied.get("population") or {}
    effects = copied.get("effect_accounting") or {}
    authorization = copied.get("authorization") or {}
    candidate_keys = copied.get("candidate_target_keys")
    execution_start = copied.get("execution_start") or {}
    attempt_claim = copied.get("attempt_claim") or {}
    catalog_receipt_keys = {
        "url_sha256",
        "maximum_response_bytes",
        "provider_attempt_count",
        "outcome",
        "failure_code",
        "http_status",
        "elapsed_seconds",
        "response_bytes",
        "response_sha256",
        "redirect_retry_refetch_count",
        "catalog_total",
        "historical_target_count",
        "consumed_target_count",
        "runtime_compatible_fresh_count",
        "selected_candidate_count",
        "phase_elapsed_seconds",
        "url",
        "response_path",
        "self_proved_one_page_complete",
    }
    expected_empty_population = {
        "private_path": None,
        "private_sha256": None,
        "selected_target_keys": [],
        "selected_target_count": 0,
        "entity_count": 0,
        "entities_sha256": None,
        "rows_per_task": 0,
        "task_count": 0,
        "task_vector_sha256": None,
        "rendered_page_count": 0,
        "selected_target_overlap_count": 0,
        "selected_entity_overlap_count": 0,
        "selected_response_overlap_count": 0,
    }
    row_identity = isinstance(rows, list) and all(
        isinstance(row, Mapping) and _receipt_shape(row) for row in rows
    )
    if row_identity and isinstance(candidate_keys, list):
        expected_pairs = {
            (index, page)
            for index in range(1, len(candidate_keys) + 1)
            for page in (1, 2)
        }
        row_identity = {
            (row["candidate_ordinal"], row["page"]) for row in rows
        } == (expected_pairs if rows else set())
        for row in rows:
            index = int(row["candidate_ordinal"])
            key = candidate_keys[index - 1] if 0 < index <= len(candidate_keys) else ""
            indicator = key.rsplit("@", 1)[0] if isinstance(key, str) else ""
            expected_path = (
                TARGET_RESPONSE_ROOT
                / f"response_{index:02d}_page_{row['page']}.bin"
            )
            success = row["outcome"] == "success"
            if (
                row["target_key"] != key
                or row["url_sha256"]
                != hashlib.sha256(
                    selector.target_urls(indicator)[int(row["page"]) - 1].encode()
                ).hexdigest()
                or (
                    success
                    and (
                        row["provider_attempt_count"] != 1
                        or row["failure_code"] is not None
                        or row["http_status"] != 200
                        or not isinstance(row["response_bytes"], int)
                        or row["response_bytes"] <= 0
                        or re.fullmatch(
                            r"[0-9a-f]{64}", str(row["response_sha256"])
                        )
                        is None
                        or row["response_path"] != str(expected_path)
                    )
                )
                or (
                    not success
                    and (
                        not isinstance(row["failure_code"], str)
                        or row["response_bytes"] != 0
                        or row["response_sha256"] is not None
                        or row["response_path"] is not None
                    )
                )
            ):
                row_identity = False
                break
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git_head",
            "execution_start",
            "attempt_claim",
            "build_audit",
            "decision",
            "failure_code",
            "catalog",
            "historical_target_count",
            "historical_target_keys_sha256",
            "consumed_manifest",
            "candidate_target_keys",
            "candidate_target_count",
            "target_transport",
            "population",
            "effect_accounting",
            "whole_elapsed_seconds",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "freeze_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_head"))) is None
        or set(execution_start) != {"path", "sha256"}
        or execution_start.get("path") != str(EXECUTION_START)
        or re.fullmatch(r"[0-9a-f]{64}", str(execution_start.get("sha256")))
        is None
        or set(attempt_claim) != {"path", "sha256"}
        or attempt_claim.get("path") != str(ATTEMPT_CLAIM)
        or re.fullmatch(r"[0-9a-f]{64}", str(attempt_claim.get("sha256")))
        is None
        or copied.get("build_audit")
        != {"path": str(BUILD_AUDIT), "sha256": BUILD_AUDIT_SHA256}
        or decision not in {"go", "no_go"}
        or (copied.get("failure_code") is None) is not go
        or not isinstance(catalog, Mapping)
        or set(catalog) != catalog_receipt_keys
        or catalog.get("url") != CATALOG_URL
        or catalog.get("url_sha256")
        != hashlib.sha256(CATALOG_URL.encode()).hexdigest()
        or catalog.get("maximum_response_bytes") != CATALOG_MAXIMUM_BYTES
        or catalog.get("provider_attempt_count") not in {0, 1}
        or catalog.get("redirect_retry_refetch_count") != 0
        or catalog.get("outcome") not in {"success", "failure"}
        or not isinstance(catalog.get("elapsed_seconds"), (int, float))
        or isinstance(catalog.get("elapsed_seconds"), bool)
        or not math.isfinite(float(catalog["elapsed_seconds"]))
        or not 0 <= float(catalog["elapsed_seconds"]) <= transport.HELPER_HARD_TIMEOUT_SECONDS + 2
        or not isinstance(catalog.get("phase_elapsed_seconds"), (int, float))
        or isinstance(catalog.get("phase_elapsed_seconds"), bool)
        or not math.isfinite(float(catalog["phase_elapsed_seconds"]))
        or float(catalog["phase_elapsed_seconds"]) < 0
        or any(
            isinstance(catalog.get(name), bool)
            or not isinstance(catalog.get(name), int)
            or catalog[name] < 0
            for name in (
                "catalog_total",
                "historical_target_count",
                "consumed_target_count",
                "runtime_compatible_fresh_count",
                "selected_candidate_count",
            )
        )
        or catalog.get("historical_target_count") != len(HISTORICAL_TARGET_KEYS)
        or catalog.get("consumed_target_count") != 24
        or not isinstance(catalog.get("self_proved_one_page_complete"), bool)
        or catalog.get("self_proved_one_page_complete")
        is not (len(candidate_keys) == selector.MINIMUM_TARGET_OVERSAMPLE)
        or (
            catalog.get("outcome") == "success"
            and (
                catalog.get("provider_attempt_count") != 1
                or catalog.get("failure_code") is not None
                or catalog.get("http_status") != 200
                or not isinstance(catalog.get("response_bytes"), int)
                or catalog["response_bytes"] <= 0
                or re.fullmatch(
                    r"[0-9a-f]{64}", str(catalog.get("response_sha256"))
                )
                is None
                or catalog.get("response_path") != str(CATALOG_RESPONSE)
            )
        )
        or (
            catalog.get("outcome") == "failure"
            and (
                not isinstance(catalog.get("failure_code"), str)
                or catalog.get("response_bytes") != 0
                or catalog.get("response_sha256") is not None
                or catalog.get("response_path") is not None
            )
        )
        or copied.get("historical_target_count") != len(HISTORICAL_TARGET_KEYS)
        or copied.get("historical_target_keys_sha256")
        != payload_sha256(list(HISTORICAL_TARGET_KEYS))
        or copied.get("consumed_manifest")
        != {
            "target_count": 24,
            "target_keys_sha256": _build_authority()[
                "consumed_target_keys_sha256"
            ],
            "entity_count": 144,
            "entity_codes_sha256": _build_authority()[
                "consumed_entity_codes_sha256"
            ],
            "response_count": 48,
            "response_vector_sha256": _build_authority()[
                "consumed_response_vector_sha256"
            ],
        }
        or not isinstance(candidate_keys, list)
        or len(candidate_keys) != len(set(candidate_keys))
        or copied.get("candidate_target_count") != len(candidate_keys)
        or any(
            not isinstance(key, str)
            or not key.endswith("@2022")
            or selector.parent.INDICATOR.fullmatch(key.rsplit("@", 1)[0]) is None
            for key in candidate_keys
        )
        or not isinstance(rows, list)
        or len(rows) not in {0, 48}
        or not row_identity
        or not isinstance(target, Mapping)
        or set(target)
        != {
            "fixed_request_count",
            "concurrency",
            "elapsed_seconds",
            "rows",
            "successful_response_count",
            "provider_attempt_count",
            "response_body_receipt_mismatch_count",
            "consumed_response_overlap_count",
        }
        or target.get("fixed_request_count") != 48
        or target.get("concurrency") != TARGET_CONCURRENCY
        or target.get("successful_response_count")
        != sum(row.get("outcome") == "success" for row in rows)
        or target.get("provider_attempt_count")
        != sum(int(row.get("provider_attempt_count") or 0) for row in rows)
        or not isinstance(target.get("response_body_receipt_mismatch_count"), int)
        or target.get("response_body_receipt_mismatch_count") < 0
        or not isinstance(target.get("consumed_response_overlap_count"), int)
        or target.get("consumed_response_overlap_count") < 0
        or not isinstance(target.get("elapsed_seconds"), (int, float))
        or isinstance(target.get("elapsed_seconds"), bool)
        or not math.isfinite(float(target["elapsed_seconds"]))
        or float(target["elapsed_seconds"]) < 0
        or not isinstance(population, Mapping)
        or set(population) != set(expected_empty_population)
        or not isinstance(effects, Mapping)
        or set(effects)
        != {
            "catalog_provider_attempt_count",
            "target_provider_attempt_count",
            "redirect_retry_refetch_resume_backfill_replacement_count",
            "model_search_evaluator_or_benchmark_effect_count",
            "public_worldbank_network_or_api_called",
        }
        or effects.get("catalog_provider_attempt_count")
        != catalog.get("provider_attempt_count")
        or effects.get("catalog_provider_attempt_count") not in {0, 1}
        or effects.get("target_provider_attempt_count")
        != target.get("provider_attempt_count")
        or effects.get("redirect_retry_refetch_resume_backfill_replacement_count")
        != 0
        or effects.get("model_search_evaluator_or_benchmark_effect_count") != 0
        or effects.get("public_worldbank_network_or_api_called")
        is not bool(
            effects.get("catalog_provider_attempt_count")
            + effects.get("target_provider_attempt_count")
        )
        or not isinstance(copied.get("whole_elapsed_seconds"), (int, float))
        or isinstance(copied.get("whole_elapsed_seconds"), bool)
        or not math.isfinite(float(copied["whole_elapsed_seconds"]))
        or float(copied["whole_elapsed_seconds"]) < 0
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "external_monotone_fill_protocol_after_valid_postfreeze_audit": go,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_population_attempt": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or (
            go
            and (
                len(candidate_keys) != 24
                or len(rows) != 48
                or target.get("successful_response_count") != 48
                or target.get("provider_attempt_count") != 48
                or target.get("response_body_receipt_mismatch_count") != 0
                or target.get("consumed_response_overlap_count") != 0
                or population.get("selected_target_count") != 4
                or population.get("entity_count") not in {96, 108}
                or population.get("rows_per_task") not in {8, 9}
                or population.get("entity_count")
                != population.get("rows_per_task") * 12
                or population.get("task_count") != 12
                or population.get("rendered_page_count") != 8
                or population.get("selected_target_overlap_count") != 0
                or population.get("selected_entity_overlap_count") != 0
                or population.get("selected_response_overlap_count") != 0
                or not population.get("private_sha256")
            )
        )
        or (not go and population != expected_empty_population)
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.17 population result drifted")
    return copied


def _source_manifest() -> dict[str, str]:
    return {
        str(path): sha256(_ordinary(path))
        for path in (SOURCE, HELPER, SELECTOR, PARENT_TRANSPORT, TEST)
    }


def _preactivation_authority() -> bool:
    try:
        value = json.loads(_ordinary(PREACTIVATION).read_text(encoding="utf-8"))
        unsigned = dict(value)
        signature = unsigned.pop("audit_payload_sha256", None)
        authorization = value.get("authorization") or {}
        git = value.get("git") or {}
        checks = value.get("checks") or {}
        semantic = value.get("semantic_audit") or {}
        return bool(
            set(value)
            == {
                "artifact_version",
                "role",
                "created_at_unix",
                "git",
                "fixed_inputs",
                "implementation_commit",
                "source_manifest",
                "tests",
                "runtime_dependency_vector",
                "runtime_dependency_vector_sha256",
                "runtime_dependency_path_sha256",
                "semantic_audit",
                "runtime_invariants",
                "disjointness_contract",
                "protected_watchers",
                "shared_api_lease_inactive",
                "active_conflicts",
                "future_surfaces_pristine",
                "checks",
                "findings",
                "audit_valid",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
                "authorization",
                "audit_payload_sha256",
            }
            and value.get("role")
            == "v25318_disjoint_worldbank_population_preactivation_audit"
            and isinstance(value.get("created_at_unix"), int)
            and not isinstance(value.get("created_at_unix"), bool)
            and isinstance(git, Mapping)
            and git.get("head") == git.get("target_main")
            and git.get("equal") is True
            and git.get("clean") is True
            and value.get("audit_valid") is True
            and value.get("findings") == []
            and isinstance(checks, Mapping)
            and checks
            and all(item is True for item in checks.values())
            and value.get("source_manifest") == _source_manifest()
            and semantic.get("privileged_runtime_field_accesses") == []
            and semantic.get("evaluator_capabilities") == []
            and semantic.get("credential_literal_hits") == []
            and semantic.get("auditor_or_explicit_file_credential_literal_hits")
            == []
            and semantic.get("untracked_sources") == []
            and value.get("disjointness_contract")
            == {
                "consumed_target_count": 24,
                "consumed_entity_count": 144,
                "consumed_response_count": 48,
                "preferred_entity_count": 108,
                "minimum_entity_count": 96,
                "task_count": 12,
                "all_overlap_counts_must_be_zero": True,
            }
            and value.get("active_conflicts") == []
            and value.get("future_surfaces_pristine") is True
            and value.get("shared_api_lease_inactive") is True
            and value.get(
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
            )
            is False
            and value.get(
                "network_model_search_fetch_evaluator_benchmark_or_api_called"
            )
            is False
            and authorization
            == {
                "execution_start_generation": True,
                "single_disjoint_worldbank_population_freeze": False,
                "external_forward_or_evaluator": False,
                "deepwidebench_dev64_exact220_forward_or_evaluator": False,
                "retry_resume_backfill_replacement_or_second_attempt": False,
            }
            and signature == payload_sha256(unsigned)
        )
    except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _validate_execution_start(
    value: Mapping[str, Any], *, current_head: str
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("start_payload_sha256", None)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git_parent",
            "preactivation_audit",
            "source_manifest",
            "runtime_state",
            "transport_contract",
            "disjointness_contract",
            "fixed_attempt_claim_path",
            "fixed_result_path",
            "fixed_output_root",
            "single_catalog_then_single_48_target_response_batch",
            "retry_resume_refetch_backfill_replacement_or_second_attempt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "start_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25319_disjoint_worldbank_population_execution_start"
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or re.fullmatch(r"[0-9a-f]{40}", current_head) is None
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_parent"))) is None
        or copied.get("preactivation_audit")
        != {
            "path": str(PREACTIVATION),
            "sha256": sha256(_ordinary(PREACTIVATION)),
        }
        or copied.get("source_manifest") != _source_manifest()
        or copied.get("runtime_state")
        != {
            "protected_watchers": list(EXPECTED_WATCHERS),
            "shared_api_lease_inactive": True,
        }
        or copied.get("transport_contract")
        != {
            "catalog_url": CATALOG_URL,
            "catalog_provider_attempt_count": 1,
            "candidate_target_count": 24,
            "target_provider_attempt_count": 48,
            "target_concurrency": TARGET_CONCURRENCY,
            "catalog_phase_hard_wall_seconds": CATALOG_PHASE_HARD_WALL_SECONDS,
            "target_phase_hard_wall_seconds": TARGET_PHASE_HARD_WALL_SECONDS,
            "whole_freeze_hard_wall_seconds": WHOLE_FREEZE_HARD_WALL_SECONDS,
        }
        or copied.get("disjointness_contract")
        != {
            "consumed_target_count": 24,
            "consumed_entity_count": 144,
            "consumed_response_count": 48,
            "preferred_entity_count": 108,
            "minimum_entity_count": 96,
            "task_count": 12,
            "all_overlap_counts_must_be_zero": True,
        }
        or copied.get("fixed_attempt_claim_path") != str(ATTEMPT_CLAIM)
        or copied.get("fixed_result_path") != str(RESULT)
        or copied.get("fixed_output_root") != str(OUTPUT_ROOT)
        or copied.get("single_catalog_then_single_48_target_response_batch")
        is not True
        or copied.get("retry_resume_refetch_backfill_replacement_or_second_attempt")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization")
        != {
            "single_disjoint_worldbank_population_freeze": True,
            "external_forward_or_evaluator": False,
        }
        or not _preactivation_authority()
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.19 execution start drifted")
    return copied


def main() -> None:
    head = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain") or head != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.53.17 requires clean pushed HEAD")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (ATTEMPT_CLAIM, RESULT, OUTPUT_ROOT, POSTFREEZE_AUDIT)
    ):
        raise FileExistsError("V2.53.17 future surface is not pristine")
    start_path = _ordinary(EXECUTION_START)
    start = _validate_execution_start(
        json.loads(start_path.read_text(encoding="utf-8")), current_head=head
    )
    if (
        _git("rev-parse", f"{head}^") != start["git_parent"]
        or sorted(
            line
            for line in _git(
                "diff-tree", "--no-commit-id", "--name-only", "-r", head
            ).splitlines()
            if line
        )
        != [str(EXECUTION_START)]
    ):
        raise RuntimeError("V2.53.19 execution-start commit boundary drifted")
    if not _protected_watchers_match():
        raise RuntimeError("V2.53.17 protected watcher identity drifted")
    start_sha = sha256(start_path)
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25317_disjoint_worldbank_population_freeze",
        purpose="single_catalog_and_single_48_response_disjoint_population_freeze",
    ):
        claim = build_attempt_claim(
            head=head, execution_start_sha256=start_sha
        )
        publish_json_exclusive(ROOT / ATTEMPT_CLAIM, claim)
        result = execute_freeze(
            head=head,
            execution_start_sha256=start_sha,
            attempt_claim_sha256=sha256(ROOT / ATTEMPT_CLAIM),
        )
        publish_json_exclusive(ROOT / RESULT, result)
    print(
        json.dumps(
            {
                "result": str(RESULT),
                "decision": result["decision"],
                "failure_code": result["failure_code"],
                "catalog_attempts": result["effect_accounting"][
                    "catalog_provider_attempt_count"
                ],
                "target_attempts": result["effect_accounting"][
                    "target_provider_attempt_count"
                ],
                "successful_target_responses": result["target_transport"][
                    "successful_response_count"
                ],
                "selected_targets": result["population"][
                    "selected_target_count"
                ],
                "entities": result["population"]["entity_count"],
                "tasks": result["population"]["task_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
