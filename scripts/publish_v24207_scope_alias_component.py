#!/usr/bin/env python3
"""Publish the selected branch-scope binding after V2.42.06 terminates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from deepwide_agent.v24207_scope_alias_publisher import (  # noqa: E402
    build_scope_publication_order,
)
from scripts.audit_v24205_markdown_rebase_feasibility import (  # noqa: E402
    _hook_counts,
    runtime_identity,
)
from scripts.publish_v24206_markdown_component import (  # noqa: E402
    OUTPUT as MARKDOWN_PUBLICATION,
    SELECTED_WORK_ORDER,
    historical_p12_binding,
    load_selected_work_order,
    read_object,
)
from scripts.replay_v24201_repo_local_candidate_dag import (  # noqa: E402
    PUBLICATIONS,
    build_replay,
    file_sha256,
    manifest_sha256,
    publication_manifest,
    read_publication,
    text_manifest,
)


OUTPUT = Path("results/v24207_selected_scope_alias_component_publication_v1_20260731.json")
MARKDOWN_PROTOCOL = Path(
    "results/v24206_selected_markdown_component_preregistration_v1_20260731.json"
)
MARKDOWN_PROTOCOL_SHA256 = (
    "3c543a528ab58afefcc5c85697c450fa83239498300e4f9d7f57a21e5ad89ffa"
)
SECRET_LITERAL = re.compile(rb"(?:ghp_|github_pat_|tvly-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE_ID = re.compile(rb"task_[0-9a-f]{24}")


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


def load_inputs(
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Bind the selected work order and its terminal Markdown publication."""

    selected, _markdown_order = load_selected_work_order(root, SELECTED_WORK_ORDER)
    work_order = selected["selected_work_order"]
    scope_order = build_scope_publication_order(work_order)
    markdown_path = root / MARKDOWN_PUBLICATION
    markdown = read_object(markdown_path)
    unsigned = dict(markdown)
    seal = unsigned.pop("publication_payload_sha256", None)
    false_fields = (
        "branch_scope_patch_or_alias_applied",
        "search_yield_or_entropy_implemented",
        "joint_package_built_or_materialized",
        "package_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    if (
        markdown.get("role") != "v24206_selected_markdown_component_publication"
        or markdown.get("label_blind") is not True
        or markdown.get("selected_work_order", {}).get("decision_sha256")
        != scope_order["decision_sha256"]
        or any(markdown.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.07 Markdown parent publication drifted")
    if scope_order["branch_scope_component_selected"] and not markdown.get(
        "markdown_component_published"
    ):
        raise RuntimeError("V2.42.07 selected branch scope lacks Markdown bytes")
    return selected, scope_order, markdown


def historical_p12_scope_binding() -> dict[str, Any]:
    replay, maps = build_replay()
    publication = read_publication(PUBLICATIONS["schema70"])
    manifest = text_manifest(maps["schema70"])
    if (
        replay.get("all_stage_file_maps_byte_exact_to_frozen_publications") is not True
        or manifest != publication_manifest(publication)
    ):
        raise RuntimeError("V2.42.07 historical schema70 bytes drifted")
    hooks = _hook_counts(maps["schema70"]["src/deepwide_agent/runtime.py"])
    if (
        hooks["markdown_import"] != 1
        or hooks["scope_import"] != 1
        or hooks["scope_fallback_call"] != 1
        or hooks["scope_audit_write"] != 1
    ):
        raise RuntimeError("V2.42.07 historical schema70 hook count drifted")
    return {
        "publication_kind": "historical_schema70_byte_exact_binding",
        "historical_publication": {
            "path": PUBLICATIONS["schema70"].path,
            "sha256": PUBLICATIONS["schema70"].sha256,
        },
        "target_pipeline_version": publication["target_pipeline_version"],
        "target_state_schema_version": publication["target_state_schema_version"],
        "candidate_regular_file_count": len(manifest),
        "candidate_regular_file_manifest": manifest,
        "candidate_regular_file_manifest_sha256": manifest_sha256(manifest),
        "historical_bytes_byte_exact": True,
        "scope_hook_counts": hooks,
        "historical_scope_patch_reapplied": False,
        "candidate_root_created": False,
    }


def mainline_zero_byte_alias(
    baseline: str, markdown: Mapping[str, Any]
) -> dict[str, Any]:
    component = markdown.get("component_publication")
    if not isinstance(component, Mapping):
        raise RuntimeError("V2.42.07 mainline Markdown component is absent")
    root = Path(str(component.get("candidate_root", "")))
    if (
        baseline not in {"schema76", "schema77"}
        or not root.is_absolute()
        or not root.resolve().is_relative_to(ROOT.resolve())
        or root.is_symlink()
        or not root.is_dir()
    ):
        raise RuntimeError("V2.42.07 mainline candidate root is noncanonical")
    manifest = component.get("candidate_regular_file_manifest")
    if not isinstance(manifest, dict) or not manifest:
        raise RuntimeError("V2.42.07 mainline candidate manifest is absent")
    for relative, digest in manifest.items():
        path = root / str(relative)
        if path.is_symlink() or not path.is_file() or file_sha256(path) != digest:
            raise RuntimeError("V2.42.07 mainline candidate bytes drifted")
    live_manifest = dict(sorted(manifest.items()))
    runtime = (root / "src/deepwide_agent/runtime.py").read_text(encoding="utf-8")
    hooks = _hook_counts(runtime)
    if (
        hooks["markdown_import"] != 1
        or hooks["scope_import"] != 1
        or hooks["scope_fallback_call"] != 1
        or hooks["scope_audit_write"] != 1
        or component.get("mainline_scope_hook_preserved_exactly_once") is not True
        or component.get("branch_scope_patch_or_alias_applied") is not False
    ):
        raise RuntimeError("V2.42.07 mainline namespace alias precondition failed")
    identity = runtime_identity(runtime)
    if identity != (
        int(component["target_state_schema_version"]),
        str(component["target_pipeline_version"]),
    ):
        raise RuntimeError("V2.42.07 mainline runtime identity drifted")
    return {
        "publication_kind": "zero_byte_mainline_scope_namespace_alias",
        "alias_name": "markdown_branch_scope_open_fallback",
        "aliased_existing_namespace": "mainline_scope_open_fallback",
        "source_markdown_publication": {
            "path": str(MARKDOWN_PUBLICATION),
            "sha256": file_sha256(ROOT / MARKDOWN_PUBLICATION),
            "publication_payload_sha256": markdown["publication_payload_sha256"],
        },
        "candidate_root": str(root),
        "target_pipeline_version": identity[1],
        "target_state_schema_version": identity[0],
        "candidate_regular_file_count": len(live_manifest),
        "candidate_regular_file_manifest": live_manifest,
        "candidate_regular_file_manifest_sha256": manifest_sha256(live_manifest),
        "scope_hook_counts": hooks,
        "mainline_scope_hook_preserved_exactly_once": True,
        "historical_scope_patch_reapplied": False,
        "candidate_bytes_modified_or_materialized": False,
        "alias_changes_runtime_behavior": False,
        "alias_changes_pipeline_or_schema_identity": False,
    }


def build_selected_publication(
    selected: Mapping[str, Any],
    order: Mapping[str, Any],
    markdown: Mapping[str, Any],
) -> dict[str, Any]:
    mode = order["publication_mode"]
    component: dict[str, Any] | None
    if mode == "no_op_component_absent":
        component = None
    elif mode == "bind_historical_schema70_bytes":
        component = historical_p12_scope_binding()
    elif mode == "bind_zero_byte_mainline_scope_namespace_alias":
        component = mainline_zero_byte_alias(order["baseline_name"], markdown)
    else:
        raise RuntimeError("V2.42.07 publication mode is unsupported")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24207_selected_scope_alias_component_publication",
        "label_blind": True,
        "selected_work_order": {
            "path": str(SELECTED_WORK_ORDER),
            "sha256": file_sha256(ROOT / SELECTED_WORK_ORDER),
            "selected_payload_sha256": selected["selected_payload_sha256"],
            "decision_sha256": order["decision_sha256"],
        },
        "markdown_parent_publication": {
            "path": str(MARKDOWN_PUBLICATION),
            "sha256": file_sha256(ROOT / MARKDOWN_PUBLICATION),
            "publication_payload_sha256": markdown["publication_payload_sha256"],
        },
        "publication_order": dict(order),
        "component_publication": component,
        "branch_scope_component_published": component is not None,
        "selected_baseline_bound": component is not None,
        "historical_scope_patch_reapplied": False,
        "candidate_bytes_modified_or_materialized": False,
        "search_yield_or_entropy_implemented": False,
        "joint_package_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    encoded = json.dumps(value, sort_keys=True).encode()
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.07 publication exposes forbidden content")
    value["publication_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    if output.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.07 CLI path drifted")
    selected, order, markdown = load_inputs(ROOT)
    value = build_selected_publication(selected, order, markdown)
    publish_new(output, value)
    print(json.dumps({"path": str(output), "sha256": file_sha256(output)}))


if __name__ == "__main__":
    main()
