#!/usr/bin/env python3
"""Create-exclusive audit for V2.42.56 dynamic-VOC calibration."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24255_finite_depth_dynamic_voc import (  # noqa: E402
    evaluate_voc_policies,
)
from deepwide_agent.v24256_dynamic_voc_calibration import (  # noqa: E402
    CALIBRATION_ROLE,
    FIT_ROLE,
    POLICY_ID,
    build_calibration_protocol,
    build_stop_loss_sample,
    build_topology,
    build_transition_sample,
    fit_dynamic_voc_source_package,
    reject_privileged_runtime_metadata,
)


ROLE = "v24256_dynamic_voc_calibration_build_audit"
OUTPUT = Path(
    "results/v24256_dynamic_voc_calibration_build_audit_v1_20260801.json"
)
MODULE = Path("src/deepwide_agent/v24256_dynamic_voc_calibration.py")
MODULE_TEST = Path("tests/test_v24256_dynamic_voc_calibration.py")
AUDIT = Path("scripts/audit_v24256_dynamic_voc_calibration.py")
AUDIT_TEST = Path("tests/test_audit_v24256_dynamic_voc_calibration.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)

V24255_RECEIPT = Path(
    "results/v24255_finite_depth_dynamic_voc_build_audit_v3_20260801.json"
)
V24255_RECEIPT_SHA256 = (
    "f285ba537f0631e69ef8ef6a227b445f106e9fbc1f94f8ca464104176809f447"
)
V24255_PAYLOAD_SHA256 = (
    "45a73ab31a78703fb4a44647f29d3c716f957cee9daca745cccce963b9927c72"
)
V24255_MANIFEST_SHA256 = (
    "26d41ffbbd8caef6359f45e10e879e7a2ab4dfa175c1d52f772cb553abd2845a"
)
V24123_PROTOCOL = Path(
    "results/v24123_release_bound_launcher_preregistration_v1_20260728.json"
)
V24123_PROTOCOL_SHA256 = (
    "f78e54b7dd1d8510a4b1afcf1e6d3a9c5c36dc81d8dbda05d39010940b8845ca"
)
V24123_SOURCE = Path("src/deepwide_agent/v24123_release.py")
V24123_SOURCE_SHA256 = (
    "49838bbcd450e995e9bbfbf0f0de9414bf98ef876945bd6830e0a79b38f21ed7"
)
EXPECTED_UNRELEASED_SCIENCE_OUTPUTS = (
    Path("results/v24123_entropy_action_response_model_v1_20260728.json"),
    Path("results/v24123_true_continuation_gate2a_report_v1_20260728.json"),
    Path(
        "results/v24193_replicate_aware_true_continuation_gate2a_report_v1_20260731.json"
    ),
)

ACTIVE_FORWARD_GUARD_FILES = (
    Path("src/deepwide_agent/__init__.py"),
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("src/deepwide_agent/v24253_candidate_runtime_integration.py"),
    Path("src/deepwide_agent/v24254_candidate_dev64_launcher.py"),
    Path("src/deepwide_agent/v24255_finite_depth_dynamic_voc.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)

ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "collections",
        "copy",
        "hashlib",
        "json",
        "math",
        "typing",
        "v24255_finite_depth_dynamic_voc",
    }
)
FORBIDDEN_CALL_NAMES = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "getattr",
        "globals",
        "input",
        "locals",
        "open",
        "setattr",
        "vars",
    }
)
FORBIDDEN_ATTRIBUTE_ROOTS = frozenset(
    {
        "aiohttp",
        "anyio",
        "asyncio",
        "builtins",
        "http",
        "httpx",
        "importlib",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "urllib",
    }
)
FORBIDDEN_ATTRIBUTE_CALLS = frozenset(
    {
        "connect",
        "fork",
        "getenv",
        "glob",
        "kill",
        "open",
        "popen",
        "read_bytes",
        "read_text",
        "request",
        "rglob",
        "spawn",
        "system",
        "urlopen",
        "walk",
        "write_bytes",
        "write_text",
    }
)
FORBIDDEN_METADATA_ACCESS_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "benchmark_category",
        "benchmark_label",
        "benchmark_subset",
        "category",
        "correctness",
        "evaluator_output",
        "evaluator_payload",
        "evaluator_score",
        "final_outcome",
        "gold",
        "ground_truth",
        "mapping",
        "official_metrics",
        "prediction",
        "question",
        "question_type",
        "raw_observation",
        "results.csv",
        "reward",
        "score",
        "split",
        "task_category",
        "task_id",
        "verifier_outcome",
    }
)
REQUIRED_PUBLIC_FUNCTIONS = frozenset(
    {
        "build_calibration_protocol",
        "build_stop_loss_sample",
        "build_topology",
        "build_transition_sample",
        "fit_dynamic_voc_source_package",
        "object_sha256",
        "reject_privileged_runtime_metadata",
        "validate_calibration_protocol",
        "validate_dynamic_voc_source_package",
        "validate_stop_loss_sample",
        "validate_topology",
        "validate_transition_sample",
    }
)
SECRET_LITERAL = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)"
    r"[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.56 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.56 expected an ordinary repository file: {relative}"
        )
    return path


def _literal_key(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.casefold()
    return None


def _attribute_root(node: ast.Attribute) -> str | None:
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    functions: set[str] = set()
    forbidden_calls: list[str] = []
    forbidden_attributes: list[str] = []
    privileged_reads: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
        elif isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in FORBIDDEN_CALL_NAMES
            ):
                forbidden_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                root = _attribute_root(node.func)
                if (
                    root in FORBIDDEN_ATTRIBUTE_ROOTS
                    or node.func.attr in FORBIDDEN_ATTRIBUTE_CALLS
                ):
                    forbidden_attributes.append(
                        f"{root}.{node.func.attr}" if root else node.func.attr
                    )
                if node.func.attr == "get" and node.args:
                    key = _literal_key(node.args[0])
                    if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                        privileged_reads.append(str(key))
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(str(key))
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_ROOTS)
    missing_functions = sorted(REQUIRED_PUBLIC_FUNCTIONS - functions)
    if (
        disallowed_imports
        or forbidden_calls
        or forbidden_attributes
        or privileged_reads
        or missing_functions
    ):
        raise RuntimeError(
            "V2.42.56 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(set(forbidden_attributes))}, "
            f"privileged_reads={sorted(set(privileged_reads))}, "
            f"missing={missing_functions}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_roots": sorted(imports),
        "required_public_functions_present": sorted(
            REQUIRED_PUBLIC_FUNCTIONS
        ),
        "disallowed_import_count": 0,
        "forbidden_file_environment_network_process_or_dynamic_code_call_count": 0,
        "privileged_runtime_metadata_read_count": 0,
        "file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability": False,
    }


def _function_string_literals(source: str, name: str) -> set[str]:
    tree = ast.parse(source)
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]
    if len(functions) != 1:
        raise RuntimeError(f"V2.42.56 parent function {name} is not unique")
    return {
        node.value
        for node in ast.walk(functions[0])
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def audit_v24123_schema(source: str) -> dict[str, Any]:
    aggregate = _function_string_literals(
        source, "aggregate_replicate_contributions"
    )
    training = _function_string_literals(source, "_action_training_rows")
    expected_aggregate = {
        "mean_signed_task_contribution",
        "replicate_action_observation_sha256s",
        "replicate_branch_adapter_receipt_sha256s",
    }
    expected_training = {
        "features",
        "task_contribution",
        "log_action_system_tokens",
    }
    forbidden_successor = {
        "post_action_features",
        "post_state_projection_sha256",
        "next_state_ref_sha256",
        "transition_probability",
        "transition_calibration_ref_sha256",
    }
    if (
        not expected_aggregate.issubset(aggregate)
        or not expected_training.issubset(training)
        or aggregate & forbidden_successor
        or training & forbidden_successor
    ):
        raise RuntimeError("V2.42.56 V2.41.23 schema audit drifted")
    return {
        "v24123_aggregate_has_terminal_contribution_and_provenance_hashes": True,
        "v24123_training_row_has_pre_action_features_and_myopic_contribution": True,
        "v24123_aggregate_has_successor_state_projection": False,
        "v24123_training_row_has_successor_state_or_transition_probability": False,
        "v24123_can_supply_myopic_target_without_new_data": True,
        "v24123_can_supply_dynamic_transition_calibration_without_new_data": False,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _topology() -> dict[str, Any]:
    root = _digest("state:root")
    left = _digest("state:left")
    right = _digest("state:right")
    bridge = _digest("state:bridge")
    terminal = _digest("state:terminal")
    return build_topology(
        abstraction_manifest_sha256=_digest("abstraction"),
        root_state_ref_sha256=root,
        max_depth=2,
        max_budget=2,
        states=[
            {
                "state_ref_sha256": root,
                "belief_entropy": 0.9,
                "actions": [
                    {
                        "action_ref_sha256": _digest("action:choose"),
                        "cost": 1,
                        "allowed_next_state_ref_sha256s": [left, right],
                    },
                    {
                        "action_ref_sha256": _digest("action:bridge"),
                        "cost": 1,
                        "allowed_next_state_ref_sha256s": [bridge],
                    },
                ],
            },
            {
                "state_ref_sha256": left,
                "belief_entropy": 0.1,
                "actions": [],
            },
            {
                "state_ref_sha256": right,
                "belief_entropy": 0.8,
                "actions": [],
            },
            {
                "state_ref_sha256": bridge,
                "belief_entropy": 0.9,
                "actions": [
                    {
                        "action_ref_sha256": _digest("action:finish"),
                        "cost": 1,
                        "allowed_next_state_ref_sha256s": [terminal],
                    }
                ],
            },
            {
                "state_ref_sha256": terminal,
                "belief_entropy": 0.9,
                "actions": [],
            },
        ],
    )


def replay_synthetic_contracts() -> dict[str, Any]:
    topology = _topology()
    fit_clusters = sorted([_digest("fit:0"), _digest("fit:1")])
    calibration_clusters = sorted(
        [_digest("calibration:0"), _digest("calibration:1")]
    )
    protocol = build_calibration_protocol(
        topology=topology,
        fit_partition_manifest_sha256=_digest("fit-partition"),
        calibration_partition_manifest_sha256=_digest(
            "calibration-partition"
        ),
        fit_task_cluster_ref_sha256s=fit_clusters,
        calibration_task_cluster_ref_sha256s=calibration_clusters,
        dirichlet_alpha_per_successor=1.0,
        minimum_fit_transition_clusters_per_action=2,
        minimum_calibration_transition_clusters_per_action=2,
        maximum_normalized_multiclass_brier=0.3,
        minimum_fit_stop_clusters_per_state=2,
        minimum_calibration_stop_clusters_per_state=2,
        maximum_stop_loss_mae=0.1,
    )
    root = _digest("state:root")
    left = _digest("state:left")
    right = _digest("state:right")
    bridge = _digest("state:bridge")
    terminal = _digest("state:terminal")
    choose = _digest("action:choose")
    open_bridge = _digest("action:bridge")
    finish = _digest("action:finish")
    sources = {choose: root, open_bridge: root, finish: bridge}
    transitions: list[dict[str, Any]] = []
    stops: list[dict[str, Any]] = []
    ordinal = 0
    for partition, clusters in (
        (FIT_ROLE, fit_clusters),
        (CALIBRATION_ROLE, calibration_clusters),
    ):
        for cluster_index, cluster in enumerate(clusters):
            for action_ref, next_state in (
                (choose, left if cluster_index == 0 else right),
                (open_bridge, bridge),
                (finish, terminal),
            ):
                transitions.append(
                    build_transition_sample(
                        topology=topology,
                        protocol=protocol,
                        partition_role=partition,
                        task_cluster_ref_sha256=cluster,
                        source_state_ref_sha256=sources[action_ref],
                        action_ref_sha256=action_ref,
                        next_state_ref_sha256=next_state,
                        pre_state_projection_sha256=_digest(
                            f"pre:{ordinal}"
                        ),
                        post_state_projection_sha256=_digest(
                            f"post:{ordinal}"
                        ),
                        action_observation_receipt_sha256=_digest(
                            f"observation:{ordinal}"
                        ),
                        state_transition_receipt_sha256=_digest(
                            f"transition:{ordinal}"
                        ),
                    )
                )
                ordinal += 1
            for state_ref, loss in (
                (root, 0.6),
                (left, 0.58),
                (right, 0.3),
                (bridge, 0.6),
                (terminal, 0.1),
            ):
                stops.append(
                    build_stop_loss_sample(
                        topology=topology,
                        protocol=protocol,
                        partition_role=partition,
                        task_cluster_ref_sha256=cluster,
                        state_ref_sha256=state_ref,
                        state_projection_sha256=_digest(
                            f"state:{ordinal}"
                        ),
                        prediction_freeze_sha256=_digest(
                            f"freeze:{ordinal}"
                        ),
                        terminal_receipt_sha256=_digest(
                            f"terminal:{ordinal}"
                        ),
                        evaluator_protocol_sha256=_digest(
                            "evaluator-protocol"
                        ),
                        evaluator_artifact_sha256=_digest(
                            f"evaluator:{ordinal}"
                        ),
                        terminal_status="completed",
                        evaluator_valid=True,
                        terminal_loss=loss,
                    )
                )
                ordinal += 1
    package = fit_dynamic_voc_source_package(
        topology=topology,
        protocol=protocol,
        transition_samples=transitions,
        stop_samples=stops,
    )
    decision = evaluate_voc_policies(
        model=package["v24255_transition_model"],
        expected_transition_model_sha256=package[
            "v24255_transition_model_sha256"
        ],
        requested_depth=2,
        available_budget=2,
    )
    if (
        package["calibration_complete"] is not True
        or decision["policies"]["pure_information_gain"][
            "selected_action_ref_sha256"
        ]
        != choose
        or decision["policies"]["myopic_terminal_loss_voc"][
            "selected_action_ref_sha256"
        ]
        != choose
        or decision["policies"]["finite_depth_dynamic_voc"][
            "selected_action_ref_sha256"
        ]
        != open_bridge
    ):
        raise RuntimeError("V2.42.56 calibrated replay drifted")
    incomplete_transitions = [
        sample
        for sample in transitions
        if not (
            sample["partition_role"] == CALIBRATION_ROLE
            and sample["action_ref_sha256"] == finish
        )
    ]
    incomplete = fit_dynamic_voc_source_package(
        topology=topology,
        protocol=protocol,
        transition_samples=incomplete_transitions,
        stop_samples=stops,
    )
    abstain = evaluate_voc_policies(
        model=incomplete["v24255_transition_model"],
        expected_transition_model_sha256=incomplete[
            "v24255_transition_model_sha256"
        ],
        requested_depth=2,
        available_budget=2,
    )
    if (
        incomplete["calibration_complete"] is not False
        or any(
            row["decision_kind"] != "abstain"
            for row in abstain["policies"].values()
        )
    ):
        raise RuntimeError("V2.42.56 incomplete calibration replay drifted")
    privileged_rejected = False
    try:
        reject_privileged_runtime_metadata(
            {"visible": [{"question_type": "evaluator-only"}]}
        )
    except ValueError:
        privileged_rejected = True
    if not privileged_rejected:
        raise RuntimeError("V2.42.56 privileged metadata was accepted")
    return {
        "content_free_split_calibration_replayed": True,
        "fit_and_calibration_task_clusters_disjoint": True,
        "task_cluster_equal_transition_fit_replayed": True,
        "dirichlet_smoothed_transition_fit_replayed": True,
        "heldout_normalized_multiclass_brier_gate_replayed": True,
        "task_cluster_equal_stop_loss_fit_replayed": True,
        "heldout_stop_loss_mae_gate_replayed": True,
        "calibration_complete_emits_v24255_ready_model": True,
        "calibration_incomplete_emits_v24255_all_abstain_model": True,
        "pure_ig_myopic_and_dynamic_policy_divergence_replayed": True,
        "nested_privileged_runtime_metadata_rejected": True,
        "real_task_state_transition_evaluator_payload_or_api_read": False,
    }


def _validate_parents(root: Path) -> dict[str, Any]:
    v24255_path = ordinary(root, V24255_RECEIPT)
    if sha256(v24255_path) != V24255_RECEIPT_SHA256:
        raise RuntimeError("V2.42.56 V2.42.55 parent receipt drifted")
    v24255 = json.loads(v24255_path.read_text(encoding="utf-8"))
    unsigned = dict(v24255)
    payload = unsigned.pop("audit_payload_sha256", None)
    manifest = {
        relative: sha256(ordinary(root, Path(relative)))
        for relative in v24255["control_surface"]["manifest"]
    }
    if (
        payload != V24255_PAYLOAD_SHA256
        or payload_sha256(unsigned) != payload
        or v24255["control_surface"]["manifest_sha256"]
        != V24255_MANIFEST_SHA256
        or payload_sha256(manifest) != V24255_MANIFEST_SHA256
        or manifest != v24255["control_surface"]["manifest"]
        or v24255.get("audit_valid") is not True
        or v24255.get("build_only") is not True
        or v24255["claims"]["benchmark_score_available"] is not False
    ):
        raise RuntimeError("V2.42.56 V2.42.55 parent validation failed")

    v24123_path = ordinary(root, V24123_PROTOCOL)
    v24123_source = ordinary(root, V24123_SOURCE)
    if (
        sha256(v24123_path) != V24123_PROTOCOL_SHA256
        or sha256(v24123_source) != V24123_SOURCE_SHA256
    ):
        raise RuntimeError("V2.42.56 V2.41.23 parent bytes drifted")
    v24123 = json.loads(v24123_path.read_text(encoding="utf-8"))
    if (
        v24123.get("role")
        != "v24123_release_bound_launcher_preregistration"
        or v24123["claims"]["real_true_continuation_result_available"]
        is not False
        or v24123["authorization"]["real_api_now"] is not False
        or v24123["authorization"]["controller_or_training"] is not False
        or v24123["authorization"]["full220_controller_launch"] is not False
    ):
        raise RuntimeError("V2.42.56 V2.41.23 authority drifted")
    source_text = v24123_source.read_text(encoding="utf-8")
    return {
        "v24255": {
            "path": str(V24255_RECEIPT),
            "file_sha256": V24255_RECEIPT_SHA256,
            "payload_sha256": V24255_PAYLOAD_SHA256,
            "control_manifest_sha256": V24255_MANIFEST_SHA256,
            "build_only_parent_validated": True,
        },
        "v24123": {
            "path": str(V24123_PROTOCOL),
            "protocol_sha256": V24123_PROTOCOL_SHA256,
            "source_path": str(V24123_SOURCE),
            "source_sha256": V24123_SOURCE_SHA256,
            "true_continuation_contract_validated": True,
            "real_true_continuation_result_available": False,
            "controller_or_training_authorized": False,
        },
        "v24123_schema_gap": audit_v24123_schema(source_text),
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.56 audit may only use the canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    guards = {
        str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARD_FILES
    }
    control_sources = {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    }
    forbidden_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in control_sources.items()
    }
    if any(forbidden_hits.values()):
        raise RuntimeError("V2.42.56 control source contains forbidden content")
    static = audit_python_source(control_sources[str(MODULE)])
    module_name = "v24256_dynamic_voc_calibration"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.56 appears in an active forward guard file")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    parents = _validate_parents(root)
    replay = replay_synthetic_contracts()
    unreleased = {
        str(path): (root / path).exists()
        for path in EXPECTED_UNRELEASED_SCIENCE_OUTPUTS
    }
    if any(unreleased.values()):
        raise RuntimeError(
            "V2.42.56 expected-unreleased parent science output appeared"
        )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "policy_id": POLICY_ID,
        "label_blind_runtime": True,
        "build_only": True,
        "parents": parents,
        "control_surface": {
            "file_count": len(control_manifest),
            "manifest": control_manifest,
            "manifest_sha256": payload_sha256(control_manifest),
        },
        "active_forward_guard": {
            "file_count": len(guard_manifest),
            "manifest": guard_manifest,
            "manifest_sha256": payload_sha256(guard_manifest),
            "module_name_hit_count_by_file": guard_hits,
            "module_absent_from_guarded_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(forbidden_hits),
            "hit_count": 0,
            "credential_or_concrete_opaque_id_literal_present": False,
        },
        "synthetic_contract_replay": replay,
        "upstream_science_output_presence_at_audit": unreleased,
        "scientific_scope": {
            "content_free_successor_transition_sample_schema_implemented": True,
            "post_terminal_development_loss_sample_schema_implemented": True,
            "fit_calibration_task_cluster_firewall_implemented": True,
            "task_cluster_equal_weighting_implemented": True,
            "dirichlet_smoothed_transition_fit_implemented": True,
            "heldout_transition_brier_gate_implemented": True,
            "heldout_stop_loss_mae_gate_implemented": True,
            "calibration_failure_forces_all_v24255_policies_to_abstain": True,
            "v24123_myopic_contribution_not_reinterpreted_as_transition": True,
            "belief_entropy_is_diagnostic_not_terminal_utility": True,
            "real_successor_state_projection_dataset_available": False,
            "real_transition_probabilities_calibrated": False,
            "real_stop_loss_model_calibrated": False,
            "v24123_action_response_model_available": False,
            "gate2a_or_gate3a_evaluated": False,
            "runtime_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipts_and_synthetic_hashes_only": True,
            "runtime_task_question_query_raw_state_observation_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "development_loss_scalar_used_only_in_synthetic_replay": True,
            "credential_environment_keyring_or_secret_value_read": False,
            "network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "production_package_authorized": False,
            "runtime_forward_authorized": False,
            "credit_training_authorized": False,
            "benchmark_evaluator_launch_authorized": False,
            "active_forward_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "candidate_materialization_or_package_gate": False,
            "dev64_full220_or_evaluator_launch": False,
            "shared_api_lease_acquire": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "build_only_dynamic_voc_calibration_primitive_available": True,
            "real_calibration_dataset_available": False,
            "real_calibrated_dynamic_voc_model_available": False,
            "runtime_integration_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.56 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.56 audit output path is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        parent_descriptor = os.open(
            target.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    target = target if target.is_absolute() else ROOT / target
    value = build_audit()
    publish_new(target, value)
    print(
        json.dumps(
            {
                "path": str(target),
                "sha256": sha256(target),
                "audit_valid": value["audit_valid"],
                "build_only": value["build_only"],
            }
        )
    )


if __name__ == "__main__":
    main()
