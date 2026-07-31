"""Outcome-before inheritance selector for one integrated all-220 candidate.

The selector consumes only terminal status envelopes from predeclared quality
watchers.  It maps the resulting feature vector to exactly one predeclared
integration slot.  It deliberately does not build candidate code, generate
freezes, acquire the shared API lease, call a service, or launch a benchmark.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from deepwide_agent.v24197_parallel_all220 import (
    EXPECTED_COUNTS,
    EXPECTED_SHARDS,
    _bytes_snapshot as v24197_bytes_snapshot,
    _object_snapshot as v24197_object_snapshot,
    _workspace_file,
    _reject_forbidden_metadata,
)
from deepwide_agent.v24198_candidate_bundle import CANONICAL_ID_FILES


QUALITY_SOURCES = {
    "schema77": {
        "path": Path(
            "outputs/v24176_predicate_completion_paired_dev_watcher_state_v1_20260730.json"
        ),
        "role": "v24176_predicate_completion_paired_dev_watcher_state",
        "protocol_sha256": "8c1c3c4d9f7ed8604258fa301ea931a6425cf6c189c5e1c30c0ee387eddd1f1e",
        "go": "complete_paired_dev_go",
        "no_go": "complete_paired_dev_no_go",
    },
    "search_yield": {
        "path": Path(
            "outputs/v24180_predicate_search_yield_watcher_state_v1_20260730.json"
        ),
        "role": "v24180_predicate_search_yield_watcher_state",
        "protocol_sha256": "1274fe4a9b7801d96dd5265443cb3f6b837edd469be3fe85bef1c3d71ebdf5e4",
        "go": "complete_search_yield_go",
        "no_go": "complete_search_yield_no_go",
        "terminal_no_go": "terminal_incomplete_attempt_no_rerun",
    },
    "markdown": {
        "path": Path("outputs/v24103_markdown_paired_dev_watcher_state_v1_20260728.json"),
        "role": "v24103_markdown_paired_dev_watcher_state",
        "protocol_sha256": "47be69831bc7b20a8ad6827bab67a14d599542fb57baf97b3e8a042862c4a9f0",
        "go": "complete_paired_dev_go",
        "no_go": "complete_paired_dev_no_go",
    },
    "scope_open": {
        "path": Path("outputs/v24105_scope_open_paired_dev_watcher_state_v1_20260729.json"),
        "role": "v24105_scope_open_paired_dev_watcher_state",
        "protocol_sha256": "a435bf2fb3ea08fa16feece631b35b51139c0134a965605987bc4e854ea3d6e9",
        "go": "complete_paired_dev_go",
        "no_go": "complete_paired_dev_no_go",
        "parent_no_go": "complete_parent_v24103_no_go_no_p12_3_api",
    },
    "entropy_credit": {
        "path": Path(
            "outputs/v24193_replicate_aware_gate2a_consumer_state_v1_20260731.json"
        ),
        "role": "v24193_replicate_aware_gate2a_consumer_state",
        "protocol_path": (
            "results/v24193_replicate_aware_gate2a_consumer_preregistration_v1_20260731.json"
        ),
        "protocol_sha256": "9b2fcf677bbb4f7cdb361d689f2634b23326d1cb640416eee920fb2b131b6031",
        "go": "replicate_aware_gate2a_pass",
        "no_go": ("replicate_aware_gate2a_fail", "replicate_aware_gate2a_not_evaluable"),
    },
}

ENTROPY_ROOT_SOURCE = {
    "path": Path("outputs/v24190_tie_aware_gate2a_consumer_state_v1_20260730.json"),
    "role": "v24190_tie_aware_gate2a_consumer_state",
    "protocol_path": "results/v24190_tie_aware_gate2a_consumer_preregistration_v1_20260730.json",
    "protocol_sha256": "e978988b6a7617bba702ced578cf1eb47fc0392a32fc7298ae136add922927ac",
    "terminal_no_report_sources": (
        "gate1_no_go_true_continuation_not_launched",
        "capture_attempt_failed_no_api_reissue",
        "fit_calibration_model_support_no_go",
    ),
}

BASELINE_PUBLICATIONS = {
    "schema76": {
        "path": "results/v24154_scope_combined_execution_candidate_publication_v1_20260729.json",
        "sha256": "0cd2c47af0f4dfbb3cc0f2b3fdc80182a48037e5936bd0a41082a8f63c2f29f1",
        "pipeline_branch": "schema76",
        "state_schema_version": 76,
        "mechanisms": ["v24108", "v24127", "v24132", "v24144", "v24104"],
    },
    "schema77": {
        "path": "results/v24175_predicate_completion_execution_candidate_publication_v1_20260730.json",
        "sha256": "139780e26566ac8d0fbd3328dafad05652552048e99330d39bb00bf8f7d77e5e",
        "pipeline_branch": "schema77",
        "state_schema_version": 77,
        "mechanisms": [
            "v24108",
            "v24127",
            "v24132",
            "v24144",
            "v24104",
            "v24172",
        ],
    },
}

FEATURE_ORDER = ("schema77", "search_yield", "markdown", "scope_open", "entropy_credit")
MARKDOWN_LEVELS = ("none", "markdown", "markdown_scope")
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_SLOT = re.compile(r"slot_schema7[67]_(?:plain|markdown|markdown_scope)_(?:base|search)_(?:static|entropy)")
PUBLICATION_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "label_blind",
        "slot_name",
        "feature_vector",
        "baseline_publication",
        "included_integrations",
        "integration_receipts",
        "merge_audit",
        "all_required_integrations_present",
        "merge_conflict",
        "candidate_build_performed_by_selector",
        "target_name",
        "pipeline_version",
        "state_schema_version",
        "candidate_method_contract_sha256",
        "candidate_regular_file_manifest_sha256",
        "canonical_all220_integrated_freezes_ready",
        "benchmark_forward_launch_allowed",
        "mapping_gold_category_question_type_evaluator_score_read_by_selector_runtime",
        "publication_payload_sha256",
    }
)
HANDOFF_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "label_blind",
        "slot_name",
        "feature_vector",
        "selector_protocol",
        "candidate_publication",
        "included_integrations",
        "all_required_integrations_present",
        "merge_conflict",
        "candidate_build_performed_by_selector",
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
INTEGRATION_RECEIPT_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "label_blind",
        "slot_name",
        "feature_vector",
        "integration_id",
        "baseline_publication",
        "source_implementation_publication",
        "candidate_pipeline_version",
        "candidate_state_schema_version",
        "candidate_method_contract_sha256",
        "candidate_regular_file_manifest_sha256",
        "integration_hooks_present",
        "integration_tests",
        "merge_conflict",
        "candidate_build_performed_by_selector",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_forward_launch_allowed",
        "mapping_gold_category_question_type_evaluator_score_read",
        "receipt_payload_sha256",
    }
)
MERGE_AUDIT_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "label_blind",
        "slot_name",
        "feature_vector",
        "baseline_publication",
        "candidate_pipeline_version",
        "candidate_state_schema_version",
        "candidate_method_contract_sha256",
        "candidate_regular_file_manifest_sha256",
        "integration_receipts",
        "all_required_integrations_present",
        "conflict_count",
        "regression_tests",
        "candidate_build_performed_by_selector",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_forward_launch_allowed",
        "mapping_gold_category_question_type_evaluator_score_read",
        "merge_audit_payload_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _without(value: dict[str, Any], key: str) -> dict[str, Any]:
    return {name: item for name, item in value.items() if name != key}


def _bytes_snapshot(path: Path) -> tuple[bytes, str]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError("V2.41.99 source is not an ordinary file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    payload = b"".join(chunks)
    if identity_before != identity_after or len(payload) != before.st_size:
        raise RuntimeError("V2.41.99 source changed during snapshot")
    return payload, hashlib.sha256(payload).hexdigest()


def object_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    payload, digest = _bytes_snapshot(path)
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("V2.41.99 source is not one UTF-8 JSON object") from exc
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.99 source is not one JSON object")
    return value, digest


def method_contract_from_freeze(freeze: dict[str, Any]) -> str:
    """Derive the worker-independent candidate method identity."""

    runtime = freeze.get("runtime") or {}
    return payload_sha256(
        {
            "pipeline_version": freeze.get("pipeline_version"),
            "state_schema_version": freeze.get("state_schema_version"),
            "manifest": freeze.get("manifest"),
            "manifest_sha256": freeze.get("manifest_sha256"),
            "code_sha256": freeze.get("code_sha256"),
            "model": freeze.get("model"),
            "search": freeze.get("search"),
            "runtime_without_workers": {
                key: value
                for key, value in runtime.items()
                if key not in {"candidate_model_workers", "row_model_workers"}
            },
        }
    )


def _result_reference(root: Path, value: object) -> tuple[dict[str, str], Path]:
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "sha256"}
        or not isinstance(value.get("path"), str)
        or Path(value["path"]).is_absolute()
        or ".." in Path(value["path"]).parts
        or Path(value["path"]).parts[0] != "results"
        or SHA256.fullmatch(str(value.get("sha256", ""))) is None
    ):
        raise RuntimeError("V2.41.99 result reference is invalid")
    path = root / value["path"]
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or v24197_bytes_snapshot(path)[1] != value["sha256"]
    ):
        raise RuntimeError("V2.41.99 result reference drifted")
    return {"path": value["path"], "sha256": value["sha256"]}, path


def build_slot_manifest() -> dict[str, Any]:
    """Enumerate every legal terminal feature vector before outcomes exist."""

    slots: dict[str, Any] = {}
    for schema77 in (False, True):
        for search_yield in (False, True):
            for markdown_level in MARKDOWN_LEVELS:
                for entropy_credit in (False, True):
                    vector = {
                        "schema77": schema77,
                        "search_yield": search_yield,
                        "markdown": markdown_level != "none",
                        "scope_open": markdown_level == "markdown_scope",
                        "entropy_credit": entropy_credit,
                    }
                    name = (
                        f"slot_schema{'77' if schema77 else '76'}_"
                        f"{'plain' if markdown_level == 'none' else markdown_level}_"
                        f"{'search' if search_yield else 'base'}_"
                        f"{'entropy' if entropy_credit else 'static'}"
                    )
                    slots[name] = {
                        "feature_vector": vector,
                        "baseline_publication": BASELINE_PUBLICATIONS[
                            "schema77" if schema77 else "schema76"
                        ],
                        "required_integrations": [
                            name
                            for name, enabled in (
                                ("predicate_completion", schema77),
                                ("search_yield_shared_query", search_yield),
                                ("markdown_rank_slot", vector["markdown"]),
                                ("scope_open_fallback", vector["scope_open"]),
                                ("entropy_credit_controller", entropy_credit),
                            )
                            if enabled
                        ],
                        "candidate_publication_path": (
                            f"results/v24199_integrated_candidates/{name}/candidate_publication.json"
                        ),
                        "candidate_handoff_path": (
                            f"results/v24199_integrated_candidates/{name}/candidate_handoff.json"
                        ),
                        "candidate_build_or_fallback_allowed_by_selector": False,
                    }
    if len(slots) != 24 or len({payload_sha256(row["feature_vector"]) for row in slots.values()}) != 24:
        raise AssertionError("V2.41.99 slot manifest is not bijective")
    return slots


def slot_for_vector(slots: dict[str, Any], vector: dict[str, bool]) -> str:
    matches = [name for name, row in slots.items() if row.get("feature_vector") == vector]
    if len(matches) != 1:
        raise RuntimeError("V2.41.99 terminal feature vector has no unique slot")
    return matches[0]


def _protocol_binding(value: dict[str, Any], spec: dict[str, Any]) -> bool:
    if "protocol_path" in spec:
        return value.get("protocol") == {
            "path": spec["protocol_path"],
            "sha256": spec["protocol_sha256"],
            "decision_contract_sha256": value.get("protocol", {}).get(
                "decision_contract_sha256"
            ),
        }
    return value.get("protocol_sha256") == spec["protocol_sha256"]


def classify_quality_state(name: str, value: dict[str, Any]) -> str:
    """Return waiting/go/no_go using status strings and immutable bindings only."""

    spec = QUALITY_SOURCES[name]
    _reject_forbidden_metadata(value)
    if value.get("role") != spec["role"] or not _protocol_binding(value, spec):
        raise RuntimeError(f"V2.41.99 {name} quality envelope binding drifted")
    status = value.get("status")
    if not isinstance(status, str) or not status:
        raise RuntimeError(f"V2.41.99 {name} quality envelope lacks status")
    if name in {"schema77", "markdown", "scope_open"} and (
        value.get("test156_or_full220_launch_allowed") is not False
        or value.get("test156_or_full220_api_called") is not False
        or value.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError(f"V2.41.99 {name} quality authorization drifted")
    if name == "schema77" and (
        value.get("forward_resume_used") is not False
        or value.get("selective_rerun_used") is not False
    ):
        raise RuntimeError("V2.41.99 schema77 rerun authorization drifted")
    if name == "search_yield" and (
        value.get("benchmark_forward_called") is not False
        or value.get("resume_or_selective_rerun_used") is not False
        or value.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.41.99 search-yield authorization drifted")
    if name == "entropy_credit":
        if status == spec["go"]:
            if (
                value.get("terminal") is not True
                or value.get("replicate_aware_gate2a_evaluated") is not True
                or value.get("replicate_aware_gate2a_passed") is not True
                or value.get("controller_design_allowed") is not True
                or value.get("controller_implementation_or_pilot_launch_allowed") is not False
                or value.get("training_credit_allowed") is not False
                or value.get("full220_controller_launch_allowed") is not False
            ):
                raise RuntimeError("V2.41.99 entropy-credit GO envelope is invalid")
            return "go"
        if status in spec["no_go"]:
            if (
                value.get("terminal") is not True
                or value.get("replicate_aware_gate2a_evaluated") is not True
                or value.get("replicate_aware_gate2a_passed") is not False
            ):
                raise RuntimeError("V2.41.99 entropy-credit NO-GO envelope is invalid")
            return "no_go"
        if value.get("terminal") is True:
            raise RuntimeError("V2.41.99 entropy-credit terminal status is unregistered")
        return "waiting"
    if status == spec["go"]:
        return "go"
    if status == spec["no_go"] or status == spec.get("terminal_no_go"):
        return "no_go"
    if status == spec.get("parent_no_go"):
        return "no_go"
    if status.startswith("complete") or status.startswith("terminal"):
        raise RuntimeError(f"V2.41.99 {name} terminal status is unregistered")
    return "waiting"


def classify_entropy_chain(
    final_value: dict[str, Any], root_value: dict[str, Any]
) -> str:
    """Use V2.41.90 only for its registered terminal-without-report closure."""

    _reject_forbidden_metadata(root_value)
    root_protocol = root_value.get("protocol") or {}
    if (
        root_value.get("role") != ENTROPY_ROOT_SOURCE["role"]
        or root_protocol.get("path") != ENTROPY_ROOT_SOURCE["protocol_path"]
        or root_protocol.get("sha256") != ENTROPY_ROOT_SOURCE["protocol_sha256"]
    ):
        raise RuntimeError("V2.41.99 entropy root envelope binding drifted")
    if root_value.get("terminal") is True:
        if root_value.get("tie_aware_gate2a_evaluated") is True:
            return classify_quality_state("entropy_credit", final_value)
        if (
            root_value.get("status") == "waiting_for_true_continuation_audit_terminal"
            and root_value.get("source_terminal") is True
            and root_value.get("source_status")
            in ENTROPY_ROOT_SOURCE["terminal_no_report_sources"]
            and root_value.get("tie_aware_gate2a_passed") is False
            and root_value.get("controller_design_allowed") is False
        ):
            return "no_go"
        raise RuntimeError("V2.41.99 entropy root terminal is unregistered")
    return classify_quality_state("entropy_credit", final_value)


def derive_terminal_vector(
    states: dict[str, dict[str, Any]], *, entropy_root: dict[str, Any]
) -> tuple[dict[str, bool] | None, dict[str, str]]:
    if set(states) != set(QUALITY_SOURCES):
        raise RuntimeError("V2.41.99 quality source set drifted")
    statuses = {
        name: classify_quality_state(name, states[name])
        for name in QUALITY_SOURCES
        if name != "entropy_credit"
    }
    statuses["entropy_credit"] = classify_entropy_chain(
        states["entropy_credit"], entropy_root
    )
    if any(status == "waiting" for status in statuses.values()):
        return None, statuses
    if statuses["scope_open"] == "go" and statuses["markdown"] != "go":
        raise RuntimeError("V2.41.99 scope-open GO lacks Markdown GO parent")
    vector = {name: statuses[name] == "go" for name in FEATURE_ORDER}
    return vector, statuses


def validate_candidate_handoff(
    root: Path,
    *,
    slot_name: str,
    slot: dict[str, Any],
    selector_protocol_sha256: str,
    capacity: dict[str, int],
    capacity_freeze: dict[str, Any],
) -> dict[str, Any]:
    """Validate the slot publisher's V2.41.98-shaped handoff without building it."""

    if SAFE_SLOT.fullmatch(slot_name) is None:
        raise RuntimeError("V2.41.99 slot name is invalid")
    publication_path = root / slot["candidate_publication_path"]
    handoff_path = root / slot["candidate_handoff_path"]
    publication, publication_sha = object_snapshot(publication_path)
    handoff, handoff_sha = object_snapshot(handoff_path)
    vector = slot["feature_vector"]
    required = slot["required_integrations"]
    receipts = publication.get("integration_receipts")
    merge_audit = publication.get("merge_audit")
    if (
        set(publication) != PUBLICATION_FIELDS
        or publication.get("artifact_version") != 1
        or publication.get("role") != "v24199_integrated_candidate_publication"
        or isinstance(publication.get("created_at_unix"), bool)
        or not isinstance(publication.get("created_at_unix"), int)
        or publication.get("label_blind") is not True
        or publication.get("slot_name") != slot_name
        or publication.get("feature_vector") != vector
        or publication.get("baseline_publication") != slot["baseline_publication"]
        or publication.get("included_integrations") != required
        or not isinstance(receipts, dict)
        or set(receipts) != set(required)
        or not isinstance(merge_audit, dict)
        or set(merge_audit) != {"path", "sha256"}
        or publication.get("all_required_integrations_present") is not True
        or publication.get("merge_conflict") is not False
        or publication.get("candidate_build_performed_by_selector") is not False
        or not isinstance(publication.get("target_name"), str)
        or not publication.get("target_name")
        or not isinstance(publication.get("pipeline_version"), str)
        or not publication.get("pipeline_version")
        or isinstance(publication.get("state_schema_version"), bool)
        or not isinstance(publication.get("state_schema_version"), int)
        or publication.get("state_schema_version", 0) <= 0
        or SHA256.fullmatch(
            str(publication.get("candidate_method_contract_sha256", ""))
        )
        is None
        or SHA256.fullmatch(
            str(publication.get("candidate_regular_file_manifest_sha256", ""))
        )
        is None
        or publication.get("canonical_all220_integrated_freezes_ready") is not True
        or publication.get("benchmark_forward_launch_allowed") is not False
        or publication.get(
            "mapping_gold_category_question_type_evaluator_score_read_by_selector_runtime"
        )
        is not False
        or publication.get("publication_payload_sha256")
        != payload_sha256(_without(publication, "publication_payload_sha256"))
    ):
        raise RuntimeError("V2.41.99 integrated candidate publication is invalid")
    evidence_paths: set[str] = set()
    receipt_values: dict[str, dict[str, Any]] = {}
    for integration_id, reference in receipts.items():
        normalized_reference, evidence_path = _result_reference(root, reference)
        if normalized_reference["path"] in evidence_paths:
            raise RuntimeError("V2.41.99 integration evidence is reused")
        evidence_paths.add(normalized_reference["path"])
        receipt, _ = object_snapshot(evidence_path)
        tests = receipt.get("integration_tests") or {}
        source_publication = receipt.get("source_implementation_publication")
        if (
            set(receipt) != INTEGRATION_RECEIPT_FIELDS
            or receipt.get("artifact_version") != 1
            or receipt.get("role") != "v24199_candidate_integration_receipt"
            or isinstance(receipt.get("created_at_unix"), bool)
            or not isinstance(receipt.get("created_at_unix"), int)
            or receipt.get("label_blind") is not True
            or receipt.get("slot_name") != slot_name
            or receipt.get("feature_vector") != vector
            or receipt.get("integration_id") != integration_id
            or receipt.get("baseline_publication") != slot["baseline_publication"]
            or not isinstance(source_publication, dict)
            or set(source_publication) != {"path", "sha256"}
            or receipt.get("candidate_pipeline_version")
            != publication["pipeline_version"]
            or receipt.get("candidate_state_schema_version")
            != publication["state_schema_version"]
            or receipt.get("candidate_method_contract_sha256")
            != publication["candidate_method_contract_sha256"]
            or receipt.get("candidate_regular_file_manifest_sha256")
            != publication["candidate_regular_file_manifest_sha256"]
            or receipt.get("integration_hooks_present") is not True
            or set(tests) != {"status", "tests_run", "tests_failed"}
            or tests.get("status") != "pass"
            or isinstance(tests.get("tests_run"), bool)
            or not isinstance(tests.get("tests_run"), int)
            or tests.get("tests_run", 0) <= 0
            or tests.get("tests_failed") != 0
            or receipt.get("merge_conflict") is not False
            or receipt.get("candidate_build_performed_by_selector") is not False
            or receipt.get("network_model_search_fetch_evaluator_or_api_called")
            is not False
            or receipt.get("benchmark_forward_launch_allowed") is not False
            or receipt.get(
                "mapping_gold_category_question_type_evaluator_score_read"
            )
            is not False
            or receipt.get("receipt_payload_sha256")
            != payload_sha256(_without(receipt, "receipt_payload_sha256"))
        ):
            raise RuntimeError("V2.41.99 integration receipt is invalid")
        _result_reference(root, source_publication)
        receipt_values[integration_id] = receipt
    normalized_merge, merge_path = _result_reference(root, merge_audit)
    if normalized_merge["path"] in evidence_paths:
        raise RuntimeError("V2.41.99 merge evidence is reused")
    merge_value, _ = object_snapshot(merge_path)
    regression = merge_value.get("regression_tests") or {}
    if (
        set(merge_value) != MERGE_AUDIT_FIELDS
        or merge_value.get("artifact_version") != 1
        or merge_value.get("role") != "v24199_candidate_merge_audit"
        or isinstance(merge_value.get("created_at_unix"), bool)
        or not isinstance(merge_value.get("created_at_unix"), int)
        or merge_value.get("label_blind") is not True
        or merge_value.get("slot_name") != slot_name
        or merge_value.get("feature_vector") != vector
        or merge_value.get("baseline_publication") != slot["baseline_publication"]
        or merge_value.get("candidate_pipeline_version")
        != publication["pipeline_version"]
        or merge_value.get("candidate_state_schema_version")
        != publication["state_schema_version"]
        or merge_value.get("candidate_method_contract_sha256")
        != publication["candidate_method_contract_sha256"]
        or merge_value.get("candidate_regular_file_manifest_sha256")
        != publication["candidate_regular_file_manifest_sha256"]
        or merge_value.get("integration_receipts") != receipts
        or merge_value.get("all_required_integrations_present") is not True
        or merge_value.get("conflict_count") != 0
        or set(regression) != {"status", "tests_run", "tests_failed"}
        or regression.get("status") != "pass"
        or isinstance(regression.get("tests_run"), bool)
        or not isinstance(regression.get("tests_run"), int)
        or regression.get("tests_run", 0) <= 0
        or regression.get("tests_failed") != 0
        or merge_value.get("candidate_build_performed_by_selector") is not False
        or merge_value.get("network_model_search_fetch_evaluator_or_api_called")
        is not False
        or merge_value.get("benchmark_forward_launch_allowed") is not False
        or merge_value.get(
            "mapping_gold_category_question_type_evaluator_score_read"
        )
        is not False
        or merge_value.get("merge_audit_payload_sha256")
        != payload_sha256(_without(merge_value, "merge_audit_payload_sha256"))
    ):
        raise RuntimeError("V2.41.99 merge audit is invalid")
    selector = {
        "path": "results/v24198_selected_candidate_selector_preregistration_v1_20260731.json",
        "sha256": selector_protocol_sha256,
    }
    if (
        set(handoff) != HANDOFF_FIELDS
        or handoff.get("artifact_version") != 1
        or handoff.get("role") != "v24199_integrated_candidate_handoff"
        or isinstance(handoff.get("created_at_unix"), bool)
        or not isinstance(handoff.get("created_at_unix"), int)
        or handoff.get("created_at_unix", -1) < publication.get("created_at_unix", 0)
        or handoff.get("label_blind") is not True
        or handoff.get("slot_name") != slot_name
        or handoff.get("feature_vector") != vector
        or handoff.get("selector_protocol") != selector
        or handoff.get("candidate_publication")
        != {"path": slot["candidate_publication_path"], "sha256": publication_sha}
        or handoff.get("included_integrations") != required
        or handoff.get("all_required_integrations_present") is not True
        or handoff.get("merge_conflict") is not False
        or handoff.get("candidate_build_performed_by_selector") is not False
        or handoff.get("target_name") != publication.get("target_name")
        or handoff.get("pipeline_version") != publication.get("pipeline_version")
        or handoff.get("state_schema_version")
        != publication.get("state_schema_version")
        or handoff.get("candidate_method_contract_sha256")
        != publication.get("candidate_method_contract_sha256")
        or handoff.get("shard_order")
        != ["test_s01", "test_s02", "test_s03", "devval"]
        or not isinstance(handoff.get("shards"), dict)
        or set(handoff.get("shards") or {})
        != {"test_s01", "test_s02", "test_s03", "devval"}
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
        or handoff.get("handoff_payload_sha256")
        != payload_sha256(_without(handoff, "handoff_payload_sha256"))
    ):
        raise RuntimeError("V2.41.99 integrated candidate handoff is invalid")
    expected_model = {
        "endpoint": capacity_freeze["endpoint"],
        "name": capacity_freeze["model"],
        "reasoning_effort": capacity_freeze["reasoning_effort"],
        "service_tier": capacity_freeze["service_tier"],
    }
    if handoff.get("model") != expected_model:
        raise RuntimeError("V2.41.99 candidate model is not capacity-bound")
    rows = handoff["shards"]
    freeze_paths: set[str] = set()
    output_paths: set[str] = set()
    stable: dict[str, Any] | None = None
    normalized: dict[str, Any] = {}
    observed_method_contract: str | None = None
    for tag in EXPECTED_SHARDS:
        row = rows[tag]
        if not isinstance(row, dict) or set(row) != {
            "freeze",
            "selected_ids",
            "output_directory",
        }:
            raise RuntimeError("V2.41.99 candidate shard row is invalid")
        freeze_ref = row["freeze"]
        if (
            not isinstance(freeze_ref, dict)
            or set(freeze_ref) != {"path", "sha256"}
            or not isinstance(freeze_ref.get("path"), str)
            or Path(freeze_ref["path"]).is_absolute()
            or ".." in Path(freeze_ref["path"]).parts
            or Path(freeze_ref["path"]).parts[0] != "configs"
            or SHA256.fullmatch(str(freeze_ref.get("sha256", ""))) is None
            or freeze_ref["path"] in freeze_paths
        ):
            raise RuntimeError("V2.41.99 candidate freeze reference is invalid")
        freeze_path = root / freeze_ref["path"]
        freeze, freeze_sha = v24197_object_snapshot(freeze_path)
        if freeze_sha != freeze_ref["sha256"]:
            raise RuntimeError("V2.41.99 candidate freeze drifted")
        freeze_paths.add(freeze_ref["path"])
        if row["selected_ids"] != CANONICAL_ID_FILES[tag]:
            raise RuntimeError("V2.41.99 candidate IDs are not canonical")
        ids_path = root / CANONICAL_ID_FILES[tag]["path"]
        if (
            ids_path.is_symlink()
            or not ids_path.is_file()
            or v24197_bytes_snapshot(ids_path)[1]
            != CANONICAL_ID_FILES[tag]["sha256"]
            or CANONICAL_ID_FILES[tag]["count"] != EXPECTED_COUNTS[tag]
        ):
            raise RuntimeError("V2.41.99 canonical ID file drifted")
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
            raise RuntimeError("V2.41.99 candidate output root is not fresh")
        output_paths.add(output)
        model = freeze.get("model") or {}
        runtime = freeze.get("runtime") or {}
        manifest_path = _workspace_file(
            root, freeze.get("manifest"), allowed_prefixes=("configs", "data")
        )
        code = freeze.get("code_sha256")
        if (
            freeze.get("pipeline_version") != publication["pipeline_version"]
            or freeze.get("state_schema_version")
            != publication["state_schema_version"]
            or freeze.get("selected_ids_file") != CANONICAL_ID_FILES[tag]["path"]
            or freeze.get("selected_ids_sha256")
            != CANONICAL_ID_FILES[tag]["sha256"]
            or freeze.get("selected_count") != EXPECTED_COUNTS[tag]
            or freeze.get("manifest_sha256")
            != v24197_bytes_snapshot(manifest_path)[1]
            or not isinstance(code, dict)
            or not code
            or any(
                not isinstance(digest, str)
                or SHA256.fullmatch(digest) is None
                or v24197_bytes_snapshot(
                    _workspace_file(
                        root, relative, allowed_prefixes=("src", "scripts")
                    )
                )[1]
                != digest
                for relative, digest in code.items()
            )
            or model.get("proxy_url") != capacity_freeze["endpoint"]
            or model.get("name") != capacity_freeze["model"]
            or model.get("reasoning_effort") != capacity_freeze["reasoning_effort"]
            or model.get("service_tier") != capacity_freeze["service_tier"]
            or runtime.get("candidate_model_workers") != capacity["workers"]
            or runtime.get("row_model_workers") != capacity["workers"]
        ):
            raise RuntimeError("V2.41.99 candidate freeze violates integration or capacity binding")
        stable_row = {
            "pipeline_version": freeze.get("pipeline_version"),
            "state_schema_version": freeze.get("state_schema_version"),
            "manifest": freeze.get("manifest"),
            "manifest_sha256": freeze.get("manifest_sha256"),
            "code_sha256": code,
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
        elif stable != stable_row:
            raise RuntimeError("V2.41.99 candidate shards are not one frozen method")
        method_contract = method_contract_from_freeze(freeze)
        if observed_method_contract is None:
            observed_method_contract = method_contract
        elif observed_method_contract != method_contract:
            raise RuntimeError("V2.41.99 candidate method contract differs by shard")
        normalized[tag] = {
            "freeze": dict(freeze_ref),
            "selected_ids": dict(row["selected_ids"]),
            "output_directory": output,
        }
    if observed_method_contract != publication["candidate_method_contract_sha256"]:
        raise RuntimeError("V2.41.99 candidate method contract is not freeze-derived")
    return {
        "slot_name": slot_name,
        "feature_vector": vector,
        "publication": {
            "path": slot["candidate_publication_path"],
            "sha256": publication_sha,
        },
        "handoff": {"path": slot["candidate_handoff_path"], "sha256": handoff_sha},
        "created_at_unix": handoff["created_at_unix"],
        "target_name": handoff.get("target_name"),
        "pipeline_version": handoff.get("pipeline_version"),
        "state_schema_version": handoff.get("state_schema_version"),
        "candidate_method_contract_sha256": handoff.get(
            "candidate_method_contract_sha256"
        ),
        "model": handoff.get("model"),
        "shards": normalized,
    }
