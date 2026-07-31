#!/usr/bin/env python3
"""Publish the V2.42.03 outcome-independent materialization audit.

This audit reads only frozen protocols/publications and the V2.42.01 byte-exact
receipt.  It never reads live status envelopes, task state, benchmark content,
predictions, evaluator artifacts, metrics, credentials, or network services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import (  # noqa: E402
    BASELINES,
    build_decision_manifest,
    payload_sha256 as v24200_payload_sha256,
)
from deepwide_agent.v24203_materialization_audit import (  # noqa: E402
    build_materialization_manifest,
    payload_sha256,
)


OUTPUT = Path(
    "results/v24203_successor_materialization_audit_v1_20260731.json"
)
V24200_PROTOCOL = Path(
    "results/v24200_hierarchical_successor_preregistration_v1_20260731.json"
)
V24200_PROTOCOL_SHA256 = (
    "d04d64ae2d05dc3daa934cc92a292b8541dce565e948df10c292a815b6a92ae3"
)
V24201_RECEIPT = Path(
    "results/v24201_repo_local_candidate_dag_replay_v1_20260731.json"
)
V24201_RECEIPT_SHA256 = (
    "cee95e892c1aa2e80dbcc70bac5f426e7f66a7e023c14554a63e42878bdb2a6f"
)
SEARCH_PROTOCOL = Path(
    "results/v24180_predicate_search_yield_preregistration_v1_20260730.json"
)
SEARCH_PROTOCOL_SHA256 = (
    "1274fe4a9b7801d96dd5265443cb3f6b837edd469be3fe85bef1c3d71ebdf5e4"
)
MARKDOWN_PUBLICATION = Path(
    "results/v24102_markdown_execution_candidate_publication_v1_20260728.json"
)
MARKDOWN_PUBLICATION_SHA256 = (
    "a16c3eb8b218478dd58246f1e7016f982732e689f8630f700daa5609e1ea9b3a"
)
SCOPE_PUBLICATION = Path(
    "results/v24104_scope_open_execution_candidate_publication_v1_20260729.json"
)
SCOPE_PUBLICATION_SHA256 = (
    "10cf31d7c6eaa812b420dfb08fd4bb9dba4cfd3da2a06761018923d522bb5154"
)
ENTROPY_PROTOCOL = Path(
    "results/v24193_replicate_aware_gate2a_consumer_preregistration_v1_20260731.json"
)
ENTROPY_PROTOCOL_SHA256 = (
    "9b2fcf677bbb4f7cdb361d689f2634b23326d1cb640416eee920fb2b131b6031"
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordinary(root: Path, relative: Path, digest: str) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.03 input path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
        or file_sha256(path) != digest
    ):
        raise RuntimeError(f"V2.42.03 frozen input drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.03 expected one JSON object")
    return value


def _manifest(value: dict[str, Any]) -> dict[str, str]:
    direct = value.get("candidate_regular_file_manifest")
    if isinstance(direct, dict):
        result = dict(sorted((str(key), str(item)) for key, item in direct.items()))
    else:
        generated = value.get("generated_file_manifest")
        support = value.get("support_file_manifest")
        if not isinstance(generated, dict) or not isinstance(support, dict):
            raise RuntimeError("V2.42.03 publication manifest is absent")
        result = dict(
            sorted(
                (str(key), str(item))
                for key, item in {**generated, **support}.items()
            )
        )
    if (
        len(result) != value.get("candidate_regular_file_count")
        or payload_sha256(result)
        != value.get("candidate_regular_file_manifest_sha256")
    ):
        raise RuntimeError("V2.42.03 publication manifest is internally invalid")
    return result


def _publication(
    root: Path,
    path: Path,
    digest: str,
    *,
    role: str,
    schema: int,
) -> tuple[dict[str, Any], dict[str, str]]:
    value = read_object(ordinary(root, path, digest))
    if (
        value.get("role") != role
        or value.get("target_state_schema_version") != schema
        or value.get("build_only") is not True
        or value.get("label_blind") is not True
        or value.get("api_or_benchmark_forward_called") is not False
        or value.get("full220_launch_allowed", False) is not False
        or value.get("paired_dev_or_full220_launch_allowed", False) is not False
        or value.get("mapping_gold_category_evaluator_score_or_outcome_read")
        is not False
    ):
        raise RuntimeError(f"V2.42.03 publication authorization drifted: {path}")
    return value, _manifest(value)


def _validate_v24200(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = read_object(
        ordinary(root, V24200_PROTOCOL, V24200_PROTOCOL_SHA256)
    )
    manifest = build_decision_manifest()
    component = protocol.get("component_contract") or {}
    authorization = protocol.get("authorization") or {}
    if (
        protocol.get("role") != "v24200_hierarchical_successor_preregistration"
        or protocol.get("protocol_id")
        != "v24200_hierarchical_baseline_integrated_package_gate_v1"
        or protocol.get("label_blind") is not True
        or component.get("terminal_package_count") != 36
        or component.get("decision_manifest_sha256")
        != v24200_payload_sha256(manifest)
        or component.get("independent_go_does_not_prove_union_package") is not True
        or component.get("nonempty_component_set_requires_new_package_gate")
        is not True
        or component.get("empty_component_set_uses_selected_baseline_identity_handoff")
        is not True
        or authorization.get("candidate_code_build_merge_or_freeze_generation")
        is not False
        or authorization.get("package_gate_evaluation_or_launch") is not False
        or authorization.get("benchmark_forward_or_full220_launch") is not False
    ):
        raise RuntimeError("V2.42.03 V2.42.00 contract drifted")
    return protocol, manifest


def _validate_v24201(root: Path) -> dict[str, Any]:
    receipt = read_object(ordinary(root, V24201_RECEIPT, V24201_RECEIPT_SHA256))
    unsigned = dict(receipt)
    seal = unsigned.pop("replay_payload_sha256", None)
    if (
        receipt.get("role") != "v24201_repo_local_candidate_dag_replay"
        or receipt.get("label_blind") is not True
        or receipt.get("build_only") is not True
        or receipt.get("all_stage_file_maps_byte_exact_to_frozen_publications")
        is not True
        or receipt.get("sibling_candidate_tree_read") is not False
        or receipt.get("candidate_tree_materialized") is not False
        or receipt.get("runtime_task_state_prediction_or_result_read") is not False
        or receipt.get("mapping_gold_category_question_type_evaluator_score_read")
        is not False
        or receipt.get("network_model_search_fetch_evaluator_or_api_called")
        is not False
        or receipt.get("benchmark_forward_or_full220_launch_allowed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.03 V2.42.01 receipt drifted")
    stage_for = {"p12": "schema68", "schema76": "schema76", "schema77": "schema77"}
    stages = receipt.get("stages") or {}
    for name, publication in BASELINES.items():
        path = Path(publication["path"])
        ordinary(root, path, publication["sha256"])
        value = read_object(root / path)
        manifest_sha = payload_sha256(_manifest(value))
        stage = stages.get(stage_for[name]) or {}
        if (
            stage.get("byte_exact") is not True
            or stage.get("manifest_sha256") != manifest_sha
            or stage.get("state_schema_version")
            != publication["state_schema_version"]
        ):
            raise RuntimeError(f"V2.42.03 {name} byte-exact baseline drifted")
    return receipt


def _validate_component_sources(root: Path) -> dict[str, Any]:
    search = read_object(ordinary(root, SEARCH_PROTOCOL, SEARCH_PROTOCOL_SHA256))
    markdown, markdown_manifest = _publication(
        root,
        MARKDOWN_PUBLICATION,
        MARKDOWN_PUBLICATION_SHA256,
        role="v24102_markdown_rank_slot_execution_candidate_publication",
        schema=69,
    )
    scope, scope_manifest = _publication(
        root,
        SCOPE_PUBLICATION,
        SCOPE_PUBLICATION_SHA256,
        role="v24104_scope_open_execution_candidate_publication",
        schema=70,
    )
    entropy = read_object(ordinary(root, ENTROPY_PROTOCOL, ENTROPY_PROTOCOL_SHA256))
    if (
        search.get("role") != "v24180_predicate_search_yield_preregistration"
        or search.get("label_blind") is not True
        or search.get("paired_gate", {}).get("go_effect")
        != (
            "permits design/build-only integration of shared-query scheduler "
            "after schema77; does not authorize dev64, test156, full220, or "
            "leaderboard launch"
        )
        or search.get("authorization", {}).get("candidate_build") is not False
        or search.get("authorization", {}).get("dev64_test156_or_full220")
        is not False
        or search.get("api_model_search_fetch_or_benchmark_forward_called")
        is not False
    ):
        raise RuntimeError("V2.42.03 search component authority drifted")
    entropy_authorization = entropy.get("authorization") or {}
    if (
        entropy.get("role")
        != "v24193_replicate_aware_gate2a_consumer_preregistration"
        or entropy.get("label_blind_before_parent_terminal") is not True
        or entropy_authorization.get("controller_implementation_or_pilot_launch")
        is not False
        or entropy_authorization.get("training_credit") is not False
        or entropy_authorization.get("full220_controller_launch") is not False
    ):
        raise RuntimeError("V2.42.03 entropy implementation authority drifted")
    return {
        "search_yield_shared_query": {
            "source": {"path": str(SEARCH_PROTOCOL), "sha256": SEARCH_PROTOCOL_SHA256},
            "historical_publication_available": False,
            "current_authority": "design_build_only_after_go",
            "selected_baseline_publication_available": False,
        },
        "markdown_rank_slot": {
            "source": {
                "path": str(MARKDOWN_PUBLICATION),
                "sha256": MARKDOWN_PUBLICATION_SHA256,
                "manifest_sha256": payload_sha256(markdown_manifest),
            },
            "historical_publication_available": True,
            "historical_parent_schema": 68,
            "selected_baseline_rebase_publication_available": False,
        },
        "markdown_branch_scope_open_fallback": {
            "source": {
                "path": str(SCOPE_PUBLICATION),
                "sha256": SCOPE_PUBLICATION_SHA256,
                "manifest_sha256": payload_sha256(scope_manifest),
            },
            "historical_publication_available": True,
            "historical_parent_schema": 69,
            "selected_baseline_rebase_publication_available": False,
            "mainline_scope_and_markdown_branch_scope_must_remain_namespaced": True,
        },
        "entropy_credit_controller": {
            "source": {"path": str(ENTROPY_PROTOCOL), "sha256": ENTROPY_PROTOCOL_SHA256},
            "historical_publication_available": False,
            "controller_design_may_be_authorized_by_future_go": True,
            "controller_implementation_authority_available": False,
            "selected_baseline_publication_available": False,
        },
    }


def build_audit(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.03 may only audit the canonical workspace")
    protocol, decisions = _validate_v24200(root)
    replay = _validate_v24201(root)
    components = _validate_component_sources(root)
    materialization = build_materialization_manifest(decisions)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24203_successor_materialization_audit",
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "label_blind": True,
        "v24200_protocol": {
            "path": str(V24200_PROTOCOL),
            "sha256": V24200_PROTOCOL_SHA256,
            "decision_contract_sha256": protocol["decision_contract_sha256"],
            "decision_manifest_sha256": protocol["component_contract"][
                "decision_manifest_sha256"
            ],
        },
        "v24201_byte_exact_replay": {
            "path": str(V24201_RECEIPT),
            "sha256": V24201_RECEIPT_SHA256,
            "replay_payload_sha256": replay["replay_payload_sha256"],
            "baseline_stages": ["schema68", "schema76", "schema77"],
        },
        "component_sources": components,
        "materialization": materialization,
        "outcome_independent_all_36_decisions_classified": True,
        "identity_handoff_decision_count": 3,
        "blocked_nonempty_package_decision_count": 33,
        "any_nonempty_package_materializable_now": False,
        "decision_receipt_or_live_status_envelope_read": False,
        "runtime_task_state_prediction_or_result_read": False,
        "benchmark_question_answer_evidence_or_url_read": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "candidate_tree_or_package_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.03 output path is noncanonical")
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": file_sha256(target)}))


if __name__ == "__main__":
    main()
