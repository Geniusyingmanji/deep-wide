#!/usr/bin/env python3
"""Clean-build source audit for the inert V2.47.80 execution package.

The audit intentionally excludes the V2.47.79 evaluator-only population and every
private truth, provenance, benchmark, score, and evaluator surface.  Running
the script later requires a clean pushed source commit and grants only the
right to generate a preactivation audit, never launch authority.
"""

from __future__ import annotations

import ast
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

from deepwide_agent import v24780_staged_fallback_execution_contract as contract  # noqa: E402


READINESS = contract.READINESS
AUDIT = contract.PACKAGE_BUILD
FORWARD_FILES = (
    Path("src/deepwide_agent/v24263_global_model_limiter.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
    Path("src/deepwide_agent/v24309_runner_exit_integration.py"),
    Path("src/deepwide_agent/v24312_deadline_reliability.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24468_total_wall_transport.py"),
    Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py"),
    Path("src/deepwide_agent/v24778_staged_fetch_fallback_runtime.py"),
    Path("src/deepwide_agent/v24779_staged_fallback_contract.py"),
    Path("src/deepwide_agent/v24780_staged_fallback_execution_contract.py"),
    Path("scripts/run_v24780_staged_fallback_task.py"),
    Path("scripts/run_v24780_staged_fallback_external.py"),
    Path("scripts/audit_v24780_staged_fallback_forward.py"),
    Path("scripts/control_v24780_staged_fallback_external.py"),
    Path("scripts/run_v24287_fetch_helper.py"),
    Path("scripts/v24468_total_wall_http_helper.py"),
)
PACKAGE_FILES = FORWARD_FILES + (
    Path("scripts/audit_v24780_staged_fallback_control_plane_readiness.py"),
    Path("scripts/audit_v24780_staged_fallback_package.py"),
    Path("tests/test_v24780_staged_fallback_package.py"),
    Path("tests/test_v24780_staged_fallback_control.py"),
    Path("tests/test_audit_v24780_staged_fallback_forward.py"),
    Path("tests/test_audit_v24780_staged_fallback_control_plane_readiness.py"),
    Path("tests/test_audit_v24780_staged_fallback_package.py"),
)
SOURCES = PACKAGE_FILES
TEST_SUITES = (
    (Path("tests/test_v24263_global_model_limiter.py"), 6, 180),
    (Path("tests/test_v24269_task_union_discovery.py"), 5, 180),
    (Path("tests/test_v24309_runner_exit_integration.py"), 5, 180),
    (Path("tests/test_v24312_deadline_reliability.py"), 7, 180),
    (Path("tests/test_v24316_deadline_search.py"), 7, 180),
    (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
    (Path("tests/test_v24756_zero_effect_structured_integration.py"), 6, 180),
    (Path("tests/test_v24778_staged_fetch_fallback_runtime.py"), 13, 180),
    (Path("tests/test_v24780_staged_fallback_package.py"), 11, 180),
    (Path("tests/test_v24780_staged_fallback_control.py"), 8, 120),
    (Path("tests/test_audit_v24780_staged_fallback_forward.py"), 7, 120),
    (Path("tests/test_audit_v24780_staged_fallback_control_plane_readiness.py"), 5, 120),
    (Path("tests/test_audit_v24780_staged_fallback_package.py"), 6, 120),
)
EXPECTED_TEST_COUNT = 94
RUNNER_MARKERS = (
    "scripts/run_v24780_staged_fallback_external.py",
    "scripts/run_v24780_staged_fallback_task.py",
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
FORBIDDEN_FORWARD_MARKERS = (
    "evaluation" + "/",
    "v24779_staged_fallback_" + "population_private",
    "private_" + "truth.json",
    "evaluator_" + "mapping.jsonl",
    "official_" + "evaluator",
    "overall_20250916" + ".jsonl",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.80 expected repository file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.80 expected JSON object")
    return value


def _parents_valid() -> bool:
    protocol = _read(contract.PROTOCOL)
    readiness = _read(READINESS)
    return bool(
        protocol.get("role")
        == "v24780_staged_fallback_external_preregistration"
        and protocol.get("protocol_id") == contract.PROTOCOL_ID
        and protocol.get("task_contract", {}).get("runtime_input_keys")
        == ["opaque_id", "question"]
        and protocol.get("authorization", {}).get("runner_or_control_plane_build")
        is True
        and protocol.get("authorization", {}).get("one_external_forward_launch")
        is False
        and _sealed(protocol, "protocol_payload_sha256")
        and readiness.get("role")
        == "v24780_staged_fallback_control_plane_readiness"
        and readiness.get("audit_valid") is True
        and readiness.get("findings") == []
        and readiness.get("authorization", {}).get(
            "package_audit_artifact_generation"
        )
        is True
        and readiness.get("authorization", {}).get("external_launch") is False
        and _sealed(readiness, "audit_payload_sha256")
    )


def ast_findings() -> tuple[list[str], list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    markers: list[str] = []
    secrets: list[str] = []
    for relative in FORWARD_FILES:
        source = _ordinary(relative).read_text(encoding="utf-8")
        markers.extend(
            f"{relative}:{marker}"
            for marker in FORBIDDEN_FORWARD_MARKERS
            if marker in source
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
                if any(token in name.casefold() for token in ("evaluator", "gold"))
            )
    return (
        sorted(set(fields)),
        sorted(set(imports)),
        sorted(set(markers)),
        sorted(set(secrets)),
    )


def implementation_contract() -> dict[str, Any]:
    runtime_source = _ordinary(
        Path("src/deepwide_agent/v24778_staged_fetch_fallback_runtime.py")
    ).read_text(encoding="utf-8")
    runtime_tree = ast.parse(runtime_source)
    union_calls = [
        node
        for node in ast.walk(runtime_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "StagedFetchFallbackSearchClient"
    ]
    child = _ordinary(Path("scripts/run_v24780_staged_fallback_task.py")).read_text(
        encoding="utf-8"
    )
    parent = _ordinary(Path("scripts/run_v24780_staged_fallback_external.py")).read_text(
        encoding="utf-8"
    )
    tasks = contract.task_vector()
    value = {
        "task_count": len(tasks),
        "runtime_input_keys_exact": all(
            set(task) == {"opaque_id", "question"} for task in tasks
        ),
        "entity_count_per_task": [
            len(contract.visible_entities(task["question"])) for task in tasks
        ],
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "parent_timeout_seconds": contract.PARENT_TIMEOUT_SECONDS,
        "experiment_wall_ceiling_seconds": contract.EXPERIMENT_WALL_CEILING_SECONDS,
        "limits": dict(contract.LIMITS),
        "runtime_owned_visible_entity_scheduler_wrapper_call_count": len(union_calls),
        "hard_total_wall_model_inner": "HardTotalWallResponsesClient(" in child,
        "deadline_aware_global_slot_wrapper":
        "DeadlineAwareGlobalModelSlotLimiter(" in child,
        "hard_total_wall_search_inner": "HardTotalWallNativeSearchClient(" in child,
        "thin_title_backfill_absent":
        "ThinSameResponseCitationTitleBackfillSearchClient" not in child
        and "ThinSameResponseCitationTitleBackfillSearchClient" not in runtime_source,
        "one_shot_total_wrapper_present": "def run_task_total(" in parent,
        "failure_as_four_row_unknown_present": "failure_predictions(" in parent,
        "visible_entity_runtime_called": "run_v24778_task(" in child,
        "strict_semantic_receipts_aggregated":
        "projection_backed_support_set_count" in parent
        and "reserve_fetch_request_count" in parent
        and "entity_slots_brought_to_two_sources_by_reserve" in parent,
        "valid": False,
    }
    value["valid"] = bool(
        value["task_count"] == 8
        and value["runtime_input_keys_exact"]
        and value["entity_count_per_task"] == [4] * 8
        and value["executor_concurrency"] == 8
        and value["model_slot_cap"] == 8
        and value["parent_timeout_seconds"] == 195.0
        and value["experiment_wall_ceiling_seconds"] == 210.0
        and value["limits"]["model_calls"] == 2
        and value["limits"]["search_queries"] == 4
        and value["limits"]["fetch_targets"] == 10
        and value["runtime_owned_visible_entity_scheduler_wrapper_call_count"] == 1
        and value["hard_total_wall_model_inner"]
        and value["deadline_aware_global_slot_wrapper"]
        and value["hard_total_wall_search_inner"]
        and value["thin_title_backfill_absent"]
        and value["one_shot_total_wrapper_present"]
        and value["failure_as_four_row_unknown_present"]
        and value["visible_entity_runtime_called"]
        and value["strict_semantic_receipts_aggregated"]
    )
    return value


def _run_test(path: Path, timeout: int) -> tuple[bool, int, str]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            path.name,
            "-v",
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return (
        completed.returncode == 0,
        observed,
        hashlib.sha256(completed.stdout.encode()).hexdigest(),
    )


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
        ["ps", "-eo", "pid=,comm=,args="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or "python" not in parts[1].casefold():
            continue
        if any(marker in parts[2] for marker in RUNNER_MARKERS):
            output.append(int(parts[0]))
    return sorted(output)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): _sha256(path) for path in SOURCES}
    fields, imports, markers, secrets = ast_findings()
    implementation = implementation_contract()
    suites = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed, output_sha = _run_test(path, timeout)
        suites.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "output_sha256": output_sha,
                "passed": passed and observed == expected,
            }
        )
    observed = sum(row["observed"] for row in suites)
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(
        _tracked(path)
        for path in (*SOURCES, contract.PROTOCOL, READINESS)
    )
    parents = _parents_valid()
    watchers = contract.protected_watcher_snapshot()
    lease = _lease_inactive()
    runners = _active_runners()
    future_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (
            contract.PREAUDIT,
            contract.ACTIVATION,
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.OUTPUT_ROOT,
        )
    )
    findings: list[str] = []
    if head != remote:
        findings.append("v24780_source_commit_not_pushed")
    if not clean:
        findings.append("v24780_source_worktree_not_clean")
    if not tracked:
        findings.append("v24780_source_not_tracked")
    if not parents:
        findings.append("v24780_protocol_or_readiness_parent_drifted")
    if not implementation["valid"]:
        findings.append("v24780_implementation_contract_drifted")
    if fields:
        findings.append("privileged_forward_field_access")
    if imports:
        findings.append("evaluator_or_gold_import_in_forward")
    if markers:
        findings.append("private_or_evaluator_marker_in_forward")
    if secrets:
        findings.append("credential_literal_in_forward")
    if any(not row["passed"] for row in suites) or observed != EXPECTED_TEST_COUNT:
        findings.append("regression_failed_or_count_drifted")
    if not lease:
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24780_runner_active")
    if not future_pristine:
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24780_staged_fallback_package_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "protocol_sha256": _sha256(contract.PROTOCOL),
            "readiness_sha256": _sha256(READINESS),
            "valid": parents,
        },
        "implementation_contract": implementation,
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "manifest_policy": {
            "private_population_truth_provenance_or_evaluator_file_in_manifest": False,
            "evaluation_directory_file_in_manifest": False,
            "benchmark_manifest_mapping_gold_score_or_reward_file_in_manifest": False,
        },
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "expected": EXPECTED_TEST_COUNT,
            "observed": observed,
            "suites": suites,
            "passed": all(row["passed"] for row in suites)
            and observed == EXPECTED_TEST_COUNT,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "runtime_input_keys": ["opaque_id", "question"],
            "privileged_forward_field_accesses": fields,
            "evaluator_or_gold_imports": imports,
            "private_or_evaluator_marker_hits": markers,
            "credential_literal_hits": secrets,
            "passed": not fields and not imports and not markers and not secrets,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "shared_api_lease_inactive": lease,
            "active_v24780_runner_pids": runners,
            "future_surface_pristine": future_pristine,
            "external_forward_launched_by_audit": False,
            "evaluator_called_by_audit": False,
        },
        "source_policy": {
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "preactivation_audit_generation": not findings,
            "activation": False,
            "execution_start": False,
            "external_launch": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24780_staged_fallback_package_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("parents", {}).get("valid") is not True
        or copied.get("implementation_contract", {}).get("valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("observed") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("manifest_policy")
        != {
            "private_population_truth_provenance_or_evaluator_file_in_manifest": False,
            "evaluation_directory_file_in_manifest": False,
            "benchmark_manifest_mapping_gold_score_or_reward_file_in_manifest": False,
        }
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive")
        is not True
        or copied.get("runtime_state", {}).get("active_v24780_runner_pids") != []
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "activation": False,
            "execution_start": False,
            "external_launch": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.80 package audit drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    validate_audit(audit)
    _publish(ROOT / AUDIT, audit)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": audit["audit_valid"],
                "findings": audit["findings"],
                "test_count": audit["tests"]["observed"],
            },
            sort_keys=True,
        )
    )
