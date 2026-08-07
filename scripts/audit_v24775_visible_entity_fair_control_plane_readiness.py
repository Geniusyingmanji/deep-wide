#!/usr/bin/env python3
"""Clean-build readiness audit for the V2.47.75 execution package.

This audit reads only tracked public sources and the inert V2.47.75 protocol.
It performs no endpoint, model, search, fetch, benchmark, or evaluator call and
cannot open the evaluator-only V2.47.74 population.  A GO authorizes only the
later clean-HEAD package-audit artifact.
"""

from __future__ import annotations

import ast
import copy
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24775_visible_entity_fair_execution_contract as contract  # noqa: E402


OUTPUT = contract.READINESS
PARENT = contract.PROTOCOL
SOURCE = Path("scripts/audit_v24775_visible_entity_fair_control_plane_readiness.py")
TEST = Path("tests/test_audit_v24775_visible_entity_fair_control_plane_readiness.py")
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24770_visible_entity_fair_semantic_runtime.py"),
    Path("src/deepwide_agent/v24775_visible_entity_fair_execution_contract.py"),
    Path("scripts/run_v24775_visible_entity_fair_task.py"),
    Path("scripts/run_v24775_visible_entity_fair_external.py"),
    Path("scripts/control_v24775_visible_entity_fair_external.py"),
    Path("scripts/audit_v24775_visible_entity_fair_forward.py"),
)
SOURCES = (
    *RUNTIME_SOURCES,
    Path("scripts/audit_v24775_visible_entity_fair_package.py"),
    Path("tests/test_v24775_visible_entity_fair_package.py"),
    Path("tests/test_v24775_visible_entity_fair_control.py"),
    Path("tests/test_audit_v24775_visible_entity_fair_package.py"),
    SOURCE,
    TEST,
    PARENT,
)
TEST_SUITES = (
    (Path("tests/test_v24770_visible_entity_fair_semantic_runtime.py"), 14),
    (Path("tests/test_v24775_visible_entity_fair_package.py"), 10),
    (Path("tests/test_v24775_visible_entity_fair_control.py"), 8),
    (Path("tests/test_audit_v24775_visible_entity_fair_package.py"), 6),
    (TEST, 5),
)
EXPECTED_TESTS = 43
RUNNER_MARKERS = (
    "scripts/run_v24775_visible_entity_fair_external.py",
    "scripts/run_v24775_visible_entity_fair_task.py",
)
PRIVILEGED = frozenset(
    {
        "answer",
        "answer_key",
        "category",
        "evaluator",
        "gold",
        "ground_truth",
        "mapping",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)
FORBIDDEN_MARKERS = (
    "evaluation" + "/",
    "v24774_visible_entity_fair_" + "population_private",
    "private_" + "truth.json",
    "evaluator_" + "mapping.jsonl",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
        or not _tracked(relative)
    ):
        raise RuntimeError(f"V2.47.75 expected tracked source: {relative}")
    return path


def _sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.75 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(PARENT)
    runtime = value.get("runtime", {})
    return bool(
        value.get("role") == "v24775_visible_entity_fair_external_preregistration"
        and value.get("protocol_id") == contract.PROTOCOL_ID
        and value.get("task_contract", {}).get("runtime_input_keys")
        == ["opaque_id", "question"]
        and value.get("task_contract", {}).get("task_count") == 8
        and runtime.get("implementation")
        == "v24770_visible_entity_fair_semantic_unknown_recovery_v1"
        and runtime.get("limits", {}).get("model_calls") == 2
        and runtime.get("limits", {}).get("search_queries") == 4
        and runtime.get("limits", {}).get("fetch_targets") == 10
        and runtime.get("scheduler_additional_model_query_search_fetch_or_token_effect")
        == 0
        and runtime.get("semantic_replay_additional_model_query_search_fetch_or_token_effect")
        == 0
        and value.get("authorization", {}).get("runner_or_control_plane_build")
        is True
        and value.get("authorization", {}).get("one_external_forward_launch")
        is False
        and value.get("authorization", {}).get("quality_surface_open") is False
        and _sealed(value, "protocol_payload_sha256")
    )


def _manifest() -> dict[str, str]:
    output = {}
    for relative in SOURCES:
        raw = _ordinary(relative).read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.75 credential literal found")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def ast_findings() -> tuple[list[str], list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    markers: list[str] = []
    secrets: list[str] = []
    for relative in RUNTIME_SOURCES:
        source = _ordinary(relative).read_text(encoding="utf-8")
        markers.extend(
            f"{relative}:{marker}" for marker in FORBIDDEN_MARKERS if marker in source
        )
        if SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key: str | None = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value
            if key is not None and key.casefold() in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            else:
                names = []
            imports.extend(
                f"{relative}:{node.lineno}:{name}"
                for name in names
                if any(marker in name.casefold() for marker in ("evaluator", "gold"))
            )
    return tuple(map(lambda values: sorted(set(values)), (fields, imports, markers, secrets)))  # type: ignore[return-value]


def implementation_contract() -> dict[str, Any]:
    runtime = _ordinary(RUNTIME_SOURCES[0]).read_text(encoding="utf-8")
    child = _ordinary(RUNTIME_SOURCES[2]).read_text(encoding="utf-8")
    parent = _ordinary(RUNTIME_SOURCES[3]).read_text(encoding="utf-8")
    tasks = contract.task_vector()
    value = {
        "task_count": len(tasks),
        "runtime_input_keys_exact": all(set(task) == {"opaque_id", "question"} for task in tasks),
        "entity_count_per_task": [len(contract.visible_entities(task["question"])) for task in tasks],
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "parent_timeout_seconds": contract.PARENT_TIMEOUT_SECONDS,
        "experiment_wall_ceiling_seconds": contract.EXPERIMENT_WALL_CEILING_SECONDS,
        "limits": dict(contract.LIMITS),
        "visible_entity_scheduler_call_count": runtime.count("scheduler = VisibleEntityFairSearchClient("),
        "parent_runtime_call_count": runtime.count("run_v24756_task("),
        "hard_total_wall_model_inner": "HardTotalWallResponsesClient(" in child,
        "deadline_aware_global_slot_wrapper": "DeadlineAwareGlobalModelSlotLimiter(" in child,
        "hard_total_wall_search_inner": "HardTotalWallNativeSearchClient(" in child,
        "one_shot_total_wrapper_present": "def run_task_total(" in parent,
        "fixed_denominator_freeze_present": "failure_predictions(" in parent,
        "semantic_receipts_aggregated": "projection_backed_support_set_count" in parent
        and "entity_slots_with_two_requested_aligned_sources" in parent,
        "valid": False,
    }
    value["valid"] = bool(
        value["task_count"] == 8 and value["runtime_input_keys_exact"]
        and value["entity_count_per_task"] == [4] * 8
        and value["executor_concurrency"] == 8 and value["model_slot_cap"] == 8
        and value["parent_timeout_seconds"] == 195.0
        and value["experiment_wall_ceiling_seconds"] == 210.0
        and value["limits"]["model_calls"] == 2
        and value["limits"]["search_queries"] == 4
        and value["limits"]["fetch_targets"] == 10
        and value["visible_entity_scheduler_call_count"] == 1
        and value["parent_runtime_call_count"] == 1
        and value["hard_total_wall_model_inner"]
        and value["deadline_aware_global_slot_wrapper"]
        and value["hard_total_wall_search_inner"]
        and value["one_shot_total_wrapper_present"]
        and value["fixed_denominator_freeze_present"]
        and value["semantic_receipts_aggregated"]
    )
    return value


def _run_tests() -> tuple[bool, int, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected in TEST_SUITES:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
             "discover", "-s", "tests", "-p", path.name, "-v"],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=180, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append({
            "path": str(path), "expected": expected, "observed": observed,
            "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
            "passed": completed.returncode == 0 and observed == expected,
        })
    total = sum(row["observed"] for row in rows)
    return all(row["passed"] for row in rows) and total == EXPECTED_TESTS, total, rows


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active_runners() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 3 and "python" in parts[1].casefold() and any(
            marker in parts[2] for marker in RUNNER_MARKERS
        ):
            output.append(int(parts[0]))
    return sorted(output)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = _manifest()
    fields, imports, markers, secrets = ast_findings()
    implementation = implementation_contract()
    tests_passed, observed, suites = _run_tests()
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    watchers = contract.protected_watcher_snapshot()
    lease = _lease_inactive()
    runners = _active_runners()
    future_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (
            OUTPUT, contract.PACKAGE_BUILD, contract.PREAUDIT, contract.ACTIVATION,
            contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
            contract.OUTPUT_ROOT,
        )
    )
    findings = []
    if not _parent_valid(): findings.append("protocol_parent_invalid")
    if not implementation["valid"]: findings.append("implementation_contract_drifted")
    if fields: findings.append("privileged_forward_field_access")
    if imports: findings.append("evaluator_or_gold_import_in_forward")
    if markers: findings.append("private_or_evaluator_marker_in_forward")
    if secrets: findings.append("credential_literal_in_forward")
    if not tests_passed: findings.append("regression_failed_or_count_drifted")
    if head != remote: findings.append("source_commit_not_pushed")
    if not clean: findings.append("source_worktree_not_clean")
    if not all(_tracked(path) for path in SOURCES): findings.append("source_not_tracked")
    if not lease: findings.append("shared_api_lease_active")
    if runners: findings.append("v24775_runner_active")
    if not future_pristine: findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24775_visible_entity_fair_control_plane_readiness",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": _sha256(PARENT),
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "implementation_contract": implementation,
        "tests": {"expected": EXPECTED_TESTS, "observed": observed, "suites": suites,
                  "passed": tests_passed,
                  "network_model_search_fetch_benchmark_or_evaluator_called": False},
        "label_blind_audit": {"runtime_input_keys": ["opaque_id", "question"],
                              "privileged_forward_field_accesses": fields,
                              "evaluator_or_gold_imports": imports,
                              "private_or_evaluator_marker_hits": markers,
                              "credential_literal_hits": secrets,
                              "passed": not fields and not imports and not markers and not secrets},
        "runtime_state": {"protected_watchers": watchers,
                          "shared_api_lease_inactive": lease,
                          "active_v24775_runner_pids": runners,
                          "future_surface_pristine": future_pristine,
                          "external_forward_launched_by_audit": False,
                          "evaluator_called_by_audit": False},
        "git": {"head": head, "target_main": remote,
                "head_equals_target_main": head == remote,
                "worktree_clean": clean, "all_sources_tracked": all(_tracked(path) for path in SOURCES)},
        "source_policy": {
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "package_audit_artifact_generation": not findings,
            "preactivation_audit_generation": False, "activation": False,
            "execution_start": False, "external_launch": False,
            "private_truth_or_quality_surface_open": False, "paired_dev64": False,
            "exact220": False, "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role") != "v24775_visible_entity_fair_control_plane_readiness"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True or copied.get("findings") != []
        or copied.get("protocol_sha256") != _sha256(PARENT)
        or copied.get("source_manifest") != _manifest()
        or copied.get("implementation_contract", {}).get("valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("active_v24775_runner_pids") != []
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("authorization") != {
            "package_audit_artifact_generation": True,
            "preactivation_audit_generation": False, "activation": False,
            "execution_start": False, "external_launch": False,
            "private_truth_or_quality_surface_open": False, "paired_dev64": False,
            "exact220": False, "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.75 readiness audit drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


if __name__ == "__main__":
    value = validate_audit(build_audit())
    _publish(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": value["audit_valid"],
                      "findings": value["findings"],
                      "package_audit_artifact_generation": value["authorization"]["package_audit_artifact_generation"]}, sort_keys=True))
