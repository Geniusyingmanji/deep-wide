"""Create-exclusive keyless coverage bundle with exact effect accounting.

The bundle separates admitted logical queries, executed logical queries, HTTP
responses, provider attempts, actual public-page fetches, usable pages, and
hard helper effects.  A ten-fetch budget is a cap: low source availability is
valid and is represented by the actual lower fetch count.  A completed parent
prediction therefore remains publishable even when search returns no response
or fewer than ten leads.

The module receives only already-produced artifacts and content-free provider
counters.  It has no benchmark, evaluator, environment, credential, process,
model, search, fetch, or network capability.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .v24263_global_model_limiter import payload_sha256
from .v24861_coverage_revision_exact_task import (
    IntegratedCoverageRevisionTaskOutcome,
    build_envelope,
    validate_envelope,
)


POLICY_ID = "v24874_keyless_coverage_effect_bundle_v1"
EFFECT_ROLE = "v24874_keyless_coverage_effect_receipt"
BUNDLE_ROLE = "v24874_keyless_coverage_bundle_receipt"
RESULT_NAME = "result.json"
FINAL_MODEL_NAME = "model_slot_receipt.json"
PARENT_MODEL_NAME = "parent_model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
SINGLE_NAME = "search_single_shot_receipt.json"
BACKFILL_NAME = "citation_title_backfill_receipt.json"
COVERAGE_NAME = "coverage_revision_receipt.json"
EFFECT_NAME = "keyless_effect_receipt.json"
BUNDLE_NAME = "keyless_coverage_bundle_receipt.json"
DATA_NAMES = (
    RESULT_NAME,
    FINAL_MODEL_NAME,
    PARENT_MODEL_NAME,
    TRANSPORT_NAME,
    SINGLE_NAME,
    BACKFILL_NAME,
    COVERAGE_NAME,
    EFFECT_NAME,
)
ALL_NAMES = (*DATA_NAMES, BUNDLE_NAME)
STATUS_BUCKETS = (
    "status_2xx",
    "status_3xx",
    "status_408",
    "status_409",
    "status_429",
    "status_4xx_other",
    "status_5xx",
    "status_other",
)


def _integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.48.74 {label} is not a nonnegative integer")
    return value


def _ordinary_directory(directory: Path, output_root: Path) -> Path:
    root = output_root.resolve()
    target = directory.resolve()
    if (
        output_root.is_symlink()
        or not output_root.is_dir()
        or directory.is_symlink()
        or not directory.is_dir()
        or not target.is_relative_to(root)
    ):
        raise ValueError("V2.48.74 task directory escaped output root")
    return target


def _ordinary_file(path: Path, directory: Path) -> Path:
    target = path.resolve(strict=False)
    if (
        path.name not in ALL_NAMES
        or path.parent != directory
        or path.is_symlink()
        or not path.is_file()
        or not target.is_relative_to(directory)
    ):
        raise ValueError("V2.48.74 expected an ordinary bundle artifact")
    return target


def _read(path: Path, directory: Path) -> dict[str, Any]:
    value = json.loads(
        _ordinary_file(path, directory).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise ValueError("V2.48.74 expected an object artifact")
    return value


def _sha256(path: Path, directory: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary_file(path, directory).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _status_buckets(status_counts: Mapping[object, object]) -> dict[str, int]:
    output = {name: 0 for name in STATUS_BUCKETS}
    for raw_status, raw_count in status_counts.items():
        if isinstance(raw_status, bool):
            raise ValueError("V2.48.74 HTTP status is invalid")
        try:
            status = int(raw_status)
        except (TypeError, ValueError):
            raise ValueError("V2.48.74 HTTP status is invalid") from None
        count = _integer(raw_count, label="HTTP status count")
        if 200 <= status < 300:
            bucket = "status_2xx"
        elif 300 <= status < 400:
            bucket = "status_3xx"
        elif status == 408:
            bucket = "status_408"
        elif status == 409:
            bucket = "status_409"
        elif status == 429:
            bucket = "status_429"
        elif 400 <= status < 500:
            bucket = "status_4xx_other"
        elif 500 <= status < 600:
            bucket = "status_5xx"
        else:
            bucket = "status_other"
        output[bucket] += count
    return output


def _effect_projection(envelope: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_envelope(envelope)
    parent = checked["result"]["parent_result"]
    retrieval = parent.get("two_wave_retrieval")
    if not isinstance(retrieval, Mapping):
        raise ValueError("V2.48.74 parent retrieval receipt is absent")
    status = str(retrieval.get("status"))
    if status not in {"completed", "failed"}:
        raise ValueError("V2.48.74 parent retrieval status drifted")
    budget = parent.get("budget")
    cost = parent.get("cost")
    search_cost = cost.get("search") if isinstance(cost, Mapping) else None
    evidence = parent.get("evidence")
    if (
        not isinstance(budget, Mapping)
        or not isinstance(search_cost, Mapping)
        or not isinstance(evidence, Mapping)
    ):
        raise ValueError("V2.48.74 parent effect accounting is absent")
    admitted_queries = _integer(
        budget.get("admitted_search_queries"), label="admitted queries"
    )
    parent_fetch_targets = _integer(
        budget.get("admitted_fetch_targets"), label="parent fetch targets"
    )
    evidence_pages = _integer(
        evidence.get("fetch_target_count"), label="parent evidence pages"
    )
    if status == "completed":
        nested = retrieval.get("receipt")
        if not isinstance(nested, Mapping):
            raise ValueError("V2.48.74 completed retrieval receipt is absent")
        total = nested.get("total")
        discovery = nested.get("discovery_union")
        if not isinstance(total, Mapping) or not isinstance(discovery, Mapping):
            raise ValueError("V2.48.74 nested retrieval accounting is absent")
        executed = _integer(
            total.get("queries_executed"), label="executed queries"
        )
        fetches = _integer(
            total.get("fetches_attempted"), label="actual fetches"
        )
        usable = _integer(total.get("usable_pages"), label="usable pages")
        unrecoverable = _integer(
            total.get("unrecoverable_search_failures"),
            label="unrecoverable search failures",
        )
        if (
            discovery.get("logical_query_count") != executed
            or discovery.get("fetch_requested_source_count") != fetches
            or discovery.get("fetch_usable_page_count") != usable
        ):
            raise ValueError("V2.48.74 discovery accounting drifted")
        observed = True
    else:
        executed = 0
        fetches = _integer(
            retrieval.get("observed_inner_fetch_calls"),
            label="failed retrieval fetches",
        )
        usable = 0
        unrecoverable = 0
        observed = False
    return {
        "retrieval_status": status,
        "admitted_logical_queries": admitted_queries,
        "executed_logical_queries": executed,
        "executed_logical_queries_observed": observed,
        "actual_fetches": fetches,
        "usable_pages": usable,
        "usable_pages_observed": observed,
        "unrecoverable_search_failures": unrecoverable,
        "parent_response_calls": _integer(
            search_cost.get("calls"), label="parent response calls"
        ),
        "parent_failed_query_rows": _integer(
            search_cost.get("failures"), label="parent failed query rows"
        ),
        "parent_fetch_calls": _integer(
            search_cost.get("fetch_calls"), label="parent fetch calls"
        ),
        "parent_fetch_failures": _integer(
            search_cost.get("fetch_failures"), label="parent fetch failures"
        ),
        "parent_admitted_fetch_targets": parent_fetch_targets,
        "parent_evidence_pages": evidence_pages,
        "transport_health": checked["transport_health"],
    }


def build_effect_receipt(
    envelope: Mapping[str, Any],
    *,
    status_counts: Mapping[object, object],
    transport_failures: int,
    hard_total_wall_timeouts: int,
) -> dict[str, Any]:
    projected = _effect_projection(envelope)
    transport = projected.pop("transport_health")
    buckets = _status_buckets(status_counts)
    value = {
        "artifact_version": 1,
        "role": EFFECT_ROLE,
        "policy_id": POLICY_ID,
        **projected,
        "provider_attempts": int(transport["hosted_search_attempts"]),
        "transport_failures": _integer(
            transport_failures, label="transport failures"
        ),
        "hard_total_wall_timeouts": _integer(
            hard_total_wall_timeouts, label="hard total-wall timeouts"
        ),
        **buckets,
        "hard_fetch_helper_calls": int(transport["hard_fetch_helper_calls"]),
        "hard_fetch_deadline_failures": int(
            transport["hard_fetch_deadline_failures"]
        ),
        "fetch_deadline_rejections": int(
            transport["fetch_deadline_rejections"]
        ),
        "fetch_helper_failures": int(transport["fetch_helper_failures"]),
        "query_cap": 4,
        "fetch_cap": 10,
        "logical_queries_equal_http_responses_required": False,
        "fetch_cap_equal_actual_fetches_required": False,
        "entropy_or_information_gain_used_for_admission": False,
        "question_query_url_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_effect_receipt(value, envelope=envelope)


def validate_effect_receipt(
    value: Mapping[str, Any], *, envelope: Mapping[str, Any]
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    projected = _effect_projection(envelope)
    transport = projected.pop("transport_health")
    integer_fields = {
        "artifact_version",
        "admitted_logical_queries",
        "executed_logical_queries",
        "actual_fetches",
        "usable_pages",
        "unrecoverable_search_failures",
        "parent_response_calls",
        "parent_failed_query_rows",
        "parent_fetch_calls",
        "parent_fetch_failures",
        "parent_admitted_fetch_targets",
        "parent_evidence_pages",
        "provider_attempts",
        "transport_failures",
        "hard_total_wall_timeouts",
        *STATUS_BUCKETS,
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_deadline_rejections",
        "fetch_helper_failures",
        "query_cap",
        "fetch_cap",
    }
    boolean_fields = {
        "executed_logical_queries_observed",
        "usable_pages_observed",
        "logical_queries_equal_http_responses_required",
        "fetch_cap_equal_actual_fetches_required",
        "entropy_or_information_gain_used_for_admission",
        "question_query_url_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
    expected = {
        "role",
        "policy_id",
        "retrieval_status",
        "receipt_payload_sha256",
        *integer_fields,
        *boolean_fields,
    }
    response_sum = sum(int(copied.get(name, 0)) for name in STATUS_BUCKETS)
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != EFFECT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("retrieval_status") not in {"completed", "failed"}
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or any(copied.get(name) != amount for name, amount in projected.items())
        or copied.get("provider_attempts")
        != int(transport["hosted_search_attempts"])
        or copied.get("hard_fetch_helper_calls")
        != int(transport["hard_fetch_helper_calls"])
        or copied.get("hard_fetch_deadline_failures")
        != int(transport["hard_fetch_deadline_failures"])
        or copied.get("fetch_deadline_rejections")
        != int(transport["fetch_deadline_rejections"])
        or copied.get("fetch_helper_failures")
        != int(transport["fetch_helper_failures"])
        or response_sum != copied.get("parent_response_calls")
        or copied.get("provider_attempts")
        != copied.get("parent_response_calls")
        + copied.get("transport_failures")
        + copied.get("hard_total_wall_timeouts")
        or copied.get("parent_fetch_calls") != copied.get("actual_fetches")
        or copied.get("hard_fetch_helper_calls")
        + copied.get("fetch_deadline_rejections")
        != copied.get("actual_fetches")
        or copied.get("hard_fetch_deadline_failures")
        + copied.get("fetch_helper_failures")
        > copied.get("parent_fetch_failures")
        or copied.get("admitted_logical_queries") > copied.get("query_cap")
        or copied.get("executed_logical_queries")
        > copied.get("admitted_logical_queries")
        or copied.get("actual_fetches") > copied.get("fetch_cap")
        or copied.get("usable_pages") > copied.get("actual_fetches")
        or copied.get("parent_failed_query_rows")
        > copied.get("admitted_logical_queries")
        or copied.get("unrecoverable_search_failures")
        > copied.get("executed_logical_queries")
        or copied.get("retrieval_status") == "completed"
        and copied.get("parent_failed_query_rows")
        != copied.get("unrecoverable_search_failures")
        or copied.get("usable_pages", 0) > 0
        and copied.get("status_2xx", 0) <= 0
        or copied.get("query_cap") != 4
        or copied.get("fetch_cap") != 10
        or copied.get("logical_queries_equal_http_responses_required") is not False
        or copied.get("fetch_cap_equal_actual_fetches_required") is not False
        or copied.get("entropy_or_information_gain_used_for_admission") is not False
        or copied.get(
            "question_query_url_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.74 keyless effect receipt drifted")
    if copied["retrieval_status"] == "completed":
        if (
            copied["executed_logical_queries_observed"] is not True
            or copied["usable_pages_observed"] is not True
            or copied["parent_admitted_fetch_targets"] != copied["usable_pages"]
            or copied["parent_evidence_pages"] != copied["usable_pages"]
            or copied["parent_fetch_failures"]
            != copied["actual_fetches"] - copied["usable_pages"]
        ):
            raise ValueError("V2.48.74 completed retrieval binding drifted")
    elif (
        copied["executed_logical_queries_observed"] is not False
        or copied["usable_pages_observed"] is not False
        or copied["executed_logical_queries"] != 0
        or copied["usable_pages"] != 0
        or copied["parent_admitted_fetch_targets"] != 0
        or copied["parent_evidence_pages"] != 0
    ):
        raise ValueError("V2.48.74 failed retrieval binding drifted")
    return copied


def _validate_values(
    values: Mapping[str, Mapping[str, Any]], *, expected_model_slot_cap: int
) -> dict[str, Any]:
    if set(values) != set(DATA_NAMES):
        raise ValueError("V2.48.74 bundle data vector drifted")
    envelope = validate_envelope(values[RESULT_NAME])
    copies = {
        FINAL_MODEL_NAME: "model_slot_receipt",
        PARENT_MODEL_NAME: "parent_model_slot_receipt",
        TRANSPORT_NAME: "transport_health",
        SINGLE_NAME: "search_single_shot_receipt",
        BACKFILL_NAME: "citation_title_backfill_receipt",
        COVERAGE_NAME: "coverage_revision_receipt",
    }
    if any(envelope[field] != values[name] for name, field in copies.items()):
        raise ValueError("V2.48.74 independent artifact copy drifted")
    if (
        envelope["model_slot_receipt"].get("slot_cap")
        != expected_model_slot_cap
        or envelope["parent_model_slot_receipt"].get("slot_cap")
        != expected_model_slot_cap
    ):
        raise ValueError("V2.48.74 model slot cap drifted")
    validate_effect_receipt(values[EFFECT_NAME], envelope=envelope)
    return envelope


def build_bundle_receipt(
    manifest: Mapping[str, str], *, expected_model_slot_cap: int
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": BUNDLE_ROLE,
        "policy_id": POLICY_ID,
        "artifact_count": len(DATA_NAMES),
        "artifact_manifest": dict(manifest),
        "expected_model_slot_cap": int(expected_model_slot_cap),
        "result_envelope_cannot_substitute_for_external_receipt": True,
        "bundle_commit_marker_written_after_all_data_artifacts": True,
        "question_query_url_host_page_prediction_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_or_process_effect_by_bundle_builder": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_bundle_receipt(
        value,
        expected_manifest=manifest,
        expected_model_slot_cap=expected_model_slot_cap,
    )


def validate_bundle_receipt(
    value: Mapping[str, Any],
    *,
    expected_manifest: Mapping[str, str],
    expected_model_slot_cap: int,
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    manifest = copied.get("artifact_manifest")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "artifact_count",
        "artifact_manifest",
        "expected_model_slot_cap",
        "result_envelope_cannot_substitute_for_external_receipt",
        "bundle_commit_marker_written_after_all_data_artifacts",
        "question_query_url_host_page_prediction_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_or_process_effect_by_bundle_builder",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != BUNDLE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("artifact_count") != len(DATA_NAMES)
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dict(expected_manifest)
        or set(manifest) != set(DATA_NAMES)
        or any(
            not isinstance(name, str)
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            for name, digest in manifest.items()
        )
        or copied.get("expected_model_slot_cap") != expected_model_slot_cap
        or copied.get("result_envelope_cannot_substitute_for_external_receipt")
        is not True
        or copied.get("bundle_commit_marker_written_after_all_data_artifacts")
        is not True
        or copied.get(
            "question_query_url_host_page_prediction_candidate_value_evidence_id_or_credential_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("network_model_search_fetch_or_process_effect_by_bundle_builder")
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.74 bundle receipt drifted")
    return copied


def write_bundle(
    *,
    output_root: Path,
    directory: Path,
    outcome: IntegratedCoverageRevisionTaskOutcome,
    status_counts: Mapping[object, object],
    transport_failures: int,
    hard_total_wall_timeouts: int,
    expected_model_slot_cap: int,
    writer: Callable[[Path, Mapping[str, Any]], None] = _atomic_new,
) -> dict[str, Any]:
    task_directory = _ordinary_directory(directory, output_root)
    if any(
        (task_directory / name).exists() or (task_directory / name).is_symlink()
        for name in ALL_NAMES
    ):
        raise FileExistsError("V2.48.74 bundle surface is not pristine")
    envelope = build_envelope(outcome, arm="baseline")
    effect = build_effect_receipt(
        envelope,
        status_counts=status_counts,
        transport_failures=transport_failures,
        hard_total_wall_timeouts=hard_total_wall_timeouts,
    )
    values: dict[str, Mapping[str, Any]] = {
        RESULT_NAME: envelope,
        FINAL_MODEL_NAME: outcome.model_slot_receipt,
        PARENT_MODEL_NAME: outcome.parent_model_slot_receipt,
        TRANSPORT_NAME: outcome.transport_health,
        SINGLE_NAME: outcome.search_single_shot_receipt,
        BACKFILL_NAME: outcome.citation_title_backfill_receipt,
        COVERAGE_NAME: outcome.coverage_revision_receipt,
        EFFECT_NAME: effect,
    }
    _validate_values(values, expected_model_slot_cap=expected_model_slot_cap)
    for name in DATA_NAMES:
        writer(task_directory / name, values[name])
    manifest = {
        name: _sha256(task_directory / name, task_directory) for name in DATA_NAMES
    }
    receipt = build_bundle_receipt(
        manifest, expected_model_slot_cap=expected_model_slot_cap
    )
    writer(task_directory / BUNDLE_NAME, receipt)
    return validate_bundle(
        output_root=output_root,
        directory=task_directory,
        expected_model_slot_cap=expected_model_slot_cap,
    )


def validate_bundle(
    *, output_root: Path, directory: Path, expected_model_slot_cap: int
) -> dict[str, Any]:
    task_directory = _ordinary_directory(directory, output_root)
    values = {
        name: _read(task_directory / name, task_directory) for name in DATA_NAMES
    }
    manifest = {
        name: _sha256(task_directory / name, task_directory) for name in DATA_NAMES
    }
    bundle = _read(task_directory / BUNDLE_NAME, task_directory)
    validate_bundle_receipt(
        bundle,
        expected_manifest=manifest,
        expected_model_slot_cap=expected_model_slot_cap,
    )
    _validate_values(values, expected_model_slot_cap=expected_model_slot_cap)
    return bundle


__all__ = [
    "ALL_NAMES",
    "BACKFILL_NAME",
    "BUNDLE_NAME",
    "COVERAGE_NAME",
    "DATA_NAMES",
    "EFFECT_NAME",
    "FINAL_MODEL_NAME",
    "PARENT_MODEL_NAME",
    "RESULT_NAME",
    "SINGLE_NAME",
    "TRANSPORT_NAME",
    "build_effect_receipt",
    "validate_bundle",
    "validate_effect_receipt",
    "write_bundle",
]
