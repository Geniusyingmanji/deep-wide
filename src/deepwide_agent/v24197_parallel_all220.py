"""Capacity-bound planning for one fresh, label-blind all-220 execution.

This module validates a future candidate bundle against the independently
measured V2.41.96 capacity freeze.  It produces a deterministic wave plan but
never launches a benchmark process, calls an API, or reads evaluator metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from deepwide_agent.v24194_capacity_ladder import (
    CAPACITY_REPORT_CORE_FIELDS,
    CAPACITY_REPORT_EXECUTION_FIELDS,
    build_capacity_freeze,
    validate_capacity_report,
)


EXPECTED_SHARDS = ("test_s01", "test_s02", "test_s03", "devval")
EXPECTED_COUNTS = {
    "test_s01": 52,
    "test_s02": 52,
    "test_s03": 52,
    "devval": 64,
}
CANONICAL_ALL220_SHA256 = (
    "cace8746d5a817a467e7cb70e715ee599a242cc88ce4474802b9d93a9221082b"
)
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
SAFE_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}")
SHA256 = re.compile(r"[0-9a-f]{64}")
CREDENTIAL_LIKE = re.compile(
    r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
CREDENTIAL_METADATA_KEYS = frozenset(
    {"api_key", "api_keys", "credential", "credentials", "secret", "secrets", "token"}
)
FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "answers",
        "api_key",
        "api_keys",
        "category",
        "credential",
        "credentials",
        "evidence",
        "evaluator",
        "gold",
        "ground_truth",
        "mapping",
        "prediction",
        "predictions",
        "question",
        "questions",
        "question_type",
        "score",
        "scores",
        "secret",
        "secrets",
        "split",
        "task_category",
        "token",
        "url",
        "urls",
    }
)
BUNDLE_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "label_blind",
        "target_name",
        "pipeline_version",
        "state_schema_version",
        "candidate_method_contract_sha256",
        "capacity_freeze",
        "candidate_quality_go_receipt",
        "model",
        "shard_order",
        "shards",
        "selected_total",
        "all_output_directories_absent_at_bundle",
        "same_pipeline_code_prompt_search_budget_threshold",
        "forward_failure_scored_as_zero",
        "resume_or_selective_rerun_allowed",
        "dev64_is_gate_not_primary_result",
        "all220_is_primary_result",
        "search_capacity_preflight_required",
        "full220_launch_allowed",
        "separate_executor_activation_required",
        "leaderboard_submission_or_sota_claim",
        "bundle_payload_sha256",
    }
)
GO_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "label_blind",
        "decision",
        "candidate_freeze_allowed",
        "benchmark_forward_launch_allowed",
        "candidate_pipeline_version",
        "candidate_state_schema_version",
        "all220_opaque_partition_sha256",
        "candidate_method_contract_sha256",
        "runtime_mapping_gold_category_question_type_evaluator_score_read",
        "receipt_payload_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _without(value: dict[str, Any], key: str) -> dict[str, Any]:
    return {name: item for name, item in value.items() if name != key}


def _reject_forbidden_metadata(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).casefold()
            if normalized in CREDENTIAL_METADATA_KEYS:
                raise RuntimeError("V2.41.97 credential-like metadata key appeared")
            if normalized in FORBIDDEN_METADATA_KEYS:
                raise RuntimeError("V2.41.97 evaluator-only metadata key appeared")
            _reject_forbidden_metadata(item)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_metadata(item)
    elif isinstance(value, str) and CREDENTIAL_LIKE.search(value):
        raise RuntimeError("V2.41.97 credential-like value appeared")


def _ordinary(root: Path, raw: object, *, prefix: str) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise RuntimeError("V2.41.97 path is not a canonical relative path")
    relative = Path(raw)
    if ".." in relative.parts or relative.parts[0] != prefix:
        raise RuntimeError("V2.41.97 path escapes its declared prefix")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.41.97 expected an ordinary workspace file")
    return path


def _workspace_file(
    root: Path,
    raw: object,
    *,
    allowed_prefixes: tuple[str, ...],
) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise RuntimeError("V2.41.97 workspace path is noncanonical")
    relative = Path(raw)
    if (
        ".." in relative.parts
        or not relative.parts
        or relative.parts[0] not in allowed_prefixes
    ):
        raise RuntimeError("V2.41.97 workspace path escapes the repository")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.41.97 expected an ordinary workspace file")
    return path


def _bytes_snapshot(path: Path) -> tuple[bytes, str]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError("V2.41.97 snapshot source is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if before_identity != after_identity:
        raise RuntimeError("V2.41.97 source changed during byte snapshot")
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise RuntimeError("V2.41.97 source snapshot is truncated")
    return payload, hashlib.sha256(payload).hexdigest()


def _object_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    payload, digest = _bytes_snapshot(path)
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("V2.41.97 source is not UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.97 expected one JSON object")
    return value, digest


def _object(path: Path) -> dict[str, Any]:
    return _object_snapshot(path)[0]


def validate_capacity_pair(
    report: dict[str, Any],
    freeze: dict[str, Any],
    *,
    report_sha256: str,
    protocol_sha256: str,
) -> dict[str, int]:
    """Recompute the capacity decision and bind its report/freeze pair."""

    if (
        set(report) != CAPACITY_REPORT_CORE_FIELDS | CAPACITY_REPORT_EXECUTION_FIELDS
        or report.get("report_payload_sha256")
        != payload_sha256(_without(report, "report_payload_sha256"))
        or freeze.get("freeze_payload_sha256")
        != payload_sha256(_without(freeze, "freeze_payload_sha256"))
    ):
        raise RuntimeError("V2.41.97 capacity payload seal is invalid")
    derived = validate_capacity_report(report)
    selected = int(derived["selected"])
    workers = int(derived["workers"])
    shards = int(derived["shards"])
    expected = build_capacity_freeze(
        report,
        report_path="results/v24196_capacity_ladder_report_v1_20260731.json",
        report_sha256=report_sha256,
        protocol_path="results/v24196_capacity_executor_preregistration_v1_20260731.json",
        protocol_sha256=protocol_sha256,
    )
    expected["freeze_payload_sha256"] = payload_sha256(expected)
    if (
        freeze != expected
        or freeze.get("role") != "v24194_next_fresh_all220_capacity_freeze"
        or freeze.get("source_report")
        != {
            "path": "results/v24196_capacity_ladder_report_v1_20260731.json",
            "sha256": report_sha256,
        }
        or freeze.get("protocol")
        != {
            "path": "results/v24196_capacity_executor_preregistration_v1_20260731.json",
            "sha256": protocol_sha256,
        }
        or freeze.get("endpoint") != "http://127.0.0.1:9878/responses"
        or freeze.get("model") != "gpt-5.6-sol"
        or freeze.get("reasoning_effort") != "high"
        or freeze.get("service_tier") != "priority"
        or freeze.get("model_request_concurrency_cap") != selected
        or freeze.get("parallel_shard_cap") != shards
        or freeze.get("per_shard_candidate_model_workers_cap") != workers
        or freeze.get("per_shard_row_model_workers_cap") != workers
        or freeze.get("worst_case_model_request_concurrency")
        != shards * workers
        or freeze.get("same_all220_opaque_partition_required") is not True
        or freeze.get("new_output_roots_required") is not True
        or freeze.get("resume_or_selective_rerun_allowed") is not False
        or freeze.get("forward_failure_scored_as_zero") is not True
        or freeze.get("fixed_concurrency_for_entire_all220") is not True
        or freeze.get("all220_is_primary_result") is not True
        or freeze.get("candidate_forward_code_prompt_search_budget_or_threshold_frozen")
        is not False
        or freeze.get("full220_launch_allowed") is not False
        or freeze.get("separate_candidate_freeze_and_go_decision_required")
        is not True
        or freeze.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.41.97 capacity freeze does not replay exactly")
    return {"selected": selected, "workers": workers, "shards": shards}


def load_capacity_pair(
    root: Path,
    *,
    report_path: str,
    freeze_path: str,
    protocol_sha256: str,
) -> tuple[dict[str, int], dict[str, Any], dict[str, str]]:
    report_file = _ordinary(root, report_path, prefix="results")
    freeze_file = _ordinary(root, freeze_path, prefix="results")
    report, report_digest = _object_snapshot(report_file)
    freeze, freeze_digest = _object_snapshot(freeze_file)
    derived = validate_capacity_pair(
        report,
        freeze,
        report_sha256=report_digest,
        protocol_sha256=protocol_sha256,
    )
    return derived, freeze, {
        "report_sha256": report_digest,
        "freeze_sha256": freeze_digest,
    }


def _read_ids(path: Path, expected: int, digest: str) -> list[str]:
    payload, observed = _bytes_snapshot(path)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("V2.41.97 opaque-ID file is not UTF-8") from exc
    values = [line.strip() for line in text.splitlines()]
    if (
        observed != digest
        or len(values) != expected
        or len(set(values)) != expected
        or any(OPAQUE_ID.fullmatch(value) is None for value in values)
    ):
        raise RuntimeError("V2.41.97 shard is not an exact opaque-ID partition")
    return values


def _validate_go_receipt(root: Path, row: object) -> dict[str, Any]:
    if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
        raise RuntimeError("V2.41.97 candidate GO receipt reference is invalid")
    path = _ordinary(root, row["path"], prefix="results")
    value, digest = _object_snapshot(path)
    if row["sha256"] != digest:
        raise RuntimeError("V2.41.97 candidate GO receipt hash drifted")
    if (
        set(value) != GO_FIELDS
        or value.get("role") != "v24197_candidate_quality_go_receipt"
        or value.get("label_blind") is not True
        or value.get("decision") != "go"
        or value.get("candidate_freeze_allowed") is not True
        or value.get("benchmark_forward_launch_allowed") is not False
        or not isinstance(value.get("candidate_pipeline_version"), str)
        or not value.get("candidate_pipeline_version")
        or isinstance(value.get("candidate_state_schema_version"), bool)
        or not isinstance(value.get("candidate_state_schema_version"), int)
        or SHA256.fullmatch(str(value.get("all220_opaque_partition_sha256", "")))
        is None
        or SHA256.fullmatch(str(value.get("candidate_method_contract_sha256", "")))
        is None
        or value.get(
            "runtime_mapping_gold_category_question_type_evaluator_score_read"
        )
        is not False
        or value.get("receipt_payload_sha256")
        != payload_sha256(_without(value, "receipt_payload_sha256"))
    ):
        raise RuntimeError("V2.41.97 candidate GO receipt is invalid")
    _reject_forbidden_metadata(
        {
            key: item
            for key, item in value.items()
            if key
            not in {
                "runtime_mapping_gold_category_question_type_evaluator_score_read"
            }
        }
    )
    return value


def validate_candidate_bundle(
    root: Path,
    bundle: dict[str, Any],
    *,
    bundle_path: str,
    bundle_sha256: str,
    capacity_path: str,
    capacity_sha256: str,
    capacity: dict[str, int],
    capacity_freeze: dict[str, Any],
) -> dict[str, Any]:
    """Validate four immutable candidate shards without opening questions."""

    if (
        set(bundle) != BUNDLE_FIELDS
        or bundle.get("role") != "v24197_fresh_all220_execution_bundle"
        or bundle.get("label_blind") is not True
        or bundle.get("bundle_payload_sha256")
        != payload_sha256(_without(bundle, "bundle_payload_sha256"))
        or SAFE_NAME.fullmatch(str(bundle.get("target_name", ""))) is None
        or not isinstance(bundle.get("pipeline_version"), str)
        or not bundle.get("pipeline_version")
        or isinstance(bundle.get("state_schema_version"), bool)
        or not isinstance(bundle.get("state_schema_version"), int)
        or bundle.get("state_schema_version", 0) <= 0
        or bundle.get("capacity_freeze")
        != {"path": capacity_path, "sha256": capacity_sha256}
        or bundle.get("model")
        != {
            "endpoint": capacity_freeze["endpoint"],
            "name": capacity_freeze["model"],
            "reasoning_effort": capacity_freeze["reasoning_effort"],
            "service_tier": capacity_freeze["service_tier"],
        }
        or bundle.get("shard_order") != list(EXPECTED_SHARDS)
        or bundle.get("selected_total") != 220
        or bundle.get("all_output_directories_absent_at_bundle") is not True
        or bundle.get("same_pipeline_code_prompt_search_budget_threshold") is not True
        or bundle.get("forward_failure_scored_as_zero") is not True
        or bundle.get("resume_or_selective_rerun_allowed") is not False
        or bundle.get("dev64_is_gate_not_primary_result") is not True
        or bundle.get("all220_is_primary_result") is not True
        or bundle.get("search_capacity_preflight_required") is not True
        or bundle.get("full220_launch_allowed") is not False
        or bundle.get("separate_executor_activation_required") is not True
        or bundle.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.41.97 candidate bundle header is invalid")
    _reject_forbidden_metadata(bundle)
    go = _validate_go_receipt(root, bundle.get("candidate_quality_go_receipt"))
    if (
        bundle.get("candidate_method_contract_sha256")
        != go["candidate_method_contract_sha256"]
    ):
        raise RuntimeError("V2.41.97 bundle method contract is not quality-bound")
    rows = bundle.get("shards")
    if not isinstance(rows, dict) or set(rows) != set(EXPECTED_SHARDS):
        raise RuntimeError("V2.41.97 candidate shard map is invalid")

    all_ids: list[str] = []
    stable: dict[str, Any] | None = None
    summaries: dict[str, Any] = {}
    workers = capacity["workers"]
    freeze_paths: set[str] = set()
    ids_paths: set[str] = set()
    output_paths: set[str] = set()
    for tag in EXPECTED_SHARDS:
        row = rows[tag]
        if not isinstance(row, dict) or set(row) != {
            "freeze",
            "selected_ids",
            "output_directory",
        }:
            raise RuntimeError("V2.41.97 candidate shard row is invalid")
        freeze_ref = row["freeze"]
        ids_ref = row["selected_ids"]
        if (
            not isinstance(freeze_ref, dict)
            or set(freeze_ref) != {"path", "sha256"}
            or not isinstance(ids_ref, dict)
            or set(ids_ref) != {"path", "sha256", "count"}
            or ids_ref["count"] != EXPECTED_COUNTS[tag]
        ):
            raise RuntimeError("V2.41.97 candidate shard references are invalid")
        freeze_path = _ordinary(root, freeze_ref["path"], prefix="configs")
        ids_path = _ordinary(root, ids_ref["path"], prefix="configs")
        if (
            freeze_ref["path"] in freeze_paths
            or ids_ref["path"] in ids_paths
        ):
            raise RuntimeError("V2.41.97 candidate shard files are reused")
        freeze_paths.add(freeze_ref["path"])
        ids_paths.add(ids_ref["path"])
        freeze, freeze_digest = _object_snapshot(freeze_path)
        if freeze_ref["sha256"] != freeze_digest:
            raise RuntimeError("V2.41.97 candidate freeze hash drifted")
        output_raw = row["output_directory"]
        if (
            not isinstance(output_raw, str)
            or not output_raw
            or Path(output_raw).is_absolute()
        ):
            raise RuntimeError("V2.41.97 candidate output path is invalid")
        output_path = root / output_raw
        if (
            Path(output_raw).parts[0] != "outputs"
            or ".." in Path(output_raw).parts
            or output_path.resolve(strict=False) != output_path.absolute()
            or output_path.exists()
            or output_path.is_symlink()
            or output_raw in output_paths
        ):
            raise RuntimeError("V2.41.97 candidate output root is not fresh")
        output_paths.add(output_raw)
        ids = _read_ids(ids_path, EXPECTED_COUNTS[tag], ids_ref["sha256"])
        model = freeze.get("model") or {}
        runtime = freeze.get("runtime") or {}
        _reject_forbidden_metadata(freeze)
        manifest_path = _workspace_file(
            root,
            freeze.get("manifest"),
            allowed_prefixes=("configs", "data"),
        )
        _manifest_payload, manifest_digest = _bytes_snapshot(manifest_path)
        code = freeze.get("code_sha256")
        if (
            freeze.get("manifest_sha256") != manifest_digest
            or not isinstance(code, dict)
            or not code
            or any(
                not isinstance(digest, str)
                or len(digest) != 64
                or _bytes_snapshot(
                    _workspace_file(
                        root,
                        relative,
                        allowed_prefixes=("src", "scripts"),
                    )
                )[1]
                != digest
                for relative, digest in code.items()
            )
        ):
            raise RuntimeError("V2.41.97 candidate manifest or code hash drifted")
        stable_row = {
            "pipeline_version": freeze.get("pipeline_version"),
            "state_schema_version": freeze.get("state_schema_version"),
            "manifest": freeze.get("manifest"),
            "manifest_sha256": freeze.get("manifest_sha256"),
            "code_sha256": freeze.get("code_sha256"),
            "model": model,
            "search": freeze.get("search"),
            "runtime_without_workers": {
                key: value
                for key, value in runtime.items()
                if key not in {"candidate_model_workers", "row_model_workers"}
            },
        }
        if stable is None:
            stable = stable_row
        elif stable_row != stable:
            raise RuntimeError("V2.41.97 candidate shards are not one frozen method")
        if (
            freeze.get("pipeline_version") != bundle["pipeline_version"]
            or freeze.get("state_schema_version") != bundle["state_schema_version"]
            or freeze.get("selected_ids_file") != ids_ref["path"]
            or freeze.get("selected_ids_sha256") != ids_ref["sha256"]
            or freeze.get("selected_count") != EXPECTED_COUNTS[tag]
            or model.get("proxy_url") != capacity_freeze["endpoint"]
            or model.get("name") != capacity_freeze["model"]
            or model.get("reasoning_effort") != capacity_freeze["reasoning_effort"]
            or model.get("service_tier") != capacity_freeze["service_tier"]
            or runtime.get("candidate_model_workers") != workers
            or runtime.get("row_model_workers") != workers
        ):
            raise RuntimeError("V2.41.97 candidate shard violates capacity binding")
        all_ids.extend(ids)
        summaries[tag] = {
            "freeze": freeze_ref,
            "selected_ids": ids_ref,
            "output_directory": output_raw,
        }
    if len(all_ids) != 220 or len(set(all_ids)) != 220:
        raise RuntimeError("V2.41.97 candidate shards do not form exact all-220")
    partition_sha = payload_sha256(sorted(all_ids))
    if (
        partition_sha != CANONICAL_ALL220_SHA256
        or
        go["candidate_pipeline_version"] != bundle["pipeline_version"]
        or go["candidate_state_schema_version"] != bundle["state_schema_version"]
        or go["all220_opaque_partition_sha256"] != partition_sha
    ):
        raise RuntimeError("V2.41.97 candidate partition is not quality-bound")
    return {
        "bundle": {"path": bundle_path, "sha256": bundle_sha256},
        "target_name": bundle["target_name"],
        "pipeline_version": bundle["pipeline_version"],
        "state_schema_version": bundle["state_schema_version"],
        "shards": summaries,
        "candidate_method_contract_sha256": bundle[
            "candidate_method_contract_sha256"
        ],
        "opaque_partition_sha256": partition_sha,
    }


def compile_parallel_plan(
    candidate: dict[str, Any],
    capacity: dict[str, int],
    *,
    capacity_freeze_path: str,
    capacity_freeze_sha256: str,
) -> dict[str, Any]:
    """Compile deterministic capacity waves; execution remains unauthorized."""

    if capacity["selected"] <= 0 or capacity["workers"] <= 0 or capacity["shards"] <= 0:
        raise RuntimeError("V2.41.97 cannot plan from a capacity NO-GO")
    width = min(len(EXPECTED_SHARDS), capacity["shards"])
    waves = [
        list(EXPECTED_SHARDS[index : index + width])
        for index in range(0, len(EXPECTED_SHARDS), width)
    ]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24197_capacity_bound_fresh_all220_parallel_plan",
        "label_blind": True,
        "candidate_bundle": candidate["bundle"],
        "capacity_freeze": {
            "path": capacity_freeze_path,
            "sha256": capacity_freeze_sha256,
        },
        "target_name": candidate["target_name"],
        "pipeline_version": candidate["pipeline_version"],
        "state_schema_version": candidate["state_schema_version"],
        "candidate_method_contract_sha256": candidate[
            "candidate_method_contract_sha256"
        ],
        "opaque_partition_sha256": candidate["opaque_partition_sha256"],
        "shards": candidate["shards"],
        "schedule": {
            "model_request_concurrency_cap": capacity["selected"],
            "parallel_shards": width,
            "candidate_model_workers_per_shard": capacity["workers"],
            "row_model_workers_per_shard": capacity["workers"],
            "worst_case_model_request_concurrency": width * capacity["workers"],
            "waves": waves,
            "fixed_for_entire_all220": True,
        },
        "selected_total": 220,
        "new_output_roots_required": True,
        "resume_or_selective_rerun_allowed": False,
        "forward_failure_scored_as_zero": True,
        "search_capacity_preflight_required": True,
        "full220_launch_allowed": False,
        "separate_identity_bound_executor_activation_required": True,
        "single_parent_shared_lease_owner_required": True,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["plan_payload_sha256"] = payload_sha256(value)
    return value
