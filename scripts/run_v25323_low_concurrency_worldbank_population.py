#!/usr/bin/env python3
"""One-shot low-concurrency World Bank population supervisor.

This successor is disjoint from both V2.53.05 and V2.53.17.  It consumes 48
unique probed target keys, 144 entity codes, and 84 successfully frozen target
response hashes.  It changes only target transport scheduling from 12 to 6
workers; every URL still receives exactly one provider attempt, with no retry,
resume, refetch, backfill, or replacement.  Importing this module has no effect.
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25322_twice_disjoint_worldbank_population as selector  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts import audit_v25320_disjoint_worldbank_population_nogo as prior_audit  # noqa: E402
from scripts import diagnose_v25321_v25317_transport_capacity as diagnosis  # noqa: E402
from scripts import run_v25297_worldbank_population_freeze as first  # noqa: E402
from scripts import run_v25317_disjoint_worldbank_population as second  # noqa: E402


DATE = "20260813"
ROLE = "v25323_low_concurrency_worldbank_population_freeze"
CLAIM_ROLE = "v25323_low_concurrency_worldbank_population_attempt_claim"
PRIVATE_ROLE = "v25323_private_twice_disjoint_worldbank_population"
OUTPUT_ROOT = Path(f"outputs/v25323_low_concurrency_worldbank_population_v1_{DATE}")
CATALOG_RESPONSE = OUTPUT_ROOT / "catalog_response.bin"
TARGET_RESPONSE_ROOT = OUTPUT_ROOT / "target_responses"
POPULATION = OUTPUT_ROOT / "population.json"
ATTEMPT_CLAIM = Path(
    f"results/v25323_low_concurrency_worldbank_population_attempt_claim_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v25323_low_concurrency_worldbank_population_freeze_v1_{DATE}.json"
)
BUILD_AUDIT = Path(
    f"results/v25324_low_concurrency_worldbank_population_build_audit_v1_{DATE}.json"
)
PREACTIVATION = Path(
    f"results/v25325_low_concurrency_worldbank_population_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25326_low_concurrency_worldbank_population_execution_start_v1_{DATE}.json"
)
POSTFREEZE_AUDIT = Path(
    f"results/v25327_low_concurrency_worldbank_population_postfreeze_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/run_v25323_low_concurrency_worldbank_population.py")
TEST = Path("tests/test_run_v25323_low_concurrency_worldbank_population.py")
HELPER = first.HELPER
SELECTOR = Path("src/deepwide_agent/v25322_twice_disjoint_worldbank_population.py")
FIRST_RUNNER = first.SOURCE
SECOND_RUNNER = second.SOURCE
PRIOR_AUDIT_SOURCE = prior_audit.SOURCE
DIAGNOSIS_SOURCE = diagnosis.SOURCE
LEASE_SOURCE = Path("scripts/deepwide_api_lease.py")
DIAGNOSIS = diagnosis.OUTPUT
DIAGNOSIS_SHA256 = (
    "064bec116fb9112a7b8bf68590146d59d68c21c434ed041e94368322bfee2f5f"
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
SECOND_AUDIT = prior_audit.OUTPUT
SECOND_AUDIT_SHA256 = (
    "ac9614e2948263382621f8d25404d491b31cec96874827045b2df9d7e7dff2e1"
)
EXPECTED_TARGET_VECTOR_SHA256 = (
    "75f892dab20cee8e2cd47ba57c5c9644fe62f82373b4048b73f09d78dbbffb89"
)
EXPECTED_ENTITY_VECTOR_SHA256 = (
    "8674522def1925ab683d9b388f283de184dfd729f8f011113d581383e7958b67"
)
EXPECTED_RESPONSE_VECTOR_SHA256 = (
    "9037c2b1522ca8a6f11e4d447f6cbc75b5dcabb6d17a3c79bee6699a7e221c07"
)

RESULT_FAILURE_CODES = frozenset(
    {
        "catalog_transport",
        "catalog_body_receipt_mismatch",
        "catalog_hard_wall",
        "catalog_validation_or_capacity",
        "target_transport_or_hard_wall",
        "response_body_receipt_mismatch",
        "consumed_response_overlap",
        "population_disjoint_capacity_or_rendering",
        "whole_freeze_hard_wall",
    }
)
PREACTIVATION_CHECK_NAMES = frozenset(
    {
        "fixed_sources_build_audit_and_implementation_commit_exact",
        "focused_parent_and_transport_tests_exact_green",
        "runtime_dependency_closure_hash_bound",
        "all_explicit_and_closure_files_tracked",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "build_audit_authorizes_preactivation_only",
        "source_manifest_binds_all_direct_runtime_sources",
        "claim_precedes_catalog_or_target_effect",
        "shared_lease_wraps_claim_network_and_result",
        "single_catalog_and_exact48_target_batch_all_or_nothing",
        "target_concurrency_exact6_and_only_transport_policy_change",
        "body_receipt_and_consumed_response_hashes_both_checked",
        "consumed_48_target_144_entity_84_response_contract_exact",
        "twelve_task_108_then96_disjoint_capacity_contract_exact",
        "helper_exact_url_allowlist_zero_redirect_retry_and_trust_env",
        "failure_no_go_without_retry_resume_backfill_or_replacement",
        "future_start_claim_result_output_and_postaudit_pristine",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "active_population_forward_or_evaluator_conflicts_zero",
        "git_clean_head_equals_target_main",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_information_gain_shadow_and_positive_credit_zero",
    }
)

CATALOG_URL = first.CATALOG_URL
CATALOG_MAXIMUM_BYTES = first.CATALOG_MAXIMUM_BYTES
TARGET_MAXIMUM_BYTES = first.TARGET_MAXIMUM_BYTES
CATALOG_SOCKET_TIMEOUT_SECONDS = first.CATALOG_SOCKET_TIMEOUT_SECONDS
TARGET_SOCKET_TIMEOUT_SECONDS = first.TARGET_SOCKET_TIMEOUT_SECONDS
CATALOG_PHASE_HARD_WALL_SECONDS = 30.0
TARGET_PHASE_HARD_WALL_SECONDS = 110.0
WHOLE_FREEZE_HARD_WALL_SECONDS = 145.0
TARGET_CONCURRENCY = 6
EXPECTED_WATCHERS = first.EXPECTED_WATCHERS
HISTORICAL_TARGET_KEYS = tuple(
    f"{indicator}@{selector.TARGET_YEAR}"
    for indicator in sorted(first.EXPECTED_HISTORICAL_INDICATORS)
)


def payload_sha256(value: object) -> str:
    return first.payload_sha256(value)


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
        raise ValueError("V2.53.23 path drifted")
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


def _payload_vector_sha256(value: object) -> str:
    return payload_sha256(value)


def _authority() -> dict[str, Any]:
    fixed = {
        DIAGNOSIS: DIAGNOSIS_SHA256,
        FIRST_RESULT: FIRST_RESULT_SHA256,
        FIRST_PRIVATE: FIRST_PRIVATE_SHA256,
        SECOND_RESULT: SECOND_RESULT_SHA256,
        SECOND_AUDIT: SECOND_AUDIT_SHA256,
    }
    if any(sha256(_ordinary(path)) != digest for path, digest in fixed.items()):
        raise RuntimeError("V2.53.23 authority hash drifted")
    diagnosis_value = diagnosis.validate_diagnosis(
        json.loads(_ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    )
    first_result = first.validate_result(
        json.loads(_ordinary(FIRST_RESULT).read_text(encoding="utf-8"))
    )
    first_private = json.loads(
        _ordinary(FIRST_PRIVATE).read_text(encoding="utf-8")
    )
    second_result = second.validate_result(
        json.loads(_ordinary(SECOND_RESULT).read_text(encoding="utf-8"))
    )
    second_audit = prior_audit.validate_audit(
        json.loads(_ordinary(SECOND_AUDIT).read_text(encoding="utf-8"))
    )
    if (
        first_private.get("role")
        != "v25305_private_frozen_worldbank_population"
        or not first.seal.sealed(first_private, "population_payload_sha256")
        or diagnosis_value["diagnosis_valid"] is not True
        or diagnosis_value["findings"] != []
        or diagnosis_value["authorization"][
            "low_concurrency_fresh_disjoint_transport_successor_build"
        ]
        is not True
        or diagnosis_value["authorization"][
            "successor_population_network_activation_or_launch"
        ]
        is not False
        or diagnosis_value["diagnosis"]["next_candidate_target_concurrency"]
        != TARGET_CONCURRENCY
        or second_audit["audit_valid"] is not True
        or second_audit["findings"] != []
        or second_audit["authorization"][
            "reuse_successful_partial_responses_for_population_or_successor"
        ]
        is not False
    ):
        raise RuntimeError("V2.53.23 authority semantics drifted")
    targets = list(first_result["candidate_target_keys"]) + list(
        second_result["candidate_target_keys"]
    )
    entities = list(first_private["population"]["entities"])
    responses = [
        str(row["response_sha256"])
        for row in first_result["target_transport"]["rows"]
        if row["response_sha256"] is not None
    ] + [
        str(row["response_sha256"])
        for row in second_result["target_transport"]["rows"]
        if row["response_sha256"] is not None
    ]
    if (
        len(targets) != selector.CONSUMED_TARGET_COUNT
        or len(set(item.casefold() for item in targets))
        != selector.CONSUMED_TARGET_COUNT
        or len(entities) != selector.CONSUMED_ENTITY_COUNT
        or len(set(entities)) != selector.CONSUMED_ENTITY_COUNT
        or len(responses) != selector.CONSUMED_RESPONSE_COUNT
        or len(set(responses)) != selector.CONSUMED_RESPONSE_COUNT
        or _payload_vector_sha256(targets) != EXPECTED_TARGET_VECTOR_SHA256
        or _payload_vector_sha256(entities) != EXPECTED_ENTITY_VECTOR_SHA256
        or _payload_vector_sha256(responses) != EXPECTED_RESPONSE_VECTOR_SHA256
    ):
        raise RuntimeError("V2.53.23 merged consumed manifest drifted")
    return {
        "diagnosis": {"path": str(DIAGNOSIS), "sha256": DIAGNOSIS_SHA256},
        "consumed_target_keys": targets,
        "consumed_entity_codes": entities,
        "consumed_response_sha256": responses,
        "consumed_target_keys_sha256": EXPECTED_TARGET_VECTOR_SHA256,
        "consumed_entity_codes_sha256": EXPECTED_ENTITY_VECTOR_SHA256,
        "consumed_response_vector_sha256": EXPECTED_RESPONSE_VECTOR_SHA256,
    }


def invoke_helper(
    url: str, maximum: int, timeout_seconds: float
) -> tuple[bytes | None, dict[str, Any]]:
    return first.invoke_helper(url, maximum, timeout_seconds)


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
    if len(targets) != selector.MINIMUM_TARGET_OVERSAMPLE:
        raise ValueError("V2.53.23 target vector drifted")
    work = [
        (index, target, page, target.urls[page - 1])
        for index, target in enumerate(targets, 1)
        for page in (1, 2)
    ]
    started = time.monotonic()
    bodies: dict[tuple[int, int], bytes] = {}
    rows: dict[tuple[int, int], dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY) as executor:
        futures = {
            executor.submit(
                get,
                url,
                TARGET_MAXIMUM_BYTES,
                TARGET_SOCKET_TIMEOUT_SECONDS,
            ): (index, target, page)
            for index, target, page, url in work
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
    ordered = [rows[(index, page)] for index, _target, page, _url in work]
    grouped: dict[selector.TargetSpec, tuple[bytes, bytes]] = {}
    if len(bodies) == len(work):
        for index, target in enumerate(targets, 1):
            grouped[target] = (bodies[(index, 1)], bodies[(index, 2)])
    return grouped, bodies, ordered, elapsed


def build_attempt_claim(
    *, head: str, execution_start_sha256: str, now: int | None = None
) -> dict[str, Any]:
    if (
        re.fullmatch(r"[0-9a-f]{40}", head) is None
        or re.fullmatch(r"[0-9a-f]{64}", execution_start_sha256) is None
    ):
        raise ValueError("V2.53.23 claim authority drifted")
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
        "claim_created_before_catalog_or_target_network_effect": True,
        "claim_is_permanent_even_on_crash_or_no_go": True,
        "single_catalog_and_single_48_response_batch_only": True,
        "consumed_target_entity_response_counts": [48, 144, 84],
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
        or re.fullmatch(
            r"[0-9a-f]{64}", str(copied["execution_start"].get("sha256"))
        )
        is None
        or copied.get("diagnosis")
        != {"path": str(DIAGNOSIS), "sha256": DIAGNOSIS_SHA256}
        or copied.get("fixed_result_path") != str(RESULT)
        or copied.get("fixed_output_root") != str(OUTPUT_ROOT)
        or copied.get("target_concurrency") != 6
        or copied.get("claim_created_before_catalog_or_target_network_effect")
        is not True
        or copied.get("claim_is_permanent_even_on_crash_or_no_go") is not True
        or copied.get("single_catalog_and_single_48_response_batch_only") is not True
        or copied.get("consumed_target_entity_response_counts") != [48, 144, 84]
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
        raise ValueError("V2.53.23 attempt claim drifted")
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
    candidate_bodies: dict[selector.TargetSpec, tuple[bytes, bytes]] = {}
    response_body_receipt_mismatch_count = 0
    consumed_response_overlap_count = 0
    population_value: dict[str, Any] | None = None
    if failure is None:
        candidate_bodies, successful_bodies, target_rows, target_elapsed = (
            _request_target_pages(candidates, get=get)
        )
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
            relative = (
                TARGET_RESPONSE_ROOT
                / f"response_{key[0]:02d}_page_{key[1]}.bin"
            )
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
                "target_count": 48,
                "target_keys_sha256": authority["consumed_target_keys_sha256"],
                "entity_count": 144,
                "entity_codes_sha256": authority["consumed_entity_codes_sha256"],
                "response_count": 84,
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
        "diagnosis": authority["diagnosis"],
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
        "consumed_manifest": {
            "target_count": 48,
            "target_keys_sha256": authority["consumed_target_keys_sha256"],
            "entity_count": 144,
            "entity_codes_sha256": authority["consumed_entity_codes_sha256"],
            "response_count": 84,
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
        or not 0 <= float(row["elapsed_seconds"]) <= first.HELPER_HARD_TIMEOUT_SECONDS + 2
    ):
        return False
    index = int(row["candidate_ordinal"])
    if not 0 < index <= len(candidate_keys):
        return False
    key = candidate_keys[index - 1]
    indicator = key.rsplit("@", 1)[0]
    expected_path = TARGET_RESPONSE_ROOT / f"response_{index:02d}_page_{row['page']}.bin"
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
            "artifact_version",
            "role",
            "created_at_unix",
            "git_head",
            "execution_start",
            "attempt_claim",
            "diagnosis",
            "decision",
            "failure_code",
            "catalog",
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
        or not isinstance(execution_start, Mapping)
        or set(execution_start) != {"path", "sha256"}
        or execution_start.get("path") != str(EXECUTION_START)
        or re.fullmatch(r"[0-9a-f]{64}", str(execution_start.get("sha256")))
        is None
        or not isinstance(attempt_claim, Mapping)
        or set(attempt_claim) != {"path", "sha256"}
        or attempt_claim.get("path") != str(ATTEMPT_CLAIM)
        or re.fullmatch(r"[0-9a-f]{64}", str(attempt_claim.get("sha256")))
        is None
        or copied.get("diagnosis")
        != {"path": str(DIAGNOSIS), "sha256": DIAGNOSIS_SHA256}
        or decision not in {"go", "no_go"}
        or (copied.get("failure_code") is None) is not go
        or (
            not go
            and (
                not isinstance(copied.get("failure_code"), str)
                or copied.get("failure_code") not in RESULT_FAILURE_CODES
            )
        )
        or not isinstance(catalog, Mapping)
        or not _catalog_valid(catalog, candidate_keys or [])
        or copied.get("consumed_manifest")
        != {
            "target_count": 48,
            "target_keys_sha256": authority["consumed_target_keys_sha256"],
            "entity_count": 144,
            "entity_codes_sha256": authority["consumed_entity_codes_sha256"],
            "response_count": 84,
            "response_vector_sha256": authority["consumed_response_vector_sha256"],
        }
        or not isinstance(candidate_keys, list)
        or len(candidate_keys) != len(set(candidate_keys))
        or any(
            not isinstance(key, str)
            or not key.endswith("@2022")
            or selector.parent.parent.INDICATOR.fullmatch(
                key.rsplit("@", 1)[0]
            )
            is None
            for key in candidate_keys
        )
        or copied.get("candidate_target_count") != len(candidate_keys)
        or not isinstance(rows, list)
        or len(rows) not in {0, 48}
        or any(
            not isinstance(row, Mapping) or not _row_valid(row, candidate_keys)
            for row in rows
        )
        or {(row["candidate_ordinal"], row["page"]) for row in rows}
        != (expected_pairs if rows else set())
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
        or target.get("concurrency") != 6
        or isinstance(target.get("successful_response_count"), bool)
        or not isinstance(target.get("successful_response_count"), int)
        or target.get("successful_response_count")
        != sum(row["outcome"] == "success" for row in rows)
        or isinstance(target.get("provider_attempt_count"), bool)
        or not isinstance(target.get("provider_attempt_count"), int)
        or target.get("provider_attempt_count")
        != sum(int(row["provider_attempt_count"]) for row in rows)
        or not isinstance(target.get("response_body_receipt_mismatch_count"), int)
        or isinstance(target.get("response_body_receipt_mismatch_count"), bool)
        or target.get("response_body_receipt_mismatch_count") < 0
        or not isinstance(target.get("consumed_response_overlap_count"), int)
        or isinstance(target.get("consumed_response_overlap_count"), bool)
        or target.get("consumed_response_overlap_count") < 0
        or not isinstance(target.get("elapsed_seconds"), (int, float))
        or isinstance(target.get("elapsed_seconds"), bool)
        or not math.isfinite(float(target["elapsed_seconds"]))
        or float(target["elapsed_seconds"]) < 0
        or not isinstance(population, Mapping)
        or set(population) != set(empty_population)
        or not isinstance(effects, Mapping)
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
                or population.get("entity_count")
                != population.get("rows_per_task") * 12
                or population.get("task_count") != 12
                or population.get("rendered_page_count") != 8
                or population.get("selected_target_overlap_count") != 0
                or population.get("selected_entity_overlap_count") != 0
                or population.get("selected_response_overlap_count") != 0
                or population.get("private_path") != str(POPULATION)
                or re.fullmatch(
                    r"[0-9a-f]{64}", str(population.get("private_sha256"))
                )
                is None
                or re.fullmatch(
                    r"[0-9a-f]{64}", str(population.get("entities_sha256"))
                )
                is None
                or re.fullmatch(
                    r"[0-9a-f]{64}", str(population.get("task_vector_sha256"))
                )
                is None
                or not isinstance(population.get("selected_target_keys"), list)
                or population.get("selected_target_count")
                != len(population.get("selected_target_keys"))
                or not {
                    str(item).casefold()
                    for item in population.get("selected_target_keys", [])
                }.issubset({str(item).casefold() for item in candidate_keys})
            )
        )
        or (not go and population != empty_population)
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.23 population result drifted")
    return copied


def _source_manifest() -> dict[str, str]:
    return {
        str(path): sha256(_ordinary(path))
        for path in (
            SOURCE,
            TEST,
            HELPER,
            SELECTOR,
            FIRST_RUNNER,
            SECOND_RUNNER,
            PRIOR_AUDIT_SOURCE,
            DIAGNOSIS_SOURCE,
            LEASE_SOURCE,
        )
    }


def _consumed_manifest_contract() -> dict[str, Any]:
    return {
        "target_count": 48,
        "entity_count": 144,
        "response_count": 84,
        "preferred_entity_count": 108,
        "minimum_entity_count": 96,
        "task_count": 12,
        "all_overlap_counts_must_be_zero": True,
    }


def _protected_watcher_artifact_exact(value: object) -> bool:
    expected = {
        str(row["pid"]): int(row["start_ticks"]) for row in EXPECTED_WATCHERS
    }
    return bool(
        isinstance(value, Mapping)
        and set(value) == set(expected)
        and all(
            isinstance(value.get(pid), Mapping)
            and value[pid].get("present") is True
            and value[pid].get("start_ticks") == ticks
            and value[pid].get("matches_frozen_identity") is True
            and set(value[pid])
            == {"present", "start_ticks", "matches_frozen_identity"}
            for pid, ticks in expected.items()
        )
    )


def _protected_watchers_match() -> bool:
    return first._protected_watchers_match()


def _preactivation_authority() -> bool:
    try:
        value = json.loads(_ordinary(PREACTIVATION).read_text(encoding="utf-8"))
        unsigned = dict(value)
        signature = unsigned.pop("audit_payload_sha256", None)
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
                "build_audit",
                "source_manifest",
                "tests",
                "runtime_dependency_vector",
                "runtime_dependency_vector_sha256",
                "runtime_dependency_path_sha256",
                "semantic_audit",
                "runtime_invariants",
                "consumed_manifest_contract",
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
            and value.get("artifact_version") == 1
            and value.get("role")
            == "v25325_low_concurrency_worldbank_population_preactivation_audit"
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
            and set(checks) == PREACTIVATION_CHECK_NAMES
            and all(item is True for item in checks.values())
            and value.get("build_audit")
            == {
                "path": str(BUILD_AUDIT),
                "sha256": sha256(_ordinary(BUILD_AUDIT)),
            }
            and value.get("source_manifest") == _source_manifest()
            and semantic.get("privileged_runtime_field_accesses") == []
            and semantic.get("evaluator_capabilities") == []
            and semantic.get("credential_literal_hits") == []
            and semantic.get("auditor_or_explicit_file_credential_literal_hits")
            == []
            and semantic.get("untracked_sources") == []
            and value.get("consumed_manifest_contract")
            == _consumed_manifest_contract()
            and _protected_watcher_artifact_exact(
                value.get("protected_watchers")
            )
            and value.get("active_conflicts") == []
            and value.get("shared_api_lease_inactive") is True
            and value.get("future_surfaces_pristine") is True
            and value.get(
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
            )
            is False
            and value.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
            is False
            and value.get("entropy_or_information_gain_assigns_signed_credit")
            is False
            and value.get("authorization")
            == {
                "execution_start_generation": True,
                "single_low_concurrency_population_freeze": False,
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
            "consumed_manifest_contract",
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
        != "v25326_low_concurrency_worldbank_population_execution_start"
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
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
            "target_concurrency": 6,
            "catalog_phase_hard_wall_seconds": 30.0,
            "target_phase_hard_wall_seconds": 110.0,
            "whole_freeze_hard_wall_seconds": 145.0,
        }
        or copied.get("consumed_manifest_contract")
        != _consumed_manifest_contract()
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
            "single_low_concurrency_population_freeze": True,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
        }
        or not _preactivation_authority()
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.26 execution start drifted")
    return copied


def main() -> None:
    head = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain") or head != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.53.23 requires clean pushed HEAD")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (ATTEMPT_CLAIM, RESULT, OUTPUT_ROOT, POSTFREEZE_AUDIT)
    ):
        raise FileExistsError("V2.53.23 future surface is not pristine")
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
        raise RuntimeError("V2.53.26 execution-start commit boundary drifted")
    if not _protected_watchers_match():
        raise RuntimeError("V2.53.23 protected watcher identity drifted")
    start_sha = sha256(start_path)
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25323_low_concurrency_worldbank_population_freeze",
        purpose="single_low_concurrency_twice_disjoint_worldbank_population_freeze",
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
                "selected_targets": result["population"]["selected_target_count"],
                "entities": result["population"]["entity_count"],
                "tasks": result["population"]["task_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
