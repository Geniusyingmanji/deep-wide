"""Create-exclusive child artifact bundle for coverage revision tasks.

Every parent, revision, model-slot, search, and transport receipt is persisted
as an independent ordinary file.  The result envelope cannot substitute for a
missing external receipt.  A content-free hash manifest is written last and
acts as the bundle commit marker.  This module has no benchmark mapping, gold,
label, evaluator, score, reward, or historical-result capability.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .v24263_global_model_limiter import payload_sha256
from .v24796_deadline_tavily_search import (
    validate_receipt as validate_direct_receipt,
)
from .v24852_rate_aware_tavily_search import (
    validate_receipt as validate_rate_receipt,
)
from .v24856_pacing_aware_admission import (
    validate_receipt as validate_pacing_receipt,
)
from .v24861_coverage_revision_exact_task import (
    IntegratedCoverageRevisionTaskOutcome,
    build_envelope,
    validate_envelope,
)


POLICY_ID = "v24863_coverage_revision_child_artifact_bundle_v1"
BUNDLE_ROLE = "v24863_coverage_revision_child_bundle_receipt"
RESULT_NAME = "result.json"
FINAL_MODEL_NAME = "model_slot_receipt.json"
PARENT_MODEL_NAME = "parent_model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
SINGLE_NAME = "search_single_shot_receipt.json"
BACKFILL_NAME = "citation_title_backfill_receipt.json"
COVERAGE_NAME = "coverage_revision_receipt.json"
PACING_NAME = "pacing_aware_admission_receipt.json"
DIRECT_NAME = "direct_search_receipt.json"
RATE_NAME = "rate_aware_search_receipt.json"
BUNDLE_NAME = "coverage_revision_bundle_receipt.json"
DATA_NAMES = (
    RESULT_NAME,
    FINAL_MODEL_NAME,
    PARENT_MODEL_NAME,
    TRANSPORT_NAME,
    SINGLE_NAME,
    BACKFILL_NAME,
    COVERAGE_NAME,
    PACING_NAME,
    DIRECT_NAME,
    RATE_NAME,
)
ALL_NAMES = (*DATA_NAMES, BUNDLE_NAME)


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
        raise ValueError("V2.48.63 task directory escaped output root")
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
        raise ValueError("V2.48.63 expected an ordinary bundle artifact")
    return target


def _read(path: Path, directory: Path) -> dict[str, Any]:
    target = _ordinary_file(path, directory)
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("V2.48.63 expected an object artifact")
    return value


def _sha256(path: Path, directory: Path) -> str:
    target = _ordinary_file(path, directory)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
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


def _runtime_binding(
    envelope: Mapping[str, Any],
    *,
    direct: Mapping[str, Any],
    rate: Mapping[str, Any],
    pacing: Mapping[str, Any],
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
) -> None:
    result = envelope["result"]
    parent = result["parent_result"]
    retrieval = parent.get("two_wave_retrieval")
    if not isinstance(retrieval, Mapping) or retrieval.get("status") != "completed":
        raise ValueError("V2.48.63 successful bundle lacks completed retrieval")
    nested = retrieval.get("receipt")
    if not isinstance(nested, Mapping):
        raise ValueError("V2.48.63 retrieval receipt is absent")
    controller = nested.get("controller")
    total = nested.get("total")
    if not isinstance(controller, Mapping) or not isinstance(total, Mapping):
        raise ValueError("V2.48.63 retrieval accounting is absent")
    first = controller.get("first_wave")
    policy = controller.get("policy")
    if not isinstance(first, Mapping) or not isinstance(policy, Mapping):
        raise ValueError("V2.48.63 controller binding is absent")
    raw_first = float(first.get("search_seconds", -1)) + float(
        first.get("fetch_seconds", -1)
    )
    logical_queries = int(total.get("queries_executed", -1))
    if (
        envelope["model_slot_receipt"].get("slot_cap")
        != expected_model_slot_cap
        or envelope["parent_model_slot_receipt"].get("slot_cap")
        != expected_model_slot_cap
        or direct.get("key_slot_cap") != expected_tavily_key_slot_cap
        or direct.get("successful_queries", 0) + direct.get("failed_queries", 0)
        != logical_queries
        or direct.get("successful_queries", 0)
        > direct.get("provider_attempts", -1)
        or int((parent.get("cost") or {}).get("search", {}).get("calls", -1))
        != logical_queries
        or direct.get("provider_attempts")
        != rate.get("provider_start_reservations")
        or direct.get("status_429") != rate.get("provider_429_responses")
        or pacing.get("provider_start_reservations_at_admission", -1)
        > rate.get("provider_start_reservations", -1)
        or pacing.get("pacing_aware_decision") != controller.get("decision")
        or pacing.get("pacing_aware_reason") != controller.get("reason")
        or not math.isclose(
            float(pacing.get("raw_wave1_elapsed_seconds", -1)),
            raw_first,
            rel_tol=0.0,
            abs_tol=1e-6,
        )
        or not math.isclose(
            float(pacing.get("effective_wave1_ceiling_seconds", -1)),
            float(policy.get("maximum_wave1_seconds", -2)),
            rel_tol=0.0,
            abs_tol=1e-6,
        )
    ):
        raise ValueError("V2.48.63 runtime artifact binding drifted")


def _validate_values(
    values: Mapping[str, Mapping[str, Any]],
    *,
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
) -> dict[str, Any]:
    if set(values) != set(DATA_NAMES):
        raise ValueError("V2.48.63 bundle data vector drifted")
    envelope = validate_envelope(values[RESULT_NAME])
    direct = validate_direct_receipt(values[DIRECT_NAME])
    rate = validate_rate_receipt(values[RATE_NAME])
    pacing = validate_pacing_receipt(values[PACING_NAME])
    copies = {
        FINAL_MODEL_NAME: "model_slot_receipt",
        PARENT_MODEL_NAME: "parent_model_slot_receipt",
        TRANSPORT_NAME: "transport_health",
        SINGLE_NAME: "search_single_shot_receipt",
        BACKFILL_NAME: "citation_title_backfill_receipt",
        COVERAGE_NAME: "coverage_revision_receipt",
    }
    if any(envelope[field] != values[name] for name, field in copies.items()):
        raise ValueError("V2.48.63 independent artifact copy drifted")
    _runtime_binding(
        envelope,
        direct=direct,
        rate=rate,
        pacing=pacing,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
    )
    return envelope


def build_bundle_receipt(
    manifest: Mapping[str, str],
    *,
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": BUNDLE_ROLE,
        "policy_id": POLICY_ID,
        "artifact_count": len(DATA_NAMES),
        "artifact_manifest": dict(manifest),
        "expected_model_slot_cap": int(expected_model_slot_cap),
        "expected_tavily_key_slot_cap": int(expected_tavily_key_slot_cap),
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
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
    )


def validate_bundle_receipt(
    value: Mapping[str, Any],
    *,
    expected_manifest: Mapping[str, str],
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
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
        "expected_tavily_key_slot_cap",
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
        or copied.get("expected_tavily_key_slot_cap")
        != expected_tavily_key_slot_cap
        or copied.get(
            "result_envelope_cannot_substitute_for_external_receipt"
        )
        is not True
        or copied.get(
            "bundle_commit_marker_written_after_all_data_artifacts"
        )
        is not True
        or copied.get(
            "question_query_url_host_page_prediction_candidate_value_evidence_id_or_credential_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_or_process_effect_by_bundle_builder"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.63 bundle receipt drifted")
    return copied


def write_bundle(
    *,
    output_root: Path,
    directory: Path,
    outcome: IntegratedCoverageRevisionTaskOutcome,
    direct_receipt: Mapping[str, Any],
    rate_receipt: Mapping[str, Any],
    pacing_receipt: Mapping[str, Any],
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
    writer: Callable[[Path, Mapping[str, Any]], None] = _atomic_new,
) -> dict[str, Any]:
    task_directory = _ordinary_directory(directory, output_root)
    if any((task_directory / name).exists() or (task_directory / name).is_symlink() for name in ALL_NAMES):
        raise FileExistsError("V2.48.63 bundle surface is not pristine")
    envelope = build_envelope(outcome, arm="baseline")
    values: dict[str, Mapping[str, Any]] = {
        RESULT_NAME: envelope,
        FINAL_MODEL_NAME: outcome.model_slot_receipt,
        PARENT_MODEL_NAME: outcome.parent_model_slot_receipt,
        TRANSPORT_NAME: outcome.transport_health,
        SINGLE_NAME: outcome.search_single_shot_receipt,
        BACKFILL_NAME: outcome.citation_title_backfill_receipt,
        COVERAGE_NAME: outcome.coverage_revision_receipt,
        PACING_NAME: validate_pacing_receipt(pacing_receipt),
        DIRECT_NAME: validate_direct_receipt(direct_receipt),
        RATE_NAME: validate_rate_receipt(rate_receipt),
    }
    _validate_values(
        values,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
    )
    for name in DATA_NAMES:
        writer(task_directory / name, values[name])
    manifest = {
        name: _sha256(task_directory / name, task_directory)
        for name in DATA_NAMES
    }
    receipt = build_bundle_receipt(
        manifest,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
    )
    writer(task_directory / BUNDLE_NAME, receipt)
    return validate_bundle(
        output_root=output_root,
        directory=task_directory,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
    )


def validate_bundle(
    *,
    output_root: Path,
    directory: Path,
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
) -> dict[str, Any]:
    task_directory = _ordinary_directory(directory, output_root)
    values = {
        name: _read(task_directory / name, task_directory) for name in DATA_NAMES
    }
    manifest = {
        name: _sha256(task_directory / name, task_directory)
        for name in DATA_NAMES
    }
    bundle = _read(task_directory / BUNDLE_NAME, task_directory)
    validate_bundle_receipt(
        bundle,
        expected_manifest=manifest,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
    )
    _validate_values(
        values,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
    )
    return bundle


__all__ = [
    "ALL_NAMES",
    "BACKFILL_NAME",
    "BUNDLE_NAME",
    "COVERAGE_NAME",
    "DATA_NAMES",
    "DIRECT_NAME",
    "FINAL_MODEL_NAME",
    "PACING_NAME",
    "PARENT_MODEL_NAME",
    "RATE_NAME",
    "RESULT_NAME",
    "SINGLE_NAME",
    "TRANSPORT_NAME",
    "build_bundle_receipt",
    "validate_bundle",
    "validate_bundle_receipt",
    "write_bundle",
]
