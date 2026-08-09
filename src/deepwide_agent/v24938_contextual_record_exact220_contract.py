"""Frozen label-blind exact-220 contract for contextual-record projection.

Relative to the V2.49.35 cold replication, this exploratory successor changes
only the evidence projector from the Unicode-total V2.49.28 policy to the
Unicode-total contextual-record V2.49.33 policy.  The public 220-task vector,
model, transport, budgets, and 20-by-8 capacity are unchanged.

V2.49.37 ended in a ceiling tie (24/24 exact in both arms) and did not authorize
an exact-220 launch.  This contract preserves that fact.  The launch authority
is the user's later explicit request for one complete exploratory run; it is
not represented as an external-gate GO.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import v24928_unicode_total_visible_row_compactor as legacy_projector
from . import v24933_contextual_record_value_projector as projector
from . import v24935_unicode_total_replication_contract as parent
from . import v24635_exact220_contract as root_contract


DATE = "20260809"
ROLE = "v24938_contextual_record_exact220_preregistration"
PROTOCOL_ID = "v24938_keyless_contextual_record_exact220_exploratory_v1"
PROTOCOL = Path(f"results/v24938_contextual_record_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24938_contextual_record_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24938_contextual_record_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24938_contextual_record_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24938_contextual_record_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24938_contextual_record_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
PROJECTION_RECEIPT_NAME = "contextual_record_projection_receipt.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24938_contextual_record_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_contextual_record_keyless_exact220_exploratory"
RUNNER_MARKER = "scripts/run_v24938_contextual_record_exact220.py"
CHILD_MARKER = "scripts/run_v24938_contextual_record_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
PROJECTOR_SOURCE = Path("src/deepwide_agent/v24933_contextual_record_value_projector.py")
PROJECTOR_AUDIT = Path("results/v24933_contextual_record_value_build_audit_v1_20260809.json")
LEGACY_PROJECTOR_SOURCE = parent.PROJECTOR_SOURCE
TARGET_VALUE_SOURCE = parent.TARGET_VALUE_SOURCE
EXTERNAL_ERRATUM_RESULT = Path("results/v24936_v24934_identity_evaluator_erratum_result_v1_20260809.json")
EXTERNAL_ERRATUM_POSTAUDIT = Path("results/v24936_v24934_identity_evaluator_erratum_postresult_audit_v1_20260809.json")
EXTERNAL_CEILING_RESULT = Path("results/v24937_layout_diverse_contextual_external_result_v1_20260809.json")
EXTERNAL_CEILING_POSTAUDIT = Path("results/v24937_layout_diverse_contextual_external_postresult_audit_v1_20260809.json")
SOURCE = Path("src/deepwide_agent/v24938_contextual_record_exact220_contract.py")
BINDING = parent.BINDING
CONTROL = Path("scripts/control_v24938_contextual_record_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24938_contextual_record_exact220.py")
TEST = Path("tests/test_v24938_contextual_record_exact220.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.38 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.38 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return parent.protected_watcher_snapshot(proc_root)


@lru_cache(maxsize=1)
def _cached_parent_contract(root_string: str) -> dict[str, Any]:
    root = Path(root_string)
    value = _read(root / PARENT_PROTOCOL)
    unsigned = dict(value)
    seal = unsigned.pop("protocol_payload_sha256", None)
    manifest = value.get("dependency_manifest")
    if (
        value.get("role") != parent.ROLE
        or value.get("protocol_id") != parent.PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or not isinstance(manifest, dict)
        or value.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or any(
            not isinstance(relative, str)
            or not isinstance(digest, str)
            or sha256(parent._ordinary_tracked(root, Path(relative))) != digest
            for relative, digest in manifest.items()
        )
        or value.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        )
        is not False
    ):
        raise RuntimeError("V2.49.38 immutable parent protocol drifted")
    return value


def parent_contract(root: Path) -> dict[str, Any]:
    return copy.deepcopy(_cached_parent_contract(str(root.resolve())))


def _task_contract(tasks: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
        "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
    }


def task_vector(root: Path, protocol: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    parent_value = parent_contract(root)
    base = root_contract.validate_forward_contract(root)
    tasks = root_contract.selected_tasks(root, base)
    if len(tasks) != 220 or any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.49.38 visible exact-220 vector drifted")
    if parent_value.get("task_contract") != _task_contract(tasks):
        raise RuntimeError("V2.49.38 immutable parent task binding drifted")
    if protocol is not None and protocol.get("task_contract") != _task_contract(tasks):
        raise RuntimeError("V2.49.38 visible task binding drifted")
    return tasks


def _validate_evidence_chain(root: Path) -> dict[str, Any]:
    audit = _read(root / PROJECTOR_AUDIT)
    checks = audit.get("checks") or {}
    policy = audit.get("source_policy") or {}
    manifest = audit.get("source_manifest") or {}
    if (
        audit.get("role") != "v24933_contextual_record_value_build_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or checks.get("focused_tests_exact10") is not True
        or checks.get("synthetic_contextual_mechanism_reachable") is not True
        or checks.get("fixed_30k_total_and_5k_page_caps") is not True
        or checks.get("runtime_forbidden_import_zero") is not True
        or checks.get("runtime_dynamic_or_io_call_zero") is not True
        or checks.get("credential_literal_zero") is not True
        or checks.get("entropy_assigns_no_credit") is not True
        or policy.get("visible_question_and_same_forward_pages_only") is not True
        or policy.get("entropy_or_information_gain_assigns_credit") is not False
        or audit.get("authorization", {}).get("public_dev64_or_exact220") is not False
        or manifest.get(str(PROJECTOR_SOURCE)) != sha256(root / PROJECTOR_SOURCE)
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.38 projector build evidence drifted")

    erratum = _read(root / EXTERNAL_ERRATUM_RESULT)
    erratum_post = _read(root / EXTERNAL_ERRATUM_POSTAUDIT)
    ceiling = _read(root / EXTERNAL_CEILING_RESULT)
    ceiling_post = _read(root / EXTERNAL_CEILING_POSTAUDIT)
    if (
        erratum.get("status") != "corrected_external_go"
        or erratum.get("passed") is not True
        or not _sealed(erratum, "result_payload_sha256")
        or erratum_post.get("audit_valid") is not True
        or erratum_post.get("findings") != []
        or not _sealed(erratum_post, "audit_payload_sha256")
        or ceiling.get("status") != "layout_diverse_contextual_external_no_go"
        or ceiling.get("passed") is not False
        or ceiling.get("metrics", {}).get("arms", {}).get("parent_30k", {}).get("exact_table_successes") != 24
        or ceiling.get("metrics", {}).get("arms", {}).get("target_value_30k", {}).get("exact_table_successes") != 24
        or ceiling.get("authorization", {}).get("public_exact220_launch") is not False
        or not _sealed(ceiling, "result_payload_sha256")
        or ceiling_post.get("audit_valid") is not True
        or ceiling_post.get("findings") != []
        or not _sealed(ceiling_post, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.38 external evidence chain drifted")
    return {
        "projector_build_audit_valid": True,
        "corrected_external_mechanism_go_valid": True,
        "layout_diverse_external_ceiling_tie_valid": True,
        "external_gate_authorized_public_exact220": False,
    }


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update(
        (
            PARENT_PROTOCOL,
            PROJECTOR_SOURCE,
            PROJECTOR_AUDIT,
            LEGACY_PROJECTOR_SOURCE,
            TARGET_VALUE_SOURCE,
            EXTERNAL_ERRATUM_RESULT,
            EXTERNAL_ERRATUM_POSTAUDIT,
            EXTERNAL_CEILING_RESULT,
            EXTERNAL_CEILING_POSTAUDIT,
            *LOCAL_SOURCES,
        )
    )
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def _single_change() -> dict[str, Any]:
    equalities = {
        "selected_count_equal_parent": SELECTED_COUNT == parent.SELECTED_COUNT == 220,
        "executor_concurrency_equal_parent": EXECUTOR_CONCURRENCY == parent.EXECUTOR_CONCURRENCY == 20,
        "model_slot_cap_equal_parent": MODEL_SLOT_CAP == parent.MODEL_SLOT_CAP == 8,
        "limits_equal_parent": LIMITS == parent.LIMITS,
        "model_equal_parent": MODEL == parent.MODEL,
        "search_equal_parent": SEARCH == parent.SEARCH,
        "two_wave_policy_equal_parent": TWO_WAVE_POLICY == parent.TWO_WAVE_POLICY,
    }
    if not all(equalities.values()):
        raise RuntimeError("V2.49.38 parent equality drifted")
    return {
        "field": "evidence_projector",
        "from": legacy_projector.POLICY_ID,
        "to": projector.POLICY_ID,
        "change": "carry bounded visible target context to following value-bearing records",
        "same_forward_page_bytes_only": True,
        "additional_search_fetch_model_token_context_or_wall_cap": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "equalities": equalities,
    }


def build_protocol(
    root: Path,
    *,
    now: int,
    require_clean: bool = True,
    require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        _git(root, "status", "--porcelain")
        or _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.49.38 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.49.38 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    evidence = _validate_evidence_chain(root)
    manifest = dependency_manifest(root)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": _git(root, "rev-parse", "HEAD"),
        "parent_algorithm": {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        },
        "projector": {
            "policy_id": projector.POLICY_ID,
            "source": str(PROJECTOR_SOURCE),
            "source_sha256": sha256(root / PROJECTOR_SOURCE),
            "build_audit": str(PROJECTOR_AUDIT),
            "build_audit_sha256": sha256(root / PROJECTOR_AUDIT),
            "total_character_cap": 30_000,
            "per_page_character_cap": 5_000,
            "visible_question_and_same_forward_pages_only": True,
            "content_free_per_task_receipt": True,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "external_evidence": evidence,
        "task_contract": _task_contract(tasks),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "task_wall_seconds": LIMITS["wall_seconds"],
            "model_calls_per_task": LIMITS["model_calls"],
            "search_queries_per_task": LIMITS["search_queries"],
            "fetch_targets_per_task": LIMITS["fetch_targets"],
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "two_wave_policy": copy.deepcopy(TWO_WAVE_POLICY),
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": _single_change(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_benchmark_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "unseen_heldout_or_disjoint_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
            "v24937_external_gate_no_go_and_no_launch_authorization_preserved": True,
            "explicit_user_request_after_external_ceiling_authorizes_one_exploratory_exact220": True,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value, manifest=manifest, tasks=tasks)


def validate_protocol(
    root: Path,
    value: Mapping[str, Any],
    *,
    manifest: Mapping[str, str] | None = None,
    tasks: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    base = parent_contract(root)
    tasks = task_vector(root) if tasks is None else tasks
    manifest = dependency_manifest(root) if manifest is None else dict(manifest)
    execution = copied.get("execution") or {}
    projection = copied.get("projector") or {}
    policy = copied.get("source_policy") or {}
    evidence = _validate_evidence_chain(root)
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("parent_algorithm") != {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        }
        or copied.get("task_contract") != _task_contract(tasks)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("external_evidence") != evidence
        or projection.get("policy_id") != projector.POLICY_ID
        or projection.get("source_sha256") != sha256(root / PROJECTOR_SOURCE)
        or projection.get("build_audit_sha256") != sha256(root / PROJECTOR_AUDIT)
        or projection.get("total_character_cap") != 30_000
        or projection.get("per_page_character_cap") != 5_000
        or projection.get("entropy_or_information_gain_assigns_credit") is not False
        or execution.get("executor_concurrency") != 20
        or execution.get("model_slot_cap") != 8
        or execution.get("task_wall_seconds") != 240
        or execution.get("model_calls_per_task") != 3
        or execution.get("search_queries_per_task") != 4
        or execution.get("fetch_targets_per_task") != 10
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy") != TWO_WAVE_POLICY
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or copied.get("single_change") != _single_change()
        or policy.get("mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward") is not False
        or policy.get("v24937_external_gate_no_go_and_no_launch_authorization_preserved") is not True
        or policy.get("explicit_user_request_after_external_ceiling_authorizes_one_exploratory_exact220") is not True
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.49.38 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "parent_contract",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sha256",
    "task_vector",
    "validate_protocol",
]
