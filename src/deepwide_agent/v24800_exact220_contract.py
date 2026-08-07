"""Fresh V2.47.98 successor with fixed full-budget retrieval admission."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24798_exact220_contract as parent
from . import v24799_fixed_full_budget_control as full_budget


DATE = "20260807"
ROLE = "v24800_exact220_preregistration"
PROTOCOL_ID = "v24800_fixed_full_budget_no_entropy_exact220_v1"
PROTOCOL = Path(f"results/v24800_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24800_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24800_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24800_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24800_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24800_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
KEY_SLOT_DIRECTORY = OUTPUT_ROOT / "tavily_key_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24800_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_fixed_full_budget_no_entropy_exact220"
RUNNER_MARKER = "scripts/run_v24800_exact220.py"
CHILD_MARKER = "scripts/run_v24800_exact220_task.py"
DIRECT_RECEIPT_NAME = "direct_search_receipt.json"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
TAVILY_KEY_SLOT_CAP = 12
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(full_budget.POLICY_VALUES)
POLICY_CHANGE_KEYS = (
    "content_chars_per_column",
    "information_gain_weight",
    "latency_loss_per_second",
    "minimum_net_value",
    "minimum_novel_pages",
    "minimum_unique_hosts",
    "minimum_usable_pages",
)
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)
PARENT_PROTOCOL = parent.PROTOCOL
CONTROL_GATE = Path(
    "results/v24799_fixed_full_budget_control_build_audit_v1_20260807.json"
)
CONTROL_POLICY_SOURCE = Path(
    "src/deepwide_agent/v24799_fixed_full_budget_control.py"
)
CONTROL_POLICY_TEST = Path("tests/test_v24799_fixed_full_budget_control.py")
CONTROL_GATE_SCRIPT = Path("scripts/audit_v24799_fixed_full_budget_control.py")
SMOKE_PROTOCOL = Path("results/v24797_tavily_transport_smoke_preregistration_v1_20260807.json")
SMOKE_RESULT = Path("results/v24797_tavily_transport_smoke_result_v1_20260807.json")
SOURCE = Path("src/deepwide_agent/v24800_exact220_contract.py")
TRANSPORT = Path("src/deepwide_agent/v24796_deadline_tavily_search.py")
CONTROL = Path("scripts/control_v24800_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
TEST = Path("tests/test_v24800_exact220.py")
TRANSPORT_TEST = Path("tests/test_v24796_deadline_tavily_search.py")
FINALIZER = Path("scripts/finalize_v24800_exact220.py")
FINALIZER_TEST = Path("tests/test_finalize_v24800_exact220.py")
LOCAL_SOURCES = (
    SOURCE, TRANSPORT, CONTROL, RUNNER, CHILD, TEST, TRANSPORT_TEST,
    FINALIZER, FINALIZER_TEST, CONTROL_POLICY_SOURCE, CONTROL_POLICY_TEST,
    CONTROL_GATE_SCRIPT,
)


def validate_single_change() -> dict[str, Any]:
    parent_policy = parent.TWO_WAVE_POLICY
    changed = tuple(
        sorted(
            key
            for key in set(parent_policy) | set(TWO_WAVE_POLICY)
            if parent_policy.get(key) != TWO_WAVE_POLICY.get(key)
        )
    )
    if (
        LIMITS != parent.LIMITS
        or MODEL != parent.MODEL
        or SEARCH != parent.SEARCH
        or SELECTED_COUNT != parent.SELECTED_COUNT
        or EXECUTOR_CONCURRENCY != parent.EXECUTOR_CONCURRENCY
        or MODEL_SLOT_CAP != parent.MODEL_SLOT_CAP
        or TWO_WAVE_POLICY != full_budget.POLICY_VALUES
        or changed != POLICY_CHANGE_KEYS
    ):
        raise RuntimeError("V2.48.00 single-change invariant drifted")
    return {
        "limits_equal_v24798": True,
        "model_equal_v24798": True,
        "search_equal_v24798": True,
        "selected_executor_and_model_slots_equal_v24798": True,
        "policy_changed_fields": list(POLICY_CHANGE_KEYS),
    }


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.48.00 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.00 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _ordinary_tracked(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.parts[:1] in {("evaluation",), ("outputs",)}
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
        or subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode != 0
    ):
        raise RuntimeError(f"V2.48.00 expected tracked source: {relative}")
    return path


def parent_contract(root: Path) -> dict[str, Any]:
    return parent.validate_protocol(root, _read(root / PARENT_PROTOCOL))


def validate_smoke(root: Path) -> dict[str, Any]:
    protocol = _read(root / SMOKE_PROTOCOL)
    result = _read(root / SMOKE_RESULT)
    observed = result.get("observed") or {}
    receipt = result.get("direct_search_receipt") or {}
    if (
        protocol.get("role") != "v24797_tavily_transport_smoke_preregistration"
        or protocol.get("authorization", {}).get("one_neutral_tavily_live_smoke") is not True
        or not _sealed(protocol, "protocol_payload_sha256")
        or result.get("role") != "v24797_tavily_transport_smoke_result"
        or result.get("protocol_sha256") != sha256(root / SMOKE_PROTOCOL)
        or result.get("passed") is not True
        or result.get("authorization", {}).get("exact220_protocol_design") is not True
        or observed.get("credential_count") != TAVILY_KEY_SLOT_CAP
        or observed.get("successful_query_rows") != 12
        or observed.get("failed_query_rows") != 0
        or observed.get("projected_url_leads") != 36
        or observed.get("usable_fetched_pages", 0) < 12
        or receipt.get("key_slot_cap") != TAVILY_KEY_SLOT_CAP
        or receipt.get("slot_timeouts") != 0
        or receipt.get("credential_echo_rejections") != 0
        or receipt.get("credential_value_persisted_hashed_emitted_or_in_error") is not False
        or not _sealed(result, "result_payload_sha256")
    ):
        raise RuntimeError("V2.48.00 neutral Tavily smoke drifted")
    return {
        "protocol_sha256": sha256(root / SMOKE_PROTOCOL),
        "result_sha256": sha256(root / SMOKE_RESULT),
        "result_payload_sha256": result["result_payload_sha256"],
        "credential_count": observed["credential_count"],
        "successful_query_rows": observed["successful_query_rows"],
        "projected_url_leads": observed["projected_url_leads"],
        "usable_fetched_pages": observed["usable_fetched_pages"],
        "wall_seconds": observed["wall_seconds"],
    }


def validate_control_gate(root: Path) -> dict[str, Any]:
    gate = _read(root / CONTROL_GATE)
    unsigned = dict(gate)
    seal = unsigned.pop("audit_payload_sha256", None)
    synthetic = gate.get("synthetic_gate") or {}
    diagnosis_sha256 = gate.get("parents", {}).get("v24798_diagnosis_sha256")
    if (
        gate.get("role") != "v24799_fixed_full_budget_control_build_audit"
        or gate.get("audit_valid") is not True
        or gate.get("findings") != []
        or not isinstance(diagnosis_sha256, str)
        or len(diagnosis_sha256) != 64
        or any(character not in "0123456789abcdef" for character in diagnosis_sha256)
        or gate.get("authorization", {}).get(
            "next_fresh_exact220_protocol_design"
        )
        is not True
        or gate.get("authorization", {}).get("exact220_launch") is not False
        or synthetic.get("policy") != TWO_WAVE_POLICY
        or synthetic.get("synthetic_observation_count") != 9072
        or synthetic.get("pre_synthesis_safety_ceiling_expand_count") != 9072
        or synthetic.get("zero_entropy_value_count") != 9072
        or synthetic.get("hard_query_cap") != LIMITS["search_queries"]
        or synthetic.get("hard_fetch_cap") != LIMITS["fetch_targets"]
        or synthetic.get("entropy_or_information_gain_used_for_admission")
        is not False
        or gate.get("source_policy", {}).get(
            "visible_question_task_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or gate.get("source_policy", {}).get(
            "entropy_or_information_gain_used_for_admission"
        )
        is not False
        or seal != full_budget.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.00 full-budget control gate drifted")
    return {
        "audit_sha256": sha256(root / CONTROL_GATE),
        "gate_parent_diagnosis_sha256": diagnosis_sha256,
        "diagnosis_opened_or_hashed_by_protocol": False,
        "policy_id": synthetic["policy_id"],
        "synthetic_observation_count": synthetic["synthetic_observation_count"],
        "pre_synthesis_safety_ceiling_expand_count": synthetic[
            "pre_synthesis_safety_ceiling_expand_count"
        ],
        "entropy_or_information_gain_used_for_admission": False,
        "hard_query_cap": synthetic["hard_query_cap"],
        "hard_fetch_cap": synthetic["hard_fetch_cap"],
    }


def task_vector(root: Path, protocol: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    tasks = parent.task_vector(root, parent_contract(root))
    if len(tasks) != SELECTED_COUNT or any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.48.00 task vector drifted")
    if protocol is not None:
        expected = protocol.get("task_contract", {})
        if expected != {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
        }:
            raise RuntimeError("V2.48.00 task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update(
        (
            PARENT_PROTOCOL,
            SMOKE_PROTOCOL,
            SMOKE_RESULT,
            CONTROL_GATE,
        )
    )
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.00 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.48.00 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def build_protocol(
    root: Path, *, now: int, require_clean: bool = True, require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        _git(root, "status", "--porcelain")
        or _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.48.00 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.48.00 future surface exists")
    single_change_invariants = validate_single_change()
    base = parent_contract(root)
    smoke = validate_smoke(root)
    control_gate = validate_control_gate(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    value = {
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
        "neutral_transport_gate": smoke,
        "fixed_full_budget_control_gate": control_gate,
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "tavily_key_slot_cap": TAVILY_KEY_SLOT_CAP,
            "task_wall_seconds": LIMITS["wall_seconds"],
            "model_calls_per_task": LIMITS["model_calls"],
            "search_queries_per_task": LIMITS["search_queries"],
            "fetch_targets_per_task": LIMITS["fetch_targets"],
            "model": MODEL,
            "search": SEARCH,
            "two_wave_policy": TWO_WAVE_POLICY,
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "key_slot_directory": str(KEY_SLOT_DIRECTORY),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": {
            "v24798_entropy_voc_admission_replaced_by_fixed_full_budget_control": True,
            "entropy_or_information_gain_used_for_admission": False,
            "tavily_transport_model_prompt_renderer_and_hard_budgets_unchanged": True,
            "wave1_and_wave2_query_and_fetch_caps_unchanged": True,
            "first_wave_safety_ceiling_seconds": 30.0,
            "executor_model_slots_task_wall_and_task_vector_unchanged": True,
            "exact_parent_equality": single_change_invariants,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_v24798_output_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_values_environment_only_not_persisted_hashed_or_emitted": True,
            "fixed_public_exact220_task_set_reexecuted": True,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
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
    return validate_protocol(root, value)


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    single_change_invariants = validate_single_change()
    base = parent_contract(root)
    smoke = validate_smoke(root)
    control_gate = validate_control_gate(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    change = copied.get("single_change") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("parent_algorithm") != {
            "path": str(PARENT_PROTOCOL), "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        }
        or copied.get("neutral_transport_gate") != smoke
        or copied.get("fixed_full_budget_control_gate") != control_gate
        or copied.get("task_contract") != {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
        }
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("execution", {}).get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or copied.get("execution", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or copied.get("execution", {}).get("tavily_key_slot_cap") != TAVILY_KEY_SLOT_CAP
        or copied.get("execution", {}).get("task_wall_seconds") != LIMITS["wall_seconds"]
        or copied.get("execution", {}).get("model_calls_per_task") != LIMITS["model_calls"]
        or copied.get("execution", {}).get("search_queries_per_task") != LIMITS["search_queries"]
        or copied.get("execution", {}).get("fetch_targets_per_task") != LIMITS["fetch_targets"]
        or copied.get("execution", {}).get("model") != MODEL
        or copied.get("execution", {}).get("search") != SEARCH
        or copied.get("execution", {}).get("protected_watchers") != protected_watcher_snapshot()
        or copied.get("execution", {}).get("two_wave_policy") != TWO_WAVE_POLICY
        or change.get(
            "v24798_entropy_voc_admission_replaced_by_fixed_full_budget_control"
        )
        is not True
        or change.get("entropy_or_information_gain_used_for_admission")
        is not False
        or change.get(
            "tavily_transport_model_prompt_renderer_and_hard_budgets_unchanged"
        )
        is not True
        or change.get("exact_parent_equality") != single_change_invariants
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        ) is not False
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.48.00 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "dependency_manifest", "parent_contract", "payload_sha256",
    "protected_watcher_snapshot", "sha256", "task_vector", "validate_protocol",
    "validate_control_gate", "validate_single_change", "validate_smoke",
]
