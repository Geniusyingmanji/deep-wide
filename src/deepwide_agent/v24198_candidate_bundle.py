"""Compile one independently selected candidate into the V2.41.97 bundle.

This module is deliberately not a selector and not an executor.  It accepts a
future, independently published candidate handoff, binds it to the neutral
capacity freeze, and produces the exact GO receipt and bundle consumed by
V2.41.97.  It never opens benchmark questions, calls a network service, or
authorizes a benchmark launch.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from deepwide_agent.v24197_parallel_all220 import (
    CANONICAL_ALL220_SHA256,
    EXPECTED_COUNTS,
    EXPECTED_SHARDS,
    GO_FIELDS,
    _bytes_snapshot,
    _object_snapshot,
    _reject_forbidden_metadata,
    file_sha256,
    payload_sha256,
    validate_candidate_bundle,
)


COMPILER_PROTOCOL = Path(
    "results/v24198_candidate_bundle_preregistration_v1_20260731.json"
)
SELECTION_PROTOCOL = Path(
    "results/v24198_selected_candidate_selector_preregistration_v1_20260731.json"
)
QUALITY_TERMINAL_RECEIPT = Path(
    "results/v24198_selected_candidate_terminal_receipt_v1_20260731.json"
)
HANDOFF = Path("results/v24198_selected_candidate_handoff_v1_20260731.json")
GO_RECEIPT = Path("results/v24198_candidate_quality_go_receipt_v1_20260731.json")
BUNDLE = Path("results/v24197_fresh_all220_execution_bundle_v1_20260731.json")

SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}")
CANONICAL_ID_FILES = {
    "test_s01": {
        "path": "configs/full220_v2403_r1_test_s01.ids",
        "sha256": "9f4c7bb4e9f63b01b574a52ec840266358dae6d9982dc7caebfeb813eca02dfb",
        "count": 52,
    },
    "test_s02": {
        "path": "configs/full220_v2403_r1_test_s02.ids",
        "sha256": "2b48a04896437fdea127e02ad7980f2cb9310db9a16841696affd04796502bbd",
        "count": 52,
    },
    "test_s03": {
        "path": "configs/full220_v2403_r1_test_s03.ids",
        "sha256": "abaadc27927a9dbd5ad8cc856513baa85e8c900ed041cf6e5c0978534d103566",
        "count": 52,
    },
    "devval": {
        "path": "configs/full220_v2403_r1_devval_s04.ids",
        "sha256": "79ba11a41c186daa80e8779e8fa2c1b47e7907f8e398d817dedb43099333d69c",
        "count": 64,
    },
}

REFERENCE_FIELDS = frozenset({"path", "sha256"})
SELECTOR_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "label_blind",
        "selection_frozen_before_quality_outcomes",
        "candidate_set_manifest_sha256",
        "candidate_inheritance_rule_sha256",
        "selection_uses_only_predeclared_quality_gate_statuses",
        "selection_requires_entire_quality_chain_terminal",
        "selected_candidate_must_have_integrated_canonical_all220_freezes",
        "bundle_compiler_has_no_selection_discretion",
        "terminal_receipt_path",
        "handoff_path",
        "benchmark_forward_launch_allowed",
        "mapping_gold_category_question_type_evaluator_score_read_by_selector_runtime",
        "leaderboard_submission_or_sota_claim",
        "selector_payload_sha256",
    }
)
TERMINAL_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "label_blind",
        "decision",
        "selector_protocol",
        "all_required_quality_gates_terminal",
        "candidate_selection_rule_live_replayed",
        "selected_candidate_publication",
        "selected_pipeline_version",
        "selected_state_schema_version",
        "selected_candidate_method_contract_sha256",
        "canonical_all220_integrated_freezes_ready",
        "benchmark_forward_launch_allowed",
        "mapping_gold_category_question_type_evaluator_score_read_by_bundle_compiler",
        "leaderboard_submission_or_sota_claim",
        "terminal_receipt_payload_sha256",
    }
)
HANDOFF_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "label_blind",
        "decision",
        "compiler_protocol",
        "selection_protocol",
        "quality_chain_terminal_receipt",
        "candidate_publication",
        "selection_was_frozen_before_bundle_compilation",
        "candidate_selected_by_predeclared_quality_gates",
        "selection_not_made_by_bundle_compiler",
        "target_name",
        "pipeline_version",
        "state_schema_version",
        "candidate_method_contract_sha256",
        "model",
        "shard_order",
        "shards",
        "selected_total",
        "all_output_directories_absent_at_handoff",
        "same_pipeline_code_prompt_search_budget_threshold",
        "forward_failure_scored_as_zero",
        "resume_or_selective_rerun_allowed",
        "dev64_is_gate_not_primary_result",
        "all220_is_primary_result",
        "search_capacity_preflight_required",
        "benchmark_forward_launch_allowed",
        "separate_executor_activation_required",
        "runtime_mapping_gold_category_question_type_evaluator_score_read",
        "leaderboard_submission_or_sota_claim",
        "handoff_payload_sha256",
    }
)


def _without(value: dict[str, Any], key: str) -> dict[str, Any]:
    return {name: item for name, item in value.items() if name != key}


def _result_reference(
    root: Path,
    value: object,
    *,
    expected_path: Path | None = None,
) -> tuple[dict[str, str], Path]:
    if not isinstance(value, dict) or set(value) != REFERENCE_FIELDS:
        raise RuntimeError("V2.41.98 result reference is invalid")
    raw = value.get("path")
    digest = value.get("sha256")
    if (
        not isinstance(raw, str)
        or not raw
        or Path(raw).is_absolute()
        or ".." in Path(raw).parts
        or Path(raw).parts[0] != "results"
        or SHA256.fullmatch(str(digest or "")) is None
    ):
        raise RuntimeError("V2.41.98 result reference is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to((root / "results").resolve())
        or (expected_path is not None and Path(raw) != expected_path)
    ):
        raise RuntimeError("V2.41.98 result reference drifted")
    try:
        observed = _bytes_snapshot(path)[1]
    except OSError as exc:
        raise RuntimeError("V2.41.98 result reference changed during snapshot") from exc
    if observed != digest:
        raise RuntimeError("V2.41.98 result reference drifted")
    return {"path": raw, "sha256": str(digest)}, path


def _validate_selector_protocol(
    path: Path,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    value, digest = _object_snapshot(path)
    if (
        digest != expected_sha256
        or set(value) != SELECTOR_FIELDS
        or value.get("artifact_version") != 1
        or value.get("role")
        != "v24198_selected_candidate_selector_preregistration"
        or value.get("protocol_id")
        != "v24198_predeclared_quality_chain_candidate_selector_v1"
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value.get("label_blind") is not True
        or value.get("selection_frozen_before_quality_outcomes") is not True
        or SHA256.fullmatch(str(value.get("candidate_set_manifest_sha256", "")))
        is None
        or SHA256.fullmatch(
            str(value.get("candidate_inheritance_rule_sha256", ""))
        )
        is None
        or value.get("selection_uses_only_predeclared_quality_gate_statuses")
        is not True
        or value.get("selection_requires_entire_quality_chain_terminal") is not True
        or value.get("selected_candidate_must_have_integrated_canonical_all220_freezes")
        is not True
        or value.get("bundle_compiler_has_no_selection_discretion") is not True
        or value.get("terminal_receipt_path") != str(QUALITY_TERMINAL_RECEIPT)
        or value.get("handoff_path") != str(HANDOFF)
        or value.get("benchmark_forward_launch_allowed") is not False
        or value.get(
            "mapping_gold_category_question_type_evaluator_score_read_by_selector_runtime"
        )
        is not False
        or value.get("leaderboard_submission_or_sota_claim") is not False
        or value.get("selector_payload_sha256")
        != payload_sha256(_without(value, "selector_payload_sha256"))
    ):
        raise RuntimeError("V2.41.98 selector protocol is invalid")
    return value


def _validate_terminal_receipt(
    path: Path,
    *,
    expected_sha256: str,
    selector_reference: dict[str, str],
) -> dict[str, Any]:
    value, digest = _object_snapshot(path)
    if (
        digest != expected_sha256
        or set(value) != TERMINAL_FIELDS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24198_selected_candidate_terminal_receipt"
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value.get("label_blind") is not True
        or value.get("decision") != "go"
        or value.get("selector_protocol") != selector_reference
        or value.get("all_required_quality_gates_terminal") is not True
        or value.get("candidate_selection_rule_live_replayed") is not True
        or not isinstance(value.get("selected_candidate_publication"), dict)
        or set(value["selected_candidate_publication"]) != REFERENCE_FIELDS
        or not isinstance(value.get("selected_pipeline_version"), str)
        or not value.get("selected_pipeline_version")
        or isinstance(value.get("selected_state_schema_version"), bool)
        or not isinstance(value.get("selected_state_schema_version"), int)
        or value.get("selected_state_schema_version", 0) <= 0
        or SHA256.fullmatch(
            str(value.get("selected_candidate_method_contract_sha256", ""))
        )
        is None
        or value.get("canonical_all220_integrated_freezes_ready") is not True
        or value.get("benchmark_forward_launch_allowed") is not False
        or value.get(
            "mapping_gold_category_question_type_evaluator_score_read_by_bundle_compiler"
        )
        is not False
        or value.get("leaderboard_submission_or_sota_claim") is not False
        or value.get("terminal_receipt_payload_sha256")
        != payload_sha256(_without(value, "terminal_receipt_payload_sha256"))
    ):
        raise RuntimeError("V2.41.98 quality-chain terminal receipt is invalid")
    return value


def validate_handoff(
    root: Path,
    handoff: dict[str, Any],
    *,
    handoff_path: str,
    handoff_sha256: str,
    compiler_protocol_sha256: str,
    capacity_freeze: dict[str, Any],
) -> dict[str, Any]:
    """Validate a structural selector handoff without opening selector bytes."""

    if (
        set(handoff) != HANDOFF_FIELDS
        or handoff.get("artifact_version") != 1
        or handoff.get("role") != "v24198_selected_candidate_handoff"
        or isinstance(handoff.get("created_at_unix"), bool)
        or not isinstance(handoff.get("created_at_unix"), int)
        or handoff.get("label_blind") is not True
        or handoff.get("decision") != "go"
        or handoff.get("handoff_payload_sha256")
        != payload_sha256(_without(handoff, "handoff_payload_sha256"))
        or handoff.get("compiler_protocol")
        != {
            "path": str(COMPILER_PROTOCOL),
            "sha256": compiler_protocol_sha256,
        }
        or handoff.get("selection_was_frozen_before_bundle_compilation") is not True
        or handoff.get("candidate_selected_by_predeclared_quality_gates") is not True
        or handoff.get("selection_not_made_by_bundle_compiler") is not True
        or SAFE_NAME.fullmatch(str(handoff.get("target_name", ""))) is None
        or not isinstance(handoff.get("pipeline_version"), str)
        or not handoff.get("pipeline_version")
        or isinstance(handoff.get("state_schema_version"), bool)
        or not isinstance(handoff.get("state_schema_version"), int)
        or handoff.get("state_schema_version", 0) <= 0
        or SHA256.fullmatch(
            str(handoff.get("candidate_method_contract_sha256", ""))
        )
        is None
        or handoff.get("model")
        != {
            "endpoint": capacity_freeze["endpoint"],
            "name": capacity_freeze["model"],
            "reasoning_effort": capacity_freeze["reasoning_effort"],
            "service_tier": capacity_freeze["service_tier"],
        }
        or handoff.get("shard_order") != list(EXPECTED_SHARDS)
        or handoff.get("selected_total") != 220
        or handoff.get("all_output_directories_absent_at_handoff") is not True
        or handoff.get("same_pipeline_code_prompt_search_budget_threshold") is not True
        or handoff.get("forward_failure_scored_as_zero") is not True
        or handoff.get("resume_or_selective_rerun_allowed") is not False
        or handoff.get("dev64_is_gate_not_primary_result") is not True
        or handoff.get("all220_is_primary_result") is not True
        or handoff.get("search_capacity_preflight_required") is not True
        or handoff.get("benchmark_forward_launch_allowed") is not False
        or handoff.get("separate_executor_activation_required") is not True
        or handoff.get(
            "runtime_mapping_gold_category_question_type_evaluator_score_read"
        )
        is not False
        or handoff.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.41.98 selected candidate handoff is invalid")
    _reject_forbidden_metadata(
        {
            key: item
            for key, item in handoff.items()
            if key
            != "runtime_mapping_gold_category_question_type_evaluator_score_read"
        }
    )
    selection, selection_path = _result_reference(
        root,
        handoff.get("selection_protocol"),
        expected_path=SELECTION_PROTOCOL,
    )
    terminal, terminal_path = _result_reference(
        root,
        handoff.get("quality_chain_terminal_receipt"),
        expected_path=QUALITY_TERMINAL_RECEIPT,
    )
    publication, _ = _result_reference(root, handoff.get("candidate_publication"))
    if len({selection["path"], terminal["path"], publication["path"]}) != 3:
        raise RuntimeError("V2.41.98 selector evidence files are reused")
    selector = _validate_selector_protocol(
        selection_path, expected_sha256=selection["sha256"]
    )
    terminal_value = _validate_terminal_receipt(
        terminal_path,
        expected_sha256=terminal["sha256"],
        selector_reference=selection,
    )
    if (
        terminal_value["created_at_unix"] < selector["created_at_unix"]
        or handoff["created_at_unix"] < terminal_value["created_at_unix"]
    ):
        raise RuntimeError("V2.41.98 selector terminal handoff order is invalid")
    if (
        terminal_value["selected_candidate_publication"] != publication
        or terminal_value["selected_pipeline_version"]
        != handoff["pipeline_version"]
        or terminal_value["selected_state_schema_version"]
        != handoff["state_schema_version"]
        or terminal_value["selected_candidate_method_contract_sha256"]
        != handoff["candidate_method_contract_sha256"]
    ):
        raise RuntimeError("V2.41.98 terminal selection differs from handoff")
    rows = handoff.get("shards")
    if not isinstance(rows, dict) or set(rows) != set(EXPECTED_SHARDS):
        raise RuntimeError("V2.41.98 selected candidate shards are invalid")
    freeze_paths: set[str] = set()
    output_paths: set[str] = set()
    normalized: dict[str, Any] = {}
    for tag in EXPECTED_SHARDS:
        row = rows[tag]
        if not isinstance(row, dict) or set(row) != {
            "freeze",
            "selected_ids",
            "output_directory",
        }:
            raise RuntimeError("V2.41.98 selected candidate shard row is invalid")
        freeze = row["freeze"]
        if (
            not isinstance(freeze, dict)
            or set(freeze) != REFERENCE_FIELDS
            or not isinstance(freeze.get("path"), str)
            or Path(freeze["path"]).is_absolute()
            or ".." in Path(freeze["path"]).parts
            or Path(freeze["path"]).parts[0] != "configs"
            or SHA256.fullmatch(str(freeze.get("sha256", ""))) is None
            or freeze["path"] in freeze_paths
        ):
            raise RuntimeError("V2.41.98 selected candidate freeze is invalid")
        freeze_path = root / freeze["path"]
        if (
            freeze_path.resolve(strict=False) != freeze_path.absolute()
            or freeze_path.is_symlink()
            or not freeze_path.is_file()
        ):
            raise RuntimeError("V2.41.98 selected candidate freeze drifted")
        try:
            observed_freeze_sha = _bytes_snapshot(freeze_path)[1]
        except OSError as exc:
            raise RuntimeError("V2.41.98 selected candidate freeze changed") from exc
        if observed_freeze_sha != freeze["sha256"]:
            raise RuntimeError("V2.41.98 selected candidate freeze drifted")
        freeze_paths.add(freeze["path"])
        if row["selected_ids"] != CANONICAL_ID_FILES[tag]:
            raise RuntimeError("V2.41.98 selected IDs are not the canonical shard")
        ids_path = root / CANONICAL_ID_FILES[tag]["path"]
        observed_ids_sha = (
            _bytes_snapshot(ids_path)[1]
            if ids_path.is_file() and not ids_path.is_symlink()
            else None
        )
        if (
            ids_path.is_symlink()
            or not ids_path.is_file()
            or observed_ids_sha != CANONICAL_ID_FILES[tag]["sha256"]
            or EXPECTED_COUNTS[tag] != CANONICAL_ID_FILES[tag]["count"]
        ):
            raise RuntimeError("V2.41.98 canonical selected-ID file drifted")
        output = row["output_directory"]
        if (
            not isinstance(output, str)
            or not output
            or Path(output).is_absolute()
            or ".." in Path(output).parts
            or Path(output).parts[0] != "outputs"
            or output in output_paths
            or (root / output).exists()
            or (root / output).is_symlink()
        ):
            raise RuntimeError("V2.41.98 output root is not fresh")
        output_paths.add(output)
        normalized[tag] = {
            "freeze": dict(freeze),
            "selected_ids": dict(row["selected_ids"]),
            "output_directory": output,
        }
    return {
        "handoff": {"path": handoff_path, "sha256": handoff_sha256},
        "selection_protocol": selection,
        "quality_chain_terminal_receipt": terminal,
        "candidate_publication": publication,
        "target_name": handoff["target_name"],
        "pipeline_version": handoff["pipeline_version"],
        "state_schema_version": handoff["state_schema_version"],
        "candidate_method_contract_sha256": handoff[
            "candidate_method_contract_sha256"
        ],
        "model": dict(handoff["model"]),
        "shards": normalized,
    }


def build_go_receipt(selected: dict[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24197_candidate_quality_go_receipt",
        "label_blind": True,
        "decision": "go",
        "candidate_freeze_allowed": True,
        "benchmark_forward_launch_allowed": False,
        "candidate_pipeline_version": selected["pipeline_version"],
        "candidate_state_schema_version": selected["state_schema_version"],
        "all220_opaque_partition_sha256": CANONICAL_ALL220_SHA256,
        "candidate_method_contract_sha256": selected[
            "candidate_method_contract_sha256"
        ],
        "runtime_mapping_gold_category_question_type_evaluator_score_read": False,
    }
    if set(value) != GO_FIELDS - {"receipt_payload_sha256"}:
        raise AssertionError("V2.41.98 GO receipt schema drifted")
    value["receipt_payload_sha256"] = payload_sha256(value)
    return value


def build_bundle(
    selected: dict[str, Any],
    *,
    capacity_freeze_path: str,
    capacity_freeze_sha256: str,
    go_receipt_path: str,
    go_receipt_sha256: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24197_fresh_all220_execution_bundle",
        "label_blind": True,
        "target_name": selected["target_name"],
        "pipeline_version": selected["pipeline_version"],
        "state_schema_version": selected["state_schema_version"],
        "candidate_method_contract_sha256": selected[
            "candidate_method_contract_sha256"
        ],
        "capacity_freeze": {
            "path": capacity_freeze_path,
            "sha256": capacity_freeze_sha256,
        },
        "candidate_quality_go_receipt": {
            "path": go_receipt_path,
            "sha256": go_receipt_sha256,
        },
        "model": selected["model"],
        "shard_order": list(EXPECTED_SHARDS),
        "shards": selected["shards"],
        "selected_total": 220,
        "all_output_directories_absent_at_bundle": True,
        "same_pipeline_code_prompt_search_budget_threshold": True,
        "forward_failure_scored_as_zero": True,
        "resume_or_selective_rerun_allowed": False,
        "dev64_is_gate_not_primary_result": True,
        "all220_is_primary_result": True,
        "search_capacity_preflight_required": True,
        "full220_launch_allowed": False,
        "separate_executor_activation_required": True,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["bundle_payload_sha256"] = payload_sha256(value)
    return value


def compile_outputs(
    root: Path,
    handoff: dict[str, Any],
    *,
    handoff_path: str,
    handoff_sha256: str,
    compiler_protocol_sha256: str,
    capacity: dict[str, int],
    capacity_freeze: dict[str, Any],
    capacity_freeze_path: str,
    capacity_freeze_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    selected = validate_handoff(
        root,
        handoff,
        handoff_path=handoff_path,
        handoff_sha256=handoff_sha256,
        compiler_protocol_sha256=compiler_protocol_sha256,
        capacity_freeze=capacity_freeze,
    )
    go = build_go_receipt(selected)
    bundle = build_bundle(
        selected,
        capacity_freeze_path=capacity_freeze_path,
        capacity_freeze_sha256=capacity_freeze_sha256,
        go_receipt_path=str(GO_RECEIPT),
        go_receipt_sha256=payload_file_sha256(go),
    )
    return selected, go, bundle


def payload_file_sha256(value: object) -> str:
    """Hash the pretty JSON bytes emitted by all V2.41.98 publishers."""

    import hashlib
    import json

    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def validate_published_outputs(
    root: Path,
    *,
    bundle: dict[str, Any],
    bundle_sha256: str,
    capacity: dict[str, int],
    capacity_freeze: dict[str, Any],
    capacity_freeze_path: str,
    capacity_freeze_sha256: str,
) -> dict[str, Any]:
    return validate_candidate_bundle(
        root,
        bundle,
        bundle_path=str(BUNDLE),
        bundle_sha256=bundle_sha256,
        capacity_path=capacity_freeze_path,
        capacity_sha256=capacity_freeze_sha256,
        capacity=capacity,
        capacity_freeze=capacity_freeze,
    )
