#!/usr/bin/env python3
"""One-shot concurrency-three, four-attempt-disjoint World Bank population supervisor.

The 48 fixed target requests retain at most three in flight. Their actual
provider starts remain ticket ordered, with no additional pacing interval.
Every URL still has one provider attempt and there is no retry, resume,
refetch, backfill, replacement, model, benchmark, or evaluator capability.
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
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25336_four_attempt_disjoint_worldbank_population as selector  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts import audit_v25334_rate_paced_worldbank_population_nogo as fourth_audit  # noqa: E402
from scripts import diagnose_v25335_v25330_transport_capacity as diagnosis  # noqa: E402
from scripts import run_v25297_worldbank_population_freeze as first  # noqa: E402
from scripts import run_v25317_disjoint_worldbank_population as second  # noqa: E402
from scripts import run_v25323_low_concurrency_worldbank_population as third  # noqa: E402
from scripts import run_v25330_rate_paced_worldbank_population as fourth  # noqa: E402


DATE = "20260813"
ROLE = "v25337_concurrency3_worldbank_population_freeze"
CLAIM_ROLE = "v25337_concurrency3_worldbank_population_attempt_claim"
PRIVATE_ROLE = "v25337_private_four_attempt_disjoint_worldbank_population"
OUTPUT_ROOT = Path(f"outputs/v25337_concurrency3_worldbank_population_v1_{DATE}")
CATALOG_RESPONSE = OUTPUT_ROOT / "catalog_response.bin"
TARGET_RESPONSE_ROOT = OUTPUT_ROOT / "target_responses"
POPULATION = OUTPUT_ROOT / "population.json"
ATTEMPT_CLAIM = Path(
    f"results/v25337_concurrency3_worldbank_population_attempt_claim_v1_{DATE}.json"
)
RESULT = Path(f"results/v25337_concurrency3_worldbank_population_freeze_v1_{DATE}.json")
BUILD_AUDIT = Path(
    f"results/v25338_concurrency3_worldbank_population_build_audit_v1_{DATE}.json"
)
PREACTIVATION = Path(
    f"results/v25339_concurrency3_worldbank_population_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25340_concurrency3_worldbank_population_execution_start_v1_{DATE}.json"
)
POSTFREEZE_AUDIT = Path(
    f"results/v25341_concurrency3_worldbank_population_postfreeze_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/run_v25337_concurrency3_worldbank_population.py")
TEST = Path("tests/test_run_v25337_concurrency3_worldbank_population.py")
HELPER = first.HELPER
SELECTOR = Path("src/deepwide_agent/v25336_four_attempt_disjoint_worldbank_population.py")
DIAGNOSIS = diagnosis.OUTPUT
DIAGNOSIS_SHA256 = (
    "63bd489d140788fc681a8c5758bca6d0f1df0fedd147385df494ce81c5e212d5"
)
FIRST_RESULT = first.RESULT
FIRST_RESULT_SHA256 = (
    "6abbce3cb6271cde5046479b78a8436ba41fbb383679c102d857731d262e600b"
)
FIRST_PRIVATE = first.POPULATION
FIRST_PRIVATE_SHA256 = (
    "ced33e651b0d72a65a59d4106ea5b68316f25bd5b31ca9a54f8f1c9d2689fcec"
)
SECOND_RESULT = second.RESULT
SECOND_RESULT_SHA256 = (
    "f5015143ccc03beb40785eb18d91507223c8dcdd30cb95156793a3d895fd9c65"
)
THIRD_RESULT = third.RESULT
THIRD_RESULT_SHA256 = (
    "431886229c29e72b89c149ca246bd6f9c5f009c69a924d061f45aea081aa0812"
)
FOURTH_RESULT = fourth.RESULT
FOURTH_RESULT_SHA256 = (
    "71db9cf2f6090b324a5bd2179e27268c0829efa5dda1ed5fe52587651bfc1282"
)
FOURTH_AUDIT = fourth_audit.OUTPUT
FOURTH_AUDIT_SHA256 = (
    "8791bfd6744083ef52b032866027d3a63c6a37fcd685aa3d90eb3a5509f95ab2"
)
EXPECTED_TARGET_VECTOR_SHA256 = (
    "49ae552a5b1021e08169fac4ad0e9aaa074ad0590c0884dd52ed0c584278fbbd"
)
EXPECTED_ENTITY_VECTOR_SHA256 = (
    "8674522def1925ab683d9b388f283de184dfd729f8f011113d581383e7958b67"
)
EXPECTED_RESPONSE_VECTOR_SHA256 = (
    "1663c031db8eb081a455ee6a7113c6a67d5ec9169827ac80183a31c1ad439f25"
)

CATALOG_URL = first.CATALOG_URL
CATALOG_MAXIMUM_BYTES = first.CATALOG_MAXIMUM_BYTES
TARGET_MAXIMUM_BYTES = first.TARGET_MAXIMUM_BYTES
CATALOG_SOCKET_TIMEOUT_SECONDS = first.CATALOG_SOCKET_TIMEOUT_SECONDS
TARGET_SOCKET_TIMEOUT_SECONDS = first.TARGET_SOCKET_TIMEOUT_SECONDS
CATALOG_PHASE_HARD_WALL_SECONDS = 30.0
TARGET_PHASE_HARD_WALL_SECONDS = 110.0
WHOLE_FREEZE_HARD_WALL_SECONDS = 145.0
TARGET_CONCURRENCY = 3
REQUEST_START_INTERVAL_SECONDS = 0.0
EXPECTED_WATCHERS = first.EXPECTED_WATCHERS
HISTORICAL_TARGET_KEYS = tuple(
    f"{indicator}@{selector.TARGET_YEAR}"
    for indicator in sorted(first.EXPECTED_HISTORICAL_INDICATORS)
)
RESULT_FAILURE_CODES = fourth.RESULT_FAILURE_CODES


def payload_sha256(value: object) -> str:
    return first.payload_sha256(value)


def sha256(path: Path) -> str:
    return third.sha256(path)


def _ordinary(relative: Path, *, required: bool = True) -> Path:
    return third._ordinary(relative, required=required)


def _git(*args: str) -> str:
    return third._git(*args)


def publish_exclusive(path: Path, data: bytes) -> None:
    third.publish_exclusive(path, data)


def publish_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    third.publish_json_exclusive(path, value)


def invoke_helper(
    url: str, maximum: int, timeout_seconds: float
) -> tuple[bytes | None, dict[str, Any]]:
    return first.invoke_helper(url, maximum, timeout_seconds)


def _authority() -> dict[str, Any]:
    fixed = {
        DIAGNOSIS: DIAGNOSIS_SHA256,
        FIRST_RESULT: FIRST_RESULT_SHA256,
        FIRST_PRIVATE: FIRST_PRIVATE_SHA256,
        SECOND_RESULT: SECOND_RESULT_SHA256,
        THIRD_RESULT: THIRD_RESULT_SHA256,
        FOURTH_RESULT: FOURTH_RESULT_SHA256,
        FOURTH_AUDIT: FOURTH_AUDIT_SHA256,
    }
    if any(sha256(_ordinary(path)) != digest for path, digest in fixed.items()):
        raise RuntimeError("V2.53.37 authority hash drifted")
    diagnosis_value = diagnosis.validate_diagnosis(
        json.loads(_ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    )
    first_result = first.validate_result(
        json.loads(_ordinary(FIRST_RESULT).read_text(encoding="utf-8"))
    )
    first_private = json.loads(_ordinary(FIRST_PRIVATE).read_text(encoding="utf-8"))
    second_result = second.validate_result(
        json.loads(_ordinary(SECOND_RESULT).read_text(encoding="utf-8"))
    )
    third_result = third.validate_result(
        json.loads(_ordinary(THIRD_RESULT).read_text(encoding="utf-8"))
    )
    post = fourth_audit.validate_audit(
        json.loads(_ordinary(FOURTH_AUDIT).read_text(encoding="utf-8"))
    )
    if (
        first_private.get("role") != "v25305_private_frozen_worldbank_population"
        or not first.seal.sealed(first_private, "population_payload_sha256")
        or diagnosis_value["diagnosis_valid"] is not True
        or diagnosis_value["findings"] != []
        or diagnosis_value["authorization"][
            "concurrency3_fresh_disjoint_transport_successor_build"
        ]
        is not True
        or diagnosis_value["authorization"][
            "successor_population_network_activation_or_launch"
        ]
        is not False
        or post["audit_valid"] is not True
        or post["findings"] != []
        or post["authorization"][
            "reuse_successful_partial_responses_for_population_or_successor"
        ]
        is not False
    ):
        raise RuntimeError("V2.53.37 authority semantics drifted")
    fourth_result = fourth.validate_result(
        json.loads(_ordinary(FOURTH_RESULT).read_text(encoding="utf-8"))
    )
    results = (first_result, second_result, third_result, fourth_result)
    targets = [item for result in results for item in result["candidate_target_keys"]]
    entities = list(first_private["population"]["entities"])
    responses = [
        str(row["response_sha256"])
        for result in results
        for row in result["target_transport"]["rows"]
        if row["response_sha256"] is not None
    ]
    if (
        len(targets) != selector.CONSUMED_TARGET_COUNT
        or len(set(item.casefold() for item in targets)) != selector.CONSUMED_TARGET_COUNT
        or len(entities) != selector.CONSUMED_ENTITY_COUNT
        or len(set(entities)) != selector.CONSUMED_ENTITY_COUNT
        or len(responses) != selector.CONSUMED_RESPONSE_COUNT
        or len(set(responses)) != selector.CONSUMED_RESPONSE_COUNT
        or payload_sha256(targets) != EXPECTED_TARGET_VECTOR_SHA256
        or payload_sha256(entities) != EXPECTED_ENTITY_VECTOR_SHA256
        or payload_sha256(responses) != EXPECTED_RESPONSE_VECTOR_SHA256
    ):
        raise RuntimeError("V2.53.37 merged consumed manifest drifted")
    return {
        "diagnosis": {"path": str(DIAGNOSIS), "sha256": DIAGNOSIS_SHA256},
        "consumed_target_keys": targets,
        "consumed_entity_codes": entities,
        "consumed_response_sha256": responses,
        "consumed_target_keys_sha256": EXPECTED_TARGET_VECTOR_SHA256,
        "consumed_entity_codes_sha256": EXPECTED_ENTITY_VECTOR_SHA256,
        "consumed_response_vector_sha256": EXPECTED_RESPONSE_VECTOR_SHA256,
    }


def _request_target_pages(
    targets: Sequence[selector.TargetSpec],
    *,
    get: Callable[[str, int, float], tuple[bytes | None, dict[str, Any]]],
    logical_start: Callable[[int, float], float] | None = None,
) -> tuple[
    dict[selector.TargetSpec, tuple[bytes, bytes]],
    dict[tuple[int, int], bytes],
    list[dict[str, Any]],
    float,
    dict[str, Any],
]:
    if len(targets) != selector.MINIMUM_TARGET_OVERSAMPLE:
        raise ValueError("V2.53.37 target vector drifted")
    work = [
        (ticket, index, target, page, target.urls[page - 1])
        for ticket, (index, target, page) in enumerate(
            (
                (index, target, page)
                for index, target in enumerate(targets, 1)
                for page in (1, 2)
            )
        )
    ]
    started = time.monotonic()
    condition = threading.Condition()
    next_ticket = 0
    next_allowed_start = started
    active = 0
    maximum_active = 0
    starts: dict[int, float] = {}
    bodies: dict[tuple[int, int], bytes] = {}
    rows: dict[tuple[int, int], dict[str, Any]] = {}

    def paced_get(
        ticket: int, url: str
    ) -> tuple[bytes | None, dict[str, Any]]:
        nonlocal next_ticket, next_allowed_start, active, maximum_active
        with condition:
            while ticket != next_ticket:
                condition.wait()
            if logical_start is None:
                while time.monotonic() < next_allowed_start:
                    condition.wait(timeout=next_allowed_start - time.monotonic())
                actual = time.monotonic()
            else:
                actual = logical_start(ticket, started)
                if (
                    isinstance(actual, bool)
                    or not isinstance(actual, (int, float))
                    or not math.isfinite(float(actual))
                    or float(actual) < next_allowed_start
                ):
                    raise ValueError("V2.53.37 logical start schedule drifted")
                actual = float(actual)
            starts[ticket] = actual
            next_allowed_start = actual + REQUEST_START_INTERVAL_SECONDS
            next_ticket += 1
            active += 1
            maximum_active = max(maximum_active, active)
            condition.notify_all()
        try:
            return get(url, TARGET_MAXIMUM_BYTES, TARGET_SOCKET_TIMEOUT_SECONDS)
        finally:
            with condition:
                active -= 1

    with ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY) as executor:
        futures = {
            executor.submit(paced_get, ticket, url): (index, target, page)
            for ticket, index, target, page, url in work
        }
        for future in as_completed(futures):
            index, target, page = futures[future]
            try:
                body, receipt = future.result()
            except BaseException:
                body, receipt = None, {
                    "url_sha256": hashlib.sha256(
                        target.urls[page - 1].encode()
                    ).hexdigest(),
                    "maximum_response_bytes": TARGET_MAXIMUM_BYTES,
                    "provider_attempt_count": 0,
                    "outcome": "failure",
                    "failure_code": "supervisor_error",
                    "http_status": None,
                    "elapsed_seconds": 0.0,
                    "response_bytes": 0,
                    "response_sha256": None,
                    "redirect_retry_refetch_count": 0,
                }
            rows[(index, page)] = {
                "candidate_ordinal": index,
                "target_key": target.key,
                "page": page,
                **copy.deepcopy(receipt),
            }
            if body is not None:
                bodies[(index, page)] = body
    elapsed = time.monotonic() - started
    ordered = [rows[(index, page)] for _ticket, index, _target, page, _url in work]
    offsets = [round(starts[ticket] - started, 6) for ticket in range(len(work))]
    intervals = [starts[index] - starts[index - 1] for index in range(1, len(work))]
    schedule = {
        "configured_minimum_start_interval_seconds": REQUEST_START_INTERVAL_SECONDS,
        "observed_minimum_start_interval_seconds": round(min(intervals), 6),
        "maximum_observed_concurrency": maximum_active,
        "request_start_offsets_seconds": offsets,
        "starts_follow_fixed_work_order": True,
    }
    grouped: dict[selector.TargetSpec, tuple[bytes, bytes]] = {}
    if len(bodies) == len(work):
        for index, target in enumerate(targets, 1):
            grouped[target] = (bodies[(index, 1)], bodies[(index, 2)])
    return grouped, bodies, ordered, elapsed, schedule


def build_attempt_claim(
    *, head: str, execution_start_sha256: str, now: int | None = None
) -> dict[str, Any]:
    if (
        re.fullmatch(r"[0-9a-f]{40}", head) is None
        or re.fullmatch(r"[0-9a-f]{64}", execution_start_sha256) is None
    ):
        raise ValueError("V2.53.37 claim authority drifted")
    authority = _authority()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CLAIM_ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "execution_start": {
            "path": str(EXECUTION_START),
            "sha256": execution_start_sha256,
        },
        "diagnosis": authority["diagnosis"],
        "fixed_result_path": str(RESULT),
        "fixed_output_root": str(OUTPUT_ROOT),
        "target_concurrency": TARGET_CONCURRENCY,
        "request_start_interval_seconds": REQUEST_START_INTERVAL_SECONDS,
        "claim_created_before_catalog_or_target_network_effect": True,
        "claim_is_permanent_even_on_crash_or_no_go": True,
        "single_catalog_and_single_48_response_batch_only": True,
        "consumed_target_entity_response_counts": [96, 144, 169],
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
            "diagnosis",
            "fixed_result_path",
            "fixed_output_root",
            "target_concurrency",
            "request_start_interval_seconds",
            "claim_created_before_catalog_or_target_network_effect",
            "claim_is_permanent_even_on_crash_or_no_go",
            "single_catalog_and_single_48_response_batch_only",
            "consumed_target_entity_response_counts",
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
        or not isinstance(copied.get("execution_start"), Mapping)
        or set(copied["execution_start"]) != {"path", "sha256"}
        or copied["execution_start"].get("path") != str(EXECUTION_START)
        or re.fullmatch(r"[0-9a-f]{64}", str(copied["execution_start"].get("sha256")))
        is None
        or copied.get("diagnosis")
        != {"path": str(DIAGNOSIS), "sha256": DIAGNOSIS_SHA256}
        or copied.get("fixed_result_path") != str(RESULT)
        or copied.get("fixed_output_root") != str(OUTPUT_ROOT)
        or copied.get("target_concurrency") != 3
        or copied.get("request_start_interval_seconds") != 0.0
        or copied.get("claim_created_before_catalog_or_target_network_effect")
        is not True
        or copied.get("claim_is_permanent_even_on_crash_or_no_go") is not True
        or copied.get("single_catalog_and_single_48_response_batch_only") is not True
        or copied.get("consumed_target_entity_response_counts") != [96, 144, 169]
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
        raise ValueError("V2.53.37 attempt claim drifted")
    return copied


def execute_freeze(
    *,
    head: str,
    execution_start_sha256: str,
    attempt_claim_sha256: str,
    get: Callable[[str, int, float], tuple[bytes | None, dict[str, Any]]] = invoke_helper,
    logical_start: Callable[[int, float], float] | None = None,
    persist: bool = True,
    now: int | None = None,
) -> dict[str, Any]:
    if logical_start is not None and persist:
        raise ValueError("V2.53.37 logical clock is synthetic-only")
    started = time.monotonic()
    authority = _authority()
    catalog_started = time.monotonic()
    catalog_body, catalog_receipt = get(
        CATALOG_URL, CATALOG_MAXIMUM_BYTES, CATALOG_SOCKET_TIMEOUT_SECONDS
    )
    catalog_elapsed = time.monotonic() - catalog_started
    candidates: list[selector.TargetSpec] = []
    catalog_stats = {
        "catalog_total": 0,
        "historical_target_count": len(HISTORICAL_TARGET_KEYS),
        "consumed_target_count": selector.CONSUMED_TARGET_COUNT,
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
    target_elapsed = 0.0
    schedule = {
        "configured_minimum_start_interval_seconds": REQUEST_START_INTERVAL_SECONDS,
        "observed_minimum_start_interval_seconds": 0.0,
        "maximum_observed_concurrency": 0,
        "request_start_offsets_seconds": [],
        "starts_follow_fixed_work_order": True,
    }
    candidate_bodies: dict[selector.TargetSpec, tuple[bytes, bytes]] = {}
    response_body_receipt_mismatch_count = 0
    consumed_response_overlap_count = 0
    population_value: dict[str, Any] | None = None
    if failure is None:
        (
            candidate_bodies,
            successful_bodies,
            target_rows,
            target_elapsed,
            schedule,
        ) = _request_target_pages(candidates, get=get, logical_start=logical_start)
        consumed = set(authority["consumed_response_sha256"])
        for row in target_rows:
            key = (int(row["candidate_ordinal"]), int(row["page"]))
            if key not in successful_bodies:
                row["response_path"] = None
                continue
            body = successful_bodies[key]
            digest = hashlib.sha256(body).hexdigest()
            response_body_receipt_mismatch_count += digest != str(
                row.get("response_sha256")
            )
            consumed_response_overlap_count += digest in consumed
            relative = TARGET_RESPONSE_ROOT / f"response_{key[0]:02d}_page_{key[1]}.bin"
            row["response_path"] = str(relative)
            if persist:
                publish_exclusive(ROOT / relative, body)
        if (
            len(target_rows) != 48
            or len(candidate_bodies) != selector.MINIMUM_TARGET_OVERSAMPLE
            or any(row["outcome"] != "success" for row in target_rows)
            or target_elapsed > TARGET_PHASE_HARD_WALL_SECONDS
        ):
            failure = "target_transport_or_hard_wall"
        elif response_body_receipt_mismatch_count:
            failure = "response_body_receipt_mismatch"
        elif consumed_response_overlap_count:
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
            "diagnosis": authority["diagnosis"],
            "candidate_target_keys": candidate_keys,
            "consumed_manifest": {
                "target_count": 96,
                "target_keys_sha256": authority["consumed_target_keys_sha256"],
                "entity_count": 144,
                "entity_codes_sha256": authority["consumed_entity_codes_sha256"],
                "response_count": 169,
                "response_vector_sha256": authority["consumed_response_vector_sha256"],
            },
            "population": population_value,
        }
        envelope["population_payload_sha256"] = payload_sha256(envelope)
        encoded = (
            json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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
        "execution_start": {"path": str(EXECUTION_START), "sha256": execution_start_sha256},
        "attempt_claim": {"path": str(ATTEMPT_CLAIM), "sha256": attempt_claim_sha256},
        "diagnosis": authority["diagnosis"],
        "decision": decision,
        "failure_code": failure,
        "catalog": {
            **catalog_receipt,
            **catalog_stats,
            "phase_elapsed_seconds": round(catalog_elapsed, 6),
            "url": CATALOG_URL,
            "response_path": str(CATALOG_RESPONSE) if catalog_body is not None else None,
            "self_proved_one_page_complete": bool(candidates),
        },
        "consumed_manifest": {
            "target_count": 96,
            "target_keys_sha256": authority["consumed_target_keys_sha256"],
            "entity_count": 144,
            "entity_codes_sha256": authority["consumed_entity_codes_sha256"],
            "response_count": 169,
            "response_vector_sha256": authority["consumed_response_vector_sha256"],
        },
        "candidate_target_keys": candidate_keys,
        "candidate_target_count": len(candidate_keys),
        "target_transport": {
            "fixed_request_count": 48,
            "concurrency": TARGET_CONCURRENCY,
            **schedule,
            "elapsed_seconds": round(target_elapsed, 6),
            "rows": target_rows,
            "successful_response_count": sum(
                row.get("outcome") == "success" for row in target_rows
            ),
            "provider_attempt_count": sum(
                int(row.get("provider_attempt_count") or 0) for row in target_rows
            ),
            "response_body_receipt_mismatch_count": response_body_receipt_mismatch_count,
            "consumed_response_overlap_count": consumed_response_overlap_count,
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
            "rendered_page_count": len(population_value["pages"]) if population_value else 0,
            "selected_target_overlap_count": population_value["disjointness_receipt"]["selected_target_overlap_count"] if population_value else 0,
            "selected_entity_overlap_count": population_value["disjointness_receipt"]["selected_entity_overlap_count"] if population_value else 0,
            "selected_response_overlap_count": population_value["disjointness_receipt"]["selected_response_overlap_count"] if population_value else 0,
        },
        "effect_accounting": {
            "catalog_provider_attempt_count": int(catalog_receipt.get("provider_attempt_count") or 0),
            "target_provider_attempt_count": sum(int(row.get("provider_attempt_count") or 0) for row in target_rows),
            "redirect_retry_refetch_resume_backfill_replacement_count": 0,
            "model_search_evaluator_or_benchmark_effect_count": 0,
            "public_worldbank_network_or_api_called": bool(
                int(catalog_receipt.get("provider_attempt_count") or 0)
                + sum(int(row.get("provider_attempt_count") or 0) for row in target_rows)
            ),
        },
        "whole_elapsed_seconds": round(elapsed, 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "postfreeze_audit": decision == "go",
            "external_monotone_fill_protocol_or_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_population_attempt": False,
        },
    }
    value["freeze_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def _row_valid(row: Mapping[str, Any], candidate_keys: list[str]) -> bool:
    if (
        set(row)
        != {
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
        or not isinstance(row.get("candidate_ordinal"), int)
        or isinstance(row.get("candidate_ordinal"), bool)
        or row.get("page") not in {1, 2}
        or row.get("provider_attempt_count") not in {0, 1}
        or row.get("outcome") not in {"success", "failure"}
        or row.get("maximum_response_bytes") != TARGET_MAXIMUM_BYTES
        or row.get("redirect_retry_refetch_count") != 0
        or (
            row.get("http_status") is not None
            and (
                isinstance(row.get("http_status"), bool)
                or not isinstance(row.get("http_status"), int)
            )
        )
        or not isinstance(row.get("elapsed_seconds"), (int, float))
        or isinstance(row.get("elapsed_seconds"), bool)
        or not math.isfinite(float(row["elapsed_seconds"]))
        or not 0
        <= float(row["elapsed_seconds"])
        <= first.HELPER_HARD_TIMEOUT_SECONDS + 2
    ):
        return False
    index = int(row["candidate_ordinal"])
    if not 0 < index <= len(candidate_keys):
        return False
    key = candidate_keys[index - 1]
    indicator = key.rsplit("@", 1)[0]
    expected_path = (
        TARGET_RESPONSE_ROOT / f"response_{index:02d}_page_{row['page']}.bin"
    )
    success = row["outcome"] == "success"
    return bool(
        row["target_key"] == key
        and row["url_sha256"]
        == hashlib.sha256(
            selector.target_urls(indicator)[int(row["page"]) - 1].encode()
        ).hexdigest()
        and (
            not success
            or (
                row["provider_attempt_count"] == 1
                and row["failure_code"] is None
                and row["http_status"] == 200
                and isinstance(row["response_bytes"], int)
                and not isinstance(row["response_bytes"], bool)
                and row["response_bytes"] > 0
                and row["response_bytes"] <= TARGET_MAXIMUM_BYTES
                and re.fullmatch(r"[0-9a-f]{64}", str(row["response_sha256"]))
                is not None
                and row["response_path"] == str(expected_path)
            )
        )
        and (
            success
            or (
                isinstance(row["failure_code"], str)
                and bool(row["failure_code"])
                and row["response_bytes"] == 0
                and row["response_sha256"] is None
                and row["response_path"] is None
            )
        )
    )


def _catalog_valid(catalog: Mapping[str, Any], candidate_keys: list[str]) -> bool:
    expected_keys = {
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
    if (
        set(catalog) != expected_keys
        or catalog.get("url") != CATALOG_URL
        or catalog.get("url_sha256")
        != hashlib.sha256(CATALOG_URL.encode()).hexdigest()
        or catalog.get("maximum_response_bytes") != CATALOG_MAXIMUM_BYTES
        or catalog.get("provider_attempt_count") not in {0, 1}
        or catalog.get("outcome") not in {"success", "failure"}
        or catalog.get("redirect_retry_refetch_count") != 0
        or (
            catalog.get("http_status") is not None
            and (
                isinstance(catalog.get("http_status"), bool)
                or not isinstance(catalog.get("http_status"), int)
            )
        )
        or not isinstance(catalog.get("elapsed_seconds"), (int, float))
        or isinstance(catalog.get("elapsed_seconds"), bool)
        or not math.isfinite(float(catalog["elapsed_seconds"]))
        or not 0
        <= float(catalog["elapsed_seconds"])
        <= first.HELPER_HARD_TIMEOUT_SECONDS + 2
        or not isinstance(catalog.get("phase_elapsed_seconds"), (int, float))
        or isinstance(catalog.get("phase_elapsed_seconds"), bool)
        or not math.isfinite(float(catalog["phase_elapsed_seconds"]))
        or float(catalog["phase_elapsed_seconds"]) < 0
        or any(
            isinstance(catalog.get(name), bool)
            or not isinstance(catalog.get(name), int)
            or int(catalog[name]) < 0
            for name in (
                "catalog_total",
                "historical_target_count",
                "consumed_target_count",
                "runtime_compatible_fresh_count",
                "selected_candidate_count",
            )
        )
        or catalog.get("historical_target_count") != len(HISTORICAL_TARGET_KEYS)
        or catalog.get("consumed_target_count") != selector.CONSUMED_TARGET_COUNT
        or catalog.get("selected_candidate_count") != len(candidate_keys)
        or not isinstance(catalog.get("self_proved_one_page_complete"), bool)
        or catalog.get("self_proved_one_page_complete")
        is not (len(candidate_keys) == selector.MINIMUM_TARGET_OVERSAMPLE)
    ):
        return False
    success = catalog["outcome"] == "success"
    if success:
        return bool(
            catalog["provider_attempt_count"] == 1
            and catalog["failure_code"] is None
            and catalog["http_status"] == 200
            and isinstance(catalog["response_bytes"], int)
            and not isinstance(catalog["response_bytes"], bool)
            and 0 < catalog["response_bytes"] <= CATALOG_MAXIMUM_BYTES
            and re.fullmatch(r"[0-9a-f]{64}", str(catalog["response_sha256"]))
            is not None
            and catalog["response_path"] == str(CATALOG_RESPONSE)
        )
    return bool(
        isinstance(catalog["failure_code"], str)
        and catalog["failure_code"]
        and catalog["response_bytes"] == 0
        and catalog["response_sha256"] is None
        and catalog["response_path"] is None
    )


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("freeze_payload_sha256", None)
    decision = copied.get("decision")
    go = decision == "go"
    catalog = copied.get("catalog") or {}
    candidate_keys = copied.get("candidate_target_keys")
    target = copied.get("target_transport") or {}
    rows = target.get("rows")
    population = copied.get("population") or {}
    effects = copied.get("effect_accounting") or {}
    authorization = copied.get("authorization") or {}
    authority = _authority()
    execution_start = copied.get("execution_start") or {}
    attempt_claim = copied.get("attempt_claim") or {}
    empty_population = {
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
    offsets = target.get("request_start_offsets_seconds")
    offset_valid = bool(
        isinstance(offsets, list)
        and len(offsets) == (48 if rows else 0)
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(float(item))
            and float(item) >= 0
            for item in offsets
        )
        and all(
            float(offsets[index]) >= float(offsets[index - 1])
            for index in range(1, len(offsets))
        )
    )
    expected_pairs = (
        {
            (index, page)
            for index in range(1, len(candidate_keys or []) + 1)
            for page in (1, 2)
        }
        if isinstance(candidate_keys, list)
        else set()
    )
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "git_head",
            "execution_start", "attempt_claim", "diagnosis", "decision",
            "failure_code", "catalog", "consumed_manifest",
            "candidate_target_keys", "candidate_target_count", "target_transport",
            "population", "effect_accounting", "whole_elapsed_seconds",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "freeze_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_head"))) is None
        or not isinstance(execution_start, Mapping)
        or set(execution_start) != {"path", "sha256"}
        or execution_start.get("path") != str(EXECUTION_START)
        or re.fullmatch(r"[0-9a-f]{64}", str(execution_start.get("sha256"))) is None
        or not isinstance(attempt_claim, Mapping)
        or set(attempt_claim) != {"path", "sha256"}
        or attempt_claim.get("path") != str(ATTEMPT_CLAIM)
        or re.fullmatch(r"[0-9a-f]{64}", str(attempt_claim.get("sha256"))) is None
        or copied.get("diagnosis") != {"path": str(DIAGNOSIS), "sha256": DIAGNOSIS_SHA256}
        or decision not in {"go", "no_go"}
        or (copied.get("failure_code") is None) is not go
        or (not go and copied.get("failure_code") not in RESULT_FAILURE_CODES)
        or not isinstance(catalog, Mapping)
        or not _catalog_valid(catalog, candidate_keys or [])
        or copied.get("consumed_manifest")
        != {
            "target_count": 96,
            "target_keys_sha256": authority["consumed_target_keys_sha256"],
            "entity_count": 144,
            "entity_codes_sha256": authority["consumed_entity_codes_sha256"],
            "response_count": 169,
            "response_vector_sha256": authority["consumed_response_vector_sha256"],
        }
        or not isinstance(candidate_keys, list)
        or len(candidate_keys) != len(set(candidate_keys))
        or copied.get("candidate_target_count") != len(candidate_keys)
        or not isinstance(rows, list)
        or len(rows) not in {0, 48}
        or any(not isinstance(row, Mapping) or not _row_valid(row, candidate_keys) for row in rows)
        or {(row["candidate_ordinal"], row["page"]) for row in rows}
        != (expected_pairs if rows else set())
        or not isinstance(target, Mapping)
        or set(target)
        != {
            "fixed_request_count", "concurrency",
            "configured_minimum_start_interval_seconds",
            "observed_minimum_start_interval_seconds",
            "maximum_observed_concurrency", "request_start_offsets_seconds",
            "starts_follow_fixed_work_order", "elapsed_seconds", "rows",
            "successful_response_count", "provider_attempt_count",
            "response_body_receipt_mismatch_count", "consumed_response_overlap_count",
        }
        or target.get("fixed_request_count") != 48
        or target.get("concurrency") != 3
        or target.get("configured_minimum_start_interval_seconds") != 0.0
        or target.get("starts_follow_fixed_work_order") is not True
        or not offset_valid
        or (
            rows
            and (
                not isinstance(target.get("observed_minimum_start_interval_seconds"), (int, float))
                or float(target["observed_minimum_start_interval_seconds"]) < 0.0
                or not isinstance(target.get("maximum_observed_concurrency"), int)
                or not 1 <= target["maximum_observed_concurrency"] <= 3
            )
        )
        or target.get("successful_response_count") != sum(row["outcome"] == "success" for row in rows)
        or target.get("provider_attempt_count") != sum(int(row["provider_attempt_count"]) for row in rows)
        or not isinstance(target.get("response_body_receipt_mismatch_count"), int)
        or target.get("response_body_receipt_mismatch_count") < 0
        or not isinstance(target.get("consumed_response_overlap_count"), int)
        or target.get("consumed_response_overlap_count") < 0
        or not isinstance(target.get("elapsed_seconds"), (int, float))
        or float(target["elapsed_seconds"]) < 0
        or not isinstance(population, Mapping)
        or set(population) != set(empty_population)
        or effects
        != {
            "catalog_provider_attempt_count": catalog.get("provider_attempt_count"),
            "target_provider_attempt_count": target.get("provider_attempt_count"),
            "redirect_retry_refetch_resume_backfill_replacement_count": 0,
            "model_search_evaluator_or_benchmark_effect_count": 0,
            "public_worldbank_network_or_api_called": bool(
                int(catalog.get("provider_attempt_count") or 0)
                + int(target.get("provider_attempt_count") or 0)
            ),
        }
        or not isinstance(copied.get("whole_elapsed_seconds"), (int, float))
        or float(copied["whole_elapsed_seconds"]) < 0
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "postfreeze_audit": go,
            "external_monotone_fill_protocol_or_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_population_attempt": False,
        }
        or (
            go
            and (
                len(candidate_keys) != 24
                or len(rows) != 48
                or target.get("provider_attempt_count") != 48
                or target.get("successful_response_count") != 48
                or target.get("response_body_receipt_mismatch_count") != 0
                or target.get("consumed_response_overlap_count") != 0
                or population.get("selected_target_count") != 4
                or population.get("entity_count") not in {96, 108}
                or population.get("rows_per_task") not in {8, 9}
                or population.get("entity_count") != population.get("rows_per_task") * 12
                or population.get("task_count") != 12
                or population.get("rendered_page_count") != 8
                or population.get("selected_target_overlap_count") != 0
                or population.get("selected_entity_overlap_count") != 0
                or population.get("selected_response_overlap_count") != 0
                or population.get("private_path") != str(POPULATION)
                or re.fullmatch(r"[0-9a-f]{64}", str(population.get("private_sha256"))) is None
            )
        )
        or (not go and population != empty_population)
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.37 population result drifted")
    return copied


def _source_manifest() -> dict[str, str]:
    paths = (
        SOURCE, TEST, HELPER, SELECTOR, first.SOURCE, second.SOURCE, third.SOURCE,
        fourth.SOURCE, fourth_audit.SOURCE, diagnosis.SOURCE,
        Path("scripts/deepwide_api_lease.py"),
    )
    return {str(path): sha256(_ordinary(path)) for path in paths}


def _protected_watchers_match() -> bool:
    return first._protected_watchers_match()


def _preactivation_authority() -> bool:
    try:
        value = json.loads(_ordinary(PREACTIVATION).read_text(encoding="utf-8"))
        unsigned = dict(value)
        signature = unsigned.pop("audit_payload_sha256", None)
        return bool(
            value.get("role")
            == "v25339_concurrency3_worldbank_population_preactivation_audit"
            and value.get("audit_valid") is True
            and value.get("findings") == []
            and value.get("source_manifest") == _source_manifest()
            and value.get("active_conflicts") == []
            and value.get("shared_api_lease_inactive") is True
            and value.get("future_surfaces_pristine") is True
            and value.get("consumed_manifest_contract")
            == {
                "target_count": 96, "entity_count": 144, "response_count": 169,
                "preferred_entity_count": 108, "minimum_entity_count": 96,
                "task_count": 12, "all_overlap_counts_must_be_zero": True,
            }
            and value.get("transport_contract", {}).get("target_concurrency") == 3
            and value.get("transport_contract", {}).get("request_start_interval_seconds") == 0.0
            and value.get("authorization")
            == {
                "execution_start_generation": True,
                "single_concurrency3_population_freeze": False,
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
            "artifact_version", "role", "created_at_unix", "git_parent",
            "preactivation_audit", "source_manifest", "runtime_state",
            "transport_contract", "consumed_manifest_contract",
            "fixed_attempt_claim_path", "fixed_result_path", "fixed_output_root",
            "single_catalog_then_single_48_target_response_batch",
            "retry_resume_refetch_backfill_replacement_or_second_attempt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "start_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25340_concurrency3_worldbank_population_execution_start"
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or re.fullmatch(r"[0-9a-f]{40}", current_head) is None
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_parent"))) is None
        or copied.get("preactivation_audit")
        != {"path": str(PREACTIVATION), "sha256": sha256(_ordinary(PREACTIVATION))}
        or copied.get("source_manifest") != _source_manifest()
        or copied.get("runtime_state")
        != {"protected_watchers": list(EXPECTED_WATCHERS), "shared_api_lease_inactive": True}
        or copied.get("transport_contract")
        != {
            "catalog_url": CATALOG_URL, "catalog_provider_attempt_count": 1,
            "candidate_target_count": 24, "target_provider_attempt_count": 48,
            "target_concurrency": 3, "request_start_interval_seconds": 0.0,
            "catalog_phase_hard_wall_seconds": 30.0,
            "target_phase_hard_wall_seconds": 110.0,
            "whole_freeze_hard_wall_seconds": 145.0,
        }
        or copied.get("consumed_manifest_contract")
        != {
            "target_count": 96, "entity_count": 144, "response_count": 169,
            "preferred_entity_count": 108, "minimum_entity_count": 96,
            "task_count": 12, "all_overlap_counts_must_be_zero": True,
        }
        or copied.get("fixed_attempt_claim_path") != str(ATTEMPT_CLAIM)
        or copied.get("fixed_result_path") != str(RESULT)
        or copied.get("fixed_output_root") != str(OUTPUT_ROOT)
        or copied.get("single_catalog_then_single_48_target_response_batch") is not True
        or copied.get("retry_resume_refetch_backfill_replacement_or_second_attempt") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("authorization")
        != {
            "single_concurrency3_population_freeze": True,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
        }
        or not _preactivation_authority()
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.40 execution start drifted")
    return copied


def main() -> None:
    head = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain") or head != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.53.37 requires clean pushed HEAD")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (ATTEMPT_CLAIM, RESULT, OUTPUT_ROOT, POSTFREEZE_AUDIT)
    ):
        raise FileExistsError("V2.53.37 future surface is not pristine")
    start_path = _ordinary(EXECUTION_START)
    start = _validate_execution_start(
        json.loads(start_path.read_text(encoding="utf-8")), current_head=head
    )
    if (
        _git("rev-parse", f"{head}^") != start["git_parent"]
        or sorted(
            line
            for line in _git("diff-tree", "--no-commit-id", "--name-only", "-r", head).splitlines()
            if line
        )
        != [str(EXECUTION_START)]
    ):
        raise RuntimeError("V2.53.40 execution-start commit boundary drifted")
    if not _protected_watchers_match():
        raise RuntimeError("V2.53.37 protected watcher identity drifted")
    start_sha = sha256(start_path)
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25337_concurrency3_worldbank_population_freeze",
        purpose="single_concurrency3_four_attempt_disjoint_worldbank_population_freeze",
    ):
        claim = build_attempt_claim(head=head, execution_start_sha256=start_sha)
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
                "result": str(RESULT), "decision": result["decision"],
                "failure_code": result["failure_code"],
                "catalog_attempts": result["effect_accounting"]["catalog_provider_attempt_count"],
                "target_attempts": result["effect_accounting"]["target_provider_attempt_count"],
                "successful_target_responses": result["target_transport"]["successful_response_count"],
                "minimum_start_interval_seconds": result["target_transport"]["observed_minimum_start_interval_seconds"],
                "maximum_observed_concurrency": result["target_transport"]["maximum_observed_concurrency"],
                "selected_targets": result["population"]["selected_target_count"],
                "entities": result["population"]["entity_count"],
                "tasks": result["population"]["task_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
