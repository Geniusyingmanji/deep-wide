#!/usr/bin/env python3
"""Clean-build audit for the inert V2.46.94 World Bank forward package."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24686_worldbank_target_value_runtime import ARMS  # noqa: E402
from deepwide_agent.v24694_worldbank_external_contract import (  # noqa: E402
    ARM_COUNT,
    EXECUTOR_CONCURRENCY,
    LIMITS,
    MODEL_SLOT_CAP,
    PARENT_TIMEOUT_SECONDS,
    PROTOCOL_ID,
    SEARCH,
    SELECTED_COUNT,
    payload_sha256,
    protected_watcher_snapshot,
    task_vector,
)
from deepwide_agent.v24696_worldbank_forward_contract import TASK_WALL_SECONDS  # noqa: E402
from deepwide_agent.v24696_worldbank_search_transport import HARD_FETCH_DEADLINE_SECONDS  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


DATE = "20260806"
PARENT = Path(f"results/v24695_worldbank_surface_repair_build_audit_v1_{DATE}.json")
AUDIT = Path(f"results/v24696_worldbank_external_package_build_audit_v1_{DATE}.json")
FORWARD_FILES = (
    Path("src/deepwide_agent/v24686_worldbank_target_value_runtime.py"),
    Path("src/deepwide_agent/v24694_worldbank_external_contract.py"),
    Path("src/deepwide_agent/v24696_worldbank_forward_contract.py"),
    Path("src/deepwide_agent/v24696_worldbank_search_transport.py"),
    Path("src/deepwide_agent/v24696_worldbank_runner_integration.py"),
    Path("scripts/run_v24694_worldbank_task.py"),
    Path("scripts/run_v24694_worldbank_forward.py"),
)
SOURCES = FORWARD_FILES + (
    PARENT,
    Path("scripts/deepwide_api_lease.py"),
    Path("tests/test_v24686_worldbank_target_value_runtime.py"),
    Path("tests/test_v24696_worldbank_forward_package.py"),
    Path("scripts/audit_v24696_worldbank_external_package_build.py"),
    Path("tests/test_audit_v24696_worldbank_external_package_build.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24686_worldbank_target_value_runtime.py"), 10),
    (Path("tests/test_v24696_worldbank_forward_package.py"), 7),
    (Path("tests/test_audit_v24696_worldbank_external_package_build.py"), 6),
)
EXPECTED_TEST_COUNT = 23
FORBIDDEN_MARKERS = (
    "evaluation/",
    "v24694_worldbank_external_evaluator",
    "v24694_worldbank_gold_v1",
    "v24694_worldbank_gold_provenance",
    "v24690_worldbank_population_private",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
PRIVILEGED_FIELDS = frozenset(
    {
        "question_type",
        "category",
        "task_category",
        "ground_truth",
        "answer_key",
        "gold",
        "mapping",
        "evaluator",
        "score",
        "reward",
    }
)


def _ordinary(relative: str | Path) -> Path:
    raw = Path(relative)
    path = ROOT / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.46.96 expected ordinary file: {relative}")
    return path


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with _ordinary(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = json.loads(_ordinary(PARENT).read_text(encoding="utf-8"))
    return (
        value.get("role") == "v24695_worldbank_surface_repair_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get("one_repaired_surface_publication") is True
        and value.get("authorization", {}).get("external_protocol_design") is False
        and value.get("authorization", {}).get("preactivation_or_launch") is False
        and value.get("authorization", {}).get("evaluator_execution_on_predictions") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _constant(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.casefold()
    return None


def _forward_findings() -> tuple[list[str], list[str], list[str], list[str]]:
    markers: list[str] = []
    imports: list[str] = []
    literals: list[str] = []
    fields: list[str] = []
    for relative in FORWARD_FILES:
        source = _ordinary(relative).read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker in source:
                markers.append(f"{relative}:{marker}")
        if SECRET.search(source):
            literals.append(str(relative))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            imports.extend(
                f"{relative}:{name}"
                for name in names
                if any(token in name.casefold() for token in ("external_evaluator", "gold", "provenance"))
            )
            if isinstance(node, ast.Subscript):
                field = _constant(node.slice)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
                field = _constant(node.args[0]) if node.func.attr in {"get", "pop", "setdefault"} else None
            else:
                field = None
            if field in PRIVILEGED_FIELDS:
                fields.append(f"{relative}:{field}")
    return sorted(markers), sorted(imports), sorted(literals), sorted(fields)


def _run_test(path: Path) -> tuple[bool, int]:
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
        ],
        cwd=ROOT,
        env={
            "HOME": str(Path.home()),
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
        timeout=180,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    return completed.returncode == 0, int(match.group(1)) if match else 0


def _implementation_valid() -> bool:
    tasks = task_vector()
    return (
        PROTOCOL_ID == "v24694_worldbank_target_value_external_v1"
        and SELECTED_COUNT == 12
        and ARM_COUNT == len(ARMS) == 3
        and EXECUTOR_CONCURRENCY == 12
        and MODEL_SLOT_CAP == 8
        and TASK_WALL_SECONDS == 240.0
        and PARENT_TIMEOUT_SECONDS == 255.0
        and HARD_FETCH_DEADLINE_SECONDS == 40.0
        and SEARCH["fetch_timeout_seconds"] >= 35
        and LIMITS["model_calls"] == 3
        and LIMITS["search_queries"] == 4
        and LIMITS["fetch_targets"] == 10
        and len(tasks) == SELECTED_COUNT
        and all(set(task) == {"opaque_id", "question"} for task in tasks)
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): _sha256(path) for path in SOURCES}
    markers, imports, secret_hits, privileged = _forward_findings()
    suites = []
    for path, expected in TEST_SUITES:
        passed, observed = _run_test(path)
        suites.append(
            {
                "path": str(path),
                "expected_test_count": expected,
                "observed_test_count": observed,
                "passed": passed and observed == expected,
            }
        )
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in SOURCES)
    parent_valid = _parent_valid()
    implementation_valid = _implementation_valid()
    lease = lease_observation(ROOT, Path("/proc"))
    watchers = protected_watcher_snapshot()
    findings: list[str] = []
    if head != remote:
        findings.append("v24696_source_commit_not_pushed")
    if not clean:
        findings.append("v24696_source_worktree_not_clean")
    if not tracked:
        findings.append("v24696_source_not_tracked")
    if not parent_valid:
        findings.append("v24695_surface_parent_drifted")
    if not implementation_valid:
        findings.append("v24694_forward_package_contract_drifted")
    if markers:
        findings.append("private_or_evaluator_marker_in_forward")
    if imports:
        findings.append("evaluator_gold_or_provenance_import_in_forward")
    if secret_hits:
        findings.append("credential_literal_in_forward")
    if privileged:
        findings.append("privileged_field_access_in_forward")
    if any(not suite["passed"] for suite in suites):
        findings.append("regression_failed_or_count_drifted")
    if sum(suite["observed_test_count"] for suite in suites) != EXPECTED_TEST_COUNT:
        findings.append("total_test_count_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24696_worldbank_external_package_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"surface_repair_audit_sha256": _sha256(PARENT), "valid": parent_valid},
        "mechanism": {
            "selected_tasks": SELECTED_COUNT,
            "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
            "arms": list(ARMS),
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "task_wall_seconds": TASK_WALL_SECONDS,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "fixed_total_model_query_fetch_caps": [3, 4, 10],
            "hard_fetch_deadline_seconds": HARD_FETCH_DEADLINE_SECONDS,
            "failure_as_zero": True,
            "one_wave_no_resume_retry_skip_or_selective_rerun": True,
            "entropy_shadow_only": True,
            "implementation_valid": implementation_valid,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "suites": suites,
            "test_count": sum(suite["observed_test_count"] for suite in suites),
            "passed": all(suite["passed"] for suite in suites),
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "runtime_input_keys": ["opaque_id", "question"],
            "forbidden_forward_markers": markers,
            "evaluator_gold_or_provenance_imports": imports,
            "credential_literal_hits": secret_hits,
            "privileged_field_accesses": privileged,
            "passed": not markers and not imports and not secret_hits and not privileged,
        },
        "runtime_state": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "external_forward_launched_by_audit": False,
            "evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "external_protocol_publication": not findings,
            "preactivation_audit": False,
            "activation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24696_worldbank_external_package_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("mechanism", {}).get("implementation_valid") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_active") is not False
        or copied.get("authorization")
        != {
            "external_protocol_publication": True,
            "preactivation_audit": False,
            "activation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.96 package audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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
    value = build_audit()
    validate_audit(value)
    publish_new(ROOT / AUDIT, value)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "test_count": value["tests"]["test_count"],
            },
            sort_keys=True,
        )
    )
