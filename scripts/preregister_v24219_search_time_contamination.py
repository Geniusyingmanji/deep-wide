#!/usr/bin/env python3
"""Freeze the post-terminal, label-blind V2.42.19 STC audit."""

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
from deepwide_agent.v24219_search_time_contamination import (  # noqa: E402
    MIN_QCL_CHARS,
    PRIMARY_QCL_RATIO,
    QCL_SENSITIVITY_RATIOS,
    payload_sha256,
)
from scripts.run_v24219_search_time_contamination import (  # noqa: E402
    DETAIL,
    FORWARD_BARRIER,
    MANIFEST,
    PROTOCOL,
    REPORT,
    RESULT,
    SHARD_IDS,
)


ROLE = "v24219_search_time_contamination_preregistration"
PROTOCOL_ID = "v24219_post_terminal_label_blind_stc_audit_v1"
STATE = Path("outputs/v24219_search_time_contamination_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24219_search_time_contamination_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24219_search_time_contamination_wait_audit_v1_20260731.json")
PARENT_PROTOCOL = Path("results/v24218_exact220_executor_preregistration_v1_20260731.json")
PARENT_PROTOCOL_SHA256 = (
    "99b1d7bda8468e3464b347aadb74f2174b0832a29fd5e398f4319b931e1d9667"
)
PARENT_ACTIVATION = Path("results/v24218_exact220_executor_activation_v1_20260731.json")
PARENT_ACTIVATION_SHA256 = (
    "28fe50a2bcb3f2597b41152dc3fad03d7da19573adf74a313a9ea20ce68958aa"
)
PARENT_WAIT_AUDIT = Path("results/v24218_exact220_executor_wait_audit_v1_20260731.json")
PARENT_WAIT_AUDIT_SHA256 = (
    "8a69fc9962646bc7e8ee720b5999a5427a20fbdcf77bf5e8a1b5ab596f65eb18"
)
PARENT_STATE = Path("outputs/v24218_exact220_executor_watcher_state_v1_20260731.json")
PARENT_CONTROL_MANIFEST_SHA256 = (
    "61612a55fd390d7694412ded0fde091fc91f6b812d94ea23368beb26a299e102"
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
    "src/deepwide_agent/v24219_search_time_contamination.py",
    "scripts/run_v24219_search_time_contamination.py",
    "scripts/preregister_v24219_search_time_contamination.py",
    "scripts/watch_v24219_search_time_contamination.py",
    "scripts/activate_v24219_search_time_contamination.py",
    "scripts/audit_v24219_search_time_contamination_wait.py",
    "tests/test_v24219_search_time_contamination.py",
    "tests/test_run_v24219_search_time_contamination.py",
    "tests/test_preregister_v24219_search_time_contamination.py",
    "tests/test_watch_v24219_search_time_contamination.py",
    "tests/test_activate_v24219_search_time_contamination.py",
    "tests/test_audit_v24219_search_time_contamination_wait.py",
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
        raise RuntimeError("V2.42.19 preregistration path is noncanonical")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.resolve() != path.absolute()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.42.19 expected an ordinary file: {relative}")
    if digest is not None and file_sha256(path) != digest:
        raise RuntimeError(f"V2.42.19 frozen input drifted: {relative}")
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
        _ordinary(root, PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256).read_text(encoding="utf-8")
    )
    activation = json.loads(
        _ordinary(root, PARENT_ACTIVATION, PARENT_ACTIVATION_SHA256).read_text(encoding="utf-8")
    )
    wait = json.loads(
        _ordinary(root, PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256).read_text(encoding="utf-8")
    )
    if (
        protocol.get("protocol_id")
        != "v24218_post_capacity_single_owner_fresh_exact220_v1"
        or protocol.get("control_surface", {}).get("manifest_sha256")
        != PARENT_CONTROL_MANIFEST_SHA256
        or protocol.get("source_policy", {}).get(
            "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_route"
        )
        is not False
        or activation.get("role") != "v24218_exact220_executor_activation"
        or activation.get("leaderboard_submission_or_sota_claim") is not False
        or wait.get("role") != "v24218_exact220_executor_wait_audit"
        or wait.get("boundary", {}).get("benchmark_forward_called") is not False
    ):
        raise RuntimeError("V2.42.19 parent control identity drifted")
    return {
        "protocol": {"path": str(PARENT_PROTOCOL), "sha256": PARENT_PROTOCOL_SHA256},
        "activation": {"path": str(PARENT_ACTIVATION), "sha256": PARENT_ACTIVATION_SHA256},
        "wait_audit": {"path": str(PARENT_WAIT_AUDIT), "sha256": PARENT_WAIT_AUDIT_SHA256},
        "state_path": str(PARENT_STATE),
        "forward_barrier_path": str(FORWARD_BARRIER),
        "result_path": str(RESULT),
        "accepted_terminal_status": "complete_exact220_local_result_released_not_sota",
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
    root: Path = ROOT, *, created_at_unix: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.19 preregistration boundary drifted")
    parent = _parent(root)
    _ordinary(root, MANIFEST, RUNTIME_MANIFEST_SHA256)
    partition = _partition(root)
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (PROTOCOL, STATE, ACTIVATION, WAIT_AUDIT, DETAIL, REPORT)
    ):
        raise RuntimeError("V2.42.19 output namespace is not pristine")
    manifest: dict[str, str] = {}
    for relative in CONTROL_FILES:
        path = _ordinary(root, Path(relative))
        raw = path.read_bytes()
        if _CREDENTIAL.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.42.19 control surface contains a credential literal")
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
            "runtime_manifest": {"path": str(MANIFEST), "sha256": RUNTIME_MANIFEST_SHA256},
            "canonical_partition": partition,
            "runtime_visible_fields": ["opaque_id", "question"],
            "same_task_terminal_evidence_projection": [
                "id",
                "kind",
                "url",
                "source_family",
                "title",
                "text",
                "fingerprint",
            ],
            "query_fields_read": False,
            "prediction_or_renderer_output_used": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        },
        "detector_contract": {
            "taxonomy_source": "Wang et al. arXiv:2606.05241v1",
            "bml": "artifact/dataset URL, benchmark marker, or opaque-ID exposure",
            "qcl": "longest normalized contiguous question substring divided by normalized question length",
            "primary_qcl_ratio": PRIMARY_QCL_RATIO,
            "minimum_qcl_contiguous_chars": MIN_QCL_CHARS,
            "qcl_sensitivity_ratios": list(QCL_SENSITIVITY_RATIOS),
            "paper_did_not_publish_a_portable_qcl_threshold": True,
            "query_question_overlap_is_not_a_contamination_signal": True,
            "eal_requires_exact_question_and_corresponding_gold_answer_pair": True,
            "gold_is_unavailable_so_automatic_eal_confirmation": False,
            "report_only_eal_candidate_and_manual_review_flag": True,
        },
        "execution": {
            "runner": "scripts/run_v24219_search_time_contamination.py",
            "watcher": "scripts/watch_v24219_search_time_contamination.py",
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "wait_audit_path": str(WAIT_AUDIT),
            "post_terminal_only": True,
            "parent_result_and_forward_barrier_must_both_be_sealed": True,
            "create_exclusive_detail": str(DETAIL),
            "create_exclusive_report": str(REPORT),
            "rerun_or_resume_allowed": False,
        },
        "reporting_contract": {
            "official_primary_denominator": 220,
            "official_primary_result_unchanged": True,
            "sample_exclusion_or_score_recomputation": False,
            "contamination_sensitive_subset_separate_from_primary": True,
            "private_detail_emits_no_raw_question_query_page_text_url_or_task_id": True,
            "public_aggregate_emits_no_question_query_page_text_url_or_task_id": True,
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
            "v24218_control_surface_modified": False,
        },
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path = ROOT, path: Path = PROTOCOL) -> dict[str, Any]:
    target = _ordinary(root, path)
    observed = json.loads(target.read_text(encoding="utf-8"))
    created = observed.get("created_at_unix")
    if isinstance(created, bool) or not isinstance(created, int):
        raise RuntimeError("V2.42.19 protocol timestamp is invalid")
    expected = build_protocol(root, created_at_unix=created, require_pristine=False)
    if observed != expected:
        raise RuntimeError("V2.42.19 protocol differs from live replay")
    return {"value": observed, "sha256": file_sha256(target)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(PROTOCOL))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / PROTOCOL).resolve(strict=False):
        raise RuntimeError("V2.42.19 protocol output drifted")
    value = build_protocol()
    _publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": file_sha256(target)}))


if __name__ == "__main__":
    main()
