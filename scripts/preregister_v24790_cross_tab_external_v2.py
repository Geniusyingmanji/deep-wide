#!/usr/bin/env python3
"""Corrected inert V2.47.90 protocol preserving full-target segmentation.

The V2.47.90 v1 protocol proposed rebuilding a one-target semantic catalog.
Static review before any integration, runner, lease, model, search, fetch, or
forward effect found that this would remove the other visible entities from
V2.43.65's segment-boundary set.  An adjacent entity relation could therefore
be rebound to the selected target.  V1 is retained as immutable history but
its integration-build authority is revoked by this successor.

V2 keeps the fully validated full-target catalog byte-for-byte intact.  A pure
adapter selects the first baseline Unknown in canonical row-major order, then
filters projection/support groups for that binding while preserving the full
catalog's original segmentation and source bindings.  Only fixed-vocabulary
selected-target counts may leave the child; full predictions remain unchanged.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24786_projection_support_cross_tab_observer as observer  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import preregister_v24790_cross_tab_external as v1  # noqa: E402


DATE = "20260807"
PROTOCOL_ID = "v24790_selected_unknown_cross_tab_external_v2"
OUTPUT = Path(f"results/v24790_cross_tab_external_preregistration_v2_{DATE}.json")
V1_PROTOCOL = v1.OUTPUT
SOURCE = Path("scripts/preregister_v24790_cross_tab_external_v2.py")
TEST = Path("tests/test_preregister_v24790_cross_tab_external_v2.py")
SEGMENT = Path("src/deepwide_agent/v24365_entity_segment_projection.py")
SEGMENT_TEST = Path("tests/test_v24365_entity_segment_projection.py")
DEPENDENCIES = (
    V1_PROTOCOL,
    Path("scripts/preregister_v24790_cross_tab_external.py"),
    Path("tests/test_preregister_v24790_cross_tab_external.py"),
    v1.POPULATION,
    v1.POPULATION_FREEZE_AUDIT,
    v1.VISIBLE_CONTRACT,
    v1.BASE_RUNTIME,
    v1.BASE_RUNTIME_TEST,
    v1.OBSERVER,
    v1.OBSERVER_TEST,
    SEGMENT,
    SEGMENT_TEST,
    SOURCE,
    TEST,
)
FUTURE_SURFACES = (
    OUTPUT,
    Path(f"results/v24790_cross_tab_integration_build_audit_v2_{DATE}.json"),
    Path(f"results/v24790_cross_tab_package_audit_v2_{DATE}.json"),
    Path(f"results/v24790_cross_tab_preactivation_audit_v2_{DATE}.json"),
    Path(f"results/v24790_cross_tab_activation_v2_{DATE}.json"),
    Path(f"results/v24790_cross_tab_execution_start_v2_{DATE}.json"),
    Path(f"results/v24790_cross_tab_forward_result_v2_{DATE}.json"),
    Path(f"results/v24790_cross_tab_forward_audit_v2_{DATE}.json"),
    Path(f"outputs/v24790_cross_tab_external_v2_{DATE}"),
)
V1_IMPLEMENTATION_SURFACES = (
    Path(f"results/v24790_cross_tab_integration_build_audit_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_package_audit_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_preactivation_audit_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_activation_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_execution_start_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_forward_result_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_forward_audit_v1_{DATE}.json"),
    Path(f"outputs/v24790_cross_tab_external_v1_{DATE}"),
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.90 v2 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.90 v2 expected JSON object")
    return value


def _tracked(relative: Path) -> Path:
    path = ROOT / relative
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0
    if (
        relative.is_absolute() or ".." in relative.parts
        or relative.parts[:1] in {("evaluation",), ("outputs",)}
        or path.is_symlink() or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve()) or not tracked
    ):
        raise RuntimeError(f"V2.47.90 v2 expected tracked public file: {relative}")
    return path


def dependency_manifest() -> dict[str, str]:
    return {str(path): sha256(_tracked(path)) for path in DEPENDENCIES}


def _v1() -> dict[str, Any]:
    value = _read(ROOT / V1_PROTOCOL)
    v1.validate_protocol(value)
    if (
        value.get("protocol_id") != v1.PROTOCOL_ID
        or value.get("authorization", {}).get(
            "append_only_trusted_child_integration_build"
        ) is not True
        or value.get("authorization", {}).get("one_external_forward_launch") is not False
        or not all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in V1_IMPLEMENTATION_SURFACES
        )
    ):
        raise RuntimeError("V2.47.90 v1 boundary drifted")
    return value


def build_protocol(*, now: int | None = None, require_clean: bool = True, require_pristine: bool = True) -> dict[str, Any]:
    if require_clean and (_git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")):
        raise RuntimeError("V2.47.90 v2 requires clean pushed HEAD")
    if require_pristine and any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in FUTURE_SURFACES):
        raise FileExistsError("V2.47.90 v2 future surface exists")
    prior = _v1()
    manifest = dependency_manifest()
    value = {
        "artifact_version": 2,
        "role": "v24790_cross_tab_external_preregistration_v2",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parent_v1": {
            "path": str(V1_PROTOCOL),
            "sha256": sha256(ROOT / V1_PROTOCOL),
            "protocol_id": prior["protocol_id"],
            "integration_build_authority_revoked_before_implementation": True,
            "runner_lease_model_search_fetch_or_forward_effect_before_revocation": False,
            "all_v1_implementation_and_execution_surfaces_pristine": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "unchanged_contract": {
            "population_sha256": prior["parents"]["population_design_sha256"],
            "population_freeze_audit_sha256": prior["parents"]["population_freeze_audit_sha256"],
            "visible_contract_sha256": prior["parents"]["visible_contract_sha256"],
            "task_contract": copy.deepcopy(prior["task_contract"]),
            "base_runtime_effect_envelope": copy.deepcopy(prior["base_runtime_effect_envelope"]),
            "forward_health_gate": copy.deepcopy(prior["forward_health_gate"]),
            "mechanism_gate_before_private_truth": copy.deepcopy(prior["mechanism_gate_before_private_truth"]),
            "entropy_credit_scope": copy.deepcopy(prior["entropy_credit_scope"]),
        },
        "v1_defect": {
            "defect_class": "selected_target_rebuild_changes_entity_segmentation_boundary_set",
            "one_target_catalog_rebuild_allowed": False,
            "full_target_catalog_required_for_segment_replay": True,
            "other_visible_entities_continue_to_delimit_selected_target_segments": True,
            "adjacent_entity_relation_may_be_rebound_if_boundaries_are_removed": True,
            "detected_before_integration_runner_or_external_effect": True,
        },
        "corrected_future_integration": {
            "implementation_status": "not_built",
            "ordered_steps": [
                "run_and_validate_v24778_base_once",
                "freeze_full_baseline_and_candidate_predictions",
                "validate_original_full_target_semantic_catalog",
                "select_first_baseline_unknown_in_canonical_row_major_order",
                "filter_selected_target_projection_support_and_change_groups_inside_full_catalog",
                "validate_fixed_v24786_compatible_selected_target_receipt",
                "emit_unchanged_full_predictions_plus_counts_only_selected_target_receipt",
            ],
            "full_target_catalog_or_original_projection_vector_mutated": False,
            "single_target_catalog_rebuilt": False,
            "maximum_selected_target_per_task": 1,
            "private_truth_quality_or_evaluator_used_for_selection": False,
            "additional_model_search_fetch_or_evaluator_effect": 0,
            "prediction_bytes_changed_by_observer": False,
            "selected_identity_field_value_host_page_prediction_or_private_hash_emitted": False,
            "positive_entropy_or_task_credit_assigned": False,
        },
        "selected_target_receipt_contract": {
            "base_schema_policy_id": observer.POLICY_ID,
            "fixed_catalog_dispositions": list(observer.CATALOG_DISPOSITIONS),
            "fixed_catalog_quarantine_dispositions": list(observer.CATALOG_QUARANTINE_DISPOSITIONS),
            "fixed_proposal_dispositions": list(observer.PROPOSAL_DISPOSITIONS),
            "fixed_group_change_dispositions": list(observer.GROUP_CHANGE_DISPOSITIONS),
            "target_count": 1,
            "unknown_target_count": 1,
            "target_and_group_partitions_exact": True,
            "strict_joint_requires_same_selected_target_value_group": True,
            "cross_task_or_cross_group_margins_used_as_joint": False,
        },
        "source_policy": {
            "v24784_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "v24789_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_publication": False,
        },
        "claim_scope": {
            "benchmark_external_mechanism_localization_only": True,
            "deepwidebench_dev64_or_exact220_score": False,
            "entropy_or_credit_validated": False,
            "leaderboard_or_sota": False,
        },
        "authorization": {
            "v1_integration_build": False,
            "v2_protocol_published": True,
            "append_only_full_catalog_selected_target_integration_build": True,
            "runner_or_control_plane_build": False,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "quality_or_evaluator_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value)


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    manifest = copied.get("dependency_manifest")
    defect = copied.get("v1_defect", {})
    integration = copied.get("corrected_future_integration", {})
    receipt = copied.get("selected_target_receipt_contract", {})
    if (
        copied.get("role") != "v24790_cross_tab_external_preregistration_v2"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(manifest, Mapping) or dict(manifest) != dependency_manifest()
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("parent_v1", {}).get("integration_build_authority_revoked_before_implementation") is not True
        or copied.get("parent_v1", {}).get("runner_lease_model_search_fetch_or_forward_effect_before_revocation") is not False
        or copied.get("parent_v1", {}).get("all_v1_implementation_and_execution_surfaces_pristine") is not True
        or defect != {
            "defect_class": "selected_target_rebuild_changes_entity_segmentation_boundary_set",
            "one_target_catalog_rebuild_allowed": False,
            "full_target_catalog_required_for_segment_replay": True,
            "other_visible_entities_continue_to_delimit_selected_target_segments": True,
            "adjacent_entity_relation_may_be_rebound_if_boundaries_are_removed": True,
            "detected_before_integration_runner_or_external_effect": True,
        }
        or integration.get("implementation_status") != "not_built"
        or integration.get("full_target_catalog_or_original_projection_vector_mutated") is not False
        or integration.get("single_target_catalog_rebuilt") is not False
        or integration.get("maximum_selected_target_per_task") != 1
        or integration.get("private_truth_quality_or_evaluator_used_for_selection") is not False
        or integration.get("additional_model_search_fetch_or_evaluator_effect") != 0
        or integration.get("prediction_bytes_changed_by_observer") is not False
        or integration.get("positive_entropy_or_task_credit_assigned") is not False
        or receipt.get("fixed_catalog_dispositions") != list(observer.CATALOG_DISPOSITIONS)
        or receipt.get("fixed_catalog_quarantine_dispositions") != list(observer.CATALOG_QUARANTINE_DISPOSITIONS)
        or receipt.get("fixed_proposal_dispositions") != list(observer.PROPOSAL_DISPOSITIONS)
        or receipt.get("fixed_group_change_dispositions") != list(observer.GROUP_CHANGE_DISPOSITIONS)
        or receipt.get("target_count") != 1 or receipt.get("unknown_target_count") != 1
        or receipt.get("strict_joint_requires_same_selected_target_value_group") is not True
        or receipt.get("cross_task_or_cross_group_margins_used_as_joint") is not False
        or copied.get("source_policy") != {
            "v24784_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "v24789_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_publication": False,
        }
        or copied.get("claim_scope") != {
            "benchmark_external_mechanism_localization_only": True,
            "deepwidebench_dev64_or_exact220_score": False,
            "entropy_or_credit_validated": False,
            "leaderboard_or_sota": False,
        }
        or copied.get("authorization") != {
            "v1_integration_build": False,
            "v2_protocol_published": True,
            "append_only_full_catalog_selected_target_integration_build": True,
            "runner_or_control_plane_build": False,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "quality_or_evaluator_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.90 v2 protocol drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    protocol = build_protocol()
    publish_new(ROOT / OUTPUT, protocol)
    print(json.dumps({"output": str(OUTPUT), "protocol_id": PROTOCOL_ID, "v1_integration_authorized": False, "v2_integration_build_authorized": True, "external_launch": False}, sort_keys=True))
