#!/usr/bin/env python3
"""Freeze the V2.42.59 label-blind deterministic-normalizer smoke16."""

from __future__ import annotations

import argparse
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

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24257_score_first_smoke import (  # noqa: E402
    ID_SOURCE,
    MANIFEST,
    OUTPUT as PARENT_PROTOCOL,
    _ordinary,
    _read_object,
    _selected_ids,
    validate_protocol as validate_parent_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    sha256,
)


ROLE = "v24259_deterministic_normalizer_smoke_preregistration"
PROTOCOL_ID = "v24259_deterministic_normalizer_smoke16_v1"
OUTPUT = Path(
    "results/v24259_deterministic_normalizer_smoke_preregistration_v1_20260802.json"
)
ACTIVATION = Path(
    "results/v24259_deterministic_normalizer_smoke_activation_v1_20260802.json"
)
EXECUTION_START = Path(
    "results/v24259_deterministic_normalizer_smoke_execution_start_v1_20260802.json"
)
OUTPUT_ROOT = Path("outputs/v24259_deterministic_normalizer_smoke16_v1_20260802")
RESULT = Path(
    "results/v24259_deterministic_normalizer_smoke_result_v1_20260802.json"
)
STATE = Path(
    "outputs/v24259_deterministic_normalizer_smoke_watcher_state_v1_20260802.json"
)
PARENT_RESULT = Path("results/v24257_score_first_smoke_result_v1_20260802.json")
PARENT_POSTRESULT_AUDIT = Path(
    "results/v24257_score_first_smoke_audit_v1_20260802_postresult.json"
)
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24259_deterministic_normalizer_smoke16_v1"
LEASE_PURPOSE = "label_blind_deterministic_table_normalizer_smoke16_gate"
RUNNER_MARKER = "scripts/run_v24259_score_first_smoke.py"
WATCHER_MARKER = "scripts/watch_v24259_deterministic_normalizer_smoke.py"
EXPECTED_LEGACY_ACTIVE_FINDING = "v24195:unknown_lease_owner"
CONTROL_FILES = (
    Path("src/deepwide_agent/v24259_deterministic_table_normalizer.py"),
    Path("scripts/run_v24259_score_first_task.py"),
    Path("scripts/run_v24259_score_first_smoke.py"),
    Path("scripts/preregister_v24259_deterministic_normalizer_smoke.py"),
    Path("scripts/activate_v24259_deterministic_normalizer_smoke.py"),
    Path("scripts/audit_v24259_deterministic_normalizer_smoke.py"),
    Path("scripts/watch_v24259_deterministic_normalizer_smoke.py"),
    Path("tests/test_v24259_deterministic_table_normalizer.py"),
    Path("tests/test_run_v24259_score_first_smoke.py"),
    Path("tests/test_v24259_deterministic_normalizer_protocol.py"),
    Path("tests/test_audit_v24259_deterministic_normalizer_smoke.py"),
)
FUTURE_PATHS = (ACTIVATION, EXECUTION_START, OUTPUT_ROOT, RESULT, STATE)
SECRET_LITERAL = re.compile(
    r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_LITERAL = re.compile(r"task_[0-9a-f]{24}")


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _matching(rows: list[dict[str, Any]], marker: str) -> list[int]:
    values: list[int] = []
    for row in rows:
        script = actual_python_script([str(item) for item in row.get("argv") or []])
        if script and (script == marker or script.endswith("/" + marker)):
            values.append(int(row["pid"]))
    return sorted(values)


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = validate_parent_protocol(root, PARENT_PROTOCOL)
    result = _read_object(_ordinary(root, PARENT_RESULT))
    audit = _read_object(_ordinary(root, PARENT_POSTRESULT_AUDIT))
    if (
        result.get("role") != "v24257_score_first_smoke_result"
        or result.get("protocol_id") != protocol["protocol_id"]
        or result.get("selected") != 16
        or result.get("terminal") != 16
        or result.get("model_generated_tables") != 14
        or result.get("fallback_tables") != 2
        or result.get("engineering_gate") != "no_go"
        or result.get("mapping_gold_category_question_type_evaluator_score_read")
        is not False
        or result.get("official_evaluator_called") is not False
        or not _sealed(result, "result_payload_sha256")
        or audit.get("role") != "v24257_score_first_smoke_audit"
        or audit.get("audit_valid") is not True
        or audit.get("result", {}).get("present") is not True
        or audit.get("claims", {}).get("benchmark_improvement_observed") is not False
    ):
        raise RuntimeError("V2.42.59 parent terminal evidence drifted")
    return protocol, result


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    proc_root: Path = Path("/proc"),
    processes: list[dict[str, Any]] | None = None,
    observed_lease: dict[str, Any] | None = None,
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    parent_protocol, parent_result = _parent(root)
    rows = process_snapshot(proc_root) if processes is None else processes
    lease = (
        lease_observation(root, proc_root)
        if observed_lease is None
        else dict(observed_lease)
    )
    present = [
        str(path)
        for path in FUTURE_PATHS
        if (root / path).exists() or (root / path).is_symlink()
    ]
    if require_pristine and present:
        raise RuntimeError("V2.42.59 future execution surface is not pristine")
    if (
        lease.get("active") is not False
        or lease.get("ordinary") is not True
        or _matching(rows, RUNNER_MARKER)
        or _matching(rows, WATCHER_MARKER)
    ):
        raise RuntimeError("V2.42.59 process or lease boundary is not clean")
    selected = _selected_ids(root)
    if payload_sha256(selected) != parent_protocol["task_contract"][
        "selected_opaque_ids_sha256"
    ]:
        raise RuntimeError("V2.42.59 selected task identity drifted")
    limits = ScoreFirstLimits(**dict(parent_protocol["limits"]))
    limits.validate()
    manifest: dict[str, str] = {}
    for relative in CONTROL_FILES:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET_LITERAL.search(source):
            raise RuntimeError(f"V2.42.59 control contains a credential: {relative}")
        if not str(relative).startswith("tests/") and OPAQUE_LITERAL.search(source):
            raise RuntimeError(f"V2.42.59 control contains an opaque ID: {relative}")
        manifest[str(relative)] = sha256(path)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "label_blind": True,
        "parents": {
            "protocol": {"path": str(PARENT_PROTOCOL), "sha256": sha256(root / PARENT_PROTOCOL)},
            "result": {"path": str(PARENT_RESULT), "sha256": sha256(root / PARENT_RESULT)},
            "postresult_audit": {
                "path": str(PARENT_POSTRESULT_AUDIT),
                "sha256": sha256(root / PARENT_POSTRESULT_AUDIT),
            },
            "no_go": {
                "model_generated_tables": parent_result["model_generated_tables"],
                "fallback_tables": parent_result["fallback_tables"],
                "findings": parent_result["findings"],
            },
        },
        "single_change": {
            "mechanism": "deterministic_visible_column_markdown_normalization_before_model_repair",
            "allowed": [
                "canonical_pipe_frame_and_separator",
                "exact_visible_header_reorder",
                "equal_arity_visible_header_replacement",
                "generic_index_column_drop",
                "empty_cell_explicit_unknown_marker",
            ],
            "nonempty_factual_cell_rewrite": False,
            "partial_malformed_row_deletion": False,
            "ambiguous_extra_column_drop": False,
            "model_prompt_search_provider_budget_selection_and_gate_unchanged": True,
        },
        "task_contract": {
            **parent_protocol["task_contract"],
            "manifest": {
                "path": str(MANIFEST),
                "sha256": sha256(_ordinary(root, MANIFEST)),
                "row_schema": ["opaque_id", "question"],
            },
            "id_source": {
                "path": str(ID_SOURCE),
                "sha256": sha256(_ordinary(root, ID_SOURCE)),
            },
            "selection_rule": "same_frozen_first_16_devval_ids_as_v24257_full_fresh_cold_start",
            "selected_opaque_ids_sha256": payload_sha256(selected),
            "selective_parent_failure_rerun": False,
        },
        "limits": dict(parent_protocol["limits"]),
        "provider_contract": dict(parent_protocol["provider_contract"]),
        "gate_contract": {
            **parent_protocol["gate_contract"],
            "model_generated_kinds": [
                "primary",
                "repaired",
                "normalized_primary",
                "normalized_repaired",
            ],
            "normalized_table_requires_no_nonempty_factual_cell_rewrite": True,
        },
        "lease_contract": {
            "path": str(LEASE),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_posix_flock_required": True,
            "single_owner_across_all_16_tasks": True,
            "legacy_expected_finding": EXPECTED_LEGACY_ACTIVE_FINDING,
            "suppress_only_when_exact_runner_identity_valid": True,
        },
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "task_runner_marker": "scripts/run_v24259_score_first_task.py",
            "watcher_marker": WATCHER_MARKER,
            "activation_path": str(ACTIVATION),
            "execution_start_path": str(EXECUTION_START),
            "output_root": str(OUTPUT_ROOT),
            "result_path": str(RESULT),
            "watcher_state_path": str(STATE),
            "executor_concurrency": 1,
            "parent_deadline_grace_seconds": 5,
            "forward_resume_or_selective_rerun_allowed": False,
            "result_overwrite_allowed": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "visible_question_same_pass_candidate_and_tool_results_only": True,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_tuning": False,
            "question_query_url_page_prediction_or_answer_in_safe_progress": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "activation_publish_after_protocol_freeze": True,
            "single_fresh_smoke16_forward_after_activation_and_shared_lease": True,
            "process_signal_restart_resume_skip_or_selective_retry": False,
            "official_evaluator_call": False,
            "paired_dev64_or_full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "safe_freeze_boundary": {
            "future_paths_present": present,
            "shared_api_lease_active": False,
            "existing_benchmark_or_watcher_signaled_restarted_modified_or_terminated": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha256(manifest),
        },
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    value = _read_object(_ordinary(root, path))
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or not _sealed(value, "decision_contract_sha256")
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_evaluator_score_read"
        )
        is not False
    ):
        raise RuntimeError("V2.42.59 protocol drifted")
    manifest = value.get("control_surface", {}).get("manifest") or {}
    if (
        not isinstance(manifest, dict)
        or value["control_surface"].get("file_count") != len(manifest)
        or value["control_surface"].get("manifest_sha256")
        != payload_sha256(manifest)
    ):
        raise RuntimeError("V2.42.59 control manifest drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, Path(relative))) != digest:
            raise RuntimeError(f"V2.42.59 control source drifted: {relative}")
    ScoreFirstLimits(**dict(value["limits"])).validate()
    _parent(root)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to((ROOT / "results").resolve()):
        raise RuntimeError("V2.42.59 protocol output is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    publish_new(ROOT / OUTPUT, build_protocol())
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}))


if __name__ == "__main__":
    main()
