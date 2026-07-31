#!/usr/bin/env python3
"""Freeze the post-terminal, label-blind V2.42.20 source-dependency audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24218_exact220_executor import (  # noqa: E402
    EXPECTED_COUNTS,
    EXPECTED_SHARDS,
    file_sha256,
    read_opaque_ids,
    validate_exact_partition,
)
from deepwide_agent.v24220_source_dependency import (  # noqa: E402
    CHAR_SHINGLE_SIZE,
    MIN_NEAR_DUPLICATE_CHARS,
    MIN_NEAR_DUPLICATE_LENGTH_RATIO,
    MIN_SHARED_QUOTE_CHARS,
    NEAR_DUPLICATE_CONTAINMENT,
    NEAR_DUPLICATE_JACCARD,
    PATH_MIRROR_RHO,
    SAME_FAMILY_RHO,
    SHARED_QUOTE_RHO,
    SHARED_STRUCTURED_RECORD_RHO,
    payload_sha256,
)
from scripts.run_v24220_source_dependency import (  # noqa: E402
    DETAIL,
    MANIFEST,
    PARENT_PROTOCOL,
    PARENT_REPORT,
    PARENT_STATE,
    PROTOCOL,
    REPORT,
    SHARD_IDS,
)


ROLE = "v24220_source_dependency_preregistration"
PROTOCOL_ID = "v24220_post_terminal_label_blind_source_dependency_v1"
STATE = Path("outputs/v24220_source_dependency_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24220_source_dependency_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24220_source_dependency_wait_audit_v1_20260731.json")
PARENT_PROTOCOL_SHA256 = (
    "d7923f65800d2e1b65b6fe735a859a401566800878e50cd7c9f4dd48e5be0a61"
)
PARENT_DECISION_SHA256 = (
    "c5dcbea70e72049c284646240738b341ae63442f00a5064a5125978784cdc0c4"
)
PARENT_CONTROL_MANIFEST_SHA256 = (
    "4784cb91995e7ee8d7e158ea6c1241dea25e81d01a76ed9fd02a12a5efc85737"
)
RUNTIME_MANIFEST_SHA256 = (
    "4e394daf67e0bdc7d1fe247d4781945334026c0065ec7666d298f18f4b7180fb"
)
SHARD_ID_SHA256 = {
    "test_s01": "9f4c7bb4e9f63b01b574a52ec840266358dae6d9982dc7caebfeb813eca02dfb",
    "test_s02": "2b48a04896437fdea127e02ad7980f2cb9310db9a16841696affd04796502bbd",
    "test_s03": "abaadc27927a9dbd5ad8cc856513baa85e8c900ed041cf6e5c0978534d103566",
    "devval": "79ba11a41c186daa80e8779e8fa2c1b47e7907f8e398d817dedb43099333d69c",
}
CONTROL_FILES = (
    "src/deepwide_agent/v24220_source_dependency.py",
    "scripts/run_v24220_source_dependency.py",
    "scripts/preregister_v24220_source_dependency.py",
    "scripts/watch_v24220_source_dependency.py",
    "scripts/activate_v24220_source_dependency.py",
    "scripts/audit_v24220_source_dependency_wait.py",
    "tests/test_v24220_source_dependency.py",
    "tests/test_run_v24220_source_dependency.py",
    "tests/test_preregister_v24220_source_dependency.py",
    "tests/test_watch_v24220_source_dependency.py",
    "tests/test_activate_v24220_source_dependency.py",
    "tests/test_audit_v24220_source_dependency_wait.py",
)
FORBIDDEN_CREDENTIAL_LITERALS = (
    "gh" + "p_",
    "github" + "_pat_",
    "tvly" + "-dev-",
    "s" + "k-",
)
_CREDENTIAL = re.compile(
    r"(?:"
    + "|".join(re.escape(value) for value in FORBIDDEN_CREDENTIAL_LITERALS)
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(root: Path, relative: Path, digest: str | None = None) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.20 preregistration path is noncanonical")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.resolve() != path.absolute()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.42.20 expected an ordinary file: {relative}")
    if digest is not None and file_sha256(path) != digest:
        raise RuntimeError(f"V2.42.20 frozen input drifted: {relative}")
    return path


def _publish_new(path: Path, value: dict[str, Any]) -> None:
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


def _parent(root: Path) -> dict[str, Any]:
    protocol = json.loads(
        _ordinary(root, PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256).read_text(
            encoding="utf-8"
        )
    )
    if (
        protocol.get("role") != "v24219_search_time_contamination_preregistration"
        or protocol.get("protocol_id")
        != "v24219_post_terminal_label_blind_stc_audit_v1"
        or protocol.get("decision_contract_sha256") != PARENT_DECISION_SHA256
        or protocol.get("control_surface", {}).get("manifest_sha256")
        != PARENT_CONTROL_MANIFEST_SHA256
        or protocol.get("input_contract", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or protocol.get("authorization", {}).get(
            "network_model_search_fetch_evaluator_or_api_call"
        )
        is not False
    ):
        raise RuntimeError("V2.42.20 parent control identity drifted")
    return {
        "protocol": {"path": str(PARENT_PROTOCOL), "sha256": PARENT_PROTOCOL_SHA256},
        "state_path": str(PARENT_STATE),
        "report_path": str(PARENT_REPORT),
        "accepted_terminal_status": "complete_post_terminal_contamination_audit",
    }


def _partition(root: Path) -> dict[str, Any]:
    rows: dict[str, list[str]] = {}
    contract: dict[str, Any] = {}
    for tag in EXPECTED_SHARDS:
        path = _ordinary(root, SHARD_IDS[tag], SHARD_ID_SHA256[tag])
        rows[tag] = read_opaque_ids(path, EXPECTED_COUNTS[tag])
        contract[tag] = {
            "path": str(SHARD_IDS[tag]),
            "sha256": SHARD_ID_SHA256[tag],
            "count": EXPECTED_COUNTS[tag],
        }
    contract["canonical_opaque_partition_sha256"] = validate_exact_partition(rows)
    return contract


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.20 preregistration boundary drifted")
    parent = _parent(root)
    _ordinary(root, MANIFEST, RUNTIME_MANIFEST_SHA256)
    partition = _partition(root)
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (PROTOCOL, STATE, ACTIVATION, WAIT_AUDIT, DETAIL, REPORT)
    ):
        raise RuntimeError("V2.42.20 output namespace is not pristine")
    manifest: dict[str, str] = {}
    for relative in CONTROL_FILES:
        path = _ordinary(root, Path(relative))
        raw = path.read_bytes()
        if _CREDENTIAL.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.42.20 control surface contains a credential literal")
        manifest[relative] = hashlib.sha256(raw).hexdigest()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "parent_contract": parent,
        "input_contract": {
            "canonical_partition": partition,
            "same_task_terminal_evidence_projection": [
                "id",
                "kind",
                "url",
                "source_family",
                "title",
                "text",
                "fingerprint",
            ],
            "runtime_manifest_content_opened": False,
            "question_query_prediction_or_renderer_output_read": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "only_visited_page_kind_enters_width": True,
        },
        "estimator_contract": {
            "hard_edges": [
                "same_canonical_url",
                "exact_content",
                "near_duplicate_content",
                "redirect_equivalent",
                "cross_family_path_content_mirror",
            ],
            "near_duplicate_character_shingle_size": CHAR_SHINGLE_SIZE,
            "near_duplicate_minimum_chars": MIN_NEAR_DUPLICATE_CHARS,
            "near_duplicate_minimum_length_ratio": MIN_NEAR_DUPLICATE_LENGTH_RATIO,
            "near_duplicate_jaccard_threshold": NEAR_DUPLICATE_JACCARD,
            "near_duplicate_containment_threshold": NEAR_DUPLICATE_CONTAINMENT,
            "minimum_shared_quote_chars": MIN_SHARED_QUOTE_CHARS,
            "soft_pairwise_rho": {
                "same_source_family": SAME_FAMILY_RHO,
                "shared_quoted_span": SHARED_QUOTE_RHO,
                "shared_structured_record": SHARED_STRUCTURED_RECORD_RHO,
                "cross_family_path_mirror": PATH_MIRROR_RHO,
            },
            "effective_width_formula": "n_hard^2 / (n_hard + 2 * sum(max_pairwise_soft_rho))",
            "same_host_or_family_alone_never_forms_hard_cluster": True,
            "structured_record_reuse_is_soft_not_confirmed_mirror": True,
            "dependency_adjusted_width_is_sensitivity_not_correctness": True,
        },
        "execution": {
            "runner": "scripts/run_v24220_source_dependency.py",
            "watcher": "scripts/watch_v24220_source_dependency.py",
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "wait_audit_path": str(WAIT_AUDIT),
            "post_v24219_terminal_only": True,
            "create_exclusive_detail": str(DETAIL),
            "create_exclusive_report": str(REPORT),
            "rerun_or_resume_allowed": False,
        },
        "reporting_contract": {
            "official_primary_denominator": 220,
            "official_primary_result_unchanged": True,
            "sample_exclusion_score_or_prediction_recomputation": False,
            "private_detail_emits_no_question_query_page_text_raw_url_evidence_id_or_task_id": True,
            "public_aggregate_emits_no_question_query_page_text_raw_url_evidence_id_or_task_id": True,
            "persisted_query_focused_evidence_not_full_raw_page_limitation": True,
        },
        "authorization": {
            "offline_post_terminal_read_only_audit": True,
            "network_model_search_fetch_evaluator_or_api_call": False,
            "shared_api_lease_acquire": False,
            "forward_result_evaluator_or_watcher_modification": False,
            "benchmark_forward_or_full220_launch": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha256(manifest),
            "v24218_or_v24219_control_surface_modified": False,
        },
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def validate_protocol(
    root: Path = ROOT, path: Path = PROTOCOL
) -> dict[str, Any]:
    target = _ordinary(root, path)
    value = json.loads(target.read_text(encoding="utf-8"))
    unsigned = dict(value)
    decision = unsigned.pop("decision_contract_sha256", None)
    manifest = (value.get("control_surface") or {}).get("manifest")
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(manifest, dict)
        or value.get("control_surface", {}).get("file_count") != len(CONTROL_FILES)
        or tuple(manifest) != CONTROL_FILES
        or value.get("control_surface", {}).get("manifest_sha256")
        != payload_sha256(manifest)
        or decision != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.20 protocol identity drifted")
    for relative, digest in manifest.items():
        if file_sha256(_ordinary(root, Path(relative))) != digest:
            raise RuntimeError("V2.42.20 control bytes drifted")
    return {"value": value, "sha256": file_sha256(target)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(PROTOCOL))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / PROTOCOL).resolve(strict=False):
        raise RuntimeError("V2.42.20 protocol output drifted")
    value = build_protocol()
    _publish_new(target, value)
    verified = validate_protocol(ROOT, PROTOCOL)
    print(
        json.dumps(
            {
                "path": str(target),
                "sha256": verified["sha256"],
                "decision_contract_sha256": value["decision_contract_sha256"],
                "control_manifest_sha256": value["control_surface"]["manifest_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()
