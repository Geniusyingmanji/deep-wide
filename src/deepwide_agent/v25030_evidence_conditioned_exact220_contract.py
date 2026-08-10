"""Frozen label-blind contract for the V2.50.30 DeepWideBench exact-220 run.

The benchmark population is byte-bound to the visible task vector used by
V2.48.57.  The forward algorithm and transport are deliberately *not* claimed
to be equal to V2.48.57: V2.50.30 uses the keyless GPT-5.6 transport and the
V2.50.29 evidence-conditioned resolve-then-expand runtime.
"""

from __future__ import annotations

import copy
import ast
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25029_evidence_conditioned_runtime as runtime


DATE = "20260810"
PROTOCOL_ID = "v25030_evidence_conditioned_keyless_exact220_v1"
BUILD_AUDIT = Path(f"results/v25030_evidence_conditioned_exact220_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25030_evidence_conditioned_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25030_evidence_conditioned_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25030_evidence_conditioned_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25030_evidence_conditioned_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25030_evidence_conditioned_exact220_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25030_evidence_conditioned_exact220_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25030_evidence_conditioned_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25030_evidence_conditioned_exact220_postresult_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v25030_evidence_conditioned_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
RUNTIME_RESULTS = OUTPUT_ROOT / "runtime_results.jsonl"
TASK_RECEIPTS = OUTPUT_ROOT / "content_free_task_receipts.jsonl"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v25030_evidence_conditioned_exact220_forward_v1"
LEASE_PURPOSE = "single_fresh_label_blind_evidence_conditioned_exact220"

PARENT_TASK_PROTOCOL = Path("results/v24857_pacing_aware_exact220_preregistration_v1_20260808.json")
VISIBLE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
ID_SOURCES = (
    Path("configs/full220_v2403_r1_test_s01.ids"),
    Path("configs/full220_v2403_r1_test_s02.ids"),
    Path("configs/full220_v2403_r1_test_s03.ids"),
    Path("configs/full220_v2403_r1_devval_s04.ids"),
)
ID_COUNTS = (52, 52, 52, 64)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")

SELECTED_COUNT = 220
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
LIMITS = {
    "wall_seconds": 240,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "provider": "azure-native-keyless-bounded-robust-late-page-fetch",
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "batch_size": 8,
    "workers": 1,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 65,
    "max_retries": 2,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
    "server_auto_fetch_enabled": False,
}
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)

SOURCE = Path("src/deepwide_agent/v25030_evidence_conditioned_exact220_contract.py")
RUNTIME = Path("src/deepwide_agent/v25029_evidence_conditioned_runtime.py")
REFINEMENT = Path("src/deepwide_agent/v25024_evidence_conditioned_queries.py")
PARENT_SHARED_WAVE = Path("src/deepwide_agent/v24996_shared_first_wave_paired_runtime.py")
PARENT_COMPACT = Path("src/deepwide_agent/v24990_query_vector_paired_runtime.py")
PARENT_ROBUST = Path("src/deepwide_agent/v24986_robust_paired_runtime.py")
PARENT_COUNTERS = Path("src/deepwide_agent/v24982_paired_production_runtime.py")
FETCH = Path("src/deepwide_agent/v24985_robust_late_page_fetch.py")
FETCH_HELPER = Path("scripts/run_v24985_robust_late_page_fetch_helper.py")
LEASE = Path("scripts/deepwide_api_lease.py")
CONTROL = Path("scripts/control_v25030_evidence_conditioned_exact220.py")
RUNNER = Path("scripts/run_v25030_evidence_conditioned_exact220.py")
FINALIZER = Path("scripts/finalize_v25030_evidence_conditioned_exact220.py")
TEST = Path("tests/test_v25030_evidence_conditioned_exact220.py")
PARENT_TESTS = (
    Path("tests/test_v25029_evidence_conditioned_runtime.py"),
    Path("tests/test_v25024_evidence_conditioned_queries.py"),
    Path("tests/test_v24996_shared_first_wave_paired_runtime.py"),
    Path("tests/test_v24990_query_vector_paired_runtime.py"),
    Path("tests/test_v24986_robust_paired_runtime.py"),
    Path("tests/test_v24985_robust_late_page_fetch.py"),
    Path("tests/test_v24982_paired_production_runtime.py"),
)
RUNNER_MARKER = str(RUNNER)
CHILD_MARKER = "v25030_no_child_process"

FORWARD_SOURCES = (
    SOURCE,
    RUNTIME,
    REFINEMENT,
    PARENT_SHARED_WAVE,
    PARENT_COMPACT,
    PARENT_ROBUST,
    PARENT_COUNTERS,
    FETCH,
    FETCH_HELPER,
    LEASE,
    RUNNER,
)
LOCAL_SOURCES = (*FORWARD_SOURCES, CONTROL, FINALIZER, TEST, PARENT_TASK_PROTOCOL)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop(field, None)
    copied[field] = payload_sha256(copied)
    return copied


def sealed(value: Mapping[str, Any], field: str) -> bool:
    copied = copy.deepcopy(dict(value))
    observed = copied.pop(field, None)
    return isinstance(observed, str) and observed == payload_sha256(copied)


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.50.30 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.50.30 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def _ordinary(path: Path, root: Path) -> Path:
    candidate = root / path
    if (
        path.is_absolute() or ".." in path.parts or candidate.is_symlink()
        or not candidate.is_file() or not candidate.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.50.30 expected ordinary repository file: {path}")
    return candidate


def forward_dependency_closure(root: Path) -> tuple[Path, ...]:
    """Resolve the complete repository-local Python import closure."""

    pending = list(FORWARD_SOURCES)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = _ordinary(relative, root)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            candidates: list[Path] = []
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
                for name in names:
                    if name.startswith("deepwide_agent."):
                        candidates.append(Path("src") / Path(*name.split(".")) .with_suffix(".py"))
                    elif name.startswith("scripts."):
                        candidates.append(Path(*name.split(".")).with_suffix(".py"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == ("src", "deepwide_agent"):
                    if module:
                        candidates.append(Path("src/deepwide_agent") / Path(*module.split(".")).with_suffix(".py"))
                    else:
                        candidates.extend(
                            Path("src/deepwide_agent") / f"{item.name}.py"
                            for item in node.names
                        )
                elif module == "deepwide_agent":
                    candidates.extend(
                        Path("src/deepwide_agent") / f"{item.name}.py"
                        for item in node.names
                    )
                elif module.startswith("deepwide_agent."):
                    candidates.append(Path("src") / Path(*module.split(".")).with_suffix(".py"))
                elif module == "scripts":
                    candidates.extend(Path("scripts") / f"{item.name}.py" for item in node.names)
                elif module.startswith("scripts."):
                    candidates.append(Path(*module.split(".")).with_suffix(".py"))
            for candidate in candidates:
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def _source_ids(root: Path) -> list[str]:
    values: list[str] = []
    for relative, expected in zip(ID_SOURCES, ID_COUNTS, strict=True):
        path = _ordinary(relative, root)
        current = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        if (
            len(current) != expected or len(set(current)) != expected
            or any(OPAQUE.fullmatch(item) is None for item in current)
        ):
            raise RuntimeError("V2.50.30 visible ID source drifted")
        values.extend(current)
    if len(values) != SELECTED_COUNT or len(set(values)) != SELECTED_COUNT:
        raise RuntimeError("V2.50.30 visible ID vector is not exact-220")
    return values


def _parent_task_contract(root: Path) -> dict[str, Any]:
    path = _ordinary(PARENT_TASK_PROTOCOL, root)
    value = json.loads(path.read_text(encoding="utf-8"))
    task = value.get("task_contract") if isinstance(value, dict) else None
    if (
        not isinstance(task, dict) or task.get("selected_count") != SELECTED_COUNT
        or task.get("runtime_input_keys") != ["opaque_id", "question"]
    ):
        raise RuntimeError("V2.50.30 V2.48.57 task binding drifted")
    return copy.deepcopy(task)


def task_vector(root: Path, protocol: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    manifest = _ordinary(VISIBLE_MANIFEST, root)
    rows: dict[str, dict[str, str]] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        if (
            not isinstance(raw, dict) or set(raw) != {"opaque_id", "question"}
            or OPAQUE.fullmatch(str(raw.get("opaque_id", ""))) is None
            or not isinstance(raw.get("question"), str) or not raw["question"].strip()
            or raw["opaque_id"] in rows
        ):
            raise RuntimeError("V2.50.30 visible manifest schema drifted")
        rows[raw["opaque_id"]] = {"opaque_id": raw["opaque_id"], "question": raw["question"]}
    ids = _source_ids(root)
    if any(item not in rows for item in ids):
        raise RuntimeError("V2.50.30 selected visible task is absent")
    tasks = [rows[item] for item in ids]
    observed = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256(ids),
        "visible_question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
    }
    if observed != _parent_task_contract(root):
        raise RuntimeError("V2.50.30 task vector is not byte-equal to V2.48.57")
    if protocol is not None and protocol.get("task_contract") != observed:
        raise RuntimeError("V2.50.30 protocol task binding drifted")
    return tasks


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    output: dict[str, str] = {}
    relatives = {
        *forward_dependency_closure(root),
        CONTROL,
        FINALIZER,
        TEST,
        *PARENT_TESTS,
        PARENT_TASK_PROTOCOL,
    }
    for relative in sorted(relatives, key=str):
        path = _ordinary(relative, root)
        if tracked and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode != 0:
            raise RuntimeError(f"V2.50.30 source is not tracked: {relative}")
        output[str(relative)] = sha256(path)
    return output


def _input_bindings(root: Path) -> dict[str, Any]:
    return {
        "visible_manifest": {"path": str(VISIBLE_MANIFEST), "sha256": sha256(_ordinary(VISIBLE_MANIFEST, root))},
        "id_sources": {str(path): sha256(_ordinary(path, root)) for path in ID_SOURCES},
        "v24857_task_protocol": {"path": str(PARENT_TASK_PROTOCOL), "sha256": sha256(_ordinary(PARENT_TASK_PROTOCOL, root))},
    }


def _build_audit_binding(root: Path) -> dict[str, str] | None:
    path = root / BUILD_AUDIT
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.50.30 build audit is nonordinary")
    return {"path": str(BUILD_AUDIT), "sha256": sha256(path)}


def build_protocol(
    root: Path, *, now: int, tracked: bool = True,
    require_clean: bool = True, require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        git(root, "status", "--porcelain")
        or git(root, "rev-parse", "HEAD") != git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.50.30 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, EVALUATOR_PROTOCOL, RESULT, POSTAUDIT, OUTPUT_ROOT)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.50.30 future surface exists")
    tasks = task_vector(root)
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25030_evidence_conditioned_exact220_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD"),
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
            "visible_question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
        },
        "build_audit": _build_audit_binding(root),
        "input_bindings": _input_bindings(root),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "limits": copy.deepcopy(LIMITS),
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "runtime_policy_id": runtime.POLICY_ID,
            "runtime_phases": list(runtime.PHASES),
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "single_fresh_forward_no_retry_resume_skip_or_selective_rerun": True,
        },
        "treatment_scope": {
            "v25029_evidence_conditioned_second_wave_enabled": True,
            "v24857_same_visible_task_vector": True,
            "v24857_tavily_transport_reused": False,
            "keyless_gpt56_resolve_then_expand_transport": True,
            "cross_rollout_difference_is_not_a_pure_query_treatment_effect": True,
            "v25028_external_gate_supports_mechanism_and_quality_but_not_deepwidebench_score": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
            "mapping_gold_category_question_type_split_answer_evaluator_score_reward_read_by_forward": False,
            "prior_prediction_result_score_reward_or_evaluator_read_by_forward": False,
            "prediction_freeze_before_mapping_query_answer_or_official_evaluator_open": True,
            "entropy_or_information_gain_assigns_signed_credit_or_routes": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "new_or_disjoint_task_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "postfreeze_official_evaluator": False,
            "retry_resume_skip_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value, tracked=tracked)


def validate_protocol(root: Path, value: Mapping[str, Any], *, tracked: bool = True) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    observed_seal = unsigned.pop("protocol_payload_sha256", None)
    tasks = task_vector(root)
    manifest = dependency_manifest(root, tracked=tracked)
    execution = copied.get("execution") or {}
    expected_task = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
        "visible_question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
    }
    if (
        copied.get("role") != "v25030_evidence_conditioned_exact220_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or observed_seal != payload_sha256(unsigned)
        or copied.get("task_contract") != expected_task
        or copied.get("build_audit") != _build_audit_binding(root)
        or copied.get("input_bindings") != _input_bindings(root)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("executor_concurrency") != 20
        or execution.get("model_slot_cap") != 8
        or execution.get("limits") != LIMITS
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("runtime_policy_id") != runtime.POLICY_ID
        or execution.get("runtime_phases") != list(runtime.PHASES)
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or copied.get("treatment_scope", {}).get("v24857_tavily_transport_reused") is not False
        or copied.get("treatment_scope", {}).get("cross_rollout_difference_is_not_a_pure_query_treatment_effect") is not True
        or copied.get("source_policy", {}).get("mapping_gold_category_question_type_split_answer_evaluator_score_reward_read_by_forward") is not False
        or copied.get("source_policy", {}).get("entropy_or_information_gain_assigns_signed_credit_or_routes") is not False
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "postfreeze_official_evaluator": False,
            "retry_resume_skip_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
    ):
        raise RuntimeError("V2.50.30 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "dependency_manifest", "forward_dependency_closure",
    "git", "payload_sha256",
    "protected_watcher_snapshot", "seal", "sealed", "sha256",
    "task_vector", "validate_protocol",
]
