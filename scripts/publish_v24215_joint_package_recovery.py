#!/usr/bin/env python3
"""Publish the V2.42.15 joint package under the corrected parent binding."""

from __future__ import annotations

import argparse
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
from deepwide_agent.v24214_joint_package import (  # noqa: E402
    build_joint_package_order,
)
from deepwide_agent.v24215_joint_package_recovery import (  # noqa: E402
    FAILED_AUDIT_PATH,
    FAILED_AUDIT_SHA256,
    build_recovery_order,
    validate_recovery_order,
)
from scripts.publish_v24214_joint_package import (  # noqa: E402
    COMPONENT_PUBLICATIONS,
    SELECTED_WORK_ORDER,
    file_sha256,
    load_selected_inputs,
    materialize_joint_candidate,
    resolve_deepest_graph,
)


OUTPUT = Path(
    "results/v24215_selected_joint_package_recovery_publication_v1_20260731.json"
)
CANDIDATE_ROOT = (
    ROOT / "outputs/v24215_selected_joint_package_recovery_candidate_v1_20260731"
)
SECRET_LITERAL = re.compile(
    rb"(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = re.compile(rb"task_[0-9a-f]{24}")


def load_recovery_inputs(
    root: Path = ROOT,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, dict[str, Any]],
]:
    """Load terminal V2.42.13 inputs and derive both old and corrected orders."""

    selected, base_order, publications = load_selected_inputs(root)
    work_order = selected["selected_work_order"]
    expected_base = build_joint_package_order(work_order)
    if base_order != expected_base:
        raise RuntimeError("V2.42.15 V2.42.14 base order drifted")
    recovery = build_recovery_order(work_order)
    validate_recovery_order(recovery)
    return selected, base_order, recovery, publications


def build_recovery_publication(
    selected: Mapping[str, Any],
    base_order: Mapping[str, Any],
    recovery_order: Mapping[str, Any],
    publications: Mapping[str, Mapping[str, Any]],
    *,
    candidate: Path = CANDIDATE_ROOT,
) -> dict[str, Any]:
    """Revalidate one graph while publishing only the corrected order."""

    corrected = validate_recovery_order(recovery_order)
    if dict(base_order) != build_joint_package_order(selected["selected_work_order"]):
        raise RuntimeError("V2.42.15 base order no longer matches selected work")
    identity = bool(corrected["identity_handoff_only"])
    files, names, count, provenance = resolve_deepest_graph(
        base_order, publications
    )
    if identity:
        component = None
        identity_manifest = {
            relative: __import__("hashlib").sha256(source.encode()).hexdigest()
            for relative, source in sorted(files.items())
        }
        disposition = "byte_exact_selected_baseline_identity_handoff_recovered"
    else:
        component = materialize_joint_candidate(
            files,
            names,
            count,
            provenance,
            candidate=candidate,
        )
        identity_manifest = None
        disposition = "corrected_single_deepest_graph_joint_package_revalidated"
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24215_selected_joint_package_recovery_publication",
        "label_blind": True,
        "recovery_parent": {
            "path": FAILED_AUDIT_PATH,
            "sha256": FAILED_AUDIT_SHA256,
            "failure_classification": (
                "entropy_publication_path_binding_mismatch_fail_closed"
            ),
        },
        "selected_work_order": {
            "path": str(SELECTED_WORK_ORDER),
            "sha256": file_sha256(ROOT / SELECTED_WORK_ORDER),
            "selected_payload_sha256": selected["selected_payload_sha256"],
            "decision_sha256": corrected["decision_sha256"],
        },
        "component_publications": {
            name: {
                "path": str(COMPONENT_PUBLICATIONS[name]),
                "sha256": file_sha256(ROOT / COMPONENT_PUBLICATIONS[name]),
                "publication_payload_sha256": publications[name][
                    "publication_payload_sha256"
                ],
            }
            for name in ("markdown", "scope", "search", "entropy")
        },
        "joint_package_order": corrected,
        "only_recovery_delta": (
            "bind_entropy_deepest_publication_to_actual_v24213_output_path"
        ),
        "v24214_protocol_activation_state_candidate_or_publication_reused_overwritten_or_resumed": False,
        "publication_disposition": disposition,
        "component_publication": component,
        "identity_handoff_manifest": identity_manifest,
        "identity_handoff_only": identity,
        "joint_package_materialized": component is not None,
        "all_selected_components_covered_exactly_once": True,
        "single_deepest_cumulative_graph_used": True,
        "component_directory_overlay_used": False,
        "complete_parent_and_component_regression_rerun": component is not None,
        "strict_component_activation_validated": component is not None,
        "silent_component_drop_or_baseline_fallback_used": False,
        "package_gate_evaluated_or_launched": False,
        "dev64_launch_allowed": False,
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
        raise RuntimeError("V2.42.15 publication exposes forbidden content")
    value["publication_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", default=str(CANDIDATE_ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    candidate = Path(args.candidate_root)
    output = Path(args.output)
    if (
        candidate.resolve(strict=False) != CANDIDATE_ROOT.resolve(strict=False)
        or output.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False)
    ):
        raise RuntimeError("V2.42.15 CLI path drifted")
    selected, base, recovery, publications = load_recovery_inputs(ROOT)
    value = build_recovery_publication(
        selected, base, recovery, publications, candidate=candidate
    )
    publish_new(output, value)
    print(json.dumps({"path": str(output), "sha256": file_sha256(output)}))


if __name__ == "__main__":
    main()
