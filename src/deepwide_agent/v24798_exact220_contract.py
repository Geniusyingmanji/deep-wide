"""Fresh label-blind exact-220 successor using validated Tavily URL leads."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24791_exact220_contract as parent


DATE = "20260807"
ROLE = "v24798_exact220_preregistration"
PROTOCOL_ID = "v24798_tavily_url_lead_exact220_v1"
PROTOCOL = Path(f"results/v24798_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24798_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24798_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24798_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24798_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24798_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
KEY_SLOT_DIRECTORY = OUTPUT_ROOT / "tavily_key_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24798_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_tavily_url_lead_exact220"
RUNNER_MARKER = "scripts/run_v24798_exact220.py"
CHILD_MARKER = "scripts/run_v24798_exact220_task.py"
DIRECT_RECEIPT_NAME = "direct_search_receipt.json"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
TAVILY_KEY_SLOT_CAP = 12
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
SEARCH.update(
    {
        "provider": "tavily-header-only-url-lead-plus-deterministic-fetch",
        "direct_workers": TAVILY_KEY_SLOT_CAP,
        "direct_timeout_seconds": 45,
        "provider_content_forwarded": False,
        "provider_result_score_used": False,
    }
)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)
PARENT_PROTOCOL = parent.PROTOCOL
SMOKE_PROTOCOL = Path("results/v24797_tavily_transport_smoke_preregistration_v1_20260807.json")
SMOKE_RESULT = Path("results/v24797_tavily_transport_smoke_result_v1_20260807.json")
SOURCE = Path("src/deepwide_agent/v24798_exact220_contract.py")
TRANSPORT = Path("src/deepwide_agent/v24796_deadline_tavily_search.py")
CONTROL = Path("scripts/control_v24798_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
TEST = Path("tests/test_v24798_exact220.py")
TRANSPORT_TEST = Path("tests/test_v24796_deadline_tavily_search.py")
FINALIZER = Path("scripts/finalize_v24798_exact220.py")
FINALIZER_TEST = Path("tests/test_finalize_v24798_exact220.py")
LOCAL_SOURCES = (
    SOURCE, TRANSPORT, CONTROL, RUNNER, CHILD, TEST, TRANSPORT_TEST,
    FINALIZER, FINALIZER_TEST,
)


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
        raise RuntimeError(f"V2.47.98 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.98 expected object")
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
        raise RuntimeError(f"V2.47.98 expected tracked source: {relative}")
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
        raise RuntimeError("V2.47.98 neutral Tavily smoke drifted")
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


def task_vector(root: Path, protocol: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    tasks = parent.task_vector(root, parent_contract(root))
    if len(tasks) != SELECTED_COUNT or any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.47.98 task vector drifted")
    if protocol is not None:
        expected = protocol.get("task_contract", {})
        if expected != {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
        }:
            raise RuntimeError("V2.47.98 task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update((PARENT_PROTOCOL, SMOKE_PROTOCOL, SMOKE_RESULT))
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
            raise RuntimeError("V2.47.98 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.47.98 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def build_protocol(
    root: Path, *, now: int, require_clean: bool = True, require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        _git(root, "status", "--porcelain")
        or _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.47.98 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.47.98 future surface exists")
    base = parent_contract(root)
    smoke = validate_smoke(root)
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
            "azure_hosted_search_replaced_by_tavily_header_only_url_leads": True,
            "tavily_answer_snippet_raw_content_and_score_discarded": True,
            "deterministically_fetched_public_page_text_is_only_active_evidence": True,
            "model_prompt_two_wave_entropy_controller_query_and_fetch_budgets_unchanged": True,
            "executor_model_slots_task_wall_and_task_vector_unchanged": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_v24791_output_prediction_result_score_or_evaluator_opened_or_hashed": False,
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
    base = parent_contract(root)
    smoke = validate_smoke(root)
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
        or copied.get("task_contract") != {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
        }
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("execution", {}).get("executor_concurrency") != 20
        or copied.get("execution", {}).get("model_slot_cap") != 8
        or copied.get("execution", {}).get("tavily_key_slot_cap") != 12
        or copied.get("execution", {}).get("task_wall_seconds") != 240
        or copied.get("execution", {}).get("protected_watchers") != protected_watcher_snapshot()
        or change.get("azure_hosted_search_replaced_by_tavily_header_only_url_leads") is not True
        or change.get("model_prompt_two_wave_entropy_controller_query_and_fetch_budgets_unchanged") is not True
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
        raise RuntimeError("V2.47.98 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "dependency_manifest", "parent_contract", "payload_sha256",
    "protected_watcher_snapshot", "sha256", "task_vector", "validate_protocol",
    "validate_smoke",
]
