#!/usr/bin/env python3
"""Staged preaudit, activation, and execution-start control for V2.47.11."""

from __future__ import annotations

import argparse
import ast
import fcntl
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

from deepwide_agent.v24711_sparse_full220_contract import (  # noqa: E402
    ACTIVATION,
    ACTIVATION_AUTHORIZATION,
    EXECUTION_START,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    LEASE_PATH,
    OUTPUT_ROOT,
    PREAUDIT,
    PREAUDIT_AUTHORIZATION,
    PROTOCOL,
    PROTOCOL_ID,
    START_AUTHORIZATION,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sealed,
    sha256,
    validate_protocol,
    validate_stage,
)


FORWARD_FILES = (
    Path("src/deepwide_agent/v24709_sparse_worldbank_adapter.py"),
    Path("src/deepwide_agent/v24711_sparse_full220_contract.py"),
    Path("scripts/run_v24711_sparse_full220.py"),
)
RUNNER_MARKER = "scripts/run_v24711_sparse_full220.py"
FORBIDDEN_FIELDS = frozenset(
    {
        "answer",
        "answer_key",
        "category",
        "evaluation",
        "evaluator",
        "evaluator_mapping",
        "gold",
        "ground_truth",
        "instance_id",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
        "topic",
    }
)
EVALUATOR_IMPORT_MARKERS = (
    "official_eval",
    "official_evaluator",
    "finalize_fullset",
    "evaluator_mapping",
)
FORBIDDEN_RESOURCE_MARKERS = (
    "data/deepwidesearch/overall_20250916.jsonl",
    "external/Marco-Search-Agent",
    "evaluator_mapping.jsonl",
    "overall_20250916_tables",
    "official_eval_results",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
TESTS = (
    ("test_v24709_sparse_worldbank_adapter.py", 11),
    ("test_v24711_sparse_full220_package.py", 8),
)


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


def _clean_remote() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.11 stage requires clean pushed HEAD")


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _lease_inactive() -> bool:
    path = ROOT / LEASE_PATH
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


def _active_runner() -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    return any(
        RUNNER_MARKER in line
        for line in completed.stdout.splitlines()
        if "ps -eo" not in line and "control_v24711_sparse_full220.py" not in line
    )


def _field_and_import_findings() -> tuple[list[str], list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    resources: list[str] = []
    secrets: list[str] = []
    for relative in FORWARD_FILES:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(str(relative))
        resources.extend(
            f"{relative}:{marker}"
            for marker in FORBIDDEN_RESOURCE_MARKERS
            if marker in source
        )
        tree = ast.parse(source, filename=str(relative))
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
            if key is not None and key.casefold() in FORBIDDEN_FIELDS:
                fields.append(f"{relative}:{node.lineno}:{key}")
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                if any(marker in name.casefold() for marker in EVALUATOR_IMPORT_MARKERS):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(fields), sorted(imports), sorted(resources), sorted(secrets)


def _run_tests() -> tuple[int, bool]:
    total = 0
    passed = True
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    for pattern, expected in TESTS:
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
                pattern,
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=90,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        count = int(match.group(1)) if match else 0
        total += count
        passed = passed and completed.returncode == 0 and count == expected
    return total, passed


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


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_remote()
    protocol = validate_protocol(ROOT)
    if not _tracked(PROTOCOL):
        raise RuntimeError("V2.47.11 protocol is not tracked")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PREAUDIT, ACTIVATION, EXECUTION_START, OUTPUT_ROOT, FORWARD_RESULT, FORWARD_AUDIT)
    ):
        raise RuntimeError("V2.47.11 preaudit future surface is not pristine")
    fields, imports, resources, secrets = _field_and_import_findings()
    test_count, tests_passed = _run_tests()
    watchers = protected_watcher_snapshot()
    lease = _lease_inactive()
    active = _active_runner()
    findings: list[str] = []
    if fields:
        findings.append("privileged_forward_field_access")
    if imports:
        findings.append("evaluator_import_in_forward")
    if resources:
        findings.append("evaluator_or_raw_benchmark_resource_in_forward")
    if secrets:
        findings.append("credential_literal_in_forward_surface")
    if not tests_passed or test_count != sum(expected for _pattern, expected in TESTS):
        findings.append("forward_package_regression_failed")
    if watchers != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if not lease:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("forward_runner_already_active")
    value = {
        "artifact_version": 1,
        "role": "v24711_sparse_full220_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "created_at_unix": int(time.time()) if now is None else int(now),
        "tests": {"observed": test_count, "passed": tests_passed},
        "label_blind_audit": {
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_field_accesses": fields,
            "evaluator_imports": imports,
            "forbidden_resource_markers": resources,
            "credential_literal_hits": secrets,
            "passed": not fields and not imports and not resources and not secrets,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers
            == protocol["execution"]["protected_watchers"],
            "shared_api_lease_inactive": lease,
            "forward_runner_active": active,
            "network_model_search_forward_or_evaluator_called_by_audit": False,
        },
        "source_policy": {
            "manifest_question_or_control_prediction_rows_opened_by_audit": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": (
            dict(PREAUDIT_AUTHORIZATION)
            if not findings
            else {
                "activation_publication": False,
                "forward_launch": False,
                "evaluator": False,
                "leaderboard_or_sota": False,
            }
        ),
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    _clean_remote()
    protocol = validate_protocol(ROOT)
    preaudit = validate_stage(
        ROOT,
        PREAUDIT,
        role="v24711_sparse_full220_preactivation_audit",
        seal_field="audit_payload_sha256",
        authorization=PREAUDIT_AUTHORIZATION,
    )
    if (
        not _tracked(PREAUDIT)
        or preaudit.get("audit_valid") is not True
        or preaudit.get("findings") != []
        or any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (ACTIVATION, EXECUTION_START, OUTPUT_ROOT, FORWARD_RESULT, FORWARD_AUDIT)
        )
        or not _lease_inactive()
        or _active_runner()
        or protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]
    ):
        raise RuntimeError("V2.47.11 activation gate failed")
    value = {
        "artifact_version": 1,
        "role": "v24711_sparse_full220_activation",
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preaudit_sha256": sha256(ROOT / PREAUDIT),
        "created_at_unix": int(time.time()) if now is None else int(now),
        "shared_api_lease_inactive": True,
        "protected_watchers": protected_watcher_snapshot(),
        "network_model_search_forward_or_evaluator_called": False,
        "authorization": dict(ACTIVATION_AUTHORIZATION),
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    _clean_remote()
    protocol = validate_protocol(ROOT)
    activation = validate_stage(
        ROOT,
        ACTIVATION,
        role="v24711_sparse_full220_activation",
        seal_field="activation_payload_sha256",
        authorization=ACTIVATION_AUTHORIZATION,
    )
    if (
        not _tracked(ACTIVATION)
        or activation.get("preaudit_sha256") != sha256(ROOT / PREAUDIT)
        or any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (EXECUTION_START, OUTPUT_ROOT, FORWARD_RESULT, FORWARD_AUDIT)
        )
        or not _lease_inactive()
        or _active_runner()
        or protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]
    ):
        raise RuntimeError("V2.47.11 execution-start gate failed")
    value = {
        "artifact_version": 1,
        "role": "v24711_sparse_full220_execution_start",
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "activation_sha256": sha256(ROOT / ACTIVATION),
        "created_at_unix": int(time.time()) if now is None else int(now),
        "runtime_input_keys": ["opaque_id", "question"],
        "download_cap": 4,
        "model_calls": 0,
        "search_calls": 0,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_forward_or_evaluator_called_before_start": False,
        "authorization": dict(START_AUTHORIZATION),
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("preaudit", "activation", "execution-start"))
    args = parser.parse_args()
    if args.stage == "preaudit":
        path, value = PREAUDIT, build_preaudit()
    elif args.stage == "activation":
        path, value = ACTIVATION, build_activation()
    else:
        path, value = EXECUTION_START, build_execution_start()
    _publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "authorization": value["authorization"]}, sort_keys=True))
