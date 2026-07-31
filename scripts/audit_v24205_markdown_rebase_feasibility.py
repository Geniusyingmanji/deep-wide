#!/usr/bin/env python3
"""Publish a repo-local Markdown rebase feasibility audit.

The audit reconstructs the frozen baseline DAG in memory, checks production
hook compatibility, and classifies every V2.42.00 decision.  It never writes a
candidate tree, reads live task state or benchmark content, calls a service,
evaluates a package, or authorizes a benchmark.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from deepwide_agent.v24205_markdown_rebase_audit import (  # noqa: E402
    build_markdown_rebase_manifest,
)
from scripts import build_v24102_markdown_candidate as markdown  # noqa: E402
from scripts import build_v24104_scope_open_candidate as scope  # noqa: E402
from scripts.replay_v24201_repo_local_candidate_dag import (  # noqa: E402
    PUBLICATIONS,
    build_replay,
    text_manifest,
)


OUTPUT = Path("results/v24205_markdown_rebase_feasibility_audit_v1_20260731.json")
V24201_RECEIPT = Path(
    "results/v24201_repo_local_candidate_dag_replay_v1_20260731.json"
)
V24201_RECEIPT_SHA256 = (
    "cee95e892c1aa2e80dbcc70bac5f426e7f66a7e023c14554a63e42878bdb2a6f"
)
V24204_PROTOCOL = Path(
    "results/v24204_postdecision_work_order_preregistration_v1_20260731.json"
)
V24204_PROTOCOL_SHA256 = (
    "aedd97c0ccbfaa3e18f157aa56e0d0969c39fc28b0903cbe2260a3db1172d5e4"
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordinary(root: Path, relative: Path, digest: str) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.05 input path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
        or file_sha256(path) != digest
    ):
        raise RuntimeError(f"V2.42.05 frozen input drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.05 expected one JSON object")
    return value


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if source.count(old) != 1:
        raise RuntimeError(f"V2.42.05 expected one {label}")
    return source.replace(old, new, 1)


def runtime_identity(source: str) -> tuple[int, str]:
    tree = ast.parse(source)
    schema: int | None = None
    version: str | None = None
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or not isinstance(node.value, ast.Constant):
            continue
        if target.id == "STATE_SCHEMA_VERSION" and isinstance(node.value.value, int):
            schema = node.value.value
        if target.id == "PIPELINE_VERSION" and isinstance(node.value.value, str):
            version = node.value.value
    if schema is None or version is None:
        raise RuntimeError("V2.42.05 runtime identity is absent")
    return schema, version


def rebase_markdown_production(
    files: Mapping[str, str],
    *,
    target_schema: int,
    target_suffix: str,
) -> dict[str, str]:
    """Apply historical Markdown production hooks to an arbitrary baseline."""

    output = dict(files)
    runtime_path = "src/deepwide_agent/runtime.py"
    preflight_path = "scripts/preflight_deepwide.py"
    source = output[runtime_path]
    parent_schema, parent_version = runtime_identity(source)
    normalized = replace_once(
        source,
        f'STATE_SCHEMA_VERSION = {parent_schema}\nPIPELINE_VERSION = "{parent_version}"',
        f'STATE_SCHEMA_VERSION = {markdown.PARENT_STATE_SCHEMA_VERSION}\n'
        f'PIPELINE_VERSION = "{markdown.PARENT_PIPELINE_VERSION}"',
        "runtime identity normalization hook",
    )
    patched = markdown.patch_runtime(normalized)
    target_version = parent_version + target_suffix
    patched = replace_once(
        patched,
        f'STATE_SCHEMA_VERSION = {markdown.TARGET_STATE_SCHEMA_VERSION}\n'
        f'PIPELINE_VERSION = "{markdown.TARGET_PIPELINE_VERSION}"',
        f'STATE_SCHEMA_VERSION = {target_schema}\nPIPELINE_VERSION = "{target_version}"',
        "runtime identity restoration hook",
    )
    output[runtime_path] = patched
    output[preflight_path] = markdown.patch_preflight(output[preflight_path])
    output[markdown.PURE_MODULE] = (ROOT / markdown.PURE_MODULE).read_text(
        encoding="utf-8"
    )
    for relative, text in output.items():
        if relative.endswith(".py"):
            ast.parse(text, filename=relative)
    if runtime_identity(output[runtime_path]) != (target_schema, target_version):
        raise RuntimeError("V2.42.05 rebased runtime identity drifted")
    return output


def _hook_counts(source: str) -> dict[str, int]:
    markers = {
        "v2410_import_anchor": "from .v2410 import (\n",
        "markdown_import": "from .v24102 import (\n",
        "scope_import": "from .v24104 import (\n",
        "scope_fallback_call": (
            "fallback = _v24104_conservative_open_scope_fallback(value, last_errors)"
        ),
        "scope_audit_write": (
            'state.setdefault("scope_open_fallback_audits", []).append(fallback.audit())'
        ),
    }
    return {name: source.count(marker) for name, marker in markers.items()}


def _validate_parents(root: Path) -> dict[str, Any]:
    replay = read_object(ordinary(root, V24201_RECEIPT, V24201_RECEIPT_SHA256))
    work = read_object(ordinary(root, V24204_PROTOCOL, V24204_PROTOCOL_SHA256))
    unsigned = dict(replay)
    replay_seal = unsigned.pop("replay_payload_sha256", None)
    if (
        replay.get("role") != "v24201_repo_local_candidate_dag_replay"
        or replay.get("all_stage_file_maps_byte_exact_to_frozen_publications")
        is not True
        or replay.get("candidate_tree_materialized") is not False
        or replay.get("benchmark_forward_or_full220_launch_allowed") is not False
        or replay_seal != payload_sha256(unsigned)
        or work.get("role") != "v24204_postdecision_work_order_preregistration"
        or work.get("authorization", {}).get(
            "candidate_code_build_merge_materialization_or_freeze_generation"
        )
        is not False
        or work.get("authorization", {}).get("benchmark_forward_or_full220_launch")
        is not False
    ):
        raise RuntimeError("V2.42.05 frozen parent contract drifted")
    return {
        "v24201_replay": {
            "path": str(V24201_RECEIPT),
            "sha256": V24201_RECEIPT_SHA256,
            "replay_payload_sha256": replay_seal,
        },
        "v24204_work_order_protocol": {
            "path": str(V24204_PROTOCOL),
            "sha256": V24204_PROTOCOL_SHA256,
            "decision_contract_sha256": work["decision_contract_sha256"],
        },
    }


def build_audit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.05 may only audit the canonical workspace")
    parents = _validate_parents(root)
    replay, maps = build_replay()
    if replay.get("all_stage_file_maps_byte_exact_to_frozen_publications") is not True:
        raise RuntimeError("V2.42.05 repo-local DAG replay failed")

    historical = {}
    for baseline, stage in (("p12_markdown", "schema69"), ("p12_markdown_scope", "schema70")):
        manifest = text_manifest(maps[stage])
        publication = PUBLICATIONS[stage]
        value = read_object(ordinary(root, Path(publication.path), publication.sha256))
        expected = value.get("candidate_regular_file_manifest")
        if not isinstance(expected, dict):
            expected = dict(
                sorted(
                    {
                        **(value.get("support_file_manifest") or {}),
                        **(value.get("generated_file_manifest") or {}),
                    }.items()
                )
            )
        if manifest != expected:
            raise RuntimeError("V2.42.05 historical Markdown map drifted")
        historical[baseline] = {
            "stage": stage,
            "publication": {"path": publication.path, "sha256": publication.sha256},
            "file_count": len(manifest),
            "byte_exact": True,
            "postdecision_selected_package_binding_available": False,
        }

    mainline: dict[str, Any] = {}
    for baseline, stage, target_schema in (
        ("schema76", "schema76", 78),
        ("schema77", "schema77", 79),
    ):
        before = maps[stage]
        before_runtime = before["src/deepwide_agent/runtime.py"]
        before_hooks = _hook_counts(before_runtime)
        rebased = rebase_markdown_production(
            before,
            target_schema=target_schema,
            target_suffix="-markdown-rank-slot-rebase-feasibility-only",
        )
        after_runtime = rebased["src/deepwide_agent/runtime.py"]
        after_hooks = _hook_counts(after_runtime)
        changed = sorted(
            relative
            for relative in set(before) | set(rebased)
            if before.get(relative) != rebased.get(relative)
        )
        if (
            before_hooks["markdown_import"] != 0
            or before_hooks["scope_import"] != 1
            or before_hooks["scope_fallback_call"] != 1
            or before_hooks["scope_audit_write"] != 1
            or after_hooks["markdown_import"] != 1
            or after_hooks["scope_import"] != 1
            or after_hooks["scope_fallback_call"] != 1
            or after_hooks["scope_audit_write"] != 1
            or markdown.PURE_MODULE not in changed
            or "src/deepwide_agent/runtime.py" not in changed
            or "scripts/preflight_deepwide.py" not in changed
        ):
            raise RuntimeError("V2.42.05 mainline hook compatibility drifted")

        normalized = replace_once(
            after_runtime,
            f'STATE_SCHEMA_VERSION = {target_schema}\n'
            f'PIPELINE_VERSION = "{runtime_identity(after_runtime)[1]}"',
            f'STATE_SCHEMA_VERSION = {scope.PARENT_STATE_SCHEMA_VERSION}\n'
            f'PIPELINE_VERSION = "{scope.PARENT_PIPELINE_VERSION}"',
            "scope duplicate identity normalization hook",
        )
        duplicate_scope_runtime = scope.patch_runtime(normalized)
        duplicate_scope_hooks = _hook_counts(duplicate_scope_runtime)
        if (
            duplicate_scope_hooks["scope_import"] != 2
            or duplicate_scope_hooks["scope_fallback_call"] != 2
            or duplicate_scope_hooks["scope_audit_write"] != 2
        ):
            raise RuntimeError(
                "V2.42.05 duplicate branch scope audit signature drifted"
            )
        mainline[baseline] = {
            "source_stage": stage,
            "source_runtime_identity": {
                "state_schema_version": runtime_identity(before_runtime)[0],
                "pipeline_version": runtime_identity(before_runtime)[1],
            },
            "production_hook_compatibility": True,
            "rebase_feasibility_file_count": len(rebased),
            "changed_files": changed,
            "before_hook_counts": before_hooks,
            "after_hook_counts": after_hooks,
            "mainline_scope_hook_preserved_exactly_once": True,
            "historical_branch_scope_patch_mechanically_succeeds": True,
            "historical_branch_scope_patch_duplicate_hook_counts": (
                duplicate_scope_hooks
            ),
            "historical_branch_scope_patch_reapplication_rejected_by_audit": True,
            "branch_scope_requires_zero_byte_namespace_alias_design": True,
            "tests_version_guards_rebased": False,
            "candidate_or_publication_built": False,
        }

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24205_markdown_rebase_feasibility_audit",
        "label_blind": True,
        "frozen_parents": parents,
        "decision_classification": build_markdown_rebase_manifest(),
        "historical_p12_paths": historical,
        "mainline_hook_audit": mainline,
        "conclusion": {
            "p12_schema69_schema70_bytes_repo_local_and_exact": True,
            "schema76_schema77_markdown_production_hooks_compatible": True,
            "schema76_schema77_mainline_scope_hook_already_active_once": True,
            "branch_scope_must_not_reapply_historical_v24104_patch": True,
            "branch_scope_namespace_alias_semantics_still_unpublished": True,
            "selected_baseline_test_rebase_and_joint_regression_still_absent": True,
            "selected_package_publication_available": False,
        },
        "live_status_or_decision_receipt_read": False,
        "runtime_task_state_prediction_or_result_read": False,
        "benchmark_question_answer_evidence_or_url_read": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "candidate_tree_or_package_materialized": False,
        "component_implementation_authority_granted": False,
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
        raise RuntimeError("V2.42.05 output path is noncanonical")
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": file_sha256(target)}))


if __name__ == "__main__":
    main()
